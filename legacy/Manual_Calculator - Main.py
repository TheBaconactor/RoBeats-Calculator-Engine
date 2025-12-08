#                       !/usr/bin/env python3
"""
Manual Calculator + Iteration Engine + Co-Evolution Finder
(Unified Genome: Optimizes Gear AND Minis simultaneously for perfect synergy)
WITH PERMANENT EVOLUTION DATABASE
"""

import concurrent.futures
from concurrent.futures.process import BrokenProcessPool
import configparser
import contextlib
import csv
import gc
import hashlib
import json
import logging
import os
import random
import re
import sqlite3
import subprocess
import sys
import threading
import time
import traceback
import multiprocessing
from io import StringIO
import numpy as np
from math import floor, ceil
from dataclasses import dataclass
from cachetools import LRUCache

try:
    import psutil
except ImportError:
    psutil = None

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(_path=None):
        return False

try:
    import requests
except ImportError:
    requests = None

# Force single-core execution for any threaded numerical backends
for _env in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_env, "1")


def cfg_to_dict(cfg):
    """Serialize ConfigParser to a plain dict for safe process transport."""
    return {section: dict(cfg.items(section)) for section in cfg.sections()}


def cfg_from_dict(cfg_dict):
    """Rehydrate ConfigParser from a plain dict copy."""
    cfg = configparser.ConfigParser()
    for section, items in cfg_dict.items():
        if not cfg.has_section(section):
            cfg.add_section(section)
        for k, v in items.items():
            cfg.set(section, k, v)
    return cfg


class Tee:
    """Writes to multiple targets (e.g., stdout + buffer) for live logging."""

    def __init__(self, *targets):
        self.targets = targets

    def write(self, data):
        for t in self.targets:
            t.write(data)
        return len(data)

    def flush(self):
        for t in self.targets:
            t.flush()

# --- OPTIONAL JIT ACCELERATION ---
try:
    from numba import jit as numba_jit
    HAS_NUMBA = True

    def jit(nopython=True, cache=True):
        # Disable numba disk cache to avoid filesystem churn and potential lock issues.
        return numba_jit(nopython=nopython, cache=False)
except ImportError:
    HAS_NUMBA = False

    def jit(nopython=True, cache=True):
        def decorator(func):
            return func
        return decorator


# --- CONFIGURABLE CONSTANTS ---
GEM_SCALE_NORMAL = 2
GEM_SCALE_FEVER  = 3
ELEMENTAL_GEM_SCALE = 6
GEM_STAT_TO_ELEMENT_SCALE = 3

MAX_STAT_INDEX = 160
TOTAL_GEM_BUDGET = 90
TOTAL_ROWS = 160

# --- GA CONSTANTS (Will be overwritten by Config) ---
GA_POPULATION_SIZE = 250
GA_GENERATIONS = 75
GA_MUTATION_RATE = 0.275
GA_ELITISM = 1
GA_MULTI_RUNS_DEFAULT = 3  # Multi-start passes to escape local maxima
GA_MUTATION_RATE_MAX = 0.45  # Cap for adaptive mutation bumps

# --- DATABASE FILE ---
DB_FILE = "evolution.db"
# Hard cap per song to keep the DB size manageable
LOADOUTS_PER_SONG_LIMIT = 50


@dataclass(frozen=True)
class PathConfig:
    script_dir: str
    bin_dir: str
    status_file: str

    @classmethod
    def build(cls):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        bin_dir = os.path.join(script_dir, "bin")

        # BUG FIX: Make status file path configurable for server deployment
        # Priority: 1) Environment variable 2) config.ini 3) Hardcoded fallback
        status_file = None

        # Try environment variable first (best for server deployment)
        if "METAFINDER_STATUS_FILE" in os.environ:
            status_file = os.environ["METAFINDER_STATUS_FILE"]
        else:
            # Try config.ini
            try:
                cfg = configparser.ConfigParser()
                cfg.read(os.path.join(script_dir, "config.ini"), encoding="utf-8-sig")
                if cfg.has_option("IterationEngine", "StatusFilePath"):
                    status_file = cfg.get("IterationEngine", "StatusFilePath")
            except Exception:
                pass

        # Fallback to original hardcoded path for local development
        if not status_file:
            status_file = os.path.join(
                os.path.dirname(script_dir),
                "RoBeatMetaWebsite",
                "RoBeatsMeta",
                "web",
                "dist",
                "data",
                "metafinder_status.json",
            )

        return cls(script_dir, bin_dir, status_file)

    def bin_path(self, *parts):
        return os.path.join(self.bin_dir, *parts)

    @property
    def discord_env(self):
        return os.path.join(self.script_dir, "Discord.env")

    @property
    def stats_csv(self):
        return os.path.join(self.script_dir, "Stats.csv")

    @property
    def data_dir(self):
        return os.path.join(self.script_dir, "Data")

    @property
    def evolution_db_default(self):
        return os.path.join(self.script_dir, DB_FILE)


PATHS = PathConfig.build()
SCRIPT_DIR = PATHS.script_dir
BIN_DIR = PATHS.bin_dir

# --- Global LRU caches (not per-song limits) ---
# Memory leak fix: Use LRU with global limits instead of unbounded dicts
MAX_TIMELINE_CACHE_GLOBAL = 10000  # ~10MB max (was 500K per song)
MAX_GEM_SOLVER_CACHE = 5000        # ~10MB max
MAX_FG_CACHE = 2000                # ~6MB max

FEVER_TIMELINE_CACHE = LRUCache(maxsize=MAX_TIMELINE_CACHE_GLOBAL)
GEM_SOLVER_CACHE = LRUCache(maxsize=MAX_GEM_SOLVER_CACHE)
FG_CACHE = LRUCache(maxsize=MAX_FG_CACHE)

# Song counter for deterministic GC scheduling (fixes non-deterministic random GC)
_SONG_GC_COUNTER = 0

# --- Warning helpers ---
class WarnOnce:
    """Simple helper to emit a warning message only once per key."""

    def __init__(self):
        self._issued = set()

    def warn(self, key, message):
        if key in self._issued:
            return
        self._issued.add(key)
        try:
            logging.warning(message)
        except Exception:
            pass
        try:
            print(message)
        except Exception:
            pass


WARN_ONCE = WarnOnce()

# Keys to skip when aggregating gear/mini stats (metadata, not actual stats).
SKIP_ITEM_KEYS = frozenset({"Name", "type"})

# Soft RSS ceiling defaults to half of physical RAM when auto-detected.
DEFAULT_MEMORY_GUARD_PERCENT = 50.0
STRICT_PLATFORM_MEMORY_GUARD_PERCENT = 35.0
MEMORY_WATCHDOG_INTERVAL_SEC = 5
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
    return value / (1024 ** 3)


def memory_release_requested():
    return MEMORY_WATCHDOG_EVENT.is_set()


def get_memory_release_message():
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
        pass


def trigger_memory_release(reason):
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
            pass
    MEMORY_WATCHDOG_EVENT.set()


def _process_tree_rss_bytes(root_process, include_compressed=False):
    """Return RSS (optionally + compressed) for the root process plus all children."""

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
        pass
    return total


def _memory_watchdog_loop():
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
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self.pending = []
        self.context = {}

    def prime(self, queue, context):
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
        with self.lock:
            if preserve_pending and self.pending:
                self._write_locked()
            else:
                self.pending = []
                self.context = {}
                self._write_locked()


def restart_process_for_memory_guard():
    python = sys.executable or "python"
    script = os.path.abspath(__file__)
    message = "[MemoryGuard] Restarting optimizer to release memory and resume pending songs."
    print(message)
    try:
        logging.warning(message)
    except Exception:
        pass
    sys.stdout.flush()
    try:
        subprocess.Popen([python, script] + sys.argv[1:])
    except Exception as exc:
        fail_msg = f"[MemoryGuard] Failed to relaunch automatically: {exc}"
        print(fail_msg)
        logging.error(fail_msg)
        sys.exit(1)
    else:
        sys.exit(0)

def stats_signature(stats, calc_song, selected_color):
    """
    Compute a cache key that captures exactly the inputs influencing the gem
    solver for a given song context. Two loadouts with the same signature will
    produce identical gem allocations and scores.
    
    Key insight: elemental stats only matter if they feed into the song's
    Primary/Secondary/Selected Element paths. Differences in other elements
    are irrelevant and should share the same cache entry.
    """
    meta = calc_song["metadata"]
    p_color = meta.get("Primary Color", "")
    s_color = meta.get("Secondary Color", "")

    gs = stats.get

    # Mirror the same Beat/Vibe mapping the solver uses.
    base_beat = gs("Beat", 0)
    base_vibe = gs("Vibe", 0)

    def get_val_inline(k):
        if k == "Beat":
            return base_beat
        if k == "Vibe":
            return base_vibe
        return gs(k, 0)

    # Only capture elemental values that actually feed into P/S lanes.
    base_p_val = get_val_inline(p_color)
    base_s_val = get_val_inline(s_color)

    return (
        meta.get("Song Name", ""),
        meta.get("Difficulty", ""),
        selected_color,
        p_color,
        s_color,
        gs("Perfect Points", 0),
        gs("Combo Multiplier", 0),
        gs("Fever Multiplier", 0),
        gs("Fever Fill Rate", 0),
        gs("Fever Time", 0),
        base_p_val,
        base_s_val,
    )


# --- Gear Dominance Pruning ---
# DOMINANCE_KEYS is aliased to STAT_KEYS (defined below) since they are identical.

def is_dominated_by(a, b):
    """
    Check if gear 'a' is strictly dominated by gear 'b'.
    
    Returns True if:
      - b[stat] >= a[stat] for ALL stats in DOMINANCE_KEYS, AND
      - b[stat] > a[stat] for AT LEAST ONE stat
    
    This means 'a' can never be optimal if 'b' is available.
    """
    dominated = all(b.get(k, 0) >= a.get(k, 0) for k in DOMINANCE_KEYS)
    if not dominated:
        return False
    strictly_better = any(b.get(k, 0) > a.get(k, 0) for k in DOMINANCE_KEYS)
    return strictly_better


def prune_dominated_gear(gear_list):
    """
    Remove gear items that are strictly dominated by another gear in the list.
    
    For each gear, check if any other gear in the list dominates it.
    Only keep gear that is NOT dominated by any other.
    
    Returns a new list with dominated gear removed.
    """
    if len(gear_list) <= 1:
        return gear_list
    
    pruned = []
    for g in gear_list:
        dominated = False
        for other in gear_list:
            if other is g:
                continue
            if is_dominated_by(g, other):
                dominated = True
                break
        if not dominated:
            pruned.append(g)
    return pruned


# --- STAT KEYS / HELPERS ---
STAT_KEYS = [
    "Perfect Points",
    "Combo Multiplier",
    "Fever Multiplier",
    "Fever Fill Rate",
    "Fever Time",
    "Chill",
    "Flow",
    "Rush",
    "Beat",
    "Vibe",
]

# Alias for gear dominance pruning (same keys used for dominance comparison).
DOMINANCE_KEYS = STAT_KEYS


def empty_stats():
    """Return a fresh stats dict with all relevant keys initialized to 0."""
    return {k: 0 for k in STAT_KEYS}


# --- Helper Conversion Functions ---
def safe_int(val, default=0):
    try:
        if val is None:
            return default
        s = str(val).strip()
        if not s:
            return default
        # Prefer direct int parsing to avoid float precision loss on large IDs.
        try:
            return int(s, 10)
        except ValueError:
            return int(float(s))
    except Exception:
        return default


def safe_float(val, default=0.0):
    try:
        if not val or val == "-":
            return default
        return float(val)
    except Exception:
        return default


def compute_memory_guard_limit(cfg):
    """
    Compute the RSS ceiling in bytes.

    - MemorySoftLimitGB enforces an absolute cap when > 0.
    - MemorySoftLimitPercent (default DEFAULT_MEMORY_GUARD_PERCENT) reserves a
      percentage of detected physical RAM. Set to 0 or negative to disable.
    - When both are provided we respect the stricter (smaller) ceiling.
    """
    platform_default_percent = STRICT_PLATFORM_MEMORY_GUARD_PERCENT if sys.platform in ("win32", "cygwin", "darwin") else DEFAULT_MEMORY_GUARD_PERCENT
    limit_gb = safe_float(
        cfg.get("IterationEngine", "MemorySoftLimitGB", fallback=0.0), default=0.0
    )
    limit_percent = safe_float(
        cfg.get(
            "IterationEngine",
            "MemorySoftLimitPercent",
            fallback=platform_default_percent,
        ),
        default=platform_default_percent,
    )

    # Clamp percent to the stricter platform default to avoid overly loose limits on Windows/macOS.
    effective_percent = min(limit_percent, platform_default_percent) if limit_percent > 0 else 0.0

    candidates = []
    if limit_gb > 0:
        candidates.append(limit_gb * (1024 ** 3))
    if effective_percent > 0:
        total_ram = detect_total_physical_memory()
        if total_ram > 0:
            candidates.append(total_ram * (effective_percent / 100.0))
        else:
            logging.warning(
                "[MemoryGuard] Physical RAM auto-detect failed; percent limit ignored."
            )

    if not candidates:
        return 0
    return int(min(candidates))


# --- Setup Directories and Logging ---
os.makedirs(BIN_DIR, exist_ok=True)
log_file_path = os.path.join(BIN_DIR, "error.log")
logging.basicConfig(
    filename=log_file_path,
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s: %(message)s"
)

###########################################################################
# Web Status Integration (RoBeatsMeta)
#
# Writes a local JSON file that the website on this Mac can read
# to show "Server 1 (MetaFinder)" status.
#
# The website reads:
#   web/public/data/metafinder_status.json
###########################################################################

STATUS_FILE = PATHS.status_file


def write_metafinder_status(status, message=None):
    """
    Export a lightweight status JSON for the RoBeatsMeta website.

    The website reads this from:
      web/public/data/metafinder_status.json
    and uses the timestamp to determine if MetaFinder is considered online.
    """
    payload = {
        "source": "MetaFinder",
        "status": str(status),
        "message": (message or "")[:500],
        "timestamp": time.time(),
    }
    try:
        status_dir = os.path.dirname(STATUS_FILE)
        os.makedirs(status_dir, exist_ok=True)
        tmp_path = STATUS_FILE + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        os.replace(tmp_path, STATUS_FILE)
    except Exception as e:
        # BUG FIX: Always print status file errors to console so they're visible
        error_msg = f"Failed to write MetaFinder status file to {STATUS_FILE}: {e}"
        print(f"[WARNING] {error_msg}")
        try:
            logging.warning(error_msg)
        except Exception:
            # Avoid crashing the optimizer if logging fails.
            pass

# --- Environment (Discord + external paths) ---
ENV_PATH = PATHS.discord_env
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
else:
    load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
LOGGING_CHANNEL_ID = safe_int(os.getenv("LOGGINGCHANNEL"), 0) or None
STATS_CHANNEL_ID = safe_int(os.getenv("STATSCHANNEL"), 0) or None
EVOLUTION_DB_PATH = os.getenv("EVOLUTION_DB_PATH") or PATHS.evolution_db_default


class DiscordReporter:
    """Minimal helper to push log and stat updates to Discord."""

    def __init__(self, token, log_channel_id=None, stats_channel_id=None):
        self.token = token
        self.log_channel_id = log_channel_id
        self.stats_channel_id = stats_channel_id

    def _post(self, channel_id, content):
        if not self.token or not channel_id or not content or requests is None:
            return

        chunks = [content[i:i + 1800] for i in range(0, len(content), 1800)] or [content]
        headers = {
            "Authorization": f"Bot {self.token}",
            "Content-Type": "application/json",
        }

        for chunk in chunks:
            payload = {"content": chunk}
            attempts = 0
            while attempts < 3:
                attempts += 1
                try:
                    resp = requests.post(
                        f"https://discord.com/api/v10/channels/{channel_id}/messages",
                        headers=headers,
                        json=payload,
                        timeout=10,
                    )
                    if resp.status_code == 429:
                        try:
                            retry_after = float(resp.json().get("retry_after", 1))
                        except Exception:
                            retry_after = 1.0
                        time.sleep(max(retry_after, 0.5))
                        continue
                    if resp.status_code >= 300:
                        print(
                            f"[DiscordReporter] Failed to send to {channel_id}: "
                            f"{resp.status_code} {resp.text}"
                        )
                    break
                except Exception as e:
                    print(f"[DiscordReporter] Error sending Discord message: {e}")
                    break

    def send_log(self, content):
        self._post(self.log_channel_id, sanitize_public_message(content))

    def send_stats(self, content):
        self._post(self.stats_channel_id, content)


discord_reporter = DiscordReporter(DISCORD_TOKEN, LOGGING_CHANNEL_ID, STATS_CHANNEL_ID)


def build_stats_summary(res, completed, total):
    """Create a compact Discord-friendly summary for a completed song run."""
    payload = res.get("db_payload") or {}
    details = payload.get("details") or {}

    score = payload.get("score")
    score_txt = "N/A" if score is None else f"{int(score):,}" if isinstance(score, (int, float)) else str(score)
    gear_names = payload.get("gear") or []
    mini_names = payload.get("minis") or []
    element = details.get("SelectedElement") or details.get("Selected Element", "")
    ft = details.get("FT")
    ff = details.get("FF")

    lines = [f"[{completed}/{total}] {res.get('song', 'Unknown Song')}"]
    lines.append(f"Score: {score_txt}")
    attempts_best = payload.get("attempts_first")
    attempt_lifetime = payload.get("attempt_lifetime")
    attempt_parts = []
    if attempts_best is not None:
        attempt_parts.append(f"Best: {attempts_best}")
    if attempt_lifetime is not None:
        attempt_parts.append(f"Lifetime: {attempt_lifetime}")
    if attempt_parts:
        lines.append(f"Attempts: {' | '.join(attempt_parts)}")
    if element:
        lines.append(f"Element: {element}")
    if ft is not None or ff is not None:
        lines.append(f"FT: {ft if ft is not None else 'N/A'} | FF: {ff if ff is not None else 'N/A'}")
    lines.append(f"Gear: {', '.join(gear_names) if gear_names else 'N/A'}")
    lines.append(f"Minis: {', '.join(mini_names) if mini_names else 'N/A'}")
    return "\n".join(lines)


# --- DATABASE FUNCTIONS ---
def get_evolution_db_path():
    """Return the configured evolution DB location (env override supported)."""
    return EVOLUTION_DB_PATH if EVOLUTION_DB_PATH else os.path.join(SCRIPT_DIR, DB_FILE)

