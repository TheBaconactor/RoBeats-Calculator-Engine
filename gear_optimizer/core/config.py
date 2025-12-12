"""
Configuration management for the gear optimizer.
Handles config.ini parsing, validation, and status file writing.
"""
import json
import logging
import os
import re
import sys
import time
from .constants import (
    DEFAULT_MEMORY_GUARD_PERCENT,
    STRICT_PLATFORM_MEMORY_GUARD_PERCENT,
    SCRIPT_DIR,
)
from .utils import safe_int, safe_float


def compute_memory_guard_limit(cfg):
    """
    Compute the RSS ceiling in bytes.

    - MemorySoftLimitGB enforces an absolute cap when > 0.
    - MemorySoftLimitPercent (default DEFAULT_MEMORY_GUARD_PERCENT) reserves a
      percentage of detected physical RAM. Set to 0 or negative to disable.
    - When both are provided we respect the stricter (smaller) ceiling.

    Args:
        cfg: ConfigParser instance

    Returns:
        int: Memory limit in bytes, or 0 if no limit
    """
    # Import here to avoid circular dependency
    from .memory import detect_total_physical_memory
    platform_default_percent = (
        STRICT_PLATFORM_MEMORY_GUARD_PERCENT
        if sys.platform in ("win32", "cygwin", "darwin")
        else DEFAULT_MEMORY_GUARD_PERCENT
    )

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

    # Clamp percent to the stricter platform default to avoid overly loose limits on Windows/macOS
    effective_percent = (
        min(limit_percent, platform_default_percent) if limit_percent > 0 else 0.0
    )

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





def load_force_greats_config(cfg):
    """
    Parse [ForceGreats] options into a list indexed by non-fever section (0-based).
    Keys follow the pattern NonFever{N}; missing values default to zero.

    Args:
        cfg: ConfigParser instance

    Returns:
        list: Force greats values per section, or empty list if not configured
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


def find_and_cache_paths():
    """
    Automatically discover data file paths and cache them.

    Searches for:
    - Easy/Normal/Hard folders (song difficulties)
    - Gears.csv, Minis.csv, Stats.txt files

    Returns:
        dict: Discovered paths configuration
    """
    import os
    from pathlib import Path
    from collections import deque

    PROJECT_ROOT = Path(SCRIPT_DIR)
    cache_file = os.path.join(SCRIPT_DIR, "bin", "paths_cache.json")

    results = {k: "" for k in ["Easy", "Normal", "Hard", "Gear", "Gears", "Minis", "Stats"]}
    targets_dirs = set(["Easy", "Normal", "Hard"])
    targets_files = set(["Gears.csv", "Minis.csv", "Stats.txt"])

    # Start scanning from the project root (or Data/ if present) to avoid scanning
    # unrelated parent directories (which can be very large on some systems).
    data_dir = PROJECT_ROOT / "Data"
    base_dir = data_dir if data_dir.exists() else PROJECT_ROOT
    queue = deque([base_dir])
    visited = {str(base_dir.resolve())}

    while queue and (targets_dirs or targets_files):
        curr = queue.popleft()
        try:
            for entry in os.scandir(curr):
                try:
                    p = Path(entry.path)
                    if entry.is_dir(follow_symlinks=False):
                        if entry.name in targets_dirs:
                            results[entry.name] = str(p.resolve())
                            targets_dirs.remove(entry.name)
                        if str(p.resolve()) not in visited:
                            visited.add(str(p.resolve()))
                            queue.append(p)
                    elif entry.is_file(follow_symlinks=False):
                        if entry.name in targets_files:
                            name = entry.name
                            if name.lower() == "gears.csv":
                                results["Gears"] = str(p.resolve())
                                results["Gear"] = str(p.resolve().parent)
                            elif name.lower() == "minis.csv":
                                results["Minis"] = str(p.resolve())
                            elif name.lower() == "stats.txt":
                                results["Stats"] = str(p.resolve())
                            try:
                                targets_files.remove(entry.name)
                            except KeyError:
                                pass
                    if not targets_dirs and not targets_files:
                        break
                except Exception:
                    continue
        except Exception:
            continue

    # Save to cache
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)

    return results


def load_paths_cache():
    """
    Load paths configuration from cached JSON file.
    Automatically discovers and caches paths if cache doesn't exist.

    Returns:
        dict: Cached paths configuration, or empty dict if not found
    """
    cache_file = os.path.join(SCRIPT_DIR, "bin", "paths_cache.json")

    # Check if cache exists and has required keys
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
                # Validate cache has essential keys
                if all(cached.get(k) for k in ["Easy", "Normal", "Hard", "Gears", "Stats"]):
                    return cached
        except Exception:
            logging.debug("[Paths] Failed to load/validate paths_cache.json", exc_info=True)

    # Cache doesn't exist or is invalid - discover paths
    print("[Paths] Discovering data file paths...")
    return find_and_cache_paths()
