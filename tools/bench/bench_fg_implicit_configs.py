"""
Benchmark: FG Stage-1 implicit FP-target decode vs cfg-table read/write.

Compares counts_max_fp task execution with:
- FG_IMPLICIT_CONFIGS=0: generate configs into fg_forced_counts + Stage-1 reads table
- FG_IMPLICIT_CONFIGS=1: Stage-1 decodes FP targets implicitly (no cfg table writes/reads)

Run:
  python tools/bench/bench_fg_implicit_configs.py
"""

from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _make_ref_arrays() -> dict:
    from gear_optimizer.core.constants import TOTAL_ROWS

    rows = int(TOTAL_ROWS) + 1
    return {
        "Perfect Points": np.linspace(1.0, 2.0, rows, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=np.float32),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=np.float32),
        "Fever Time": np.linspace(1.0, 2.5, rows, dtype=np.float32),
    }


def _run_once(
    *, implicit: bool, task: dict, genome_stats_arr: np.ndarray, timestamps: np.ndarray, ref_arrays: dict
) -> float:
    import taichi as ti
    from gear_optimizer.solver.taichi_gem.force_greats.api import (
        fg_reset_global_best,
        solve_force_greats_finder_gpu_tasks,
    )

    os.environ["FG_IMPLICIT_CONFIGS"] = "1" if implicit else "0"

    n_genomes = int(genome_stats_arr.shape[0])
    fg_reset_global_best(n_genomes)

    t0 = time.perf_counter()
    solve_force_greats_finder_gpu_tasks(
        genome_stats_arr,
        timestamps,
        None,
        0,  # long_notes
        float(timestamps[-1]),
        fg_tasks=[task],
        n_sections=int(task["n_sections"]),
        ref_arrays=ref_arrays,
        return_raw=True,
        accumulate_global=True,
        is_p_ft=0,
        is_s_ft=0,
        is_p_ff=0,
        is_s_ff=0,
        is_p_pp=0,
        is_s_pp=0,
        is_p_cm=0,
        is_s_cm=0,
        is_p_fm=0,
        is_s_fm=0,
        is_p_ov=1,
        is_s_ov=0,
    )
    ti.sync()
    return float(time.perf_counter() - t0)


def main() -> int:
    # Warmup env (avoid mixing user env)
    os.environ.setdefault("FG_IMPLICIT_CONFIGS", "1")

    ref_arrays = _make_ref_arrays()

    # Synthetic song
    timestamps = np.linspace(0.0, 120.0, 180, dtype=np.float32)

    # Workloads: keep cfg_len=4096 but vary n_sections to hit both kernels.
    cases = [
        {"n_sections": 3, "max_fp": [15, 15, 15], "name": "small3(16^3=4096)"},
        {"n_sections": 4, "max_fp": [7, 7, 7, 7], "name": "general(8^4=4096)"},
    ]
    ftff_pairs = [
        (0, 0),
        (1, 0),
        (0, 1),
        (2, 0),
        (0, 2),
        (1, 1),
        (2, 1),
        (1, 2),
        (3, 0),
        (0, 3),
        (2, 2),
        (3, 1),
        (1, 3),
        (4, 0),
        (0, 4),
        (3, 2),
    ]

    rng = np.random.default_rng(12345)
    n_genomes = 128
    # [pp, cm, fm, p_val, s_val, ft_stat, ff_stat]
    genome_stats_arr = np.zeros((n_genomes, 7), dtype=np.int32)
    genome_stats_arr[:, 0] = rng.integers(80, 130, size=n_genomes, dtype=np.int32)
    genome_stats_arr[:, 1] = rng.integers(80, 130, size=n_genomes, dtype=np.int32)
    genome_stats_arr[:, 2] = rng.integers(80, 130, size=n_genomes, dtype=np.int32)
    genome_stats_arr[:, 3] = rng.integers(150, 240, size=n_genomes, dtype=np.int32)
    genome_stats_arr[:, 4] = rng.integers(100, 160, size=n_genomes, dtype=np.int32)
    genome_stats_arr[:, 5] = rng.integers(60, 100, size=n_genomes, dtype=np.int32)
    genome_stats_arr[:, 6] = rng.integers(60, 100, size=n_genomes, dtype=np.int32)

    iters = 5
    for case in cases:
        task = {
            "n_sections": int(case["n_sections"]),
            "counts_max_fp": list(case["max_fp"]),
            "ftff_pairs": list(ftff_pairs),
            "base_cfg_offset": 0,
        }

        # Warmup (JIT) per shape
        _ = _run_once(
            implicit=True, task=task, genome_stats_arr=genome_stats_arr, timestamps=timestamps, ref_arrays=ref_arrays
        )

        times_explicit = []
        times_implicit = []
        for _i in range(iters):
            times_explicit.append(
                _run_once(
                    implicit=False,
                    task=task,
                    genome_stats_arr=genome_stats_arr,
                    timestamps=timestamps,
                    ref_arrays=ref_arrays,
                )
            )
            times_implicit.append(
                _run_once(
                    implicit=True,
                    task=task,
                    genome_stats_arr=genome_stats_arr,
                    timestamps=timestamps,
                    ref_arrays=ref_arrays,
                )
            )

        t0 = min(times_explicit) if times_explicit else 0.0
        t1 = min(times_implicit) if times_implicit else 0.0
        speedup = (t0 / t1) if t1 > 0 else float("inf")

        print(
            "[bench] {} counts_max_fp (n_sections={}, cfg_len=4096, genomes={}, ftff={})".format(
                case["name"], case["n_sections"], n_genomes, len(ftff_pairs)
            )
        )
        print(f"[bench] explicit(table)  min={t0 * 1000:.1f}ms samples={[round(x * 1000, 1) for x in times_explicit]}")
        print(f"[bench] implicit(decode) min={t1 * 1000:.1f}ms samples={[round(x * 1000, 1) for x in times_implicit]}")
        print(f"[bench] speedup={speedup:.2f}x (min)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
