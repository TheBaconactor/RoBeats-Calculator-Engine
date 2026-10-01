"""The memory guard: a watchdog thread that requests a graceful restart once the process tree's RSS reaches the soft
limit, and the resume queue the restarted run continues from."""

import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from collections import deque
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

import psutil

from gear_optimizer.song_queue import normalize_queue_item, queue_path_key

from ..settings import ENGINE_ROOT, RunSettings, paths

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
MEMORY_GUARD_RESUME_FILE = str(paths().bin_path("memory_guard_resume.json"))


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


def build_memory_guard_resume_context(
    diff_key,
    filter_text,
    primary_all,
    primary_colors,
    secondary_all,
    secondary_colors,
):
    """The run filters a resume queue belongs to (a queue saved under other filters is not resumed)."""
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


def _read_completion_journal(path: str, generation: str) -> tuple[set[str], bool]:
    """Path keys the journal records as completed in `generation`, and whether its tail is intact: reading stops at
    the first torn or malformed record (a crash mid-append), keeping the completions before it."""
    completed: set[str] = set()
    try:
        with open(_memory_guard_resume_journal_path(path), "r", encoding="utf-8") as fh:
            for line_number, raw_line in enumerate(fh, start=1):
                line = raw_line.strip()
                problem = "" if raw_line.endswith("\n") else "missing record terminator"
                if line and not problem:
                    try:
                        record = json.loads(line)
                    except ValueError as exc:
                        record, problem = None, str(exc)
                    if not problem and not isinstance(record, dict):
                        problem = "not a completion record"
                    elif not problem and str(record.get("generation") or "") == generation:
                        completed_path = str(record.get("path") or "")
                        if completed_path.strip():
                            completed.add(queue_path_key((completed_path, "", "")))
                        else:
                            problem = "not a completion record"
                if problem:
                    logging.warning(f"[MemoryGuard] Ignoring torn resume journal tail at line {line_number}: {problem}")
                    return completed, False
    except FileNotFoundError:
        return completed, True
    except OSError as exc:
        logging.warning(f"[MemoryGuard] Failed to load resume completion journal: {exc}")
        return completed, False
    return completed, True


def _load_memory_guard_resume_disk_state(
    path: str,
    expected_context=None,
) -> _MemoryGuardResumeDiskState | None:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except (OSError, ValueError) as exc:
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
    snapshot_pending = [entry for entry in map(_normalize_memory_guard_resume_entry, raw_pending) if entry is not None]

    generation = str(payload.get("generation") or "").strip()
    completed_path_keys, journal_tail_valid = _read_completion_journal(path, generation) if generation else (set(), True)
    return _MemoryGuardResumeDiskState(
        payload=payload,
        pending_entries=[
            entry for entry in snapshot_pending if queue_path_key((entry["path"], "", "")) not in completed_path_keys
        ],
        snapshot_pending_count=len(snapshot_pending),
        journal_completion_count=len(completed_path_keys),
        journal_tail_valid=journal_tail_valid,
    )


def load_memory_guard_resume_state(expected_context=None) -> MemoryGuardResumeState:
    """The pending queue (charts still on disk) and the original queue's path keys of the stored resume queue;
    `expected_context` None skips the run-filter check."""
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
    pending = [
        normalize_queue_item((entry["path"], entry["song"], entry["diff"]))
        for entry in disk_state.pending_entries
        if os.path.exists(entry["path"])
    ]
    return MemoryGuardResumeState(pending=pending, known_path_keys=known_path_keys)


def _replace_retrying(source: str, target: str) -> None:
    """os.replace, retried for ~0.7 s: on Windows a scanner or indexer briefly holding either file makes it fail."""
    for attempt in range(11):
        try:
            os.replace(source, target)
            return
        except OSError:
            time.sleep(0.01 * (attempt + 1))
    os.replace(source, target)


