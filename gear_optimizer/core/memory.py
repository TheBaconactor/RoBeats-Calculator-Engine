"""
Memory management and watchdog system.

This module handles memory monitoring, soft limits, and graceful restarts
when memory usage exceeds configured thresholds.

Features:
- Background thread monitoring RSS usage
- Automatic cleanup triggers for process pool workers
- Resume queue tracking for interrupted batches
- Cross-platform memory detection (Windows, macOS, Linux)
"""
import json
import logging
import os
import re
import subprocess
import sys
import threading
import time

try:
    import psutil
except ImportError:
    psutil = None

from .constants import MEMORY_WATCHDOG_INTERVAL_SEC, PATHS

# Global watchdog state
MEMORY_WATCHDOG_LIMIT_BYTES = 0
MEMORY_WATCHDOG_THREAD = None
MEMORY_WATCHDOG_EVENT = threading.Event()
MEMORY_WATCHDOG_REASON = ""
MEMORY_WATCHDOG_ANNOUNCED_LIMIT = None
MEMORY_WATCHDOG_TOTAL_RAM_BYTES = None
MEMORY_WATCHDOG_TOTAL_RAM_LOGGED = False
MEMORY_WATCHDOG_PSUTIL_WARNED = False
MEMORY_GUARD_RESUME_FILE = PATHS.bin_path("memory_guard_resume.json")


def _bytes_to_gb(value):
    """Convert bytes to gigabytes."""
    return value / (1024 ** 3)


def memory_release_requested():
    """Check if memory release has been requested by the watchdog."""
    return MEMORY_WATCHDOG_EVENT.is_set()


def get_memory_release_message():
    """Get the reason for memory release request."""
    if MEMORY_WATCHDOG_REASON:
        return MEMORY_WATCHDOG_REASON
    return "[MemoryGuard] RSS soft limit reached; finishing current queue before exit."


def log_memory_usage(label=""):
    """Log current memory usage for leak tracking."""
    if psutil is None:
        return
    try:
        process = psutil.Process(os.getpid())
        rss_gb = process.memory_info().rss / (1024**3)
        percent = process.memory_percent()
        print(f"[MEMORY] {label}: {rss_gb:.2f} GB ({percent:.1f}%)")
    except Exception:
        logging.debug("[MEMORY] Failed to read memory usage", exc_info=True)


def trigger_memory_release(reason):
    """
    Trigger memory release event and notify Discord (if configured).

    Args:
        reason: Reason for triggering memory release
    """
    global MEMORY_WATCHDOG_REASON
    if MEMORY_WATCHDOG_EVENT.is_set():
        return
    MEMORY_WATCHDOG_REASON = reason
    logging.warning(reason)
    print(reason)
    reporter = globals().get("discord_reporter")
    if reporter:
        try:
            reporter.send_log(reason)
        except Exception:
            logging.debug("[MemoryGuard] Failed to send Discord log", exc_info=True)
    MEMORY_WATCHDOG_EVENT.set()


def _process_tree_rss_bytes(root_process, include_compressed=False):
    """
    Return RSS (optionally + compressed) for the root process plus all children.

    Args:
        root_process: psutil.Process object
        include_compressed: Include compressed memory (macOS)

    Returns:
        int: Total RSS in bytes
    """
    def _rss_with_compressed(proc):
        try:
            info = proc.memory_full_info() if include_compressed else proc.memory_info()
        except Exception:
            return 0
        rss_val = getattr(info, "rss", 0) or 0
        if include_compressed:
            rss_val += getattr(info, "compressed", 0) or 0
        return rss_val

    total = _rss_with_compressed(root_process)
    try:
        for child in root_process.children(recursive=True):
            total += _rss_with_compressed(child)
    except Exception:
        logging.debug("[MemoryGuard] Failed to read child process memory", exc_info=True)
    return total


def _memory_watchdog_loop():
    """
    Background thread loop that monitors memory usage.
    Triggers graceful shutdown when RSS exceeds soft limit.
    """
    if psutil is None:
        return
    process = psutil.Process(os.getpid())
    include_compressed = sys.platform == "darwin"
    while True:
        if MEMORY_WATCHDOG_EVENT.is_set():
            break
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
    if psutil is None:
        return
    if MEMORY_WATCHDOG_THREAD and MEMORY_WATCHDOG_THREAD.is_alive():
        return
    MEMORY_WATCHDOG_THREAD = threading.Thread(
        target=_memory_watchdog_loop, name="MemoryWatchdog", daemon=True
    )
    MEMORY_WATCHDOG_THREAD.start()


