# Gear Optimizer Refactoring Guide

## Executive Summary

Your 5,196-line monolith needs to be split into **8 focused modules** with clean separation of concerns. This guide provides the complete architecture and step-by-step instructions.

---

## 📁 Proposed Architecture

```
Gear Optimizer/
├── gear_optimizer/              # New package directory
│   ├── __init__.py             # Package initialization
│   ├── constants.py            # ✅ CREATED - Global constants (123 lines)
│   ├── models.py               # ✅ CREATED - Data classes (127 lines)
│   ├── utils.py                # Helpers & utilities (~300 lines)
│   ├── config.py               # Configuration management (~200 lines)
│   ├── database.py             # SQLite operations (~400 lines)
│   ├── csv_parser.py           # CSV parsing for gear/minis (~200 lines)
│   ├── memory.py               # Memory watchdog system (~350 lines)
│   ├── scoring.py              # Score calculation engine (~600 lines)
│   ├── genetic.py              # Genetic algorithm solver (~900 lines)
│   ├── song_processor.py       # Song processing orchestration (~800 lines)
│   └── discord_reporter.py     # Discord integration (~150 lines)
│
├── Manual_Calculator - Main.py # ⚠️  ORIGINAL (keep as backup)
├── main.py                     # ✅ NEW ENTRY POINT (~200 lines)
├── config.ini                  # Configuration file (unchanged)
├── Stats.csv                   # Data files (unchanged)
├── Gears.csv
├── Minis.csv
└── evolution.db                # Database (unchanged)
```

---

## 🎯 Module Breakdown

### 1. `constants.py` ✅ **CREATED**
**Lines:** ~150 | **Status:** Complete

**Contains:**
- `GEM_SCALE_NORMAL`, `GEM_SCALE_FEVER`, etc.
- `GA_POPULATION_SIZE`, `GA_GENERATIONS`, etc.
- `DB_FILE`, `LOADOUTS_PER_SONG_LIMIT`
- `PathConfig` dataclass
- Global `PATHS`, `SCRIPT_DIR`, `BIN_DIR`

**Exports:**
```python
from gear_optimizer.constants import PATHS, GA_POPULATION_SIZE, LOADOUTS_PER_SONG_LIMIT
```

---

### 2. `models.py` ✅ **CREATED**
**Lines:** ~130 | **Status:** Complete

**Contains:**
- `Tee` class (stdout multiplexer)
- `WarnOnce` class (warning deduplication)
- `GASettings` dataclass
- `MemoryGuardResumeTracker` class

**Exports:**
```python
from gear_optimizer.models import GASettings, Tee, WarnOnce
```

---

### 3. `utils.py` ⚠️ **TO CREATE**
**Lines:** ~300 | **Extract from:** Lines 54-66, 596-745

**Functions to move:**
```python
# Config serialization
cfg_to_dict(cfg) -> dict
cfg_from_dict(cfg_dict) -> ConfigParser

# Type conversion
safe_int(val, default=0) -> int
safe_float(val, default=0.0) -> float

# Stats helpers
empty_stats() -> dict
stats_signature(stats, calc_song, selected_color) -> tuple

# Gear optimization
is_dominated_by(a, b) -> bool
prune_dominated_gear(gear_list) -> list

# Constants
STAT_KEYS = [list of stat names]
DOMINANCE_KEYS = STAT_KEYS
SKIP_ITEM_KEYS = frozenset({"Name", "type"})
```

**Why separate:** Pure utility functions with no dependencies, highly reusable.

---

### 4. `config.py` ⚠️ **TO CREATE**
**Lines:** ~200 | **Extract from:** Lines 738-840, 1715-1830

**Functions to move:**
```python
compute_memory_guard_limit(cfg) -> int
write_metafinder_status(status, message=None) -> None
load_force_greats_config(cfg) -> dict
```

**Responsibilities:**
- Parse config.ini
- Validate settings
- Compute derived configuration (memory limits, etc.)
- Write status files for external monitoring

**Why separate:** Configuration is a cross-cutting concern, best isolated.

---

### 5. `database.py` ⚠️ **TO CREATE**
**Lines:** ~400 | **Extract from:** Lines 933-1323

**Functions to move:**
```python
# Core operations
get_evolution_db_path() -> str
get_db_connection(db_path=None) -> sqlite3.Connection
init_db() -> None

# Loadout persistence
save_loadout_to_db(song_name, score, fg_score, gear, minis, details, force_data) -> None
save_loadouts_batch(song_name, entries) -> None
get_best_loadouts(song_name, limit=50, ...) -> list

# Internal helpers
_compact_gear_for_db(gear_list) -> list
_compact_minis_for_db(mini_list) -> list
_expand_gear_from_db(gear_names, gears_by_name) -> list
_expand_minis_from_db(mini_names, minis_by_name) -> list
get_loadout_hash(gear_list, mini_list) -> str
```

