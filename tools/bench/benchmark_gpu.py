"""
GPU Benchmark - Measures throughput of Taichi Vulkan genome gem solvers.

This benchmarks the modern GPU solver APIs:
1. solve_genomes_with_ftff: GPU-resident FT/FF iteration
2. solve_genomes_parallel: CPU work-item generation + GPU reduction

The legacy batch gem solver API has been removed.
"""

from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from gear_optimizer.core.color_flags import build_color_flags
from gear_optimizer.core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
    MAX_STAT_INDEX,
    TOTAL_GEM_BUDGET,
    TOTAL_ROWS,
)
from gear_optimizer.solver.scoring_core import optimize_core_jit
from gear_optimizer.solver.taichi_gem_solver import (
    init_taichi_vulkan,
    load_ref_arrays,
    solve_genomes_parallel,
    solve_genomes_with_ftff,
)


def create_ref_arrays() -> dict:
    """Create reference arrays. Shapes must be (161,)."""
    idx = np.arange(161, dtype=np.float32)
    pp = idx * np.float32(2.5)
    cm = np.float32(1.0) + (idx * np.float32(0.005))
    fm = np.float32(1.5) + (idx * np.float32(0.01))

    # Used by GPU timeline precomputation.
    ft = np.float32(1.0) + (idx * np.float32(0.003))
    ff = np.float32(1.0) + (idx * np.float32(0.002))

    return {
        "Perfect Points": pp,
        "Combo Multiplier": cm,
        "Fever Multiplier": fm,
        "Fever Time": ft,
        "Fever Fill Rate": ff,
    }


def create_calc_song(*, total_notes: int = 2000, last_note_time: float = 120.0, long_notes: int = 0) -> dict:
    """Create a lightweight calc_song dict compatible with the GPU solver APIs."""
    total_notes = int(total_notes)
    if total_notes < 2:
        total_notes = 2

    last_note_time = float(last_note_time)
    if last_note_time <= 0:
        last_note_time = 120.0

    timestamps = np.linspace(0.0, last_note_time, num=total_notes, dtype=np.float32)

    return {
        "metadata": {
            "Song Name": "benchmark_song",
            "Long Notes": int(long_notes),
            "Last Note Time": float(last_note_time),
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "HumanHitSimSeed": 0,
            "HumanHitSimApplyTo": "",
            "HumanHitSimDistribution": "",
            "HumanHitSimGreatMode": "",
        },
        "song_data": {"timestamps": timestamps},
    }


def benchmark_cpu(ref_arrays: dict, n_items: int, warmup: int = 5) -> tuple[float, float]:
    """Benchmark CPU Numba JIT performance (single timeline item)."""
    fever_mask_head = np.array([i % 3 == 0 for i in range(100)], dtype=np.bool_)

    for _ in range(int(warmup)):
        optimize_core_jit(
            int(TOTAL_GEM_BUDGET),
            100,
            80,
            60,
            500,
            300,
            1,
            0,
            0,
            1,
            0,
            0,
            1,
            0,
            ref_arrays["Perfect Points"],
            ref_arrays["Combo Multiplier"],
            ref_arrays["Fever Multiplier"],
            fever_mask_head,
            150,
            250,
            GEM_SCALE_NORMAL,
            GEM_SCALE_FEVER,
            GEM_STAT_TO_ELEMENT_SCALE,
            ELEMENTAL_GEM_SCALE,
            TOTAL_ROWS,
            MAX_STAT_INDEX,
        )

    start = time.perf_counter()
    for _ in range(int(n_items)):
        optimize_core_jit(
            int(TOTAL_GEM_BUDGET),
            100,
            80,
            60,
            500,
            300,
            1,
            0,
            0,
            1,
            0,
            0,
            1,
            0,
            ref_arrays["Perfect Points"],
            ref_arrays["Combo Multiplier"],
            ref_arrays["Fever Multiplier"],
            fever_mask_head,
            150,
            250,
            GEM_SCALE_NORMAL,
            GEM_SCALE_FEVER,
            GEM_STAT_TO_ELEMENT_SCALE,
            ELEMENTAL_GEM_SCALE,
            TOTAL_ROWS,
            MAX_STAT_INDEX,
        )
    elapsed = time.perf_counter() - start
    return elapsed, float(n_items) / elapsed if elapsed > 0 else float("inf")


def _make_genome_stats(n_genomes: int) -> np.ndarray:
    """
    Format expected by solve_genomes_*:
      [pp, cm, fm, p_val, s_val, ft, ff] int16
    """
    n = int(n_genomes)
    stats = np.empty((n, 7), dtype=np.int16)
    stats[:, 0] = 100  # base_pp
    stats[:, 1] = 80  # base_cm
    stats[:, 2] = 60  # base_fm
    stats[:, 3] = 500  # base_p_val
    stats[:, 4] = 300  # base_s_val
    stats[:, 5] = 0  # base_ft_stat (0..160)
    stats[:, 6] = 0  # base_ff_stat (0..160)
    return stats


