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

To stop safely:
- Press `Ctrl+C` once to request a graceful stop (finishes current work, flushes DB, then exits)
- Press `Ctrl+C` again to force-exit
- Or create a stop file at `bin/STOP` (override path via `METAFINDER_STOP_FILE`)

The optimizer will:
- Load all songs from Data folders (Easy/Normal/Hard)
- Run genetic algorithm optimization for each song
- Store results in `evolution.db` SQLite database (compact baseline-only; tiers recomputed on demand)
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
- **Dual-Table Architecture:** Clean separation of Base and Force Greats loadouts

---

## Configuration

### Basic Configuration

Edit `config.ini` to customize behavior:

```ini
[CalculateSong]
Song_Name = Aether
Difficulty = All

[IterationEngine]
; Main optimizer toggles
MetaFinder = true

; GPU acceleration (Taichi/Vulkan)
GPU_Mode = true
GPU_Native_GA = true
InFlightSongs = 0

; Force Greats
ForceGreatsMode = true
ForceGreatsFinder = true
FG_CandidateLimit = 200
FG_SearchRadius = 5

; GA settings
GA_SearchDepth = 500
GA_MultiStart = 35

; Resource limits
EvalCPUCores = 0
MemorySoftLimitGB = 7
MemorySoftLimitPercent = 0

[Gear]
; Leave blank to let GA choose a starting point
Hat =
Neck =
Face =
Shirt =
Back =
Pant =

[Minis]
; Leave blank to let GA choose a starting point
1 =
2 =
3 =
```

### Advanced Configuration

Environment variable overrides:

```bash
# Custom config.ini location
export METAFINDER_CONFIG_PATH=/path/to/config.ini

# Custom database location
export EVOLUTION_DB_PATH=/path/to/evolution.db

# Deterministic testing
export GA_SEED=42

# Profiling / timing (opt-in)
export PERF_TIMING=1
export GPU_PROFILER=1
export GPU_EXECUTOR_PROFILE=1
```

---

## Project Structure

Quick navigation: see `docs/README.md` for the docs index, `docs/NAVIGATION.md` for the code map, and `docs/ENGINEERING_PRINCIPLES.md` for repo-wide engineering doctrine.

High-level layout (current):

```text
RoBeats-Calculator-Engine/
├── main.py                      # Optimizer entrypoint
├── general_meta_main.py         # Cross-song/meta analysis entrypoint
├── config.ini                   # User configuration
├── gear_optimizer/              # Main package
├── tests/                       # Pytest suite
├── tools/                       # Maintained utilities/bench/verifiers
├── scripts/                     # Ad-hoc profiling/debug scripts
├── docs/                        # Design + math + schema docs
├── Data/                        # Inputs (songs + gear metadata)
├── bin/                         # Caches/logs/profiles (generated)
└── artifacts/                   # Run outputs (generated)
```

<details>
<summary>Historical: detailed tree (may be out-of-date)</summary>

```
RoBeats-Calculator-Engine/
├── main.py                           # Entry point → GearOptimizerApp
├── config.ini                        # User configuration (GA, memory, paths)
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
│   │
│   ├── solver/                       # Algorithm layer (40+ modules, 7,200+ LOC)
│   │   ├── genetic.py                # Main GA loop with multi-start restarts
│   │   ├── fever_timeline.py         # Fever timeline calculation (Rules layer)
│   │   ├── gpu_executor.py           # GPU worker process management & IPC
│   │   ├── gpu_profiler.py           # GPU performance profiling
│   │   ├── taichi_gem/               # Taichi gem solver runtime, APIs, and kernels
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
│   ├── helpers/                      # Modular helper packages (song + GA helper packages)
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
    └── Implementation Records/       # Detailed change logs
```

</details>

**Note:** `bin/`, `artifacts/`, and `evolution.db` are typically generated during runs.

---

## Architecture

### Layered Design

```
┌─────────────────────────────────────────┐
│      Orchestration Layer               │
│  main.py                               │
│  gear_optimizer/app.py (GearOptimizerApp) │
│  gear_optimizer/pipeline/song_processor.py │
└────────────────────┬────────────────────┘
                     │
┌────────────────────┴────────────────────┐
│      Algorithm Layer                   │
│  gear_optimizer/solver/genetic.py (CPU GA) │
│  gear_optimizer/solver/inflight_* (in-flight) │
│  gear_optimizer/solver/gpu_executor.py (GPU IPC) │
└────────────────────┬────────────────────┘
                     │
┌────────────────────┴────────────────────┐
│      Rules/Compute Layers              │
│  gear_optimizer/solver/scoring/ (CPU/GPU dispatch) │
│  gear_optimizer/solver/scoring_core.py (JIT scoring) │
│  gear_optimizer/solver/fever_timeline.py (CPU logic) │
│  gear_optimizer/solver/taichi_gem/ (GPU kernels) │
└────────────────────┬────────────────────┘
                     │
┌────────────────────┴────────────────────┐
│      Helper Layer                      │
│  gear_optimizer/helpers/ga_helpers/ + song_helpers/ │
└────────────────────┬────────────────────┘
                     │
┌────────────────────┴────────────────────┐
│      Data Layer                        │
│  gear_optimizer/data/database.py + migrations/ │
│  gear_optimizer/data/csv_parser.py                      │
└────────────────────┬────────────────────┘
                     │
┌────────────────────┴────────────────────┐
│      Foundation Layer                  │
│  gear_optimizer/core/                  │
└─────────────────────────────────────────┘
```

