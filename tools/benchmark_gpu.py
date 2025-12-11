"""
GPU Benchmark - Measures throughput of Taichi Vulkan Gem Solver.

Tests:
1. Single-item latency
2. Batch throughput (varying batch sizes)
3. Large batch (simulating full GA population)
"""
import numpy as np
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gear_optimizer.solver.taichi_gem_solver import (
    init_taichi_vulkan,
    load_ref_arrays,
    optimize_gems_batch_gpu,
)
from gear_optimizer.solver.scoring_core import optimize_core_jit
from gear_optimizer.core.constants import (
    GEM_SCALE_NORMAL,
    GEM_SCALE_FEVER,
    GEM_STAT_TO_ELEMENT_SCALE,
    ELEMENTAL_GEM_SCALE,
    TOTAL_ROWS,
    MAX_STAT_INDEX,
)


def create_ref_arrays():
    """Create realistic reference arrays."""
    pp = np.array([i * 2.5 for i in range(161)], dtype=np.float64)
    cm = np.array([1.0 + i * 0.005 for i in range(161)], dtype=np.float64)
    fm = np.array([1.5 + i * 0.01 for i in range(161)], dtype=np.float64)
    return {"Perfect Points": pp, "Combo Multiplier": cm, "Fever Multiplier": fm}


def create_work_item():
    """Create a realistic work item."""
    fever_mask = np.array([i % 3 == 0 for i in range(100)], dtype=np.bool_)
    return {
        "budget": 90,
        "fever_mask_head": fever_mask,
        "count_body_fever": 150,
        "count_body_normal": 250,
        "ft_gems": 0,
        "ff_gems": 0,
    }


def benchmark_cpu(ref_arrays, n_items, warmup=5):
    """Benchmark CPU Numba JIT performance."""
    fever_mask = np.array([i % 3 == 0 for i in range(100)], dtype=np.bool_)
    
    # Warmup
    for _ in range(warmup):
        optimize_core_jit(
            90, 100, 80, 60, 500, 300,
            1, 0, 0, 1, 0, 0, 1, 0,
            ref_arrays["Perfect Points"],
            ref_arrays["Combo Multiplier"],
            ref_arrays["Fever Multiplier"],
            fever_mask, 150, 250,
            GEM_SCALE_NORMAL, GEM_SCALE_FEVER,
            GEM_STAT_TO_ELEMENT_SCALE, ELEMENTAL_GEM_SCALE,
            TOTAL_ROWS, MAX_STAT_INDEX,
        )
    
    start = time.perf_counter()
    for _ in range(n_items):
        optimize_core_jit(
            90, 100, 80, 60, 500, 300,
            1, 0, 0, 1, 0, 0, 1, 0,
            ref_arrays["Perfect Points"],
            ref_arrays["Combo Multiplier"],
            ref_arrays["Fever Multiplier"],
            fever_mask, 150, 250,
            GEM_SCALE_NORMAL, GEM_SCALE_FEVER,
            GEM_STAT_TO_ELEMENT_SCALE, ELEMENTAL_GEM_SCALE,
            TOTAL_ROWS, MAX_STAT_INDEX,
        )
    elapsed = time.perf_counter() - start
    
    return elapsed, n_items / elapsed


def benchmark_gpu_batch(ref_arrays, batch_size, n_batches, warmup=3):
    """Benchmark GPU batch performance."""
    batch_input = [create_work_item() for _ in range(batch_size)]
    
    # Warmup
    for _ in range(warmup):
        optimize_gems_batch_gpu(
            batch_input,
            100, 80, 60, 500, 300,
            0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0,
            ref_arrays,
        )
    
    start = time.perf_counter()
    for _ in range(n_batches):
        optimize_gems_batch_gpu(
            batch_input,
            100, 80, 60, 500, 300,
            0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0,
            ref_arrays,
        )
    elapsed = time.perf_counter() - start
    
    total_items = batch_size * n_batches
    return elapsed, total_items / elapsed


def main():
    print("=" * 70)
    print("TAICHI VULKAN GEM SOLVER BENCHMARK - RX 7900 XTX")
    print("=" * 70)
    print()
    
    ref_arrays = create_ref_arrays()
    
    # Initialize GPU
    print("Initializing Taichi Vulkan...")
    init_taichi_vulkan()
    load_ref_arrays(ref_arrays)
    print()
    
    # CPU Baseline
    print("-" * 70)
    print("CPU BASELINE (Numba JIT, single-threaded)")
    print("-" * 70)
    
    cpu_items = 1000
    elapsed, throughput = benchmark_cpu(ref_arrays, cpu_items)
    print(f"  Items processed: {cpu_items:,}")
    print(f"  Time: {elapsed:.3f}s")
    print(f"  Throughput: {throughput:,.0f} items/sec")
    cpu_throughput = throughput
    print()
    
    # GPU Benchmarks
    print("-" * 70)
    print("GPU BENCHMARKS (Taichi Vulkan)")
    print("-" * 70)
    
    batch_configs = [
        (1, 1000, "Single item (latency test)"),
        (10, 500, "Small batch (10)"),
        (100, 100, "Medium batch (100)"),
        (1000, 50, "Large batch (1000)"),
        (5000, 20, "Very large batch (5000)"),
        (10000, 10, "Mega batch (10000)"),
        (50000, 5, "Population batch (50000)"),
    ]
    
    best_throughput = 0
    best_config = ""
    
    for batch_size, n_batches, label in batch_configs:
        try:
            elapsed, throughput = benchmark_gpu_batch(ref_arrays, batch_size, n_batches)
            speedup = throughput / cpu_throughput
            
            if throughput > best_throughput:
                best_throughput = throughput
                best_config = label
            
            print(f"\n  {label}:")
            print(f"    Batch size: {batch_size:,} | Batches: {n_batches}")
            print(f"    Time: {elapsed:.3f}s")
            print(f"    Throughput: {throughput:,.0f} items/sec")
            print(f"    Speedup vs CPU: {speedup:.1f}x")
            
        except Exception as e:
            print(f"\n  {label}: FAILED - {e}")
    
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  CPU throughput:     {cpu_throughput:>12,.0f} items/sec")
    print(f"  Best GPU throughput:{best_throughput:>12,.0f} items/sec")
    print(f"  Best config:        {best_config}")
    print(f"  MAX SPEEDUP:        {best_throughput / cpu_throughput:>12.1f}x")
    print("=" * 70)


if __name__ == "__main__":
    main()
