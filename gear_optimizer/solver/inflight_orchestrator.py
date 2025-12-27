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
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

from gear_optimizer.core.memory import memory_release_requested
from gear_optimizer.core.utils import cfg_from_dict, safe_int
from gear_optimizer.helpers.song_helpers.database_context import load_database_context
from gear_optimizer.helpers.song_helpers.loadout_builder import build_loadout_entries
from gear_optimizer.helpers.song_helpers.song_config import setup_song_config
from gear_optimizer.solver.gpu_executor import get_gpu_executor
from gear_optimizer.solver.gpu_service import GpuServiceClient
from gear_optimizer.solver.inflight_genetic import SolveGenomesJob, solve_coevolution_genetic_inflight


def _truthy(v: Any) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


def _build_calc_song_from_file(*, fp: str, found_song_name: str, cfg) -> dict:
    from gear_optimizer.pipeline.song_processor import read_song_file

    song_data = read_song_file(fp)
    song_timestamps_np = np.array(song_data.get("timestamps") or [], dtype=np.float64)
    song_note_types_np = np.array(song_data.get("note_types") or [], dtype=np.int16)
    if song_note_types_np.shape[0] != song_timestamps_np.shape[0]:
        song_note_types_np = np.ones(song_timestamps_np.shape[0], dtype=np.int16)

    calc_song = {
        "metadata": song_data.get("song_details") or {},
        "song_data": {"timestamps": song_timestamps_np, "note_types": song_note_types_np},
    }

    # Optional: HumanHitSim (match song_processor.py semantics).
    try:
        sim_enabled = cfg.getboolean("HumanHitSim", "Enabled", fallback=False)
    except Exception:
        sim_enabled = False
    if sim_enabled and calc_song.get("song_data", {}).get("timestamps") is not None:
        from gear_optimizer.solver.hit_simulation import (
            simulate_perfect_hit_timestamps_with_great_candidates,
            stable_seed_from_text,
        )

        apply_to = cfg.get("HumanHitSim", "ApplyTo", fallback="FG").strip().upper()
        if apply_to not in {"FG", "ALL"}:
            apply_to = "FG"

        try:
            seed_in = int(cfg.get("HumanHitSim", "Seed", fallback="0") or "0")
        except Exception:
            seed_in = 0

        dist = cfg.get("HumanHitSim", "Distribution", fallback="uniform").strip().lower()
        great_mode = cfg.get("HumanHitSim", "GreatMode", fallback="late").strip().lower()

        if seed_in == 0:
            song_key = str(calc_song.get("metadata", {}).get("Song Name", "")) or str(found_song_name)
            seed_in = stable_seed_from_text(song_key)

        base_ts = np.asarray(calc_song["song_data"].get("timestamps", ()), dtype=np.float64)
        base_types = np.asarray(calc_song["song_data"].get("note_types", ()), dtype=np.int16)
        if base_types.shape[0] != base_ts.shape[0]:
            base_types = np.ones(base_ts.shape[0], dtype=np.int16)

        sim_ts, sim_great_candidates, sim_dbg = simulate_perfect_hit_timestamps_with_great_candidates(
            base_ts,
            base_types,
            seed=seed_in,
            distribution=dist,
            great_mode=great_mode,
        )

        calc_song["song_data"]["fg_timestamps"] = np.asarray(sim_ts, dtype=np.float64)
        calc_song["song_data"]["fg_great_candidate_timestamps"] = np.asarray(
            sim_great_candidates, dtype=np.float64
        )
        calc_song["metadata"]["HumanHitSimSeed"] = int(seed_in)
        calc_song["metadata"]["HumanHitSimApplyTo"] = apply_to
        calc_song["metadata"]["HumanHitSimDistribution"] = dist
        calc_song["metadata"]["HumanHitSimGreatMode"] = great_mode
        calc_song["metadata"]["HumanHitSimDebug"] = sim_dbg
        calc_song["metadata"]["HumanHitSimApplied"] = True
        if apply_to == "ALL":
            calc_song["song_data"]["timestamps"] = np.asarray(sim_ts, dtype=np.float64)

    return calc_song


def _compact_items(items: list) -> list[str]:
    out: list[str] = []
    for it in items or []:
        if isinstance(it, dict):
            name = it.get("Name", "")
        else:
            name = str(it) if it else ""
        if name:
            out.append(name)
    return out


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


