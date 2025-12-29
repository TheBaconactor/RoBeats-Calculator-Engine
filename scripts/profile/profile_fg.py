"""
Profile Force Greats (FG) GPU processing to identify bottlenecks.

Measures:
1. Kernel dispatch overhead (per-chunk)
2. Data upload/download times
3. Stage 1 vs Stage 2 timing
4. Total FG solve time per genome batch
"""

import os
import sys
import time

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Enable sync for accurate timing
os.environ["GPU_SYNC_FOR_TIMING"] = "1"
os.environ["GPU_FORCE_SYNC"] = "1"

import numpy as np


def profile_fg_processing():
    """Profile FG processing with detailed timing breakdown."""
    from gear_optimizer.solver.fever_timeline import SongTimelineGrid
    from gear_optimizer.solver.taichi_gem import api as gem_api
    from gear_optimizer.solver.taichi_gem.force_greats import api as fg_api
    from gear_optimizer.solver.taichi_gem.force_greats import fields as fg_fields
    from gear_optimizer.solver.taichi_gem.force_greats import kernels as fg_kernels
    from gear_optimizer.solver.taichi_gem import fields as gem_fields
    import taichi as ti

    print("=" * 70)
    print("FORCE GREATS (FG) PROFILE")
    print("=" * 70)

    # Setup test data
    ref_arrays = {
        "Perfect Points": np.linspace(0, 100, 161, dtype=np.float64),
        "Combo Multiplier": np.linspace(1, 2, 161, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.5, 3.1, 161, dtype=np.float64),
        "Fever Fill Rate": np.linspace(0.5, 1.8, 161, dtype=np.float64),
        "Fever Time": np.linspace(0.5, 1.8, 161, dtype=np.float64),
    }

    # Generate test song (typical length)
    timestamps = np.linspace(0, 120, 800, dtype=np.float32)
    long_notes = 50
    last_note_time = 120.0

    # Generate FG configs (reduced for fast profiling)
    # Each config is per-section forced great counts [0, 1, 2] x n_sections
    n_sections = 4  # Reduced for faster runs
    n_configs = 81  # 3^4 = 81 configs

    # Generate all possible configs (0,1,2 for each section)
    from itertools import product

    fg_configs = list(product([0, 1, 2], repeat=n_sections))
    print(f"  FG configs: {len(fg_configs)}")

    # Generate FTFF pairs (FT x FF gem combinations)
    # Use step of 15 for faster runs and smaller pair set
    ftff_pairs = [(ft, ff) for ft in range(0, 91, 15) for ff in range(0, 91 - ft, 15)]
    print(f"  FT/FF pairs: {len(ftff_pairs)}")

    # Test with smaller genome counts for faster profiling
    genome_counts = [1, 10, 50, 100]

    results = {}

    for n_genomes in genome_counts:
        print(f"\n{'=' * 70}")
        print(f"  n_genomes = {n_genomes}")
        print(f"{'=' * 70}")

        # Generate genome stats
        genome_stats = [
            {
                "base_pp": 50 + i % 20,
                "base_cm": 50 + i % 15,
                "base_fm": 50 + i % 10,
                "base_p_val": 100 + i % 30,
                "base_s_val": 50 + i % 20,
                "base_ft_stat": 30 + i % 40,
                "base_ff_stat": 30 + i % 40,
            }
            for i in range(n_genomes)
        ]

        # Warmup
        print("  Warmup...")
        _ = fg_api.solve_force_greats_finder_gpu(
            genome_stats[: min(5, n_genomes)],
            timestamps,
            long_notes,
            last_note_time,
            fg_configs[:100],
            ftff_pairs[:10],
            n_sections=n_sections,
            is_p_ft=1,
            is_s_ft=0,
            is_p_ff=0,
            is_s_ff=1,
            is_p_pp=1,
            is_s_pp=0,
            is_p_cm=0,
            is_s_cm=1,
            is_p_fm=1,
            is_s_fm=0,
            is_p_ov=0,
            is_s_ov=1,
            ref_arrays=ref_arrays,
            total_budget=90,
            gem_scale_fever=3,
            cfg_chunk=8192,
        )
        ti.sync()

        # Full profile run
        print("  Running full profile...")

        chunk_sizes = [64, 128, 256, 512]

        for cfg_chunk in chunk_sizes:
            times = []
            for trial in range(2):
                t0 = time.perf_counter()

                _ = fg_api.solve_force_greats_finder_gpu(
                    genome_stats,
                    timestamps,
                    long_notes,
                    last_note_time,
                    fg_configs,
                    ftff_pairs,
                    n_sections=n_sections,
                    is_p_ft=1,
                    is_s_ft=0,
                    is_p_ff=0,
                    is_s_ff=1,
                    is_p_pp=1,
                    is_s_pp=0,
                    is_p_cm=0,
                    is_s_cm=1,
                    is_p_fm=1,
                    is_s_fm=0,
                    is_p_ov=0,
                    is_s_ov=1,
                    ref_arrays=ref_arrays,
                    total_budget=90,
                    gem_scale_fever=3,
                    cfg_chunk=cfg_chunk,
                )
                ti.sync()

                elapsed = time.perf_counter() - t0
                times.append(elapsed)

            avg_time = np.mean(times)
            n_chunks = (len(fg_configs) + cfg_chunk - 1) // cfg_chunk
            n_work_items = n_genomes * len(ftff_pairs)
            total_kernel_calls = n_chunks + 2  # stage1 per chunk + init + stage2

            print(
                f"    cfg_chunk={cfg_chunk:5d}: {avg_time * 1000:8.2f}ms "
                f"({n_chunks:2d} chunks, {total_kernel_calls:2d} kernel calls, "
                f"{avg_time / total_kernel_calls * 1000:.3f}ms/kernel)"
            )

            results[(n_genomes, cfg_chunk)] = {
                "avg_time_ms": avg_time * 1000,
                "n_chunks": n_chunks,
                "n_work_items": n_work_items,
                "kernel_calls": total_kernel_calls,
                "ms_per_kernel": avg_time / total_kernel_calls * 1000,
            }

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY: Kernel Dispatch Analysis")
    print("=" * 70)
    print(f"{'Genomes':<10} {'Chunk':<8} {'Total ms':<12} {'Kernels':<10} {'ms/kernel':<12}")
    print("-" * 70)
    for (ng, chunk), data in sorted(results.items()):
        print(
            f"{ng:<10} {chunk:<8} {data['avg_time_ms']:<12.2f} {data['kernel_calls']:<10} {data['ms_per_kernel']:<12.3f}"
        )

    print("\n" + "=" * 70)
    print("RECOMMENDATION")
    print("=" * 70)

    # Find optimal chunk size
    best_by_genomes = {}
    for (ng, chunk), data in results.items():
        if ng not in best_by_genomes or data["avg_time_ms"] < best_by_genomes[ng][1]:
            best_by_genomes[ng] = (chunk, data["avg_time_ms"])

    for ng, (chunk, time_ms) in sorted(best_by_genomes.items()):
        print(f"  {ng} genomes: best chunk_size = {chunk}, time = {time_ms:.2f}ms")


if __name__ == "__main__":
    profile_fg_processing()
