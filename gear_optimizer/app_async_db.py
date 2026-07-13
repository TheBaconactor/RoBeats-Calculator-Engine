from __future__ import annotations
import logging
import os
import queue
import sqlite3
import threading
import time
from typing import Optional

from gear_optimizer.core.constants import PATHS
from gear_optimizer.core.parsing import env_flag
from gear_optimizer.core.team_buff import resolve_baseline_team_buff_from_cfg_dict
from gear_optimizer.data.database import (
    configure_persistent_writer_connection,
    get_db_connection,
    get_evolution_db_path,
    save_optimizer_song_result,
)


logger = logging.getLogger(__name__)
_TEAM_BUFF_REF_ARRAYS_LOCK = threading.Lock()
_TEAM_BUFF_REF_ARRAYS_CACHE: dict | None = None


def _build_ref_arrays_from_stats_table(stats_table) -> dict:
    from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats

    return build_ref_arrays_from_stats(stats_table)


def _get_team_buff_ref_arrays_cached() -> dict | None:
    """
    Load the Stats.txt lookup arrays used by on-demand TeamBuff replay.

    The main app preloads these during a normal optimizer run; DB-manager callers
    need the same tables without constructing `GearOptimizerApp`.
    """
    global _TEAM_BUFF_REF_ARRAYS_CACHE
    with _TEAM_BUFF_REF_ARRAYS_LOCK:
        if isinstance(_TEAM_BUFF_REF_ARRAYS_CACHE, dict) and _TEAM_BUFF_REF_ARRAYS_CACHE:
            return _TEAM_BUFF_REF_ARRAYS_CACHE

        try:
            from gear_optimizer.core.config import load_paths_cache
            from gear_optimizer.data.csv_parser import read_table

            paths = load_paths_cache()
            stats_path = str((paths or {}).get("Stats", "") or PATHS.stats_csv)
            stats_table = read_table(stats_path)
            _TEAM_BUFF_REF_ARRAYS_CACHE = _build_ref_arrays_from_stats_table(stats_table)
        except Exception as e:
            logger.warning(f"app_async_db:_get_team_buff_ref_arrays_cached: {e}")
            _TEAM_BUFF_REF_ARRAYS_CACHE = None
        return _TEAM_BUFF_REF_ARRAYS_CACHE


def _async_db_strict() -> bool:
    """
    Strict async DB policy.

    When enabled, async DB failures should surface to the caller so the optimizer
    doesn't continue "successfully" while persistence is broken.
    """
    return env_flag("GPU_STRICT", "1")


