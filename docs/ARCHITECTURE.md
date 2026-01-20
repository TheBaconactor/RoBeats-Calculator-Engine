# Gear Optimizer - Software Architecture

> [!NOTE]
> This is a high-level overview. For the current file-level map, start at `docs/NAVIGATION.md`.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          MAIN ENTRY POINT                            │
│                            (main.py)                                 │
│                                                                       │
│  - Initialize systems                                                │
│  - Load configuration                                                │
│  - Orchestrate song processing                                       │
│  - Handle graceful shutdown                                          │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      SONG PROCESSOR LAYER                            │
│                      (pipeline/song_processor.py)                     │
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ Read Song    │──│ Parse Config │──│ Execute      │              │
│  │ Files        │  │ & Settings   │  │ Optimization │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│                                                                       │
└───────────┬──────────────────────────┬──────────────────────────────┘
            │                          │
            ▼                          ▼
┌───────────────────────┐    ┌───────────────────────┐
│  GENETIC ALGORITHM    │    │  SCORING ENGINE       │
│  (solver/genetic.py)  │◄───│  (solver/scoring/)    │
│                       │    │                       │
│  - Population mgmt    │    │  - Score calculation  │
│  - Mutation/crossover │    │  - Gem optimization   │
│  - Multi-start logic  │    │  - Force greats       │
│  - Fitness evaluation │    │  - Caching (LRU)      │
└───────────┬───────────┘    └───────────┬───────────┘
            │                            │
            │                            │
            ▼                            ▼
┌───────────────────────────────────────────────────────────────────┐
│                         DATA PERSISTENCE LAYER                     │
│                                                                     │
│  ┌────────────────┐    ┌────────────────┐    ┌────────────────┐ │
│  │  DATABASE      │    │  CSV PARSER    │    │  CONFIG        │ │
│  │  (database.py) │    │  (csv_parser.py)│   │  (core/config.py)│ │
│  │                │    │                 │    │                 │ │
│  │ - SQLite ops   │    │ - Load gear    │    │ - Parse ini    │ │
│  │ - Loadout CRUD │    │ - Load minis   │    │ - Validate     │ │
│  │ - Compression  │    │ - Load stats   │    │ - Cache paths  │ │
│  └────────────────┘    └────────────────┘    └────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
            │                            │
            ▼                            ▼
┌───────────────────────┐    ┌───────────────────────┐
│  MEMORY MANAGEMENT    │    │  EXTERNAL SERVICES    │
│  (memory.py)          │    │  (discord_reporter.py)│
│                       │    │                       │
│  - Watchdog thread    │    │  - Webhook sender     │
│  - RSS monitoring     │    │  - Stats formatter    │
│  - Resume tracking    │    │  - Log reporter       │
└───────────────────────┘    └───────────────────────┘
            │
            ▼
┌───────────────────────────────────────────────────────────────────┐
│                     FOUNDATION LAYER                               │
│                                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐           │
│  │ CONSTANTS   │    │   MODELS    │    │   UTILS     │           │
│  │             │    │             │    │             │           │
│  │ - GA params │    │ - Tee       │    │ - safe_int  │           │
│  │ - Paths     │    │ - GASettings│    │ - safe_float│           │
│  │ - Limits    │    │ - WarnOnce  │    │ - pruning   │           │
│  └─────────────┘    └─────────────┘    └─────────────┘           │
└───────────────────────────────────────────────────────────────────┘
```

## Module Dependencies

### Import Hierarchy (Top → Bottom)

```
Level 1 (No Dependencies):
  └─ core/constants.py
  └─ data/models.py
  └─ core/utils.py

Level 2 (Depend on Level 1):
  └─ core/config.py      [constants, utils]
  └─ data/csv_parser.py  [constants, utils]
  └─ core/memory.py      [constants, models]

Level 3 (Depend on Levels 1-2):
  └─ data/database.py    [constants, utils, config]
  └─ solver/scoring/     [constants, utils, models]

Level 4 (Depend on Levels 1-3):
  └─ solver/genetic.py     [constants, models, utils, database, scoring]
  └─ data/discord_reporter.py [config]

Level 5 (Orchestration):
  └─ pipeline/song_processor.py [ALL]
  └─ main.py          [ALL]
```

## Data Flow

### Song Optimization Pipeline

```
┌──────────┐
│ Song CSV │
└────┬─────┘
     │
     ▼
┌────────────────┐
│ Read Song File │  (song_processor.scan_song_header)
└────┬───────────┘
     │
     ▼
┌──────────────────┐
│ Load Gear/Minis  │  (csv_parser.parse_gear_rows)
└────┬─────────────┘
     │
     ▼
┌──────────────────────┐
│ Load DB Seeds        │  (database.get_best_loadouts)
│ (Top 50 from prev)   │
└────┬─────────────────┘
     │
     ▼
┌──────────────────────────┐
│ Genetic Algorithm Solver │  (genetic.solve_coevolution_genetic)
│                          │
│  ┌─────────────────┐    │
│  │ Initialize Pop  │────┼──┐
│  └────────┬────────┘    │  │
│           │             │  │
│           ▼             │  │  Multi-start
│  ┌─────────────────┐   │  │  Loop (3x)
│  │ Evaluate        │◄──┼──┘
│  │ (solver/scoring/)│   │
│  └────────┬────────┘   │
│           │            │
│           ▼            │
│  ┌─────────────────┐  │
│  │ Select/Mutate   │  │
│  └────────┬────────┘  │
│           │           │
│           ▼           │
│  ┌─────────────────┐ │
│  │ Memetic Search  │ │
│  └────────┬────────┘ │
│           │          │
│           ▼          │
│  ┌─────────────────┐│
│  │ Return Best     ││
│  └────────┬────────┘│
└───────────┼─────────┘
            │
            ▼
