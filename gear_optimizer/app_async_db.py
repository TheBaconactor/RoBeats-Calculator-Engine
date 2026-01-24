from __future__ import annotations

import logging
import queue
import threading
import time
import os
from typing import Optional

from gear_optimizer.core.constants import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.data.database import get_song_counters, save_loadouts_batch, update_song_counters


class AsyncDbSaver:
    """
    Background DB writer to avoid blocking the main loop between songs.

    This keeps `save_loadouts_batch()` off the critical path so the next song can
    start immediately (GPU stays busier) while DB inserts/dedup/prune run in a
    background thread.
    """

    def __init__(self):
        self._queue: queue.Queue = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(
                target=self._loop,
                name="AsyncDbSaver",
                daemon=True,
            )
            self._thread.start()

    def submit(self, song_name: str, entries: list[dict], *, meta: dict | None = None) -> None:
        meta = meta or {}
        # Allow "meta-only" submissions (no entries) so per-song attempt counters can
        # advance even when we intentionally skip persistence (e.g., score=0).
        if not entries and not meta.get("_processed_run"):
            return
        if not self._running:
            self.start()
        self._queue.put(("save", song_name, entries or [], meta))

    def submit_pending_fg_job(self, song_name: str, candidates: list[dict]) -> None:
        if not song_name:
            return
        if not self._running:
            self.start()
        self._queue.put(("upsert_pending_fg_job", str(song_name), candidates or []))

    def delete_pending_fg_job(self, song_name: str) -> None:
        if not song_name:
            return
        if not self._running:
            self.start()
        self._queue.put(("delete_pending_fg_job", str(song_name)))

    def flush(self, timeout: float = 30.0) -> None:
        if not self._running:
            return
        deadline = time.monotonic() + max(0.0, float(timeout))
        while getattr(self._queue, "unfinished_tasks", 0) > 0:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(0.05, remaining))

        if getattr(self._queue, "unfinished_tasks", 0) > 0:
            try:
                pending = int(getattr(self._queue, "unfinished_tasks", 0))
            except Exception:
                pending = -1
            msg = f"[DB] Warning: async DB flush timed out; pending_tasks={pending}"
            try:
                print(msg)
            except Exception:
                pass
            try:
                logging.warning(msg)
            except Exception:
                pass

    def shutdown(self, timeout: float = 30.0) -> None:
        if not self._running:
            return

        # Best-effort flush before stopping.
        self.flush(timeout=timeout)

        try:
            self._queue.put(None)
        except Exception:
            pass

        try:
            if self._thread is not None:
                self._thread.join(timeout=timeout)
        except Exception:
            pass

        with self._lock:
            self._running = False
            self._thread = None

    def _loop(self) -> None:
        while True:
            item = self._queue.get()
            try:
                if item is None:
                    return
                if not isinstance(item, tuple) or not item:
                    continue

                kind = item[0]
                if kind == "delete_pending_fg_job":
                    try:
                        _, song_name = item
                    except Exception:
                        continue
                    try:
                        from gear_optimizer.data.database import delete_pending_fg_job

                        delete_pending_fg_job(str(song_name))
                    except Exception:
                        pass
                    continue

                if kind == "upsert_pending_fg_job":
                    try:
                        _, song_name, candidates = item
                    except Exception:
                        continue
                    try:
                        from gear_optimizer.data.database import upsert_pending_fg_job

                        upsert_pending_fg_job(str(song_name), list(candidates or []))
                    except Exception:
                        pass
                    continue

                if kind != "save":
                    continue

                try:
                    _, song_name, entries, meta = item
                except Exception:
                    continue
                if not isinstance(meta, dict):
                    meta = {}

                try:
                    db_key = meta.get("db_key") or song_name
                    processed_run = bool(meta.get("_processed_run", True))
                    file_path = meta.get("file_path")
                    cfg_dict = meta.get("cfg_dict") or {}
                    ref_arrays = meta.get("ref_arrays")

                    prev_life, prev_attempts, prev_best_score, prev_best_fg = get_song_counters(db_key)

                    run_score = 0
                    run_best_fg = 0
                    for e in entries or []:
                        if not isinstance(e, dict):
                            continue
                        try:
                            s = int(e.get("score", 0) or 0)
                        except Exception:
                            s = 0
                        try:
                            fg = int(e.get("fg_score", 0) or 0)
                        except Exception:
                            fg = 0
                        if s > run_score:
                            run_score = s
                        if e.get("force") and fg > s and fg > run_best_fg:
                            run_best_fg = fg

                    record_improved = (run_score > int(prev_best_score or 0)) or (run_best_fg > int(prev_best_fg or 0))

                    # Apply attempt metadata to persisted details (per-song semantics).
                    if processed_run:
                        attempt_lifetime = int(prev_life or 0) + 1
                        attempts_first = (
                            1 if record_improved else (int(prev_attempts or 0) + 1 if int(prev_attempts or 0) else 1)
                        )
                        for e in entries or []:
                            if not isinstance(e, dict):
                                continue
                            details = e.get("details") or {}
                            if not isinstance(details, dict):
                                details = {}
                            details = dict(details)
                            details["attempt_lifetime"] = attempt_lifetime
                            details["attempts_first"] = attempts_first
                            e["details"] = details

                    if entries:
                        save_loadouts_batch(db_key, entries)

                    # Update per-song counters (even if there were no entries to persist).
                    # NOTE: For deferred FG-only updates, `processed_run=False` is still meaningful:
                    # we do not increment attempt counters, but we may reset `attempts_first` when
                    # the best FG score improves.
                    update_song_counters(db_key, processed_run=processed_run, record_improved=record_improved)

                    # Optional: Populate TeamBuff-tier tables (T1/T5/T10/T15/NONE) in async mode.
                    # This is intentionally after base persistence so it never blocks GPU work.
                    tiers_enabled = str(os.environ.get("POST_TEAM_BUFF_TIERS", "1") or "").strip().lower() in {
                        "1",
                        "true",
                        "yes",
                        "on",
                        "",
                    }
                    if tiers_enabled and entries and file_path and ref_arrays:
                        try:
                            from gear_optimizer.data.database import save_team_buff_loadouts_batch
                            from gear_optimizer.helpers.song_helpers.team_buff_tiers import (
                                build_team_buff_tier_db_batches,
                            )
                            from gear_optimizer.pipeline.song_processor import clone_calc_song, get_base_calc_song

                            base_calc_song = get_base_calc_song(str(file_path), cfg_dict)
                            calc_song = clone_calc_song(base_calc_song)
                            # Match per-run timestamp semantics when HumanHitSim is enabled.
                            try:
                                from gear_optimizer.solver.hit_simulation import apply_human_hit_sim

                                apply_human_hit_sim(calc_song, cfg_dict=cfg_dict)
                            except Exception:
                                pass

                            batches = build_team_buff_tier_db_batches(
                                entries=entries,
                                calc_song=calc_song,
                                ref_arrays=ref_arrays,
                                cfg_dict=cfg_dict,
                                limit=int(LOADOUTS_PER_SONG_LIMIT),
                            )
                            for tier, tier_entries in (batches or {}).items():
                                if not tier_entries:
                                    continue
                                save_team_buff_loadouts_batch(db_key, str(tier), tier_entries)
                        except Exception:
                            pass
                except Exception as exc:
                    msg = f"[DB] Async save failed for {song_name}: {type(exc).__name__}: {exc}"
                    try:
                        print(msg)
                    except Exception:
                        pass
                    try:
                        logging.error(msg)
                    except Exception:
                        pass
            finally:
                try:
                    self._queue.task_done()
                except Exception:
                    pass
