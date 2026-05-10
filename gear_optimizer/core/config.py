"""
Configuration management for the gear optimizer.
Handles config.ini parsing, validation, and status file writing.
"""

import configparser
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .fallback_monitor import FallbackAwareConfigParser, warn_fallback
from .constants import (
    DEFAULT_MEMORY_GUARD_PERCENT,
    STRICT_PLATFORM_MEMORY_GUARD_PERCENT,
    SCRIPT_DIR,
)
from .parsing import env_str
from .utils import safe_float, safe_int

_EXTENDS_KEY = "_extends"

def get_config_path(default: str = "config.ini") -> str:
    """
    Resolve the effective config path.

    Precedence:
    - `METAFINDER_CONFIG_PATH` when set and non-empty
    - `default` (typically "config.ini")
    """
    env_path = env_str("METAFINDER_CONFIG_PATH", "")
    if env_path:
        return env_path
    return str(default)


def _resolve_extends_chain(cfg_path: str, seen: set[str] | None = None) -> list[str]:
    """
    Walk the ``_extends`` chain starting from *cfg_path* and return an
    ordered list of paths to load (base-first, leaf-last).

    ``_extends`` is a special key that may appear in *any* section of a
    config file; its value is a relative or absolute path to a parent
    config. The chain is resolved recursively with cycle detection.
    """

    if seen is None:
        seen = set()

    abs_path = str(Path(cfg_path).resolve())
    if abs_path in seen:
        return []
    seen.add(abs_path)

    cfg_dir = str(Path(cfg_path).resolve().parent)

    tmp = configparser.ConfigParser()
    try:
        tmp.read(cfg_path, encoding="utf-8-sig")
    except (AttributeError, TypeError, ValueError, configparser.Error):
        return [cfg_path]

    extends_path = None
    for section in tmp.sections():
        if tmp.has_option(section, _EXTENDS_KEY):
            extends_path = tmp.get(section, _EXTENDS_KEY).strip()
            break

    base_paths: list[str] = []
    if extends_path:
        if not os.path.isabs(extends_path):
            extends_path = os.path.normpath(os.path.join(cfg_dir, extends_path))
        if not os.path.isfile(extends_path):
            raise FileNotFoundError(
                f"Config _extends chain broken: {cfg_path!r} references "
                f"{extends_path!r} which does not exist or is not a file."
            )
        base_paths = _resolve_extends_chain(extends_path, seen)

    return base_paths + [cfg_path]


def load_config(path: str | None = None) -> configparser.ConfigParser:
    """
    Load config.ini (or an override path) into a ConfigParser.

    Supports ``_extends``: if any section in the config file contains a
    ``_extends`` key, its value is resolved as a path to a base config.
    Base configs are loaded first; the leaf config overrides them.

    This intentionally does not raise on missing files to preserve existing behavior in entrypoints
    that historically used `ConfigParser().read(...)` without checking the return value.
    """
    cfg = FallbackAwareConfigParser()
    cfg_path = str(path or get_config_path())
    chain = _resolve_extends_chain(cfg_path)
    try:
        cfg.read(chain, encoding="utf-8-sig")
    except (AttributeError, TypeError, ValueError, configparser.Error) as exc:
        warn_fallback("config.load.read_error", "failed to read config file", context={"path": cfg_path}, exc=exc)
        logging.debug(f"[Config] Failed to read {cfg_path}: {type(exc).__name__}: {exc}")
    for section in cfg.sections():
        if cfg.has_option(section, _EXTENDS_KEY):
            cfg.remove_option(section, _EXTENDS_KEY)
    return cfg


def _warn_cfg_fallback(method: str, section: str, key: str, default: Any, exc: BaseException) -> None:
    warn_fallback(
        f"config.{method}.invalid",
        "failed reading config value; using default",
        context={"section": section, "option": key, "fallback": default},
        exc=exc,
    )


def _parse_cfg_int(raw: Any) -> int:
    sentinel = object()
    parsed = safe_int(raw, sentinel)
    if parsed is sentinel:
        raise ValueError(f"invalid integer value: {raw!r}")
    return int(parsed)


_parse_cfg_int.__name__ = "getint"


def _parse_cfg_float(raw: Any) -> float:
    sentinel = object()
    parsed = safe_float(raw, sentinel)
    if parsed is sentinel:
        raise ValueError(f"invalid float value: {raw!r}")
    return float(parsed)


_parse_cfg_float.__name__ = "getfloat"


def cfg_get(cfg: Any, section: str, key: str, type_, default: Any, *, clamp_min=None, clamp_max=None):
    try:
        raw = cfg.get(section, key, fallback=default)
        if type_ is str:
            value = default if raw is None or raw == "" else str(raw)
        else:
            value = type_(raw)
    except (AttributeError, TypeError, ValueError, configparser.Error) as exc:
        method = "get"
        if type_ is _parse_cfg_int:
            method = "getint"
        elif type_ is _parse_cfg_float:
            method = "getfloat"
        _warn_cfg_fallback(method, section, key, default, exc)
        return default

    if clamp_min is not None or clamp_max is not None:
        try:
            if clamp_min is not None:
                value = max(clamp_min, value)
            if clamp_max is not None:
                value = min(clamp_max, value)
        except (TypeError, ValueError) as exc:
            _warn_cfg_fallback("get", section, key, default, exc)
            return default

    return value


