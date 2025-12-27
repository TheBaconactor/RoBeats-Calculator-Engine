# RoBeats MetaFinder - Architecture Improvements Proposal

## Current State Analysis

**RoBeats MetaFinder v2.0.0** is a high-performance genetic algorithm (GA) solver for optimizing gear and mini loadouts in rhythm games. It features:
- **92 Python modules** organized in a clean 6-layer architecture
- **33,218 total lines of code** refactored from a 7,216-line monolith
- **JIT-compiled scoring** (Numba) and **GPU-accelerated gem solving** (Taichi)
- **Zero circular dependencies** - pure hierarchical structure
- **Comprehensive test suite** - 44 test files, 45 total test modules
- **Advanced features:** Multi-start GA, memetic local search, force greats optimization, memory watchdog, Discord integration

---

## Current Layered Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Level 6: ORCHESTRATION LAYER                                    │
│ ├─ main.py → GearOptimizerApp (1,399 LOC)                      │
│ └─ pipeline/song_processor.py (1,056 LOC)                      │
└────────────────────┬────────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────────────┐
│ Level 5: ALGORITHM LAYER                                        │
│ ├─ solver/genetic.py (1,916 LOC) - Main GA loop               │
│ ├─ solver/gpu_executor.py (1,056 LOC) - Cross-process GPU IPC │
│ ├─ solver/inflight_orchestrator.py (811 LOC) - Multi-song     │
│ └─ solver/inflight_genetic.py (735 LOC) - GPU-native GA       │
└────────────────────┬────────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────────────┐
│ Level 4: SCORING & RULES LAYER                                 │
│ ├─ solver/scoring/ (7 modules, ~100 LOC avg)                  │
│ │  ├─ gpu_solver.py - Lazy GPU init + global LRU caches       │
│ │  ├─ genome_evaluation.py (909 LOC) - Batch evaluation       │
│ │  ├─ force_greats.py (1,105 LOC) - FG simulation & optimization
│ │  ├─ fever_solver.py - Fever timeline optimization           │
│ │  └─ stats_scoring.py - Stats evaluation helpers             │
│ ├─ solver/fever_timeline.py (706 LOC) - CPU fever logic       │
│ └─ solver/taichi_gem/ (25+ modules) - GPU kernels             │
└────────────────────┬────────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────────────┐
│ Level 3: HELPER LAYER                                           │
│ ├─ helpers/ga_helpers/ (6 modules, ~228 LOC avg)              │
│ │  ├─ pool_initialization.py - Dominance pruning              │
│ │  ├─ genome_factory.py - Genome creation/manipulation        │
│ │  ├─ evaluation.py - Parallel evaluation with caching        │
│ │  ├─ local_search.py - Hill-climbing refinement              │
│ │  ├─ population.py - Crossover/mutation operations           │
│ │  └─ diversity.py - Diversity metrics & adaptive mutation    │
│ ├─ helpers/song_helpers/ (6 modules, ~221 LOC avg)            │
│ │  ├─ database_context.py - DB seeds loading                  │
│ │  ├─ song_config.py - Configuration setup                    │
│ │  ├─ loadout_builder.py - Loadout entry building             │
│ │  ├─ force_greats.py (1,027 LOC) - FG processing             │
│ │  ├─ persistence.py - DB payload building                    │
│ │  └─ results_printer.py - Results formatting                 │
│ ├─ helpers/song_preloader.py (13K) - Multi-song optimization  │
│ └─ helpers/fg_utils.py (21K) - Force greats utilities         │
└────────────────────┬────────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────────────┐
│ Level 2: DATA PERSISTENCE LAYER                                 │
│ ├─ data/database.py (727 LOC) - SQLite CRUD, batch ops       │
│ ├─ data/csv_parser.py - Gear/mini/stats CSV parsing           │
│ ├─ data/models.py - Dataclasses (Tee, WarnOnce, GASettings)  │
│ ├─ data/db_merge.py (705 LOC) - Database merging utilities    │
│ └─ data/discord_reporter.py - Discord integration            │
└────────────────────┬────────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────────────┐
│ Level 1: FOUNDATION LAYER (Core)                               │
│ ├─ core/constants.py - GA/scoring/cache constants             │
│ ├─ core/config.py - INI file parsing, path detection          │
│ ├─ core/utils.py - Pure utility functions                     │
│ ├─ core/memory.py (100 LOC+) - Memory watchdog, OOM recovery  │
│ ├─ core/env_config.py - Environment variable access          │
│ ├─ core/jit_setup.py - Numba JIT wrapper                      │
│ └─ core/math_utils.py - Specialized math utilities            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Proposed Improvements

### 🏆 High-Impact Improvements

#### 1. Introduce a Dependency Injection Container

**Current State:** Factory functions and manual parameter threading across layers.

**Proposal:** Adopt a lightweight DI container (like `dependency-injector` or a custom solution) to manage cross-cutting concerns:

```python
# core/container.py
class AppContainer:
    config: ConfigService
    database: DatabaseService
    gpu_executor: GpuExecutorService
    cache_manager: CacheManager
    memory_watchdog: MemoryWatchdog

    def __init__(self, config_path: str):
        self.config = ConfigService(config_path)
        self.cache_manager = CacheManager(self.config)
        # Wire dependencies declaratively
```

**Benefits:**
- Eliminates `cfg_dict` serialization/deserialization for IPC
- Makes testing easier (swap real implementations for mocks)
- Centralizes lifecycle management

