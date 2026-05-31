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
    from .memory import detect_total_physical_memory
    platform_default_percent = (
        STRICT_PLATFORM_MEMORY_GUARD_PERCENT
        if sys.platform in ("win32", "cygwin", "darwin")
        else DEFAULT_MEMORY_GUARD_PERCENT
    )
    limit_gb = cfg.getfloat("IterationEngine", "MemorySoftLimitGB", fallback=0.0)
    limit_percent = cfg.getfloat(
        "IterationEngine",
        "MemorySoftLimitPercent",
        fallback=platform_default_percent,
    )
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
def _assert_no_obsolete_force_greats_modes(cfg: Any) -> None:
    if cfg is None:
        return
    try:
        if cfg.has_section("ForceGreats"):
            raise ValueError(
                "[ForceGreats] manual config was removed; response-frontier is the only supported ForceGreats scorer."
            )
        if cfg.has_option("IterationEngine", "ForceGreatsManual"):
            raw = str(cfg.get("IterationEngine", "ForceGreatsManual", fallback="") or "").strip()
            if raw:
                raise ValueError(
                    "IterationEngine.ForceGreatsManual was removed; response-frontier is the only supported ForceGreats scorer."
                )
        for option in ("ForceGreatsMode", "FG_SolverMode", "ForceGreatsFinder", "FG_SearchRadius"):
            if cfg.has_option("IterationEngine", option):
                raise ValueError(
                    f"IterationEngine.{option} was removed; response-frontier is the only supported ForceGreats scorer."
                )
    except (AttributeError, TypeError, configparser.Error) as exc:
        raise ValueError("Invalid ForceGreats config surface; response-frontier is the only supported scorer.") from exc


@dataclass(frozen=True)
class IterationEngineSettings:
    """
    Parsed, normalized settings from the `[IterationEngine]` section.
    Centralizing this avoids logic drift across the app, workers, and solver code.
    """
    force_greats_debug: bool
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
    search_depth: int = 125
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
        search_depth = cfg_get_int(
            cfg,
            "IterationEngine",
            "GA_SearchDepth",
            125,
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
            search_depth=int(search_depth),
            multi_start=int(multi_start),
        )
@dataclass(frozen=True, slots=True)
class InflightSettings:
    songs: int = 0
    song_file_cache_max: int = 0
    team_buff_calc_cache_max: int = 0
    ga_queue_mult: int = 0
    @classmethod
    def from_config(cls, cfg: Any) -> "InflightSettings":
        if cfg is None:
            return cls()
        songs = cfg_get_int(cfg, "IterationEngine", "InFlightSongs", 0, clamp_min=0)
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
    loop_forever: bool = False
    @classmethod
    def from_config(cls, cfg: Any) -> "CalculateSongSettings":
        if cfg is None:
            return cls()
        difficulty = cfg_get(cfg, "CalculateSong", "Difficulty", str, "All")
        song_name = cfg_get(cfg, "CalculateSong", "Song_Name", str, "")
        target_primary = cfg_get(cfg, "CalculateSong", "TargetPrimary", str, "")
        target_secondary = cfg_get(cfg, "CalculateSong", "TargetSecondary", str, "")
        loop_forever = cfg_get_bool(cfg, "CalculateSong", "LoopForever", False)
        return cls(
            difficulty=str(difficulty or "All"),
            song_name=str(song_name or ""),
            target_primary=str(target_primary or ""),
            target_secondary=str(target_secondary or ""),
            loop_forever=bool(loop_forever),
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
        loop_forever = bool(calculate_song.loop_forever)
        eval_cpu_cores = cfg_get_int(cfg, "IterationEngine", "EvalCPUCores", 0, clamp_min=0)
        song_queue_limit = cfg_get_int(cfg, "IterationEngine", "SongQueueLimit", 0, clamp_min=0)
        ignore_resume_queue = cfg_get_bool(cfg, "IterationEngine", "IgnoreResumeQueue", False)
        song_repeats = cfg_get_int(cfg, "IterationEngine", "SongRepeats", 1, clamp_min=1)
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
            loop_restart_wait_sec=float(loop_restart_wait_sec),
        )
def read_iteration_engine_settings(cfg: Any) -> IterationEngineSettings:
    """
    Read and normalize `[IterationEngine]` behavior settings.
    Important semantics:
    - Production optimizer mode is always active.
    - These are no longer config switches; they are native runtime policy.
    - ForceGreats has exactly one production scorer: response-frontier.
    """
    _assert_no_obsolete_force_greats_modes(cfg)
    force_greats_debug = cfg_get_bool(cfg, "IterationEngine", "ForceGreatsDebug", False) if cfg is not None else False
    return IterationEngineSettings(
        force_greats_debug=bool(force_greats_debug),
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
    return cfg_get_int(
        cfg,
        "IterationEngine",
        "FG_CandidateLimit",
        default,
        clamp_min=int(min_limit),
        clamp_max=int(max_limit),
    )
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
                    continue
        except (OSError, PermissionError):
            continue
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
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
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
    warn_fallback("config.paths_cache.miss", "paths cache missing/invalid; running path discovery")
    print("[Paths] Discovering data file paths...")
    return find_and_cache_paths()
