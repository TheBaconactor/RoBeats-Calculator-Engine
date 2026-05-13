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
from pathlib import Path
from typing import Any

from .fallback_monitor import FallbackAwareConfigParser, warn_fallback
from .constants import (
    DEFAULT_MEMORY_GUARD_PERCENT,
    GA_ELITISM,
    GA_MUTATION_RATE,
    GA_MULTI_RUNS_DEFAULT,
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


_CFG_ALIAS_WARNED: set[tuple[str, str, str]] = set()
_SINGLE_OWNER_FLAG_WARNED: set[str] = set()


def _cfg_has_option(cfg: Any, section: str, key: str) -> bool:
    try:
        return bool(cfg.has_option(section, key))
    except (AttributeError, TypeError, ValueError, configparser.Error):
        return False


def _warn_legacy_cfg_alias(section: str, legacy_key: str, canonical_key: str) -> None:
    warn_key = (str(section), str(legacy_key), str(canonical_key))
    if warn_key in _CFG_ALIAS_WARNED:
        return
    _CFG_ALIAS_WARNED.add(warn_key)
    logging.warning(
        "[Config] IterationEngine.%s is deprecated; use IterationEngine.%s.",
        legacy_key,
        canonical_key,
    )


def _warn_single_owner_noop_flag(key: str, value: Any) -> None:
    key_s = str(key)
    if key_s in _SINGLE_OWNER_FLAG_WARNED:
        return
    _SINGLE_OWNER_FLAG_WARNED.add(key_s)
    logging.warning("[InFlight] IterationEngine.%s=%s ignored (single native GPU owner policy); using 1.", key_s, value)


def cfg_get_int_alias(
    cfg: Any,
    section: str,
    canonical_key: str,
    legacy_key: str,
    default: int,
    *,
    clamp_min=None,
    clamp_max=None,
) -> int:
    if _cfg_has_option(cfg, section, canonical_key):
        return cfg_get_int(
            cfg,
            section,
            canonical_key,
            default,
            clamp_min=clamp_min,
            clamp_max=clamp_max,
        )
    if _cfg_has_option(cfg, section, legacy_key):
        _warn_legacy_cfg_alias(section, legacy_key, canonical_key)
        return cfg_get_int(
            cfg,
            section,
            legacy_key,
            default,
            clamp_min=clamp_min,
            clamp_max=clamp_max,
        )
    return cfg_get_int(
        cfg,
        section,
        canonical_key,
        default,
        clamp_min=clamp_min,
        clamp_max=clamp_max,
    )


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

    # PRODUCTION: memory guard flags (MemorySoftLimitGB, MemorySoftLimitPercent).
    limit_gb = cfg.getfloat("IterationEngine", "MemorySoftLimitGB", fallback=0.0)
    limit_percent = cfg.getfloat(
        "IterationEngine",
        "MemorySoftLimitPercent",
        fallback=platform_default_percent,
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
    except (ValueError, KeyError, AttributeError, TypeError, configparser.Error) as e:
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
    except (AttributeError, TypeError, ValueError, configparser.Error) as exc:
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
        except (json.JSONDecodeError, TypeError, ValueError) as e:
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
            except ValueError:
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

    force_greats_debug: bool
    force_greats_config: list[int]
    manual_force_greats: bool


@dataclass(frozen=True, slots=True)
class GPUExecutionSettings:
    gpu_song_slots: int = 0
    ga_queue_mult: int = 0

    @classmethod
    def from_config(cls, cfg: Any) -> "GPUExecutionSettings":
        if cfg is None:
            return cls()
        gpu_song_slots = cfg_get_int(cfg, "IterationEngine", "GPU_SongSlots", 0, clamp_min=0)
        ga_queue_mult = cfg_get_int(cfg, "IterationEngine", "InFlight_GA_QueueMult", 0, clamp_min=0)
        return cls(
            gpu_song_slots=int(gpu_song_slots),
            ga_queue_mult=int(ga_queue_mult),
        )


@dataclass(frozen=True, slots=True)
class GASettings:
    tournament_k: int = 3
    mutation_rate: float = GA_MUTATION_RATE
    immigrant_rate: float = 0.0
    elite_count: int = GA_ELITISM
    novelty_repair_attempts: int = 2
    convergence_trace: bool = False
    convergence_trace_every: int = 1
    convergence_trace_out_dir: str = "artifacts/ga_trace"
    convergence_trace_song_filter: str = ""
    search_depth: int = 50
    multi_start: int = GA_MULTI_RUNS_DEFAULT

    @classmethod
    def from_config(cls, cfg: Any) -> "GASettings":
        if cfg is None:
            return cls()
        tournament_k = cfg_get_int(cfg, "IterationEngine", "GPU_GA_TournamentK", 3, clamp_min=1, clamp_max=8)
        mutation_rate = cfg_get_float(
            cfg,
            "IterationEngine",
            "GPU_GA_MutationRate",
            GA_MUTATION_RATE,
            clamp_min=0.0,
            clamp_max=1.0,
        )
        immigrant_rate = cfg_get_float(
            cfg,
            "IterationEngine",
            "GPU_GA_ImmigrantRate",
            0.0,
            clamp_min=0.0,
            clamp_max=1.0,
        )
        elite_count = cfg_get_int(cfg, "IterationEngine", "GPU_GA_EliteCount", GA_ELITISM, clamp_min=0)
        novelty_repair_attempts = cfg_get_int(
            cfg,
            "IterationEngine",
            "GPU_GA_NoveltyRepairAttempts",
            2,
            clamp_min=0,
            clamp_max=4,
        )
        convergence_trace = cfg_get_bool(cfg, "IterationEngine", "GAConvergenceTrace", False)
        convergence_trace_every = cfg_get_int(cfg, "IterationEngine", "GAConvergenceTraceEvery", 1, clamp_min=1)
        convergence_trace_out_dir = cfg_get(
            cfg,
            "IterationEngine",
            "GAConvergenceTraceOutDir",
            str,
            "artifacts/ga_trace",
        )
        convergence_trace_song_filter = cfg_get(cfg, "IterationEngine", "GAConvergenceTraceSongFilter", str, "")
        search_depth = cfg_get_int_alias(
            cfg,
            "IterationEngine",
            "GA_SearchDepth",
            "GA_Depth",
            50,
            clamp_min=1,
        )
        multi_start = cfg_get_int(
            cfg,
            "IterationEngine",
            "GA_MultiStart",
            GA_MULTI_RUNS_DEFAULT,
            clamp_min=1,
        )

        return cls(
            tournament_k=int(tournament_k),
            mutation_rate=float(mutation_rate),
            immigrant_rate=float(immigrant_rate),
            elite_count=int(elite_count),
            novelty_repair_attempts=int(novelty_repair_attempts),
            convergence_trace=bool(convergence_trace),
            convergence_trace_every=int(convergence_trace_every),
            convergence_trace_out_dir=str(convergence_trace_out_dir),
            convergence_trace_song_filter=str(convergence_trace_song_filter),
            search_depth=int(search_depth),
            multi_start=int(multi_start),
        )


@dataclass(frozen=True, slots=True)
class InflightSettings:
    songs: int = 0
    instances: int = 1
    ram_mode: bool = False
    song_file_cache_max: int = 0
    team_buff_calc_cache_max: int = 0
    ga_queue_mult: int = 0

    @classmethod
    def from_config(cls, cfg: Any) -> "InflightSettings":
        if cfg is None:
            return cls()
        songs = cfg_get_int(cfg, "IterationEngine", "InFlightSongs", 0, clamp_min=0)
        requested_instances = cfg_get_int(cfg, "IterationEngine", "InFlightInstances", 1, clamp_min=1)
        instances = 1
        if int(requested_instances) > 1:
            _warn_single_owner_noop_flag("InFlightInstances", int(requested_instances))
        ram_mode = cfg_get_bool(cfg, "IterationEngine", "InFlight_RamMode", False)
        song_file_cache_max = cfg_get_int(cfg, "IterationEngine", "InFlight_SongFileCacheMax", 0, clamp_min=0)
        team_buff_calc_cache_max = cfg_get_int(
            cfg,
            "IterationEngine",
            "TeamBuff_BaseCalcSongCacheMax",
            0,
            clamp_min=0,
        )
        ga_queue_mult = cfg_get_int(cfg, "IterationEngine", "InFlight_GA_QueueMult", 0, clamp_min=0)
        return cls(
            songs=int(songs),
            instances=int(instances),
            ram_mode=bool(ram_mode),
            song_file_cache_max=int(song_file_cache_max),
            team_buff_calc_cache_max=int(team_buff_calc_cache_max),
            ga_queue_mult=int(ga_queue_mult),
        )


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
    ga: GASettings
    inflight: InflightSettings
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
                ga=GASettings(),
                inflight=InflightSettings(),
            )

        iteration_engine = read_iteration_engine_settings(cfg)
        calculate_song = CalculateSongSettings.from_config(cfg)
        gpu = GPUExecutionSettings.from_config(cfg)
        ga = GASettings.from_config(cfg)
        inflight = InflightSettings.from_config(cfg)

        loop_forever = cfg_get_bool(cfg, "IterationEngine", "LoopForever", False)
        eval_cpu_cores = cfg_get_int(cfg, "IterationEngine", "EvalCPUCores", 0, clamp_min=0)
        song_queue_limit = cfg_get_int(cfg, "IterationEngine", "SongQueueLimit", 0, clamp_min=0)
        ignore_resume_queue = cfg_get_bool(cfg, "IterationEngine", "IgnoreResumeQueue", False)
        song_repeats = cfg_get_int(cfg, "IterationEngine", "SongRepeats", 1, clamp_min=1)
        bundle_song_repeats = cfg_get_bool(cfg, "IterationEngine", "BundleSongRepeats", False)
        loop_restart_wait_sec = cfg_get_float(
            cfg,
            "IterationEngine",
            "LoopRestartWaitSec",
            0.0,
            clamp_min=0.0,
            clamp_max=60.0,
        )

        return cls(
            iteration_engine=iteration_engine,
            calculate_song=calculate_song,
            gpu=gpu,
            ga=ga,
            inflight=inflight,
            loop_forever=bool(loop_forever),
            eval_cpu_cores=int(eval_cpu_cores),
            song_queue_limit=int(song_queue_limit),
            ignore_resume_queue=bool(ignore_resume_queue),
            song_repeats=int(song_repeats),
            bundle_song_repeats=bool(bundle_song_repeats),
            loop_restart_wait_sec=float(loop_restart_wait_sec),
        )


def read_iteration_engine_settings(cfg: Any) -> IterationEngineSettings:
    """
    Read and normalize `[IterationEngine]` behavior settings.

    Important semantics:
    - Production optimizer mode is always active.
    - These are no longer config switches; they are native runtime policy.
    - A non-empty manual FG config disables finder mode (deliberate override).
    """
    # DEV / DEBUG: diagnostic-only flag (ForceGreatsDebug).
    force_greats_debug = cfg_get_bool(cfg, "IterationEngine", "ForceGreatsDebug", False) if cfg is not None else False

    # Prefer explicit [ForceGreats] section; fall back to inline config if section is absent/empty.
    force_greats_config = load_force_greats_config(cfg) if cfg is not None else []
    if not force_greats_config and cfg is not None:
        inline_cfg = load_force_greats_inline(cfg, key="ForceGreatsManual")
        if inline_cfg:
            force_greats_config = inline_cfg

    manual_force_greats = any(force_greats_config)

    return IterationEngineSettings(
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
    return cfg_get_int(
        cfg,
        "IterationEngine",
        "FG_CandidateLimit",
        default,
        clamp_min=int(min_limit),
        clamp_max=int(max_limit),
    )


def read_fg_search_radius(cfg: Any) -> int | None:
    """
    Read `[IterationEngine].FG_SearchRadius`.

    Semantics:
    - unset/empty => return None (use default radius elsewhere)
    - -1 => full window over all FT/FF allocations within TOTAL_GEM_BUDGET
    - >=0 => radius in gem-space around each loadout's (FT, FF) center
    """
    # PRODUCTION: FG tuning flag (FG_SearchRadius).
    raw = str(cfg_get(cfg, "IterationEngine", "FG_SearchRadius", str, "") or "").strip()
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
