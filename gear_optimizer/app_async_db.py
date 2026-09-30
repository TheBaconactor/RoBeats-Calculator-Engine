from __future__ import annotations
import logging
import os
import queue
import sqlite3
import threading
import time
from typing import Optional

from gear_optimizer.core.team_buff import OPTIMIZER_BASELINE_TEAM_BUFF
from gear_optimizer.gamedata import load_gears, load_minis
from gear_optimizer.settings import paths
from gear_optimizer.store import schema
from gear_optimizer.store.legacy import store_entries


class AsyncDbSaver:
    """
    Background DB writer to avoid blocking the main loop between songs.

    This keeps the results store's merge off the critical path so the next song can
    start immediately (GPU stays busier) while it runs in a background thread.
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
        # A processed run with nothing to store still marks the song processed (the queue skips it).
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
            pending = int(getattr(self._queue, "unfinished_tasks", 0))
            msg = f"[DB] Warning: async DB flush timed out; pending_tasks={pending}"
            print(msg)
            logging.warning(msg)
            # Fail the run rather than continue "successfully" while persistence is broken.
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
        err = self.last_error()
        if not err:
            return
        kind = err.get("kind") or "unknown"
        song = err.get("song") or "?"
        msg = err.get("message") or "unknown error"
        raise RuntimeError(f"[DB][ASYNC][{kind}] {song}: {msg}")

    def _record_error(self, kind: str, exc: BaseException, *, song_name: str = "") -> None:
        msg = f"{type(exc).__name__}: {exc}"
        now = float(time.monotonic())
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
        conn = schema.connect(resolved_path, write=True)
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

                    _, song_name, entries, meta = item
                    if not isinstance(meta, dict):
                        meta = {}

                    try:
                        db_key = str(meta.get("db_key") or song_name or "").strip()
                        if not db_key:
                            raise ValueError("a result needs a non-empty song key")
                        conn = self._get_writer_connection(str(paths().database))
                        store_entries(
                            conn,
                            db_key,
                            OPTIMIZER_BASELINE_TEAM_BUFF,
                            entries,
                            gears=load_gears(paths().gears_csv),
                            minis=load_minis(paths().minis_csv),
                        )
                    except Exception as exc:
                        self._record_error("save", exc, song_name=str(song_name))
                        msg = f"[DB] Async save failed for {song_name}: {type(exc).__name__}: {exc}"
                        print(msg)
                        logging.error(msg)
                finally:
                    self._queue.task_done()
        finally:
            try:
                self._close_writer_connection()
            finally:
                with self._lock:
                    if self._thread is threading.current_thread():
                        self._thread = None
                        self._state = "terminated"
                        self._terminated_event.set()
