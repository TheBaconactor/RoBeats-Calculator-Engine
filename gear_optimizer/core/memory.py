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
import tempfile
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass

from gear_optimizer.song_queue import normalize_queue_item, queue_path_key

try:
    import psutil
except ImportError:
    psutil = None

# Errors a per-process RSS read can raise. `psutil.AccessDenied` is a `psutil.Error`, NOT an
# `OSError`, so it must be listed explicitly or it escapes the read guard and kills the
# watchdog thread (on macOS, `memory_full_info()` on a CHILD process needs the `task_for_pid`
# entitlement and raises AccessDenied).
_RSS_READ_ERRORS: tuple[type[BaseException], ...] = (OSError, AttributeError, ValueError)
if psutil is not None:
    _RSS_READ_ERRORS = _RSS_READ_ERRORS + (psutil.Error,)

from .constants import MEMORY_WATCHDOG_INTERVAL_SEC, PATHS

# Global watchdog state
MEMORY_WATCHDOG_LIMIT_BYTES = 0
MEMORY_WATCHDOG_THREAD = None
MEMORY_WATCHDOG_EVENT = threading.Event()
MEMORY_WATCHDOG_ANNOUNCED_LIMIT = None
MEMORY_WATCHDOG_TOTAL_RAM_BYTES = None
MEMORY_WATCHDOG_TOTAL_RAM_LOGGED = False
MEMORY_WATCHDOG_PSUTIL_WARNED = False
MEMORY_GUARD_RESUME_FILE = PATHS.bin_path("memory_guard_resume.json")


@dataclass(frozen=True, slots=True)
class MemoryGuardResumeState:
    pending: list[tuple[str, str, str]]
    known_path_keys: set[str] | None


@dataclass(frozen=True, slots=True)
class _MemoryGuardResumeDiskState:
    payload: dict
    pending_entries: list[dict[str, str]]
    snapshot_pending_count: int
    journal_completion_count: int
    journal_tail_valid: bool


def _bytes_to_gb(value):
    """Convert bytes to gigabytes."""
    return value / (1024**3)


def memory_release_requested():
    """Check if memory release has been requested by the watchdog."""
    return MEMORY_WATCHDOG_EVENT.is_set()




def trigger_memory_release(reason):
    """
    Trigger memory release event (best-effort logging).

    Args:
        reason: Reason for triggering memory release
    """
    if MEMORY_WATCHDOG_EVENT.is_set():
        return
    logging.warning(reason)
    print(reason)
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
        except _RSS_READ_ERRORS:
            if not include_compressed:
                return 0
            # macOS: memory_full_info() (uss/compressed) needs the task_for_pid entitlement
            # for child processes and raises AccessDenied; plain rss via memory_info() does
            # not. Fall back so the watchdog keeps accounting the child's rss (minus the
            # compressed portion) instead of the whole watchdog thread dying.
            try:
                info = proc.memory_info()
            except _RSS_READ_ERRORS:
                return 0
            return getattr(info, "rss", 0) or 0
        rss_val = getattr(info, "rss", 0) or 0
        if include_compressed:
            rss_val += getattr(info, "compressed", 0) or 0
        return rss_val

    total = _rss_with_compressed(root_process)
    try:
        for child in root_process.children(recursive=True):
            total += _rss_with_compressed(child)
    except _RSS_READ_ERRORS:
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
    MEMORY_WATCHDOG_THREAD = threading.Thread(target=_memory_watchdog_loop, name="MemoryWatchdog", daemon=True)
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
            warn = "[MemoryGuard] psutil is unavailable; memory watchdog cannot monitor RSS."
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
        except (OSError, TypeError, ValueError):
            return 0
        return 0

    detectors = []
    if psutil is not None:
        _psutil = psutil
        detectors.append(lambda _psutil=_psutil: _psutil.virtual_memory().total)

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
            print(f"[MemoryGuard] Detected physical RAM: {_bytes_to_gb(MEMORY_WATCHDOG_TOTAL_RAM_BYTES):.2f} GB")
            MEMORY_WATCHDOG_TOTAL_RAM_LOGGED = True
    elif not MEMORY_WATCHDOG_TOTAL_RAM_LOGGED:
        logging.warning("[MemoryGuard] Unable to auto-detect physical RAM; percent-based soft limit disabled.")
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
        "primary": sorted({c.strip().lower() for c in (primary_colors or set())}) if not primary_all else [],
        "secondary_all": bool(secondary_all),
        "secondary": sorted({c.strip().lower() for c in (secondary_colors or set())}) if not secondary_all else [],
    }


def _memory_guard_resume_journal_path(path: str) -> str:
    return f"{path}.completed.jsonl"