---

#### 2. Event-Driven Architecture for Cross-Cutting Concerns

**Current State:** Direct calls between layers (e.g., Discord reporting, memory watchdog callbacks).

**Proposal:** Add a lightweight event bus for decoupling:

```python
# core/events.py
class EventBus:
    def emit(self, event_type: str, payload: Any): ...
    def subscribe(self, event_type: str, handler: Callable): ...

# Events:
# - "song.started", "song.completed", "song.failed"
# - "memory.threshold_exceeded", "memory.recovered"
# - "ga.generation_completed", "ga.restart_triggered"
```

**Benefits:**
- Discord reporter subscribes to events instead of being called directly
- Memory watchdog can emit events instead of setting globals
- Easier to add new integrations (logging, metrics, webhooks)

---

#### 3. Abstract GPU Backend Interface

**Current State:** Taichi-specific code scattered across `solver/taichi_gem/` and `gpu_executor.py`.

**Proposal:** Create a GPU backend abstraction:

```python
# solver/gpu/backend.py
class GpuBackend(Protocol):
    def initialize(self, device: str) -> None: ...
    def evaluate_genomes(self, genomes: np.ndarray, ...) -> np.ndarray: ...
    def precompute_timeline(self, song_data: SongData) -> TimelineGrid: ...
    def shutdown(self) -> None: ...

# solver/gpu/taichi_backend.py
class TaichiBackend(GpuBackend):
    """Current implementation using Taichi."""

# solver/gpu/cpu_fallback.py
class CpuFallbackBackend(GpuBackend):
    """Pure NumPy fallback when no GPU."""
```

**Benefits:**
- Easier to test (mock the GPU backend)
- Potential for alternative backends (CUDA direct, Metal compute, etc.)
- Cleaner separation between algorithm logic and GPU specifics

---

### 🔧 Medium-Impact Improvements

#### 4. Configuration as Typed Dataclasses

**Current State:** ConfigParser with string access (`cfg.get("Section", "Key")`).

**Proposal:** Parse config into validated dataclasses at startup:

```python
# core/config.py
@dataclass(frozen=True)
class GAConfig:
    search_depth: int = 75
    multi_start: int = 5
    population_size: int = 250
    mutation_rate: float = 0.35
    db_seed_probability: float = 0.5

    @classmethod
    def from_config_parser(cls, cfg: ConfigParser) -> "GAConfig":
        return cls(
            search_depth=safe_int(cfg.get("IterationEngine", "GA_SearchDepth", fallback=75)),
            # ... validated parsing
        )

@dataclass(frozen=True)
class AppConfig:
    ga: GAConfig
    memory: MemoryConfig
    force_greats: ForceGreatsConfig
    paths: PathsConfig
```

**Benefits:**
- IDE autocompletion and type checking
- Validation at startup (fail fast on bad config)
- Immutable configuration prevents accidental mutation

---

#### 5. Repository Pattern for Database Layer

**Current State:** Functions in `data/database.py` with direct SQL queries.

**Proposal:** Introduce repository classes:

```python
# data/repositories/loadout_repository.py
class LoadoutRepository:
    def __init__(self, db_connection: Connection):
        self._conn = db_connection

    def get_top_by_score(self, song_name: str, limit: int = 51) -> List[Loadout]: ...
    def get_top_by_fg_score(self, song_name: str, limit: int = 51) -> List[Loadout]: ...
    def save_batch(self, song_name: str, loadouts: List[Loadout]) -> None: ...
    def count_by_song(self, song_name: str) -> int: ...

# data/repositories/song_repository.py
class SongRepository:
    def get_all(self) -> List[Song]: ...
    def update_best_scores(self, song_name: str, best: float, best_fg: float): ...
```

**Benefits:**
- Easier to mock for testing
- Encapsulates SQL complexity
- Clear API for data access

---

#### 6. Command/Query Separation for GA Operations

**Current State:** `solve_coevolution_genetic()` is a large function (1,916 LOC) doing everything.

**Proposal:** Separate into commands and queries:

```python
# solver/commands/
# - InitializePopulationCommand
# - PerformGenerationCommand
# - LocalSearchCommand
# - DeepMiningCommand

# solver/queries/
# - GetBestGenomesQuery
# - ComputeDiversityQuery
# - CheckConvergenceQuery

# solver/genetic.py (orchestrator)
class GeneticAlgorithmOrchestrator:
    def __init__(self, commands: GACommands, queries: GAQueries):
        self._cmds = commands
        self._qry = queries

    def solve(self, song_data: SongData, settings: GAConfig) -> SolveResult:
        population = self._cmds.initialize_population(...)
        for gen in range(settings.search_depth):
            population = self._cmds.perform_generation(population, ...)
            if self._qry.check_convergence(population):
                break
        return SolveResult(best=self._qry.get_best_genomes(population))
```

**Benefits:**
- Smaller, testable units
- Easier to modify individual steps
- Clear separation of state-changing vs. read-only operations

---

### 🎨 Architectural Patterns to Consider

#### 7. Pipeline/Stage Pattern for Song Processing

**Current State:** `song_processor.py` has a monolithic `safe_process_song_task()`.

**Proposal:** Define processing as a pipeline of stages:

