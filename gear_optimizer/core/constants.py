"""
Global constants and configuration values for the gear optimizer.
"""
import os
import configparser
from dataclasses import dataclass

# --- SCORING CONSTANTS ---
GEM_SCALE_NORMAL = 2
GEM_SCALE_FEVER = 3
ELEMENTAL_GEM_SCALE = 6
GEM_STAT_TO_ELEMENT_SCALE = 3

MAX_STAT_INDEX = 160
TOTAL_GEM_BUDGET = 90
TOTAL_ROWS = 160

# --- GA (GENETIC ALGORITHM) CONSTANTS ---
# These will be overwritten by config.ini if present
GA_POPULATION_SIZE = 250
GA_GENERATIONS = 75
GA_MUTATION_RATE = 0.275
GA_ELITISM = 1
GA_MULTI_RUNS_DEFAULT = 3  # Multi-start passes to escape local maxima
GA_MUTATION_RATE_MAX = 0.45  # Cap for adaptive mutation bumps

# --- DATABASE CONFIGURATION ---
DB_FILE = "evolution.db"
LOADOUTS_PER_SONG_LIMIT = 50  # Hard cap per song to keep DB size manageable

# --- CACHE LIMITS ---
# Memory leak fix: Use LRU with global limits instead of unbounded dicts
MAX_TIMELINE_CACHE_GLOBAL = 10000  # ~10MB max (was 500K per song)
MAX_GEM_SOLVER_CACHE = 5000        # ~10MB max
MAX_FG_CACHE = 2000                # ~6MB max

# --- MEMORY MANAGEMENT CONSTANTS ---
DEFAULT_MEMORY_GUARD_PERCENT = 50.0
STRICT_PLATFORM_MEMORY_GUARD_PERCENT = 35.0
MEMORY_WATCHDOG_INTERVAL_SEC = 5

# --- GEAR/MINI METADATA ---
# Keys to skip when aggregating gear/mini stats (metadata, not actual stats)
SKIP_ITEM_KEYS = frozenset({"Name", "type"})


@dataclass(frozen=True)
class PathConfig:
    """
    Centralized path configuration for the application.
    Handles script directory, binary directory, and status file location.
    """
    script_dir: str
    bin_dir: str
    status_file: str

    @classmethod
    def build(cls):
        """Build PathConfig with automatic detection and fallback logic."""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
        """Get a path within the bin directory."""
        return os.path.join(self.bin_dir, *parts)

    @property
    def discord_env(self):
        """Path to Discord.env file."""
        return os.path.join(self.script_dir, "Discord.env")

    @property
    def stats_csv(self):
        """Path to Stats.csv file."""
        return os.path.join(self.script_dir, "Stats.csv")

    @property
    def data_dir(self):
        """Path to Data directory containing song files."""
        return os.path.join(self.script_dir, "Data")

    @property
    def evolution_db_default(self):
        """Default path for evolution database."""
        return os.path.join(self.script_dir, DB_FILE)


# Global path configuration instance
PATHS = PathConfig.build()
SCRIPT_DIR = PATHS.script_dir
BIN_DIR = PATHS.bin_dir
STATUS_FILE = PATHS.status_file