def _normalize_memory_guard_resume_entry(entry) -> dict[str, str] | None:
    if not isinstance(entry, dict):
        return None
    fp = str(entry.get("path") or "")
    song_name = str(entry.get("song") or "")
    if not fp.strip() or not song_name.strip():
        return None
    return {
        "path": os.path.abspath(fp),
        "song": song_name,
        "diff": str(entry.get("diff") or "Unknown"),
    }


def _load_memory_guard_resume_disk_state(
    path: str,
    expected_context=None,
) -> _MemoryGuardResumeDiskState | None:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        logging.warning(f"[MemoryGuard] Failed to load resume queue: {exc}")
        return None
    if not isinstance(payload, dict):
        logging.warning("[MemoryGuard] Failed to load resume queue: root must be an object")
        return None

    stored_context = payload.get("context") or {}
    if expected_context and stored_context != expected_context:
        return None

    raw_pending = payload.get("pending", [])
    if not isinstance(raw_pending, list):
        logging.warning("[MemoryGuard] Failed to load resume queue: pending must be a list")
        return None
    snapshot_pending = []
    for entry in raw_pending:
        normalized = _normalize_memory_guard_resume_entry(entry)
        if normalized is not None:
            snapshot_pending.append(normalized)

    generation = str(payload.get("generation") or "").strip()
    completed_path_keys: set[str] = set()
    journal_tail_valid = True
    if generation:
        journal_path = _memory_guard_resume_journal_path(path)
        try:
            with open(journal_path, "r", encoding="utf-8") as fh:
                for line_number, raw_line in enumerate(fh, start=1):
                    if not raw_line.endswith("\n"):
                        logging.warning(
                            f"[MemoryGuard] Ignoring torn resume journal tail at line {line_number}: "
                            "missing record terminator"
                        )
                        journal_tail_valid = False
                        break
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except (json.JSONDecodeError, ValueError) as exc:
                        logging.warning(
                            f"[MemoryGuard] Ignoring torn resume journal tail at line {line_number}: {exc}"
                        )
                        journal_tail_valid = False
                        break
                    if not isinstance(record, dict):
                        logging.warning(
                            f"[MemoryGuard] Ignoring malformed resume journal tail at line {line_number}"
                        )
                        journal_tail_valid = False
                        break
                    if str(record.get("generation") or "") != generation:
                        continue
                    completed_path = str(record.get("path") or "")
                    if not completed_path.strip():
                        logging.warning(
                            f"[MemoryGuard] Ignoring malformed resume journal tail at line {line_number}"
                        )
                        journal_tail_valid = False
                        break
                    completed_path_keys.add(queue_path_key((completed_path, "", "")))
        except FileNotFoundError:
            pass
        except OSError as exc:
            logging.warning(f"[MemoryGuard] Failed to load resume completion journal: {exc}")
            journal_tail_valid = False

    pending_entries = [
        entry
        for entry in snapshot_pending
        if queue_path_key((entry["path"], "", "")) not in completed_path_keys
    ]
    return _MemoryGuardResumeDiskState(
        payload=payload,
        pending_entries=pending_entries,
        snapshot_pending_count=len(snapshot_pending),
        journal_completion_count=len(completed_path_keys),
        journal_tail_valid=journal_tail_valid,
    )


def load_memory_guard_resume_state(expected_context=None) -> MemoryGuardResumeState:
    """
    Load pending song queue plus original queue membership from the memory guard resume file.

    Args:
        expected_context: Expected resume context (None to skip validation)

    Returns:
        MemoryGuardResumeState with pending queue and optional known path keys
    """
    disk_state = _load_memory_guard_resume_disk_state(MEMORY_GUARD_RESUME_FILE, expected_context)
    if disk_state is None:
        return MemoryGuardResumeState(pending=[], known_path_keys=None)

    known_path_keys = None
    raw_known_paths = disk_state.payload.get("known_paths")
    if isinstance(raw_known_paths, list):
        known_path_keys = {
            queue_path_key((str(path or ""), "", ""))
            for path in raw_known_paths
            if str(path or "").strip()
        }

    pending = []
    for entry in disk_state.pending_entries:
        fp = entry["path"]
        if not os.path.exists(fp):
            continue
        pending.append(normalize_queue_item((fp, entry["song"], entry["diff"])))
    return MemoryGuardResumeState(pending=pending, known_path_keys=known_path_keys)


