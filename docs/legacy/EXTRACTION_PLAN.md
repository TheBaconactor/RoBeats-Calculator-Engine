# Scoring Module Extraction Plan

> [!WARNING]
> **Legacy / archived:** This document lives under `docs/legacy/` and may not match the current code layout/config. See `docs/NAVIGATION.md` for current entrypoints/paths.

## Status: Creating scoring.py module

Due to the size and complexity of the scoring engine (~600-800 lines), I'm creating a comprehensive module that includes:

### Functions Being Extracted (Lines 1830-2570)

**JIT-Compiled Core Functions:**
- `lookup_reference_py()` - Line 1830
- `lookup_reference_jit()` - Line 1836 (JIT)
- `calculate_fever_timeline_indices()` - Line 1846 (JIT, ~65 lines)
- `fast_calculate_score()` - Line 1913 (JIT, ~40 lines)
- `optimize_core_jit()` - Line 1953 (JIT, ~170 lines)

**Evaluation Functions:**
- `worker_coevolution_evaluate()` - Line 2122 (~50 lines)
- `evaluate_stats_score()` - Line 2174 (~60 lines)

**Force Greats System:**
- `_force_greats_counts_to_dict()` - Line 2235
- `build_great_penalty_table()` - Line 2243
- `evaluate_force_greats()` - Line 2258 (~160 lines)
- `run_force_greats_hill_climb()` - Line 2418 (~30 lines)
- `apply_force_greats_to_result()` - Line 2508 (~60 lines)

**Fever Combination Solver:**
- `solve_best_fever_combination()` - Line 2570 (~300 lines!)

### Global State:
- `FEVER_TIMELINE_CACHE` (LRUCache)
- `GEM_SOLVER_CACHE` (LRUCache)
- `FG_CACHE` (LRUCache)

### Dependencies:
- JIT setup (jit_setup.py) ✅ Created
- Constants (constants.py) ✅ Already have
- Utils (utils.py) ✅ Already have

### Total Lines: ~800 lines

## Next Step:
Creating scoring.py with complete implementation...