**Why separate:** Database is a clear bounded context with specific responsibility.

---

### 6. `csv_parser.py` ⚠️ **TO CREATE**
**Lines:** ~200 | **Extract from:** Lines 1421-1712

**Functions to move:**
```python
parse_gear_rows(filepath) -> list[dict]
parse_mini_rows(filepath) -> list[dict]
load_stats_table(stats_csv_path) -> tuple[list, dict]
```

**Responsibilities:**
- Read CSV files
- Parse gear/mini/stats data
- Handle malformed data gracefully
- Return normalized data structures

**Why separate:** Data loading is distinct from business logic.

---

### 7. `memory.py` ⚠️ **TO CREATE**
**Lines:** ~350 | **Extract from:** Lines 246-595

**Functions to move:**
```python
# Memory monitoring
_bytes_to_gb(value) -> float
memory_release_requested() -> bool
get_memory_release_message() -> str
log_memory_usage(label="") -> None
trigger_memory_release(reason) -> None

# Watchdog system
_process_tree_rss_bytes(root_process, include_compressed=False) -> int
_memory_watchdog_loop() -> None
ensure_memory_watchdog_thread() -> None
set_memory_watchdog_limit(limit_bytes) -> None
detect_total_physical_memory() -> int

# Resume functionality
build_memory_guard_resume_context(...) -> dict
load_memory_guard_resume_queue(expected_context=None) -> tuple
restart_process_for_memory_guard() -> None
```

**Global state to move:**
```python
MEMORY_WATCHDOG_LIMIT_BYTES = 0
MEMORY_WATCHDOG_THREAD = None
MEMORY_WATCHDOG_EVENT = threading.Event()
MEMORY_WATCHDOG_REASON = ""
```

**Why separate:** Memory management is complex and should be isolated.

---

### 8. `scoring.py` ⚠️ **TO CREATE**
**Lines:** ~600 | **Extract from:** Lines 1830-2450

**Functions to move:**
```python
# Core scoring
lookup_reference_py(value, ref_array, total_rows=160) -> int
lookup_reference_jit(value, ref_array, total_rows) -> int
calculate_fever_timeline_indices(...) -> tuple
fast_calculate_score(...) -> tuple

# Optimization
optimize_core_jit(...) -> dict

# Force greats system
_force_greats_counts_to_dict(counts, sections) -> dict
build_great_penalty_table(...) -> np.ndarray
evaluate_force_greats(stats, calc_song, ref_arrays, forced_counts=None) -> dict
run_force_greats_hill_climb(stats, calc_song, ref_arrays) -> dict
apply_force_greats_to_result(data_dict, ...) -> dict

# Evaluation
evaluate_stats_score(stats, calc_song, ref_arrays, ...) -> dict
worker_coevolution_evaluate(args) -> tuple
```

**Global caches:**
```python
from cachetools import LRUCache
FEVER_TIMELINE_CACHE = LRUCache(maxsize=10000)
GEM_SOLVER_CACHE = LRUCache(maxsize=5000)
FG_CACHE = LRUCache(maxsize=2000)
```

**Why separate:** Scoring is the core algorithm, deserves its own module.

---

### 9. `genetic.py` ⚠️ **TO CREATE**
**Lines:** ~900 | **Extract from:** Lines 2570-3603

**Functions to move:**
```python
# Main GA solver
solve_best_fever_combination(...) -> tuple
solve_coevolution_genetic(...) -> tuple

# GA operators (extract from inside solve_coevolution_genetic)
create_random_genome(gear_pool, mini_pool, p_color) -> dict
mutate_genome(genome, gear_pool, mini_pool, rate) -> dict
crossover_genomes(parent1, parent2) -> dict
fitness_function(genome, ...) -> float
tournament_selection(population, k=3) -> dict
```

**Responsibilities:**
- Genetic algorithm implementation
- Population management
- Mutation/crossover operators
- Multi-start restart logic
- Memetic local search

**Why separate:** GA is complex enough to deserve its own module.

---

### 10. `song_processor.py` ⚠️ **TO CREATE**
**Lines:** ~800 | **Extract from:** Lines 1745-1829, 3604-4394

**Functions to move:**
```python
# Song I/O
scan_song_header(fp) -> dict
read_song_file(fp) -> dict

# Main processing (REFACTOR THESE!)
process_song_task(args) -> dict
safe_process_song_task(args) -> dict
```

**⚠️ CRITICAL REFACTORING NEEDED:**

Current `process_song_task` is 767 lines. Break into:

```python
def process_song_task(args) -> dict:
    """Main entry point - orchestrates song processing."""
    config = _parse_song_task_args(args)  # ~50 lines
    _setup_song_environment(config)       # ~30 lines

    if config.skip_optimization:
        return _calculate_only_mode(config)  # ~100 lines
    else:
        return _run_full_optimization(config)  # ~150 lines

def _run_full_optimization(config) -> dict:
    """Run GA optimization for a song."""
    db_loadouts = _load_database_seeds(config)     # ~50 lines
    result = _execute_genetic_algorithm(config, db_loadouts)  # ~100 lines
    _persist_results(result, config)                # ~50 lines
    return _build_result_payload(result, config)    # ~50 lines
```

