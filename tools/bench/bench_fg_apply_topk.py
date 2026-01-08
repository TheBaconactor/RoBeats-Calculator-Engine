"""
Benchmark: CPU-side apply cost for FG results (full vs top-K subset).

This isolates the Python overhead of applying FG results to loadout entries, which is
often the dominant win when reducing downloaded results.

Run:
  python tools/bench/bench_fg_apply_topk.py
"""

from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _run(n: int, *, n_sections: int) -> float:
    from gear_optimizer.helpers.song_helpers.force_greats import result_application

    pending_sigs = [f"sig{i}" for i in range(int(n))]
    pending = []
    sig_map = {}
    for i, sig in enumerate(pending_sigs):
        bs = {
            "Perfect Points": 100 + (i % 7),
            "Combo Multiplier": 100 + (i % 9),
            "Fever Multiplier": 100 + (i % 11),
            "Fever Time": 80 + (i % 5),
            "Fever Fill Rate": 80 + (i % 5),
            "Chill": 200,
            "Flow": 200,
            "Rush": 200,
            "Beat": 200,
            "Vibe": 200,
        }
        pending.append(bs)
        entry = {"score": 123456 + i, "gear": [], "minis": []}
        sig_map[sig] = [(entry, {}, bs)]

    # Synthetic GPU outputs (already-aligned arrays)
    rng = np.random.default_rng(12345)
    result_final = rng.integers(1_000_000, 1_050_000, size=int(n), dtype=np.int32)
    result_base = rng.integers(900_000, 950_000, size=int(n), dtype=np.int32)
    result_cfg_idx = rng.integers(0, 8, size=int(n), dtype=np.int32)
    result_ft = rng.integers(0, 10, size=int(n), dtype=np.int32)
    result_ff = rng.integers(0, 10, size=int(n), dtype=np.int32)
    result_g_pp = rng.integers(0, 30, size=int(n), dtype=np.int32)
    result_g_cm = rng.integers(0, 30, size=int(n), dtype=np.int32)
    result_g_fm = rng.integers(0, 30, size=int(n), dtype=np.int32)
    result_g_ov = rng.integers(0, 30, size=int(n), dtype=np.int32)

    # Provide cfg_counts directly so apply doesn't index into counts_list.
    cfg_counts = rng.integers(0, 3, size=(int(n), int(n_sections)), dtype=np.int32)

    t0 = time.perf_counter()
    _ = result_application.apply_gpu_results_to_entries(
        pending_sigs=pending_sigs,
        pending=pending,
        sig_map=sig_map,
        sel_color="Chill",
        n_sections=int(n_sections),
        max_per_section=15,
        counts_list=None,
        fg_scorer=None,
        result_final=result_final,
        result_base=result_base,
        result_cfg_idx=result_cfg_idx,
        result_cfg_counts=cfg_counts,
        result_ft=result_ft,
        result_ff=result_ff,
        result_g_pp=result_g_pp,
        result_g_cm=result_g_cm,
        result_g_fm=result_g_fm,
        result_g_ov=result_g_ov,
        fg_variants=None,
        build_details_fn=None,
        names_list_fn=lambda items: ["" for _ in (items or [])],
        perf=False,
        materialize_force_details=False,
        materialize_stats=False,
        store_raw=True,
    )
    return float(time.perf_counter() - t0)


def main() -> int:
    os.environ.setdefault("FG_MATERIALIZE_ALL_FORCE_DETAILS", "0")

    n_sections = 3
    n_full = 1024
    n_topk = 256
    iters = 10

    # Warmup
    _ = _run(64, n_sections=n_sections)

    full_times = [_run(n_full, n_sections=n_sections) for _ in range(iters)]
    topk_times = [_run(n_topk, n_sections=n_sections) for _ in range(iters)]

    t_full = min(full_times) if full_times else 0.0
    t_topk = min(topk_times) if topk_times else 0.0
    speedup = (t_full / t_topk) if t_topk > 0 else float("inf")

    print(f"[bench] FG apply (lean/raw) n_sections={n_sections} iters={iters}")
    print(f"[bench] full  n={n_full} min={t_full * 1000:.2f}ms")
    print(f"[bench] topk  n={n_topk} min={t_topk * 1000:.2f}ms")
    print(f"[bench] speedup={speedup:.2f}x (apply-only)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
