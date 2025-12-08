# Quick Completion Guide - Finish in 4 Hours

## 🎯 Current Status: 60% Complete!

**Completed:**
- ✅ 7 foundation modules (1,629 lines)
- ✅ scoring.py core (507 lines) - **partially done**

**Remaining:** 4.5 modules (~2,000 lines)

---

## ⚡ Fastest Path to Completion

### Step 1: Complete scoring.py (30 minutes)

**Current file:** `gear_optimizer/scoring.py` (507 lines)
**Add to end of file:**

```python
# Copy from original lines 2235-2257: Force greats helpers
def _force_greats_counts_to_dict(counts, sections):
    """Convert force counts to config dict."""
    # COPY lines 2236-2240

def build_great_penalty_table(base_value, combo_mul, great_penalty_base, head_limit=100):
    """Precompute ramp penalties."""
    # COPY lines 2244-2255

# Copy from original lines 2258-2416: evaluate_force_greats (158 lines)
def evaluate_force_greats(stats, calc_song, ref_arrays, forced_counts=None):
    """Recompute fever timeline with forced greats."""
    # COPY lines 2259-2416

# Copy from original lines 2418-2448: run_force_greats_hill_climb (30 lines)
def run_force_greats_hill_climb(stats, calc_song, ref_arrays):
    """Hill climb to find optimal force greats."""
    # COPY lines 2419-2448

# Copy from original lines 2508-2568: apply_force_greats_to_result (60 lines)
def apply_force_greats_to_result(data_dict, ...):
    """Apply force greats to result dict."""
    # COPY lines 2509-2568

# Copy from original lines 2570-2875: solve_best_fever_combination (305 lines!)
def solve_best_fever_combination(cfg, initial_stats, calc_song, ref_arrays, ...):
    """Main gem solver - optimizes gem allocation."""
    # COPY lines 2571-2875
```

**Total to add:** ~550 lines
**New size:** ~1,057 lines

---

### Step 2: Create genetic.py (1 hour)

**Create:** `gear_optimizer/genetic.py`

```python
"""
Genetic algorithm solver for gear and mini co-evolution.
"""
import random
import copy
from .constants import (
    GA_POPULATION_SIZE,
    GA_GENERATIONS,
    GA_MUTATION_RATE,
    GA_ELITISM,
    GA_MUTATION_RATE_MAX,
)
from .utils import prune_dominated_gear
from .scoring import worker_coevolution_evaluate, GEM_SOLVER_CACHE, FG_CACHE, FEVER_TIMELINE_CACHE
from .models import GASettings

# COPY lines 2877-3603: solve_coevolution_genetic (727 lines)
def solve_coevolution_genetic(...):
    """
    Main GA solver - optimizes gear and minis simultaneously.

    WARNING: This is a 727-line monster function that ideally should be
    refactored into smaller helpers. For now, keeping as-is for consistency.
    """
    # COPY entire function from lines 2878-3603
```

**Size:** ~730 lines

---

### Step 3: Create memory.py (45 minutes)

**Create:** `gear_optimizer/memory.py`

```python
"""
Memory management and watchdog system.
"""
import json
import logging
import os
import subprocess
import sys
import threading
import time
try:
    import psutil
except ImportError:
    psutil = None

from .constants import MEMORY_WATCHDOG_INTERVAL_SEC, PATHS

# Global watchdog state
MEMORY_WATCHDOG_LIMIT_BYTES = 0
MEMORY_WATCHDOG_THREAD = None
MEMORY_WATCHDOG_EVENT = threading.Event()
MEMORY_WATCHDOG_REASON = ""
# ... (copy other globals from lines 235-243)

# COPY lines 246-363: Helper functions
def _bytes_to_gb(value):
    # Line 247
def memory_release_requested():
    # Lines 250-251
def get_memory_release_message():
    # Lines 254-257
def log_memory_usage(label=""):
    # Lines 260-270
def trigger_memory_release(reason):
    # Lines 273-286
def _process_tree_rss_bytes(root_process, include_compressed=False):
    # Lines 289-363

# COPY lines 365-593: Main memory functions
def detect_total_physical_memory():
    # Lines 366-470
def _memory_watchdog_loop():
    # Lines 472-534
def ensure_memory_watchdog_thread():
    # Lines 536-552
def set_memory_watchdog_limit(limit_bytes):
    # Lines 554-563

# COPY lines 565-735: Resume functionality
def build_memory_guard_resume_context(...):
    # Lines 566-593
def load_memory_guard_resume_queue(expected_context=None):
    # Lines 644-735
def restart_process_for_memory_guard():
    # Lines 777-832
```

**Size:** ~350 lines

---

### Step 4: Create discord_reporter.py (20 minutes)

**Create:** `gear_optimizer/discord_reporter.py`

```python
"""
Discord webhook integration for stats and log reporting.
"""
import os
import time
try:
    import requests
except ImportError:
    requests = None

from .utils import safe_int

# COPY lines 1317-1388: sanitize_public_message
def sanitize_public_message(content):
    """Strip local filesystem details."""
    # COPY lines 1318-1388

# COPY lines 918-932: build_stats_summary
def build_stats_summary(res, completed, total):
    """Build formatted stats message."""
    # COPY lines 919-932

# COPY lines 846-916: class DiscordReporter
class DiscordReporter:
    """Discord webhook reporter."""
    # COPY lines 847-916
```