Each helper function should be **50-150 lines max**.

---

### 11. `discord_reporter.py` ⚠️ **TO CREATE**
**Lines:** ~150 | **Extract from:** Lines 846-932

**Class to move:**
```python
class DiscordReporter:
    def __init__(self, webhook_url=None):
        ...

    def send_log(self, content):
        """Send a log message to Discord."""
        ...

    def send_stats(self, content):
        """Send stats update to Discord."""
        ...

def build_stats_summary(res, completed, total) -> str:
    """Build formatted stats message."""
    ...
```

**Why separate:** External integration should be isolated.

---

### 12. `main.py` ⚠️ **TO CREATE** (New Entry Point)
**Lines:** ~200 | **Replace:** Lines 4397-5196

**Structure:**
```python
#!/usr/bin/env python3
"""
Gear Optimizer - Main Entry Point
Refactored modular architecture
"""

import multiprocessing
from gear_optimizer import (
    constants,
    models,
    config,
    database,
    memory,
    song_processor,
    discord_reporter,
)

def main():
    """Main execution loop."""
    multiprocessing.freeze_support()

    # Initialize systems
    database.init_db()
    memory.ensure_memory_watchdog_thread()

    # Load configuration
    cfg = config.load_config()

    # Setup Discord reporting
    reporter = discord_reporter.DiscordReporter()

    # Process songs
    song_files = discover_song_files()
    results = process_all_songs(song_files, cfg, reporter)

    # Cleanup
    shutdown_gracefully()

if __name__ == "__main__":
    main()
```

---

## 🚀 Migration Steps

### Step 1: Create Utility Modules (Low Risk)
1. Create `utils.py` - extract pure functions
2. Create `config.py` - extract configuration logic
3. Update imports in main file to use new modules
4. Test: Verify program still runs

### Step 2: Extract Data Layers (Medium Risk)
1. Create `database.py` - move all SQLite code
2. Create `csv_parser.py` - move CSV parsing
3. Update imports
4. Test: Verify optimization runs end-to-end

### Step 3: Extract Core Algorithms (High Risk)
1. Create `scoring.py` - move score calculation
2. Create `genetic.py` - move GA solver
3. Update imports and test thoroughly
4. Test: Compare scores before/after refactoring

### Step 4: Refactor Monster Functions (Critical)
1. Break down `process_song_task` into helpers
2. Move to `song_processor.py`
3. Extensive testing required
4. Test: Process multiple songs, verify results match

### Step 5: Final Integration
1. Create `main.py` with clean orchestration
2. Move memory management to `memory.py`
3. Move Discord to `discord_reporter.py`
4. Final end-to-end testing

---

## ⚠️ Testing Strategy

### Before Refactoring
```bash
# Run optimizer and save output
python "Manual_Calculator - Main.py" > baseline_output.txt
# Save evolution.db as baseline.db
cp evolution.db baseline.db
```

### After Each Step
```bash
# Run with new architecture
python main.py > refactored_output.txt
# Compare scores
diff baseline_output.txt refactored_output.txt
```

**Critical Metrics to Verify:**
- Same best score for each song
- Same number of loadouts in database
- Same memory usage patterns
- No new exceptions/errors

---

## 📊 Benefits Summary

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Largest File** | 5,196 lines | ~900 lines | 82% reduction |
| **Longest Function** | 826 lines | <150 lines | 82% reduction |
| **Max Nesting** | 10 levels | <5 levels | 50% reduction |
| **Testability** | 3/10 | 9/10 | 200% improvement |
| **Maintainability** | 4/10 | 8/10 | 100% improvement |
| **Comments** | 5.7% | Target 15% | 163% increase |

---

## 🎓 Key Principles Applied

1. **Single Responsibility:** Each module has one clear purpose
2. **Dependency Inversion:** High-level modules don't depend on low-level details
3. **Interface Segregation:** Clean, minimal interfaces between modules
4. **DRY:** Eliminate duplication (e.g., DB compaction logic)
5. **Separation of Concerns:** Business logic ≠ I/O ≠ Configuration

---

## 📝 Next Steps

1. **Immediate:** Create the remaining module files following this guide
2. **Short-term:** Refactor the 3 monster functions
3. **Medium-term:** Add comprehensive docstrings (target 15% comments)
4. **Long-term:** Add unit tests for each module

**Time estimate:** 2-3 days of focused work for complete refactoring.

**Risk level:** Medium (high reward, requires thorough testing)

---

**This architecture transforms your working-but-messy code into professional, maintainable software engineering.**