```python
# pipeline/stages.py
class SongProcessingPipeline:
    stages: List[ProcessingStage] = [
        LoadSongDataStage(),
        LoadDatabaseContextStage(),
        InitializePoolsStage(),
        GeneticOptimizationStage(),
        ForceGreatsOptimizationStage(),
        PersistResultsStage(),
    ]

    def process(self, song: SongInput) -> SongResult:
        context = PipelineContext(song)
        for stage in self.stages:
            if stage.should_run(context):
                context = stage.execute(context)
        return context.result
```

**Benefits:**
- Stages can be skipped conditionally (e.g., skip FG if disabled)
- Easier to add new processing steps
- Each stage is independently testable

---

#### 8. Introduce Domain Models

**Current State:** Uses dicts, tuples, and np.arrays throughout.

**Proposal:** Create rich domain models:

```python
# domain/models.py
@dataclass
class Genome:
    gear: List[GearItem]  # 6 slots
    minis: List[MiniItem]  # 3 slots

    @property
    def stats(self) -> StatsVector: ...

    def mutate(self, rate: float, pool: ItemPool) -> "Genome": ...
    def crossover(self, other: "Genome") -> Tuple["Genome", "Genome"]: ...

@dataclass
class Loadout:
    genome: Genome
    score: float
    fg_score: Optional[float]
    details: LoadoutDetails

    @property
    def hash(self) -> str:
        return md5(self.genome.stats.to_bytes())

@dataclass
class SongData:
    name: str
    difficulty: str
    timestamps: np.ndarray
    note_types: np.ndarray
    metadata: SongMetadata
```

**Benefits:**
- Self-documenting code
- Methods belong with data
- Type hints work properly

---

## Suggested Directory Structure Refactor

```
gear_optimizer/
├── core/                      # Foundation layer (keep as-is)
│   ├── config.py             # → Typed dataclass config
│   ├── constants.py
│   ├── events.py             # NEW: Event bus
│   ├── container.py          # NEW: DI container
│   └── ...
│
├── domain/                    # NEW: Rich domain models
│   ├── models.py             # Genome, Loadout, Song, etc.
│   ├── value_objects.py      # StatsVector, LoadoutHash, etc.
│   └── services.py           # Domain services
│
├── data/                      # Data layer (mostly keep)
│   ├── repositories/         # NEW: Repository pattern
│   │   ├── loadout_repository.py
│   │   └── song_repository.py
│   ├── csv_parser.py
│   └── migrations/           # NEW: Schema versioning
│
├── solver/                    # Algorithm layer
│   ├── genetic/              # Refactor from single file
│   │   ├── orchestrator.py   # Main coordinator
│   │   ├── commands/         # State-changing ops
│   │   └── queries/          # Read-only ops
│   ├── scoring/              # Keep as-is
│   └── gpu/                  # NEW: GPU abstraction
│       ├── backend.py        # Protocol/interface
│       ├── taichi_backend.py # Current impl
│       └── cpu_fallback.py   # Fallback impl
│
├── pipeline/                  # Song processing
│   ├── orchestrator.py       # Pipeline coordinator
│   ├── stages/               # Individual stages
│   └── context.py            # Pipeline context
│
├── integrations/             # NEW: External integrations
│   ├── discord/
│   └── metrics/              # Future: Prometheus/StatsD
│
└── app.py                    # Application entry point
```

---

## Quick Wins (Low Effort, High Value)

1. **Add `__all__` exports** to all `__init__.py` files for cleaner imports
2. **Create type aliases** for complex types (`GenomeArray = np.ndarray`, `StatsDict = Dict[str, float]`)
3. **Move magic numbers to constants** (e.g., `TOP_N_RETENTION = 51`)
4. **Add schema versioning** for database migrations
5. **Create a `Result[T]` type** for operations that can fail (instead of raising exceptions)

---

## Priority Matrix

| Improvement | Impact | Effort | Priority |
|-------------|--------|--------|----------|
| DI Container | High | Medium | ⭐⭐⭐ |
| Event Bus | High | Low | ⭐⭐⭐ |
| GPU Backend Abstraction | High | High | ⭐⭐ |
| Typed Config | Medium | Low | ⭐⭐⭐ |
| Repository Pattern | Medium | Medium | ⭐⭐ |
| Command/Query Separation | Medium | High | ⭐ |
| Pipeline Pattern | Medium | Medium | ⭐⭐ |
| Domain Models | High | High | ⭐⭐ |

---

## Implementation Roadmap

### Phase 1: Foundation (Quick Wins)
- Add `__all__` exports to all modules
- Create type aliases for complex types
- Move magic numbers to constants
- Add schema versioning infrastructure

### Phase 2: Configuration & Events
- Implement typed dataclass configuration
- Add lightweight event bus
- Migrate Discord reporter to event-driven

### Phase 3: Data Layer
- Implement repository pattern for database
- Add database migrations support
- Create domain models for core entities

### Phase 4: Algorithm Layer
- Abstract GPU backend interface
- Implement command/query separation for GA
- Refactor song processor to pipeline pattern

### Phase 5: Integration
- Implement DI container
- Wire all components through container
- Add metrics/observability integrations

---

## Existing Patterns & Conventions (Preserve These)

### Naming Conventions
- **GA tuning parameters:** `GA_SearchDepth`, `GA_MultiStart`, `GA_MemeticElites`
- **Cache objects:** `*_CACHE` (e.g., GEM_SOLVER_CACHE)
- **Configuration sections:** `[IterationEngine]`, `[Gear]`, `[Minis]`
- **File naming:** `solver_*`, `gpu_*`, `taichi_*` for GPU-related modules
- **Function naming:** Action-verb pattern (`calculate_`, `optimize_`, `load_`, `save_`)

