"""Song-queue discovery and task preparation, extracted from GearOptimizerApp.

Owns the queue/task half of a run iteration: config-driven chart discovery and
filtering, memory-guard resume merge, queue finalization, and per-song task
tuples (including per-repeat GA seed assignment). App state reaches this class
only through two injected callables, so the logic is unit-testable without a
GPU, a DB write path, or a constructed GearOptimizerApp:

- ``runtime_settings_fn(cfg)`` -> the app's current runtime settings view
- ``stop_requested_fn()``      -> cooperative stop polling during discovery
"""

from __future__ import annotations

import logging
import os
import re
import secrets
import typing
import zlib

from gear_optimizer.core.constants import PATHS, SCRIPT_DIR
from gear_optimizer.core.memory import (
    build_memory_guard_resume_context,
    load_memory_guard_resume_queue,
)
from gear_optimizer.core.parsing import env_get, truthy
from gear_optimizer.core.utils import cfg_to_dict, safe_int
from gear_optimizer.data.database import get_song_names_present_in_db
from gear_optimizer.data.song_io import scan_song_header
from gear_optimizer.domain.jobs import (
    SharedRunContext,
    SongJob,
    task_tuple_from_job_context,
)
from gear_optimizer.song_queue import (
    SongQueueItem,
    finalize_song_queue,
    infer_song_difficulty_from_path,
)

logger = logging.getLogger(__name__)


