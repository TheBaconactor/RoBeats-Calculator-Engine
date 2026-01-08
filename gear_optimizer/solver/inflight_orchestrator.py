"""
In-flight multi-song orchestrator (single process, single GPU owner thread).

This module finishes the "multi-song in-flight" architecture by:
- Running multiple songs' CPU GA orchestration in the main thread
- Offloading Taichi GPU calls (population evaluation + optional ForceGreats) to
  the `GpuExecutor` thread via `GpuServiceClient`

This is intentionally opt-in and designed to be called from the sequential
runner in `gear_optimizer/app.py`.
"""

from __future__ import annotations

import concurrent.futures
import queue
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

from gear_optimizer.core.config import read_fg_candidate_limit, read_fg_search_radius
from gear_optimizer.core.constants import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.core.memory import memory_release_requested
from gear_optimizer.core.utils import cfg_from_dict, safe_int
from gear_optimizer.helpers.song_helpers.database_context import load_database_context
from gear_optimizer.helpers.song_helpers.loadout_builder import build_loadout_entries
from gear_optimizer.helpers.song_helpers.persistence import make_build_details_fn
from gear_optimizer.helpers.song_helpers.song_config import setup_song_config
from gear_optimizer.solver.gpu_executor import get_gpu_executor
from gear_optimizer.solver.gpu_service import GpuServiceClient
from gear_optimizer.solver.inflight_genetic import SolveGenomesJob, solve_coevolution_genetic_inflight
from gear_optimizer.solver.inflight_utils import (
    _build_calc_song_from_file,
    _compact_items,
    _compact_prev_record,
    _summarize_db_context,
    _truthy,
)


def _compact_fg_variants(variants: list[dict]) -> list[dict]:
    out = []
    for v in variants or []:
        if not isinstance(v, dict):
            continue
        out.append(
            {
                "score": v.get("score", 0),
                "fg_score": v.get("fg_score", 0),
                "gear": _compact_items(v.get("gear")),
                "minis": _compact_items(v.get("minis")),
                "data": v.get("data") or {},
            }
        )
    return out


def _compact_ga_candidates(candidates: list[dict]) -> list[dict]:
    out = []
    for c in candidates or []:
        if not isinstance(c, dict):
            continue
        out.append(
            {
                "Score": c.get("Score", 0),
                "BaseScore": c.get("BaseScore", c.get("Score", 0)),
                "Gear": _compact_items(c.get("Gear")),
                "Minis": _compact_items(c.get("Minis")),
                "Data": c.get("Data") or {},
                "_fg_priority": c.get("_fg_priority", 0),
            }
        )
    return out


def _compact_loadout_entries(entries: Optional[dict]) -> Optional[dict]:
    if entries is None:
        return None
    out = {}
    for k, v in entries.items():
        if not isinstance(v, dict):
            continue
        out[str(k)] = {
            "score": v.get("score", 0),
            "base_score": v.get("base_score", v.get("score", 0)),
            "fg_score": v.get("fg_score", 0),
            "gear": _compact_items(v.get("gear")),
            "minis": _compact_items(v.get("minis")),
            "details": v.get("details") or {},
            "force": v.get("force"),
        }
    return out


class SongSlotPool:
    def __init__(self, max_song_slots: int):
        # Slot 0 is reserved; allocate 1..N-1.
        n = max(2, int(max_song_slots))
        self._free = deque(range(1, n))

    def acquire(self) -> int:
        if not self._free:
            raise RuntimeError("No free GPU song slots")
        return int(self._free.popleft())

    def release(self, slot_id: int) -> None:
        slot_id = int(slot_id)
        if slot_id <= 0:
            return
        if slot_id not in self._free:
            self._free.append(slot_id)


@dataclass
class _InflightSong:
    task: tuple
    song_slot: int
    cfg: Any
    calc_song: dict
    fixed_stats: dict
    current_gear_list: list
    current_mini_list: list
    enable_gear: bool
    enable_mini: bool
    manual_force_greats: bool
    force_greats_finder: bool
    force_greats_config: list
    prev_record: Optional[dict]
    known_loadouts: Optional[dict]
    db_best_fg_score: int
    attempt_lifetime: int
    prev_attempts_first: int
    meta_primary_color: str
    meta_secondary_color: str

    ga_gen: Any
    pending_eval: Optional[concurrent.futures.Future] = None
    pending_job: Optional[SolveGenomesJob] = None

    ga_done: bool = False
    ga_candidates: Optional[list] = None
    loadout_entries: Optional[dict] = None
    pending_fg: Optional[concurrent.futures.Future] = None
    fg_variants: list = None

    def __post_init__(self) -> None:
        if self.fg_variants is None:
            self.fg_variants = []