### Code Organization
- **Single responsibility:** Each file handles one major concern
- **Import grouping:** Standard library → Third-party → Relative imports
- **JIT functions:** Placed in dedicated modules (jit_setup.py, fever_timeline.py)
- **Test files:** Parallel structure to source (test_*.py for modules, conftest.py for fixtures)

### Error Handling
- **Graceful degradation:** Falls back to CPU if GPU unavailable
- **WarnOnce pattern:** Prevents log spam for repetitive warnings
- **Try-except wrapping:** Defensive imports for optional dependencies
- **Logging:** WARNING level for memory/performance issues

---

## Architecture Strengths to Preserve

1. **Clean Separation of Concerns**
   - 6 distinct layers with clear responsibilities
   - No circular dependencies
   - Modular design (92 files, average 360 LOC each)

2. **Performance Optimization**
   - Multiple acceleration strategies (JIT, GPU, caching, parallel)
   - Memory watchdog prevents OOM crashes
   - Async I/O keeps critical path fast

3. **Maintainability**
   - Comprehensive test suite (44 files)
   - Well-documented (README, architecture docs, code comments)
   - Backward-compatible refactoring (large files → focused modules)

4. **Extensibility**
   - Factory pattern for GA operators
   - Strategy pattern for FG optimization
   - Environment-driven configuration

---

## Key Design Decisions to Preserve

1. **Cross-Process GPU Ownership** - Prevents Taichi conflicts
2. **Dual-Table Architecture** - Separates base + FG loadouts
3. **Lazy Initialization** - Faster startup, deferred GPU setup
4. **Batch Evaluation** - Amortizes GPU kernel overhead
5. **Resume Tracking** - Graceful OOM recovery
6. **LRU Caching** - Triple-layer hit rate optimization
7. **Async DB Saver** - Prevents I/O blocking

---

## Areas of Complexity (Handle With Care)

1. **Fever Timeline Calculation** - Reverse-engineered from server
2. **Force Greats Optimization** - 3D search space (FT/FF/loadout)
3. **GPU Kernel Dispatch** - Taichi fields, field reuse
4. **Memory Management** - Cross-platform limits, process tree tracking
5. **Configuration** - Multiple override layers (env, INI, defaults)

---

# Repository Structure Beyond gear_optimizer/

## Root-Level Entry Points

### Primary Entry Points

| File | LOC | Purpose |
|------|-----|---------|
| `main.py` | 21 | Main application entry point - initializes `GearOptimizerApp`, handles multiprocessing and exceptions |
| `general_meta_main.py` | 67 | Universal loadout finder - cross-song gem allocation optimizer, exports to `general_meta_results.json` |

---

## Scripts Directory (56 Python files across 7 subdirectories)

Ad-hoc debugging, profiling, DB inspection, and one-off queries. Ruff linting is disabled for scripts (prioritize working code over strict formatting).

### scripts/data/ (5 scripts)
Data manipulation and song-specific loading helpers:

| Script | Purpose |
|--------|---------|
| `dump_ice_angel_raw.py` | Debug database dumps for Ice Angel |
| `evaluate_reference_loadout.py` | Evaluate specific loadout configurations |
| `ice_angel_gems.py` | Ice Angel gem-specific analysis |
| `populate_ice_angel_real.py` | Populate Ice Angel with actual data |
| `repopulate_and_verify_ice_angel.py` | Verify and re-populate Ice Angel data |

### scripts/db/ (9 scripts)
Database inspection, verification, and schema checking:

| Script | Purpose |
|--------|---------|
| `check_db_consistency.py` | Verify DB integrity |
| `check_new_schema.py` | Schema validation for new changes |
| `check_top_entries.py` | Verify top loadout entries |
| `inspect_db_format.py` | Format inspection |
| `inspect_full_db.py` | Comprehensive database inspection |
| `show_db_rankings.py` | Display rankings by song |
| `verify_db_contents.py` | Content verification |
| `verify_schema.py` | Schema verification |
| `verify_timestamps.py` | Timestamp integrity checks |

### scripts/debug/ (5 scripts)
Bug reproduction and regression testing:

| Script | Purpose |
|--------|---------|
| `debug_heuristic_ranking.py` | Debug ranking heuristics |
| `reproduce_fg_visibility.py` | Force Greats visibility issues |
| `reproduce_truncation.py` | Score truncation reproduction |
| `verify_note_types.py` | Note type validation |
| `verify_top.py` | Top score verification |

### scripts/fg/ (10 scripts)
Force Greats exploration and verification:

| Script | Purpose |
|--------|---------|
| `check_fg_base_score.py` | Base score consistency |
| `check_fg_diversity.py` | Diversity metrics |
| `check_fg_entries.py` | Entry validation |
| `check_fg_mismatch.py` | FG/base score mismatches |
| `fg_probe.py` | FG configuration probing |
| `find_fg_keys.py` | Key discovery |
| `scan_fg_diversity.py` | Diversity scanning |
| `show_fg_structure.py` | Structure visualization |
| `verify_fg_json_structure.py` | JSON validation |
| `verify_fg_pruning.py` | Pruning verification |

### scripts/profile/ (13 scripts)
Performance profiling and benchmarking:

