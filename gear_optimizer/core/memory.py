"""The memory guard: a watchdog thread that asks the process to leave once its process tree's RSS reaches the soft
limit (a run's solve worker leaves after its song and a new worker takes its place; the service's worker leaves after
its request)."""

import logging
import os
import sys
import threading
import time

import psutil

from ..settings import RunSettings

# Errors a per-process RSS read can raise. `psutil.AccessDenied` is a `psutil.Error`, NOT an
# `OSError`, so it must be listed explicitly or it escapes the read guard and kills the
# watchdog thread (on macOS, `memory_full_info()` on a CHILD process needs the `task_for_pid`
# entitlement and raises AccessDenied).
_RSS_READ_ERRORS: tuple[type[BaseException], ...] = (OSError, AttributeError, ValueError, psutil.Error)

# Default RSS ceiling as a share of physical memory; Windows and macOS keep a stricter default.
DEFAULT_MEMORY_GUARD_PERCENT = 50.0
STRICT_PLATFORM_MEMORY_GUARD_PERCENT = 35.0
MEMORY_WATCHDOG_INTERVAL_SEC = 5

# Global watchdog state
MEMORY_WATCHDOG_LIMIT_BYTES = 0
MEMORY_WATCHDOG_THREAD = None
MEMORY_WATCHDOG_EVENT = threading.Event()
MEMORY_WATCHDOG_ANNOUNCED_LIMIT = None
MEMORY_WATCHDOG_TOTAL_RAM_BYTES = None


def _bytes_to_gb(value):
    return value / (1024**3)


def memory_release_requested():
    """Whether the watchdog has requested the graceful restart."""
    return MEMORY_WATCHDOG_EVENT.is_set()


def trigger_memory_release(reason):
    if MEMORY_WATCHDOG_EVENT.is_set():
        return
    logging.warning(reason)
    print(reason)
    MEMORY_WATCHDOG_EVENT.set()


def _rss_bytes(proc, include_compressed: bool) -> int:
    """RSS of one process (+ compressed memory where psutil reports it); 0 when it cannot be read."""
    try:
        info = proc.memory_full_info() if include_compressed else proc.memory_info()
    except _RSS_READ_ERRORS:
        # macOS: memory_full_info() of a child needs the task_for_pid entitlement; plain RSS does not.
        return _rss_bytes(proc, False) if include_compressed else 0
    rss = getattr(info, "rss", 0) or 0
    return rss + (getattr(info, "compressed", 0) or 0) if include_compressed else rss


def _process_tree_rss_bytes(root_process, include_compressed=False):
    """RSS of the process and all its children (a child list that cannot be read counts as none)."""
    try:
        children = root_process.children(recursive=True)
    except _RSS_READ_ERRORS:
        children = []
    return sum(_rss_bytes(proc, include_compressed) for proc in (root_process, *children))


def _memory_watchdog_loop():
    process = psutil.Process(os.getpid())
    include_compressed = sys.platform == "darwin"
    while not MEMORY_WATCHDOG_EVENT.is_set():
        limit = MEMORY_WATCHDOG_LIMIT_BYTES
        if limit > 0:
            rss = _process_tree_rss_bytes(process, include_compressed=include_compressed)
            if rss >= limit:
                trigger_memory_release(
                    f"[MemoryGuard] RSS{' + compressed' if include_compressed else ''} {_bytes_to_gb(rss):.2f} GB >= soft limit {_bytes_to_gb(limit):.2f} GB. "
                    "Graceful restart requested after current songs finish."
                )
                break
        time.sleep(MEMORY_WATCHDOG_INTERVAL_SEC)


def ensure_memory_watchdog_thread():
    """Start the memory watchdog thread if not already running."""
    global MEMORY_WATCHDOG_THREAD
    if MEMORY_WATCHDOG_THREAD and MEMORY_WATCHDOG_THREAD.is_alive():
        return
    MEMORY_WATCHDOG_THREAD = threading.Thread(target=_memory_watchdog_loop, name="MemoryWatchdog", daemon=True)
    MEMORY_WATCHDOG_THREAD.start()


def compute_memory_guard_limit(run: RunSettings) -> int:
    """The RSS ceiling in bytes (0: no limit).

    MemorySoftLimitGB > 0 is an absolute cap; MemorySoftLimitPercent reserves a share of physical RAM
    (unset: the platform default, capped at that default; <= 0 disables it). With both, the smaller wins.
    """
    platform_default_percent = (
        STRICT_PLATFORM_MEMORY_GUARD_PERCENT
        if sys.platform in ("win32", "cygwin", "darwin")
        else DEFAULT_MEMORY_GUARD_PERCENT
    )
    limit_percent = (
        platform_default_percent if run.memory_soft_limit_percent is None else run.memory_soft_limit_percent
    )
    effective_percent = min(limit_percent, platform_default_percent) if limit_percent > 0 else 0.0
    candidates = []
    if run.memory_soft_limit_gb > 0:
        candidates.append(run.memory_soft_limit_gb * (1024**3))
    if effective_percent > 0:
        candidates.append(detect_total_physical_memory() * (effective_percent / 100.0))
    if not candidates:
        return 0
    return int(min(candidates))


def set_memory_watchdog_limit(limit_bytes: int) -> None:
    """Set the RSS soft limit (0 disables it) and start the watchdog."""
    global MEMORY_WATCHDOG_LIMIT_BYTES, MEMORY_WATCHDOG_ANNOUNCED_LIMIT
    MEMORY_WATCHDOG_LIMIT_BYTES = limit_bytes
    if limit_bytes <= 0:
        MEMORY_WATCHDOG_ANNOUNCED_LIMIT = None
        return
    ensure_memory_watchdog_thread()
    if MEMORY_WATCHDOG_ANNOUNCED_LIMIT != limit_bytes:
        MEMORY_WATCHDOG_ANNOUNCED_LIMIT = limit_bytes
        print(f"[MemoryGuard] Soft limit active: {_bytes_to_gb(limit_bytes):.2f} GB RSS")


def detect_total_physical_memory():
    """Total physical RAM in bytes (read once)."""
    global MEMORY_WATCHDOG_TOTAL_RAM_BYTES
    if MEMORY_WATCHDOG_TOTAL_RAM_BYTES is None:
        MEMORY_WATCHDOG_TOTAL_RAM_BYTES = int(psutil.virtual_memory().total)
        print(f"[MemoryGuard] Detected physical RAM: {_bytes_to_gb(MEMORY_WATCHDOG_TOTAL_RAM_BYTES):.2f} GB")
    return MEMORY_WATCHDOG_TOTAL_RAM_BYTES