def set_memory_watchdog_limit(limit_bytes):
    """
    Set the memory watchdog soft limit and start monitoring.

    Args:
        limit_bytes: RSS limit in bytes (0 to disable)
    """
    global MEMORY_WATCHDOG_LIMIT_BYTES, MEMORY_WATCHDOG_ANNOUNCED_LIMIT, MEMORY_WATCHDOG_PSUTIL_WARNED
    limit_bytes = max(0, int(limit_bytes or 0))
    MEMORY_WATCHDOG_LIMIT_BYTES = limit_bytes
    if limit_bytes <= 0:
        MEMORY_WATCHDOG_ANNOUNCED_LIMIT = None
        return
    if psutil is None:
        if not MEMORY_WATCHDOG_PSUTIL_WARNED:
            warn = (
                "[MemoryGuard] psutil is unavailable; memory watchdog cannot monitor RSS."
            )
            logging.warning(warn)
            print(warn)
            MEMORY_WATCHDOG_PSUTIL_WARNED = True
        return
    ensure_memory_watchdog_thread()
    if MEMORY_WATCHDOG_ANNOUNCED_LIMIT != limit_bytes:
        MEMORY_WATCHDOG_ANNOUNCED_LIMIT = limit_bytes
        print(f"[MemoryGuard] Soft limit active: {_bytes_to_gb(limit_bytes):.2f} GB RSS")


def detect_total_physical_memory():
    """
    Detect total physical RAM in bytes using psutil (preferred) or
    platform-specific fallbacks so we can derive percentage-based limits.

    Returns:
        int: Total physical RAM in bytes (0 if detection fails)
    """
    global MEMORY_WATCHDOG_TOTAL_RAM_BYTES, MEMORY_WATCHDOG_TOTAL_RAM_LOGGED
    if MEMORY_WATCHDOG_TOTAL_RAM_BYTES is not None:
        return MEMORY_WATCHDOG_TOTAL_RAM_BYTES

    def _safe_detect(func):
        try:
            value = int(func() or 0)
            if value > 0:
                return value
        except Exception:
            return 0
        return 0

    detectors = []
    if psutil is not None:
        detectors.append(lambda: psutil.virtual_memory().total)

    if os.name == "nt":
        def _win32_ctypes_total():
            import ctypes

            kernel32 = ctypes.windll.kernel32
            get_mem = getattr(kernel32, "GetPhysicallyInstalledSystemMemory", None)
            if not get_mem:
                return 0
            value = ctypes.c_ulonglong(0)
            if get_mem(ctypes.byref(value)):
                return value.value * 1024
            return 0

        def _wmic_total():
            out = subprocess.check_output(
                ["wmic", "computersystem", "get", "TotalPhysicalMemory"],
                text=True,
                timeout=3,
            )
            for line in out.splitlines():
                line = line.strip()
                if line.isdigit():
                    return int(line)
            return 0

        detectors.extend((_win32_ctypes_total, _wmic_total))
    else:
        def _sysconf_total():
            page_size = os.sysconf("SC_PAGE_SIZE")
            phys_pages = os.sysconf("SC_PHYS_PAGES")
            return int(page_size) * int(phys_pages)

        detectors.append(_sysconf_total)

        if sys.platform == "darwin":
            def _sysctl_total():
                out = subprocess.check_output(
                    ["sysctl", "-n", "hw.memsize"],
                    text=True,
                    timeout=3,
                )
                return int(out.strip())

            detectors.append(_sysctl_total)
        else:
            def _proc_meminfo_total():
                try:
                    with open("/proc/meminfo", "r", encoding="utf-8") as fh:
                        for line in fh:
                            if line.lower().startswith("memtotal:"):
                                match = re.search(r"(\\d+)", line)
                                if match:
                                    return int(match.group(1)) * 1024
                except FileNotFoundError:
                    return 0
                return 0

            detectors.append(_proc_meminfo_total)

    for detector in detectors:
        total = _safe_detect(detector)
        if total:
            MEMORY_WATCHDOG_TOTAL_RAM_BYTES = total
            break
    else:
        MEMORY_WATCHDOG_TOTAL_RAM_BYTES = 0

    if MEMORY_WATCHDOG_TOTAL_RAM_BYTES > 0:
        if not MEMORY_WATCHDOG_TOTAL_RAM_LOGGED:
            print(
                "[MemoryGuard] Detected physical RAM: "
                f"{_bytes_to_gb(MEMORY_WATCHDOG_TOTAL_RAM_BYTES):.2f} GB"
            )
            MEMORY_WATCHDOG_TOTAL_RAM_LOGGED = True
    elif not MEMORY_WATCHDOG_TOTAL_RAM_LOGGED:
        logging.warning(
            "[MemoryGuard] Unable to auto-detect physical RAM; percent-based soft "
            "limit disabled."
        )
        MEMORY_WATCHDOG_TOTAL_RAM_LOGGED = True

    return MEMORY_WATCHDOG_TOTAL_RAM_BYTES