def _resolve_base_team_buff_for_persistence(cfg_dict: dict) -> str:
    """
    Resolve the baseline TeamBuff tier used by the optimizer for this run.

    This matches runtime semantics:
    - runtime baseline TeamBuff tier is fixed at T5
    - stale TeamContributionBuffConstant config entries are ignored
    """
    return resolve_baseline_team_buff_from_cfg_dict(cfg_dict, default="T5")


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
        self._state = "new"
        self._stop_enqueued = False
        self._terminated_event = threading.Event()
        self._lock = threading.Lock()
        self._error_lock = threading.Lock()
        self._last_error: BaseException | None = None
        self._last_error_msg: str = ""
        self._last_error_kind: str = ""
        self._last_error_song: str = ""
        self._last_error_ts: float = 0.0
        self._failures_total = 0
        self._writer_connection: sqlite3.Connection | None = None
        self._writer_db_path = ""

    def start(self) -> None:
        with self._lock:
            self._start_locked()

    def _start_locked(self) -> None:
        if self._state == "running":
            return
        if self._state != "new":
            raise RuntimeError(f"AsyncDbSaver cannot start after shutdown; state={self._state}")
        self._state = "running"
        self._stop_enqueued = False
        self._terminated_event.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name="AsyncDbSaver",
            daemon=True,
        )
        self._thread.start()

    def submit(self, song_name: str, entries: list[dict], *, meta: dict | None = None) -> None:
        self.raise_if_failed()
        meta = meta or {}
        # Allow "meta-only" submissions (no entries) so per-song attempt counters can
        # advance even when we intentionally skip persistence (e.g., score=0).
        if not entries and not meta.get("_processed_run"):
            return
        with self._lock:
            if self._state == "new":
                self._start_locked()
            if self._state != "running":
                raise RuntimeError(f"AsyncDbSaver is not accepting submissions; state={self._state}")
            self._queue.put(("save", song_name, entries or [], meta))

    def flush(self, timeout: float = 30.0) -> None:
        with self._lock:
            if self._state in {"new", "terminated"}:
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
            except Exception as e:
                logger.warning(f"app_async_db:flush: {e}")
                pending = -1
            msg = f"[DB] Warning: async DB flush timed out; pending_tasks={pending}"
            try:
                print(msg)
            except Exception as e:
                logger.warning(f"app_async_db:flush: {e}")
            try:
                logging.warning(msg)
            except Exception as e:
                logger.warning(f"app_async_db:flush: {e}")
            if _async_db_strict():
                raise RuntimeError(msg)
        self.raise_if_failed()

    def shutdown(self, timeout: float = 30.0) -> None:
        with self._lock:
            if self._state == "new":
                self._state = "terminated"
                self._terminated_event.set()
                return
            if self._state == "terminated":
                return
            if self._state == "running":
                self._state = "stopping"
            thread = self._thread

        flush_exc: BaseException | None = None
        try:
            # Best-effort flush before stopping.
            self.flush(timeout=timeout)
        except BaseException as exc:
            # Still shut down the thread to avoid leaving it running across a "failed" shutdown.
            flush_exc = exc

        with self._lock:
            if not self._stop_enqueued:
                self._queue.put(None)
                self._stop_enqueued = True

        if thread is not None:
            thread.join(timeout=max(0.0, float(timeout)))
        termination_exc: BaseException | None = None
        if thread is not None and thread.is_alive():
            termination_exc = RuntimeError("[DB] Async writer shutdown timed out before termination")

        if flush_exc is not None:
            raise flush_exc
        if termination_exc is not None:
            raise termination_exc
        self.raise_if_failed()

    def last_error(self) -> dict | None:
        with self._error_lock:
            if self._last_error is None:
                return None
            return {
                "kind": str(self._last_error_kind or ""),
                "song": str(self._last_error_song or ""),
                "message": str(self._last_error_msg or ""),
                "ts_monotonic": float(self._last_error_ts or 0.0),
                "failures_total": int(self._failures_total),
            }

    def raise_if_failed(self) -> None:
        if not _async_db_strict():
            return
        err = self.last_error()
        if not err:
            return
        kind = err.get("kind") or "unknown"
        song = err.get("song") or "?"
        msg = err.get("message") or "unknown error"
        raise RuntimeError(f"[DB][ASYNC][{kind}] {song}: {msg}")

    def _record_error(self, kind: str, exc: BaseException, *, song_name: str = "") -> None:
        msg = f"{type(exc).__name__}: {exc}"
        try:
            now = float(time.monotonic())
        except Exception as e:
            logger.warning(f"app_async_db:_record_error: {e}")
            now = 0.0
        with self._error_lock:
            self._last_error = exc
            self._last_error_msg = str(msg)
            self._last_error_kind = str(kind or "unknown")
            self._last_error_song = str(song_name or "")
            self._last_error_ts = float(now)
            self._failures_total = int(self._failures_total) + 1

    def _get_writer_connection(self, db_path: str) -> sqlite3.Connection:
        resolved_path = os.path.normcase(os.path.realpath(os.path.abspath(str(db_path))))
        if self._writer_connection is not None and resolved_path == self._writer_db_path:
            return self._writer_connection
        self._close_writer_connection()
        conn = get_db_connection(resolved_path)
        try:
            configure_persistent_writer_connection(conn)
        except BaseException:
            conn.close()
            raise
        self._writer_connection = conn
        self._writer_db_path = resolved_path
        return conn

    def _close_writer_connection(self) -> None:
        conn = self._writer_connection
        self._writer_connection = None
        self._writer_db_path = ""
        if conn is not None:
            conn.close()

    def _loop(self) -> None:
        try:
            while True:
                item = self._queue.get()
                try:
                    if item is None:
                        return
                    if not isinstance(item, tuple) or not item:
                        continue
                    if item[0] != "save":
                        continue

                    try:
                        _, song_name, entries, meta = item
                    except Exception as e:
                        logger.warning(f"app_async_db:_loop: {e}")
                        continue
                    if not isinstance(meta, dict):
                        meta = {}

                    try:
                        db_key = meta.get("db_key") or song_name
                        processed_run = bool(meta.get("_processed_run", True))
                        cfg_dict = meta.get("cfg_dict") or {}
                        canonical_db_path = str(get_evolution_db_path() or "").strip()
                        conn = self._get_writer_connection(canonical_db_path)
                        save_optimizer_song_result(
                            db_key,
                            entries,
                            processed_run=processed_run,
                            conn=conn,
                            db_path=canonical_db_path,
                            team_buff=_resolve_base_team_buff_for_persistence(cfg_dict),
                        )
                    except Exception as exc:
                        self._record_error("save", exc, song_name=str(song_name))
                        msg = f"[DB] Async save failed for {song_name}: {type(exc).__name__}: {exc}"
                        try:
                            print(msg)
                        except Exception as e:
                            logger.warning(f"app_async_db:_loop: {e}")
                        try:
                            logging.error(msg)
                        except Exception as e:
                            logger.warning(f"app_async_db:_loop: {e}")
                finally:
                    try:
                        self._queue.task_done()
                    except Exception as e:
                        logger.warning(f"app_async_db:_loop: {e}")
        finally:
            try:
                self._close_writer_connection()
            finally:
                with self._lock:
                    if self._thread is threading.current_thread():
                        self._thread = None
                        self._state = "terminated"
                        self._terminated_event.set()
