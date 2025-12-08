# Gear Optimizer

A high-performance genetic algorithm solver for optimizing gear and mini loadouts in rhythm games. Features JIT-compiled scoring, parallel song processing, and intelligent caching for maximum throughput.

## Quick Start

### 1. Run the Optimizer

No setup required! The optimizer automatically discovers your Data folder structure on first run.

```bash
python main.py
```

The optimizer will:
- Load all songs from Data folders
- Run genetic algorithm optimization for each song
- Store results in `evolution.db` SQLite database
- Report progress via Discord webhooks (if configured)

## Configuration

Edit `config.ini` to customize behavior:

```ini
[Gear Optimizer]
enable_stats = 1              # Enable/disable processing
enable_force_greats = 0       # Force greats simulation
max_depth = 75                # GA generation depth
workers = 4                   # Parallel worker count
memory_limit_pct = 80         # Memory watchdog threshold
```

Add Discord credentials to `Discord.env`:

```env
DISCORD_BOT_TOKEN=your_token_here
DISCORD_LOG_CHANNEL_ID=123456789
DISCORD_STATS_CHANNEL_ID=987654321
```

## Project Structure

```
Gear Optimizer/
├── main.py                    # Main entry point
├── cleanup_duplicates.py      # Database cleanup utility
├── config.ini                 # User configuration
├── Discord.env                # Discord credentials
├── evolution.db               # SQLite results database
│
├── gear_optimizer/            # Core package (12 modules + helpers)
│   ├── constants.py           # Global constants
│   ├── models.py              # Data classes
│   ├── utils.py               # Utility functions
│   ├── config.py              # Config management
│   ├── database.py            # SQLite operations
│   ├── csv_parser.py          # CSV parsing
│   ├── jit_setup.py           # Numba JIT wrapper
│   ├── scoring.py             # Scoring engine (1,105 lines)
│   ├── genetic.py             # GA solver (424 lines, refactored)
│   ├── memory.py              # Memory watchdog
│   ├── discord_reporter.py    # Discord integration
│   ├── song_processor.py      # Song orchestration (561 lines, refactored)
│   └── helpers/               # Helper modules for modularity
│       ├── song_helpers.py    # Song processing helpers (7 functions)
│       └── ga_helpers.py      # GA algorithm helpers (9 functions)
│
├── Data/                      # Song files
│   ├── Easy/
│   ├── Normal/
│   ├── Hard/
│   ├── Gear.csv
│   ├── Minis.csv
│   └── Stats.txt
│
├── bin/                       # Runtime data
│   ├── paths_cache.json       # Cached folder paths
│   ├── error.log              # Error logging
│   └── build/                 # JIT compilation cache
│
├── tests/                     # Test suite
│   └── test_refactoring.py    # Validation tests (8/8 passing)
│
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md        # System architecture
│   ├── REFACTORING_VALIDATION.md  # Test results
│   └── legacy/                # Old refactoring guides
│
└── legacy/                    # Archived code
    ├── Manual_Calculator - Main.py      # Original 5,196-line monolith
    └── Manual_Calculator - Original.py  # Pre-refactor version
```

## Features

### Performance Optimizations
- **JIT Compilation:** Numba-accelerated scoring functions (10-100x speedup)
- **Parallel Processing:** Multi-process song evaluation with shared memory
- **Intelligent Caching:** LRU caches for gem solver, fever timelines, force greats
- **Memory Watchdog:** Auto-restart when RAM usage exceeds threshold

### Algorithm Features
- **Co-Evolution GA:** Simultaneous gear and mini optimization
- **Memetic Search:** Local search hill-climbing after crossover
- **Multi-Start Restarts:** Escape local optima with fresh populations
- **Pareto Pruning:** Remove dominated gear to reduce search space
- **Deep Mining:** Iterative refinement of best-known solutions

### Data Management
- **SQLite Database:** Efficient storage with WAL mode, batch inserts
- **Loadout Deduplication:** SHA256 hashing prevents redundant evaluations
- **Stats Signatures:** Deterministic cache keys for identical configurations

## Architecture

### Layered Design

1. **Foundation Layer** (constants.py, models.py, utils.py)
   - Global configuration and data structures
   - Pure utility functions with no dependencies

2. **Data Layer** (config.py, database.py, csv_parser.py, jit_setup.py)
   - Configuration management and file I/O
   - SQLite CRUD operations
   - CSV parsing for gear/minis/stats