def build_memory_guard_resume_context(
    diff_key,
    filter_text,
    primary_all,
    primary_colors,
    secondary_all,
    secondary_colors,
):
    """
    Build resume context dictionary for memory guard restarts.

    Args:
        diff_key: Difficulty filter key
        filter_text: Song name filter text
        primary_all: Include all primary colors
        primary_colors: Set of primary colors
        secondary_all: Include all secondary colors
        secondary_colors: Set of secondary colors

    Returns:
        dict: Resume context
    """
    return {
        "diff": (diff_key or "").strip().lower() or "all",
        "filter": (filter_text or "").strip().lower(),
        "primary_all": bool(primary_all),
        "primary": sorted({c.strip().lower() for c in (primary_colors or set())})
        if not primary_all
        else [],
        "secondary_all": bool(secondary_all),
        "secondary": sorted({c.strip().lower() for c in (secondary_colors or set())})
        if not secondary_all
        else [],
    }


def load_memory_guard_resume_queue(expected_context=None):
    """
    Load pending song queue from memory guard resume file.

    Args:
        expected_context: Expected resume context (None to skip validation)

    Returns:
        list: List of (file_path, song_name, difficulty) tuples
    """
    if not os.path.exists(MEMORY_GUARD_RESUME_FILE):
        return []
    try:
        with open(MEMORY_GUARD_RESUME_FILE, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception as exc:
        logging.warning(f"[MemoryGuard] Failed to load resume queue: {exc}")
        return []

    stored_context = payload.get("context") or {}
    if expected_context and stored_context != expected_context:
        return []

    pending = []
    for entry in payload.get("pending", []):
        fp = entry.get("path")
        song_name = entry.get("song")
        diff = entry.get("diff", "Unknown")
        if not fp or not song_name:
            continue
        if not os.path.exists(fp):
            continue
        pending.append((fp, song_name, diff))
    return pending


class MemoryGuardResumeTracker:
    """
    Tracks pending songs for graceful restart after memory limit is reached.

    Thread-safe tracker that maintains a resume queue on disk so interrupted
    batch processing can resume from where it left off.
    """
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self.pending = []
        self.context = {}

    def prime(self, queue, context):
        """Initialize tracker with full queue and context."""
        with self.lock:
            self.context = context or {}
            self.pending = [
                {
                    "path": os.path.abspath(item[0]),
                    "song": item[1],
                    "diff": item[2],
                }
                for item in queue
            ]
            self._write_locked()

    def mark_completed(self, song_name):
        """Remove completed song from pending queue."""
        if not song_name:
            return
        norm = song_name.strip().lower()
        if not norm:
            return
        with self.lock:
            for idx, entry in enumerate(self.pending):
                if entry.get("song", "").strip().lower() == norm:
                    self.pending.pop(idx)
                    self._write_locked()
                    break

    def _write_locked(self):
        """Write resume queue to disk (must be called with lock held)."""
        if not self.pending:
            try:
                os.remove(self.path)
            except FileNotFoundError:
                pass
            return
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp_path = self.path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump({"pending": self.pending, "context": self.context}, fh)
        os.replace(tmp_path, self.path)

    def finalize(self, preserve_pending):
        """Finalize tracker, optionally preserving pending queue."""
        with self.lock:
            if preserve_pending and self.pending:
                self._write_locked()
            else:
                self.pending = []
                self.context = {}
                self._write_locked()


def restart_process_for_memory_guard():
    """
    Restart the current process to release memory.

    Launches a new instance of the script with the same arguments,
    then exits the current process.
    """
    python = sys.executable or "python"
    is_frozen = bool(getattr(sys, "frozen", False))
    message = "[MemoryGuard] Restarting optimizer to release memory and resume pending songs."
    print(message)
    try:
        logging.warning(message)
    except Exception:
        pass
    sys.stdout.flush()
    try:
        # Relaunch the *actual entrypoint* (not this module).
        #
        # - Non-frozen: sys.argv is typically ["main.py", ...] so `python + sys.argv`
        #   faithfully recreates the invocation.
        # - Frozen (PyInstaller): sys.executable is the app; sys.argv[0] is the app
        #   path, so we must NOT duplicate it.
        if is_frozen:
            cmd = [python] + sys.argv[1:]
        else:
            if sys.argv and sys.argv[0] and os.path.exists(sys.argv[0]):
                cmd = [python] + sys.argv
            else:
                main_py = os.path.join(PATHS.script_dir, "main.py")
                cmd = [python, main_py] + sys.argv[1:]

        subprocess.Popen(cmd, cwd=PATHS.script_dir)
    except Exception as exc:
        fail_msg = f"[MemoryGuard] Failed to relaunch automatically: {exc}"
        print(fail_msg)
        logging.error(fail_msg)
        sys.exit(1)
    else:
        sys.exit(0)
