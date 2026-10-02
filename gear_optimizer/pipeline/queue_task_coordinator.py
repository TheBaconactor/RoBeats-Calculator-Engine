"""Song-queue discovery and task preparation, extracted from GearOptimizerApp.

Owns the queue/task half of a run iteration: chart discovery and filtering by the
run settings, memory-guard resume merge, queue finalization, and the queue's
tasks (one per song run, each with its GA seed). App state reaches this class
only through the injected ``stop_requested_fn()`` (cooperative stop polling during
discovery), so the logic is unit-testable without a GPU, a DB write path, or a
constructed GearOptimizerApp.
"""

from __future__ import annotations

import logging
import os
import re
import secrets
import typing
import zlib

from gear_optimizer.core.memory import (
    build_memory_guard_resume_context,
    load_memory_guard_resume_state,
)
from gear_optimizer.store import schema
from gear_optimizer.store.db import present_songs
from gear_optimizer.domain.jobs import SharedRunContext, SongTask
from gear_optimizer import settings
from gear_optimizer.chart import read_header
from gear_optimizer.settings import RunSettings
from gear_optimizer.song_queue import (
    SongQueueItem,
    finalize_song_queue,
    infer_song_difficulty_from_path,
    queue_path_key,
)

logger = logging.getLogger(__name__)


class QueueTaskCoordinator:
    def __init__(self, *, stop_requested_fn):
        self._stop_requested = stop_requested_fn

    def get_filter_params(self, run: RunSettings):
        diff_lower = run.difficulty.strip().lower()
        filter_search = run.song_name.strip().lower()

        def _parse_color_targets(raw_val):
            tokens = [c.strip().lower() for c in re.split(r"[,\|/]", raw_val or "") if c and c.strip()]
            is_all = not tokens or any(c in ("all", "any", "*") for c in tokens)
            return is_all, set() if is_all else set(tokens)

        target_primary_all, target_primary_colors = _parse_color_targets(run.target_primary)
        target_secondary_all, target_secondary_colors = _parse_color_targets(run.target_secondary)
        return (
            diff_lower,
            filter_search,
            target_primary_all,
            target_primary_colors,
            target_secondary_all,
            target_secondary_colors,
        )

    def build_song_queue(self, run: RunSettings):
        diff_lower, filter_search, tp_all, tp_cols, ts_all, ts_cols = self.get_filter_params(run)
        resume_context = build_memory_guard_resume_context(diff_lower, filter_search, tp_all, tp_cols, ts_all, ts_cols)

        song_queue_limit = int(run.song_queue_limit)

        _presence_lookup_cache: dict[tuple[str, ...], set[str]] = {}

        def _lookup_song_presence(song_names: typing.Iterable[str]) -> set[str]:
            names = tuple(sorted({str(name or "").strip() for name in (song_names or []) if str(name or "").strip()}))
            if not names:
                return set()
            cached = _presence_lookup_cache.get(names)
            if cached is not None:
                return cached
            present = _songs_in_database(names)
            _presence_lookup_cache[names] = present
            return present

        resume_seed_queue: list[SongQueueItem] = []
        resume_known_path_keys: set[str] | None = None
        resume_has_known_paths = False
        if not run.ignore_resume_queue:
            resume_state = load_memory_guard_resume_state(resume_context)
            resume_seed_queue = resume_state.pending
            resume_known_path_keys = resume_state.known_path_keys
            resume_has_known_paths = resume_known_path_keys is not None
            if resume_seed_queue:
                logger.info(f"[MemoryGuard] Resuming {len(resume_seed_queue)} song(s) from previous interrupted run.")
        song_queue: list[SongQueueItem] = []
        seen_paths = set()
        if diff_lower not in ("easy", "normal", "hard"):
            difficulties = settings.DIFFICULTIES
        else:
            difficulties = (diff_lower.capitalize(),)
        dirs_to_search = [str(settings.paths().chart_dir(difficulty)) for difficulty in difficulties]
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
                    meta = read_header(fp)
                    name = meta.get("Song Name", "")
                    if not name:
                        raise ValueError(f"{fp}: chart has no Song Name header")
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
        if resume_seed_queue and not resume_has_known_paths:
            resume_known_path_keys = {queue_path_key(item) for item in song_queue}
        logger.info(f"[Queue] Discovered {len(song_queue)} song(s) (Difficulty={run.difficulty})")
        song_names_present_in_db: set[str] = set()
        try:
            song_names_present_in_db = _lookup_song_presence((item[1] for item in song_queue))
        except Exception as exc:
            logging.warning(f"[DB] Failed to prioritize song queue: {type(exc).__name__}: {exc}")

        finalized = finalize_song_queue(
            discovered_queue=song_queue,
            resume_queue=resume_seed_queue or None,
            resume_known_path_keys=resume_known_path_keys,
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

    def prepare_tasks(self, song_queue, run: RunSettings, curves, gears, minis) -> list[SongTask]:
        """A task per song and run (SongRepeats, at most 100), each with a GA seed of its own: with GA_SEED set the
        seed is stable per song and run, else random; no two tasks of the queue share one."""
        context = SharedRunContext(
            multi_start=run.multi_start, curves=curves, gears=gears, minis=minis, ga_depth=run.search_depth
        )
        seed_base = settings.ga_seed()
        song_repeats = max(1, min(run.song_repeats, 100))
        used_seeds: set[int] = set()
        tasks = []
        for fp, song_name, _difficulty in song_queue:
            for repeat_index in range(1, song_repeats + 1):
                if seed_base is not None:
                    name_crc = zlib.crc32(song_name.encode("utf-8", errors="replace"))
                    seed = ((seed_base & 0xFFFFFFFF) + name_crc + repeat_index * 0x9E3779B1) & 0xFFFFFFFF
                    while seed in used_seeds:
                        seed = (seed + 1) & 0xFFFFFFFF
                else:
                    seed = secrets.randbits(32)
                    while seed in used_seeds:
                        seed = secrets.randbits(32)
                used_seeds.add(seed)
                task = SongTask(fp, song_name, context, seed, repeat_index, song_repeats)
                logger.info(f"[QUEUE] {task.label}")
                tasks.append(task)
        return tasks


def _songs_in_database(names: typing.Iterable[str]) -> set[str]:
    """The given songs the results database has processed; none when it does not exist yet."""
    path = settings.paths().database
    if not path.exists():
        return set()
    conn = schema.connect(path)
    try:
        return present_songs(conn, names)
    finally:
        conn.close()
