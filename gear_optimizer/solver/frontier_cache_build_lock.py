"""Cross-process single-builder lock for the frontier-cache cold builds.

Both frontier caches (timeline exact + FG response) are content-addressed: two concurrent
``main.py`` processes that miss the same bundles rebuild ~all of the same work (~2x wall) and
multiply peak RAM -- which is how the 2026-07-02 EXTENDED CUT giant-chart builds hit "Unable to
allocate memory". This serializes the cold build per cache directory: the first process to acquire
builds, later processes wait, then re-run their manifest plan (which now fast-hits everything the
first process wrote) instead of duplicating the build.

External-boundary code (a lock file owned by another OS process): it must fail LOUDLY on a stale
lock -- a dead owner pid or a heartbeat that stopped advancing -- by breaking the lock and building,
never by silently skipping the build. A live owner's heartbeat keeps waiters parked; a crashed or
hung owner's heartbeat goes stale and the next waiter reclaims the lock.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_LOCK_FILE_NAME = ".build.lock"
# The owner rewrites its heartbeat this often while it holds the lock.
_HEARTBEAT_INTERVAL_S = 5.0
# A lock whose heartbeat has not advanced within this window is treated as dead (owner crashed or
# hung) and broken. Several heartbeat intervals wide so a briefly-stalled owner is not evicted.
_HEARTBEAT_STALE_S = 30.0
# Waiter poll cadence and how often it logs that it is still waiting.
_POLL_INTERVAL_S = 0.5
_WAIT_LOG_INTERVAL_S = 30.0


def _pid_alive(pid: int) -> bool:
    """Whether ``pid`` is a running process. psutil is cross-platform and safe on Windows (unlike
    ``os.kill(pid, 0)``, which terminates the process there). Absent psutil, assume alive and let
    the heartbeat-staleness window be the sole liveness signal."""
    if pid <= 0:
        return False
    try:
        import psutil

        return bool(psutil.pid_exists(int(pid)))
    except Exception:
        return True


class FrontierBuildLock:
    """A best-effort cross-process build lock rooted in the cache directory.

    Ownership is a single atomically-created lock file (``O_CREAT | O_EXCL``) carrying the owner pid
    and a heartbeat. A background thread advances the heartbeat while the lock is held; waiters poll
    and break the lock only when its owner is provably gone (dead pid or stale heartbeat).
    """

    def __init__(self, cache_dir: str | os.PathLike[str], *, label: str) -> None:
        self._path = Path(cache_dir) / _LOCK_FILE_NAME
        self._label = str(label)
        self._held = False
        self._stop = threading.Event()
        self._heartbeat_thread: threading.Thread | None = None

    def __enter__(self) -> "FrontierBuildLock":
        self._acquire()
        return self

    def __exit__(self, *_exc: object) -> bool:
        self._release()
        return False

    def _owner_payload(self) -> bytes:
        return json.dumps({"pid": int(os.getpid()), "heartbeat_ns": int(time.time_ns())}).encode("utf-8")

    def _write_owner_atomic(self) -> None:
        """Publish a fresh owner payload without a torn read: write a temp file, then atomically
        replace the lock path onto it."""
        tmp = self._path.with_name(f"{self._path.name}.{os.getpid()}.{time.perf_counter_ns()}.tmp")
        tmp.write_bytes(self._owner_payload())
        os.replace(tmp, self._path)

    def _read_owner(self) -> tuple[int, int] | None:
        """(pid, heartbeat_ns) recorded in the lock file, or None if it is missing / mid-write /
        malformed."""
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return int(data["pid"]), int(data["heartbeat_ns"])
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            logger.debug("frontier_cache_build_lock:_read_owner: %s", exc)
            return None

    def _lock_age_s(self) -> float:
        try:
            return max(0.0, (time.time_ns() - int(self._path.stat().st_mtime_ns)) / 1e9)
        except OSError:
            return 0.0

    def _is_stale(self) -> bool:
        owner = self._read_owner()
        if owner is None:
            # Unreadable/empty: could be an owner mid-create. Only stale once the file itself has sat
            # untouched past the heartbeat window.
            return self._lock_age_s() > _HEARTBEAT_STALE_S
        pid, heartbeat_ns = owner
        if not _pid_alive(pid):
            logger.warning(
                "[FrontierBuildLock] %s build lock owner pid %s is gone; breaking stale lock.",
                self._label,
                pid,
            )
            return True
        heartbeat_age_s = max(0.0, (time.time_ns() - heartbeat_ns) / 1e9)
        if heartbeat_age_s > _HEARTBEAT_STALE_S:
            logger.warning(
                "[FrontierBuildLock] %s build lock heartbeat is %.0fs stale (owner pid %s); breaking it.",
                self._label,
                heartbeat_age_s,
                pid,
            )
            return True
        return False

    def _break_stale(self) -> bool:
        """Reclaim a stale lock via a rename-steal so racing waiters cannot both break the same lock:
        only the process whose rename of the lock path succeeds owns the removal. Returns True if we
        should retry acquisition (the lock is gone or being recreated)."""
        stolen = self._path.with_name(f"{self._path.name}.stale.{os.getpid()}.{time.perf_counter_ns()}")
        try:
            os.replace(self._path, stolen)
        except (FileNotFoundError, PermissionError, OSError) as exc:
            # Another waiter stole/removed it first, or the file vanished -- just retry the acquire.
            logger.debug("frontier_cache_build_lock:_break_stale: %s", exc)
            return True
        try:
            os.unlink(stolen)
        except OSError as exc:
            logger.debug("frontier_cache_build_lock:_break_stale_unlink: %s", exc)
        return True

    def _acquire(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        waited_since_log = 0.0
        announced_wait = False
        while True:
            try:
                fd = os.open(self._path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                if self._is_stale():
                    self._break_stale()
                    continue
                if not announced_wait:
                    logger.info(
                        "[FrontierBuildLock] Another process holds the %s frontier build lock; "
                        "waiting for it to finish before re-running the manifest plan.",
                        self._label,
                    )
                    announced_wait = True
                time.sleep(_POLL_INTERVAL_S)
                waited_since_log += _POLL_INTERVAL_S
                if waited_since_log >= _WAIT_LOG_INTERVAL_S:
                    logger.info("[FrontierBuildLock] Still waiting on the %s frontier build lock...", self._label)
                    waited_since_log = 0.0
                continue
            try:
                os.write(fd, self._owner_payload())
            finally:
                os.close(fd)
            self._held = True
            self._start_heartbeat()
            if announced_wait:
                logger.info("[FrontierBuildLock] Acquired the %s frontier build lock after waiting.", self._label)
            return

    def _start_heartbeat(self) -> None:
        self._stop.clear()

        def _beat() -> None:
            while not self._stop.wait(_HEARTBEAT_INTERVAL_S):
                try:
                    self._write_owner_atomic()
                except OSError as exc:
                    logger.debug("frontier_cache_build_lock:heartbeat: %s", exc)

        thread = threading.Thread(target=_beat, name=f"frontier-build-lock-{self._label}", daemon=True)
        self._heartbeat_thread = thread
        thread.start()

    def _release(self) -> None:
        if not self._held:
            return
        self._held = False
        self._stop.set()
        thread = self._heartbeat_thread
        if thread is not None:
            thread.join(timeout=_HEARTBEAT_INTERVAL_S + 1.0)
        self._heartbeat_thread = None
        # Only drop the lock if it still records us as owner: a waiter that (wrongly) judged us stale
        # may already have stolen it, and unlinking then would remove a different owner's live lock.
        owner = self._read_owner()
        if owner is not None and owner[0] != int(os.getpid()):
            return
        try:
            os.unlink(self._path)
        except FileNotFoundError:
            pass
        except OSError as exc:
            logger.debug("frontier_cache_build_lock:_release: %s", exc)