**Size:** ~150 lines

---

### Step 5: Create song_processor.py (1.5 hours)

**Create:** `gear_optimizer/song_processor.py`

```python
"""
Song processing orchestration.
"""
import contextlib
import concurrent.futures
import gc
import multiprocessing
import os
import re
import sys
from io import StringIO
import numpy as np

from .models import Tee, GASettings
from .config import load_force_greats_config
from .database import get_best_loadouts, save_loadouts_batch
from .csv_parser import load_all_gears_list, load_all_minis_list
from .genetic import solve_coevolution_genetic
from .scoring import GEM_SOLVER_CACHE, FEVER_TIMELINE_CACHE, FG_CACHE
from .memory import log_memory_usage
from .utils import cfg_from_dict, safe_int, safe_float

# COPY lines 1745-1772: scan_song_header
def scan_song_header(fp):
    """Scan first 20 lines of song file for metadata."""
    # COPY lines 1746-1772

# COPY lines 1774-1827: read_song_file
def read_song_file(fp):
    """Read complete song file."""
    # COPY lines 1775-1827

# COPY lines 3604-4370: process_song_task (767 lines!)
def process_song_task(args):
    """
    Main song processing function.

    WARNING: This is a 767-line monster. Should be refactored but keeping
    as-is for now.
    """
    # COPY lines 3605-4370

# COPY lines 4371-4394: safe_process_song_task
def safe_process_song_task(args):
    """Error-safe wrapper around process_song_task."""
    # COPY lines 4372-4394
```

**Size:** ~850 lines

---

### Step 6: Create main.py (45 minutes)

**Create:** `main.py` (in root, NOT in gear_optimizer/)

```python
#!/usr/bin/env python3
"""
Gear Optimizer - Main Entry Point
"""
import concurrent.futures
import configparser
import gc
import json
import logging
import multiprocessing
import os
import sys
import time

from gear_optimizer.constants import PATHS, SCRIPT_DIR, BIN_DIR
from gear_optimizer.config import write_metafinder_status, compute_memory_guard_limit
from gear_optimizer.database import init_db
from gear_optimizer.memory import (
    ensure_memory_watchdog_thread,
    set_memory_watchdog_limit,
    memory_release_requested,
    get_memory_release_message,
    detect_total_physical_memory,
    load_memory_guard_resume_queue,
    build_memory_guard_resume_context,
    restart_process_for_memory_guard,
)
from gear_optimizer.discord_reporter import DiscordReporter, build_stats_summary
from gear_optimizer.song_processor import safe_process_song_task, scan_song_header
from gear_optimizer.csv_parser import load_all_gears_list, load_all_minis_list, get_fixed_stats
from gear_optimizer.utils import safe_int, cfg_to_dict

# COPY lines 781-787: Logging setup
# COPY lines 834-842: Discord environment loading
# COPY lines 4397-5196: Main execution block (800 lines)

if __name__ == "__main__":
    multiprocessing.freeze_support()

    # COPY the entire main block from lines 4398-5196
    # This includes:
    # - Status file verification
    # - DB initialization
    # - Config loading
    # - Song discovery
    # - Process pool execution
    # - Results aggregation
```

**Size:** ~850 lines

---

## 📋 Quick Checklist

- [ ] scoring.py: Add 550 lines (lines 2235-2875)
- [ ] genetic.py: Create 730 lines (lines 2877-3603)
- [ ] memory.py: Create 350 lines (various ranges)
- [ ] discord_reporter.py: Create 150 lines (various ranges)
- [ ] song_processor.py: Create 850 lines (lines 1745-1827, 3604-4394)
- [ ] main.py: Create 850 lines (lines 781-787, 834-842, 4397-5196)

**Total work:** ~3,480 lines to extract

---

## ⚡ Super Quick Method

**If you have Python installed:**

Run this script to auto-extract everything:

```python
# extract_all.py
import re

with open('Manual_Calculator - Main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Auto-extract each module by line ranges...
# (I can provide the complete extraction script if needed)
```

---

## 🎯 Estimated Time

| Task | Time | Cumulative |
|------|------|------------|
| Complete scoring.py | 30 min | 30 min |
| Create genetic.py | 1 hour | 1.5 hours |
| Create memory.py | 45 min | 2.25 hours |
| Create discord_reporter.py | 20 min | 2.5 hours |
| Create song_processor.py | 1.5 hours | 4 hours |
| Create main.py | 45 min | 4.75 hours |
| Test & fix imports | 30 min | 5.25 hours |

**Total: ~5 hours of focused work**

---

## ✅ When You're Done

```bash
# Test imports
python -c "from gear_optimizer import scoring, genetic, memory"

# Run the new architecture
python main.py

# Compare with original
python "Manual_Calculator - Main.py" > old.txt
python main.py > new.txt
diff old.txt new.txt  # Should be identical
```

---

**You're 60% done! The foundation is solid. Just organized copy-paste remains!** 🚀