def cfg_get_bool(cfg: Any, section: str, key: str, default: bool = False) -> bool:
    try:
        return bool(cfg.getboolean(section, key, fallback=default))
    except (AttributeError, TypeError, ValueError, configparser.Error) as exc:
        _warn_cfg_fallback("getboolean", section, key, default, exc)
        return bool(default)


def cfg_get_int(
    cfg: Any,
    section: str,
    key: str,
    default: int,
    *,
    clamp_min=None,
    clamp_max=None,
) -> int:
    return int(
        cfg_get(
            cfg,
            section,
            key,
            _parse_cfg_int,
            default,
            clamp_min=clamp_min,
            clamp_max=clamp_max,
        )
    )


def cfg_get_float(
    cfg: Any,
    section: str,
    key: str,
    default: float,
    *,
    clamp_min=None,
    clamp_max=None,
) -> float:
    return float(
        cfg_get(
            cfg,
            section,
            key,
            _parse_cfg_float,
            default,
            clamp_min=clamp_min,
            clamp_max=clamp_max,
        )
    )


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

    del cfg
    limit_gb = 0.0
    limit_percent = platform_default_percent

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


@dataclass(frozen=True)
class IterationEngineSettings:
    """
    Hardwired skyline production settings.
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


@dataclass(frozen=True, slots=True)
class GPUExecutionSettings:
    gpu_mode: bool = True
    gpu_song_slots: int = 0

    @classmethod
    def from_config(cls, cfg: Any) -> "GPUExecutionSettings":
        del cfg
        return cls(gpu_mode=True, gpu_song_slots=0)


@dataclass(frozen=True, slots=True)
class CalculateSongSettings:
    difficulty: str = "All"
    song_name: str = ""
    target_primary: str = ""
    target_secondary: str = ""

    @classmethod
    def from_config(cls, cfg: Any) -> "CalculateSongSettings":
        if cfg is None:
            return cls()
        difficulty = cfg_get(cfg, "CalculateSong", "Difficulty", str, "All")
        song_name = cfg_get(cfg, "CalculateSong", "Song_Name", str, "")
        target_primary = cfg_get(cfg, "CalculateSong", "TargetPrimary", str, "")
        target_secondary = cfg_get(cfg, "CalculateSong", "TargetSecondary", str, "")
        return cls(
            difficulty=str(difficulty or "All"),
            song_name=str(song_name or ""),
            target_primary=str(target_primary or ""),
            target_secondary=str(target_secondary or ""),
        )


@dataclass(frozen=True, slots=True)
class AppRuntimeSettings:
    iteration_engine: IterationEngineSettings
    calculate_song: CalculateSongSettings
    gpu: GPUExecutionSettings
    use_evolution_db: bool = True
    loop_forever: bool = False
    eval_cpu_cores: int = 0
    song_queue_limit: int = 0
    ignore_resume_queue: bool = False
    song_repeats: int = 1
    bundle_song_repeats: bool = False
    loop_restart_wait_sec: float = 0.0

    @classmethod
    def from_config(cls, cfg: Any) -> "AppRuntimeSettings":
        if cfg is None:
            return cls(
                iteration_engine=read_iteration_engine_settings(None),
                calculate_song=CalculateSongSettings(),
                gpu=GPUExecutionSettings(),
            )

        iteration_engine = read_iteration_engine_settings(cfg)
        calculate_song = CalculateSongSettings.from_config(cfg)
        gpu = GPUExecutionSettings.from_config(cfg)

        loop_forever = cfg_get_bool(cfg, "CalculateSong", "LoopForever", True)

        return cls(
            iteration_engine=iteration_engine,
            calculate_song=calculate_song,
            gpu=gpu,
            use_evolution_db=True,
            loop_forever=bool(loop_forever),
            eval_cpu_cores=0,
            song_queue_limit=0,
            ignore_resume_queue=False,
            song_repeats=1,
            bundle_song_repeats=False,
            loop_restart_wait_sec=0.0,
        )


def read_iteration_engine_settings(cfg: Any) -> IterationEngineSettings:
    """
    Return hardwired skyline production behavior.
    """
    del cfg
    return IterationEngineSettings(
        meta_finder=True,
        enable_fever=True,
        enable_mini=True,
        enable_gear=True,
        auto_select_buff_and_color=True,
        force_greats_mode=True,
        force_greats_finder=True,
        force_greats_debug=False,
        force_greats_config=[],
        manual_force_greats=False,
    )


def read_fg_candidate_limit(
    cfg: Any,
    *,
    default: int,
    min_limit: int,
    max_limit: int = 5000,
) -> int:
    """Return the retained-candidate FG limit requested by the caller."""
    del cfg, max_limit
    return max(int(default), int(min_limit))


def read_fg_search_radius(cfg: Any) -> int | None:
    """Return full FT/FF search for skyline-native FG."""
    del cfg
    return -1


def read_outer_search_engine(cfg: Any, *, default: str = "ga") -> str:
    """Return the production outer solver. Skyline supersedes GA."""
    del cfg, default
    return "exact"


def read_pre_prune_mode(cfg: Any, *, default: str = "auto") -> str:
    """Return the production skyline pre-prune mode."""
    del cfg, default
    return "none"


def read_fg_solver_mode(cfg: Any, *, default: str = "finder") -> str:
    """Return the production FG mode. Skyline owns retained-candidate FG scoring."""
    del cfg, default
    return "finder"


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
