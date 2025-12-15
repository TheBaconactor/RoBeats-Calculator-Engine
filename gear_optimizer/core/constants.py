"""
Global constants and configuration values for the gear optimizer.
"""
import os
import configparser
import logging
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
# 
# EXPLORATION vs EXPLOITATION TUNING:
# - Higher mutation_rate = more exploration (random changes)
# - More multi_runs = more fresh starts (escape local optima)
# - Elitism = exploitation (preserving best solutions)
GA_POPULATION_SIZE = 250          # Balance: keep moderate for diversity + speed
GA_GENERATIONS = 75               # Enough iterations per run
GA_MUTATION_RATE = 0.35           # INCREASED: 0.275 → 0.35 (more exploration)
GA_ELITISM = 1                    # Keep 1 elite (exploitation anchor)
GA_MULTI_RUNS_DEFAULT = 5         # INCREASED: 3 → 5 (more fresh starts)
GA_MUTATION_RATE_MAX = 0.55       # INCREASED: 0.45 → 0.55 (allow more aggressive mutation on stagnation)

# --- GPU GA ISLAND MODEL ---
GPU_GA_NUM_ISLANDS = 5            # Number of sub-populations (islands)
GPU_GA_GENS_PER_MIGRATION = 5     # Generations between elite migrations
GPU_GA_MIGRATE_COUNT = 2          # Elites to migrate per island (ring topology)

# --- DATABASE CONFIGURATION ---
DB_FILE = "evolution.db"
LOADOUTS_PER_SONG_LIMIT = 100  # Hard cap per song to keep DB size manageable

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

    @classmethod
    def build(cls):
        """Build PathConfig with automatic detection and fallback logic."""
        # Project root resolution:
        # This file lives at: <root>/gear_optimizer/core/constants.py
        # We want <root> as the script_dir so that user-facing files like
        # config.ini, Discord.env, Data/, bin/, etc resolve correctly.
        script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        bin_dir = os.path.join(script_dir, "bin")

        return cls(script_dir, bin_dir)

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