| Script | Purpose |
|--------|---------|
| `analyze_profile.py` | Profile analysis |
| `measure_fg_perf.py` | Force Greats performance measurement |
| `profile_fg.py` | FG profiling |
| `profile_ga_gpu.py` | GA GPU profiling |
| `profile_hotspots.py` | Hotspot detection |
| `profile_main.py` | Main loop profiling with PERF_TIMING |
| `profile_main_hot.py` | Hot path profiling |
| `profile_main_hot_nocold.py` | Isolated hot path profiling |
| `profile_multi_song.py` | Multi-song profiling |
| `profile_parallel.py` | Parallel execution profiling |
| `profile_parallel_scale.py` | Parallelization scaling |
| `profile_song.py` | Single song profiling |
| `test_parallel_stall.py` | Parallel stall analysis |

### scripts/query/ (10 scripts)
Ad-hoc database queries and result analysis:

| Script | Purpose |
|--------|---------|
| `compare_bopeebo_loadouts.py` | Compare Bopeebo loadouts |
| `find_song_by_gear.py` | Reverse lookup: gear → songs |
| `find_song_name.py` | Song name search |
| `query_bopeebo.py` | Bopeebo song queries |
| `query_feeling_alright.py` | Feeling Alright queries |
| `query_ice_angel.py` | Ice Angel loadout queries |
| `query_top_loadouts.py` | Top loadout queries across songs |
| `show_all_bopeebo_loadouts.py` | Complete Bopeebo leaderboards |
| `show_leaderboards.py` | Song leaderboards |
| `show_remember_loadouts.py` | Remember song queries |

### scripts/regression/ (3 scripts)
Regression baseline and comparison:

| Script | Purpose |
|--------|---------|
| `regression_baseline.py` | Baseline comparison |
| `regression_fixed.py` | Fixed version comparison |
| `regression_ga.py` | GA regression testing |

### scripts/AGENTS.md
Developer guidelines for scripts:
- **Role:** Ad-hoc debugging, profiling, DB inspection, one-off queries
- **Convention:** Safe to run from repo root with relative paths
- **Environment variables:** `EVOLUTION_DB_PATH`, `METAFINDER_CONFIG_PATH`, `GA_SEED`, `GPU_EXECUTOR_PROFILE`
- **Linting:** Ruff disabled (prioritize working code over strict formatting)

---

## Tools Directory (22 Python files across 6 subdirectories)

Maintained utilities for development workflow. Ruff linting disabled; keep scripts readable.

### tools/bench/ (2 scripts)
Benchmarking and performance testing:

| Script | Purpose |
|--------|---------|
| `benchmark_gpu.py` | GPU benchmark harness |
| `bench_fg_reliability.py` | Force Greats reliability benchmarking |

### tools/db/ (7 scripts)
Database maintenance and inspection:

| Script | Purpose |
|--------|---------|
| `backfill_stats.py` | Backfill missing statistics |
| `check_db.py` | DB health check |
| `check_db_fg.py` | FG database verification |
| `check_force.py` | Force mode checking |
| `clean_db_test.py` | Test database cleanup |
| `db_inspector.py` | Interactive database inspector |
| `debug_entries.py` | Debug individual entries |

### tools/data/ (4 scripts)
Data format conversion and statistics:

| Script | Purpose |
|--------|---------|
| `calc_stats.py` | Calculate statistics |
| `eval_take_your_time.py` | "Take Your Time" song evaluation |
| `osu_to_songdata.py` | Osu! format conversion |
| `reseed_take_your_time_record.py` | Seed management |

### tools/dev/ (2 items)
Developer workflow helpers:

| Item | Purpose |
|------|---------|
| `quality_check.ps1` | PowerShell quality check script (syntax check, Ruff linting, pytest subset) |
| `cleanup_test_data.py` | Test artifact cleanup |

**quality_check.ps1 Usage:**
```powershell
powershell -ExecutionPolicy Bypass -File tools/dev/quality_check.ps1 [-Fix]
```
- Syntax check via `compileall`
- Ruff linting with optional `-Fix` parameter
- Quick pytest subset (FG performance + Taichi parity tests)

### tools/meta/ (1 script)
| Script | Purpose |
|--------|---------|
| `general_meta_main.py` | Wrapper/entrypoint for meta analysis |

### tools/verify/ (3 scripts)
Correctness verification:

| Script | Purpose |
|--------|---------|
| `debug_gear_rank.py` | Gear ranking validation |
| `validate_gpu_native_eval.py` | GPU native evaluation validation |
| `verify_loadout.py` | Individual loadout validation |

### tools/profile/ (3 scripts)
Profiling infrastructure:

| Script | Purpose |
|--------|---------|
| `inspect_prof.py` | Profile analysis tool |
| `profile_ga.py` | GA profiling |
| `tests/profile_ga.py`, `tests/profile_gpu_batch.py` | Profile test variants |

### tools/AGENTS.md
Developer guidelines for tools:
- **Role:** Maintained utilities (benchmarks, verifiers, dev scripts)
- **Convention:** Do not change behavior that production code depends on
- **Linting:** Ruff disabled; keep scripts readable

---

## Configuration Files

### Root Config Files

| File | Lines | Purpose |
|------|-------|---------|
| `config.ini` | 119 | Main configuration file |
| `config_profile_baseline.ini` | - | Baseline profiling config |
| `config_profile_inflight.ini` | - | In-flight pipeline profiling config |

### config.ini Sections

