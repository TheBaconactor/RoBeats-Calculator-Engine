"""
Configuration management for the gear optimizer.
Handles config.ini parsing, validation, and status file writing.
"""

import configparser
import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from typing import Any
from .fallback_monitor import FallbackAwareConfigParser, warn_fallback
from .constants import (
    DEFAULT_MEMORY_GUARD_PERCENT,
    STRICT_PLATFORM_MEMORY_GUARD_PERCENT,
    SCRIPT_DIR,
)
from .utils import safe_int, safe_float


def get_config_path(default: str = "config.ini") -> str:
    """
    Resolve the effective config path.

    Precedence:
    - `METAFINDER_CONFIG_PATH` when set and non-empty
    - `default` (typically "config.ini")
    """
    env_path = os.environ.get("METAFINDER_CONFIG_PATH")
    if env_path is not None:
        p = str(env_path).strip()
        if p:
            return p
    return str(default)


def load_config(path: str | None = None) -> configparser.ConfigParser:
    """
    Load config.ini (or an override path) into a ConfigParser.

    This intentionally does not raise on missing files to preserve existing behavior in entrypoints
    that historically used `ConfigParser().read(...)` without checking the return value.
    """
    cfg = FallbackAwareConfigParser()
    cfg_path = str(path or get_config_path())
    try:
        cfg.read(cfg_path, encoding="utf-8-sig")
    except Exception as exc:
        warn_fallback("config.load.read_error", "failed to read config file", context={"path": cfg_path}, exc=exc)
        logging.debug(f"[Config] Failed to read {cfg_path}: {type(exc).__name__}: {exc}")
    return cfg


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

    # PRODUCTION: memory guard flags (MemorySoftLimitGB, MemorySoftLimitPercent).
    limit_gb = safe_float(cfg.get("IterationEngine", "MemorySoftLimitGB", fallback=0.0), default=0.0)
    limit_percent = safe_float(
        cfg.get(
            "IterationEngine",
            "MemorySoftLimitPercent",
            fallback=platform_default_percent,
        ),
        default=platform_default_percent,
    )

    # Clamp percent to the stricter platform default to avoid overly loose limits on Windows/macOS
    effective_percent = min(limit_percent, platform_default_percent) if limit_percent > 0 else 0.0

    candidates = []
    if limit_gb > 0:
        candidates.append(limit_gb * (1024**3))
    if effective_percent > 0:
        total_ram = detect_total_physical_memory()
        if total_ram > 0:
            candidates.append(total_ram * (effective_percent / 100.0))
        else:
            logging.warning("[MemoryGuard] Physical RAM auto-detect failed; percent limit ignored.")

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
    except (ValueError, KeyError, AttributeError) as e:
        warn_fallback("config.force_greats.section", "failed to parse [ForceGreats] section; using empty config", exc=e)
        logging.debug(f"[ForceGreats Config] Failed to parse ForceGreats section: {e}")
        return []

    if not entries:
        return []

    max_idx = max(idx for idx, _ in entries)
    values = [0] * (max_idx + 1)
    for idx, val in entries:
        values[idx] = val
    return values


def load_force_greats_inline(cfg, *, key: str = "ForceGreatsManual"):
    """
    Parse an inline ForceGreats manual config from [IterationEngine].

    Supported formats:
      - Comma/space-separated ints: "0,1,0" or "0 1 0"
      - JSON list: "[0, 1, 0]"
      - Single int: "3" (equivalent to "3" for NonFever1)

    Returns:
      list[int]: Parsed values (may be empty).
    """
    if not cfg:
        return []
    try:
        raw = cfg.get("IterationEngine", key, fallback="").strip()
    except Exception as exc:
        warn_fallback(
            "config.force_greats.inline.read",
            "failed reading inline ForceGreats config; using empty config",
            context={"key": key},
            exc=exc,
        )
        return []
    if not raw:
        return []

    # JSON list form
    if raw.startswith("[") and raw.endswith("]"):
        try:
            arr = json.loads(raw)
            if not isinstance(arr, list):
                return []
            out = []
            for v in arr:
                out.append(max(0, safe_int(v, 0)))
            # Trim trailing zeros to keep behavior consistent with section parsing
            while out and out[-1] == 0:
                out.pop()
            return out
        except Exception as e:
            warn_fallback(
                "config.force_greats.inline.json",
                "failed parsing inline ForceGreats JSON list; using empty config",
                context={"key": key, "value": raw},
                exc=e,
            )
            logging.debug(f"[ForceGreats Config] Failed to parse {key} JSON list: {e}")
            return []

    # Split by commas and/or whitespace.
    parts = re.split(r"[,\s]+", raw)
    values = []
    for p in parts:
        p = (p or "").strip()
        if not p:
            continue
        # Allow a "NonFeverN=V" mini-syntax for convenience.
        if "=" in p:
            try:
                _, rhs = p.split("=", 1)
                p = rhs.strip()
            except Exception:
                continue
        values.append(max(0, safe_int(p, 0)))

    while values and values[-1] == 0:
        values.pop()
    return values


@dataclass(frozen=True)
class IterationEngineSettings:
    """
    Parsed, normalized settings from the `[IterationEngine]` section.

    Centralizing this avoids logic drift across the app, workers, and solver code.
    """

    meta_finder: bool
    enable_fever: bool
    enable_mini: bool
    enable_gear: bool
    auto_select_buff_and_color: bool
    force_greats_mode: bool
    force_greats_finder: bool
    force_greats_debug: bool
    force_greats_config: list[int]
    manual_force_greats: bool


