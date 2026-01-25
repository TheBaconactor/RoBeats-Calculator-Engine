#!/usr/bin/env python
"""
Benchmark: Python overhead in GA hot loop

Measures the time spent in Python code per-generation by simulating
the GA hot loop call pattern without actual GPU work.
"""

import os
import time
import numpy as np

# Simulate the old approach with per-call os.environ.get
def old_approach(n_genomes, n_combos):
    """Old approach: os.environ.get on every call"""
    prune_plateaus_i = 1
    raw_prune = str(os.environ.get("GPU_NATIVE_GA_PLATEAU_PRUNE", "1") or "").strip().lower()
    if raw_prune in {"0", "false", "no", "off"}:
        prune_plateaus_i = 0
    
    MAX_WORK_ITEMS = 4194304
    combo_chunk = n_combos
    if n_genomes * n_combos > MAX_WORK_ITEMS:
        try:
            target = int(MAX_WORK_ITEMS) // max(1, int(n_genomes))
        except Exception:
            target = 1024
        try:
            min_chunk = int(os.environ.get("GPU_NATIVE_GA_COMBO_CHUNK_MIN", "1024") or 1024)
        except Exception:
            min_chunk = 1024
        try:
            max_chunk = int(os.environ.get("GPU_NATIVE_GA_COMBO_CHUNK_MAX", "4096") or 4096)
        except Exception:
            max_chunk = 4096
        min_chunk = max(64, int(min_chunk))
        max_chunk = max(min_chunk, int(max_chunk))
        combo_chunk = int(min(int(n_combos), max_chunk, max(int(min_chunk), max(1, int(target)))))
    return prune_plateaus_i, combo_chunk


# New approach with cached module-level variables
_GA_PLATEAU_PRUNE_ENABLED = 1
_GA_COMBO_CHUNK_MIN = 1024
_GA_COMBO_CHUNK_MAX = 4096

def new_approach(n_genomes, n_combos):
    """New approach: cached module-level variables"""
    prune_plateaus_i = _GA_PLATEAU_PRUNE_ENABLED
    
    MAX_WORK_ITEMS = 4194304
    combo_chunk = n_combos
    if n_genomes * n_combos > MAX_WORK_ITEMS:
        target = MAX_WORK_ITEMS // max(1, n_genomes)
        combo_chunk = min(n_combos, _GA_COMBO_CHUNK_MAX, max(_GA_COMBO_CHUNK_MIN, max(1, target)))
    return prune_plateaus_i, combo_chunk


def benchmark(name, func, n_genomes, n_combos, n_iters):
    """Benchmark a function"""
    # Warmup
    for _ in range(100):
        func(n_genomes, n_combos)
    
    # Timed runs
    t0 = time.perf_counter()
    for _ in range(n_iters):
        func(n_genomes, n_combos)
    t1 = time.perf_counter()
    
    avg_us = (t1 - t0) * 1e6 / n_iters
    return avg_us


def main():
    print("=" * 60)
    print("GA Hot Loop Python Overhead Benchmark")
    print("=" * 60)
    print()
    
    n_genomes = 256
    n_combos = 4186
    n_iters = 10000
    
    # Benchmark both approaches
    old_us = benchmark("old", old_approach, n_genomes, n_combos, n_iters)
    new_us = benchmark("new", new_approach, n_genomes, n_combos, n_iters)
    
    print(f"Old approach (per-call os.environ.get): {old_us:.2f} µs/call")
    print(f"New approach (cached module vars):      {new_us:.2f} µs/call")
    print(f"Speedup: {old_us/new_us:.1f}x")
    print()
    
    # Estimate savings for typical run
    n_gens = 300  # 15 runs × 20 generations
    old_total_ms = old_us * n_gens / 1000
    new_total_ms = new_us * n_gens / 1000
    savings_ms = old_total_ms - new_total_ms
    
    print(f"Estimated savings per song ({n_gens} generations):")
    print(f"  Old total: {old_total_ms:.2f} ms")
    print(f"  New total: {new_total_ms:.2f} ms")
    print(f"  Saved:     {savings_ms:.2f} ms")
    print()
    
    # Verify correctness
    assert old_approach(256, 4186) == new_approach(256, 4186), "Results differ!"
    assert old_approach(1024, 4186) == new_approach(1024, 4186), "Results differ (chunking)!"
    print("✓ Correctness verified")


if __name__ == "__main__":
    main()
