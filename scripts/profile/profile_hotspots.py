"""
Profiling script to identify hotspots in the GPU pipeline.

Run with: python scripts/profile_hotspots.py

This profiles:
1. Python-side overhead (cProfile)
2. GPU kernel timing (gpu_profiler)
3. Taichi kernel breakdown (TAICHI_KERNEL_PROFILER=1)
"""

import os
import sys
import cProfile
import pstats
import io
import time

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Enable profilers
os.environ["GPU_PROFILER"] = "1"
# Ensure kernel time is measured separately from download time (adds sync points).
os.environ["GPU_SYNC_FOR_TIMING"] = "1"
os.environ["TAICHI_KERNEL_PROFILER"] = "1"

import numpy as np


def profile_solve_genomes():
    """Profile the core GPU solver path."""
    from gear_optimizer.solver.taichi_gem.api import (
        solve_genomes_parallel,
        load_ref_arrays,
    )
    from gear_optimizer.solver.fever_timeline import SongTimelineGrid
    from gear_optimizer.solver.gpu_profiler import get_gpu_profiler
    import taichi as ti
    
    profiler = get_gpu_profiler()
    profiler.reset()
    
    # Create test data
    ref_arrays = {
        "Perfect Points": np.linspace(0, 100, 161, dtype=np.float64),
        "Combo Multiplier": np.linspace(1, 2, 161, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.5, 3.1, 161, dtype=np.float64),
        "Fever Fill Rate": np.linspace(0.5, 1.8, 161, dtype=np.float64),
        "Fever Time": np.linspace(0.5, 1.8, 161, dtype=np.float64),
    }
    
    # Simulate 500 genomes (typical GA population)
    n_genomes = 500
    genome_stats_list = []
    for i in range(n_genomes):
        genome_stats_list.append({
            "base_pp": 50 + i % 20,
            "base_cm": 50 + i % 15,
            "base_fm": 50 + i % 10,
            "base_p_val": 100 + i % 30,
            "base_s_val": 50 + i % 20,
            "base_ft_stat": 30 + i % 40,
            "base_ff_stat": 30 + i % 40,
        })
    
    # Create timeline grid
    timestamps = np.linspace(0, 120, 800)  # Typical song length
    calc_song = {
        "song_data": {"timestamps": timestamps},
        "metadata": {
            "Long Notes": 20,
            "Last Note Time": 120.0,
            "Primary Color": "Chill",
            "Secondary Color": "Flow",
        }
    }
    
    grid = SongTimelineGrid(calc_song, ref_arrays)
    
    # Color flags
    is_p_pp, is_s_pp = 1, 0
    is_p_cm, is_s_cm = 0, 1
    is_p_fm, is_s_fm = 0, 0
    is_p_ov, is_s_ov = 1, 0
    is_p_ft, is_s_ft = 0, 0
    is_p_ff, is_s_ff = 0, 0
    
    print("=" * 60)
    print("PROFILING GPU SOLVE PATH")
    print("=" * 60)
    print(f"Genomes: {n_genomes}")
    print(f"Notes: {len(timestamps)}")
    print()
    
    # Warmup (first call has JIT overhead)
    print("Warmup run...")
    profiler.start_song("warmup")
    t0 = time.perf_counter()
    _ = solve_genomes_parallel(
        genome_stats_list[:10],  # Small warmup
        grid,
        is_p_ft, is_s_ft, is_p_ff, is_s_ff,
        is_p_pp, is_s_pp, is_p_cm, is_s_cm,
        is_p_fm, is_s_fm, is_p_ov, is_s_ov,
        ref_arrays,
    )
    warmup_time = time.perf_counter() - t0
    profiler.end_song()
    print(f"Warmup: {warmup_time:.3f}s (includes JIT)")
    profiler.reset()  # Reset after warmup
    
    # Timed run
    print()
    print("Timed run (5 iterations)...")
    
    times = []
    for run in range(5):
        profiler.start_song(f"run_{run}")
        t0 = time.perf_counter()
        results = solve_genomes_parallel(
            genome_stats_list,
            grid,
            is_p_ft, is_s_ft, is_p_ff, is_s_ff,
            is_p_pp, is_s_pp, is_p_cm, is_s_cm,
            is_p_fm, is_s_fm, is_p_ov, is_s_ov,
            ref_arrays,
        )
        elapsed = time.perf_counter() - t0
        profiler.end_song()
        times.append(elapsed)
        print(f"  Run {run+1}: {elapsed:.3f}s ({len(results)} results)")
    
    print()
    print("=" * 60)
    print("TIMING SUMMARY")
    print("=" * 60)
    print(f"Avg time per batch: {np.mean(times):.3f}s")
    print(f"Min: {np.min(times):.3f}s, Max: {np.max(times):.3f}s")
    print(f"Genomes/sec: {n_genomes / np.mean(times):.0f}")
    print()
    
    # GPU profiler report
    profiler.report()
    
    # Print Taichi kernel stats
    print()
    print("=" * 60)
    print("TAICHI KERNEL PROFILER")
    print("=" * 60)
    try:
        ti.profiler.print_kernel_profiler_info("count")
    except Exception as e:
        print(f"Kernel profiler not available: {e}")
    
    return times


def run_cprofile():
    """Run cProfile to find Python-side hotspots."""
    print()
    print("=" * 60)
    print("PYTHON CPROFILE (cumulative)")
    print("=" * 60)
    
    pr = cProfile.Profile()
    pr.enable()
    
    times = profile_solve_genomes()
    
    pr.disable()
    
    # Print top 20 by cumulative time
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
    ps.print_stats(30)
    print(s.getvalue())


if __name__ == "__main__":
    run_cprofile()
