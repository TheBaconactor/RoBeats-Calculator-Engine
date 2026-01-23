from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Any, Optional

from gear_optimizer.data.database import save_loadouts_batch


class AsyncDbSaver:
    """
    Background DB writer to avoid blocking the main loop between songs.

    This keeps `save_loadouts_batch()` off the critical path so the next song can
    start immediately (GPU stays busier) while DB inserts/dedup/prune run in a
    background thread.
    """

    def __init__(self, discord_reporter: Any | None = None):
        # `discord_reporter` is intentionally typed loosely to avoid import cycles.
        # It is expected to expose `.send_log(str) -> None`.
        self._discord_reporter = discord_reporter
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
        if not entries:
            return
        if not self._running:
            self.start()
        self._queue.put((song_name, entries, meta or {}))

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
            try:
                if self._discord_reporter is not None:
                    self._discord_reporter.send_log(msg)
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
                song_name, entries, meta = item
                if not isinstance(meta, dict):
                    meta = {}

                try:
                    save_loadouts_batch(song_name, entries)
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
                    try:
                        if self._discord_reporter is not None:
                            self._discord_reporter.send_log(msg)
                    except Exception:
                        pass
            finally:
                try:
                    self._queue.task_done()
                except Exception:
                    pass
