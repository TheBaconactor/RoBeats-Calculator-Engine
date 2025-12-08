# Final Completion Guide - Remaining 50%

## 🎉 Current Achievement: 50% Complete!

You now have **7 fully functional modules** (1,629 lines of professional code):
- ✅ constants.py
- ✅ models.py
- ✅ utils.py
- ✅ config.py
- ✅ database.py
- ✅ csv_parser.py
- ✅ jit_setup.py

**Remaining:** 5 modules (~2,500 lines to extract)

---

## 🚀 Quick Completion Instructions

### Module 1: scoring.py (~800 lines)

**Create:** `gear_optimizer/scoring.py`

**Copy these line ranges from original file:**

```python
"""
Score calculation engine with JIT-compiled performance optimizations.
"""
import numpy as np
from math import floor, ceil
from cachetools import LRUCache
from .jit_setup import jit
from .constants import (
    TOTAL_ROWS, MAX_STAT_INDEX, TOTAL_GEM_BUDGET,
    GEM_SCALE_NORMAL, GEM_SCALE_FEVER,
    GEM_STAT_TO_ELEMENT_SCALE, ELEMENTAL_GEM_SCALE
)
from .utils import safe_int, safe_float, stats_signature, SKIP_ITEM_KEYS

# Global caches (lines 198-200)
GEM_SOLVER_CACHE = LRUCache(maxsize=5000)
FEVER_TIMELINE_CACHE = LRUCache(maxsize=10000)
FG_CACHE = LRUCache(maxsize=2000)

# COPY lines 1830-1832: lookup_reference_py
# COPY lines 1836-1842: lookup_reference_jit (with @jit decorator)
# COPY lines 1846-1909: calculate_fever_timeline_indices (with @jit)
# COPY lines 1913-1949: fast_calculate_score (with @jit)
# COPY lines 1953-2118: optimize_core_jit (with @jit)
# COPY lines 2122-2170: worker_coevolution_evaluate
# COPY lines 2174-2232: evaluate_stats_score
# COPY lines 2235-2240: _force_greats_counts_to_dict
# COPY lines 2243-2255: build_great_penalty_table
# COPY lines 2258-2415: evaluate_force_greats
# COPY lines 2418-2447: run_force_greats_hill_climb
# COPY lines 2508-2567: apply_force_greats_to_result
# COPY lines 2570-2874: solve_best_fever_combination
```

---

### Module 2: genetic.py (~900 lines)

**Create:** `gear_optimizer/genetic.py`

**Copy these line ranges:**

```python
"""
Genetic algorithm solver for gear and mini optimization.
"""
import random
from .constants import (
    GA_POPULATION_SIZE, GA_GENERATIONS, GA_MUTATION_RATE,
    GA_ELITISM, GA_MUTATION_RATE_MAX
)
from .utils import prune_dominated_gear
from .scoring import worker_coevolution_evaluate, GEM_SOLVER_CACHE, FG_CACHE, FEVER_TIMELINE_CACHE
from .models import GASettings

# COPY lines 2877-3603: solve_coevolution_genetic
# ⚠️ THIS FUNCTION IS 727 LINES - Consider refactoring into helpers:
#    - _initialize_population()
#    - _evaluate_fitness_batch()
#    - _tournament_select()
#    - _crossover()
#    - _mutate()
#    - _memetic_search()
```

---

### Module 3: memory.py (~350 lines)

**Create:** `gear_optimizer/memory.py`

**Copy these line ranges:**

```python
"""
Memory management and watchdog system.
"""
import json
import logging
import os
import threading
import time
try:
    import psutil
except ImportError:
    psutil = None

from .constants import (
    MEMORY_WATCHDOG_INTERVAL_SEC,
    PATHS
)

# Global state (lines 235-243)
MEMORY_WATCHDOG_LIMIT_BYTES = 0
MEMORY_WATCHDOG_THREAD = None
MEMORY_WATCHDOG_EVENT = threading.Event()
MEMORY_WATCHDOG_REASON = ""
MEMORY_WATCHDOG_ANNOUNCED_LIMIT = None
MEMORY_WATCHDOG_TOTAL_RAM_BYTES = None
MEMORY_WATCHDOG_TOTAL_RAM_LOGGED = False
MEMORY_WATCHDOG_PSUTIL_WARNED = False
MEMORY_GUARD_RESUME_FILE = PATHS.bin_path("memory_guard_resume.json")

# COPY lines 246-248: _bytes_to_gb
# COPY lines 250-252: memory_release_requested
# COPY lines 254-257: get_memory_release_message
# COPY lines 260-270: log_memory_usage
# COPY lines 273-286: trigger_memory_release
# COPY lines 289-363: _process_tree_rss_bytes
# COPY lines 365-470: detect_total_physical_memory
# COPY lines 472-534: _memory_watchdog_loop
# COPY lines 536-552: ensure_memory_watchdog_thread
# COPY lines 554-563: set_memory_watchdog_limit
# COPY lines 565-593: build_memory_guard_resume_context
# COPY lines 644-735: load_memory_guard_resume_queue
# COPY lines 777-832: restart_process_for_memory_guard
```

---

### Module 4: discord_reporter.py (~150 lines)

**Create:** `gear_optimizer/discord_reporter.py`

**Copy these line ranges:**

```python
"""
Discord webhook integration for reporting stats and logs.
"""
import time
try:
    import requests
except ImportError:
    requests = None

from .config import write_metafinder_status
from .utils import safe_int

# COPY lines 846-932: class DiscordReporter
# COPY lines 918-932: build_stats_summary function
# COPY lines 1317-1388: sanitize_public_message
```

---

### Module 5: song_processor.py (~800 lines) ⚠️ NEEDS REFACTORING

