#!/usr/bin/env python
"""
Benchmark: Dict vs Numpy unpacking for genome_base_stats upload.

Measures the CPU overhead of:
1. Current approach: Python loop over list[dict], extracting 7 keys per genome
2. Optimized: Pre-packed numpy array passed directly

This is a pure CPU benchmark (no GPU involved) to isolate the unpacking cost.
"""

import numpy as np
import time
from typing import Any

# Simulate the constants
MAX_GENOMES = 4096

# Pre-allocate buffer (as in current code)
_GENOME_STATS_CACHE = np.empty((MAX_GENOMES, 7), dtype=np.int16)


def make_genome_stats_dicts(n: int) -> list[dict[str, int]]:
    """Create n genome stats dictionaries (current format)."""
    return [
        {
            "base_pp": np.random.randint(0, 160),
            "base_cm": np.random.randint(0, 160),
            "base_fm": np.random.randint(0, 160),
            "base_p_val": np.random.randint(0, 1000),
            "base_s_val": np.random.randint(0, 1000),
            "base_ft_stat": np.random.randint(0, 160),
            "base_ff_stat": np.random.randint(0, 160),
        }
        for _ in range(n)
    ]


def make_genome_stats_numpy(n: int) -> np.ndarray:
    """Create n genome stats as a packed numpy array (optimized format)."""
    arr = np.empty((n, 7), dtype=np.int16)
    arr[:, 0] = np.random.randint(0, 160, n, dtype=np.int16)  # pp
    arr[:, 1] = np.random.randint(0, 160, n, dtype=np.int16)  # cm
    arr[:, 2] = np.random.randint(0, 160, n, dtype=np.int16)  # fm
    arr[:, 3] = np.random.randint(0, 1000, n, dtype=np.int16)  # p_val
    arr[:, 4] = np.random.randint(0, 1000, n, dtype=np.int16)  # s_val
    arr[:, 5] = np.random.randint(0, 160, n, dtype=np.int16)  # ft
    arr[:, 6] = np.random.randint(0, 160, n, dtype=np.int16)  # ff
    return arr


def unpack_current(genome_stats_list: list[dict], stats_buf: np.ndarray) -> None:
    """Current implementation: Python loop over dicts."""
    for i, stats in enumerate(genome_stats_list):
        stats_buf[i, 0] = stats["base_pp"]
        stats_buf[i, 1] = stats["base_cm"]
        stats_buf[i, 2] = stats["base_fm"]
        stats_buf[i, 3] = stats["base_p_val"]
        stats_buf[i, 4] = stats["base_s_val"]
        stats_buf[i, 5] = stats["base_ft_stat"]
        stats_buf[i, 6] = stats["base_ff_stat"]


def unpack_optimized_dict(genome_stats_list: list[dict], stats_buf: np.ndarray) -> None:
    """Optimized dict unpacking: enumerate keys, use list comp -> numpy."""
    keys = ["base_pp", "base_cm", "base_fm", "base_p_val", "base_s_val", "base_ft_stat", "base_ff_stat"]
    for j, k in enumerate(keys):
        stats_buf[:len(genome_stats_list), j] = [g[k] for g in genome_stats_list]


def unpack_numpy_passthrough(genome_stats_np: np.ndarray, stats_buf: np.ndarray) -> None:
    """Optimized: numpy array passed directly, just slice-copy."""
    n = genome_stats_np.shape[0]
    stats_buf[:n, :] = genome_stats_np


def benchmark_approach(name: str, setup_fn, unpack_fn, n_genomes: int, n_iters: int = 1000) -> float:
    """Benchmark an unpacking approach, return avg time in microseconds."""
    # Warmup
    data = setup_fn(n_genomes)
    buf = _GENOME_STATS_CACHE[:n_genomes]
    for _ in range(10):
        unpack_fn(data, buf)

    # Timed runs
    times = []
    for _ in range(n_iters):
        data = setup_fn(n_genomes)  # Fresh data each iter to avoid cache effects
        buf = _GENOME_STATS_CACHE[:n_genomes]
        t0 = time.perf_counter()
        unpack_fn(data, buf)
        times.append(time.perf_counter() - t0)

    avg_us = np.mean(times) * 1e6
    std_us = np.std(times) * 1e6
    return avg_us, std_us


def main():
    print("=" * 70)
    print("Genome Stats Unpacking Benchmark")
    print("=" * 70)
    print()

    # Test different genome counts (typical GA population sizes)
    genome_counts = [64, 128, 256, 512, 1024, 2048]
    n_iters = 500

    print(f"{'Genomes':>8} {'Current (dict loop)':>22} {'Optimized (list comp)':>22} {'Numpy passthrough':>22}")
    print(f"{'':>8} {'avg ± std (µs)':>22} {'avg ± std (µs)':>22} {'avg ± std (µs)':>22}")
    print("-" * 78)

    for n in genome_counts:
        # Current approach: dict loop
        avg1, std1 = benchmark_approach(
            "current",
            make_genome_stats_dicts,
            unpack_current,
            n,
            n_iters
        )

        # Optimized dict: list comprehension per column
        avg2, std2 = benchmark_approach(
            "optimized_dict",
            make_genome_stats_dicts,
            unpack_optimized_dict,
            n,
            n_iters
        )

        # Numpy passthrough (ideal case)
        avg3, std3 = benchmark_approach(
            "numpy",
            make_genome_stats_numpy,
            unpack_numpy_passthrough,
            n,
            n_iters
        )

        print(f"{n:>8} {avg1:>12.1f} ± {std1:>6.1f} {avg2:>12.1f} ± {std2:>6.1f} {avg3:>12.1f} ± {std3:>6.1f}")

    print()
    print("Analysis:")
    print("-" * 70)

    # Show speedup for typical case (256 genomes)
    n = 256
    avg_dict, _ = benchmark_approach("current", make_genome_stats_dicts, unpack_current, n, n_iters)
    avg_numpy, _ = benchmark_approach("numpy", make_genome_stats_numpy, unpack_numpy_passthrough, n, n_iters)
    speedup = avg_dict / avg_numpy if avg_numpy > 0 else 0

    print(f"At {n} genomes (typical GA population):")
    print(f"  - Dict loop:       {avg_dict:.1f} µs")
    print(f"  - Numpy passthru:  {avg_numpy:.1f} µs")
    print(f"  - Speedup:         {speedup:.1f}x")
    print()

    # Estimate per-generation overhead
    # GA typically does 1 upload per generation, ~100-500 generations per run
    gens_per_run = 200
    overhead_per_run_ms = (avg_dict - avg_numpy) * gens_per_run / 1000
    print(f"Estimated savings per GA run ({gens_per_run} generations):")
    print(f"  - {overhead_per_run_ms:.1f} ms saved by using numpy passthrough")
    print()

    # Count how many from_numpy calls per generation
    print("Note: This only measures CPU unpacking time.")
    print("The from_numpy() GPU upload itself is not included.")


if __name__ == "__main__":
    main()