class MemoryGuardResumeTracker:
    """The batch's pending songs, kept on disk so a memory-guard restart resumes where the run stopped.

    A snapshot (pending songs, the original queue's paths, the run context, a generation id) is replaced atomically;
    each completion appends one fsynced record to <snapshot>.completed.jsonl. The journal is folded into a new
    snapshot once (when it holds max(64, half the snapshot) completions) and whenever an append fails. The state
    is best effort: a disk failure is logged and never stops the run.
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

    def _clear_locked(self) -> None:
        self.context = {}
        self.known_paths = []
        self._set_pending_locked([])
        self._remove_state_locked()
        self._generation = ""
        self._snapshot_pending_count = 0
        self._journal_completion_count = 0
        self._journal_compacted = False
        self._durability_dirty = False

    def prime(self, queue, context):
        """Initialize tracker with full queue and context, reusing compatible durable state."""
        if context is not None and not isinstance(context, dict):
            raise TypeError("Memory guard resume context must be a dictionary")
        entries = [dict(zip(("path", "song", "diff"), normalize_queue_item(item))) for item in queue]
        requested_context = context or {}
        with self.lock:
            if not entries:
                self._clear_locked()
                return
            disk_state = _load_memory_guard_resume_disk_state(self.path, requested_context)
            stored_generation = "" if disk_state is None else str(disk_state.payload.get("generation") or "")
            self.context = requested_context
            self.known_paths = self._merge_known_paths(
                [] if disk_state is None else disk_state.payload.get("known_paths"),
                (entry["path"] for entry in entries),
            )
            self._set_pending_locked(entries)
            if stored_generation and disk_state.journal_tail_valid and disk_state.pending_entries == entries:
                self._generation = stored_generation
                self._snapshot_pending_count = disk_state.snapshot_pending_count
                self._journal_completion_count = disk_state.journal_completion_count
                self._journal_compacted = bool(disk_state.payload.get("journal_compacted"))
                self._snapshot_persisted = True
                self._durability_dirty = False
                return
            self._generation = uuid.uuid4().hex
            self._snapshot_pending_count = len(entries)
            self._journal_completion_count = 0
            self._journal_compacted = False
            self._snapshot_persisted = self._write_snapshot_locked(generation=self._generation, journal_compacted=False)
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

            compaction_threshold = max(self._MIN_COMPACTION_COMPLETIONS, (self._snapshot_pending_count + 1) // 2)
            if not self._journal_compacted and self._journal_completion_count >= compaction_threshold:
                self._compact_locked(journal_compacted=True)

    def pending_count(self) -> int:
        with self.lock:
            return len(self._pending_by_path)

    def _append_completion_locked(self, completed_path: str) -> bool:
        if not self._snapshot_persisted:
            return False
        journal_path = _memory_guard_resume_journal_path(self.path)
        record = json.dumps({"generation": self._generation, "path": completed_path}, separators=(",", ":"))
        try:
            os.makedirs(os.path.dirname(journal_path) or ".", exist_ok=True)
            with open(journal_path, "a", encoding="utf-8", newline="") as fh:
                fh.write(record + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            return True
        except OSError as exc:
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
        directory = os.path.dirname(self.path) or "."
        tmp_path = None
        try:
            os.makedirs(directory, exist_ok=True)
            tmp_fd, tmp_path = tempfile.mkstemp(
                prefix=os.path.basename(self.path) + ".", suffix=".tmp", dir=directory, text=True
            )
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh)
                fh.flush()
                os.fsync(fh.fileno())
            _replace_retrying(tmp_path, self.path)
            return True
        except OSError as exc:
            logging.warning(f"[MemoryGuard] Failed to persist resume queue (continuing): {exc}")
            return False
        finally:
            if tmp_path is not None:
                with suppress(OSError):  # a Windows scanner may still hold it; the next snapshot uses a new name
                    os.remove(tmp_path)

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
            Path(_memory_guard_resume_journal_path(self.path)).unlink(missing_ok=True)
        except OSError as exc:
            logging.warning(f"[MemoryGuard] Failed to remove resume completion journal: {exc}")

    def _remove_state_locked(self) -> None:
        try:
            Path(self.path).unlink(missing_ok=True)
        except OSError as exc:
            logging.warning(f"[MemoryGuard] Failed to remove resume queue: {exc}")
            return
        self._remove_journal_locked()
        self._snapshot_persisted = False

    def finalize(self, preserve_pending):
        """Finalize tracker, optionally preserving pending queue."""
        with self.lock:
            if preserve_pending and self._pending_by_path:
                if self._durability_dirty:
                    self._compact_locked(journal_compacted=True)
            else:
                self._clear_locked()


def restart_process_for_memory_guard():
    """Relaunch this run (same entry point and arguments) to release memory, then exit."""
    message = "[MemoryGuard] Restarting optimizer to release memory and resume pending songs."
    print(message)
    logging.warning(message)
    sys.stdout.flush()
    python = sys.executable or "python"
    if getattr(sys, "frozen", False):
        cmd = [python, *sys.argv[1:]]  # PyInstaller: sys.executable is the app and sys.argv[0] its path
    elif sys.argv and sys.argv[0] and os.path.exists(sys.argv[0]):
        cmd = [python, *sys.argv]
    else:
        cmd = [python, str(ENGINE_ROOT / "main.py"), *sys.argv[1:]]
    try:
        subprocess.Popen(cmd, cwd=str(ENGINE_ROOT))
    except OSError as exc:
        fail_msg = f"[MemoryGuard] Failed to relaunch automatically: {exc}"
        print(fail_msg)
        logging.error(fail_msg)
        sys.exit(1)
    sys.exit(0)