def read_iteration_engine_settings(cfg: Any) -> IterationEngineSettings:
    """
    Read and normalize `[IterationEngine]` behavior flags.

    Important semantics:
    - `MetaFinder` gates the optimizer family (fever/mini/gear).
    - `ForceGreatsFinder` is only active when `ForceGreatsMode` is enabled.
    - A non-empty manual FG config disables `ForceGreatsFinder` (deliberate override).
    """
    if cfg is None:
        return IterationEngineSettings(
            meta_finder=False,
            enable_fever=False,
            enable_mini=False,
            enable_gear=False,
            auto_select_buff_and_color=False,
            force_greats_mode=False,
            force_greats_finder=False,
            force_greats_debug=False,
            force_greats_config=[],
            manual_force_greats=False,
        )

    # PRODUCTION: core runtime flags (MetaFinder, AutoSelectBuffAndColor, ForceGreatsMode, ForceGreatsFinder).
    try:
        meta_finder = cfg.getboolean("IterationEngine", "MetaFinder", fallback=False)
    except Exception:
        meta_finder = False

    enable_fever = enable_mini = enable_gear = bool(meta_finder)

    try:
        auto_select_buff_and_color = cfg.getboolean("IterationEngine", "AutoSelectBuffAndColor", fallback=False)
    except Exception:
        auto_select_buff_and_color = False

    try:
        force_greats_mode = cfg.getboolean("IterationEngine", "ForceGreatsMode", fallback=False)
    except Exception:
        force_greats_mode = False

    try:
        force_greats_finder = cfg.getboolean("IterationEngine", "ForceGreatsFinder", fallback=False)
    except Exception:
        force_greats_finder = False

    # DEV / DEBUG: diagnostic-only flag (ForceGreatsDebug).
    try:
        force_greats_debug = cfg.getboolean("IterationEngine", "ForceGreatsDebug", fallback=False)
    except Exception:
        force_greats_debug = False

    # ForceGreatsMode must be enabled for ForceGreatsFinder to work.
    if not force_greats_mode:
        force_greats_finder = False

    # Prefer explicit [ForceGreats] section; fall back to inline config if section is absent/empty.
    force_greats_config = load_force_greats_config(cfg)
    if not force_greats_config:
        inline_cfg = load_force_greats_inline(cfg, key="ForceGreatsManual")
        if inline_cfg:
            force_greats_config = inline_cfg

    manual_force_greats = bool(force_greats_mode) and any(force_greats_config)
    if manual_force_greats:
        # Manual config is a deliberate override; allow it to work regardless of
        # ForceGreatsFinder setting by disabling finder when manual values are provided.
        force_greats_finder = False

    return IterationEngineSettings(
        meta_finder=bool(meta_finder),
        enable_fever=bool(enable_fever),
        enable_mini=bool(enable_mini),
        enable_gear=bool(enable_gear),
        auto_select_buff_and_color=bool(auto_select_buff_and_color),
        force_greats_mode=bool(force_greats_mode),
        force_greats_finder=bool(force_greats_finder),
        force_greats_debug=bool(force_greats_debug),
        force_greats_config=list(force_greats_config or []),
        manual_force_greats=bool(manual_force_greats),
    )


def read_fg_candidate_limit(
    cfg: Any,
    *,
    default: int,
    min_limit: int,
    max_limit: int = 5000,
) -> int:
    """
    Read and clamp `[IterationEngine].FG_CandidateLimit`.

    This is used across multiple CPU/GPU pipelines; centralizing it prevents drift in
    clamping semantics and limits "accidental" extreme values that could cause huge
    DB reads or GPU batches.
    """
    # PRODUCTION: FG tuning flag (FG_CandidateLimit).
    try:
        raw = cfg.get("IterationEngine", "FG_CandidateLimit", fallback=default)
    except Exception as exc:
        warn_fallback(
            "config.fg_candidate_limit.read",
            "failed reading FG_CandidateLimit; using default",
            context={"default": default},
            exc=exc,
        )
        raw = default
    limit = safe_int(raw, default)
    limit = max(int(min_limit), min(int(max_limit), int(limit)))
    return limit


def read_fg_search_radius(cfg: Any) -> int | None:
    """
    Read `[IterationEngine].FG_SearchRadius`.

    Semantics:
    - unset/empty => return None (use default radius elsewhere)
    - -1 => full window over all FT/FF allocations within TOTAL_GEM_BUDGET
    - >=0 => radius in gem-space around each loadout's (FT, FF) center
    """
    # PRODUCTION: FG tuning flag (FG_SearchRadius).
    try:
        raw = str(cfg.get("IterationEngine", "FG_SearchRadius", fallback="") or "").strip()
    except Exception as exc:
        warn_fallback("config.fg_search_radius.read", "failed reading FG_SearchRadius; using default behavior", exc=exc)
        raw = ""
    if not raw:
        return None
    return safe_int(raw, -1)


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
                except (OSError, PermissionError):
                    # Skip files/directories we can't access
                    continue
        except (OSError, PermissionError):
            # Skip directories we can't scan
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
        except (OSError, json.JSONDecodeError, KeyError) as e:
            warn_fallback(
                "config.paths_cache.read",
                "failed loading paths cache; rediscovering paths",
                context={"cache_file": cache_file},
                exc=e,
            )
            logging.debug(f"[Paths] Failed to load/validate paths_cache.json: {e}", exc_info=True)

    # Cache doesn't exist or is invalid - discover paths
    warn_fallback("config.paths_cache.miss", "paths cache missing/invalid; running path discovery")
    print("[Paths] Discovering data file paths...")
    return find_and_cache_paths()
