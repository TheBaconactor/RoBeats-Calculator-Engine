# RoBeats MetaFinder

A high-performance genetic algorithm solver for optimizing gear and mini loadouts in rhythm games. Features JIT-compiled scoring, GPU-accelerated gem allocation, parallel song processing, and intelligent caching for maximum throughput.

**Version:** 2.0.0

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Dev/test tools: `pip install -r requirements-dev.txt`

### 2. Run the Optimizer

No additional setup required! The optimizer automatically discovers your Data folder structure on first run.

```bash
python main.py
```

The optimizer will:
- Load all songs from Data folders (Easy/Normal/Hard)
- Run genetic algorithm optimization for each song
- Store results in `evolution.db` SQLite database
- Report progress via Discord webhooks (if configured)
- Use GPU acceleration for gem allocation (if available)

---

## Features

### 🚀 Performance Optimizations
- **JIT Compilation:** Numba-accelerated scoring functions (10-100x speedup)
- **GPU Acceleration:** Taichi-based parallel gem allocation kernels (5-20x speedup)
- **Batch Execution:** True batched GPU kernel dispatch (Phase 4)
- **Parallel Processing:** Multi-process song evaluation with process pool
- **Triple-Layer Caching:** LRU caches for gem solver (5K), fever timelines (10K), force greats (2K)
- **Memory Watchdog:** Auto-restart when RAM usage exceeds threshold with resume capability

### 🧬 Algorithm Features
- **Co-Evolution GA:** Simultaneous gear (6 slots) and mini (3 slots) optimization
- **Memetic Search:** Local search hill-climbing after crossover for elite solutions
- **Multi-Start Restarts:** Escape local optima with fresh populations (3-30 restarts)
- **Pareto Pruning:** Remove dominated gear to reduce search space
- **Deep Mining:** Iterative refinement of best-known solutions from database
- **Adaptive Mutation:** Dynamic mutation rate (0.35-0.55) based on stagnation

### 💾 Data Management
- **SQLite Database:** Efficient storage with WAL mode, batch inserts, indexed queries
- **Loadout Deduplication:** MD5 hashing prevents redundant evaluations
- **Stats Signatures:** Deterministic cache keys for identical configurations
- **Database Merging:** Utilities for combining results from multiple runs
- **Discord Integration:** Real-time progress reporting with rate limiting
- **Dual-Table Architecture:** Clean separation of Base and Force Greats loadouts

---

## Configuration

### Basic Configuration

Edit `config.ini` to customize behavior:

```ini
[IterationEngine]
# GA Settings
GA_SearchDepth = 75           # Generations per GA run (default: 75)
GA_MultiStart = 3             # Multi-start restarts (default: 3, deep mining: 30)

  # GPU Settings  
  GPU_Mode = true               # Enable GPU acceleration
  MaxParallelSongs = 4          # Max concurrent song workers (default: 4)
  InFlightSongs = 0             # Experimental: single-process multi-song pipeline (set >1)

  # Force Greats
  ForceGreatsMode = false       # Enable ForceGreats evaluation (true/false)
  ForceGreatsFinder = false     # Auto ForceGreats optimization (true/false)
  # Manual ForceGreats (only used when ForceGreatsFinder=false)
  # Option A: Inline list (NonFever1, NonFever2, ...):
  # ForceGreatsManual = 3,0,1
  # Option B: Explicit section:
  # [ForceGreats]
  # NonFever1 = 3
  # NonFever2 = 0

  [Gear]
  # Default gear loadout (6 slots)
  Slot1 = Gear Name Here
...

[Minis]
# Default mini loadout (3 slots)
Slot1 = Mini Name Here
...
```

### Discord Integration (Optional)

Create `Discord.env` for real-time progress reporting:

```env
DISCORD_TOKEN=your_bot_token_here
LOGGINGCHANNEL=123456789
STATSCHANNEL=987654321
```

### Advanced Configuration

Environment variable overrides:

```bash
# Custom database location
export EVOLUTION_DB_PATH=/path/to/evolution.db

# Status JSON for deployments
export METAFINDER_STATUS_FILE=/path/to/metafinder_status.json

# GPU profiling
export GPU_EXECUTOR_PROFILE=1
export GPU_BATCH_LOG=1

# Deterministic testing
export GA_SEED=42
```