| Section | Purpose |
|---------|---------|
| `[CalculateSong]` | Target song/difficulty selection |
| `[IterationEngine]` | GA settings (SearchDepth, MultiStart, DeepMining) |
| `[IterationEngine]` | GPU settings (GPU_Mode, GPU_Native_GA) |
| `[IterationEngine]` | ForceGreats controls (FG_CandidateLimit, FG_SearchRadius) |
| `[IterationEngine]` | FG exploration knobs (NeighborSweep settings) |
| `[IterationEngine]` | Resource limits (EvalCPUCores, MaxParallelSongs, InFlightSongs) |
| `[TeamContributionBuffConstant]` | Default buffs/colors |
| `[Gear]` | Starting gear (6 slots) |
| `[Minis]` | Starting minis (3 slots) |
| `[UserInputStatsGems]` | Stats overrides |
| `[ElementalGems]` | Elemental gem overflow amounts |
| `[HumanHitSim]` | Human hit simulation (Enabled, ApplyTo, Seed, Distribution, GreatMode) |
| `[ForceGreats]` | Manual FG settings (NonFever1, NonFever2, etc.) |

### Bin Directory Configs
Located in `/bin` (for profiling runs):
- `config.profile.ini` - Profile run configuration
- `config_aether_applyto_fg.ini` - Aether debug config (FG mode)
- `config_aether_hard_debug.ini` - Aether debug config (hard debugging)

---

## Data Directory (2,169 files)

Organized song data by difficulty:

```
Data/
├── Easy/          # Song difficulty: Easy
├── Normal/        # Song difficulty: Normal
├── Hard/          # Song difficulty: Hard
└── Gear/          # Gear/equipment metadata
```

Each `.txt` file contains song-specific data including note timings, gem requirements, and scoring details.

---

## Test Infrastructure (44 test files)

Comprehensive test suite in `/tests`:

### Test Categories

| Category | Files | Purpose |
|----------|-------|---------|
| GPU Integration | 8 | Executor, batch ops, IPC |
| Taichi Parity | 2 | GPU/CPU result matching |
| Force Greats | 4 | Correctness & performance |
| GA Validation | 3 | Return values, deep mining |
| Database | 6 | Persistence, merging, schema |
| API Stability | 1 | Compatibility checks |
| Regression | 2 | Bug prevention |

### Test Files

| File | Purpose |
|------|---------|
| `conftest.py` | Pytest configuration, test DB setup |
| `test_analytical_*.py` (3 files) | Force greats accuracy |
| `test_api_stability.py` | API compatibility checks |
| `test_async_fg_integrity.py` | Async FG thread safety |
| `test_breakpoint_parity.py` | GPU-CPU parity at checkpoints |
| `test_calculate_only_force_greats_candidates.py` | FG candidate calculation |
| `test_cpu_gpu_fg_parity.py` | Force greats equivalence |
| `test_db_*.py` (6 files) | Database round-tripping |
| `test_double_retention.py` | Top-N retention logic |
| `test_fever_solver_stats_persistence.py` | Fever timeline caching |
| `test_fg_*.py` (4 files) | Force greats specific tests |
| `test_gpu_*.py` (8 files) | GPU executor & kernels |
| `test_parity_smoke.py` | Quick sanity checks |
| `regression_*.py` (2 files) | Fixed bugs |

### Test Configuration (conftest.py)

```python
# Isolate test DB in temporary directory
tmp_db = tempfile.mktemp(prefix="gear_optimizer_tests_db_")
shutil.copy2(evolution.db, tmp_db)
os.environ["EVOLUTION_DB_PATH"] = tmp_db
init_db()

# Fixtures for benchmark fallback (without pytest-benchmark)
@pytest.fixture
def benchmark():
    """Minimal replacement for pytest-benchmark."""
    def measure(func, *args, **kwargs):
        return func(*args, **kwargs)
    return measure
```

### Test Markers

```python
@pytest.mark.slow        # Long-running tests
@pytest.mark.gpu         # GPU-required tests
```

### Test Fixture
- `tests/fixtures/dummy_song.txt` - Test song data

---

## Documentation Structure

### Main Documentation (`/docs`)

| File | Purpose |
|------|---------|
| `ARCHITECTURE.md` | System architecture and layer diagrams |
| `DATABASE_SCHEMA.md` | SQLite schema (dual-table architecture) |
| `DATABASE_MERGE.md` | Database merging procedures |
| `DATABASE_MERGE_BUG_FIX.md` | Merge bug fixes and solutions |
| `CHANGES_SUMMARY.md` | Changelog and version updates |
| `CODEBASE_CLEANUP_PLAN.md` | Refactoring roadmap |
| `FEVER_TIMELINE_MATH.md` | Fever mechanics mathematics |
| `TAICHI_PORT_ROADMAP.md` | GPU kernel migration plan |
| `OPTIMIZATION_ANALYSIS.md` | Performance optimization details |
| `REFACTORING_VALIDATION.md` | Validation procedures post-refactor |
| `NAVIGATION.md` | Codebase navigation guide |
| `HUMAN_HIT_SIM.md` | Human hit simulation implementation |
| `HELPER_EXTRACTION.md` | Helper module extraction documentation |
| `FG_PRECISION_PROPOSAL_LETTER.md` | Force Greats precision improvements |
| `FORMULA EXPLANATION.txt` | Scoring formula documentation |

### Implementation Records (`/docs/Implementation Records`)