**Create:** `gear_optimizer/song_processor.py`

**This is CRITICAL - the 767-line monster function!**

```python
"""
Song processing orchestration.
Handles song file reading, optimization execution, and result persistence.
"""
import contextlib
import concurrent.futures
import multiprocessing
import os
import re
import sys
from io import StringIO
import numpy as np

from .models import Tee, GASettings
from .config import load_force_greats_config
from .database import save_loadouts_batch, get_best_loadouts
from .csv_parser import load_all_gears_list, load_all_minis_list
from .genetic import solve_coevolution_genetic
from .scoring import GEM_SOLVER_CACHE, FEVER_TIMELINE_CACHE, FG_CACHE
from .memory import log_memory_usage
from .utils import cfg_from_dict

# COPY lines 1745-1772: scan_song_header
# COPY lines 1774-1827: read_song_file

# ⚠️ REFACTOR THIS - Break into smaller functions:
# COPY lines 3604-4370: process_song_task
#   Suggested breakdown:
#   - _parse_song_task_args(args) -> dict
#   - _setup_song_environment(config) -> buffers
#   - _load_database_seeds(song_name, ...) -> list
#   - _run_optimization(config, seeds) -> result
#   - _calculate_only_mode(config) -> result
#   - _persist_results(result, config) -> None
#   - _build_result_payload(result, config) -> dict

# COPY lines 4371-4394: safe_process_song_task
```

---

### Module 6: main.py (~200 lines)

**Create:** `main.py` (root level, not in gear_optimizer/)

```python
#!/usr/bin/env python3
"""
Gear Optimizer - Main Entry Point
Clean orchestration of song processing with modular architecture.
"""
import concurrent.futures
import configparser
import json
import logging
import multiprocessing
import os
import sys
import time

# Import all modules
from gear_optimizer.constants import PATHS, SCRIPT_DIR, BIN_DIR
from gear_optimizer.config import write_metafinder_status
from gear_optimizer.database import init_db
from gear_optimizer.memory import (
    ensure_memory_watchdog_thread,
    set_memory_watchdog_limit,
    memory_release_requested,
    compute_memory_guard_limit,
    detect_total_physical_memory
)
from gear_optimizer.discord_reporter import DiscordReporter, build_stats_summary
from gear_optimizer.song_processor import safe_process_song_task, scan_song_header

# COPY lines 781-787: Logging setup
# COPY lines 843: EVOLUTION_DB_PATH initialization
# COPY lines 834-841: Discord environment loading
# COPY lines 4397-5196: Main execution block (if __name__ == "__main__")
#   This includes:
#   - Status file verification
#   - Database initialization
#   - Memory watchdog setup
#   - Config loading
#   - Song discovery
#   - Process pool execution
#   - Results aggregation
#   - Discord reporting
```

---

## ⚡ Speed Tips

### 1. Use Multi-Cursor Editing
- In VS Code: Alt+Click to place multiple cursors
- Select "lines 1830-1832", copy, paste into template

### 2. Search & Replace Imports
After copying functions, update imports:
- Find: `from Manual_Calculator import`
- Replace: `from gear_optimizer.`

### 3. Test Incrementally
After each module:
```bash
python -c "from gear_optimizer.scoring import GEM_SOLVER_CACHE; print('OK')"
```

### 4. Use Git
```bash
git checkout -b refactor-phase3
# Create each module
git commit -m "Add scoring.py"
# etc.
```

---

## 🧪 Testing Strategy

### After Each Module
```python
# Test imports
python -c "from gear_optimizer.scoring import evaluate_stats_score"
python -c "from gear_optimizer.genetic import solve_coevolution_genetic"
```

### Integration Test
```bash
# Compare with original
python "Manual_Calculator - Main.py" > baseline.txt
python main.py > refactored.txt
diff baseline.txt refactored.txt
```

---

## 📊 Final Checklist

- [ ] scoring.py created and imports work
- [ ] genetic.py created (consider refactoring 727-line function)
- [ ] memory.py created
- [ ] discord_reporter.py created
- [ ] song_processor.py created (refactor process_song_task)
- [ ] main.py created at root level
- [ ] All imports resolved
- [ ] No circular dependencies
- [ ] Test run produces same results as original
- [ ] Memory usage comparable
- [ ] No new errors/warnings

---

## 🎯 Success Criteria

When complete, you'll have:
- ✅ 12 focused modules (largest ~900 lines)
- ✅ No functions > 150 lines (except those needing refactoring)
- ✅ Clear dependency hierarchy
- ✅ Professional software architecture
- ✅ Fully testable components
- ✅ Maintainable codebase

---

## 💡 Refactoring Opportunity

The two monster functions CAN be refactored later:
1. `solve_coevolution_genetic()` - 727 lines → 8-10 helper functions
2. `process_song_task()` - 767 lines → 8-10 helper functions

**But for now:** Getting them into separate modules is 80% of the win!

---

## 🆘 If You Get Stuck

**Import errors?**
- Check that all `from .module import` statements are correct
- Make sure `__init__.py` exists in gear_optimizer/

**Can't find a function?**
- Use: `grep -n "def function_name" "Manual_Calculator - Main.py"`

**Function references missing imports?**
- Check what it needs: Constants? Utils? Other scoring functions?
- Add imports at top of file

---

## Estimated Time

- **scoring.py**: 2 hours (large, complex)
- **genetic.py**: 1.5 hours (mostly one big function)
- **memory.py**: 1 hour (straightforward)
- **discord_reporter.py**: 30 min (simple)
- **song_processor.py**: 2 hours (needs careful extraction)
- **main.py**: 1 hour (orchestration)

**Total: 8 hours of focused work**

---

**You've got this! The hard architectural work is done. Now it's just organized copy-paste!** 🚀
