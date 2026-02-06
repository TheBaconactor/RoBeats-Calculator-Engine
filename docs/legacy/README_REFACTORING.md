# Refactoring Status & Next Steps

> [!WARNING]
> **Legacy / archived:** This document lives under `docs/legacy/` and may not match the current code layout/config. See `docs/NAVIGATION.md` for current entrypoints/paths.

## ✅ What Has Been Created

### 1. Package Structure
```
gear_optimizer/
├── __init__.py          ✅ Created
├── constants.py         ✅ Created (150 lines)
└── models.py            ✅ Created (127 lines)
```

### 2. Documentation
```
REFACTORING_GUIDE.md     ✅ Created - Complete step-by-step guide
ARCHITECTURE.md          ✅ Created - System architecture & design patterns
```

---

## 🎯 Your 5,196-Line File Broken Down

### Current State: Single Monolith
```
Manual_Calculator - Main.py: 5,196 lines
└─ 68 functions
└─ 6 classes
└─ 826-line monster function (safe_process_song_task)
└─ 767-line monster function (process_song_task)
└─ 727-line monster function (solve_coevolution_genetic)
```

### Target State: 12 Focused Modules
```
gear_optimizer/
├── constants.py           150 lines  ✅ Done
├── models.py              127 lines  ✅ Done
├── utils.py               300 lines  ⏳ To extract
├── config.py              200 lines  ⏳ To extract
├── database.py            400 lines  ⏳ To extract
├── csv_parser.py          200 lines  ⏳ To extract
├── memory.py              350 lines  ⏳ To extract
├── scoring.py             600 lines  ⏳ To extract
├── genetic.py             900 lines  ⏳ To extract
├── song_processor.py      800 lines  ⏳ To extract
└── discord_reporter.py    150 lines  ⏳ To extract

main.py                    200 lines  ⏳ To create
```

---

## 📋 Extraction Checklist

### Phase 1: Foundation (2-3 hours)
- [ ] Create `utils.py`
  - [ ] Move `cfg_to_dict()` and `cfg_from_dict()` (lines 54-66)
  - [ ] Move `safe_int()` and `safe_float()` (lines 713-735)
  - [ ] Move `empty_stats()` (line 707-709)
  - [ ] Move `stats_signature()` (lines 596-640)
  - [ ] Move `is_dominated_by()` and `prune_dominated_gear()` (lines 646-686)
  - [ ] Move `STAT_KEYS`, `DOMINANCE_KEYS` (lines 690-704)

- [ ] Create `config.py`
  - [ ] Move `compute_memory_guard_limit()` (lines 738-800)
  - [ ] Move `write_metafinder_status()` (find with grep)
  - [ ] Move `load_force_greats_config()` (line 1715+)

- [ ] Update imports in main file
- [ ] Test: Verify program runs

### Phase 2: Data Layer (3-4 hours)
- [ ] Create `database.py`
  - [ ] Move all functions from lines 933-1323
  - [ ] Includes: `get_db_connection()`, `init_db()`, `save_loadout_to_db()`, etc.
  - [ ] Move global `DB_FILE` path logic

- [ ] Create `csv_parser.py`
  - [ ] Move `parse_gear_rows()` (line 1421+)
  - [ ] Move `parse_mini_rows()` (line 1513+)
  - [ ] Move `load_stats_table()` (find with grep)

- [ ] Update imports
- [ ] Test: Verify data loads correctly

### Phase 3: Core Algorithm (4-5 hours)
- [ ] Create `scoring.py`
  - [ ] Move scoring functions (lines 1830-2450)
  - [ ] Move global caches: `GEM_SOLVER_CACHE`, `FEVER_TIMELINE_CACHE`, `FG_CACHE`
  - [ ] Includes JIT-compiled functions

- [ ] Create `genetic.py`
  - [ ] Move `solve_best_fever_combination()` (line 2570+)
  - [ ] Move `solve_coevolution_genetic()` (line 2877+)
  - [ ] **REFACTOR:** Break 727-line function into smaller helpers

- [ ] Update imports
- [ ] Test: Run full optimization, compare scores

### Phase 4: Infrastructure (2-3 hours)
- [ ] Create `memory.py`
  - [ ] Move memory watchdog code (lines 246-595)
  - [ ] Move global state: `MEMORY_WATCHDOG_*` variables

- [ ] Create `discord_reporter.py`
  - [ ] Move `DiscordReporter` class (line 846+)
  - [ ] Move `build_stats_summary()` function

- [ ] Update imports
- [ ] Test: Verify memory management works

### Phase 5: Orchestration (4-5 hours) **CRITICAL**
- [ ] Create `song_processor.py`
  - [ ] Move `scan_song_header()` (line 1745+)
  - [ ] Move `read_song_file()` (line 1774+)
  - [ ] Move `process_song_task()` (line 3604+)
  - [ ] **REFACTOR:** Break 767-line function into:
    - [ ] `_parse_song_task_args()` - Extract args parsing
    - [ ] `_setup_song_environment()` - Setup caches, buffers
    - [ ] `_calculate_only_mode()` - Non-optimization path
    - [ ] `_run_full_optimization()` - GA optimization path
    - [ ] `_load_database_seeds()` - Load previous results
    - [ ] `_execute_genetic_algorithm()` - Run GA
    - [ ] `_persist_results()` - Save to DB
    - [ ] `_build_result_payload()` - Format output
  - [ ] Move `safe_process_song_task()` (line 4371+)

