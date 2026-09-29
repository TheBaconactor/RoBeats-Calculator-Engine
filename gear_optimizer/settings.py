"""Engine settings: where the engine's files live, what a run solves, and the operational switches.

Paths and switches come from the environment, so the :8765 service can give each solve its own data, bin,
database and caches; they are read on every call, so they always reflect the current environment. What a run
solves comes from config.ini. Both are parsed strictly: a malformed value or an unknown key is an error that names
it, never a silent default.

Environment variables the engine reads (every one of them):
  Paths
    ROBEATSMETA_OPTIMIZER_DATA_DIR      song charts and game data         default <engine>/Data
    ROBEATSMETA_OPTIMIZER_BIN_DIR       runtime state (logs, locks)       default <engine>/bin
    METAFINDER_CONFIG_PATH              run config                        default <engine>/config.ini
    EVOLUTION_DB_PATH                   results database                  default <engine>/evolution.db
    TIMELINE_FRONTIER_CACHE_DIR         timing frontier cache             default <bin>/timeline_frontier_cache
    FG_RESPONSE_FRONTIER_CACHE_DIR      Force Great frontier cache        default <bin>/fg_response_frontier_cache
  Run
    GA_SEED                             fixed search seed (reproducible runs); unset = a fresh seed per run
    TAICHI_VULKAN_VISIBLE_DEVICE        GPU to use when several are visible
    METAFINDER_OUTPUT                   print progress/results to the console (1/0)
    METAFINDER_PROGRESS                 1 forces the progress bar on, 0 off; unset = on in an interactive terminal
    ROBEATSMETA_OPTIMIZER_SERVICE_MODE  running under the :8765 service (no self-update, GPU request timeouts,
                                        GPU runtime failures stop the process)
    ROBEATSMETA_OPTIMIZER_PERSISTENT_WORKER  keep the GPU executor alive between service solves
  :8765 service (see ServiceSettings) and MetaFinder distribution (see MetaFinderSettings).
"""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parents[1]
DIFFICULTIES = ("Easy", "Normal", "Hard")

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off", ""}


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


def _env_path(name: str, default: Path) -> Path:
    value = _env(name)
    return Path(value).expanduser() if value else default


def _env_bool(name: str, default: bool) -> bool:
    value = _env(name).lower()
    if not value:
        return default
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    raise ValueError(f"{name} must be 1/0, true/false, yes/no or on/off, got {os.environ[name]!r}")


def _env_int(name: str, default: int, *, minimum: int | None = None) -> int:
    value = _env(name)
    if not value:
        return default
    try:
        number = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {value!r}") from exc
    if minimum is not None and number < minimum:
        raise ValueError(f"{name} must be at least {minimum}, got {number}")
    return number


@dataclass(frozen=True, slots=True)
class Paths:
    data_dir: Path
    bin_dir: Path
    config_file: Path
    database: Path
    timeline_cache: Path
    fg_cache: Path

    @property
    def gear_dir(self) -> Path:
        return self.data_dir / "Gear"

    @property
    def gears_csv(self) -> Path:
        return self.gear_dir / "Gears.csv"

    @property
    def minis_csv(self) -> Path:
        return self.gear_dir / "Minis.csv"

    @property
    def stats_txt(self) -> Path:
        return self.gear_dir / "Stats.txt"

    def chart_dir(self, difficulty: str) -> Path:
        if difficulty not in DIFFICULTIES:
            raise ValueError(f"unknown difficulty {difficulty!r}; expected one of {DIFFICULTIES}")
        return self.data_dir / difficulty

    def bin_path(self, *parts: str) -> Path:
        return self.bin_dir.joinpath(*parts)


def paths() -> Paths:
    data_dir = _env_path("ROBEATSMETA_OPTIMIZER_DATA_DIR", ENGINE_ROOT / "Data")
    bin_dir = _env_path("ROBEATSMETA_OPTIMIZER_BIN_DIR", ENGINE_ROOT / "bin")
    return Paths(
        data_dir=data_dir,
        bin_dir=bin_dir,
        config_file=_env_path("METAFINDER_CONFIG_PATH", ENGINE_ROOT / "config.ini"),
        database=_env_path("EVOLUTION_DB_PATH", ENGINE_ROOT / "evolution.db"),
        timeline_cache=_env_path("TIMELINE_FRONTIER_CACHE_DIR", bin_dir / "timeline_frontier_cache"),
        fg_cache=_env_path("FG_RESPONSE_FRONTIER_CACHE_DIR", bin_dir / "fg_response_frontier_cache"),
    )