class MemoryGuardResumeTracker:
    """
    Tracks pending songs for graceful restart after memory limit is reached.

    Thread-safe tracker that maintains a resume queue on disk so interrupted
    batch processing can resume from where it left off.
    """

    _MIN_COMPACTION_COMPLETIONS = 64

    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self._pending_by_path: dict[str, dict[str, str]] = {}
        self._pending_paths_by_name: dict[str, deque[str]] = {}
        self.known_paths = []
        self.context = {}
        self._generation = ""
        self._snapshot_pending_count = 0
        self._journal_completion_count = 0
        self._journal_compacted = False
        self._snapshot_persisted = False
        self._durability_dirty = False

    @property
    def pending(self) -> list[dict[str, str]]:
        with self.lock:
            return list(self._pending_by_path.values())

    def _set_pending_locked(self, entries: list[dict[str, str]]) -> None:
        pending_by_path: dict[str, dict[str, str]] = {}
        pending_paths_by_name: dict[str, deque[str]] = {}
        for entry in entries:
            path_key = queue_path_key((entry["path"], "", ""))
            if path_key in pending_by_path:
                raise ValueError(f"Duplicate path in memory guard resume queue: {entry['path']}")
            pending_by_path[path_key] = entry
            name_key = entry["song"].strip().lower()
            pending_paths_by_name.setdefault(name_key, deque()).append(path_key)
        self._pending_by_path = pending_by_path
        self._pending_paths_by_name = pending_paths_by_name

    @staticmethod
    def _merge_known_paths(existing_paths, queue_paths) -> list[str]:
        merged = []
        seen = set()
        stored_paths = existing_paths if isinstance(existing_paths, list) else []
        for raw_path in [*stored_paths, *queue_paths]:
            normalized_path = os.path.abspath(str(raw_path or ""))
            path_key = queue_path_key((normalized_path, "", ""))
            if not str(raw_path or "").strip() or path_key in seen:
                continue
            seen.add(path_key)
            merged.append(normalized_path)
        return merged

    def prime(self, queue, context):
        """Initialize tracker with full queue and context, reusing compatible durable state."""
        if context is not None and not isinstance(context, dict):
            raise TypeError("Memory guard resume context must be a dictionary")
        entries = []
        for item in queue:
            normalized_item = normalize_queue_item(item)
            entries.append(
                {
                    "path": normalized_item[0],
                    "song": normalized_item[1],
                    "diff": normalized_item[2],
                }
            )
        requested_context = context or {}
        with self.lock:
            if not entries:
                self.context = {}
                self.known_paths = []
                self._set_pending_locked([])
                self._remove_state_locked()
                self._generation = ""
                self._snapshot_pending_count = 0
                self._journal_completion_count = 0
                self._journal_compacted = False
                self._durability_dirty = False
                return
            disk_state = _load_memory_guard_resume_disk_state(self.path, requested_context)
            stored_generation = "" if disk_state is None else str(disk_state.payload.get("generation") or "")
            if (
                disk_state is not None
                and stored_generation
                and disk_state.journal_tail_valid
                and disk_state.pending_entries == entries
            ):
                self.context = requested_context
                self.known_paths = self._merge_known_paths(
                    disk_state.payload.get("known_paths"),
                    (entry["path"] for entry in entries),
                )
                self._set_pending_locked(entries)
                self._generation = stored_generation
                self._snapshot_pending_count = disk_state.snapshot_pending_count
                self._journal_completion_count = disk_state.journal_completion_count
                self._journal_compacted = bool(disk_state.payload.get("journal_compacted"))
                self._snapshot_persisted = True
                self._durability_dirty = False
                return

            existing_known_paths = [] if disk_state is None else disk_state.payload.get("known_paths")
            self.context = requested_context
            self.known_paths = self._merge_known_paths(
                existing_known_paths,
                (entry["path"] for entry in entries),
            )
            self._set_pending_locked(entries)
            self._generation = uuid.uuid4().hex
            self._snapshot_pending_count = len(entries)
            self._journal_completion_count = 0
            self._journal_compacted = False
            self._snapshot_persisted = self._write_snapshot_locked(
                generation=self._generation,
                journal_compacted=False,
            )
            self._durability_dirty = not self._snapshot_persisted
            if self._snapshot_persisted:
                self._remove_journal_locked()

    def mark_completed(self, *, song_path: str | None = None, song_name: str | None = None):
        """Remove completed chart from pending queue (path-keyed; name is legacy fallback)."""
        path_key = queue_path_key((str(song_path or ""), "", "")) if song_path else ""
        norm_name = str(song_name or "").strip().lower()
        if not path_key and not norm_name:
            return
        with self.lock:
            matched_path_key = path_key if path_key in self._pending_by_path else ""
            if not path_key and norm_name:
                candidates = self._pending_paths_by_name.get(norm_name)
                while candidates and candidates[0] not in self._pending_by_path:
                    candidates.popleft()
                if candidates:
                    matched_path_key = candidates.popleft()
            if not matched_path_key:
                return

            entry = self._pending_by_path[matched_path_key]
            journaled = self._append_completion_locked(entry["path"])
            self._pending_by_path.pop(matched_path_key)
            if journaled:
                self._journal_completion_count += 1
            else:
                self._durability_dirty = True

            if not self._pending_by_path:
                self._remove_state_locked()
                self._durability_dirty = False
                return
            if not journaled:
                self._compact_locked(journal_compacted=True)
                return

            compaction_threshold = max(
                int(self._MIN_COMPACTION_COMPLETIONS),
                (self._snapshot_pending_count + 1) // 2,
            )
            if not self._journal_compacted and self._journal_completion_count >= compaction_threshold:
                self._compact_locked(journal_compacted=True)

    def pending_count(self) -> int:
        with self.lock:
            return len(self._pending_by_path)

    def _append_completion_locked(self, completed_path: str) -> bool:
        if not self._snapshot_persisted:
            return False
        journal_path = _memory_guard_resume_journal_path(self.path)
        directory = os.path.dirname(journal_path)
        try:
            if directory:
                os.makedirs(directory, exist_ok=True)
            record = json.dumps(
                {"generation": self._generation, "path": completed_path},
                separators=(",", ":"),
            )
            with open(journal_path, "a", encoding="utf-8", newline="") as fh:
                fh.write(record + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            return True
        except (OSError, TypeError, ValueError) as exc:
            logging.warning(f"[MemoryGuard] Failed to append resume completion journal: {exc}")
            return False

    def _write_snapshot_locked(self, *, generation: str, journal_compacted: bool) -> bool:
        payload = {
            "version": 2,
            "generation": generation,
            "journal_compacted": bool(journal_compacted),
            "pending": list(self._pending_by_path.values()),
            "known_paths": self.known_paths,
            "context": self.context,
        }
        directory = os.path.dirname(self.path)
        try:
            if directory:
                os.makedirs(directory, exist_ok=True)
        except OSError as exc:
            logging.warning(f"[MemoryGuard] Failed to create resume queue directory: {exc}")
            return False

        tmp_path = None
        tmp_fd = None
        try:
            tmp_dir = os.path.dirname(self.path) or "."
            tmp_prefix = os.path.basename(self.path) + "."
            tmp_fd, tmp_path = tempfile.mkstemp(prefix=tmp_prefix, suffix=".tmp", dir=tmp_dir, text=True)
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh)
                fh.flush()
                os.fsync(fh.fileno())
            tmp_fd = None
        except (OSError, TypeError, ValueError) as exc:
            logging.warning(f"[MemoryGuard] Failed to write resume queue tmp file: {exc}")
            if tmp_fd is not None:
                try:
                    os.close(tmp_fd)
                except OSError:
                    pass
            if tmp_path:
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            return False

        # Windows can intermittently raise PermissionError on atomic replace if an external
        # process (e.g., AV/scanner/indexer) briefly holds either file open.
        #
        # This state file is best-effort; never raise here (it can disable the in-flight
        # pipeline and abort long runs). We'll retry briefly, then log and continue.
        last_exc = None
        for attempt in range(12):
            try:
                os.replace(tmp_path, self.path)
                last_exc = None
                break
            except (PermissionError, FileNotFoundError, OSError) as exc:
                last_exc = exc
                time.sleep(0.01 * (attempt + 1))

        if last_exc is not None:
            logging.warning(f"[MemoryGuard] Failed to persist resume queue (continuing): {last_exc}")
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            return False
        return True

    def _compact_locked(self, *, journal_compacted: bool) -> bool:
        new_generation = uuid.uuid4().hex
        if not self._write_snapshot_locked(
            generation=new_generation,
            journal_compacted=journal_compacted,
        ):
            return False
        self._generation = new_generation
        self._snapshot_pending_count = len(self._pending_by_path)
        self._journal_completion_count = 0
        self._journal_compacted = bool(journal_compacted)
        self._snapshot_persisted = True
        self._durability_dirty = False
        self._remove_journal_locked()
        return True

    def _remove_journal_locked(self) -> None:
        try:
            os.remove(_memory_guard_resume_journal_path(self.path))
        except FileNotFoundError:
            pass
        except OSError as exc:
            logging.warning(f"[MemoryGuard] Failed to remove resume completion journal: {exc}")

    def _remove_state_locked(self) -> None:
        snapshot_removed = False
        try:
            os.remove(self.path)
            snapshot_removed = True
        except FileNotFoundError:
            snapshot_removed = True
        except OSError as exc:
            logging.warning(f"[MemoryGuard] Failed to remove resume queue: {exc}")
        if snapshot_removed:
            self._remove_journal_locked()
            self._snapshot_persisted = False

    def finalize(self, preserve_pending):
        """Finalize tracker, optionally preserving pending queue."""
        with self.lock:
            if preserve_pending and self._pending_by_path:
                if self._durability_dirty:
                    self._compact_locked(journal_compacted=True)
            else:
                self._pending_by_path = {}
                self._pending_paths_by_name = {}
                self.known_paths = []
                self.context = {}
                self._remove_state_locked()
                self._durability_dirty = False


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
    except OSError:
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