---

## Project Structure

Quick navigation: see `docs/NAVIGATION.md`.

```
RoBeats-Calculator-Engine/
├── main.py                           # Entry point → GearOptimizerApp
├── config.ini                        # User configuration (GA, memory, paths)
├── Discord.env                       # Discord credentials (gitignored)
├── requirements.txt                  # Runtime dependencies
├── requirements-dev.txt              # Dev/test dependencies
├── evolution.db                      # SQLite results database
├── pyproject.toml                    # Ruff + pytest configuration
│
├── gear_optimizer/                   # Main package (v2.0.0, 70+ files)
│   ├── __init__.py                   # Package metadata
│   │
│   ├── core/                         # Foundation layer (6 modules, 1,083 LOC)
│   │   ├── constants.py              # GA/scoring constants, PathConfig
│   │   ├── config.py                 # INI file parsing, path detection
│   │   ├── utils.py                  # Pure utility functions
│   │   ├── memory.py                 # Memory watchdog, OOM recovery
│   │   ├── jit_setup.py              # Numba JIT wrapper
│   │   └── math_utils.py             # Specialized math utilities
│   │
│   ├── data/                         # Data persistence layer (5 modules, 1,967 LOC)
│   │   ├── models.py                 # Tee, WarnOnce, GASettings dataclasses
│   │   ├── database.py               # SQLite CRUD, loadout hashing, batch inserts
│   │   ├── csv_parser.py             # Gear/mini/stats CSV parsing
│   │   ├── discord_reporter.py       # Discord webhook integration
│   │   └── db_merge.py               # Database merging utilities
│   │
│   ├── solver/                       # Algorithm layer (40+ modules, 7,200+ LOC)
│   │   ├── genetic.py                # Main GA loop with multi-start restarts
│   │   ├── fever_timeline.py         # Fever timeline calculation (Rules layer)
│   │   ├── gpu_executor.py           # GPU worker process management & IPC
│   │   ├── gpu_profiler.py           # GPU performance profiling
│   │   ├── taichi_gem_solver.py      # Facade to Taichi gem solver (lazy load)
│   │   │
│   │   ├── scoring/                  # Scoring package (7 modules, 1,010 → 178 avg LOC)
│   │   │   ├── batch_evaluation.py   # Batch genome evaluation with GPU/CPU
│   │   │   ├── cache_management.py   # Triple-layer LRU caching system
│   │   │   ├── core_scoring.py       # JIT-optimized core scoring (Numba)
│   │   │   ├── force_greats.py       # Force greats simulation & optimization
│   │   │   ├── orchestration.py      # Scoring dispatch (CPU+GPU paths)
│   │   │   ├── stat_extraction.py    # Base stats extraction utilities
│   │   │   └── utils.py               # Scoring helper utilities
│   │   │
│   │   └── taichi_gem/               # GPU kernels package (25+ modules)
│   │       ├── runtime.py            # Taichi initialization
│   │       ├── fields.py             # Taichi field definitions
│   │       │
│   │       ├── kernels/              # Kernels package (6 modules, 1,757 → 293 avg)
│   │       │   ├── helpers.py        # Field placeholders, lookup functions
│   │       │   ├── ga.py             # GA operations (selection, crossover, mutation)
│   │       │   ├── scoring.py        # Score calculation + greedy gem allocation
│   │       │   ├── solvers_batch.py  # Batch processing kernels
│   │       │   ├── ga_eval.py        # GA evaluation & reduction kernels
│   │       │   └── timeline.py       # Timeline grid precomputation (161×161)
│   │       │
│   │       ├── api/                  # API package (6 modules, 1,754 → 292 avg)
│   │       │   ├── initialization.py # GPU/field initialization, ref arrays
│   │       │   ├── single_batch.py   # Single-item & batch gem optimization
│   │       │   ├── mega_batch.py     # Mega-batch solver (highest performance)
│   │       │   ├── timeline.py       # GPU timeline precomputation
│   │       │   ├── parallel_solvers.py # Maximum parallelism solvers (~400k threads)
│   │       │   └── ga_operations.py  # GPU-native GA infrastructure
│   │       │
│   │       └── force_greats/         # Force greats GPU kernels (3 modules)
│   │           ├── api.py            # FG finder GPU API
│   │           ├── kernels.py        # FG simulation kernels
│   │           └── fields.py         # FG field definitions
│   │
│   ├── helpers/                      # Modular helper packages (20+ modules, 3,800+ LOC)
│   │   ├── song_preloader.py         # Pre-loading optimization for multi-song runs
│   │   │
│   │   ├── ga_helpers/               # GA helpers package (6 modules, 1,368 → 228 avg)
│   │   │   ├── pool_initialization.py # Gear/mini pools with dominance pruning
│   │   │   ├── genome_factory.py      # Genome creation & manipulation
│   │   │   ├── evaluation.py          # Evaluation with caching (in-memory + DB)
│   │   │   ├── local_search.py        # Hill-climbing local search
│   │   │   ├── population.py          # Population init, crossover, mutation
│   │   │   └── diversity.py           # Diversity metrics & adaptive mutation
│   │   │
│   │   └── song_helpers/             # Song helpers package (6 modules, 1,327 → 221 avg)
│   │       ├── database_context.py    # DB seeds & known loadouts loading
│   │       ├── song_config.py         # Configuration setup with auto-buff
│   │       ├── loadout_builder.py     # Build union of DB + GA loadouts
│   │       ├── force_greats.py        # Force greats processing (GPU/CPU)
│   │       ├── persistence.py         # DB payload & persistence entries
│   │       └── results_printer.py     # Results display & formatting
│   │
│   ├── pipeline/                     # Orchestration layer (1 module)
│   │   └── song_processor.py         # Main song processing workflow
│   │
│   └── app.py                        # GearOptimizerApp orchestrator (main loop)
│
├── Data/                             # Song files (CSV format)
│   ├── Easy/, Normal/, Hard/         # Song files by difficulty
│   ├── Gear/                         # Gear definitions
│   ├── Gear.csv                      # Gear metadata
│   ├── Minis.csv                     # Mini definitions
│   └── Stats.txt                     # Reference stats
│
├── bin/                              # Runtime data
│   ├── paths_cache.json              # Cached folder discovery
│   ├── memory_guard_resume.json      # OOM recovery state
│   ├── error.log                     # Error logging
│   └── build/                        # JIT compilation cache
│
├── tests/                            # Test suite (26 files, 3,862 LOC)
│   ├── conftest.py                   # Pytest configuration
│   ├── test_*.py                     # Unit & integration tests
│   ├── profile_*.py                  # Performance profiling scripts
│   └── regression_*.py               # Regression validation
│
├── scripts/                          # Utility scripts (14 files, 2,174 LOC)
│   ├── profile_*.py                  # Performance analysis
│   ├── evaluate_reference_loadout.py # Loadout evaluation
│   └── debug_*.py                    # Debugging utilities
│
├── tools/                            # Additional utilities
│   ├── benchmark_gpu.py              # GPU benchmarking
│   ├── check_db.py                   # Database inspection
│   └── verify_loadout.py             # Loadout verification
│
└── docs/                             # Documentation
    ├── ARCHITECTURE.md               # System architecture (15KB)
    ├── TAICHI_PORT_ROADMAP.md        # GPU optimization roadmap
    ├── CHANGES_SUMMARY.md            # Change log
    ├── HELPER_EXTRACTION.md          # Refactoring notes
    ├── REFACTORING_VALIDATION.md     # Test results
    ├── Implementation Records/       # Detailed change logs
    └── legacy/                       # Historical refactoring guides
```

