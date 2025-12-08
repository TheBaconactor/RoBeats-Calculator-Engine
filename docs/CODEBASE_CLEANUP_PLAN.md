# Codebase Cleanup & Reorganization Plan

## Current Situation Analysis

Your root directory has **23 files** including:
- 1 active main entry point (`main.py`)
- 2 legacy monoliths (`Manual_Calculator - Main.py`, `Manual_Calculator - Original.py`)
- 1 bootstrapper (`Bootstrapper.py`)
- 8 documentation/guide markdown files
- Test files, config files, and data

**This is cluttered and confusing!**

---

## Proposed Clean Structure

```
Gear Optimizer/
├── main.py                          # NEW: Main entry point
├── config.ini                       # Keep: User configuration
├── Discord.env                      # Keep: Discord credentials
├── Bootstrapper.py                  # Keep: Still needed for path detection
├── README.md                        # NEW: Single comprehensive guide
│
├── gear_optimizer/                  # Keep: Core refactored package
│   ├── __init__.py
│   ├── constants.py
│   ├── models.py
│   ├── utils.py
│   ├── config.py
│   ├── database.py
│   ├── csv_parser.py
│   ├── jit_setup.py
│   ├── scoring.py
│   ├── genetic.py
│   ├── memory.py
│   ├── discord_reporter.py
│   └── song_processor.py
│
├── bin/                             # Keep: Runtime data
│   ├── paths_cache.json
│   ├── error.log
│   └── build/
│
├── Data/                            # Keep: Song files
│   ├── Easy/
│   ├── Normal/
│   ├── Hard/
│   ├── Gear.csv
│   ├── Minis.csv
│   └── Stats.txt
│
├── tests/                           # NEW: Test directory
│   └── test_refactoring.py
│
├── docs/                            # NEW: All documentation
│   ├── ARCHITECTURE.md
│   ├── REFACTORING_VALIDATION.md
│   └── legacy/                      # OLD: Archive old guides
│       ├── EXTRACTION_PLAN.md
│       ├── FINAL_COMPLETION_GUIDE.md
│       ├── PHASE_3_STATUS.md
│       ├── QUICK_COMPLETION_GUIDE.md
│       ├── README_REFACTORING.md
│       ├── REFACTORING_COMPLETE_50_PERCENT.md
│       ├── REFACTORING_GUIDE.md
│       └── REFACTORING_STATUS.md
│
└── legacy/                          # NEW: Archive old code
    ├── Manual_Calculator - Main.py
    └── Manual_Calculator - Original.py
```

---

## Do You Still Need Bootstrapper.py?

**YES - You still need it!**

### What Bootstrapper.py Does:
1. **Auto-discovers Data folder locations** (Easy, Normal, Hard, Gear.csv, Stats.txt)
2. **Caches paths** to `bin/paths_cache.json` for fast loading
3. **Pre-builds song metadata tables** for performance
4. **Scans parent directories** to find sibling folders

### Why It's Important:
- Your `main.py` and refactored modules rely on `load_paths_cache()` which reads `bin/paths_cache.json`
- The bootstrapper **must run first** to populate this cache
- Without it, the optimizer won't know where your song files are

### Usage Flow:
```bash
# 1. First time or when paths change:
python Bootstrapper.py

# 2. Then run the optimizer:
python main.py
```

---

## Cleanup Actions

### 1. Create New Directories
```bash
mkdir tests
mkdir docs
mkdir docs/legacy
mkdir legacy
```

### 2. Move Test Files
```bash
mv test_refactoring.py tests/
```

### 3. Move Documentation
```bash
# Keep these in docs/
mv ARCHITECTURE.md docs/
mv REFACTORING_VALIDATION.md docs/

# Archive old refactoring guides
mv EXTRACTION_PLAN.md docs/legacy/
mv FINAL_COMPLETION_GUIDE.md docs/legacy/
mv PHASE_3_STATUS.md docs/legacy/
mv QUICK_COMPLETION_GUIDE.md docs/legacy/
mv README_REFACTORING.md docs/legacy/
mv REFACTORING_COMPLETE_50_PERCENT.md docs/legacy/
mv REFACTORING_GUIDE.md docs/legacy/
mv REFACTORING_STATUS.md docs/legacy/
```

### 4. Archive Legacy Code
```bash
mv "Manual_Calculator - Main.py" legacy/
mv "Manual_Calculator - Original.py" legacy/
```

### 5. Create Main README
Create a single `README.md` that explains:
- What this project does
- How to set up and run
- Project structure
- Links to detailed docs

---

## Files to Keep in Root

**Essential Files Only:**
1. `main.py` - Entry point
2. `config.ini` - User configuration
3. `Discord.env` - Credentials
4. `Bootstrapper.py` - Path discovery
5. `README.md` - Project overview
6. `evolution.db` - Database file

**Total: 6 files** (down from 23!)

---

## Benefits

✅ **Clean root directory** - Only 6 essential files
✅ **Organized documentation** - All guides in `docs/`
✅ **Preserved history** - Legacy code archived, not deleted
✅ **Clear testing** - Tests in dedicated `tests/` folder
✅ **Professional structure** - Industry-standard Python project layout

---

## Next Steps

Would you like me to:

1. **Execute the cleanup automatically** - I'll move all files to the proposed structure
2. **Create the new README.md** - Comprehensive project documentation
3. **Verify Bootstrapper.py** - Ensure it works with the new structure
4. **Update import paths** - If any files reference old locations

Just say "yes, clean it up" and I'll reorganize everything!
