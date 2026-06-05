"""
Global constants and configuration values for the gear optimizer.
"""

import os
from dataclasses import dataclass

# --- SCORING CONSTANTS ---
GEM_SCALE_NORMAL = 2
GEM_SCALE_FEVER = 3
ELEMENTAL_GEM_SCALE = 6
GEM_STAT_TO_ELEMENT_SCALE = 3

MAX_STAT_INDEX = 160
TOTAL_GEM_BUDGET = 90
TOTAL_ROWS = 160

# --- GAME FORMULA CONSTANTS (RoBeats Server Parity) ---
# These values are reverse-engineered from RoBeats game source code
# and must match server-side calculations for score accuracy.
# Reference: docs/FORMULA EXPLANATION.txt, docs/FEVER_TIMELINE_MATH.md

# Fever Fill Rate base multiplier (key point on the stat curve)
# Formula: non_fever_cas = (total_notes - long_notes) * FEVER_FILL_BASE_RATE
FEVER_FILL_BASE_RATE = 0.333

# Fever Time duration scaling factor (percentage of song length)
# Formula: fever_time_cas = last_note_time * FEVER_TIME_SCALE + FEVER_TIME_OFFSET
FEVER_TIME_SCALE = 0.15

# Fever Time constant offset added to scaled duration (seconds)
FEVER_TIME_OFFSET = 0.15

# --- GA (GENETIC ALGORITHM) CONSTANTS ---
# These will be overwritten by config.ini if present
#
# EXPLORATION vs EXPLOITATION TUNING:
# - Higher mutation_rate = more exploration (random changes)
# - More multi_runs = more fresh starts (escape local optima)
# - Elitism = exploitation (preserving best solutions)
GA_POPULATION_SIZE = 705  # 1.5x of 470; keep moderate for diversity + speed
GA_MUTATION_RATE = 0.35  # INCREASED: 0.275 → 0.35 (more exploration)
GA_ELITISM = 1  # Keep 1 elite (exploitation anchor)
GA_MULTI_RUNS_DEFAULT = 3

# Local search constants
PP_TIE_LOOKAHEAD_MAX = 8  # Max lookahead iterations for PP tie-breaking in gem optimization

# --- GPU GA ISLAND MODEL ---
# Real-song benchmarks showed island migration amplifying exact-clone pressure
# without improving score quality consistently, so keep the default on a single
# island until migration is revisited.
GPU_GA_NUM_ISLANDS = 1
GPU_GA_GENS_PER_MIGRATION = 5  # Generations between elite migrations
GPU_GA_MIGRATE_COUNT = 2  # Elites to migrate per island (ring topology)

# --- DATABASE CONFIGURATION ---
DB_FILE = "evolution.db"
LOADOUTS_PER_SONG_LIMIT = 51  # Top 51 by score + Top 51 by FG score (single FG funnel + leaderboard size)

# --- SHARED ENUMS / TOKENS ---
DIFFICULTIES = ("Easy", "Normal", "Hard")

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
        # config.ini, Data/, bin/, etc resolve correctly.
        script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        bin_dir = os.path.join(script_dir, "bin")

        return cls(script_dir, bin_dir)

    def bin_path(self, *parts):
        """Get a path within the bin directory."""
        return os.path.join(self.bin_dir, *parts)

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