| File | Purpose |
|------|---------|
| `FEVER_FIX_PLAN.md` | Fever timeline fixes |
| `FG_FEVER_SHIFT_PARITY_PLAN.md` | FG/fever shift alignment |
| `FG_FP_TARGET_INVERSE_BUG_FIX.md` | FG precision bugs |
| `FG_PRECISION_UPDATE.md` | Precision improvement tracking |
| `GPU_BUG_FIXES.md` | GPU-specific bug fixes |
| `GREAT_PENALTY_IMPLEMENTATION.md` | Great timing penalty implementation |

### Legacy Documentation (`/docs/legacy`)
- Historical refactoring guides and status documents
- Phase completion records

---

## Artifacts & Profiling

### `/bin` Directory
Contains runtime outputs and profiling data (gitignored):

| Content | Examples |
|---------|----------|
| CPU/GPU Performance Samples | `cpu_samples_*.csv`, `gpu_samples_*.csv` |
| TypePerf Metrics | `cpu_typeperf_*.csv`, `gpu_typeperf_*.csv` |
| Profile Dumps | `profile_main_*.prof`, `prof_*.pstats` |
| Configuration Snapshots | `config*.ini` (from profiling runs) |
| Caches | Numba JIT cache, paths cache JSON |
| Debug Logs | `error.log`, `profile_*.txt` |

### `/artifacts` Directory
Organized benchmarking and run results:

```
artifacts/
├── configs/        # Configuration snapshots
├── logs/           # Execution logs
├── profiles/       # Profile outputs
└── runs/           # Benchmark runs
    ├── baseline_neighbors/
    ├── runs_bench_neighbors_10/
    ├── runs_bench_neighbors_minis_10/
    └── (many other benchmark variants)
```

### Root-Level Profiling Files
- `prof_baseline.pstats` - Baseline performance profile
- `prof_inflight.pstats` - In-flight pipeline profile
- `prof_inflight_native_skip.pstats` - Native skip variant

---

## Build & Dependency Configuration

### pyproject.toml (57 lines)

**Project metadata:**
- RoBeats MetaFinder v2.0.0
- Python 3.9+

**Ruff configuration:**
- 120-char line length, Python 3.9 target
- Linting rules: E, W, F (pycodestyle, pyflakes)
- Relaxed rules for scripts/tools (F401, F841)
- Format: double quotes, space indent

**Pytest configuration:**
- Test discovery: `tests/test_*.py`
- Markers: `slow`, `gpu`
- Addopts: `-v --tb=short`

### requirements.txt (8 packages)

| Package | Purpose |
|---------|---------|
| `numpy` | Numerical computation |
| `numba` | JIT compilation |
| `taichi` | GPU kernels |
| `psutil` | System monitoring |
| `requests` | HTTP requests |
| `python-dotenv` | Environment variables |
| `cachetools` | LRU caching |

### requirements-dev.txt

| Package | Purpose |
|---------|---------|
| `pytest` | Testing framework |
| `ruff` | Linting and formatting |

---

## Git Configuration

### .gitignore Excludes:
- Python bytecode, caches, virtual envs
- Local database (`evolution.db`)
- Profiling artifacts, test results
- Sensitive configs (`.env` files)
- `bin/` directory (local logs/temp)
- `artifacts/` directory (benchmarks)

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `EVOLUTION_DB_PATH` | Custom database location |
| `METAFINDER_CONFIG_PATH` | Custom config.ini location |
| `GA_SEED` | Deterministic GA testing |
| `PERF_TIMING` | Performance profiling |
| `GPU_SYNC_FOR_TIMING` | Force GPU sync for timing accuracy |
| `GPU_EXECUTOR_PROFILE` | GPU executor profiling |

---

## Repository Statistics Summary

| Component | Count | Notes |
|-----------|-------|-------|
| **Scripts** | 56 | Across 7 focused subdirectories |
| **Tools** | 22 | Across 6 maintained utility subdirectories |
| **Test Files** | 44 | Comprehensive suite with GPU isolation |
| **Documentation** | 18+ | Plus 6 implementation records + legacy docs |
| **Data Files** | 2,169 | Song data across 4 difficulty levels |
| **Config Files** | 7+ | Main + profiling variants |
| **Core Dependencies** | 8 | NumPy, Numba, Taichi, psutil, requests, python-dotenv, cachetools |
| **Dev Dependencies** | 3 | pytest, ruff |

---

## Proposed Improvements for Non-gear_optimizer Components

### 9. Consolidate Scripts into Tools

**Current State:** 56 scripts in `scripts/` with overlapping functionality with `tools/`.

**Proposal:** Merge scripts into tools with clear categories:

```
tools/
├── debug/           # Merged from scripts/debug/ + scripts/data/
├── db/              # Keep existing + merge scripts/db/
├── profile/         # Keep existing + merge scripts/profile/
├── query/           # NEW: Merge scripts/query/
├── fg/              # NEW: Merge scripts/fg/
├── regression/      # NEW: Merge scripts/regression/
├── bench/           # Keep existing
├── data/            # Keep existing
├── dev/             # Keep existing
└── verify/          # Keep existing
```

**Benefits:**
- Single location for all utilities
- Clearer organization
- Easier discoverability

---

### 10. Standardize Script Entry Points

**Current State:** Scripts have inconsistent entry point patterns.

**Proposal:** Add a CLI runner with subcommands:

```python
# tools/cli.py
import click

@click.group()
def cli():
    """RoBeats MetaFinder development tools."""
    pass

@cli.command()
@click.argument('song_name')
def query_song(song_name):
    """Query loadouts for a specific song."""
    ...

@cli.command()
@click.option('--fix', is_flag=True)
def quality_check(fix):
    """Run quality checks (syntax, lint, tests)."""
    ...

# Usage: python -m tools query-song "Ice Angel"
# Usage: python -m tools quality-check --fix
```