def benchmark_gpu_solve(
    solve_fn,
    ref_arrays: dict,
    calc_song: dict,
    flags: dict[str, int],
    n_genomes: int,
    n_batches: int,
    warmup: int = 3,
) -> tuple[float, float]:
    """Benchmark solve_genomes_* throughput (items = genomes)."""
    n_genomes = int(n_genomes)
    n_batches = int(n_batches)
    genome_stats_np = _make_genome_stats(n_genomes)

    def _call():
        return solve_fn(
            genome_stats_np,
            calc_song,
            int(flags["is_p_ft"]),
            int(flags["is_s_ft"]),
            int(flags["is_p_ff"]),
            int(flags["is_s_ff"]),
            int(flags["is_p_pp"]),
            int(flags["is_s_pp"]),
            int(flags["is_p_cm"]),
            int(flags["is_s_cm"]),
            int(flags["is_p_fm"]),
            int(flags["is_s_fm"]),
            int(flags["is_p_ov"]),
            int(flags["is_s_ov"]),
            ref_arrays,
            total_budget=int(TOTAL_GEM_BUDGET),
            gem_scale_fever=int(GEM_SCALE_FEVER),
            song_slot=0,
        )

    # Warmup (also triggers kernel compilation + timeline precompute).
    for i in range(int(warmup)):
        genome_stats_np[0, 0] = np.int16(100 + i)  # avoid any upload-cache effects
        _call()

    start = time.perf_counter()
    for i in range(n_batches):
        genome_stats_np[0, 0] = np.int16(100 + i)
        _call()
    elapsed = time.perf_counter() - start

    total_items = n_genomes * n_batches
    return elapsed, float(total_items) / elapsed if elapsed > 0 else float("inf")


def main() -> None:
    print("=" * 70)
    print("TAICHI VULKAN GEM SOLVER BENCHMARK (solve_genomes_*) - RX 7900 XTX")
    print("=" * 70)
    print()

    ref_arrays = create_ref_arrays()
    calc_song = create_calc_song()

    print("Initializing Taichi Vulkan...")
    init_taichi_vulkan()
    load_ref_arrays(ref_arrays)
    print()

    p_color = str(calc_song["metadata"].get("Primary Color", ""))
    s_color = str(calc_song["metadata"].get("Secondary Color", ""))
    selected_color = p_color
    flags = build_color_flags(p_color, s_color, selected_color)

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

    print("-" * 70)
    print("GPU BENCHMARKS (Taichi Vulkan)")
    print("-" * 70)

    genome_configs = [
        (1, 400, "Single genome (latency-ish)"),
        (10, 200, "Small batch (10)"),
        (100, 80, "GA-like batch (100)"),
        (250, 40, "Typical GA population (250)"),
        (512, 30, "Large batch (512)"),
        (1024, 20, "Very large batch (1024)"),
        (2048, 10, "Mega batch (2048)"),
        (4096, 6, "Max batch (4096)"),
    ]

    best = {"ftff": (0.0, ""), "parallel": (0.0, "")}

    for n_genomes, n_batches, label in genome_configs:
        for solve_fn, solve_label, best_key in (
            (solve_genomes_with_ftff, "solve_genomes_with_ftff", "ftff"),
            (solve_genomes_parallel, "solve_genomes_parallel", "parallel"),
        ):
            try:
                elapsed, throughput = benchmark_gpu_solve(
                    solve_fn, ref_arrays, calc_song, flags, n_genomes, n_batches
                )
                speedup = throughput / cpu_throughput if cpu_throughput else float("inf")

                if throughput > best[best_key][0]:
                    best[best_key] = (throughput, label)

                print(f"\n  {label} [{solve_label}]:")
                print(f"    Genomes: {int(n_genomes):,} | Batches: {int(n_batches)}")
                print(f"    Time: {elapsed:.3f}s")
                print(f"    Throughput: {throughput:,.0f} genomes/sec")
                print(f"    Speedup vs CPU baseline: {speedup:.1f}x")
            except Exception as e:
                print(f"\n  {label} [{solve_label}]: FAILED - {e}")

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  CPU throughput:      {cpu_throughput:>11,.0f} items/sec")
    ftff_thr, ftff_cfg = best["ftff"]
    par_thr, par_cfg = best["parallel"]
    print(f"  Best FTFF throughput:{ftff_thr:>11,.0f} genomes/sec | {ftff_cfg}")
    print(f"  Best PAR throughput: {par_thr:>11,.0f} genomes/sec | {par_cfg}")
    max_thr = max(float(ftff_thr), float(par_thr))
    if cpu_throughput:
        print(f"  MAX SPEEDUP:         {max_thr / cpu_throughput:>11.1f}x")
    print("=" * 70)


if __name__ == "__main__":
    main()