- [ ] Create `main.py`
  - [ ] Move `if __name__ == "__main__":` section (line 4397+)
  - [ ] Simplify to clean orchestration logic
  - [ ] Import all modules

- [ ] Test: Full end-to-end run

### Phase 6: Final Testing (2-3 hours)
- [ ] Run baseline test with original code
- [ ] Run test with refactored code
- [ ] Compare outputs:
  - [ ] Same best scores
  - [ ] Same number of loadouts
  - [ ] No new errors
- [ ] Memory profiling
- [ ] Performance benchmarking
- [ ] Clean up any issues

---

## 🚀 Quick Start Commands

### Extract a Module (Example: utils.py)
```bash
# 1. Create the file
touch gear_optimizer/utils.py

# 2. Add imports at top
echo "from .constants import STAT_KEYS, SKIP_ITEM_KEYS" >> gear_optimizer/utils.py

# 3. Extract functions (manual copy-paste from original)
# Lines 54-66:   cfg_to_dict, cfg_from_dict
# Lines 713-735: safe_int, safe_float
# Lines 707-709: empty_stats
# Lines 596-640: stats_signature
# Lines 646-686: is_dominated_by, prune_dominated_gear

# 4. Update imports in main file
# Add at top: from gear_optimizer.utils import safe_int, safe_float, ...

# 5. Test
python "Manual_Calculator - Main.py"
```

### Test Refactoring
```bash
# Run before refactoring
python "Manual_Calculator - Main.py" > output_before.txt

# After each module extraction
python "Manual_Calculator - Main.py" > output_after.txt
diff output_before.txt output_after.txt

# Should show no differences in scores!
```

---

## 📊 Progress Tracker

| Module | Status | Lines | Priority | Time Est |
|--------|--------|-------|----------|----------|
| constants.py | ✅ Complete | 150 | P0 | 0h (done) |
| models.py | ✅ Complete | 127 | P0 | 0h (done) |
| utils.py | ⏳ Pending | 300 | P1 | 1h |
| config.py | ⏳ Pending | 200 | P1 | 1h |
| database.py | ⏳ Pending | 400 | P1 | 2h |
| csv_parser.py | ⏳ Pending | 200 | P1 | 1h |
| memory.py | ⏳ Pending | 350 | P2 | 2h |
| scoring.py | ⏳ Pending | 600 | P2 | 3h |
| genetic.py | ⏳ Pending | 900 | P2 | 4h |
| song_processor.py | ⏳ Pending | 800 | P3 | 5h |
| discord_reporter.py | ⏳ Pending | 150 | P3 | 1h |
| main.py | ⏳ Pending | 200 | P3 | 2h |

**Total Estimated Time:** 22-24 hours (3 full days)

**Completion:** 2/12 modules (16.7%)

---

## 💡 Pro Tips

### 1. Extract in Order
Follow the dependency hierarchy (see ARCHITECTURE.md):
- Level 1 first (utils, config)
- Level 2 next (database, csv_parser, memory)
- Level 3+ last (scoring, genetic, song_processor)

### 2. Test After Each Module
Don't extract everything at once. Test after each module to catch issues early.

### 3. Use Git Branches
```bash
git checkout -b refactor/extract-utils
# Extract utils.py
git commit -m "Extract utils module"

git checkout -b refactor/extract-database
# Extract database.py
git commit -m "Extract database module"
```

### 4. Keep Original Intact
Don't delete from `Manual_Calculator - Main.py` until fully migrated to new structure.

### 5. Add Docstrings As You Go
When extracting a function, add a proper docstring:
```python
def safe_int(val, default=0):
    """
    Safely convert a value to an integer with fallback.

    Args:
        val: Value to convert (str, int, float, or None)
        default: Default value if conversion fails

    Returns:
        int: Converted integer or default

    Examples:
        >>> safe_int("123")
        123
        >>> safe_int("invalid", 999)
        999
    """
    try:
        ...
```

---

## 🎯 Success Criteria

Your refactoring is complete when:

1. ✅ All modules created (12/12)
2. ✅ No function > 150 lines
3. ✅ No nesting > 5 levels
4. ✅ Comment ratio > 15%
5. ✅ All tests pass
6. ✅ Same optimization results as original
7. ✅ Clean import structure (no circular dependencies)
8. ✅ Each module has single, clear purpose

---

## 📞 Need Help?

Refer to:
- **REFACTORING_GUIDE.md** - Detailed instructions for each module
- **ARCHITECTURE.md** - System design and patterns
- **This file** - Quick reference and checklist

**Remember:** The goal isn't perfection—it's **maintainability**. A working 900-line module is infinitely better than a broken 5,000-line monolith.

---

**Let's transform this beast into beautiful, professional software! 🚀**
