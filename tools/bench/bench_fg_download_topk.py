"""
Benchmark: FG global_best full download vs GPU top-K subset download.

Run:
  python tools/bench/bench_fg_download_topk.py
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


def main() -> int:
    # Enable profiler hooks inside FG API
    os.environ.setdefault("GPU_PROFILER", "1")
    os.environ.setdefault("FG_IMPLICIT_CONFIGS", "1")

    from gear_optimizer.solver.gpu_profiler import get_gpu_profiler
    from gear_optimizer.solver.taichi_gem.force_greats.api import (
        fg_download_global_best,
        fg_reset_global_best,
        solve_force_greats_finder_gpu_tasks,
    )

    prof = get_gpu_profiler()
    try:
        prof.enable()
    except Exception:
        pass

    ref_arrays = _make_ref_arrays()
    timestamps = np.linspace(0.0, 120.0, 180, dtype=np.float32)

    # Workload: enough to populate global_best once; benchmark focuses on download.
    rng = np.random.default_rng(1234)
    n_genomes = 1024
    genome_stats_arr = np.zeros((n_genomes, 7), dtype=np.int32)
    genome_stats_arr[:, 0] = rng.integers(80, 130, size=n_genomes, dtype=np.int32)
    genome_stats_arr[:, 1] = rng.integers(80, 130, size=n_genomes, dtype=np.int32)
    genome_stats_arr[:, 2] = rng.integers(80, 130, size=n_genomes, dtype=np.int32)
    genome_stats_arr[:, 3] = rng.integers(150, 240, size=n_genomes, dtype=np.int32)
    genome_stats_arr[:, 4] = rng.integers(100, 160, size=n_genomes, dtype=np.int32)
    genome_stats_arr[:, 5] = rng.integers(60, 100, size=n_genomes, dtype=np.int32)
    genome_stats_arr[:, 6] = rng.integers(60, 100, size=n_genomes, dtype=np.int32)

    n_sections = 3
    counts_list = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (1, 0, 1), (0, 1, 1), (1, 1, 1)]
    ftff_pairs = [(0, 0), (1, 0), (0, 1), (2, 0), (0, 2), (1, 1), (2, 1), (1, 2)]
    task = {"counts_list": counts_list, "ftff_pairs": ftff_pairs, "base_cfg_offset": 0}

    flags = dict(
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

    # Populate global_best once (JIT warmup + data ready)
    fg_reset_global_best(n_genomes)
    solve_force_greats_finder_gpu_tasks(
        genome_stats_arr,
        timestamps,
        None,
        0,
        float(timestamps[-1]),
        fg_tasks=[task],
        n_sections=int(n_sections),
        ref_arrays=ref_arrays,
        return_raw=True,
        accumulate_global=True,
        **flags,
    )

    # Baseline full download to get base_scores for selection inputs
    full0 = fg_download_global_best(n_genomes)
    full_final = np.asarray(full0["final_score"], dtype=np.int32)
    base_scores = (full_final - 1).astype(np.int32, copy=False)

    keep_mask = np.zeros((n_genomes,), dtype=np.int32)
    keep_mask[:51] = 1
    topk = 51

    # Benchmark: repeated downloads (global_best unchanged)
    iters = 10
    full_times = []
    full_bytes = []
    topk_times = []
    topk_bytes = []

    # Snapshot profiler bytes after warmup/first download.
    base_dl0 = int(getattr(prof, "_total_download_bytes", 0) or 0)

    for _ in range(iters):
        b0 = int(getattr(prof, "_total_download_bytes", 0) or 0)
        t0 = time.perf_counter()
        _ = fg_download_global_best(n_genomes)
        dt = time.perf_counter() - t0
        b1 = int(getattr(prof, "_total_download_bytes", 0) or 0)
        full_times.append(float(dt))
        full_bytes.append(int(b1 - b0))

        b0 = int(getattr(prof, "_total_download_bytes", 0) or 0)
        t0 = time.perf_counter()
        sel = fg_download_global_best(n_genomes, topk=int(topk), base_scores=base_scores, keep_mask=keep_mask)
        dt = time.perf_counter() - t0
        b1 = int(getattr(prof, "_total_download_bytes", 0) or 0)
        topk_times.append(float(dt))
        topk_bytes.append(int(b1 - b0))

        # Keep selection size stable across iterations (sanity)
        _ = sel.get("selected_indices")

    base_dl1 = int(getattr(prof, "_total_download_bytes", 0) or 0)
    _ = base_dl1 - base_dl0  # avoid lint complaints

    t_full = min(full_times) if full_times else 0.0
    t_topk = min(topk_times) if topk_times else 0.0
    b_full = max(full_bytes) if full_bytes else 0
    b_topk = max(topk_bytes) if topk_bytes else 0
    speedup = (t_full / t_topk) if t_topk > 0 else float("inf")
    reduction = (b_full / b_topk) if b_topk > 0 else float("inf")

    print(f"[bench] FG global_best download (genomes={n_genomes}, iters={iters})")
    print(f"[bench] full   min={t_full*1000:.2f}ms download_bytes={b_full}")
    print(f"[bench] topk   min={t_topk*1000:.2f}ms download_bytes={b_topk} (keep=51 topk=51)")
    print(f"[bench] speedup={speedup:.2f}x download_reduction={reduction:.2f}x")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