def get_db_connection(db_path=None):
    if db_path is None:
        db_path = get_evolution_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    """
    Initialize the SQLite database schema if it doesn't exist.
    
    Storage optimization: gear_json and minis_json store only names (not full stats)
    as a JSON array of strings, e.g. ["Gear1", "Gear2", ...]. Full stats are looked
    up from Gears.csv/Minis.csv when loading. This reduces storage by ~90%.
    """
    db_path = get_evolution_db_path()
    conn = get_db_connection(db_path)
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS songs (
                name TEXT PRIMARY KEY,
                best_score INTEGER DEFAULT 0,
                best_fg_score INTEGER DEFAULT 0,
                last_updated REAL
            );
            CREATE TABLE IF NOT EXISTS loadouts (
                song_name TEXT,
                loadout_hash TEXT,
                score INTEGER,
                fg_score INTEGER DEFAULT 0,
                gear_json TEXT,
                minis_json TEXT,
                details_json TEXT,
                force_details_json TEXT,
                timestamp REAL,
                PRIMARY KEY (song_name, loadout_hash),
                FOREIGN KEY (song_name) REFERENCES songs(name)
            );
            CREATE INDEX IF NOT EXISTS idx_loadouts_score ON loadouts (song_name, score DESC);
        """)
        conn.commit()
    finally:
        conn.close()


def _compact_gear_for_db(gear_list):
    """Convert gear list to compact storage format (names only). Handles both dicts and strings."""
    if not gear_list:
        return []
    result = []
    for g in gear_list:
        if isinstance(g, dict):
            name = g.get("Name", "")
        else:
            name = str(g) if g else ""
        if name:
            result.append(name)
    return result


def _compact_minis_for_db(mini_list):
    """Convert mini list to compact storage format (names only). Handles both dicts and strings."""
    if not mini_list:
        return []
    result = []
    for m in mini_list:
        if isinstance(m, dict):
            name = m.get("Name", "")
        else:
            name = str(m) if m else ""
        if name:
            result.append(name)
    return result


def _expand_gear_from_db(gear_names, gears_by_name):
    """Expand gear names back to full stat dictionaries."""
    if not gear_names or not gears_by_name:
        return []
    return [gears_by_name.get(name, {"Name": name}) for name in gear_names]


def _expand_minis_from_db(mini_names, minis_by_name):
    """Expand mini names back to full stat dictionaries."""
    if not mini_names or not minis_by_name:
        return []
    return [minis_by_name.get(name, {"Name": name}) for name in mini_names]

def get_loadout_hash(gear_list, mini_list):
    """
    Generate a unique hash for a loadout (gear + minis).
    Sorts items by name to ensure consistent hashing regardless of order.
    Handles both dicts (with 'Name' key) and plain strings.
    """
    # Extract names, handling both dict and string inputs
    gear_names = []
    for g in (gear_list or []):
        if isinstance(g, dict):
            gear_names.append(g.get("Name", ""))
        else:
            gear_names.append(str(g) if g else "")
    gear_names = sorted([n for n in gear_names if n])
    
    mini_names = []
    for m in (mini_list or []):
        if isinstance(m, dict):
            mini_names.append(m.get("Name", ""))
        else:
            mini_names.append(str(m) if m else "")
    mini_names = sorted([n for n in mini_names if n])
    
    # Create a string representation
    payload = f"GEAR:{'|'.join(gear_names)}::MINIS:{'|'.join(mini_names)}"
    return hashlib.md5(payload.encode("utf-8")).hexdigest()

def save_loadout_to_db(song_name, score, fg_score, gear, minis, details, force_data=None):
    """
    Save a loadout to the database.
    Enforces the per-song loadout limit.
    
    Storage is optimized: only gear/mini names are stored, not full stats.
    """
    db_path = get_evolution_db_path()
    conn = get_db_connection(db_path)
    try:
        loadout_hash = get_loadout_hash(gear, minis)
        
        # Compact storage: store only names, not full stat dictionaries
        gear_names = _compact_gear_for_db(gear)
        mini_names = _compact_minis_for_db(minis)
        
        # Upsert the loadout
        conn.execute("""
            INSERT INTO loadouts (song_name, loadout_hash, score, fg_score, gear_json, minis_json, details_json, force_details_json, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, strftime('%s', 'now'))
            ON CONFLICT(song_name, loadout_hash) DO UPDATE SET
                score = excluded.score,
                fg_score = excluded.fg_score,
                gear_json = excluded.gear_json,
                minis_json = excluded.minis_json,
                details_json = excluded.details_json,
                force_details_json = excluded.force_details_json,
                timestamp = strftime('%s', 'now')
        """, (
            song_name,
            loadout_hash,
            score,
            fg_score,
            json.dumps(gear_names, separators=(',', ':')),
            json.dumps(mini_names, separators=(',', ':')),
            json.dumps(details, separators=(',', ':')) if details else None,
            json.dumps(force_data, separators=(',', ':')) if force_data else None,
        ))
        
        # Update the song's best score if this is better
        conn.execute("""
            INSERT INTO songs (name, best_score)
            VALUES (?, ?)
            ON CONFLICT(name) DO UPDATE SET
                best_score = MAX(best_score, excluded.best_score),
                last_updated = strftime('%s', 'now')
        """, (song_name, score))

        # Update best FG score if provided
        try:
            fg_val = int(fg_score) if fg_score is not None else 0
        except Exception:
            fg_val = 0
        if fg_val:
            conn.execute("""
                INSERT INTO songs (name, best_fg_score)
                VALUES (?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    best_fg_score = MAX(best_fg_score, excluded.best_fg_score),
                    last_updated = strftime('%s', 'now')
            """, (song_name, fg_val))
        
        # Enforce limit: Keep top N by score and preserve best FG entry
        # We only need to check this occasionally or if we suspect we are over.
        # Doing it on every insert might be expensive.
        # Let's do a quick check of count.
        cursor = conn.execute("SELECT COUNT(*) FROM loadouts WHERE song_name = ?", (song_name,))
        count = cursor.fetchone()[0]
        
        if count > LOADOUTS_PER_SONG_LIMIT:
            # Delete the worst ones, keeping top limit by score AND always keep the best FG entry (if any).
            conn.execute("""
                DELETE FROM loadouts
                WHERE song_name = ?
                AND loadout_hash NOT IN (
                    -- keep top N by score
                    SELECT loadout_hash FROM loadouts
                    WHERE song_name = ?
                    ORDER BY score DESC
                    LIMIT ?
                )
                AND loadout_hash NOT IN (
                    -- keep best FG entry if it exists
                    SELECT loadout_hash FROM loadouts
                    WHERE song_name = ?
                    ORDER BY fg_score DESC
                    LIMIT 1
                )
            """, (song_name, song_name, LOADOUTS_PER_SONG_LIMIT, song_name))
            
        conn.commit()
    except Exception as e:
        print(f"[DB] Error saving loadout: {e}")
    finally:
        conn.close()

def save_loadouts_batch(song_name, entries):
    """
    Batch insert/update loadouts for a song in a single transaction.
    entries: list of dicts with keys: score, fg_score, gear, minis, details, force
    """
    if not entries:
        return
    db_path = get_evolution_db_path()
    conn = get_db_connection(db_path)
    best_score_max = None
    best_fg_max = None
    try:
        # Relax sync during batch for throughput; WAL is already enabled in get_db_connection.
        try:
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass

        for entry in entries:
            score = entry.get("score", 0)
            fg_score = entry.get("fg_score", 0)
            gear = entry.get("gear", [])
            minis = entry.get("minis", [])
            details = entry.get("details", {})
            force_data = entry.get("force")

            loadout_hash = get_loadout_hash(gear, minis)
            gear_names = _compact_gear_for_db(gear)
            mini_names = _compact_minis_for_db(minis)

            conn.execute("""
                INSERT INTO loadouts (song_name, loadout_hash, score, fg_score, gear_json, minis_json, details_json, force_details_json, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, strftime('%s', 'now'))
                ON CONFLICT(song_name, loadout_hash) DO UPDATE SET
                    score = excluded.score,
                    fg_score = excluded.fg_score,
                    gear_json = excluded.gear_json,
                    minis_json = excluded.minis_json,
                    details_json = excluded.details_json,
                    force_details_json = excluded.force_details_json,
                    timestamp = strftime('%s', 'now')
            """, (
                song_name,
                loadout_hash,
                score,
                fg_score,
                json.dumps(gear_names, separators=(',', ':')),
                json.dumps(mini_names, separators=(',', ':')),
                json.dumps(details, separators=(',', ':')) if details else None,
                json.dumps(force_data, separators=(',', ':')) if force_data else None,
            ))

            if best_score_max is None or score > best_score_max:
                best_score_max = score
            if fg_score and (best_fg_max is None or fg_score > best_fg_max):
                best_fg_max = fg_score

        if best_score_max is not None:
            conn.execute("""
                INSERT INTO songs (name, best_score)
                VALUES (?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    best_score = MAX(best_score, excluded.best_score),
                    last_updated = strftime('%s', 'now')
            """, (song_name, best_score_max))

        if best_fg_max:
            conn.execute("""
                INSERT INTO songs (name, best_fg_score)
                VALUES (?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    best_fg_score = MAX(best_fg_score, excluded.best_fg_score),
                    last_updated = strftime('%s', 'now')
            """, (song_name, best_fg_max))

        cursor = conn.execute("SELECT COUNT(*) FROM loadouts WHERE song_name = ?", (song_name,))
        count = cursor.fetchone()[0]
        if count > LOADOUTS_PER_SONG_LIMIT:
            conn.execute("""
                DELETE FROM loadouts
                WHERE song_name = ?
                AND loadout_hash NOT IN (
                    SELECT loadout_hash FROM loadouts
                    WHERE song_name = ?
                    ORDER BY score DESC
                    LIMIT ?
                )
                AND loadout_hash NOT IN (
                    SELECT loadout_hash FROM loadouts
                    WHERE song_name = ?
                    ORDER BY fg_score DESC
                    LIMIT 1
                )
            """, (song_name, song_name, LOADOUTS_PER_SONG_LIMIT, song_name))

        conn.commit()
    except Exception as e:
        print(f"[DB] Error saving batch loadouts: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        try:
            conn.execute("PRAGMA synchronous=FULL;")
        except Exception:
            pass
        conn.close()

def get_best_loadouts(song_name, limit=LOADOUTS_PER_SONG_LIMIT, gears_by_name=None, minis_by_name=None):
    """
    Retrieve the top N loadouts for a song to seed the GA.
    
    Storage format: gear_json and minis_json are JSON arrays of name strings.
    If gears_by_name/minis_by_name are provided, expands names to full stat dicts.
    """
    db_path = get_evolution_db_path()
    if not os.path.exists(db_path):
        return []
        
    conn = get_db_connection(db_path)
    try:
        cursor = conn.execute("""
            SELECT score, fg_score, gear_json, minis_json, details_json, force_details_json
            FROM loadouts
            WHERE song_name = ?
            ORDER BY score DESC
            LIMIT ?
        """, (song_name, limit))
        
        results = []
        for row in cursor:
            gear_names = json.loads(row["gear_json"]) if row["gear_json"] else []
            mini_names = json.loads(row["minis_json"]) if row["minis_json"] else []
            force_block = json.loads(row["force_details_json"]) if row["force_details_json"] else None
            
            # Expand names to full dicts if lookup provided
            if gears_by_name:
                gear_data = _expand_gear_from_db(gear_names, gears_by_name)
            else:
                gear_data = gear_names  # Return as names for hash lookups
            
            if minis_by_name:
                minis_data = _expand_minis_from_db(mini_names, minis_by_name)
            else:
                minis_data = mini_names
            
            results.append({
                "score": row["score"],
                "fg_score": row["fg_score"],
                "gear": gear_data,
                "minis": minis_data,
                "details": json.loads(row["details_json"]) if row["details_json"] else {},
                "force": force_block if isinstance(force_block, dict) else None,
            })
        return results
    except Exception as e:
        print(f"[DB] Error retrieving loadouts: {e}")
        return []
    finally:
        conn.close()


def sanitize_public_message(content):
    """Strip local filesystem details from messages before posting externally."""
    try:
        text = str(content) if content is not None else ""
    except Exception:
        text = ""
    if not text:
        return ""

    sensitive_paths = set()
    for path_candidate in (
        SCRIPT_DIR,
        BIN_DIR,
        os.getcwd(),
        os.path.expanduser("~"),
        get_evolution_db_path(),
    ):
        if path_candidate:
            normalized = os.path.normcase(os.path.normpath(path_candidate))
            sensitive_paths.add(normalized)

    sanitized = text
    for marker in sensitive_paths:
        variants = {
            marker,
            marker.replace("\\", "/"),
            marker.replace("\\", "\\\\"),
            marker.replace("/", "\\"),
        }
        for variant in variants:
            sanitized = sanitized.replace(variant, "<redacted>")
    return sanitized


# --- Load Cached Paths ---
def load_paths_cache():
    pc = os.path.join(SCRIPT_DIR, "bin", "paths_cache.json")
    if os.path.exists(pc):
        with open(pc, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# --- Read Stats Table ---
def read_table(fp):
    if not fp or not os.path.exists(fp):
        return []
    try:
        # Explicit UTF-8-SIG to match other data files and avoid Windows 'charmap' decode issues
        with open(fp, "r", encoding="utf-8-sig") as f:
            lines = f.read().splitlines()
        if not lines:
            return []
        table = []
        for line in lines[1:]:
            parts = line.split()
            if parts:
                try:
                    row = [float(x) for x in parts]
                    table.append(row)
                except Exception as exc:
                    WARN_ONCE.warn(
                        "stats-table-row",
                        f"Malformed stats row in {fp}: {parts!r} ({exc})",
                    )
        return table
    except Exception as exc:
        WARN_ONCE.warn(
            "stats-table-file",
            f"Failed to read stats table {fp}: {exc}",
        )
        return []


def resolve_stats_csv(paths, filename):
    """Resolve Gears/Minis CSV relative to SCRIPT_DIR or Stats.csv folder."""
    csv_path = os.path.join(SCRIPT_DIR, filename)
    if not os.path.exists(csv_path):
        stats_loc = paths.get("Stats", "")
        if stats_loc:
            csv_path = os.path.join(os.path.dirname(stats_loc), filename)
    return csv_path


# --- CSV Parsing Helpers (shared) ---
def _build_row_map(row, header_lower):
    """Build a mapping from header keys to row values for CSV parsing."""
    mapped = {}
    for idx, col in enumerate(header_lower):
        key = col or f"col_{idx}"
        mapped.setdefault(key, []).append(row[idx].strip() if idx < len(row) else "")
    return mapped


def _first_val(row_map, keys):
    """Return the first non-empty value from row_map matching any of the keys."""
    for key in keys:
        for val in row_map.get(key, []):
            v = str(val).strip() if val is not None else ""
            if v:
                return v
    return ""


def parse_gear_rows(filepath):
    """Parse Gears.csv into a list of gear dicts."""
    gear_list = []
    if not os.path.exists(filepath):
        return gear_list
    try:
        with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))

        if not rows:
            return gear_list

        header = [h.strip() for h in rows[0]]
        header_lower = [h.lower() for h in header]

        modern_format = "type" in header_lower and any(
            name in header_lower for name in ("gear name", "name", "gear")
        )

        if modern_format:
            for row in rows[1:]:
                if not any((c or "").strip() for c in row):
                    continue
                row_map = _build_row_map(row, header_lower)
                name = _first_val(row_map, ("gear name", "name", "gear"))
                if not name:
                    continue
                slot = _first_val(row_map, ("type", "slot", "category")) or "Hat"
                stats = {
                    "Name": name,
                    "type": slot,
                    "Chill": safe_int(_first_val(row_map, ("chill",))),
                    "Flow": safe_int(_first_val(row_map, ("flow",))),
                    "Rush": safe_int(_first_val(row_map, ("rush",))),
                    "Beat": safe_int(_first_val(row_map, ("beat",))),
                    "Vibe": safe_int(_first_val(row_map, ("vibe",))),
                    "Perfect Points": safe_int(
                        _first_val(row_map, ("ppoint", "perfect points", "pp", "ppoints"))
                    ),
                    "Combo Multiplier": safe_int(
                        _first_val(row_map, ("cmult", "cbmlt", "combo multiplier", "combo"))
                    ),
                    "Fever Multiplier": safe_int(
                        _first_val(row_map, ("fmult", "fmlt", "fever multiplier"))
                    ),
                }
                # IMPORTANT: Perfect Time (often stored as "PTime") is a
                # completely different mechanic from Fever Time and must
                # NEVER be treated as Fever Time. Do not fall back to
                # any "ptime" column here; only true Fever Time fields
                # ("time" / "fever time" / "ft") are allowed.
                time_val = _first_val(row_map, ("time", "fever time", "ft"))
                stats["Fever Time"] = safe_int(time_val)
                stats["Fever Fill Rate"] = safe_int(
                    _first_val(row_map, ("fill", "fvfil", "fever fill rate", "fever fill"))
                )
                gear_list.append(stats)
        else:
            current_category = "Hat"
            known_slots = ["Neck", "Face", "Shirt", "Back", "Pants"]
            for row in rows[1:]:
                if not row:
                    continue
                potential_cat = row[0].strip()
                if potential_cat in known_slots:
                    current_category = potential_cat
                    continue
                if len(row) < 11:
                    continue
                name = row[0].strip()
                if not name:
                    continue
                stats = {
                    "Name": name,
                    "type": current_category,
                    "Chill": safe_int(row[1]),
                    "Flow": safe_int(row[2]),
                    "Rush": safe_int(row[3]),
                    "Beat": safe_int(row[4]),
                    "Vibe": safe_int(row[5]),
                    "Perfect Points": safe_int(row[6]),
                    "Combo Multiplier": safe_int(row[7]),
                    "Fever Multiplier": safe_int(row[8]),
                    "Fever Time": safe_int(row[9]),
                    "Fever Fill Rate": safe_int(row[10]),
                }
                gear_list.append(stats)
    except Exception as exc:
        WARN_ONCE.warn("gear-csv", f"Failed to parse gear CSV {filepath}: {exc}")
    return gear_list


def parse_mini_rows(filepath):
    """Parse Minis.csv into a list of mini dicts."""
    minis_list = []
    if not os.path.exists(filepath):
        return minis_list
    try:
        with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))

        if not rows:
            return minis_list

        header = [h.strip() for h in rows[0]]
        header_lower = [h.lower() for h in header]

        modern_format = "type" in header_lower and any(
            name in header_lower for name in ("mini name", "name", "mini")
        )

        if modern_format:
            for row in rows[1:]:
                if not any((c or "").strip() for c in row):
                    continue
                row_map = _build_row_map(row, header_lower)
                name = _first_val(row_map, ("mini name", "name", "mini"))
                if not name or name == "(Empty)":
                    continue
                mini_type = _first_val(row_map, ("type",)) or "Mini"
                stats = {
                    "Name": name,
                    "type": mini_type,
                    "Chill": safe_int(_first_val(row_map, ("chill",))),
                    "Flow": safe_int(_first_val(row_map, ("flow",))),
                    "Rush": safe_int(_first_val(row_map, ("rush",))),
                    "Beat": safe_int(_first_val(row_map, ("beat",))),
                    "Vibe": safe_int(_first_val(row_map, ("vibe",))),
                    "Perfect Points": 0,
                    "Combo Multiplier": safe_int(
                        _first_val(row_map, ("cbmlt", "cmult", "combo multiplier", "combo"))
                    ),
                    "Fever Multiplier": safe_int(
                        _first_val(row_map, ("fmult", "fmlt", "fvmlt", "fever multiplier"))
                    ),
                    "Fever Time": safe_int(
                        _first_val(row_map, ("fvtim", "time", "ft", "fever time"))
                    ),
                    "Fever Fill Rate": safe_int(
                        _first_val(row_map, ("fvfil", "fill", "ff", "fever fill"))
                    ),
                }
                minis_list.append(stats)
        else:
            for row in rows[1:]:
                if len(row) < 12:
                    continue
                name = row[1].strip()
                if not name or name == "(Empty)":
                    continue
                stats = {
                    "Name": name,
                    "type": "Mini",
                    "Chill": safe_int(row[2]),
                    "Flow": safe_int(row[3]),
                    "Rush": safe_int(row[4]),
                    "Beat": safe_int(row[5]),
                    "Vibe": safe_int(row[6]),
                    "Perfect Points": 0,
                    "Combo Multiplier": safe_int(row[8]),
                    "Fever Multiplier": safe_int(row[9]),
                    "Fever Time": safe_int(row[10]),
                    "Fever Fill Rate": safe_int(row[11]),
                }
                minis_list.append(stats)
    except Exception as exc:
        WARN_ONCE.warn("mini-csv", f"Failed to parse minis CSV {filepath}: {exc}")
    return minis_list


# --- CSV Data Loading (now using shared parsers) ---
def load_csv_db(filepath, db_type="gear"):
    db = {}
    if not os.path.exists(filepath):
        return db
    try:
        if db_type == "gear":
            gears = parse_gear_rows(filepath)
            db = {g["Name"]: g for g in gears}
        elif db_type == "mini":
            minis = parse_mini_rows(filepath)
            db = {m["Name"]: m for m in minis}
    except Exception as exc:
        WARN_ONCE.warn(
            "csv-db",
            f"Failed to build {db_type} CSV db from {filepath}: {exc}",
        )
    return db


def load_all_minis_list(paths):
    return parse_mini_rows(resolve_stats_csv(paths, "Minis.csv"))


def load_all_gears_list(paths):
    return parse_gear_rows(resolve_stats_csv(paths, "Gears.csv"))


# --- Load Config and Calculate Stats ---
def get_fixed_stats(cfg):
    total_stats = empty_stats()

    gem_perfect = safe_int(cfg.get("UserInputStatsGems", "perfect_points", fallback=0))
    gem_combo = safe_int(cfg.get("UserInputStatsGems", "combo_multiplier", fallback=0))
    gem_f_mult = safe_int(cfg.get("UserInputStatsGems", "fever_multiplier", fallback=0))
    gem_f_fill = safe_int(cfg.get("UserInputStatsGems", "fever_fill", fallback=0))
    gem_f_time = safe_int(cfg.get("UserInputStatsGems", "fever_time", fallback=0))

    total_stats["Perfect Points"] += gem_perfect * GEM_SCALE_NORMAL
    total_stats["Combo Multiplier"] += gem_combo * GEM_SCALE_NORMAL
    total_stats["Fever Multiplier"] += gem_f_mult * GEM_SCALE_FEVER
    total_stats["Fever Fill Rate"] += gem_f_fill * GEM_SCALE_FEVER
    total_stats["Fever Time"] += gem_f_time * GEM_SCALE_FEVER

    total_stats["Chill"] += gem_perfect * GEM_STAT_TO_ELEMENT_SCALE
    total_stats["Flow"] += gem_combo * GEM_STAT_TO_ELEMENT_SCALE
    total_stats["Rush"] += gem_f_mult * GEM_STAT_TO_ELEMENT_SCALE
    total_stats["Beat"] += gem_f_time * GEM_STAT_TO_ELEMENT_SCALE
    total_stats["Vibe"] += gem_f_fill * GEM_STAT_TO_ELEMENT_SCALE

    elements = ["Chill", "Flow", "Rush", "Beat", "Vibe"]
    for el in elements:
        gem_val = safe_int(cfg.get("ElementalGems", el, fallback="0"))
        if gem_val > 0:
            total_stats[el] += gem_val * ELEMENTAL_GEM_SCALE

    team_buff = cfg.get("TeamContributionBuffConstant", "TeamBuff", fallback="").strip().upper()
    team_color = cfg.get("TeamContributionBuffConstant", "TeamColor", fallback="").strip()
    buff_tiers = {
        "T1": {"PP": 25, "Elem": 35},
        "T5": {"PP": 25, "Elem": 30},
        "T10": {"PP": 20, "Elem": 25},
        "T15": {"PP": 15, "Elem": 20},
    }
    if team_buff in buff_tiers:
        buff_data = buff_tiers[team_buff]
        total_stats["Perfect Points"] += buff_data["PP"]
        valid_color_key = next((k for k in elements if k.lower() == team_color.lower()), None)
        if valid_color_key:
            total_stats[valid_color_key] += buff_data["Elem"]
        elif team_color:
            total_stats["Perfect Points"] += buff_data["PP"]
    return total_stats


def get_config_gear_stats(cfg, paths, gears_db=None):
    """
    Returns (gear_stats_dict, gear_list) from config.
    gears_db: optional dict {Name: stats}. If None, load from CSV.
    """
    if gears_db is None:
        gears_db = load_csv_db(resolve_stats_csv(paths, "Gears.csv"), "gear")

    gear_stats = empty_stats()
    gear_list = []
    gear_slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    for slot in gear_slots:
        key = "Pant" if slot == "Pants" else slot
        item_name = cfg.get("Gear", key, fallback=cfg.get("Gear", slot, fallback="")).strip().strip(" .")
        if item_name in gears_db:
            item_data = gears_db[item_name]
            if item_data.get("type", "Hat") == slot:
                gear_list.append(item_data)
                for k in gear_stats:
                    if k in item_data:
                        gear_stats[k] += item_data.get(k, 0)
        else:
            gear_list.append({"Name": "(Empty)", "type": slot})
    return gear_stats, gear_list


def get_config_mini_stats(cfg, paths, minis_db=None):
    """
    Returns (mini_stats_dict, mini_list) from config.
    minis_db: optional dict {Name: stats}. If None, load from CSV.
    """
    if minis_db is None:
        minis_db = load_csv_db(resolve_stats_csv(paths, "Minis.csv"), "mini")

    mini_stats = empty_stats()
    mini_list = []
    for i in range(1, 4):
        item_name = cfg.get("Minis", str(i), fallback="").strip().strip(" .")
        if item_name in minis_db:
            item_data = minis_db[item_name]
            mini_list.append(item_data)
            for k in mini_stats:
                if k in item_data:
                    mini_stats[k] += item_data.get(k, 0)
        else:
            mini_list.append({"Name": "(Empty)", "type": "Mini"})
    return mini_stats, mini_list


def load_force_greats_config(cfg):
    """
    Parse [ForceGreats] options into a list indexed by non-fever section (0-based).
    Keys follow the pattern NonFever{N}; missing values default to zero.
    """
    if not cfg or not cfg.has_section("ForceGreats"):
        return []
    entries = []
    try:
        for opt, raw in cfg.items("ForceGreats"):
            match = re.match(r"nonfever(\d+)", opt.strip().lower())
            if not match:
                continue
            idx = max(0, safe_int(match.group(1)) - 1)
            val = max(0, safe_int(raw, 0))
            entries.append((idx, val))
    except Exception:
        return []

    if not entries:
        return []

    max_idx = max(idx for idx, _ in entries)
    values = [0] * (max_idx + 1)
    for idx, val in entries:
        values[idx] = val
    return values


# --- Song Scanner ---
def scan_song_header(fp):
    meta = {"Song Name": "", "Primary Color": "", "Secondary Color": "", "Difficulty": ""}
    try:
        with open(fp, "r", encoding="utf-8-sig") as f:
            for _ in range(20):
                line = f.readline()
                if not line:
                    break
                line = line.strip()
                if line == "Song Data":
                    break
                # Handle both TAB and COLON separators
                if "\t" in line:
                    parts = line.split("\t", 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        if key in meta:
                            meta[key] = parts[1].strip()
                elif ":" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        if key in meta:
                            meta[key] = parts[1].strip()
        return meta if meta["Song Name"] else None
    except Exception:
        return None


def read_song_file(fp):
    data = {
        "song_details": {
            "Song Name": "",
            "Difficulty": "",
            "Primary Color": "",
            "Secondary Color": "",
            "Last Note Time": "",
            "Total Notes": "",
            "Fever Fill": "",
            "Fever Time": "",
            "Long Notes": "",
        },
        "timestamps": [],
    }
    if not fp:
        return data
    try:
        with open(fp, "r", encoding="utf-8-sig") as f:
            lines = f.read().splitlines()
        marker = next(
            (i for i, line in enumerate(lines) if line.strip() == "Song Data"), -1
        )
        if marker == -1:
            return data
        for line in lines[:marker]:
            if not line.strip():
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                if key in data["song_details"]:
                    data["song_details"][key] = parts[1].strip() or "0"

        note_lines = []
        for line in lines[marker + 1:]:
            s = line.strip()
            if not s:
                continue
            c = s[0]
            if ("0" <= c <= "9") or c == ".":
                note_lines.append(line)

        if note_lines:
            nd = np.loadtxt(StringIO("\n".join(note_lines)), delimiter=None)
            if nd.size:
                nd = nd.reshape(1, -1) if nd.ndim == 1 else nd
                if nd.shape[1] >= 4:
                    data["timestamps"] = nd[:, 0].tolist()
        return data
    except Exception as exc:
        WARN_ONCE.warn("song-file", f"Failed to read song file {fp}: {exc}")
        return data


# === JIT CALCULATION LOGIC ===
def lookup_reference_py(value, ref_array, total_rows=TOTAL_ROWS):
    clamped = max(0, min(total_rows, int(value)))
    return ref_array[clamped]


@jit(nopython=True, cache=True)
def lookup_reference_jit(value, ref_array, total_rows):
    idx = int(value)
    if idx > total_rows:
        idx = total_rows
    elif idx < 0:
        idx = 0
    return ref_array[idx]


@jit(nopython=True, cache=True)
def calculate_fever_timeline_indices(
    song_timestamps,
    total_notes,
    fever_fill_rate,
    fever_time_stat,
    long_notes_count,
    last_note_time,
    fever_mask_buffer,
):
    """
    Calculate fever timeline using corrected server-matching logic.
    
    Key fixes:
    1. First non-fever section: non_fever_base - 1 notes
       Later sections: non_fever_base notes (1 "wasted" note where fever ends)
    2. Binary search uses side="left" (>=) instead of side="right" (>)
    """
    non_fever_cas = (total_notes - long_notes_count) * 0.333
    non_fever_base = ceil(non_fever_cas * fever_fill_rate)
    fever_time_cas = last_note_time * 0.15 + 0.15
    real_fever_time = fever_time_cas * fever_time_stat

    is_fever = fever_mask_buffer
    is_fever[:] = False
    current_note_idx = 0
    fever_activations = 0
    fever_section = 0

    while current_note_idx < total_notes:
        # Non-fever section
        fever_section += 1
        # First section: -1, Later sections: use base (wasted note effect)
        if fever_section == 1:
            notes_to_fill = non_fever_base - 1
        else:
            notes_to_fill = non_fever_base
        
        end_normal_idx = min(current_note_idx + notes_to_fill, total_notes)
        current_note_idx = end_normal_idx
        if current_note_idx >= total_notes:
            break

        if current_note_idx > 0:
            fever_activations += 1
            start_time = song_timestamps[current_note_idx]
            end_time = start_time + real_fever_time
            # Use side="left" to find first note where time >= end_time (not >)
            fever_end_idx = np.searchsorted(song_timestamps, end_time, side="left")
            is_fever[current_note_idx:fever_end_idx] = True
            current_note_idx = fever_end_idx
        else:
            break

    head_limit = min(total_notes, 100)
    fever_mask_head = is_fever[:head_limit]
    count_body_fever = 0
    count_body_normal = 0
    if total_notes > 100:
        for i in range(100, total_notes):
            if is_fever[i]:
                count_body_fever += 1
            else:
                count_body_normal += 1
    return fever_mask_head, count_body_fever, count_body_normal, fever_activations


@jit(nopython=True, cache=True)
def fast_calculate_score(
    base_value,
    combo_mul,
    fever_mul,
    fever_mask_head,
    count_body_fever,
    count_body_normal,
):
    """
    Fast JIT-compiled score calculation.
    
    NOTE: The old fever_activations_count adjustment has been REMOVED.
    The timeline calculation now correctly handles note allocation per fever cycle,
    so no adjustment is needed.
    """
    combo_val_per_note = floor(base_value * combo_mul)
    fever_val_per_note = floor(base_value * combo_mul * fever_mul)

    body_score = (count_body_fever * fever_val_per_note) + (
        count_body_normal * combo_val_per_note
    )

    # OLD PATCH REMOVED - no longer needed with corrected timeline

    factor = (combo_mul - 1) * base_value / 100.0
    total_head = 0.0
    n_head = len(fever_mask_head)

    for i in range(n_head):
        current_ramp_val = base_value + ((i + 1) * factor)
        if fever_mask_head[i]:
            val = floor(current_ramp_val * fever_mul)
        else:
            val = floor(current_ramp_val)
        total_head += val

    return int(body_score + total_head)


@jit(nopython=True, cache=True)
def optimize_core_jit(
    budget,
    cur_pp,
    cur_cm,
    cur_fm,
    cur_p_val,
    cur_s_val,
    is_p_pp,
    is_s_pp,
    is_p_cm,
    is_s_cm,
    is_p_fm,
    is_s_fm,
    is_p_ov,
    is_s_ov,
    ref_pp,
    ref_cm,
    ref_fm,
    fever_mask_head,
    count_body_fever,
    count_body_normal,
    GEM_SCALE_NORMAL,
    GEM_SCALE_FEVER,
    GEM_STAT_TO_ELEMENT_SCALE,
    ELEMENTAL_GEM_SCALE,
    TOTAL_ROWS,
    MAX_STAT_INDEX,
):
    gems_pp = 0
    gems_cm = 0
    gems_fm = 0
    gems_ov = 0
    remaining_budget = budget

    while remaining_budget > 0:
        best_score = -1.0
        best_opt_idx = -1
        fill_budget = remaining_budget - 1
        fill_bonus = (fill_budget * ELEMENTAL_GEM_SCALE) if fill_budget > 0 else 0

        # 0: PP
        if cur_pp < MAX_STAT_INDEX:
            t_pp = cur_pp + GEM_SCALE_NORMAL
            t_p = cur_p_val + (GEM_STAT_TO_ELEMENT_SCALE * is_p_pp) + (
                fill_bonus * is_p_ov
            )
            t_s = cur_s_val + (GEM_STAT_TO_ELEMENT_SCALE * is_s_pp) + (
                fill_bonus * is_s_ov
            )
            pp_factor = lookup_reference_jit(t_pp, ref_pp, TOTAL_ROWS)
            base = (t_p * 2) + t_s + pp_factor
            c_mul = lookup_reference_jit(cur_cm, ref_cm, TOTAL_ROWS)
            f_mul = lookup_reference_jit(cur_fm, ref_fm, TOTAL_ROWS)
            score = fast_calculate_score(
                base,
                c_mul,
                f_mul,
                fever_mask_head,
                count_body_fever,
                count_body_normal,
            )
            if score >= best_score:
                best_score = score
                best_opt_idx = 0

        # 1: CM
        if cur_cm < MAX_STAT_INDEX:
            t_cm = cur_cm + GEM_SCALE_NORMAL
            t_p = cur_p_val + (GEM_STAT_TO_ELEMENT_SCALE * is_p_cm) + (
                fill_bonus * is_p_ov
            )
            t_s = cur_s_val + (GEM_STAT_TO_ELEMENT_SCALE * is_s_cm) + (
                fill_bonus * is_s_ov
            )
            pp_factor = lookup_reference_jit(cur_pp, ref_pp, TOTAL_ROWS)
            base = (t_p * 2) + t_s + pp_factor
            c_mul = lookup_reference_jit(t_cm, ref_cm, TOTAL_ROWS)
            f_mul = lookup_reference_jit(cur_fm, ref_fm, TOTAL_ROWS)
            score = fast_calculate_score(
                base,
                c_mul,
                f_mul,
                fever_mask_head,
                count_body_fever,
                count_body_normal,
            )
            if score > best_score:
                best_score = score
                best_opt_idx = 1

        # 2: FM
        if cur_fm < MAX_STAT_INDEX:
            t_fm = cur_fm + GEM_SCALE_FEVER
            t_p = cur_p_val + (GEM_STAT_TO_ELEMENT_SCALE * is_p_fm) + (
                fill_bonus * is_p_ov
            )
            t_s = cur_s_val + (GEM_STAT_TO_ELEMENT_SCALE * is_s_fm) + (
                fill_bonus * is_s_ov
            )
            pp_factor = lookup_reference_jit(cur_pp, ref_pp, TOTAL_ROWS)
            base = (t_p * 2) + t_s + pp_factor
            c_mul = lookup_reference_jit(cur_cm, ref_cm, TOTAL_ROWS)
            f_mul = lookup_reference_jit(t_fm, ref_fm, TOTAL_ROWS)
            score = fast_calculate_score(
                base,
                c_mul,
                f_mul,
                fever_mask_head,
                count_body_fever,
                count_body_normal,
            )
            if score > best_score:
                best_score = score
                best_opt_idx = 2

        # 3: Overflow
        t_p = cur_p_val + (ELEMENTAL_GEM_SCALE * is_p_ov) + (fill_bonus * is_p_ov)
        t_s = cur_s_val + (ELEMENTAL_GEM_SCALE * is_s_ov) + (fill_bonus * is_s_ov)
        pp_factor = lookup_reference_jit(cur_pp, ref_pp, TOTAL_ROWS)
        base = (t_p * 2) + t_s + pp_factor
        c_mul = lookup_reference_jit(cur_cm, ref_cm, TOTAL_ROWS)
        f_mul = lookup_reference_jit(cur_fm, ref_fm, TOTAL_ROWS)
        score = fast_calculate_score(
            base,
            c_mul,
            f_mul,
            fever_mask_head,
            count_body_fever,
            count_body_normal,
        )
        if score >= best_score:
            best_score = score
            best_opt_idx = 3

        if best_opt_idx == 0:
            cur_pp += GEM_SCALE_NORMAL
            cur_p_val += GEM_STAT_TO_ELEMENT_SCALE * is_p_pp
            cur_s_val += GEM_STAT_TO_ELEMENT_SCALE * is_s_pp
            gems_pp += 1
        elif best_opt_idx == 1:
            cur_cm += GEM_SCALE_NORMAL
            cur_p_val += GEM_STAT_TO_ELEMENT_SCALE * is_p_cm
            cur_s_val += GEM_STAT_TO_ELEMENT_SCALE * is_s_cm
            gems_cm += 1
        elif best_opt_idx == 2:
            cur_fm += GEM_SCALE_FEVER
            cur_p_val += GEM_STAT_TO_ELEMENT_SCALE * is_p_fm
            cur_s_val += GEM_STAT_TO_ELEMENT_SCALE * is_s_fm
            gems_fm += 1
        else:
            cur_p_val += ELEMENTAL_GEM_SCALE * is_p_ov
            cur_s_val += ELEMENTAL_GEM_SCALE * is_s_ov
            gems_ov += 1
        remaining_budget -= 1

    return (
        cur_pp,
        cur_cm,
        cur_fm,
        cur_p_val,
        cur_s_val,
        gems_pp,
        gems_cm,
        gems_fm,
        gems_ov,
    )


# === WORKERS ===
def worker_coevolution_evaluate(args):
    """
    Evaluates a Co-Evolution Individual.
    
    Uses a stat-signature cache: if multiple gear+mini combinations produce
    the same effective stats for the song's Primary/Secondary/Selected paths,
    we reuse the gem solver result instead of recomputing.
    """
    (genome, base_stats_fixed, cfg_data, calc_song, ref_arrays) = args

    current_stats = base_stats_fixed.copy()
    cs = current_stats
    cs_get = cs.get

    for item in genome:
        for k, v in item.items():
            if k not in SKIP_ITEM_KEYS:
                cs[k] = cs_get(k, 0) + v

    # Check stat-signature cache before calling the expensive gem solver.
    sel_color = cfg_data["selected_color"]
    sig = stats_signature(current_stats, calc_song, sel_color)
    cached = GEM_SOLVER_CACHE.get(sig)

    if cached is None:
        res = solve_best_fever_combination(
            None,
            current_stats,
            calc_song,
            ref_arrays,
            silent=True,
            override_cfg=cfg_data,
        )
        GEM_SOLVER_CACHE[sig] = res
    else:
        res = cached

    gear_part = genome[:6]
    mini_part = genome[6:]
    mini_names = [m["Name"] for m in mini_part]

    return {
        "Score": res["Score"],
        "Genome": genome,
        "Gear": gear_part,
        "Minis": mini_part,
        "MiniNames": mini_names,
        "Data": res,
    }


# === SOLVERS ===
def evaluate_stats_score(
    stats,
    calc_song,
    ref_arrays,
    song_timestamps=None,
    long_notes=None,
    last_note=None,
    fever_mask_buffer=None,
):
    """Return total score for a fixed stats snapshot without reallocations."""
    timestamps = (
        song_timestamps if song_timestamps is not None else calc_song["song_data"]["timestamps"]
    )
    total_notes = len(timestamps)
    long_count = (
        long_notes
        if long_notes is not None
        else safe_int(calc_song["metadata"].get("Long Notes"), 0)
    )
    default_last_note = timestamps[-1] if total_notes else 0.0
    last_time = (
        last_note
        if last_note is not None
        else safe_float(calc_song["metadata"].get("Last Note Time"), default_last_note)
    )
    mask_buffer = fever_mask_buffer
    if mask_buffer is None or mask_buffer.shape[0] != total_notes:
        mask_buffer = np.zeros(total_notes, dtype=np.bool_)

    ft_factor = lookup_reference_py(stats["Fever Time"], ref_arrays["Fever Time"], TOTAL_ROWS)
    ff_factor = lookup_reference_py(stats["Fever Fill Rate"], ref_arrays["Fever Fill Rate"], TOTAL_ROWS)
    fever_mask_head, count_body_fever, count_body_normal, _ = calculate_fever_timeline_indices(
        timestamps,
        total_notes,
        ff_factor,
        ft_factor,
        long_count,
        last_time,
        mask_buffer,
    )

    base_pp = lookup_reference_py(stats["Perfect Points"], ref_arrays["Perfect Points"], TOTAL_ROWS)
    combo_mul = lookup_reference_py(stats["Combo Multiplier"], ref_arrays["Combo Multiplier"], TOTAL_ROWS)
    fever_mul = lookup_reference_py(stats["Fever Multiplier"], ref_arrays["Fever Multiplier"], TOTAL_ROWS)

    p_color = calc_song["metadata"].get("Primary Color", "")
    s_color = calc_song["metadata"].get("Secondary Color", "")
    primary_val = stats.get(p_color, 0)
    secondary_val = stats.get(s_color, 0)
    total_base = (primary_val * 2) + secondary_val + base_pp

    return fast_calculate_score(
        total_base,
        combo_mul,
        fever_mul,
        fever_mask_head,
        count_body_fever,
        count_body_normal,
    )


def _force_greats_counts_to_dict(counts, sections):
    config = {}
    for idx in range(sections):
        val = counts[idx] if idx < len(counts) else 0
        config[f"NonFever{idx + 1}"] = max(0, int(val))
    return config


def build_great_penalty_table(base_value, combo_mul, great_penalty_base, head_limit=100):
    """
    Precompute ramp penalties for the first `head_limit` notes.
    Avoids recalculating scaling when evaluating force-great permutations.
    """
    penalties = [0] * head_limit
    combo_span = combo_mul - 1.0
    for idx in range(head_limit):
        scaling = 1.0 + combo_span * (idx + 1) / 100.0
        perfect_val = floor(base_value * scaling)
        great_val = floor(great_penalty_base * scaling)
        penalties[idx] = max(0, perfect_val - great_val)
    return penalties


def evaluate_force_greats(stats, calc_song, ref_arrays, forced_counts=None):
    """
    Recompute fever timeline and penalties when greats are forced in non-fever sections.
    Returns None when prerequisites are missing.
    """
    if not stats or not calc_song:
        return None

    timestamps = calc_song["song_data"]["timestamps"]
    total_notes = len(timestamps)
    if total_notes <= 0:
        return None

    metadata = calc_song["metadata"]
    long_notes = safe_int(metadata.get("Long Notes"), 0)
    default_last_note = timestamps[-1] if total_notes else 0.0
    last_note_time = safe_float(metadata.get("Last Note Time"), default_last_note)
    primary_color = metadata.get("Primary Color", "")
    secondary_color = metadata.get("Secondary Color", "")
    primary_val = stats.get(primary_color, 0)
    secondary_val = stats.get(secondary_color, 0)

    ref_pp = ref_arrays["Perfect Points"]
    ref_cm = ref_arrays["Combo Multiplier"]
    ref_fm = ref_arrays["Fever Multiplier"]
    ref_ff = ref_arrays["Fever Fill Rate"]
    ref_ft = ref_arrays["Fever Time"]

    pp_factor = lookup_reference_py(stats["Perfect Points"], ref_pp, TOTAL_ROWS)
    combo_mul = lookup_reference_py(stats["Combo Multiplier"], ref_cm, TOTAL_ROWS)
    fever_mul = lookup_reference_py(stats["Fever Multiplier"], ref_fm, TOTAL_ROWS)
    fever_fill_rate = lookup_reference_py(stats["Fever Fill Rate"], ref_ff, TOTAL_ROWS)
    fever_time_stat = lookup_reference_py(stats["Fever Time"], ref_ft, TOTAL_ROWS)

    base_value = (primary_val * 2) + secondary_val + pp_factor
    combo_value = floor(base_value * combo_mul)
    great_penalty_base = floor(((primary_val * 2) + secondary_val) * (2.0 / 3.0) + 150.0)
    great_combo_value = floor(great_penalty_base * combo_mul)
    penalty_table = build_great_penalty_table(base_value, combo_mul, great_penalty_base)
    body_penalty = max(0, combo_value - great_combo_value)

    non_fever_cas = max(0.0, (total_notes - long_notes) * 0.333)
    non_fever_base = ceil(non_fever_cas * fever_fill_rate)
    non_fever_great_to_fill = ceil(max(1.0, (non_fever_cas * fever_fill_rate) * 2.0))
    fever_time_cas = last_note_time * 0.15 + 0.15
    real_fever_time = fever_time_cas * fever_time_stat

    force_counts = list(forced_counts or [])
    fever_mask = np.zeros(total_notes, dtype=np.bool_)
    current_idx = 0
    non_fever_section = 0
    section_details = []

    while current_idx < total_notes:
        non_fever_section += 1
        base_notes = non_fever_base - 1 if non_fever_section == 1 else non_fever_base
        base_notes = max(0, base_notes)
        forced_val = 0
        if non_fever_section - 1 < len(force_counts):
            forced_val = max(0, int(force_counts[non_fever_section - 1]))
        forced_val = min(forced_val, non_fever_base)
        fill_penalty_notes = ceil(
            max(0.0, (non_fever_base * forced_val) / non_fever_great_to_fill)
        )
        notes_to_fill = base_notes + fill_penalty_notes
        section_start = current_idx
        end_normal = min(section_start + notes_to_fill, total_notes)
        actual_notes = max(0, end_normal - section_start)
        forced_applied = min(forced_val, actual_notes)

        section_details.append(
            {
                "start_idx": section_start,
                "notes": actual_notes,
                "forced": forced_applied,
                "fill_penalty_notes": fill_penalty_notes,
                "skip_wasted": (non_fever_section == 1),
            }
        )
        current_idx = end_normal
        if current_idx >= total_notes:
            break

        start_time = timestamps[current_idx]
        end_time = start_time + real_fever_time
        fever_end_idx = int(np.searchsorted(timestamps, end_time, side="left"))
        if fever_end_idx <= current_idx:
            fever_end_idx = min(total_notes, current_idx + 1)
        fever_mask[current_idx:fever_end_idx] = True
        current_idx = fever_end_idx

    head_limit = min(total_notes, 100)
    fever_mask_head = fever_mask[:head_limit]
    if total_notes > 100:
        body_slice = fever_mask[100:]
        count_body_fever = int(np.count_nonzero(body_slice))
        count_body_normal = max(len(body_slice) - count_body_fever, 0)
    else:
        count_body_fever = 0
        count_body_normal = 0

    base_score = fast_calculate_score(
        base_value,
        combo_mul,
        fever_mul,
        fever_mask_head,
        count_body_fever,
        count_body_normal,
    )

    total_score_penalty = 0
    total_fill_penalty = 0
    penalty_analysis = {}
    for idx, detail in enumerate(section_details):
        section_key = f"NonFever{idx + 1}"
        fill_penalty_score = detail["fill_penalty_notes"] * combo_value
        total_fill_penalty += fill_penalty_score
        forced = detail["forced"]
        if forced > 0:
            start_idx = detail["start_idx"]
            if detail.get("skip_wasted"):
                start_idx = min(total_notes, start_idx + 1)
            score_penalty = 0
            note_idx = start_idx
            remaining = forced
            while remaining > 0:
                if note_idx < len(penalty_table):
                    score_penalty += penalty_table[note_idx]
                else:
                    score_penalty += body_penalty
                note_idx += 1
                remaining -= 1
        else:
            score_penalty = 0
        total_score_penalty += score_penalty
        penalty_analysis[section_key] = {
            "forced_greats": forced,
            "score_penalty": score_penalty,
            "fill_penalty": fill_penalty_score,
            "total_penalty": score_penalty + fill_penalty_score,
        }

    used_counts = force_counts[:]
    if len(used_counts) < len(section_details):
        used_counts.extend([0] * (len(section_details) - len(used_counts)))

    return {
        "base_score": base_score,
        "final_score": max(0, base_score - total_score_penalty),
        "score_penalty": total_score_penalty,
        "fill_penalty": total_fill_penalty,
        "total_penalty": total_score_penalty + total_fill_penalty,
        "num_non_fever_sections": len(section_details),
        "config_counts": used_counts[: len(section_details)],
        "config_dict": _force_greats_counts_to_dict(used_counts, len(section_details)),
        "penalty_analysis": penalty_analysis,
        "non_fever_base": non_fever_base,
    }


def run_force_greats_hill_climb(stats, calc_song, ref_arrays):
    """
    Simple hill-climb optimizer that increments forced greats per section
    while the total score improves.
    """
    baseline = evaluate_force_greats(stats, calc_song, ref_arrays, [])
    if not baseline:
        return None

    best_counts = [0] * baseline["num_non_fever_sections"]
    best_result = evaluate_force_greats(stats, calc_song, ref_arrays, best_counts)
    if not best_result or best_result["num_non_fever_sections"] == 0:
        return best_result

    improved = True
    while improved:
        improved = False
        for idx in range(best_result["num_non_fever_sections"]):
            candidate_counts = best_counts[:]
            if idx >= len(candidate_counts):
                candidate_counts.extend([0] * (idx + 1 - len(candidate_counts)))
            candidate_counts[idx] += 1
            candidate = evaluate_force_greats(stats, calc_song, ref_arrays, candidate_counts)
            if candidate and candidate["final_score"] > best_result["final_score"]:
                best_counts = candidate_counts
                best_result = candidate
                improved = True
                break
    return best_result


@dataclass
class GASettings:
    db_seed_prob: float
    fixed_seed_copies: int
    memetic_elites: int
    memetic_steps: int
    memetic_top_gear: int
    memetic_top_minis: int
    multi_start: int
    deep_mining_enabled: bool

    @classmethod
    def from_cfg(cls, cfg):
        section = "IterationEngine"
        if not cfg:
            return cls(
                0.5,
                2,
                4,
                2,
                4,
                12,
                GA_MULTI_RUNS_DEFAULT,
                True,
            )

        def get_option(option, fallback):
            try:
                return cfg.get(section, option, fallback=fallback)
            except Exception:
                return fallback

        db_seed_prob = safe_float(get_option("GA_DBSeedProbability", "0.5"), default=0.5)
        fixed_seed_copies = max(0, safe_int(get_option("GA_FixedSeedCopies", "2"), 2))
        memetic_elites = max(0, safe_int(get_option("GA_MemeticElites", "4"), 4))
        memetic_steps = max(0, safe_int(get_option("GA_MemeticSteps", "2"), 2))
        memetic_top_gear = max(1, safe_int(get_option("GA_MemeticTopGear", "4"), 4))
        memetic_top_minis = max(1, safe_int(get_option("GA_MemeticTopMinis", "12"), 12))
        multi_start = max(
            1,
            safe_int(
                get_option("GA_MultiStart", str(GA_MULTI_RUNS_DEFAULT)),
                GA_MULTI_RUNS_DEFAULT,
            ),
        )
        deep_mining = cfg.getboolean(section, "DeepMining", fallback=True)

        return cls(
            min(1.0, max(0.0, db_seed_prob)),
            fixed_seed_copies,
            memetic_elites,
            memetic_steps,
            memetic_top_gear,
            memetic_top_minis,
            multi_start,
            deep_mining,
        )


def apply_force_greats_to_result(
    data_dict,
    calc_song,
    ref_arrays,
    manual_counts=None,
    use_finder=False,
):
    """
    Evaluate forced-great penalties (manual config or hill-climb finder) for a result dict.
    Returns a cloned variant with the adjusted score while leaving the original untouched.
    Uses FG_CACHE to avoid redundant calculations for identical stats.
    """
    if not data_dict or "Stats" not in data_dict:
        return None

    stats = data_dict.get("Stats") or {}
    if not stats:
        return None

    # Build cache key from stats signature + FG parameters
    selected_color = data_dict.get("Selected Element", calc_song["metadata"].get("Primary Color", ""))
    base_sig = stats_signature(stats, calc_song, selected_color)
    manual_tuple = tuple(manual_counts) if manual_counts else ()
    fg_cache_key = (base_sig, use_finder, manual_tuple)

    # Check cache first
    cached_fg = FG_CACHE.get(fg_cache_key)
    if cached_fg is not None:
        fg_result = cached_fg
    else:
        if use_finder:
            fg_result = run_force_greats_hill_climb(stats, calc_song, ref_arrays)
        else:
            fg_result = evaluate_force_greats(stats, calc_song, ref_arrays, manual_counts)
        # Cache the result (even if None)
        FG_CACHE[fg_cache_key] = fg_result

    if not fg_result:
        return None

    fg_info = {
        "enabled": True,
        "config": fg_result["config_dict"],
        "base_score": fg_result["base_score"],
        "final_score": fg_result["final_score"],
        "score_penalty": fg_result["score_penalty"],
        "fill_penalty": fg_result["fill_penalty"],
        "total_penalty": fg_result["total_penalty"],
        "num_non_fever_sections": fg_result["num_non_fever_sections"],
        "penalty_analysis": fg_result["penalty_analysis"],
    }

    data_dict["ForceGreats"] = fg_info

    # Memory leak fix: Shallow copy is sufficient (only modifying top-level keys)
    # Eliminates 28K deepcopy operations per song
    fg_variant = data_dict.copy()
    fg_variant["Score"] = fg_result["final_score"]
    fg_variant["ForceGreats"] = {**fg_info, "variant_applied": True}
    return fg_variant


def solve_best_fever_combination(
    cfg,
    initial_stats,
    calc_song,
    ref_arrays,
    silent=False,
    override_cfg=None,
    skip_optimizer=False,
):
    if override_cfg:
        user_ft = override_cfg["user_ft"]
        user_ff = override_cfg["user_ff"]
        user_pp = override_cfg["user_pp"]
        user_cm = override_cfg["user_cm"]
        user_fm = override_cfg["user_fm"]
        selected_color = override_cfg["selected_color"]
        static_elem_input = override_cfg["static_elem_input"]
    else:
        if not silent:
            print("\n=== STARTING FEVER ITERATION ENGINE (GEM SOLVER) ===")
        user_ft = safe_int(cfg.get("UserInputStatsGems", "fever_time", fallback=0))
        user_ff = safe_int(cfg.get("UserInputStatsGems", "fever_fill", fallback=0))
        user_pp = safe_int(cfg.get("UserInputStatsGems", "perfect_points", fallback=0))
        user_cm = safe_int(
            cfg.get("UserInputStatsGems", "combo_multiplier", fallback=0)
        )
        user_fm = safe_int(
            cfg.get("UserInputStatsGems", "fever_multiplier", fallback=0)
        )
        selected_color = calc_song["metadata"].get("Primary Color", "Rush")
        static_elem_input = safe_int(
            cfg.get("ElementalGems", selected_color, fallback=0)
        )

    base_stats = initial_stats.copy()

    # OPTIMIZATION: timestamps are already a NumPy array (set in __main__)
    song_timestamps = calc_song["song_data"]["timestamps"]
    total_notes = len(song_timestamps)
    long_notes = int(calc_song["metadata"].get("Long Notes", 0))
    last_note = float(calc_song["metadata"].get("Last Note Time", 0))
    p_color = calc_song["metadata"].get("Primary Color", "")
    s_color = calc_song["metadata"].get("Secondary Color", "")

    # Reuse mask buffer across FT/FF permutations to avoid repeated allocations.
    fever_mask_buffer = np.zeros(total_notes, dtype=np.bool_)

    ref_pp = ref_arrays["Perfect Points"]
    ref_cm = ref_arrays["Combo Multiplier"]
    ref_fm = ref_arrays["Fever Multiplier"]
    ref_ft = ref_arrays["Fever Time"]
    ref_ff = ref_arrays["Fever Fill Rate"]

    if skip_optimizer:
        score = evaluate_stats_score(
            base_stats,
            calc_song,
            ref_arrays,
            song_timestamps=song_timestamps,
            long_notes=long_notes,
            last_note=last_note,
            fever_mask_buffer=fever_mask_buffer,
        )
        return {
            "Score": score,
            "FT": user_ft,
            "FF": user_ff,
            "GemCounts": {
                "Perfect Points": user_pp,
                "Combo Multiplier": user_cm,
                "Fever Multiplier": user_fm,
                "Element Overflow": static_elem_input,
            },
            "Stats": base_stats,
            "Selected Element": selected_color,
        }

    base_stats["Fever Time"] -= user_ft * GEM_SCALE_FEVER
    base_stats["Beat"] -= user_ft * GEM_STAT_TO_ELEMENT_SCALE
    base_stats["Fever Fill Rate"] -= user_ff * GEM_SCALE_FEVER
    base_stats["Vibe"] -= user_ff * GEM_STAT_TO_ELEMENT_SCALE
    base_stats["Fever Multiplier"] -= user_fm * GEM_SCALE_FEVER
    base_stats["Rush"] -= user_fm * GEM_STAT_TO_ELEMENT_SCALE
    base_stats["Combo Multiplier"] -= user_cm * GEM_SCALE_NORMAL
    base_stats["Flow"] -= user_cm * GEM_STAT_TO_ELEMENT_SCALE
    base_stats["Perfect Points"] -= user_pp * GEM_SCALE_NORMAL
    base_stats["Chill"] -= user_pp * GEM_STAT_TO_ELEMENT_SCALE
    base_stats[selected_color] -= static_elem_input * ELEMENTAL_GEM_SCALE

    remaining_ft_stat = MAX_STAT_INDEX - base_stats["Fever Time"]
    remaining_ff_stat = MAX_STAT_INDEX - base_stats["Fever Fill Rate"]
    max_ft_gems = floor(remaining_ft_stat / GEM_SCALE_FEVER) if remaining_ft_stat > 0 else 0
    max_ff_gems = floor(remaining_ff_stat / GEM_SCALE_FEVER) if remaining_ff_stat > 0 else 0

    if not silent:
        print(f"Max allocatable Gems: FT<={max_ft_gems}, Fill<={max_ff_gems}")
        print("Iterating permutations...")

    best_score = -1
    best_tuple = None

    range_ft = min(TOTAL_GEM_BUDGET, max_ft_gems)

    is_p_pp = 1 if "Chill" == p_color else 0
    is_s_pp = 1 if "Chill" == s_color else 0
    is_p_cm = 1 if "Flow" == p_color else 0
    is_s_cm = 1 if "Flow" == s_color else 0
    is_p_fm = 1 if "Rush" == p_color else 0
    is_s_fm = 1 if "Rush" == s_color else 0
    is_p_ov = 1 if selected_color == p_color else 0
    is_s_ov = 1 if selected_color == s_color else 0

    base_beat = base_stats.get("Beat", 0)
    base_vibe = base_stats.get("Vibe", 0)

    bs_get = base_stats.get

    def get_val_inline(k, b, v):
        if k == "Beat":
            return b
        if k == "Vibe":
            return v
        return bs_get(k, 0)

    cur_pp = base_stats["Perfect Points"]
    cur_cm = base_stats["Combo Multiplier"]
    cur_fm = base_stats["Fever Multiplier"]

    base_ft_stat = base_stats["Fever Time"]
    base_ff_stat = base_stats["Fever Fill Rate"]

    song_cache_key = (
        calc_song["metadata"].get("Song Name", ""),
        total_notes,
        long_notes,
        round(last_note, 5),
    )
    # Memory leak fix: Use flattened cache key for global LRU
    # (no nested dicts, all entries at top level)

    # OPTIMIZATION: precompute FT/FF reference lookups
    ft_stat_table = [
        base_ft_stat + (ft_val * GEM_SCALE_FEVER) for ft_val in range(range_ft + 1)
    ]
    ft_factor_table = [
        lookup_reference_py(stat, ref_ft, TOTAL_ROWS) for stat in ft_stat_table
    ]

    ff_stat_table = [
        base_ff_stat + (ff_val * GEM_SCALE_FEVER) for ff_val in range(max_ff_gems + 1)
    ]
    ff_factor_table = [
        lookup_reference_py(stat, ref_ff, TOTAL_ROWS) for stat in ff_stat_table
    ]

    # Cache timelines per (ft, ff) combo for this song/config to avoid recomputing.

    for ft in range(range_ft + 1):
        remaining_for_ff = TOTAL_GEM_BUDGET - ft
        range_ff = min(remaining_for_ff, max_ff_gems)

        stat_ft_val = ft_stat_table[ft]
        ft_factor = ft_factor_table[ft]
        cur_beat = base_beat + (ft * GEM_STAT_TO_ELEMENT_SCALE)

        for ff in range(range_ff + 1):
            current_budget = TOTAL_GEM_BUDGET - ft - ff
            stat_ff_val = ff_stat_table[ff]
            ff_factor = ff_factor_table[ff]

            # Flattened cache key: song info + FT/FF stats
            cache_key = song_cache_key + (stat_ft_val, stat_ff_val)
            cached_timeline = FEVER_TIMELINE_CACHE.get(cache_key)
            if cached_timeline:
                (
                    fever_mask_head,
                    count_body_fever,
                    count_body_normal,
                    fever_activations,
                ) = cached_timeline
            else:
                (
                    fever_mask_head,
                    count_body_fever,
                    count_body_normal,
                    fever_activations,
                ) = calculate_fever_timeline_indices(
                    song_timestamps,
                    total_notes,
                    ff_factor,
                    ft_factor,
                    long_notes,
                    last_note,
                    fever_mask_buffer,
                )
                # Copy the head slice so the shared buffer can be reused safely.
                # LRUCache auto-evicts when global limit is reached
                FEVER_TIMELINE_CACHE[cache_key] = (
                    fever_mask_head.copy(),
                    count_body_fever,
                    count_body_normal,
                    fever_activations,
                )

            cur_vibe = base_vibe + (ff * GEM_STAT_TO_ELEMENT_SCALE)

            cur_p_val = get_val_inline(p_color, cur_beat, cur_vibe)
            cur_s_val = get_val_inline(s_color, cur_beat, cur_vibe)

            (
                final_pp,
                final_cm,
                final_fm,
                final_p_val,
                final_s_val,
                g_pp,
                g_cm,
                g_fm,
                g_ov,
            ) = optimize_core_jit(
                current_budget,
                cur_pp,
                cur_cm,
                cur_fm,
                cur_p_val,
                cur_s_val,
                is_p_pp,
                is_s_pp,
                is_p_cm,
                is_s_cm,
                is_p_fm,
                is_s_fm,
                is_p_ov,
                is_s_ov,
                ref_pp,
                ref_cm,
                ref_fm,
                fever_mask_head,
                count_body_fever,
                count_body_normal,
                GEM_SCALE_NORMAL,
                GEM_SCALE_FEVER,
                GEM_STAT_TO_ELEMENT_SCALE,
                ELEMENTAL_GEM_SCALE,
                TOTAL_ROWS,
                MAX_STAT_INDEX,
            )

            base = (final_p_val * 2) + final_s_val + lookup_reference_py(
                final_pp, ref_pp, TOTAL_ROWS
            )
            c_mul = lookup_reference_py(final_cm, ref_cm, TOTAL_ROWS)
            f_mul = lookup_reference_py(final_fm, ref_fm, TOTAL_ROWS)
            total_score = fast_calculate_score(
                base,
                c_mul,
                f_mul,
                fever_mask_head,
                count_body_fever,
                count_body_normal,
            )

            if total_score > best_score:
                best_score = total_score
                best_tuple = (total_score, ft, ff, g_pp, g_cm, g_fm, g_ov)

    if best_tuple:
        (score, ft, ff, g_pp, g_cm, g_fm, g_ov) = best_tuple
        final_stats = base_stats.copy()
        final_stats["Fever Time"] += ft * GEM_SCALE_FEVER
        final_stats["Fever Fill Rate"] += ff * GEM_SCALE_FEVER

        final_stats["Perfect Points"] += g_pp * GEM_SCALE_NORMAL
        final_stats["Combo Multiplier"] += g_cm * GEM_SCALE_NORMAL
        final_stats["Fever Multiplier"] += g_fm * GEM_SCALE_FEVER

        final_stats["Chill"] += g_pp * GEM_STAT_TO_ELEMENT_SCALE
        final_stats["Flow"] += g_cm * GEM_STAT_TO_ELEMENT_SCALE
        final_stats["Rush"] += g_fm * GEM_STAT_TO_ELEMENT_SCALE
        final_stats["Beat"] = base_stats.get("Beat", 0) + (
            ft * GEM_STAT_TO_ELEMENT_SCALE
        )
        final_stats["Vibe"] = base_stats.get("Vibe", 0) + (
            ff * GEM_STAT_TO_ELEMENT_SCALE
        )

        if selected_color in final_stats:
            final_stats[selected_color] += g_ov * ELEMENTAL_GEM_SCALE

        gem_counts = {
            "Perfect Points": g_pp,
            "Combo Multiplier": g_cm,
            "Fever Multiplier": g_fm,
            "Element Overflow": g_ov,
        }
        return {
            "Score": score,
            "FT": ft,
            "FF": ff,
            "GemCounts": gem_counts,
            "Stats": final_stats,
            "Selected Element": selected_color,
        }

    return {}


def solve_coevolution_genetic(
    cfg,
    base_stats_fixed,
    paths,
    calc_song,
    ref_arrays,
    all_gears,
    all_minis,
    gears_by_name,
    minis_by_name,
    optimize_gear=True,
    optimize_minis=True,
    fixed_gear=None,
    fixed_minis=None,
    ga_depth=75,
    db_seed=None,
    ga_settings=None,
    status_cb=None,
    executor=None,
    known_loadouts=None,
):
    # Caches are now cleared in process_song_task, but clearing here is safe redundancy.
    GEM_SOLVER_CACHE.clear()
    FG_CACHE.clear()
    FEVER_TIMELINE_CACHE.clear()

    print("\n=== STARTING GENETIC ALGORITHM SOLVER ===")
    print(f"Configuration: GearOptimization={optimize_gear}, MiniOptimization={optimize_minis}")

    ga_settings = ga_settings or GASettings.from_cfg(cfg)

    p_color = calc_song["metadata"].get("Primary Color", "Rush")
    selected_color = p_color

    mini_pool = [m for m in all_minis if m.get(p_color, 0) > 0]
    if not mini_pool:
        print("No valid minis found (Primary Color check).")
        return None, [], []

    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gear_pool = {s: [] for s in slots}
    for g in all_gears:
        if g["type"] in gear_pool:
            gear_pool[g["type"]].append(g)

    # Apply dominance pruning per slot to remove strictly inferior gear.
    total_before = sum(len(gear_pool[s]) for s in slots)
    for s in slots:
        gear_pool[s] = prune_dominated_gear(gear_pool[s])
    total_after = sum(len(gear_pool[s]) for s in slots)
    if total_before > total_after:
        print(f"[Dominance Pruning] Removed {total_before - total_after} dominated gear items.")

    cfg_data = {
        "selected_color": selected_color,
        "user_ft": safe_int(cfg.get("UserInputStatsGems", "fever_time", fallback=0)),
        "user_ff": safe_int(cfg.get("UserInputStatsGems", "fever_fill", fallback=0)),
        "user_pp": safe_int(cfg.get("UserInputStatsGems", "perfect_points", fallback=0)),
        "user_cm": safe_int(
            cfg.get("UserInputStatsGems", "combo_multiplier", fallback=0)
        ),
        "user_fm": safe_int(
            cfg.get("UserInputStatsGems", "fever_multiplier", fallback=0)
        ),
        "static_elem_input": safe_int(
            cfg.get("ElementalGems", selected_color, fallback=0)
        ),
    }

    # --- MEMETIC GA PARAMETERS (configurable from [IterationEngine]) ---
    if ga_settings.memetic_elites > 0 and ga_settings.memetic_steps > 0:
        print(
            f"[Memetic GA] Enabled: elites={ga_settings.memetic_elites}, "
            f"steps={ga_settings.memetic_steps}, top_gear={ga_settings.memetic_top_gear}, "
            f"top_minis={ga_settings.memetic_top_minis}"
        )
    else:
        print("[Memetic GA] Disabled (elites or steps <= 0).")

    def score_candidate(x):
        return (
            x.get(p_color, 0) * 3
            + x.get("Perfect Points", 0) * 2
            + x.get("Combo Multiplier", 0) * 2
            + x.get("Fever Multiplier", 0) * 2
        )

    gear_rank_max = 10  # keep gear sweep tight to avoid huge branching
    mini_rank_max = 40  # widen minis to escape local minima
    gear_rank_cache = {
        s: sorted(gear_pool[s], key=score_candidate, reverse=True)[:gear_rank_max]
        for s in slots
    }
    mini_rank_cache = sorted(mini_pool, key=score_candidate, reverse=True)[
        :mini_rank_max
    ]

    def genome_key(genome):
        # Helper to extract name from dict or string
        def get_name(item):
            if isinstance(item, dict):
                return item.get("Name", "")
            return str(item) if item else ""
        
        # Gear (first 6 slots): order matters because slots are positional.
        gear_names = tuple(get_name(item) for item in genome[:6])
        # Minis (last 3 slots): order-invariant - only the set/multiset matters.
        # Sorting canonicalizes permutations so [A,B,C] and [C,B,A] share a key.
        mini_names = tuple(sorted(get_name(item) for item in genome[6:]))
        return gear_names + mini_names

    evaluation_cache = {}
    cache_hits_in_run = 0

    def check_persistent_cache(genome):
        if known_loadouts:
            gear_part = genome[:6]
            mini_part = genome[6:]
            h = get_loadout_hash(gear_part, mini_part)
            if h in known_loadouts:
                entry = known_loadouts[h]

                # DB rows are stored as (score, fg_score, force_data); fall back gracefully
                score = fg_score = force_data = None
                if isinstance(entry, dict):
                    score = entry.get("score")
                    fg_score = entry.get("fg_score")
                    force_data = entry.get("force_data") or entry.get("force_details")
                elif isinstance(entry, (list, tuple)):
                    if len(entry) >= 2:
                        score, fg_score = entry[0], entry[1]
                    if len(entry) >= 3:
                        force_data = entry[2]
                else:
                    # Unknown shape; skip cache usage rather than crashing
                    return None

                if score is None or fg_score is None:
                    return None

                return {
                    "Score": score,
                    "FG_Score": fg_score,
                    "Genome": genome,
                    "Gear": gear_part,
                    "Minis": mini_part,
                    "MiniNames": [
                        m.get("Name", "") if isinstance(m, dict) else str(m) for m in mini_part
                    ],
                    "Data": {
                        "Score": score,
                        "_cached_db": True,
                        "ForceDetails": force_data,
                    },
                    "_cached": True,  # Flag so we force a full re-eval when polishing
                }
        return None

    def evaluate_genome_local(genome):
        nonlocal cache_hits_in_run
        k = genome_key(genome)
        if k in evaluation_cache:
            return evaluation_cache[k]
            
        cached_res = check_persistent_cache(genome)
        if cached_res:
            evaluation_cache[k] = cached_res
            cache_hits_in_run += 1
            return cached_res

        res = worker_coevolution_evaluate(
            (genome, base_stats_fixed, cfg_data, calc_song, ref_arrays)
        )
        evaluation_cache[k] = res
        return res

    def create_random_genome():
        genome = []
        if optimize_gear:
            for s in slots:
                genome.append(random.choice(gear_pool[s]) if gear_pool[s] else {})
        else:
            genome.extend(fixed_gear)

        if optimize_minis:
            if len(mini_pool) >= 3:
                genome.extend(random.sample(mini_pool, 3))
            else:
                genome.extend(random.sample(mini_pool, len(mini_pool)))
                while len(genome) < 9:
                    genome.append({})
        else:
            genome.extend(fixed_minis)
        return genome

    def create_heuristic_genome():
        genome = []
        if optimize_gear:
            for s in slots:
                candidates = gear_rank_cache.get(s, [])
                genome.append(random.choice(candidates[:5]) if candidates else {})
        else:
            genome.extend(fixed_gear)

        if optimize_minis:
            if len(mini_rank_cache) >= 3:
                genome.extend(random.sample(mini_rank_cache[:10], 3))
            else:
                genome.extend(random.sample(mini_pool, 3))
        else:
            genome.extend(fixed_minis)
        return genome

    def reconstruct_genome_from_db_list(db_list):
        """Rebuilds full stats from just the names in the DB."""
        r_genome = []
        for i in range(6):
            name = db_list[i] if i < len(db_list) else ""
            if name in gears_by_name:
                r_genome.append(gears_by_name[name])
            else:
                r_genome.append({"Name": "(Empty)", "type": slots[i]})
        for i in range(6, 9):
            if i < len(db_list):
                name = db_list[i]
                if name in minis_by_name:
                    r_genome.append(minis_by_name[name])
                else:
                    r_genome.append({"Name": "(Empty)", "type": "Mini"})
            else:
                r_genome.append({"Name": "(Empty)", "type": "Mini"})
        return r_genome

    def build_seed_list_from_record(record):
        """
        Normalize any stored record into a compact list of names for seeding.
        Handles both dict format (with 'Name' key) and plain string names.
        Priority: legacy loadout -> gear + minis.
        """
        if not record:
            return None
        
        def extract_name(item):
            """Extract name from either a dict or string."""
            if isinstance(item, dict):
                return item.get("Name", "")
            return str(item) if item else ""
        
        if "loadout" in record:
            load = record.get("loadout") or []
            if isinstance(load, list):
                return [extract_name(item) for item in load]
        
        gear_items = record.get("gear") or []
        mini_items = record.get("minis") or []
        
        if gear_items or mini_items:
            gear_names = [extract_name(g) for g in gear_items]
            mini_names = [extract_name(m) for m in mini_items]
            return gear_names + mini_names
        return None

    def mutate_genome_once(genome):
        """Soft mutation around a seed genome for DB seeding."""
        g = list(genome)
        mutate_idx = random.randint(0, 8)

        if mutate_idx < 6 and optimize_gear:
            slot_type = slots[mutate_idx]
            if gear_pool[slot_type]:
                g[mutate_idx] = random.choice(gear_pool[slot_type])
        elif mutate_idx >= 6 and optimize_minis:
            # Extract current mini names, handling both dict and string formats
            current_mini_names = set()
            for m in g[6:]:
                if isinstance(m, dict):
                    current_mini_names.add(m.get("Name", ""))
                elif m:
                    current_mini_names.add(str(m))
            candidates = [m for m in mini_pool if m["Name"] not in current_mini_names]
            if candidates:
                g[mutate_idx] = random.choice(candidates)

        return g

    def build_initial_population():
        population = []
        seed_list = build_seed_list_from_record(db_seed)
        if seed_list and random.random() < ga_settings.db_seed_prob:
            try:
                print(
                    f" >> [Evolution] Injecting previous best (Score: {db_seed.get('score', 0)})"
                )
                seed_genome = reconstruct_genome_from_db_list(seed_list)
                population.append(seed_genome[:])
                population.append(mutate_genome_once(seed_genome))
            except Exception as e:
                print(f" >> [Evolution] Failed to inject seed: {e}")
        elif seed_list:
            print(" >> [Evolution] Skipping DB seed this run (probability gate).")

        if fixed_gear and fixed_minis:
            seed_genome = fixed_gear + fixed_minis
        for _ in range(ga_settings.fixed_seed_copies):
                population.append(seed_genome[:])

        for _ in range(10):
            population.append(create_heuristic_genome())

        while len(population) < GA_POPULATION_SIZE:
            population.append(create_random_genome())
        return population

    def run_local_search(start_genome, max_steps, top_k_gear, top_k_minis, is_polishing=False):
        """
        Unified local search logic for both Memetic Search and Polishing.
        Iteratively improves the genome by checking neighbors in ranked lists.
        """
        best_genome = list(start_genome)
        best_result = evaluate_genome_local(best_genome)
        best_score = best_result["Score"]

        # Pre-trim candidate lists
        local_gear_rank = {
            s: gear_rank_cache.get(s, [])[:top_k_gear] for s in slots
        }
        local_mini_rank = mini_rank_cache[:top_k_minis]

        steps = 0
        # Polishing runs until no improvement (or very high limit), Memetic runs fixed steps
        limit = 999999 if is_polishing else max_steps

        while steps < limit:
            improved = False

            # Gear neighbourhood
            if optimize_gear:
                for idx, slot in enumerate(slots):
                    curr_item = best_genome[idx]
                    current_name = curr_item.get("Name") if isinstance(curr_item, dict) else str(curr_item) if curr_item else ""
                    for cand in local_gear_rank.get(slot, []):
                        if cand.get("Name") == current_name:
                            continue
                        trial = best_genome[:]
                        trial[idx] = cand
                        trial_res = evaluate_genome_local(trial)
                        if trial_res["Score"] > best_score:
                            best_score = trial_res["Score"]
                            best_result = trial_res
                            best_genome = trial
                            improved = True
                            steps += 1
                            break
                    if improved or (not is_polishing and steps >= limit):
                        break

            if not is_polishing and steps >= limit:
                break

            # Mini neighbourhood
            if (not improved or is_polishing) and optimize_minis:
                # Extract existing mini names, handling both dict and string formats
                existing = set()
                for m in best_genome[6:]:
                    if isinstance(m, dict):
                        existing.add(m.get("Name", ""))
                    elif m:
                        existing.add(str(m))
                for idx in range(6, 9):
                    curr_item = best_genome[idx]
                    curr_name = curr_item.get("Name") if isinstance(curr_item, dict) else str(curr_item) if curr_item else ""
                    for cand in local_mini_rank:
                        c_name = cand.get("Name")
                        if c_name == curr_name:
                            continue
                        if c_name in existing - {curr_name}:
                            continue
                        trial = best_genome[:]
                        trial[idx] = cand
                        trial_res = evaluate_genome_local(trial)
                        if trial_res["Score"] > best_score:
                            best_score = trial_res["Score"]
                            best_result = trial_res
                            best_genome = trial
                            improved = True
                            steps += 1
                            break
                    if improved or (not is_polishing and steps >= limit):
                        break

            if not improved:
                break

        return best_result, best_genome

    def polish_best_genome(best_genome):
        """Local sweep on top candidates per slot/mini to escape near-misses."""
        top_k_gear = 8
        top_k_minis = min(25, len(mini_rank_cache))
        return run_local_search(best_genome, 0, top_k_gear, top_k_minis, is_polishing=True)

    # --- MEMETIC LOCAL SEARCH (lightweight) ---
    def memetic_local_search(start_genome, max_steps, top_k_gear, top_k_minis):
        """
        Lightweight local search around a genome.
        """
        if max_steps <= 0:
            res = evaluate_genome_local(start_genome)
            return res # Return just result dict to match original signature expectation if needed, 
                       # but original code expected just the result dict.
                       # run_local_search returns (result, genome).
        
        res, _ = run_local_search(start_genome, max_steps, top_k_gear, top_k_minis, is_polishing=False)
        return res

    num_runs = ga_settings.multi_start
    gens_per_run = max(1, (ga_depth + num_runs - 1) // num_runs)
    print(f"Multi-start runs: {num_runs} (generations per run: {gens_per_run})")

    best_global_score = -1
    best_global_genome = []
    best_global_data = {}

    # Read Deep Mining config
    if ga_settings.deep_mining_enabled:
        print(" >> [Deep Mining] Enabled: Will extend search based on cache hits.")
    else:
        print(" >> [Deep Mining] Disabled: Fixed generation count.")

    for run_idx in range(num_runs):
        print(f"\n--- GA Run {run_idx + 1}/{num_runs} ---")
        if status_cb:
            status_cb(f"Run {run_idx + 1}/{num_runs} starting")
        population = build_initial_population()
        last_improvement_gen = 0
        stagnation_limit = max(8, gens_per_run // 2)
        mutation_rate = GA_MUTATION_RATE
        
        # Dynamic generation limit based on cache hits
        current_run_gens = gens_per_run
        cache_hits_in_run = 0 # Reset for each run
        generation = 0
        
        while generation < current_run_gens:
            generation += 1
            
            # Initialize current_mutation_rate for the first generation
            if generation == 1:
                current_mutation_rate = mutation_rate
            
            key_to_genome = {}
            pending_keys = []
            tasks = []
            for genome in population:
                k = genome_key(genome)
                if k in key_to_genome:
                    continue
                key_to_genome[k] = genome
                if k not in evaluation_cache:
                    pending_keys.append(k)
                    tasks.append((genome, base_stats_fixed, cfg_data, calc_song, ref_arrays))

            if pending_keys:
                # Use evaluate_genome_local logic for pending keys to ensure cache hits are counted
                # and known_loadouts are checked.
                # The previous logic bypassed evaluate_genome_local and went straight to worker_coevolution_evaluate
                # or executor.map, missing the persistent cache check for the initial population or bulk evals.
                
                # We need to integrate the persistent cache check into the bulk evaluation flow.
                # Or simply iterate and call evaluate_genome_local (which handles caching).
                # But evaluate_genome_local is designed for single calls.
                
                # Let's split pending_keys into "cached in DB" and "needs calculation".
                
                keys_to_calc = []
                tasks_to_calc = []
                
                for k, genome, task_payload in zip(pending_keys, [key_to_genome[k] for k in pending_keys], tasks):
                    # Check persistent cache first
                    cached_res = check_persistent_cache(genome)
                    if cached_res:
                        evaluation_cache[k] = cached_res
                        cache_hits_in_run += 1
                    else:
                        keys_to_calc.append(k)
                        tasks_to_calc.append(task_payload)

                if keys_to_calc:
                    if executor:
                        worker_count = getattr(executor, "_max_workers", None) or (
                            os.cpu_count() or 1
                        )
                        chunk = max(1, len(tasks_to_calc) // (worker_count * 4))
                        for k, res in zip(
                            keys_to_calc,
                            executor.map(
                                worker_coevolution_evaluate, tasks_to_calc, chunksize=chunk
                            ),
                        ):
                            evaluation_cache[k] = res
                    else:
                        for k, payload in zip(keys_to_calc, tasks_to_calc):
                            evaluation_cache[k] = worker_coevolution_evaluate(payload)

            results = [evaluation_cache[genome_key(g)] for g in population]
            results.sort(key=lambda x: x["Score"], reverse=True)

            def consider_candidate(cand):
                nonlocal best_global_score, best_global_genome, best_global_data
                cand_score = cand["Score"]
                cand_genome = cand["Genome"]
                cand_data = cand["Data"]
                best_key = genome_key(best_global_genome) if best_global_genome else None
                cand_key = genome_key(cand_genome)

                if (cand_score > best_global_score) or (
                    cand_score == best_global_score and cand_key != best_key
                ):
                    best_global_score = cand_score
                    best_global_genome = cand_genome
                    best_global_data = cand_data
                    return True
                return False

            promoted = consider_candidate(results[0])

            if promoted:
                m_names = results[0]["MiniNames"]
                print(
                    f"  >> Gen {generation} (Run {run_idx + 1}): New Best {best_global_score} (Minis: {m_names})"
                )
                if status_cb:
                    status_cb(
                        f"Run {run_idx + 1}/{num_runs} Gen {generation}: New Best {best_global_score}"
                    )
                last_improvement_gen = generation
                mutation_rate = GA_MUTATION_RATE
            else:
                if generation % 10 == 0:
                    print(
                        f"  >> Gen {generation} (Run {run_idx + 1}): Best {results[0]['Score']}"
                    )
                    if status_cb:
                        status_cb(
                            f"Run {run_idx + 1}/{num_runs} Gen {generation}: Best {results[0]['Score']}"
                        )

            # --- MEMETIC GA STEP: local search on top elites ---
            if ga_settings.memetic_elites > 0 and ga_settings.memetic_steps > 0:
                elite_count = min(ga_settings.memetic_elites, len(results))
                for e_idx in range(elite_count):
                    base_res = results[e_idx]
                    improved_res = memetic_local_search(
                        base_res["Genome"],
                        ga_settings.memetic_steps,
                        ga_settings.memetic_top_gear,
                        ga_settings.memetic_top_minis,
                    )
                    if improved_res["Score"] > base_res["Score"]:
                        results[e_idx] = improved_res
                        # Feed improved candidate back into global tracking
                        if consider_candidate(improved_res):
                            m_names = improved_res["MiniNames"]
                            print(
                                f"  >> [Memetic] Gen {generation} "
                                f"(Run {run_idx + 1}): New Best {best_global_score} "
                                f"(Minis: {m_names})"
                            )
                            if status_cb:
                                status_cb(
                                    f"Run {run_idx + 1}/{num_runs} Gen {generation} "
                                    f"Memetic: New Best {best_global_score}"
                                )
                            last_improvement_gen = generation
                            mutation_rate = GA_MUTATION_RATE
                # resort after memetic improvements
                results.sort(key=lambda x: x["Score"], reverse=True)

            next_gen = [results[i]["Genome"] for i in range(GA_ELITISM)]

            while len(next_gen) < GA_POPULATION_SIZE:
                if random.random() < 0.18:
                    next_gen.append(create_random_genome())
                    continue

                p1 = random.choice(results[:50])["Genome"]
                p2 = random.choice(results[:50])["Genome"]

                child = []
                L = min(len(p1), len(p2))
                for i in range(L):
                    child.append(p1[i] if random.random() > 0.5 else p2[i])

                child_gear = child[:6]
                child_minis = child[6:]

                seen_names = set()
                unique_minis = []
                for m in child_minis:
                    name = m.get("Name", None) if isinstance(m, dict) else None
                    if name and name not in seen_names and name != "(Empty)":
                        unique_minis.append(m)
                        seen_names.add(name)

                if optimize_minis:
                    while len(unique_minis) < 3:
                        candidates = [m for m in mini_pool if m["Name"] not in seen_names]
                        if candidates:
                            new_m = random.choice(candidates)
                            unique_minis.append(new_m)
                            seen_names.add(new_m["Name"])
                        else:
                            break
                else:
                    # Shallow copy suffices; minis are read-only dicts.
                    unique_minis = list(fixed_minis)

                child = child_gear + unique_minis

                # Use current_mutation_rate instead of mutation_rate
                if random.random() < current_mutation_rate:
                    mutate_idx = random.randint(0, 8)
                    if mutate_idx < 6 and optimize_gear:
                        slot_type = slots[mutate_idx]
                        if gear_pool[slot_type]:
                            child[mutate_idx] = random.choice(gear_pool[slot_type])
                    elif mutate_idx >= 6 and optimize_minis:
                        current_mini_names = {
                            m.get("Name") for m in child[6:] if isinstance(m, dict)
                        }
                        candidates = [
                            m for m in mini_pool if m["Name"] not in current_mini_names
                        ]
                        if candidates:
                            child[mutate_idx] = random.choice(candidates)

                next_gen.append(child)

            population = next_gen
            next_gen = None  # Break reference to help GC

            # Update dynamic generation limit
            # "run longer about 1 gen for each hit"
            # We add the hits to the base limit.
            if ga_settings.deep_mining_enabled:
                current_run_gens = gens_per_run + cache_hits_in_run
            
            # "increase the exploration"
            # If we have many cache hits, we are in known territory. Increase mutation.
            # Base mutation is ~0.275. Max is 0.45.
            # If we have > 10% cache hits in the run, boost mutation.
            # Let's calculate a dynamic boost based on hit density.
            total_evals_so_far = generation * GA_POPULATION_SIZE
            hit_ratio = cache_hits_in_run / max(1, total_evals_so_far)
            
            # Boost mutation by up to 0.2 if hit ratio is high
            exploration_boost = min(0.2, hit_ratio * 0.5)
            current_mutation_rate = min(0.6, mutation_rate + exploration_boost) # Allow going slightly higher than normal max
            
            # Cap the extension to avoid infinite loops (e.g. max 5000 gens)
            if current_run_gens > 5000:
                current_run_gens = 5000

            if generation - last_improvement_gen >= stagnation_limit:
                mutation_rate = min(GA_MUTATION_RATE_MAX, mutation_rate + 0.08)
                print(
                    f"  >> Stagnation detected (Run {run_idx + 1}), mutation -> {current_mutation_rate:.3f} (Boost: {exploration_boost:.3f}), injecting diversity"
                )
                elites = [r["Genome"] for r in results[:GA_ELITISM]]
                population = elites[:]
                reinject_target = int(GA_POPULATION_SIZE * 0.4)
                while len(population) < reinject_target:
                    population.append(create_random_genome())
                while len(population) < GA_POPULATION_SIZE:
                    population.append(create_heuristic_genome())
                last_improvement_gen = generation
            
            # Use the boosted rate for the next generation's crossover loop
            # Note: mutation_rate variable tracks the base rate (stagnation adjusted), 
            # while current_mutation_rate includes the exploration boost.
            # We don't overwrite mutation_rate with current_mutation_rate to avoid runaway growth.
            pass

    if best_global_genome:
        polished_result, polished_genome = polish_best_genome(best_global_genome)
        
        # If result was cached, re-evaluate fully to get all details
        if polished_result.get("_cached"):
             polished_result = worker_coevolution_evaluate(
                (polished_genome, base_stats_fixed, cfg_data, calc_song, ref_arrays)
            )
            
        polished_score = polished_result["Score"]

        if polished_score > best_global_score:
            best_global_score = polished_score
            best_global_data = polished_result["Data"]
            best_global_genome = polished_genome

    best_gear = best_global_genome[:6] if best_global_genome else []
    best_minis = best_global_genome[6:] if best_global_genome else []

    # Return all unique evaluated loadouts from the cache
    all_evaluated = list(evaluation_cache.values())

    # Memory leak fix: Clear cache immediately after extraction
    # This prevents the cache from lingering until function exit
    evaluation_cache.clear()

    # Memory leak fix: Clear all generation-scoped data before returning
    population = None
    results = None
    key_to_genome = None
    pending_keys = None
    tasks = None

    return (
        best_global_data if best_global_data else None,
        best_gear,
        best_minis,
        None,
        [],
        [],
        all_evaluated,  # All unique loadouts evaluated by GA (capped before DB persistence)
    )


def process_song_task(args):
    """
    Run a single song end-to-end.
    Optionally spins a local worker pool to parallelize inner GA work.
    """
    # --- CRITICAL: Clear caches at start of task to prevent OOM in worker process ---
    # These globals persist in the worker process if not cleared, leading to memory leaks
    # especially when GA is skipped (Calculate-Only mode) but caches are still populated.
    GEM_SOLVER_CACHE.clear()
    FEVER_TIMELINE_CACHE.clear()
    FG_CACHE.clear()

    (
        fp,
        found_song_name,
        effective_difficulty,  # Difficulty determined from file header or folder path
        cfg_dict,
        paths,
        ref_arrays,
        all_gears,
        all_minis,
        gears_by_name,
        minis_by_name,
        use_evo_db,
        auto_buff,
        ga_depth,
        status_queue,
        parallel_workers,
    ) = args

    # Initialize variables at function start to avoid 'in locals()' pattern issues
    local_executor = None
    loadout_entries = None
    known_loadouts = None
    buf_content = ""  # Capture buffer content before closing

    # Optional local pool for single-song runs to saturate available cores.
    if parallel_workers:
        worker_count = min(parallel_workers, os.cpu_count() or 1)
        if worker_count > 1:
            local_executor = concurrent.futures.ProcessPoolExecutor(
                max_workers=worker_count,
                mp_context=multiprocessing.get_context("spawn"),
            )

    buf = StringIO()
    tee = Tee(sys.stdout, buf)
    redirect_ctx = contextlib.redirect_stdout(tee)
    redirect_ctx.__enter__()

    # Memory leak tracking: Log memory at start of song
    log_memory_usage(f"Start: {found_song_name}")

    try:
        best_data = None
        best_gear = []
        best_minis = []
        db_payload = None

        cfg = cfg_from_dict(cfg_dict)
        ga_settings = GASettings.from_cfg(cfg)

        # MetaFinder controls all optimizers collectively.
        meta_finder = cfg.getboolean("IterationEngine", "MetaFinder", fallback=False)
        enable_fever = enable_mini = enable_gear = bool(meta_finder)

        force_greats_mode = cfg.getboolean("IterationEngine", "ForceGreatsMode", fallback=False)
        force_greats_finder = cfg.getboolean("IterationEngine", "ForceGreatsFinder", fallback=False)
        # ForceGreatsMode must be enabled for ForceGreatsFinder to work
        if not force_greats_mode:
            force_greats_finder = False
        force_greats_config = load_force_greats_config(cfg)
        manual_force_greats = force_greats_mode and any(force_greats_config)

        song_data = read_song_file(fp)

        # OPTIMIZATION: store timestamps as NumPy array once per song
        song_timestamps_np = np.array(song_data["timestamps"], dtype=np.float64)

        calc_song = {
            "metadata": song_data["song_details"],
            "song_data": {"timestamps": song_timestamps_np},
        }
        meta_primary_color = calc_song["metadata"].get("Primary Color", "")
        meta_secondary_color = calc_song["metadata"].get("Secondary Color", "")

        # --- Auto Select Buff & Color Logic ---
        if auto_buff:
            p_col = calc_song["metadata"].get("Primary Color", "Rush")
            if not cfg.has_section("TeamContributionBuffConstant"):
                cfg.add_section("TeamContributionBuffConstant")
            cfg.set("TeamContributionBuffConstant", "TeamColor", p_col)
            cfg.set("TeamContributionBuffConstant", "TeamBuff", "T5")
            print(f"[Auto-Config] Set Team Buff: T5 | Team Color: {p_col}")

        fixed_stats = get_fixed_stats(cfg)

        # Load Current Config for Seeding / Fallback
        current_gear_stats, current_gear_list = get_config_gear_stats(
            cfg, paths, gears_by_name
        )
        current_mini_stats, current_mini_list = get_config_mini_stats(
            cfg, paths, minis_by_name
        )

        # --- DB KEY MODIFICATION ---
        # The song name from the file header already includes difficulty suffix like "(Hard)" or "(Easy)"
        # Normal difficulty songs have no suffix. Use song name directly as DB key.
        db_key = found_song_name

        # Only seed GA if UseEvolutionDB=TRUE
        db_seed = None
        prev_record = None
        if use_evo_db:
            best_loadouts = get_best_loadouts(found_song_name, limit=1, gears_by_name=gears_by_name, minis_by_name=minis_by_name)
            if best_loadouts:
                prev_record = best_loadouts[0]
                db_seed = prev_record

        if prev_record:
            print(f"[DB] Found previous best: {prev_record.get('score', 0)}")

        attempt_lifetime_prev = 0
        prev_attempts_first = 0
        if prev_record and "details" in prev_record:
            attempt_lifetime_prev = prev_record["details"].get("attempt_lifetime", 0)
            prev_attempts_first = prev_record["details"].get("attempts_first", 0)
            
        attempt_lifetime = attempt_lifetime_prev + 1

        def emit(msg):
            if status_queue:
                try:
                    status_queue.put(f"[{found_song_name}] {msg}")
                except Exception:
                    pass

        emit("START")

        # Fetch known loadouts for persistent caching
        known_loadouts = {}
        if use_evo_db:
            try:
                conn = get_db_connection()
                cursor = conn.execute(
                    """SELECT loadout_hash, score, fg_score, force_details_json
                       FROM loadouts
                       WHERE song_name = ?
                       ORDER BY score DESC
                       LIMIT ?""",
                    (found_song_name, LOADOUTS_PER_SONG_LIMIT),
                )
                for row in cursor:
                    force_blob = row["force_details_json"]
                    force_data = None
                    if force_blob:
                        try:
                            force_data = json.loads(force_blob)
                        except Exception as exc:
                            WARN_ONCE.warn(
                                "force-loadout-json",
                                f"Invalid force JSON for {row.get('loadout_hash')}: {exc}",
                            )
                            force_data = None
                    known_loadouts[row["loadout_hash"]] = (
                        row["score"],
                        row["fg_score"],
                        force_data,
                    )
                # Memory leak fix #2: Checkpoint WAL before closing connection
                # Prevents WAL file growth (5-50 MB per 1000 songs)
                try:
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                    conn.execute("PRAGMA optimize")
                except Exception as e:
                    # CRITICAL FIX: Log checkpoint failures (was silently suppressed)
                    logging.warning(f"[DB] WAL checkpoint/optimize failed: {e}")
                conn.close()
            except Exception as e:
                print(f"[DB] Error fetching known loadouts: {e}")

        # --- LOGIC BRANCHING BASED ON FINDERS ---
        if enable_gear or enable_mini:
            # Run Genetic Algorithm (now memetic-enhanced)
            (
                best_data,
                best_gear,
                best_minis,
                _,
                _,
                _,
                all_evaluated,  # All unique loadouts from GA
            ) = solve_coevolution_genetic(
                cfg,
                fixed_stats,
                paths,
                calc_song,
                ref_arrays,
                all_gears,
                all_minis,
                gears_by_name,
                minis_by_name,
                optimize_gear=enable_gear,
                optimize_minis=enable_mini,
                fixed_gear=current_gear_list,
                fixed_minis=current_mini_list,
                ga_depth=ga_depth,
                db_seed=db_seed,
                ga_settings=ga_settings,
                status_cb=lambda m: emit(m),
                executor=local_executor,
                known_loadouts=known_loadouts,
            )

            # Memory leak fix: Clear known_loadouts after GA completes
            # This dict now caps at the per-song loadout limit (small footprint)
            if known_loadouts:
                known_loadouts.clear()

        else:
            # Run Gem Solver only (enable_fever) or Calculate-Only Mode (nothing enabled)
            all_evaluated = []  # No GA, so no evaluated loadouts
            if not enable_fever:
                print("[Calculate-Only Mode] MetaFinder disabled - calculating score with current config...")
            
            # Common logic: combine fixed_stats + gear_stats + mini_stats
            combined_stats = fixed_stats.copy()
            for k, v in current_gear_stats.items():
                combined_stats[k] = combined_stats.get(k, 0) + v
            for k, v in current_mini_stats.items():
                combined_stats[k] = combined_stats.get(k, 0) + v

            best_data = solve_best_fever_combination(
                cfg,
                combined_stats,
                calc_song,
                ref_arrays,
                silent=enable_fever,  # Silent if enable_fever, verbose otherwise
                skip_optimizer=not enable_fever,  # Skip optimizer if no finders enabled
            )
            best_gear = current_gear_list
            best_minis = current_mini_list

        # Cap GA candidates for downstream processing to the DB loadout limit
        ga_candidates = all_evaluated or []
        if ga_candidates and len(ga_candidates) > LOADOUTS_PER_SONG_LIMIT:
            ga_candidates = sorted(
                ga_candidates,
                key=lambda r: r.get("Score", 0),
                reverse=True,
            )[:LOADOUTS_PER_SONG_LIMIT]

        def build_details(data_dict):
            if not data_dict:
                return {}
            return {
                "FT": data_dict.get("FT", 0),
                "FF": data_dict.get("FF", 0),
                "GemCounts": data_dict.get("GemCounts", {}),
                "Stats": data_dict.get("Stats", {}),
                "SelectedElement": data_dict.get("Selected Element", ""),
                "PrimaryColor": meta_primary_color,
                "SecondaryColor": meta_secondary_color,
                "Difficulty": effective_difficulty,  # Use the effective difficulty
                "ForceGreats": data_dict.get("ForceGreats", {}),
            }

        # --- APPLY FORCE GREATS TO ALL EVALUATED LOADOUTS ---
        fg_variants = []
        if manual_force_greats or force_greats_finder:
            manual_counts = (
                force_greats_config if (manual_force_greats and not force_greats_finder) else []
            )
            # Build a union of unique loadouts: DB (capped) + top GA candidates
            loadout_entries = {}

            def _names_list(items):
                names = []
                for it in items or []:
                    if isinstance(it, dict):
                        names.append(it.get("Name", ""))
                    else:
                        names.append(str(it) if it else "")
                return names

            def _add_entry(gear_items, mini_items, score_val, details_obj, fg_score_val=0, force_obj=None, eval_data=None):
                h = get_loadout_hash(gear_items, mini_items)
                existing = loadout_entries.get(h)
                # Prefer the entry with actual eval_data (from GA) over DB-only details
                if existing:
                    if existing.get("eval_data") is None and eval_data is not None:
                        pass
                    elif existing.get("score", 0) >= (score_val or 0):
                        return
                loadout_entries[h] = {
                    "gear": gear_items,
                    "minis": mini_items,
                    "score": score_val or 0,
                    "details": details_obj or {},
                    "fg_score": fg_score_val or 0,
                    "force": force_obj,
                    "eval_data": eval_data,
                }

            # DB loadouts (up to the configured limit) for this song
            db_loadouts_full = []
            if use_evo_db:
                try:
                    db_loadouts_full = get_best_loadouts(found_song_name, limit=LOADOUTS_PER_SONG_LIMIT, gears_by_name=gears_by_name, minis_by_name=minis_by_name)
                except Exception:
                    db_loadouts_full = []
            for rec in db_loadouts_full or []:
                _add_entry(
                    rec.get("gear", []),
                    rec.get("minis", []),
                    rec.get("score", 0),
                    rec.get("details", {}),
                    rec.get("fg_score", 0),
                    rec.get("force"),
                    None,
                )

            # Current GA evaluated loadouts (only add if not already present)
            for eval_result in ga_candidates:
                eval_data = eval_result.get("Data")
                eval_score = eval_result.get("Score", 0)
                gear_items = eval_result.get("Gear", [])
                mini_items = eval_result.get("Minis", [])
                eval_details = build_details(eval_data) if eval_data else {}
                _add_entry(
                    gear_items,
                    mini_items,
                    eval_score,
                    eval_details,
                    0,
                    None,
                    eval_data,
                )

            # FG processing budget: number of DB loadouts (dynamic). Skip (reuse) does NOT consume budget.
            unique_stats_seen = set()
            max_fg_compute = len(db_loadouts_full) if db_loadouts_full else len(loadout_entries)
            computed = 0
            print(f"[ForceGreats] Processing {len(loadout_entries)} unique loadouts (DB + GA)...")
            for entry in loadout_entries.values():
                if computed >= max_fg_compute:
                    break

                cached_force = entry.get("force")
                if cached_force and (cached_force.get("score") or entry.get("fg_score")):
                    fg_variants.append({
                        "data": cached_force.get("details", {}),
                        "gear": entry.get("gear", []),
                        "minis": entry.get("minis", []),
                        "score": cached_force.get("score", entry.get("fg_score", 0)),
                    })
                    # Skipped entries do not consume compute budget
                    continue

                eval_data = entry.get("eval_data")
                if not eval_data:
                    det = entry.get("details") or {}
                    stats = det.get("Stats") or {}
                    if not stats:
                        continue
                    eval_data = {
                        "Stats": stats,
                        "Selected Element": det.get("SelectedElement") or det.get("Selected Element") or meta_primary_color,
                        "FT": det.get("FT", 0),
                        "FF": det.get("FF", 0),
                        "GemCounts": det.get("GemCounts", {}),
                    }

                stats = eval_data.get("Stats", {})
                sel_color = eval_data.get("Selected Element", meta_primary_color)
                sig = stats_signature(stats, calc_song, sel_color)
                unique_stats_seen.add(sig)

                fg_variant = apply_force_greats_to_result(
                    eval_data,
                    calc_song,
                    ref_arrays,
                    manual_counts=manual_counts,
                    use_finder=force_greats_finder,
                )
                computed += 1
                if fg_variant:
                    fg_variants.append({
                        "data": fg_variant,
                        "gear": entry.get("gear", []),
                        "minis": entry.get("minis", []),
                        "score": fg_variant.get("Score", 0),
                    })
                    entry["force"] = {
                        "score": fg_variant.get("Score", 0),
                        "gear": _names_list(entry.get("gear", [])),
                        "minis": _names_list(entry.get("minis", [])),
                        "details": build_details(fg_variant),
                    }
                    entry["fg_score"] = fg_variant.get("Score", 0)
            print(f"[ForceGreats] {len(unique_stats_seen)} unique stat signatures, {len(fg_variants)} FG variants generated (computed {computed}, budget {max_fg_compute})")

        # --- REPORTING & DB UPDATE (payload only; saved by coordinator) ---
        if best_data:
            score = best_data.get("Score", 0)
            print("-" * 30)
            print(f"FINAL CONFIGURATION FOR: {found_song_name}")
            print(f"Total Score: {score}")

            prev_score = prev_record.get("score") if prev_record else None
            prev_second = None
            is_first = prev_record is None
            is_better = (prev_score is None) or (score > prev_score)

            def extract_names(record):
                """Extract names from record, handling both dict and string formats."""
                def get_name(item):
                    if isinstance(item, dict):
                        return item.get("Name", "")
                    return str(item) if item else ""
                
                gear_items = record.get("gear") if record else []
                minis_items = record.get("minis") if record else []
                loadout = record.get("loadout") if record else None
                if (not gear_items and not minis_items) and loadout:
                    gear_items = loadout[:6]
                    minis_items = loadout[6:9]
                
                gear_names = [get_name(g) for g in (gear_items or [])]
                minis_names = [get_name(m) for m in (minis_items or [])]
                return gear_names, minis_names

            best_gear_names = [g.get("Name") for g in best_gear]
            best_mini_names = [m.get("Name") for m in best_minis]
            best_details = build_details(best_data)

            attempts_first = (
                1
                if is_first or is_better
                else (prev_attempts_first + 1 if prev_attempts_first else 1)
            )

            def attach_attempt_meta(details):
                """Copy details dict and tag attempt counters for DB persistence."""
                merged = dict(details or {})
                merged["attempt_lifetime"] = attempt_lifetime
                merged["attempts_first"] = attempts_first
                return merged

            # Build FG candidates from CURRENT RUN ONLY (not prev_record)
            # We always save the best FG from this run, regardless of whether it beats the old one.
            current_run_fg_candidates = []
            for fg_entry in fg_variants:
                fg_gear = fg_entry.get("gear", [])
                fg_minis = fg_entry.get("minis", [])
                fg_data = fg_entry.get("data", {})
                fg_gear_names = [g.get("Name") for g in fg_gear] if fg_gear else []
                fg_mini_names = [m.get("Name") for m in fg_minis] if fg_minis else []
                current_run_fg_candidates.append(
                    {
                        "score": fg_entry.get("score", 0),
                        "gear": fg_gear_names,
                        "minis": fg_mini_names,
                        "details": build_details(fg_data),
                    }
                )

            if is_first:
                print(
                    " >> NEW RECORD! (First entry for this song/context). "
                    "Saving to Evolution Database..."
                )
            elif is_better:
                print(
                    f" >> NEW RECORD! Previous: {prev_score} | New: {score} "
                    f"- Updating Evolution Database..."
                )
            else:
                print(f" >> No improvement over DB Record ({prev_score})")

            # Aggregate candidates (best + second from previous DB and current run) and pick top two.
            candidates = []

            if prev_record and prev_score is not None:
                prev_gear_names, prev_mini_names = extract_names(prev_record)
                candidates.append(
                    {
                        "score": prev_score,
                        "gear": prev_gear_names,
                        "minis": prev_mini_names,
                        "details": attach_attempt_meta(prev_record.get("details", {})),
                    }
                )

            candidates.append(
                {
                    "score": score,
                    "gear": best_gear_names,
                    "minis": best_mini_names,
                    "details": attach_attempt_meta(best_details),
                }
            )

            candidates = sorted(
                candidates, key=lambda c: c.get("score", -1), reverse=True
            )

            def _sig(cand):
                gear_key = tuple(cand.get("gear") or [])
                minis_key = tuple(cand.get("minis") or [])
                details = cand.get("details") or {}
                try:
                    details_key = json.dumps(details, sort_keys=True)
                except Exception:
                    details_key = str(details)
                return (gear_key, minis_key, details_key)

            top1 = candidates[0] if candidates else None

            updated_payload = {}
            updated_payload["attempt_lifetime"] = attempt_lifetime
            updated_payload["attempts_first"] = attempts_first
            if top1:
                updated_payload.update(
                    {
                        "score": top1["score"],
                        "gear": top1.get("gear", []),
                        "minis": top1.get("minis", []),
                        "details": attach_attempt_meta(top1.get("details", {})),
                    }
                )

            updated_payload.pop("second", None)

            # Always save the best FG from the CURRENT RUN
            # This ensures we always record the FG result from this GA's evaluated loadouts,
            # even if it doesn't beat the previous best FG score.
            if current_run_fg_candidates:
                current_run_fg_candidates = sorted(
                    current_run_fg_candidates, key=lambda c: c.get("score", -1), reverse=True
                )
                best_force = current_run_fg_candidates[0]
                fg_score_val = best_force.get("score", 0) or 0
                updated_payload["force"] = {
                    "score": best_force.get("score"),
                    "gear": best_force.get("gear", []),
                    "minis": best_force.get("minis", []),
                    "details": best_force.get("details", {}),
                }
            # If no FG candidates from current run, keep the old one from prev_record (if any)
            elif prev_record and prev_record.get("force"):
                updated_payload["force"] = prev_record.get("force")
                fg_score_val = (prev_record.get("force") or {}).get("score", 0) or 0
            else:
                updated_payload.pop("force", None)
                fg_score_val = 0

            updated_payload["fg_score"] = fg_score_val

            db_payload = updated_payload

            # --- Build persistence payloads: Top1, Top1 FG, capped GA candidates ---
            persist_entries = []

            def _names_list(items):
                names = []
                for it in items or []:
                    if isinstance(it, dict):
                        names.append(it.get("Name", ""))
                    else:
                        names.append(str(it) if it else "")
                return names

            def _append_entry(score_val, gear_items, mini_items, details_obj, fg_score_val=0, force_obj=None):
                # Tag attempts metadata so downstream displays (Best/Lifetime) can advance.
                details_with_meta = attach_attempt_meta(details_obj or {})
                persist_entries.append({
                    "score": score_val or 0,
                    "fg_score": fg_score_val or 0,
                    "gear": _names_list(gear_items),
                    "minis": _names_list(mini_items),
                    "details": details_with_meta,
                    "force": force_obj,
                })

            # Top 1 (base)
            _append_entry(
                db_payload.get("score", 0),
                db_payload.get("gear", []),
                db_payload.get("minis", []),
                db_payload.get("details", {}),
                db_payload.get("fg_score", 0),
                db_payload.get("force"),
            )

            # Top 1 FG (store as its own row)
            force_block = db_payload.get("force")
            if force_block:
                _append_entry(
                    force_block.get("score", 0),
                    force_block.get("gear", []),
                    force_block.get("minis", []),
                    force_block.get("details", {}),
                    force_block.get("score", 0),
                    force_block,
                )

            # GA candidates (capped to DB limit)
            if ga_candidates:
                for eval_result in ga_candidates:
                    eval_data = eval_result.get("Data") or {}
                    eval_score = eval_result.get("Score", 0)
                    eval_gear = eval_result.get("Gear", [])
                    eval_minis = eval_result.get("Minis", [])
                    eval_details = build_details(eval_data)
                    _append_entry(
                        eval_score,
                        eval_gear,
                        eval_minis,
                        eval_details,
                        0,
                        None,
                    )

            # Include DB+GA union entries (with updated FG) if available
            if "loadout_entries" in locals():
                for entry in loadout_entries.values():
                    _append_entry(
                        entry.get("score", 0),
                        entry.get("gear", []),
                        entry.get("minis", []),
                        entry.get("details", {}),
                        entry.get("fg_score", 0),
                        entry.get("force"),
                    )

            emit(f"DONE | Score={score}")

            if enable_gear:
                print("\n[Best Gear Loadout]")
                for g in best_gear:
                    print(f"{g.get('type')}: {g.get('Name')}")
            else:
                print("\n[Gear Loadout (Fixed)]")
                for g in current_gear_list:
                    print(f"{g.get('type')}: {g.get('Name')}")

            if enable_mini:
                print("\n[Best Mini Team]")
                for m in best_minis:
                    print(f"{m.get('Name', 'Unknown')}")
            else:
                print("\n[Mini Team (Fixed)]")
                for m in current_mini_list:
                    print(f"{m.get('Name', 'Unknown')}")

            if "GemCounts" in best_data:
                gem_counts = best_data["GemCounts"]
                sel_el = best_data.get("Selected Element", "Rush")
                print(f"\nGem Allocation -> Fever Time: {best_data.get('FT', 0)}")
                print(f"Gem Allocation -> Fever Fill: {best_data.get('FF', 0)}")
                print(
                    "Gem Allocation -> Fever Multiplier: "
                    f"{gem_counts.get('Fever Multiplier', 0)}"
                )
                print(
                    "Gem Allocation -> Combo Multiplier: "
                    f"{gem_counts.get('Combo Multiplier', 0)}"
                )
                print(
                    "Gem Allocation -> Perfect Points: "
                    f"{gem_counts.get('Perfect Points', 0)}"
                )
                print(
                    f"Gem Allocation -> {sel_el} (Overflow): "
                    f"{gem_counts.get('Element Overflow', 0)}"
                )

            if fg_variants:
                best_fg_entry = max(
                    fg_variants, key=lambda p: p.get("score", -1)
                )
                best_fg_variant = best_fg_entry.get("data", {})
                fg_meta = best_fg_variant.get("ForceGreats", {}) or {}
                best_fg_gear = best_fg_entry.get("gear", [])
                best_fg_minis = best_fg_entry.get("minis", [])
                fg_gear_names = [g.get("Name") for g in best_fg_gear] if best_fg_gear else []
                fg_mini_names = [m.get("Name") for m in best_fg_minis] if best_fg_minis else []
                print("\n[ForceGreats Optimizer]")
                print(
                    f"Base Score: {fg_meta.get('base_score', best_data.get('Score', 0))} | "
                    f"ForceGreat Score: {best_fg_entry.get('score', 0)}"
                )
                print(f"Best FG Gear: {fg_gear_names}")
                print(f"Best FG Minis: {fg_mini_names}")
                cfg_map = fg_meta.get("config", {})
                if cfg_map:
                    print(f"Config: {cfg_map}")

        # BUG FIX: Capture buffer content BEFORE finally block closes it
        buf_content = buf.getvalue() if buf else ""

        return {
            "song": found_song_name,
            "db_key": db_key,
            "db_payload": db_payload,
            "best_data": best_data,
            "best_gear": best_gear,
            "best_minis": best_minis,
            "persist_entries": persist_entries if best_data else [],
            "log": buf_content,
        }
    finally:
        # Memory leak tracking: Log before cleanup
        log_memory_usage(f"Before cleanup: {found_song_name}")

        if local_executor:
            local_executor.shutdown()
            local_executor = None  # Break reference

        # Prevent memory leak from unbounded cache growth across thousands of songs
        FEVER_TIMELINE_CACHE.clear()
        GEM_SOLVER_CACHE.clear()
        FG_CACHE.clear()

        # Memory leak fix: Clear local data structures explicitly
        # Using direct checks instead of 'in locals()' pattern (more reliable)
        if loadout_entries is not None:
            loadout_entries.clear()
        if known_loadouts is not None:
            known_loadouts.clear()

        # Memory leak fix: Close StringIO buffer explicitly
        # This buffer can hold 10-100MB of captured output per song
        if buf is not None:
            try:
                buf.close()
            except Exception as e:
                # Log buffer close failures (was silently suppressed)
                logging.debug(f"[StringIO] Failed to close buffer: {e}")

        # Force garbage collection (deterministic: every 5 songs for gen-2)
        # CRITICAL FIX: Use deterministic counter instead of random (was non-deterministic)
        global _SONG_GC_COUNTER
        _SONG_GC_COUNTER += 1
        if _SONG_GC_COUNTER % 5 == 0:  # Every 5 songs: full collection
            gc.collect(generation=2)
        else:  # Other songs: quick collection
            gc.collect(generation=0)

        # Memory leak tracking: Log after cleanup
        log_memory_usage(f"After cleanup: {found_song_name}")

        redirect_ctx.__exit__(None, None, None)

    # Should never reach here; fallback to avoid crashes
    return {
        "song": found_song_name,
        "db_key": found_song_name,
        "db_payload": None,
        "best_data": None,
        "best_gear": [],
        "best_minis": [],
        "log": buf_content,  # Use captured content instead of buf.getvalue()
    }


def safe_process_song_task(args):
    """
    Wrapper around process_song_task that never raises across process boundaries.
    Returns an error payload with traceback if anything escapes, to avoid crashing pools.
    """
    song_name = "Unknown"
    try:
        if isinstance(args, (list, tuple)) and len(args) > 1:
            song_name = args[1]
        return process_song_task(args)
    except Exception as exc:
        tb = traceback.format_exc()
        msg = f"[safe_process_song_task] {song_name} failed: {type(exc).__name__}: {exc}"
        try:
            logging.error(msg + "\n" + tb)
            print(msg)
        except Exception:
            pass
        return {
            "song": song_name,
            "_error": exc,
            "_trace": tb,
        }


# --- Main Execution ---
if __name__ == "__main__":
    multiprocessing.freeze_support()

    # BUG FIX: Validate status file path and show where it's writing
    print(f"[MetaFinder] Status file path: {STATUS_FILE}")
    try:
        # Test write to verify the path is accessible
        status_dir = os.path.dirname(STATUS_FILE)
        if not os.path.exists(status_dir):
            print(f"[MetaFinder] Creating status directory: {status_dir}")
        os.makedirs(status_dir, exist_ok=True)

        # Test write
        test_payload = {"test": True, "timestamp": time.time()}
        with open(STATUS_FILE + ".test", "w") as f:
            json.dump(test_payload, f)
        os.remove(STATUS_FILE + ".test")
        print(f"[MetaFinder] Status file path verified successfully")
    except Exception as e:
        print(f"[MetaFinder] WARNING: Cannot write to status file: {e}")
        print(f"[MetaFinder] Status updates will fail. Check path or set METAFINDER_STATUS_FILE env variable.")

    # Mark MetaFinder as online as soon as the main loop starts.
    write_metafinder_status("online", "MetaFinder process started")

    # Background heartbeat so the website can treat stale timestamps as offline
    _heartbeat_stop = threading.Event()

    def _heartbeat_loop():
        while not _heartbeat_stop.is_set():
            try:
                write_metafinder_status("online", "MetaFinder heartbeat")
            except Exception:
                pass
            # Sleep with interrupt support
            _heartbeat_stop.wait(60.0)

    try:
        threading.Thread(target=_heartbeat_loop, daemon=True).start()
    except Exception:
        # If heartbeat thread fails to start, we still continue the main loop.
        pass
    while True:
        loop_forever = False
        memory_guard_restart = False
        memory_resume_tracker = None
        start_time = time.time()
        
        # --- MEMORY LEAK FIX: Clear main process caches at start of each loop iteration ---
        # In LoopForever mode, these global caches can accumulate data across iterations.
        # Worker processes clear their own caches, but the main process must also clear them.
        FEVER_TIMELINE_CACHE.clear()
        GEM_SOLVER_CACHE.clear()
        FG_CACHE.clear()
        
        # Track manager/queue for cleanup in finally block
        manager = None
        status_queue = None
        status_thread = None
        
        try:
            cfg = configparser.ConfigParser()
            # Explicit UTF-8-SIG to avoid Windows default 'charmap' decoding issues
            cfg.read("config.ini", encoding="utf-8-sig")
            paths = load_paths_cache()
            set_memory_watchdog_limit(compute_memory_guard_limit(cfg))
            db_display_name = os.path.basename(get_evolution_db_path())
            discord_reporter.send_log(
                f"Gear Optimizer run started. DB file: {db_display_name}"
            )

            # --- DB LOAD (always, independent of UseEvolutionDB) ---
            init_db()

            # --- Configuration Granularity ---
            meta_finder = cfg.getboolean("IterationEngine", "MetaFinder", fallback=False)
            enable_fever = enable_mini = enable_gear = bool(meta_finder)
            force_greats_mode = cfg.getboolean("IterationEngine", "ForceGreatsMode", fallback=False)
            force_greats_finder = cfg.getboolean("IterationEngine", "ForceGreatsFinder", fallback=False)
            auto_buff = cfg.getboolean(
                "IterationEngine", "AutoSelectBuffAndColor", fallback=False
            )
            
            # Log ForceGreats configuration status
            if force_greats_mode:
                fg_status = "ForceGreatsFinder" if force_greats_finder else "Manual Config"
                print(f" >> [ForceGreats] Mode enabled ({fg_status})")
            ga_depth = safe_int(cfg.get("IterationEngine", "GA_SearchDepth", fallback=50))
            use_evo_db = cfg.getboolean(
                "IterationEngine", "UseEvolutionDB", fallback=True
            )
            loop_forever = cfg.getboolean(
                "IterationEngine", "LoopForever", fallback=False
            )
            eval_cpu_limit = safe_int(
                cfg.get("IterationEngine", "EvalCPUCores", fallback=0)
            )

            stats_path = paths.get("Stats", "")
            if not stats_path:
                stats_path = PATHS.stats_csv
            stats_table = read_table(stats_path)

            # --- CRITICAL FIX: PREVENT DB TAINTING ---
            # If any automation is active, FORCE manual gem inputs to 0 in memory.
            # This ensures the solver runs on a clean slate and the DB saves the "Pure" result.
            if enable_fever or enable_mini or enable_gear:
                print(" >> [Auto-Mode] Finders active: Ignoring manual [UserInputStatsGems] & [ElementalGems] to prevent database tainting.")

                if not cfg.has_section("UserInputStatsGems"):
                    cfg.add_section("UserInputStatsGems")
                cfg.set("UserInputStatsGems", "perfect_points", "0")
                cfg.set("UserInputStatsGems", "combo_multiplier", "0")
                cfg.set("UserInputStatsGems", "fever_multiplier", "0")
                cfg.set("UserInputStatsGems", "fever_fill", "0")
                cfg.set("UserInputStatsGems", "fever_time", "0")

                if not cfg.has_section("ElementalGems"):
                    cfg.add_section("ElementalGems")
                cfg.set("ElementalGems", "Chill", "0")
                cfg.set("ElementalGems", "Flow", "0")
                cfg.set("ElementalGems", "Rush", "0")
                cfg.set("ElementalGems", "Beat", "0")
                cfg.set("ElementalGems", "Vibe", "0")

            # Initialize variables at function scope to prevent NameError in cleanup paths
            # (CRITICAL FIX: Variables must be accessible in all code paths for cleanup)
            # BUG FIX: Explicitly initialize all variables that might persist across loop iterations
            future_map = None
            remaining_tasks = None
            completed_songs = None
            tasks = None

            # OPTIMIZATION: Pre-load References as NumPy arrays ONCE
            stat_names = [
                "Perfect Points",
                "Combo Multiplier",
                "Fever Multiplier",
                "Fever Fill Rate",
                "Fever Time",
            ]
            ref_arrays = {}
            for i, name in enumerate(stat_names):
                temp_list = []
                for v in range(TOTAL_ROWS + 1):
                    lookup_index = TOTAL_ROWS - v
                    try:
                        val = stats_table[lookup_index][i] if stats_table else 0
                    except Exception:
                        val = 0
                    temp_list.append(val)
                ref_arrays[name] = np.array(temp_list, dtype=np.float64)

            # OPTIMIZATION: Pre-load Gears and Minis ONCE
            all_gears = load_all_gears_list(paths)
            all_minis = load_all_minis_list(paths)
            gears_by_name = {g["Name"]: g for g in all_gears}
            minis_by_name = {m["Name"]: m for m in all_minis}

            diff = cfg.get("CalculateSong", "Difficulty", fallback="Hard")
            search_dir = paths.get(diff, SCRIPT_DIR)
            diff_lower = diff.strip().lower()
            filter_search = cfg.get("CalculateSong", "Song_Name", fallback="").strip().lower()

            def _parse_color_targets(raw_val):
                tokens = [
                    c.strip().lower()
                    for c in re.split(r"[,\|/]", raw_val or "")
                    if c and c.strip()
                ]
                is_all = not tokens or any(c in ("all", "any", "*") for c in tokens)
                return is_all, set() if is_all else set(tokens)

            target_primary_raw = cfg.get("CalculateSong", "TargetPrimary", fallback="")
            target_secondary_raw = cfg.get("CalculateSong", "TargetSecondary", fallback="")
            legacy_target_raw = cfg.get("CalculateSong", "TargetColor", fallback="")
            if not target_primary_raw and legacy_target_raw:
                target_primary_raw = legacy_target_raw
            if not target_secondary_raw:
                target_secondary_raw = "all"

            target_primary_all, target_primary_colors = _parse_color_targets(
                target_primary_raw
            )
            target_secondary_all, target_secondary_colors = _parse_color_targets(
                target_secondary_raw
            )
            resume_context = build_memory_guard_resume_context(
                diff_lower,
                filter_search,
                target_primary_all,
                target_primary_colors,
                target_secondary_all,
                target_secondary_colors,
            )

            diff_dirs = {}
            for key in ("Easy", "Normal", "Hard"):
                base_path = paths.get(key)
                if base_path:
                    norm = os.path.abspath(base_path).lower().rstrip("\\/") + os.sep
                    diff_dirs[key.lower()] = norm

            song_queue = []
            seen_paths = set()

            # If "All" is selected, search the entire Data folder.
            # Otherwise, search the specific difficulty folder from paths.
            if diff_lower not in ("easy", "normal", "hard"):
                # Search everything in Data/ if possible, or just SCRIPT_DIR
                data_root = PATHS.data_dir
                dirs_to_search = [data_root] if os.path.exists(data_root) else [SCRIPT_DIR]
            else:
                dirs_to_search = [search_dir]

            for d in dirs_to_search:
                if not os.path.exists(d):
                    continue
                for root, _, files in os.walk(d):
                    for f in files:
                        if f.lower().endswith(".txt"):
                            fp = os.path.join(root, f)
                            abs_fp = os.path.abspath(fp)
                            if abs_fp in seen_paths:
                                continue

                            meta = scan_song_header(fp)
                            if not meta:
                                continue
                            
                            # --- ROBUST METADATA PARSING ---
                            # Trust the file content. The Song Name usually contains the difficulty 
                            # (e.g. "Song (Hard) by Artist").
                            name = meta["Song Name"]
                            name_lower = name.lower()
                            
                            # Extract difficulty from the song name if possible, or use the Difficulty field
                            # The Difficulty field is often a number (e.g. "10"), so checking for "Hard" text is better.
                            detected_diff = "Unknown"
                            if "(hard)" in name_lower:
                                detected_diff = "Hard"
                            elif "(normal)" in name_lower:
                                detected_diff = "Normal"
                            elif "(easy)" in name_lower:
                                detected_diff = "Easy"
                            else:
                                # Fallback to the Difficulty header if it's a word
                                meta_diff_val = (meta.get("Difficulty") or "").strip().capitalize()
                                if meta_diff_val in ("Hard", "Normal", "Easy"):
                                    detected_diff = meta_diff_val

                            # --- FILTERING ---
                            # 1. Difficulty Filter
                            if diff_lower in ("easy", "normal", "hard"):
                                # If user requested specific difficulty, ensure this song matches
                                if detected_diff.lower() != diff_lower:
                                    continue

                            # 2. Color Filter
                            primary_color = (meta.get("Primary Color") or "").strip().lower()
                            secondary_color = (meta.get("Secondary Color") or "").strip().lower()
                            
                            if (
                                not target_primary_all
                                and (
                                    not primary_color
                                    or primary_color not in target_primary_colors
                                )
                            ):
                                continue
                            if (
                                not target_secondary_all
                                and (
                                    not secondary_color
                                    or secondary_color not in target_secondary_colors
                                )
                            ):
                                continue
                            
                            # 3. Name Search Filter
                            if filter_search and filter_search not in name_lower:
                                continue

                            # Store full metadata to avoid re-scanning later
                            song_queue.append((fp, name, detected_diff))
                            seen_paths.add(abs_fp)

            resume_seed_queue = load_memory_guard_resume_queue(resume_context)
            if resume_seed_queue:
                print(
                    f"[MemoryGuard] Resuming {len(resume_seed_queue)} song(s) from previous interrupted run."
                )
                song_queue = resume_seed_queue

            if not song_queue:
                print("Error: No matching songs found.")
            else:
                if not filter_search:
                    # Fetch existing songs from DB
                    existing_songs = set()
                    if use_evo_db:
                        try:
                            conn = get_db_connection()
                            cursor = conn.execute("SELECT name FROM songs")
                            existing_songs = {row[0] for row in cursor}
                            # Memory leak fix #2: Checkpoint WAL before closing connection
                            try:
                                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                                conn.execute("PRAGMA optimize")
                            except Exception as e:
                                # CRITICAL FIX: Log checkpoint failures (was silently suppressed)
                                logging.warning(f"[DB] WAL checkpoint/optimize failed: {e}")
                            conn.close()
                        except Exception as e:
                            print(f"[DB] Error fetching existing songs: {e}")

                    missing = []
                    completed = []
                    for fp, meta_name, song_diff in song_queue:
                        # Song name already contains difficulty like "(Hard)" or "(Easy)"
                        # Use song name directly as lookup key
                        lookup_key = meta_name
                        
                        # Skip _meta key when checking for completion
                        if lookup_key in existing_songs:
                            completed.append((fp, meta_name, song_diff))
                        else:
                            missing.append((fp, meta_name, song_diff))
                    if missing:
                        print(f"Auto-selection: {len(missing)} song(s) without DB records found; prioritizing those.")
                        song_queue = missing
                    else:
                        print("All songs have DB records; processing full list.")

                print(f"Found {len(song_queue)} songs to process.")

                discord_reporter.send_log(f"Queued {len(song_queue)} song(s) for processing.")

                memory_resume_tracker = MemoryGuardResumeTracker(MEMORY_GUARD_RESUME_FILE)
                memory_resume_tracker.prime(song_queue, resume_context)

                status_queue = None
                status_thread = None
                manager = multiprocessing.Manager()
                status_queue = manager.Queue()

                def _safe_sequential_gen(task_list):
                    for t in task_list:
                        try:
                            yield safe_process_song_task(t)
                        except Exception as seq_err:
                            yield {"_error": seq_err, "_song_name": t[1]}

                def _status_listener(q):
                    while True:
                        try:
                            msg = q.get()
                        except (EOFError, BrokenPipeError, OSError):
                            break
                        if msg is None:
                            break
                        print(msg, flush=True)
                        discord_reporter.send_log(str(msg))

                status_thread = threading.Thread(
                    target=_status_listener, args=(status_queue,), daemon=True
                )
                status_thread.start()

                cfg_dict = cfg_to_dict(cfg)

                tasks = []
                logical_cpus = os.cpu_count() or 1
                available_cpus = logical_cpus
                if eval_cpu_limit and eval_cpu_limit > 0:
                    available_cpus = max(1, min(logical_cpus, eval_cpu_limit))
                else:
                    available_cpus = max(1, available_cpus)
                if available_cpus != logical_cpus:
                    print(
                        f"EvalCPUCores cap applied: using {available_cpus} of {logical_cpus} cores."
                    )
                parallel_workers = 1  # Single-threaded per song to avoid nested pools on Windows

                for fp, found_song_name, task_diff in song_queue:
                    print(f"[QUEUE] {found_song_name}")
                    # Song name already includes difficulty like "(Hard)" or "(Easy)", use directly as key
                    tasks.append(
                        (
                            fp,
                            found_song_name,
                            task_diff,  # Pass the determined difficulty
                            cfg_dict,
                            paths,
                            ref_arrays,
                            all_gears,
                            all_minis,
                            gears_by_name,
                            minis_by_name,
                            use_evo_db,
                            auto_buff,
                            ga_depth,
                            status_queue,
                            parallel_workers,
                        )
                    )

                def _consume_results(
                    results_iter,
                    future_map=None,
                    propagate_broken_pool=False,
                    completed_songs=None,
                    completed_offset=0,
                ):
                    total = len(tasks)
                    completed = completed_offset
                    failed = 0
                    for item in results_iter:
                        completed += 1
                        # Handle Future objects (from ProcessPoolExecutor) with exception safety
                        if future_map is not None:
                            future = item
                            song_name = future_map.get(future, "Unknown")
                            try:
                                res = future.result()
                            except Exception as task_err:
                                failed += 1
                                err_msg = f"[{completed}/{total}] FAILED: {song_name} - {type(task_err).__name__}: {task_err}"
                                print(err_msg)
                                logging.error(err_msg)
                                discord_reporter.send_log(err_msg)
                                if propagate_broken_pool and isinstance(task_err, BrokenProcessPool):
                                    # Bubble up to trigger auto-recovery fallback
                                    raise
                                continue  # Skip this song and continue with the queue
                        else:
                            # Sequential processing - item is already the result (or error dict)
                            res = item
                            # Check if this is an error placeholder from _safe_sequential_gen
                            if isinstance(res, dict) and "_error" in res:
                                failed += 1
                                task_err = res["_error"]
                                song_name = res.get("_song_name", "Unknown")
                                err_msg = f"[{completed}/{total}] FAILED: {song_name} - {type(task_err).__name__}: {task_err}"
                                print(err_msg)
                                logging.error(err_msg)
                                discord_reporter.send_log(err_msg)
                                continue
                            # Normal sequential result; derive song name from payload
                            song_name = res.get("song", "Unknown")

                        # Track completed songs so we can avoid re-processing them in fallback
                        if completed_songs is not None and song_name:
                            completed_songs.add(song_name)
                        if memory_resume_tracker:
                            memory_resume_tracker.mark_completed(song_name)

                        # After finishing this song, bail out if MemoryGuard fired
                        if memory_release_requested():
                            print("[MemoryGuard] Early stop in _consume_results; "
                                  "leaving remaining songs for resume.")
                            break

                        print(f"[{completed}/{total}] Completed: {res['song']}")
                        print("=" * 60)
                        print(f"PROCESSING SONG: {res['song']}")
                        print("=" * 60)
                        discord_reporter.send_stats(build_stats_summary(res, completed, total))
                        # Logs already streamed live via Tee; buffer retained for completeness
                        if use_evo_db:
                            persisted = res.get("persist_entries")
                            if persisted:
                                save_loadouts_batch(res["song"], persisted)
                            else:
                                db_payload = res.get("db_payload")
                                if db_payload:
                                    save_loadouts_batch(res["song"], [{
                                        "score": db_payload.get("score", 0),
                                        "fg_score": db_payload.get("fg_score", 0),
                                        "gear": db_payload.get("gear", []),
                                        "minis": db_payload.get("minis", []),
                                        "details": db_payload.get("details", {}),
                                        "force": db_payload.get("force"),
                                    }])
                        log_content = (res.get("log") or "").strip()
                        if log_content:
                            discord_reporter.send_log(f"Log for {res.get('song', 'Unknown Song')} ({completed}/{total}):")
                            # Avoid Discord spam: keep only the tail of very long logs.
                            tail = log_content[-3000:] if len(log_content) > 3000 else log_content
                            discord_reporter.send_log(tail)

                        # Memory leak fix: Clear large result fields immediately after use
                        # These can accumulate 10-100MB per song (log buffers, persist data)
                        res["log"] = None
                        if "persist_entries" in res:
                            res["persist_entries"] = None
                        if "db_payload" in res:
                            res["db_payload"] = None
                    if failed > 0:
                        print(f"[SUMMARY] {failed}/{total} songs failed during processing.")

                # Plan parallelism across songs, capped by EvalCPUCores and per-song worker usage.
                song_worker_limit = max(1, available_cpus // max(1, parallel_workers))
                max_workers = max(1, min(len(tasks), song_worker_limit))
                print(
                    f"Parallel plan -> songs: {len(tasks)}, concurrent workers: {max_workers}, cores per song: {parallel_workers}"
                )
                print(f"Using {available_cpus} logical CPU cores")
                if len(tasks) > 1 and max_workers > 1:
                    # Track which songs completed successfully in the pool, so we can
                    # avoid re-processing them if we need to fall back to sequential.
                    completed_songs = set()

                    max_pool_retries = 3
                    broken_pool_failures = 0
                    remaining_tasks = list(tasks)
                    current_worker_cap = max_workers

                    def _run_sequential(pending_tasks, completed_offset=0):
                        if not pending_tasks:
                            return
                        _consume_results(
                            _safe_sequential_gen(pending_tasks),
                            future_map=None,
                            completed_songs=completed_songs,
                            completed_offset=completed_offset,
                        )

                    while remaining_tasks:
                        completed_offset = len(completed_songs)
                        effective_workers = max(
                            1, min(len(remaining_tasks), current_worker_cap)
                        )

                        # Use spawn everywhere to avoid fork-related state bleed across platforms.
                        try:
                            mp_ctx = multiprocessing.get_context("spawn")
                        except ValueError:
                            mp_ctx = multiprocessing.get_context()

                        if effective_workers == 1:
                            _run_sequential(remaining_tasks, completed_offset)
                            break

                        try:
                            with concurrent.futures.ProcessPoolExecutor(
                                max_workers=effective_workers,
                                mp_context=mp_ctx,
                            ) as executor:
                                future_map = {
                                    executor.submit(safe_process_song_task, t): t[1]
                                    for t in remaining_tasks
                                }
                                _consume_results(
                                    concurrent.futures.as_completed(future_map),
                                    future_map=future_map,
                                    propagate_broken_pool=True,
                                    completed_songs=completed_songs,
                                    completed_offset=completed_offset,
                                )

                                if memory_release_requested():
                                    print("[MemoryGuard] Stopping parallel loop after soft limit; "
                                          "not scheduling more songs in this run.")
                                    break
                        except BrokenProcessPool as bpp:
                            broken_pool_failures += 1
                            warn_msg = (
                                f"[Auto-Recover] Process pool broke while processing songs; "
                                f"attempt {broken_pool_failures}/{max_pool_retries}. "
                                f"Retrying remaining {len(remaining_tasks)} song(s) with up to "
                                f"{max(1, effective_workers - 1)} workers. Reason: {bpp}"
                            )
                            print(warn_msg)
                            logging.error(warn_msg)
                            discord_reporter.send_log(warn_msg)

                            # BUG FIX: Restart status_thread and manager after pool crash
                            # The old manager/queue may be in a broken state
                            print("[Auto-Recover] Restarting status_thread and manager...")
                            try:
                                # Stop old status_thread
                                if status_queue is not None:
                                    try:
                                        status_queue.put(None)
                                    except Exception:
                                        pass
                                if status_thread is not None:
                                    try:
                                        status_thread.join(timeout=2)
                                    except Exception:
                                        pass
                                # Shutdown old manager
                                if manager is not None:
                                    try:
                                        manager.shutdown()
                                    except Exception:
                                        pass

                                # Memory leak fix #4: Explicitly destroy old manager before creating new one
                                # Prevents 6-15 MB accumulation per pool crash
                                old_manager = manager
                                manager = None
                                status_queue = None
                                try:
                                    del old_manager
                                except (NameError, AttributeError):
                                    pass
                                gc.collect(generation=0)

                                # Create new manager and status_queue
                                manager = multiprocessing.Manager()
                                status_queue = manager.Queue()

                                # Restart status_thread
                                status_thread = threading.Thread(
                                    target=_status_listener, args=(status_queue,), daemon=True
                                )
                                status_thread.start()

                                print("[Auto-Recover] Status thread and manager restarted successfully.")
                            except Exception as restart_err:
                                print(f"[Auto-Recover] Warning: Failed to restart status infrastructure: {restart_err}")
                                # Continue anyway - status reporting is non-critical

                            # Rebuild remaining_tasks with new status_queue
                            remaining_songs = [t for t in tasks if t[1] not in completed_songs]
                            remaining_tasks = []
                            for fp, found_song_name, task_diff, *rest in remaining_songs:
                                # Rebuild task tuple with new status_queue
                                remaining_tasks.append((
                                    fp,
                                    found_song_name,
                                    task_diff,
                                    cfg_dict,
                                    paths,
                                    ref_arrays,
                                    all_gears,
                                    all_minis,
                                    gears_by_name,
                                    minis_by_name,
                                    use_evo_db,
                                    auto_buff,
                                    ga_depth,
                                    status_queue,  # New status_queue
                                    parallel_workers,
                                ))

                            current_worker_cap = max(1, effective_workers - 1)

                            if broken_pool_failures >= max_pool_retries:
                                fallback_msg = (
                                    "[Auto-Recover] Max pool retries hit; running remaining songs sequentially."
                                )
                                print(fallback_msg)
                                logging.error(fallback_msg)
                                discord_reporter.send_log(fallback_msg)
                                _run_sequential(
                                    remaining_tasks,
                                    completed_offset=len(completed_songs),
                                )
                                break

                            continue

                        break

                # Memory leak fix: Clear task lists after parallel processing completes
                # These accumulate 2MB per song in task tuples (ref_arrays, all_gears, all_minis)
                try:
                    if future_map is not None:
                        future_map.clear()
                except (NameError, AttributeError):
                    pass
                try:
                    if remaining_tasks is not None:
                        remaining_tasks.clear()
                except (NameError, AttributeError):
                    pass

                else:
                    # Sequential processing with per-song exception handling
                    _consume_results(_safe_sequential_gen(tasks), future_map=None)

                # Memory leak fix: Clear tasks list after consumption
                try:
                    if tasks is not None:
                        tasks.clear()
                except (NameError, AttributeError):
                    pass

                # Memory leak fix #1: Clear large reference data after task processing
                # These structures persist 5-51 MB per batch and are not reused
                try:
                    del ref_arrays, all_gears, all_minis, gears_by_name, minis_by_name
                    gc.collect(generation=0)
                except (NameError, AttributeError):
                    pass

                if status_queue:
                    status_queue.put(None)
                    if status_thread:
                        status_thread.join(timeout=2)
                    if manager:
                        manager.shutdown()
                discord_reporter.send_log("All queued songs processed.")
                if memory_resume_tracker:
                    memory_resume_tracker.finalize(memory_release_requested())
                if memory_release_requested():
                    print("[MemoryGuard] Soft limit reached; pending songs saved for resume.")
                    if loop_forever:
                        memory_guard_restart = True
                        print("[MemoryGuard] LoopForever enabled; scheduling automatic restart.")
                        discord_reporter.send_log(
                            "Memory soft limit reached; restarting MetaFinder to release RAM."
                        )

        except Exception as e:
            logging.error(f"Error: {e}")
            print(f"Error: {e}")
            discord_reporter.send_log(f"Error encountered: {e}")
        finally:
            # --- MEMORY LEAK FIX: Ensure manager/queue cleanup runs even on exceptions ---
            try:
                if status_queue is not None:
                    try:
                        status_queue.put(None)
                    except Exception:
                        pass
                if status_thread is not None:
                    try:
                        status_thread.join(timeout=2)
                    except Exception:
                        pass
                if manager is not None:
                    try:
                        manager.shutdown()
                    except Exception:
                        pass
            except Exception:
                pass
            
            elapsed = time.time() - start_time
            done_msg = f"Run completed in {elapsed:.2f}s"
            print(done_msg)
            discord_reporter.send_log(done_msg)
            # Update status timestamp so the website sees a fresh heartbeat.
            try:
                write_metafinder_status("online", done_msg)
            except Exception:
                pass
            
            # --- MEMORY LEAK FIX: Force garbage collection after each iteration ---
            # This helps reclaim memory from objects that may have circular references
            # or are otherwise not immediately collected.
            gc.collect()

        if memory_guard_restart:
            restart_process_for_memory_guard()
        elif loop_forever:
            wait_time = 3
            print(f"Restarting song scan in {wait_time} seconds...")
            time.sleep(wait_time)
            # Memory leak fix #3: Clear completed_songs set before next iteration
            # Prevents 50 KB per 1000 songs accumulation in loop_forever mode
            # BUG FIX: Properly clear/delete variables that could persist across iterations
            try:
                if completed_songs is not None:
                    completed_songs.clear()
                    del completed_songs
            except (NameError, AttributeError):
                pass
            try:
                if tasks is not None:
                    tasks.clear()
                    del tasks
            except (NameError, AttributeError):
                pass
            try:
                if future_map is not None:
                    future_map.clear()
                    del future_map
            except (NameError, AttributeError):
                pass
            try:
                if remaining_tasks is not None:
                    remaining_tasks.clear()
                    del remaining_tasks
            except (NameError, AttributeError):
                pass
        else:
            print("LoopForever=FALSE; exiting after completing queue.")
            discord_reporter.send_log("LoopForever disabled; exiting.")
            break

    # If we exit the main loop, mark MetaFinder as offline.
    try:
        write_metafinder_status("offline", "MetaFinder run stopped")
    except Exception:
        pass
