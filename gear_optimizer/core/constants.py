"""
Global constants and configuration values for the gear optimizer.
"""

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

# Fever Time constant offset added to scaled duration (seconds).
#
# 0.15 is the FEVER_TIME_SCALE-driven "+1000ms of song length" term from the
# reference scoring model's `lastNoteTimeSec`; this
# repo folds that same convention directly into the offset constant instead
# of a separate approx-length variable (algebraically identical).
#
# Decompiled server note-sequence scoring drains by event-time delta:
# DeltaTimeToTimescale(dt) * SecondsToTick(duration) algebraically cancels the
# 1/60 tick unit to dt / duration. There is no independent extra server tick in
# this path; keep only the +1000ms approximate-length term.
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
# without improving score quality consistently; the migration dispatch path was
# deleted (2026-07-03, dead at a single island). n_islands still parameterizes
# the next-generation kernel's elitism layout.
GPU_GA_NUM_ISLANDS = 1

# --- DATABASE CONFIGURATION ---
LOADOUTS_PER_SONG_LIMIT = 51  # Top 51 by score + Top 51 by FG score (single FG funnel + leaderboard size)

# --- SHARED ENUMS / TOKENS ---
DIFFICULTIES = ("Easy", "Normal", "Hard")

# --- MEMORY MANAGEMENT CONSTANTS ---
DEFAULT_MEMORY_GUARD_PERCENT = 50.0
STRICT_PLATFORM_MEMORY_GUARD_PERCENT = 35.0
MEMORY_WATCHDOG_INTERVAL_SEC = 5

# --- GEAR/MINI METADATA ---
# Keys to skip when aggregating gear/mini stats (metadata, not actual stats)
SKIP_ITEM_KEYS = frozenset(
    {
        "Name",
        "type",
        "Song Target",
        "Mini Ascension Enabled",
        "Mini Ascension Level",
        "Mini Ascension Source Version",
        "Mini Ascension Song Target Applied",
        "Mini Ascension Elemental Bonus",
        "Mini Ascension Match Qualities",
        "Mini Ascension Materialized",
        "Mini Ascension Materialized Song",
        "Mini Ascension Materialized Primary Color",
        "Mini Ascension Materialized Secondary Color",
        "Mini Ascension Base Chill",
        "Mini Ascension Base Flow",
        "Mini Ascension Base Rush",
        "Mini Ascension Base Beat",
        "Mini Ascension Base Vibe",
    }
)