@dataclass(frozen=True, slots=True)
class RunSettings:
    """config.ini: which charts a run solves and how hard it searches."""

    # [CalculateSong]
    song_name: str = ""
    difficulty: str = "All"
    target_primary: str = "All"
    target_secondary: str = "All"
    loop_forever: bool = False
    # [IterationEngine]
    song_repeats: int = 1
    song_queue_limit: int = 0
    ignore_resume_queue: bool = False
    search_depth: int = 125
    multi_start: int = 3
    memory_soft_limit_gb: float = 0.0  # 0: no absolute cap
    memory_soft_limit_percent: float | None = None  # None: the platform default; <= 0 disables


# (section, key as configparser lowercases it) -> (RunSettings field, value type)
_CONFIG_KEYS: dict[tuple[str, str], tuple[str, type]] = {
    ("CalculateSong", "song_name"): ("song_name", str),
    ("CalculateSong", "difficulty"): ("difficulty", str),
    ("CalculateSong", "targetprimary"): ("target_primary", str),
    ("CalculateSong", "targetsecondary"): ("target_secondary", str),
    ("CalculateSong", "loopforever"): ("loop_forever", bool),
    ("IterationEngine", "songrepeats"): ("song_repeats", int),
    ("IterationEngine", "songqueuelimit"): ("song_queue_limit", int),
    ("IterationEngine", "ignoreresumequeue"): ("ignore_resume_queue", bool),
    ("IterationEngine", "ga_searchdepth"): ("search_depth", int),
    ("IterationEngine", "ga_multistart"): ("multi_start", int),
    ("IterationEngine", "memorysoftlimitgb"): ("memory_soft_limit_gb", float),
    ("IterationEngine", "memorysoftlimitpercent"): ("memory_soft_limit_percent", float),
}


def _parse_value(raw: str, kind: type, *, where: str):
    text = raw.strip()
    if kind is str:
        return text
    if kind is bool:
        if text.lower() in _TRUE:
            return True
        if text.lower() in _FALSE:
            return False
        raise ValueError(f"{where} must be true/false, got {raw!r}")
    try:
        return kind(text)
    except ValueError as exc:
        raise ValueError(f"{where} must be {'an integer' if kind is int else 'a number'}, got {raw!r}") from exc


def read_run_settings(path: Path | None = None) -> RunSettings:
    """Read config.ini (a missing file means all defaults). Unknown sections or keys are errors."""
    config_file = path if path is not None else paths().config_file
    parser = configparser.ConfigParser()
    if config_file.is_file():
        parser.read(config_file, encoding="utf-8-sig")
    values = {}
    for section in parser.sections():
        for key, raw in parser.items(section):
            known = _CONFIG_KEYS.get((section, key))
            if known is None:
                raise ValueError(f"{config_file}: [{section}] {key} is not a config.ini setting (removed or misspelled)")
            name, kind = known
            values[name] = _parse_value(raw, kind, where=f"{config_file}: [{section}] {key}")
    settings = RunSettings(**values)
    if settings.song_repeats < 1 or settings.song_queue_limit < 0 or settings.search_depth < 1 or settings.multi_start < 1:
        raise ValueError(f"{config_file}: SongRepeats/GA_SearchDepth/GA_MultiStart must be >= 1, SongQueueLimit >= 0")
    return settings


def ga_seed() -> int | None:
    value = _env("GA_SEED")
    if not value:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"GA_SEED must be an integer, got {value!r}") from exc


def vulkan_device() -> str:
    return _env("TAICHI_VULKAN_VISIBLE_DEVICE")


def output_enabled() -> bool:
    return _env_bool("METAFINDER_OUTPUT", False)


def progress() -> bool | None:
    """METAFINDER_PROGRESS: True/False when set, None when unset (the caller decides)."""
    if not _env("METAFINDER_PROGRESS"):
        return None
    return _env_bool("METAFINDER_PROGRESS", False)


def service_mode() -> bool:
    return _env_bool("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", False)


def persistent_worker() -> bool:
    return _env_bool("ROBEATSMETA_OPTIMIZER_PERSISTENT_WORKER", False)