**Import Hierarchy:** Zero circular dependencies - clean hierarchical structure (Level 0-6)

### Key Algorithms

#### Genetic Algorithm ([genetic.py](gear_optimizer/solver/genetic.py))
- **Population:** 470 individuals (configurable)
- **Generations:** 75 (configurable via `GA_SearchDepth`)
- **Multi-Start:** 3-30 restarts to escape local optima
- **Selection:** Tournament selection (k=3)
- **Crossover:** Single-point crossover
- **Mutation:** Adaptive rate (0.35 default, up to 0.55 on stagnation)
- **Elitism:** Preserve top 10% across generations
- **Memetic Search:** Local hill-climbing on elite offspring

#### Scoring Engine ([scoring/](gear_optimizer/solver/scoring/) + [scoring_core.py](gear_optimizer/solver/scoring_core.py))
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
python -m pytest tests/

# CPU-only
python -m pytest -m "not gpu" tests/

# GPU (Taichi/Vulkan)
python -m pytest -m gpu tests/
```

### Test Coverage

See `tests/` for CPU/GPU parity checks, DB correctness, and regression coverage.

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

1. **Memory Management:** Set `MemorySoftLimitGB` or `MemorySoftLimitPercent` (under `[IterationEngine]`) for stable operation
2. **Worker Count:** CPU-only runs auto-parallelize songs (no config required)
3. **GA Depth:** Increase `GA_SearchDepth` for better solutions (slower)
4. **GPU Profiling:** Enable `GPU_EXECUTOR_PROFILE=1` to measure utilization
5. **Caching:** Avoid clearing `bin/numba_cache/` (JIT cache) and `bin/paths_cache.json` (data discovery cache) unless troubleshooting
6. **Dual-GPU (experimental):** Set `GPU_EXECUTOR_SECONDARY_WORKERS=<n>` and `GPU_EXECUTOR_SECONDARY_VULKAN_VISIBLE_DEVICE=<idx>` to split workers across two Vulkan devices (multi-process Taichi)

---

## Development

### Unified Script Runner

Use the unified script runner to reduce clutter when working across both `tools/` and `scripts/`:

```bash
# List maintained scripts
python -m tools list

# Show inventory + clutter hotspots (private/scratch counts)
python -m tools audit

# Run a script by id (tool ids are shown by `list`)
python -m tools run tools:db/check_db
python -m tools run scripts:query/query_top_loadouts -- --help
```

By default, private/scratch scripts (for example `_tmp_*`, underscore-prefixed files, and nested `tests/` scripts) are hidden from `list`. Include them explicitly with `--all`.

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
5. ✅ In-flight single-process multi-song pipeline (`InFlightSongs`)
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
- Direct module boundaries only
- Zero circular dependencies introduced
- Foundation for future refactoring

---

## Troubleshooting

### Common Issues

**"Could not find Data folder"**
- Delete `bin/paths_cache.json` and re-run `python main.py` to regenerate it automatically

**"Memory limit exceeded"**
- Increase `MemorySoftLimitGB` / `MemorySoftLimitPercent` in `config.ini` or reduce GA depth / multi-start

**"No module named 'numba'" or "No module named 'taichi'"**
- Install dependencies: `pip install -r requirements.txt`

**JIT compilation warnings on first run**
- Normal behavior: first run compiles functions (slow), subsequent runs use cached JIT code

**GPU not detected**
- Ensure Taichi with Vulkan backend is installed: `pip install taichi`
- Check GPU availability: `python -c "import taichi as ti; ti.init(arch=ti.vulkan)"`

---

## Credits

**Original Implementation:** 5,196-line monolith (archived off-repo)

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

⚠️ **Never commit tokens.**

---

## Contributing

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for system design details and [docs/ENGINEERING_PRINCIPLES.md](docs/ENGINEERING_PRINCIPLES.md) for the repo's root-cause, ownership, and refactoring standards.

Repo-wide agent routing starts in [AGENTS.md](AGENTS.md). Subtree-specific guidance lives in nested `AGENTS.md` files close to the code they govern.

Use `python -m tools list` to discover centralized tooling entry points.

Run `powershell -ExecutionPolicy Bypass -File tools/dev/quality_check.ps1` to verify code quality before submitting changes.