**Total Codebase:** 100+ files, 18,000+ lines of code (refactored from 7,216 monolithic lines)

---

## Architecture

### Layered Design

```
┌─────────────────────────────────────────┐
│      Orchestration Layer               │
│  app.py (GearOptimizerApp)             │
│  song_processor.py                     │
└────────────────────┬────────────────────┘
                     │
┌────────────────────┴────────────────────┐
│      Algorithm Layer                   │
│  genetic.py (GA solver)                │
│  scoring.py (fitness evaluation)       │
│  gpu_executor.py (GPU coordination)    │
└────────────────────┬────────────────────┘
                     │
┌────────────────────┴────────────────────┐
│      Rules/Compute Layers              │
│  fever_timeline.py (CPU logic)         │
│  scoring_core.py (JIT scoring)         │
│  taichi_gem/*.py (GPU kernels)         │
└────────────────────┬────────────────────┘
                     │
┌────────────────────┴────────────────────┐
│      Helper Layer                      │
│  ga_helpers.py, song_helpers.py        │
│  song_preloader.py                     │
└────────────────────┬────────────────────┘
                     │
┌────────────────────┴────────────────────┐
│      Data Layer                        │
│  database.py, csv_parser.py            │
│  discord_reporter.py                   │
└────────────────────┬────────────────────┘
                     │
┌────────────────────┴────────────────────┐
│      Foundation Layer                  │
│  constants.py, config.py, utils.py     │
│  memory.py, models.py                  │
└─────────────────────────────────────────┘
```

