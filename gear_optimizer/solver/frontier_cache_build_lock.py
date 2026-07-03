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

Identity safety under a stale break: the heartbeat writes IN PLACE through the held lock file
descriptor, never by replacing the lock pathname. So if an owner stalls past the stale window (e.g.
paged out under the very memory pressure this guards), a waiter breaks the lock via a rename-steal
and acquires a fresh one, and the stalled owner later resumes, the owner's heartbeat lands on the
now-orphaned inode its fd still points at -- it can neither recreate nor clobber the new holder's
lock file. Release is gated on a unique per-holder token, so a broken-out former owner never deletes
the new holder's lock either.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
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

    Ownership is a single atomically-created lock file (``O_CREAT | O_EXCL``) carrying the owner pid,
    a unique holder token, and a heartbeat. A background thread advances the heartbeat -- writing in
    place through the held descriptor -- while the lock is held; waiters poll and break the lock only
    when its owner is provably gone (dead pid or stale heartbeat).
    """

    def __init__(self, cache_dir: str | os.PathLike[str], *, label: str) -> None:
        self._path = Path(cache_dir) / _LOCK_FILE_NAME
        self._label = str(label)
        self._token = uuid.uuid4().hex
        self._held = False
        self._fd: int | None = None
        self._stop = threading.Event()
        self._heartbeat_thread: threading.Thread | None = None

    def __enter__(self) -> "FrontierBuildLock":
        self._acquire()
        return self

    def __exit__(self, *_exc: object) -> bool:
        self._release()
        return False

    def _owner_payload(self) -> bytes:
        return json.dumps(
            {"pid": int(os.getpid()), "token": self._token, "heartbeat_ns": int(time.time_ns())}
        ).encode("utf-8")

    def _emit_heartbeat(self) -> None:
        """Refresh the heartbeat IN PLACE through the held descriptor. Crucially this writes to the
        inode this holder created, not to the lock *path*: if a waiter has already rename-stolen this
        (stale) lock and created a new one, our fd points at the orphaned inode and this write cannot
        touch the new holder's lock file. Write-then-truncate (not truncate-then-write) so a
        concurrent reader never observes an empty file."""
        fd = self._fd
        if fd is None:
            return
        payload = self._owner_payload()
        os.lseek(fd, 0, os.SEEK_SET)
        written = os.write(fd, payload)
        os.ftruncate(fd, written)

    def _read_owner(self) -> dict | None:
        """Owner record (pid, token, heartbeat_ns) in the lock file, or None if it is missing /
        mid-write / malformed."""
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return {
                "pid": int(data["pid"]),
                "token": str(data["token"]),
                "heartbeat_ns": int(data["heartbeat_ns"]),
            }
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
        pid = owner["pid"]
        if not _pid_alive(pid):
            logger.warning(
                "[FrontierBuildLock] %s build lock owner pid %s is gone; breaking stale lock.",
                self._label,
                pid,
            )
            return True
        heartbeat_age_s = max(0.0, (time.time_ns() - owner["heartbeat_ns"]) / 1e9)
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
        only the process whose rename of the lock path succeeds owns the removal. Returns True to
        signal that acquisition should be retried (the lock is now gone or being recreated)."""
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
            # Own the descriptor for the lock's lifetime: heartbeats write through it (never by
            # replacing the path), and it is closed only in _release.
            self._fd = fd
            self._held = True
            self._emit_heartbeat()
            self._start_heartbeat()
            if announced_wait:
                logger.info("[FrontierBuildLock] Acquired the %s frontier build lock after waiting.", self._label)
            return

    def _start_heartbeat(self) -> None:
        self._stop.clear()

        def _beat() -> None:
            while not self._stop.wait(_HEARTBEAT_INTERVAL_S):
                try:
                    self._emit_heartbeat()
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
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError as exc:
                logger.debug("frontier_cache_build_lock:_release_close: %s", exc)
            self._fd = None
        # Only drop the lock if it still records OUR token: a waiter that (wrongly) judged us stale
        # may already have stolen the path and created its own lock, and unlinking then would remove
        # a different holder's live lock.
        owner = self._read_owner()
        if owner is not None and owner["token"] != self._token:
            return
        try:
            os.unlink(self._path)
        except FileNotFoundError:
            pass
        except OSError as exc:
            logger.debug("frontier_cache_build_lock:_release: %s", exc)