class QueueTaskCoordinator:
    def __init__(self, *, runtime_settings_fn, stop_requested_fn):
        self._runtime_settings = runtime_settings_fn
        self._stop_requested = stop_requested_fn

    def get_filter_params(self, cfg):
        song_settings = self._runtime_settings(cfg).calculate_song
        diff = song_settings.difficulty or "All"
        diff_lower = diff.strip().lower()
        filter_search = song_settings.song_name.strip().lower()

        def _parse_color_targets(raw_val):
            tokens = [c.strip().lower() for c in re.split(r"[,\|/]", raw_val or "") if c and c.strip()]
            is_all = not tokens or any(c in ("all", "any", "*") for c in tokens)
            return is_all, set() if is_all else set(tokens)

        target_primary_raw = song_settings.target_primary
        target_secondary_raw = song_settings.target_secondary
        if not target_secondary_raw:
            target_secondary_raw = "all"
        target_primary_all, target_primary_colors = _parse_color_targets(target_primary_raw)
        target_secondary_all, target_secondary_colors = _parse_color_targets(target_secondary_raw)
        return (
            diff_lower,
            filter_search,
            target_primary_all,
            target_primary_colors,
            target_secondary_all,
            target_secondary_colors,
        )

    def build_song_queue(self, cfg, paths):
        diff_lower, filter_search, tp_all, tp_cols, ts_all, ts_cols = self.get_filter_params(cfg)
        resume_context = build_memory_guard_resume_context(diff_lower, filter_search, tp_all, tp_cols, ts_all, ts_cols)

        def _read_song_queue_limit() -> int:
            limit = int(self._runtime_settings(cfg).song_queue_limit)
            for env_key in ("SONG_QUEUE_LIMIT",):
                raw = env_get(env_key)
                if raw is None:
                    continue
                try:
                    env_val = safe_int(raw, 0)
                except (ValueError, TypeError):
                    env_val = 0
                if env_val and env_val > 0:
                    limit = int(env_val)
                    break
            return int(limit)

        song_queue_limit = _read_song_queue_limit()

        _presence_lookup_cache: dict[tuple[str, ...], set[str]] = {}

        def _lookup_song_presence(song_names: typing.Iterable[str]) -> set[str]:
            names = tuple(sorted({str(name or "").strip() for name in (song_names or []) if str(name or "").strip()}))
            if not names:
                return set()
            cached = _presence_lookup_cache.get(names)
            if cached is not None:
                return cached
            present = get_song_names_present_in_db(names)
            _presence_lookup_cache[names] = present
            return present

        resume_seed_queue: list[SongQueueItem] = []
        ignore_resume = bool(self._runtime_settings(cfg).ignore_resume_queue)
        if truthy(env_get("METAFINDER_IGNORE_RESUME_QUEUE", "")):
            ignore_resume = True
        if not ignore_resume:
            resume_seed_queue = load_memory_guard_resume_queue(resume_context)
            if resume_seed_queue:
                logger.info(f"[MemoryGuard] Resuming {len(resume_seed_queue)} song(s) from previous interrupted run.")
        diff = self._runtime_settings(cfg).calculate_song.difficulty or "All"
        search_dir = paths.get(diff, SCRIPT_DIR)
        song_queue: list[SongQueueItem] = []
        seen_paths = set()
        if diff_lower not in ("easy", "normal", "hard"):
            data_root = PATHS.data_dir
            dirs_to_search = [data_root] if os.path.exists(data_root) else [SCRIPT_DIR]
        else:
            dirs_to_search = [search_dir]
        for d in dirs_to_search:
            if not os.path.exists(d):
                continue
            if self._stop_requested():
                break
            for root, _, files in os.walk(d):
                if self._stop_requested():
                    break
                for f in files:
                    if self._stop_requested():
                        break
                    if not f.lower().endswith(".txt"):
                        continue
                    fp = os.path.join(root, f)
                    abs_fp = os.path.abspath(fp)
                    if abs_fp in seen_paths:
                        continue
                    meta = scan_song_header(fp)
                    if not meta:
                        continue
                    name = meta["Song Name"]
                    name_lower = name.lower()
                    detected_diff = infer_song_difficulty_from_path(root)
                    if diff_lower in ("easy", "normal", "hard") and detected_diff.lower() != diff_lower:
                        continue
                    primary_color = (meta.get("Primary Color") or "").strip().lower()
                    secondary_color = (meta.get("Secondary Color") or "").strip().lower()
                    if not tp_all and (not primary_color or primary_color not in tp_cols):
                        continue
                    if not ts_all and (not secondary_color or secondary_color not in ts_cols):
                        continue
                    if filter_search and filter_search not in name_lower:
                        continue
                    song_queue.append((fp, name, detected_diff))
                    seen_paths.add(abs_fp)
        if not song_queue and not resume_seed_queue:
            logger.error("Error: No matching songs found.")
            return []
        logger.info(f"[Queue] Discovered {len(song_queue)} song(s) (Difficulty={diff})")
        song_names_present_in_db: set[str] = set()
        try:
            song_names_present_in_db = _lookup_song_presence((item[1] for item in song_queue))
        except Exception as exc:
            logging.warning(f"[DB] Failed to prioritize song queue: {type(exc).__name__}: {exc}")

        finalized = finalize_song_queue(
            discovered_queue=song_queue,
            resume_queue=resume_seed_queue or None,
            song_queue_limit=song_queue_limit,
            present_names=song_names_present_in_db,
        )
        if resume_seed_queue:
            logger.info(
                f"[Queue] Resume merge: discovered={len(song_queue)} resume={len(resume_seed_queue)} "
                f"prepended={finalized.prepended_count} merged={len(finalized.queue)}"
            )
            if finalized.prepended_count > 0:
                logger.info(
                    f"[Queue] Prepending {finalized.prepended_count} discovered chart(s) outside resume file "
                    f"ahead of resume queue."
                )
        if finalized.limit_applied:
            if resume_seed_queue:
                logger.info(
                    f"[Queue] SongQueueLimit={song_queue_limit}: running {len(finalized.queue)} song(s) (resume+new)"
                )
            else:
                logger.info(f"[Queue] SongQueueLimit={song_queue_limit}: running {len(finalized.queue)} song(s)")
        if not filter_search:
            return finalized.queue
        logger.info(f"Found {len(finalized.queue)} songs to process.")
        return finalized.queue

    def prepare_tasks(
        self,
        song_queue,
        cfg,
        paths,
        ref_arrays,
        all_gears,
        all_minis,
        gears_by_name,
        minis_by_name,
        ga_depth,
        fg_debug,
    ):
        cfg_dict = cfg_to_dict(cfg)
        tasks = []
        parallel_workers = 1
        run_context = SharedRunContext(
            cfg_dict=cfg_dict,
            paths=paths,
            ref_arrays=ref_arrays,
            all_gears=all_gears,
            all_minis=all_minis,
            gears_by_name=gears_by_name,
            minis_by_name=minis_by_name,
            ga_depth=int(ga_depth),
            parallel_workers=int(parallel_workers),
            fg_debug=bool(fg_debug),
        )

        def _append_song_task(
            fp,
            found_song_name: str,
            task_diff: str,
            *,
            repeat_ctx: dict | None = None,
            repeat_bundle: dict | None = None,
        ) -> None:
            repeat_index = 0
            repeat_total = 0
            ga_seed = None
            extras: list[typing.Any] = []
            if repeat_ctx is not None:
                repeat_index = int(repeat_ctx.get("repeat_index") or 0)
                repeat_total = int(repeat_ctx.get("repeat_total") or 0)
                seed_raw = repeat_ctx.get("ga_seed")
                ga_seed = int(seed_raw) if seed_raw is not None else None
                extras.append(repeat_ctx)
            if repeat_bundle is not None:
                repeat_total = int(repeat_bundle.get("repeat_total") or repeat_total or 0)
                extras.append(repeat_bundle)
            job = SongJob(
                file_path=fp,
                song_name=str(found_song_name or ""),
                difficulty=str(task_diff or ""),
                repeat_index=max(0, int(repeat_index)),
                repeat_total=max(0, int(repeat_total)),
                ga_seed=ga_seed,
                repeat_bundle=repeat_bundle is not None,
                queue_source="app_prepare_tasks",
            )
            tasks.append(task_tuple_from_job_context(job, run_context, *extras))

        ga_seed_base: int | None = None
        raw_ga_seed = env_get("GA_SEED")
        if raw_ga_seed is not None and str(raw_ga_seed).strip() != "":
            try:
                ga_seed_base = int(str(raw_ga_seed).strip()) & 0xFFFFFFFF
            except (ValueError, TypeError) as exc:
                raise ValueError("GA_SEED must be an integer debug seed when set") from exc
        runtime_settings = self._runtime_settings(cfg)
        song_repeats = int(runtime_settings.song_repeats)
        try:
            song_repeats_env = safe_int(env_get("SONG_REPEATS", 0), 0)
            if song_repeats_env > 0:
                song_repeats = song_repeats_env
        except (ValueError, TypeError):
            pass
        song_repeats = max(1, min(int(song_repeats), 100))
        used_ga_seeds: set[int] = set()

        def _stable_ga_seed_for_song_repeat(song_name: str, repeat_index: int) -> int:
            base = int(ga_seed_base or 0) & 0xFFFFFFFF
            name_crc = int(zlib.crc32(str(song_name).encode("utf-8", errors="replace")) & 0xFFFFFFFF)
            idx = int(repeat_index) & 0xFFFFFFFF
            seed = (base + name_crc + (idx * 0x9E3779B1)) & 0xFFFFFFFF
            return int(seed)

        def _build_repeat_ctx(song_name: str, *, repeat_index: int, repeat_total: int) -> dict:
            if ga_seed_base is not None:
                ga_seed = _stable_ga_seed_for_song_repeat(str(song_name), int(repeat_index))
                while ga_seed in used_ga_seeds:
                    ga_seed = int((ga_seed + 1) & 0xFFFFFFFF)
            else:
                ga_seed = int(secrets.randbits(32))
                while ga_seed in used_ga_seeds:
                    ga_seed = int(secrets.randbits(32))
            used_ga_seeds.add(int(ga_seed))
            return {
                "repeat_index": int(repeat_index),
                "repeat_total": int(repeat_total),
                "ga_seed": int(ga_seed),
            }

        for fp, found_song_name, task_diff in song_queue:
            if song_repeats <= 1:
                logger.info(f"[QUEUE] {found_song_name}")
                repeat_ctx = _build_repeat_ctx(str(found_song_name), repeat_index=1, repeat_total=1)
                _append_song_task(fp, found_song_name, task_diff, repeat_ctx=repeat_ctx)
                continue
            for repeat_index in range(1, song_repeats + 1):
                repeat_ctx = _build_repeat_ctx(
                    str(found_song_name),
                    repeat_index=int(repeat_index),
                    repeat_total=int(song_repeats),
                )
                logger.info(f"[QUEUE] {found_song_name} (Run {repeat_index}/{song_repeats})")
                _append_song_task(fp, found_song_name, task_diff, repeat_ctx=repeat_ctx)
        return tasks