@dataclass(frozen=True, slots=True)
class ServiceSettings:
    """The :8765 HTTP service (ROBEATSMETA_OPTIMIZER_*)."""

    host: str
    port: int
    api_token: str  # required for a non-loopback bind
    solve_pool: int  # concurrent solves admitted
    min_free_mb: int  # free memory a new solve waits for
    max_body_bytes: int
    max_custom_chart_events: int
    solve_timeout_s: int
    repeats: int  # optimizer repeats per solve
    persistent_solver: bool  # official solves reuse one warm worker process
    persistent_idle_exit_s: int
    run_dir: str  # per-solve workspaces; empty = the service's default
    catalog_data_dir: str  # official chart library; empty = <engine>/Data
    gear_source_dir: str  # game data copied into a persistent worker's data dir


def service_settings() -> ServiceSettings:
    return ServiceSettings(
        host=_env("ROBEATSMETA_OPTIMIZER_API_HOST") or "127.0.0.1",
        port=_env_int("ROBEATSMETA_OPTIMIZER_API_PORT", 8765, minimum=1),
        api_token=_env("ROBEATSMETA_OPTIMIZER_API_TOKEN"),
        solve_pool=_env_int("ROBEATSMETA_OPTIMIZER_SERVICE_POOL", 10, minimum=1),
        min_free_mb=_env_int("ROBEATSMETA_OPTIMIZER_SERVICE_MIN_FREE_MB", 3000, minimum=0),
        max_body_bytes=_env_int("ROBEATSMETA_OPTIMIZER_MAX_BODY_BYTES", 32 * 1024 * 1024, minimum=1024),
        max_custom_chart_events=_env_int("ROBEATSMETA_OPTIMIZER_MAX_CUSTOM_EVENTS", 4_000, minimum=1),
        solve_timeout_s=_env_int("ROBEATSMETA_OPTIMIZER_SERVICE_TIMEOUT_S", 30 * 60, minimum=1),
        repeats=_env_int("ROBEATSMETA_OPTIMIZER_SERVICE_REPEATS", 1, minimum=1),
        persistent_solver=_env_bool("ROBEATSMETA_OPTIMIZER_PERSISTENT_SOLVER", True),
        persistent_idle_exit_s=_env_int("ROBEATSMETA_OPTIMIZER_PERSISTENT_IDLE_EXIT_S", 15 * 60, minimum=60),
        run_dir=_env("ROBEATSMETA_OPTIMIZER_SERVICE_RUN_DIR"),
        catalog_data_dir=_env("ROBEATSMETA_OPTIMIZER_CATALOG_DATA_DIR"),
        gear_source_dir=_env("ROBEATSMETA_OPTIMIZER_GEAR_SOURCE_DIR"),
    )


@dataclass(frozen=True, slots=True)
class MetaFinderSettings:
    """MetaFinder distribution: the client syncing from the server, and the server publishing to clients."""

    server_url: str  # METAFINDER_FRONTIER_SERVER_URL (client; required to sync)
    credentials_file: Path  # METAFINDER_FRONTIER_CREDENTIALS_FILE (client)
    clients_file: Path  # ROBEATSMETA_FRONTIER_CLIENTS_FILE (server)
    publication_dir: Path  # ROBEATSMETA_FRONTIER_PUBLICATION_DIR (server)
    source_dir: Path  # ROBEATSMETA_FRONTIER_SOURCE_DIR (server)
    git_remote: str
    git_branch: str
    git_poll_seconds: int
    git_timeout_seconds: int


def metafinder_settings() -> MetaFinderSettings:
    bin_dir = paths().bin_dir
    return MetaFinderSettings(
        server_url=_env("METAFINDER_FRONTIER_SERVER_URL").rstrip("/"),
        credentials_file=_env_path("METAFINDER_FRONTIER_CREDENTIALS_FILE", bin_dir / "frontier_client_credentials.json"),
        clients_file=_env_path("ROBEATSMETA_FRONTIER_CLIENTS_FILE", bin_dir / "frontier_server_clients.json"),
        publication_dir=_env_path("ROBEATSMETA_FRONTIER_PUBLICATION_DIR", bin_dir / "frontier_publications"),
        source_dir=_env_path("ROBEATSMETA_FRONTIER_SOURCE_DIR", bin_dir / "frontier_server_sources"),
        git_remote=_env("ROBEATSMETA_FRONTIER_GIT_REMOTE") or "origin",
        git_branch=_env("ROBEATSMETA_FRONTIER_GIT_BRANCH") or "main",
        git_poll_seconds=_env_int("ROBEATSMETA_FRONTIER_GIT_POLL_SECONDS", 300, minimum=60),
        git_timeout_seconds=_env_int("ROBEATSMETA_FRONTIER_GIT_TIMEOUT_SECONDS", 120, minimum=30),
    )