def run_inflight_song_pipeline(
    tasks: list[tuple],
    *,
    in_flight_songs: int,
    completed_songs: set[str],
    memory_resume_tracker=None,
    post_queue=None,
    total_tasks: int | None = None,
    stop_requested=None,
) -> None:
    """
    Run an in-flight multi-song pipeline.

    This function owns the GPU executor lifecycle for the duration of the run.
    """
    if not tasks:
        return

    try:
        from gear_optimizer.solver.taichi_gem.fields import MAX_SONG_SLOTS

        max_song_slots = int(MAX_SONG_SLOTS)
    except Exception:
        max_song_slots = 8

    inflight_limit = max(1, int(in_flight_songs))
    inflight_limit = min(inflight_limit, max(1, max_song_slots - 1), len(tasks))

    slot_pool = SongSlotPool(max_song_slots=max_song_slots)

    gpu_executor = get_gpu_executor()
    gpu_executor.start(in_process=True)
    gpu_client = GpuServiceClient(gpu_executor)
    gpu_client.start(start_executor=False)

    pending_tasks = deque(t for t in tasks if t[1] not in completed_songs)
    active: list[_InflightSong] = []

    def _emit(status_queue, song_name: str, msg: str) -> None:
        if status_queue is None:
            return
        try:
            status_queue.put(f"[{song_name}] {msg}")
        except Exception:
            pass

    def _admit_one(task: tuple) -> Optional[_InflightSong]:
        (
            fp,
            found_song_name,
            effective_difficulty,
            cfg_dict,
            paths,
            ref_arrays,
            all_gears,
            all_minis,
            gears_by_name,
            minis_by_name,
            use_evo_db,
            auto_buff,
            ga_depth,
            status_queue,
            _parallel_workers,
            fg_debug,
        ) = task

        cfg = cfg_from_dict(cfg_dict)
        calc_song = _build_calc_song_from_file(
            fp=fp,
            found_song_name=found_song_name,
            cfg=cfg,
            cfg_dict=cfg_dict,
        )

        meta_primary_color = calc_song.get("metadata", {}).get("Primary Color", "") or ""
        meta_secondary_color = calc_song.get("metadata", {}).get("Secondary Color", "") or ""

        (
            _ga_settings,
            fixed_stats,
            _current_gear_stats,
            current_gear_list,
            _current_mini_stats,
            current_mini_list,
            _meta_finder,
            _enable_fever,
            enable_mini,
            enable_gear,
            _force_greats_mode,
            force_greats_finder,
            force_greats_config,
            manual_force_greats,
        ) = setup_song_config(cfg, calc_song, auto_buff, paths, gears_by_name, minis_by_name)

        prev_record, known_loadouts = load_database_context(
            found_song_name, bool(use_evo_db), gears_by_name, minis_by_name
        )

        db_best_fg_score, attempt_lifetime, prev_attempts_first = _summarize_db_context(prev_record, known_loadouts)

        # ForceGreatsFinder currently requires the full (Taichi-heavy) helper to run on the GPU owner thread.
        # We can still run MetaFinder-only in-flight when FG is disabled.
        gpu_mode = False
        try:
            gpu_mode = cfg.getboolean("IterationEngine", "GPU_Mode", fallback=False)
        except Exception:
            gpu_mode = False
        if not gpu_mode:
            _emit(status_queue, found_song_name, "InFlight disabled: GPU_Mode=FALSE")
            return None

        song_slot = slot_pool.acquire()
        # Propagate the reserved timeline slot to downstream FG helpers (which read from calc_song).
        try:
            calc_song["_gpu_song_slot"] = int(song_slot)
        except Exception:
            pass

        if status_queue:
            _emit(status_queue, found_song_name, f"InFlight slot={song_slot}")

        # Warm up the per-song-slot timeline on the GPU as early as possible so the first
        # population solve doesn't pay the initial grid compute cost.
        try:
            gpu_client.submit_precompute_timeline(
                calc_song=calc_song,
                ref_arrays=ref_arrays,
                song_slot=int(song_slot),
            )
        except Exception:
            pass

        ga_gen = solve_coevolution_genetic_inflight(
            cfg=cfg,
            ga_depth=int(ga_depth),
            base_stats_fixed=fixed_stats,
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            all_gears=all_gears,
            all_minis=all_minis,
            gears_by_name=gears_by_name,
            minis_by_name=minis_by_name,
            optimize_gear=bool(enable_gear),
            optimize_minis=bool(enable_mini),
            fixed_gear=current_gear_list,
            fixed_minis=current_mini_list,
            known_loadouts=known_loadouts,
            db_seed=prev_record if prev_record else None,
            song_slot=int(song_slot),
            status_cb=(lambda m, _sq=status_queue: _emit(_sq, found_song_name, str(m))),
        )

        song = _InflightSong(
            task=task,
            song_slot=song_slot,
            cfg=cfg,
            calc_song=calc_song,
            fixed_stats=fixed_stats,
            current_gear_list=current_gear_list,
            current_mini_list=current_mini_list,
            enable_gear=bool(enable_gear),
            enable_mini=bool(enable_mini),
            manual_force_greats=bool(manual_force_greats),
            force_greats_finder=bool(force_greats_finder),
            force_greats_config=force_greats_config or [],
            prev_record=prev_record,
            known_loadouts=known_loadouts,
            db_best_fg_score=int(db_best_fg_score),
            attempt_lifetime=int(attempt_lifetime),
            prev_attempts_first=int(prev_attempts_first),
            meta_primary_color=str(meta_primary_color),
            meta_secondary_color=str(meta_secondary_color),
            ga_gen=ga_gen,
        )
        return song

    def _submit_next_eval(song: _InflightSong, gpu_client: GpuServiceClient) -> None:
        if song.pending_eval is not None or song.pending_job is not None:
            return
        if song.ga_done:
            return

        try:
            job = next(song.ga_gen)
        except StopIteration as done:
            song.ga_done = True
            song.pending_job = None
            song.pending_eval = None
            song.ga_candidates = []
            try:
                res = done.value
            except Exception:
                res = None
            if res is not None:
                try:
                    song.ga_candidates = list(getattr(res, "all_evaluated", []) or [])
                    best_data = getattr(res, "best_data", {}) or {}
                    best_genome = getattr(res, "best_genome", []) or []
                    best_gear = best_genome[:6]
                    best_minis = best_genome[6:]
                    base_score = best_data.get("BaseScore") or best_data.get("Score", 0) or 0
                    song.ga_candidates.append(
                        {
                            "Score": int(base_score),
                            "BaseScore": int(base_score),
                            "Gear": best_gear,
                            "Minis": best_minis,
                            "Data": best_data,
                        }
                    )
                except Exception:
                    pass
            return

        song.pending_job = job
        handle = gpu_client.submit_solve_genomes(job.payload)
        song.pending_eval = handle.future

    def _resume_from_eval(song: _InflightSong, gpu_client: GpuServiceClient) -> None:
        if song.pending_eval is None or song.pending_job is None:
            return
        if not song.pending_eval.done():
            return

        fut = song.pending_eval
        song.pending_eval = None
        song.pending_job = None

        try:
            gpu_results = fut.result()
        except Exception as exc:
            raise RuntimeError(f"GPU solve failed for {song.task[1]}: {exc}") from exc

        try:
            next_job = song.ga_gen.send(gpu_results)
        except StopIteration as done:
            song.ga_done = True
            song.ga_candidates = []
            try:
                res = done.value
            except Exception:
                res = None
            if res is not None:
                try:
                    song.ga_candidates = list(getattr(res, "all_evaluated", []) or [])
                    best_data = getattr(res, "best_data", {}) or {}
                    best_genome = getattr(res, "best_genome", []) or []
                    best_gear = best_genome[:6]
                    best_minis = best_genome[6:]
                    base_score = best_data.get("BaseScore") or best_data.get("Score", 0) or 0
                    song.ga_candidates.append(
                        {
                            "Score": int(base_score),
                            "BaseScore": int(base_score),
                            "Gear": best_gear,
                            "Minis": best_minis,
                            "Data": best_data,
                        }
                    )
                except Exception:
                    pass
            return

        song.pending_job = next_job
        handle = gpu_client.submit_solve_genomes(next_job.payload)
        song.pending_eval = handle.future

    def _maybe_submit_force_greats(song: _InflightSong, gpu_client: GpuServiceClient) -> None:
        if not song.ga_done:
            return
        if song.pending_fg is not None or song.fg_variants:
            return

        (
            fp,
            found_song_name,
            effective_difficulty,
            cfg_dict,
            paths,
            ref_arrays,
            _all_gears,
            _all_minis,
            gears_by_name,
            minis_by_name,
            use_evo_db,
            _auto_buff,
            _ga_depth,
            _status_queue,
            _parallel_workers,
            _fg_debug,
        ) = song.task

        cfg = song.cfg
        try:
            gpu_mode = cfg.getboolean("IterationEngine", "GPU_Mode", fallback=False)
        except Exception:
            gpu_mode = False

        fg_candidate_limit = read_fg_candidate_limit(cfg, default=200, min_limit=LOADOUTS_PER_SONG_LIMIT)
        fg_search_radius = read_fg_search_radius(cfg)

        ga_candidates = list(song.ga_candidates or [])
        ga_candidates.sort(key=lambda x: x.get("Score", 0), reverse=True)
        if ga_candidates and len(ga_candidates) > fg_candidate_limit:
            ga_candidates = ga_candidates[:fg_candidate_limit]

        build_details = make_build_details_fn(song.meta_primary_color, song.meta_secondary_color, effective_difficulty)

        if not (song.manual_force_greats or song.force_greats_finder):
            song.fg_variants = []
            song.loadout_entries = None
            return

        loadout_entries = build_loadout_entries(
            found_song_name,
            bool(use_evo_db),
            ga_candidates,
            fg_candidate_limit,
            gears_by_name,
            minis_by_name,
            build_details,
        )
        song.loadout_entries = loadout_entries

        # DB loadout count (for budgeting/debug in FG helper)
        db_loadouts_full_count = 0
        if use_evo_db:
            try:
                from gear_optimizer.data.database import get_best_loadouts

                db_loadouts_full = get_best_loadouts(
                    found_song_name,
                    limit=fg_candidate_limit,
                    gears_by_name=gears_by_name,
                    minis_by_name=minis_by_name,
                )
                db_loadouts_full_count = len(db_loadouts_full)
            except Exception:
                db_loadouts_full_count = 0

        # Run the full helper on the GPU-owner thread (Taichi-heavy).
        handle = gpu_client.submit_process_force_greats(
            loadout_entries,
            bool(song.manual_force_greats),
            bool(song.force_greats_finder),
            song.force_greats_config,
            song.calc_song,
            ref_arrays,
            song.meta_primary_color,
            build_details,
            int(db_loadouts_full_count),
            use_gpu=bool(gpu_mode),
            fg_search_radius=fg_search_radius,
            perf_timing=_truthy(__import__("os").environ.get("PERF_TIMING", "0")),
        )
        song.pending_fg = handle.future

    def _finalize_ready_songs() -> list[_InflightSong]:
        finished: list[_InflightSong] = []
        for song in list(active):
            if not song.ga_done:
                continue
            if song.pending_fg is not None:
                if not song.pending_fg.done():
                    continue
                try:
                    song.fg_variants = song.pending_fg.result() or []
                except Exception:
                    song.fg_variants = []
                song.pending_fg = None

            # If FG was required, ensure variants are ready; else fg_variants is already [].
            if (song.manual_force_greats or song.force_greats_finder) and song.pending_fg is not None:
                continue
            finished.append(song)
        return finished

    def _try_post(item: Any, *, timeout_s: float = 0.5) -> bool:
        if post_queue is None:
            return True
        while True:
            if stop_requested is not None and callable(stop_requested) and stop_requested():
                return False
            try:
                post_queue.put(item, block=True, timeout=float(timeout_s))
                return True
            except queue.Full:
                continue
            except Exception:
                return False

    stopping = False
    try:
        while pending_tasks or active:
            if memory_release_requested():
                break
            if stop_requested is not None and callable(stop_requested) and stop_requested():
                if not stopping:
                    stopping = True
                    try:
                        pending_tasks.clear()
                    except Exception:
                        pass

            # Admit up to inflight_limit.
            while (not stopping) and pending_tasks and len(active) < inflight_limit:
                nxt = pending_tasks.popleft()
                if nxt[1] in completed_songs:
                    continue
                try:
                    song = _admit_one(nxt)
                except Exception as exc:
                    # Fallback: produce an error payload compatible with post_processor.
                    _try_post(
                        {
                            "_error": str(exc),
                            "_error_type": type(exc).__name__,
                            "_song_name": nxt[1],
                            "song": nxt[1],
                        }
                    )
                    completed_songs.add(nxt[1])
                    if memory_resume_tracker:
                        memory_resume_tracker.mark_completed(nxt[1])
                    continue
                if song is None:
                    # Not eligible; let caller fall back to normal sequential mode by raising.
                    raise RuntimeError("InFlight pipeline rejected a song (not eligible)")
                active.append(song)
                # Submit this song's first eval immediately so the GPU can start working
                # while we continue CPU admission for other songs.
                try:
                    _submit_next_eval(song, gpu_client)
                except Exception:
                    # If GA submission fails, let the outer loop handle the error on resume.
                    pass

            # Kick off evals for any song without a pending GPU job.
            for song in list(active):
                if memory_release_requested():
                    break
                if song.pending_eval is None and not song.ga_done:
                    _submit_next_eval(song, gpu_client)

            # Resume any evals that completed.
            for song in list(active):
                if song.pending_eval is not None and song.pending_eval.done():
                    _resume_from_eval(song, gpu_client)

            # After GA completion, schedule ForceGreats work (if needed).
            for song in list(active):
                if song.ga_done:
                    _maybe_submit_force_greats(song, gpu_client)

            # Finalize any songs whose FG stage is complete.
            finished = _finalize_ready_songs()
            for song in finished:
                (
                    fp,
                    found_song_name,
                    effective_difficulty,
                    cfg_dict,
                    paths,
                    ref_arrays,
                    _all_gears,
                    _all_minis,
                    _gears_by_name,
                    _minis_by_name,
                    use_evo_db,
                    _auto_buff,
                    _ga_depth,
                    _status_queue,
                    _parallel_workers,
                    fg_debug,
                ) = song.task

                # Build deferred compute payload for post_processor.
                best_cand = None
                if song.ga_candidates:
                    try:
                        best_cand = max(song.ga_candidates, key=lambda c: c.get("Score", 0) or 0)
                    except Exception:
                        best_cand = song.ga_candidates[-1]

                best_data = (best_cand or {}).get("Data") or {}
                best_gear = (best_cand or {}).get("Gear") or []
                best_minis = (best_cand or {}).get("Minis") or []

                db_key = found_song_name
                payload = {
                    "_deferred_post": True,
                    "song": found_song_name,
                    "db_key": db_key,
                    "file_path": fp,
                    "difficulty": effective_difficulty,
                    "use_evo_db": bool(use_evo_db),
                    "cfg_dict": cfg_dict,
                    "ref_arrays": ref_arrays,
                    "calc_song": song.calc_song,
                    "best_data": best_data,
                    "best_gear": _compact_items(best_gear),
                    "best_minis": _compact_items(best_minis),
                    "current_gear": _compact_items(song.current_gear_list),
                    "current_minis": _compact_items(song.current_mini_list),
                    "enable_gear": bool(song.enable_gear),
                    "enable_mini": bool(song.enable_mini),
                    "fg_variants": _compact_fg_variants(song.fg_variants),
                    "ga_candidates": _compact_ga_candidates(song.ga_candidates or []),
                    "loadout_entries": _compact_loadout_entries(song.loadout_entries),
                    "prev_record": _compact_prev_record(song.prev_record),
                    "attempt_lifetime": int(song.attempt_lifetime or 0),
                    "prev_attempts_first": int(song.prev_attempts_first or 0),
                    "db_best_fg_score": int(song.db_best_fg_score or 0),
                    "meta_primary_color": song.meta_primary_color,
                    "meta_secondary_color": song.meta_secondary_color,
                    "fg_debug": bool(fg_debug),
                    "log": "",
                }

                enqueued = _try_post(payload)

                if enqueued:
                    completed_songs.add(found_song_name)
                    if memory_resume_tracker:
                        memory_resume_tracker.mark_completed(found_song_name)
                else:
                    stopping = True

                try:
                    slot_pool.release(song.song_slot)
                except Exception:
                    pass

                try:
                    active.remove(song)
                except ValueError:
                    pass

            # Avoid a tight spin when GPU work is pending.
            if active:
                any_pending = any(
                    (s.pending_eval is not None and not s.pending_eval.done())
                    or (s.pending_fg is not None and not s.pending_fg.done())
                    for s in active
                )
                if any_pending:
                    time.sleep(0.001)

    finally:
        try:
            gpu_client.close(timeout=2.0)
        except Exception:
            pass
        try:
            if gpu_executor.is_running:
                gpu_executor.stop()
        except Exception:
            pass