**Import Hierarchy:** Zero circular dependencies - clean hierarchical structure (Level 0-6)

### Key Algorithms

#### Genetic Algorithm ([genetic.py](gear_optimizer/solver/genetic.py))
- **Population:** 250 individuals (configurable)
- **Generations:** 75 (configurable via `GA_SearchDepth`)
- **Multi-Start:** 3-30 restarts to escape local optima
- **Selection:** Tournament selection (k=3)
- **Crossover:** Single-point crossover
- **Mutation:** Adaptive rate (0.35 default, up to 0.55 on stagnation)
- **Elitism:** Preserve top 10% across generations
- **Memetic Search:** Local hill-climbing on elite offspring

#### Scoring Engine ([scoring.py](gear_optimizer/solver/scoring.py) + [scoring_core.py](gear_optimizer/solver/scoring_core.py))
- **Reference Lookup:** JIT-compiled O(1) stat-to-multiplier conversion
- **Fever Timeline:** CPU-side complex fever calculations ([fever_timeline.py](gear_optimizer/solver/fever_timeline.py))
- **Gem Optimization:** GPU-accelerated greedy gem allocation ([taichi_gem/](gear_optimizer/solver/taichi_gem/))
- **Combo Ramp:** Multiplier calculation with fever bonuses
- **Force Greats:** Penalty simulation for gear choice analysis
- **Caching:** Triple-layer LRU caching system

#### GPU Acceleration ([gpu_executor.py](gear_optimizer/solver/gpu_executor.py) + [taichi_gem/](gear_optimizer/solver/taichi_gem/))
- **Cross-Process GPU Ownership:** Single GPU executor in main process
- **IPC Queue Architecture:** Worker processes submit requests via multiprocessing queues
- **Batch Coalescing:** True batched kernel execution (Phase 4)
- **Multi-Song Grid Slots:** 8 parallel song slots for batch processing
- **Lazy Initialization:** Deferred Taichi/Vulkan setup for faster startup

---

## Testing

### Run Test Suite

```bash
# All tests
pytest tests/

# GPU integration tests
pytest tests/test_gpu_*.py

# Regression tests
pytest tests/regression_*.py

# Smoke tests
pytest tests/test_parity_smoke.py
```

### Test Coverage

**26 test files (3,862 LOC):**
- **GPU Integration:** 8 files (executor, batch ops, integration)
- **Taichi Parity:** 2 files (GPU/CPU validation)
- **Force Greats:** 4 files (correctness & performance)
- **GA Validation:** 3 files (return values, deep mining)
- **Regression:** 2 files (fixed bugs, GA stability)
- **API Stability:** 1 file (compatibility checks)

---

## Performance

### Benchmarks

| Optimization | Speedup | Implementation |
|--------------|---------|----------------|
| JIT Compilation | 10-100x | Numba @jit on scoring functions |
| GPU Acceleration | 5-20x | Taichi gem solver + force greats kernels |
| LRU Caching | ~100x | Triple-layer cache system (hit rate) |
| Process Pool | ~Nx | Multi-core song parallelization (N = CPU cores) |
| Batch Execution | 2-5x | True batched GPU kernel dispatch |
| Lazy Loading | Faster startup | Deferred Taichi/GPU initialization |

