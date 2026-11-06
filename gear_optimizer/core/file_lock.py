"""A cross-process exclusive lock on a file (Windows + POSIX). The OS releases it when its owner dies, so a crash leaves
no stale lock behind."""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


@contextmanager
def exclusive_file_lock(lock_path: Path, *, timeout_sec: float | None = None) -> Iterator[None]:
    """Hold the lock of `lock_path`, waiting forever when `timeout_sec` is None; TimeoutError past it."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+", encoding="utf-8")
    deadline = None if timeout_sec is None else time.monotonic() + max(0.0, float(timeout_sec))
    locked = False
    try:
        if os.name == "nt":
            import msvcrt

            # Every process locks byte 0 (Windows allows a lock past the end of the file) and never reads it: a read of a
            # byte another process holds locked fails with PermissionError.
            handle.seek(0)
            while True:
                try:
                    # `msvcrt.locking(..., LK_LOCK, ...)` is not reliably blocking on Windows and can raise `EDEADLK`
                    # under contention: a non-blocking lock in a wait loop serves bounded and unbounded waits alike.
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if deadline is not None and time.monotonic() >= deadline:
                        raise TimeoutError(f"Timed out acquiring file lock for {lock_path}") from None
                    time.sleep(0.01)
        else:
            import fcntl

            while True:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | (fcntl.LOCK_NB if deadline is not None else 0))
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f"Timed out acquiring file lock for {lock_path}") from None
                    time.sleep(0.01)
        locked = True
        yield
    finally:
        if locked and os.name == "nt":
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        elif locked:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()