┌────────────────────┐
│ Save to Database   │  (database.save_loadout_to_db)
│ (Top 50 preserved) │
└────────────────────┘
```

## Key Design Patterns

### 1. **Separation of Concerns**
- Each module has single, well-defined responsibility
- Data access isolated in `gear_optimizer/data/database.py` and `gear_optimizer/data/csv_parser.py`
- Business logic in `gear_optimizer/solver/genetic.py` and `gear_optimizer/solver/scoring/`
- Infrastructure in `gear_optimizer/core/memory.py` and `gear_optimizer/core/config.py`

### 2. **Dependency Injection**
```python
# Bad (Original)
def solve_genetic(...):
    cfg = configparser.ConfigParser()  # Hard dependency
    cfg.read("config.ini")

# Good (Refactored)
def solve_genetic(cfg: ConfigParser, ...):
    # cfg injected, testable
```

### 3. **Cache Abstraction**
```python
# solver/scoring/*
from cachetools import LRUCache

# Global caches with bounded memory
GEM_SOLVER_CACHE = LRUCache(maxsize=5000)
FEVER_TIMELINE_CACHE = LRUCache(maxsize=10000)
```

### 4. **Strategy Pattern** (Genetic Algorithm)
```python
# Different mutation strategies
def mutate_genome_standard(genome, rate): ...
def mutate_genome_adaptive(genome, rate): ...

# Configurable via GASettings
```

### 5. **Template Method** (Song Processing)
```python
def process_song_task(args):
    config = _parse_args(args)
    _setup_environment(config)

    if config.optimize:
        result = _run_optimization(config)  # Template
    else:
        result = _calculate_only(config)    # Template

    _persist_results(result, config)
    return _build_payload(result)
```

## Performance Optimizations

### 1. **JIT Compilation** (solver/scoring_core.py)
```python
try:
    from numba import jit
    HAS_NUMBA = True
except ImportError:
    def jit(nopython=True, cache=True):
        def decorator(func):
            return func
        return decorator
    HAS_NUMBA = False

@jit(nopython=True)
def lookup_reference_jit(value, ref_array, total_rows):
    # 10x faster than Python loop
```

### 2. **LRU Caching** (solver/scoring/)
```python
# Cache key based on inputs that matter
signature = stats_signature(stats, calc_song, selected_color)
if signature in GEM_SOLVER_CACHE:
    return GEM_SOLVER_CACHE[signature]  # ~100x faster
```

### 3. **Process Pool** (main.py)
```python
# Parallelize song processing across CPU cores
with ProcessPoolExecutor(max_workers=cpu_count()) as executor:
    results = executor.map(safe_process_song_task, song_args)
```

### 4. **Database Optimization** (database.py)
- WAL mode for concurrent reads
- Batch inserts with relaxed synchronous mode
- Indexed queries on (song_name, score DESC)
- Compact storage (names only, not full dicts)

## Error Handling Strategy

### Layered Approach

```
Layer 1: Individual Functions
  └─ try/except with logging
  └─ Return None or default on error

Layer 2: Song Processing
  └─ safe_process_song_task() wrapper
  └─ Never raises across process boundary
  └─ Returns error dict with traceback

Layer 3: Main Loop
  └─ Continue processing other songs on failure
  └─ Report errors to Discord
  └─ Log to file

Layer 4: Memory Guard
  └─ Resume queue for restart after OOM
  └─ Graceful shutdown on memory limit
```

### Example
```python
# database.py
def save_loadout_to_db(song_name, ...):
    try:
        conn = get_db_connection()
        conn.execute(...)
        conn.commit()
    except Exception as e:
        print(f"[DB] Error saving loadout: {e}")
        # Graceful degradation - continue without DB
    finally:
        conn.close()
```

## Testing Strategy

### Unit Tests (Per Module)
```python
# tests/test_utils.py
def test_safe_int():
    assert safe_int("123") == 123
    assert safe_int("invalid", 999) == 999

# tests/test_database.py
def test_loadout_hash():
    gear1 = [{"Name": "A"}, {"Name": "B"}]
    gear2 = [{"Name": "B"}, {"Name": "A"}]  # Different order
    assert get_loadout_hash(gear1, []) == get_loadout_hash(gear2, [])
```

### Integration Tests
```python
# tests/test_genetic.py
def test_full_optimization():
    # Load test song
    # Run GA
    # Verify score is reasonable
    # Verify loadout is valid
```

### Regression Tests
```bash
# Compare before/after refactoring
python baseline.py > baseline_scores.txt
python main.py > refactored_scores.txt
diff baseline_scores.txt refactored_scores.txt
```

## Deployment

### Production Checklist
- [ ] All modules have docstrings
- [ ] Comment ratio > 15%
- [ ] No functions > 150 lines
- [ ] No nesting > 5 levels
- [ ] All tests pass
- [ ] Memory usage verified
- [ ] Database migrations tested

### Configuration
```ini
[IterationEngine]
MetaFinder = True
ForceGreatsMode = False
GA_MultiStart = 3
MemorySoftLimitPercent = 50.0

[Paths]
StatusFilePath = /path/to/status.json
```

## Future Improvements

1. **Type Hints**: Add throughout for better IDE support
2. **Async I/O**: For Discord webhook and file I/O
3. **Plugin System**: Extensible mutation/crossover strategies
4. **Web UI**: Real-time optimization monitoring
5. **Distributed**: Run GA across multiple machines

---

**This architecture provides:**
✅ Clear module boundaries
✅ Testable components
✅ Maintainable codebase
✅ Professional structure
✅ Scalability for future features