def _compact_prev_record(record: Optional[dict]) -> Optional[dict]:
    if not isinstance(record, dict):
        return None
    out = dict(record)
    out["gear"] = _compact_items(record.get("gear"))
    out["minis"] = _compact_items(record.get("minis"))
    if isinstance(out.get("loadout"), (list, tuple)):
        out["loadout"] = [str(x) if x is not None else "" for x in out.get("loadout")]
    force_obj = out.get("force")
    if isinstance(force_obj, dict):
        force_copy = dict(force_obj)
        if isinstance(force_copy.get("gear"), (list, tuple)):
            force_copy["gear"] = [str(x) if x is not None else "" for x in force_copy.get("gear")]
        if isinstance(force_copy.get("minis"), (list, tuple)):
            force_copy["minis"] = [str(x) if x is not None else "" for x in force_copy.get("minis")]
        out["force"] = force_copy
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

    @property
    def capacity(self) -> int:
        return len(self._free)


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

    pending_tasks = [t for t in tasks if t[1] not in completed_songs]
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
        calc_song = _build_calc_song_from_file(fp=fp, found_song_name=found_song_name, cfg=cfg)

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

        db_best_fg_score = 0
        if known_loadouts:
            try:
                db_best_fg_score = max(v[1] for v in known_loadouts.values() if v[1])
            except Exception:
                db_best_fg_score = 0

        attempt_lifetime_prev = 0
        prev_attempts_first = 0
        if prev_record and "details" in prev_record:
            attempt_lifetime_prev = prev_record["details"].get("attempt_lifetime", 0) or 0
            prev_attempts_first = prev_record["details"].get("attempts_first", 0) or 0
        attempt_lifetime = int(attempt_lifetime_prev) + 1

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

        if status_queue:
            _emit(status_queue, found_song_name, f"InFlight slot={song_slot}")

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
            db_best_fg_score=int(db_best_fg_score or 0),
            attempt_lifetime=int(attempt_lifetime or 0),
            prev_attempts_first=int(prev_attempts_first or 0),
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
        job = song.pending_job
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

        # Candidate funnel size (reuse existing config key).
        fg_candidate_limit = safe_int(
            cfg.get("IterationEngine", "FG_CandidateLimit", fallback=200), 200
        )
        fg_candidate_limit = max(51, min(5000, int(fg_candidate_limit)))

        fg_search_radius = None
        try:
            raw_fg_radius = str(cfg.get("IterationEngine", "FG_SearchRadius", fallback="") or "").strip()
        except Exception:
            raw_fg_radius = ""
        if raw_fg_radius:
            fg_search_radius = safe_int(raw_fg_radius, -1)

        ga_candidates = list(song.ga_candidates or [])
        ga_candidates.sort(key=lambda x: x.get("Score", 0), reverse=True)
        if ga_candidates and len(ga_candidates) > fg_candidate_limit:
            ga_candidates = ga_candidates[:fg_candidate_limit]

        def build_details(data_dict: dict) -> dict:
            if not data_dict:
                return {}
            return {
                "FT": data_dict.get("FT", 0),
                "FF": data_dict.get("FF", 0),
                "GemCounts": data_dict.get("GemCounts", {}),
                "Stats": data_dict.get("Stats", {}),
                "SelectedElement": data_dict.get("Selected Element", ""),
                "PrimaryColor": song.meta_primary_color,
                "SecondaryColor": song.meta_secondary_color,
                "Difficulty": effective_difficulty,
                "ForceGreats": data_dict.get("ForceGreats", {}),
            }

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

    try:
        while pending_tasks or active:
            if memory_release_requested():
                break

            # Admit up to inflight_limit.
            while pending_tasks and len(active) < inflight_limit:
                nxt = pending_tasks.pop(0)
                if nxt[1] in completed_songs:
                    continue
                try:
                    song = _admit_one(nxt)
                except Exception as exc:
                    # Fallback: produce an error payload compatible with post_processor.
                    if post_queue is not None:
                        post_queue.put(
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

                if post_queue is not None:
                    post_queue.put(payload)

                completed_songs.add(found_song_name)
                if memory_resume_tracker:
                    memory_resume_tracker.mark_completed(found_song_name)

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