3. **Algorithm Layer** (scoring.py, genetic.py)
   - Core scoring engine with JIT optimization
   - Genetic algorithm solver (424 lines, refactored)

4. **Helper Layer** (helpers/song_helpers.py, helpers/ga_helpers.py)
   - Song processing workflow helpers (7 functions)
   - GA algorithm operator helpers (9 functions)
   - Extracted from monolithic functions for improved modularity

5. **Infrastructure Layer** (memory.py, discord_reporter.py)
   - Memory watchdog with cross-platform RAM detection
   - Discord webhook integration with rate limiting

6. **Orchestration Layer** (song_processor.py, main.py)
   - Song processing workflow (561 lines, refactored)
   - Multi-process execution and result aggregation

### Key Algorithms

#### Scoring Engine (scoring.py)
- Reference table lookups for stat-to-multiplier conversion
- Combo ramp calculation with fever multipliers
- Fever timeline segmentation (head + body optimization)
- Force greats penalty simulation
- JIT-optimized gem allocation (greedy search)

#### Genetic Algorithm (genetic.py)
- Population initialization with random gear/mini selection
- Fitness evaluation via scoring engine
- Tournament selection (k=3)
- Single-point crossover with memetic hill-climbing
- Elite preservation (top 10%)
- Multi-start restarts every 15 generations

## Testing

Run the validation test suite:

```bash
cd tests
python test_refactoring.py
```

Expected output: **8/8 tests passed**

Tests validate:
1. Reference lookup function
2. Fast score calculation
3. Fever timeline calculation
4. JIT gem optimizer
5. Force greats evaluation
6. Stats signature generation
7. Loadout hash generation
8. Gear pruning (Pareto dominance)

See [docs/REFACTORING_VALIDATION.md](docs/REFACTORING_VALIDATION.md) for detailed test results.

## Development

### Module Architecture

The refactored codebase separates concerns into 12 core modules + 2 helper modules:

- **Core Modules:** constants, models, utils
- **Data Modules:** config, database, csv_parser, jit_setup
- **Algorithm Modules:** scoring, genetic
- **Helper Modules:** song_helpers (7 functions), ga_helpers (9 functions)
- **Infrastructure Modules:** memory, discord_reporter
- **Orchestration Modules:** song_processor

**Helper Modules** break down monolithic functions:
- `song_helpers.py` - Extracted from 815-line `process_song_task()`
- `ga_helpers.py` - Extracted from 749-line `solve_coevolution_genetic()`

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/HELPER_EXTRACTION.md](docs/HELPER_EXTRACTION.md) for details.

### Import Hierarchy

```
main.py
  ├─ config.py → constants, models, utils
  ├─ database.py → constants, models
  ├─ memory.py → discord_reporter
  ├─ song_processor.py
  │   ├─ helpers/song_helpers.py → database, models, config, csv_parser, scoring, utils
  │   ├─ scoring.py → constants, models, utils, csv_parser, jit_setup
  │   ├─ genetic.py
  │   │   └─ helpers/ga_helpers.py → constants, utils, database, scoring
  │   └─ discord_reporter.py → utils
  └─ discord_reporter.py
```

No circular dependencies - clean hierarchical structure with modular helpers.

## Troubleshooting

### "Could not find Data folder"
Run `python Bootstrapper.py` to regenerate path cache.

### "Memory limit exceeded"
Increase `memory_limit_pct` in config.ini or reduce `workers`.

### "No module named 'numba'"
Install dependencies: `pip install numba numpy`

### JIT compilation warnings
First run compiles functions (slow). Subsequent runs use cached JIT code.

## Performance Tips

1. **Memory Management:** Set `memory_limit_pct` to 70-80% for stable operation
2. **Worker Count:** Use `workers = CPU_count - 1` for best throughput
3. **GA Depth:** Increase `max_depth` for better solutions (slower)
4. **Caching:** Don't clear `bin/build/` - contains JIT compilation cache

## Credits

**Original Implementation:** 5,196-line monolith (see legacy/)

**Refactored Architecture:** Modular design with 12 core modules + 16 helper functions

**Refactoring Highlights:**
- Eliminated monolithic functions (815 lines → 367 lines, 749 lines → 331 lines)
- Created 2 helper modules with 16 focused functions
- 100% functionally equivalent (8/8 tests passing)
- No circular dependencies

**Date:** December 2025

## License

This project is for personal use. All rights reserved.