### Performance Tips

1. **Memory Management:** Set `memory_limit_pct` to 70-80% for stable operation
2. **Worker Count:** Use `MaxParallelSongs = CPU_count - 1` for best throughput
3. **GA Depth:** Increase `GA_SearchDepth` for better solutions (slower)
4. **GPU Profiling:** Enable `GPU_EXECUTOR_PROFILE=1` to measure utilization
5. **Caching:** Never clear `bin/build/` - contains JIT compilation cache

---

## Development

### Code Quality Metrics

- ✅ **Architecture:** Clean layered design, zero circular dependencies
- ✅ **Testing:** 26 test files, comprehensive coverage
- ✅ **Performance:** JIT, GPU, caching, memory management
- ✅ **Documentation:** Architecture docs, implementation records
- ✅ **Maintainability:** Modular design, extracted helpers (16 functions)

### Recent Improvements (Phase 3 & 4 - December 2024)

#### Phase 4 - GPU Batch Execution
1. ✅ Fixed force greats persistence bug
2. ✅ Implemented true batched kernel execution
3. ✅ Added GPU executor batch gathering infrastructure
4. ✅ Multi-song grid slot infrastructure (8 slots)
5. ✅ Configurable `MaxParallelSongs` to limit concurrent workers
6. ✅ Cleaned up codebase (removed stale `__pycache__`)

#### Phase 3 - Large File Refactoring (COMPLETE)
**Transformed 5 monolithic files (7,216 lines) into 31 focused modules across 5 packages:**

1. ✅ **scoring.py** split → 7 modules (1,010 → 178 avg LOC)
   - Batch evaluation, cache management, core scoring, force greats, orchestration

2. ✅ **kernels.py** split → 6 modules (1,757 → 293 avg LOC)
   - Helpers, GA operations, scoring, solvers, evaluation, timeline

3. ✅ **api.py** split → 6 modules (1,754 → 292 avg LOC)
   - Initialization, single batch, mega batch, timeline, parallel solvers, GA ops

4. ✅ **ga_helpers.py** split → 6 modules (1,368 → 228 avg LOC)
   - Pool init, genome factory, evaluation, local search, population, diversity

5. ✅ **song_helpers.py** split → 6 modules (1,327 → 221 avg LOC)
   - DB context, song config, loadout builder, force greats, persistence, results

**Benefits:**
- Improved maintainability (220-290 lines per module vs 1,000-1,700)
- Clear module boundaries and single responsibilities
- Easier navigation and understanding
- 100% backward compatibility maintained
- Zero circular dependencies introduced
- Foundation for future refactoring

---

## Troubleshooting

### Common Issues

**"Could not find Data folder"**
- Delete `bin/paths_cache.json` and re-run `python main.py` to regenerate it automatically

**"Memory limit exceeded"**
- Increase `memory_limit_pct` in config.ini or reduce `MaxParallelSongs`

**"No module named 'numba'" or "No module named 'taichi'"**
- Install dependencies: `pip install -r requirements.txt`

**JIT compilation warnings on first run**
- Normal behavior: first run compiles functions (slow), subsequent runs use cached JIT code

**GPU not detected**
- Ensure Taichi with Vulkan backend is installed: `pip install taichi`
- Check GPU availability: `python -c "import taichi as ti; ti.init(arch=ti.vulkan)"`
- Fallback to CPU mode: Set `UseGPU = 0` in config.ini

---

## Credits

**Original Implementation:** 5,196-line monolith (archived in docs/legacy)

**Refactored Architecture (v2.0.0):** Modular design with layered architecture
- 39 modules organized into 6 layers
- 16 extracted helper functions for improved modularity
- Zero circular dependencies
- Comprehensive testing and documentation

**GPU Optimization (Phase 4):** True batched kernel execution with multi-song grid slots

**Date:** December 2025

---

## License

This project is for personal use. All rights reserved.

---

## Security Note

⚠️ **Never commit tokens.** Keep `Discord.env` local and rotate your Discord bot token if it is ever exposed.

---

## Contributing

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for system design details.

Run `tools/quality_check.ps1` to verify code quality before submitting changes.