**Benefits:**
- Discoverability via `--help`
- Consistent argument parsing
- Tab completion support

---

### 11. Test Fixture Improvements

**Current State:** Single dummy song fixture, manual test DB setup.

**Proposal:** Enhanced fixture system:

```python
# tests/fixtures/
├── songs/
│   ├── simple_song.txt      # Basic test case
│   ├── edge_case_song.txt   # Edge cases
│   └── performance_song.txt # Large song for benchmarks
├── loadouts/
│   ├── known_good.json      # Pre-computed correct results
│   └── regression_cases.json
└── configs/
    ├── minimal.ini          # Minimal config for fast tests
    └── full.ini             # Full config for integration tests

# conftest.py additions
@pytest.fixture
def known_good_loadouts():
    """Load pre-computed correct results for validation."""
    return load_json("tests/fixtures/loadouts/known_good.json")

@pytest.fixture
def minimal_config():
    """Fast test configuration."""
    return load_config("tests/fixtures/configs/minimal.ini")
```

**Benefits:**
- Reproducible test data
- Faster test discovery
- Regression prevention

---

### 12. Documentation Consolidation

**Current State:** 18+ docs spread across `/docs`, implementation records, and legacy.

**Proposal:** Reorganize with clear hierarchy:

```
docs/
├── README.md                # Overview and navigation
├── user/                    # User-facing documentation
│   ├── QUICKSTART.md
│   ├── CONFIGURATION.md
│   └── TROUBLESHOOTING.md
├── developer/               # Developer documentation
│   ├── ARCHITECTURE.md
│   ├── CONTRIBUTING.md
│   └── TESTING.md
├── reference/               # Technical reference
│   ├── DATABASE_SCHEMA.md
│   ├── FORMULA_EXPLANATION.md
│   └── FEVER_TIMELINE_MATH.md
├── decisions/               # Architecture Decision Records (ADRs)
│   ├── 001-gpu-backend.md
│   ├── 002-dual-table-architecture.md
│   └── ...
└── changelog/               # Version history
    └── CHANGELOG.md
```

**Benefits:**
- Clear audience targeting
- Easier navigation
- ADR pattern for future decisions

---

### 13. Profiling Infrastructure Improvements

**Current State:** Profiling scripts scattered, manual artifact management.

**Proposal:** Unified profiling framework:

```python
# tools/profile/runner.py
class ProfilingRunner:
    def __init__(self, config: ProfilingConfig):
        self.config = config
        self.artifacts_dir = Path("artifacts/profiles")

    def run(self, target: str, iterations: int = 1) -> ProfilingResult:
        """Run profiling with automatic artifact management."""
        timestamp = datetime.now().isoformat()
        run_dir = self.artifacts_dir / f"{target}_{timestamp}"
        run_dir.mkdir(parents=True)

        # Run profiling
        result = self._profile(target, iterations)

        # Save artifacts
        result.save_pstats(run_dir / "profile.pstats")
        result.save_flamegraph(run_dir / "flamegraph.svg")
        result.save_summary(run_dir / "summary.json")

        return result

    def compare(self, baseline: str, current: str) -> ComparisonReport:
        """Compare two profiling runs."""
        ...
```

**Benefits:**
- Consistent artifact naming
- Automatic comparison
- Historical tracking

---

## Updated Priority Matrix (Including Non-gear_optimizer)

| Improvement | Impact | Effort | Priority |
|-------------|--------|--------|----------|
| DI Container | High | Medium | ⭐⭐⭐ |
| Event Bus | High | Low | ⭐⭐⭐ |
| Typed Config | Medium | Low | ⭐⭐⭐ |
| Consolidate Scripts → Tools | Medium | Low | ⭐⭐⭐ |
| Documentation Consolidation | Medium | Low | ⭐⭐ |
| Test Fixture Improvements | Medium | Medium | ⭐⭐ |
| GPU Backend Abstraction | High | High | ⭐⭐ |
| Repository Pattern | Medium | Medium | ⭐⭐ |
| Pipeline Pattern | Medium | Medium | ⭐⭐ |
| CLI Runner for Tools | Low | Low | ⭐⭐ |
| Domain Models | High | High | ⭐⭐ |
| Command/Query Separation | Medium | High | ⭐ |
| Profiling Infrastructure | Low | Medium | ⭐ |

---

## Updated Implementation Roadmap

### Phase 1: Foundation (Quick Wins)
- Add `__all__` exports to all modules
- Create type aliases for complex types
- Move magic numbers to constants
- Add schema versioning infrastructure
- **Consolidate scripts/ into tools/**
- **Reorganize documentation structure**

### Phase 2: Configuration & Events
- Implement typed dataclass configuration
- Add lightweight event bus
- Migrate Discord reporter to event-driven
- **Add CLI runner for tools**

### Phase 3: Data Layer
- Implement repository pattern for database
- Add database migrations support
- Create domain models for core entities
- **Enhance test fixtures**

### Phase 4: Algorithm Layer
- Abstract GPU backend interface
- Implement command/query separation for GA
- Refactor song processor to pipeline pattern

### Phase 5: Integration
- Implement DI container
- Wire all components through container
- Add metrics/observability integrations
- **Unified profiling infrastructure**
