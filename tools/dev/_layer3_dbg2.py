"""Reproduce the probe's first chunk to isolate the batch-only mismatch."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np  # noqa: E402

from gear_optimizer.solver.taichi_gem.runtime import init_taichi  # noqa: E402
init_taichi()
import taichi as ti  # noqa: E402

from tests.parity.force_greats.fg_frontier_kernel_parity import (  # noqa: E402
    build_kernel_args, numba_first_frontier,
)
import tools.dev._layer3_kernel_probe as L3  # noqa: E402


def make_song(rng, n, great_later=True):
    gaps = rng.uniform(0.02, 0.2, size=n).astype(np.float32)
    ts = np.cumsum(gaps).astype(np.float32)
    bump = rng.uniform(0.0, 0.12, size=n).astype(np.float32)
    great_ts = (ts + bump).astype(np.float32) if great_later else ts.copy()
    return ts, great_ts


def main():
    rng = np.random.default_rng(20260602)
    n = 40
    ts, great_ts = make_song(rng, n, True)

    raw_fills = [20, 40, 60, 75, 88, 96, 100, 108, 120, 140]
    bases = [4, 6, 8, 10, 12]
    real_times = [1.0, 1.4, 1.8, 2.2, 2.5]
    geom_args = []
    geom_meta = []
    for raw in raw_fills:
        for base_v in bases:
            for rt in real_times:
                geom_args.append(build_kernel_args(
                    timestamps=ts, great_candidate_timestamps=great_ts,
                    raw_fever_fill=float(raw), non_fever_base=int(base_v),
                    real_fever_time=float(rt), use_forced_great_timing=True,
                ))
                geom_meta.append((raw, base_v, rt))

    # The target geometry (20,4,1.4) is index 1.
    target = (20, 4, 1.4)
    ti_idx = geom_meta.index(target)
    print("target index in sweep:", ti_idx)

    CHUNK = 96
    chunk = geom_args[0:CHUNK]
    res = L3._run_batch(chunk, cap_bt=64, cap_head=256, cap_red3=64, cap_ff=512)
    g_out, g_counts, g_err = res[ti_idx]
    o_out, o_se, o_gs, o_rt, o_msf = numba_first_frontier(geom_args[ti_idx])
    print("batched GPU counts", g_counts, "err", g_err)
    print("oracle      counts", [int(o_se), int(o_gs), int(o_rt), int(o_msf)])

    # Now run target ALONE.
    res1 = L3._run_batch([geom_args[ti_idx]], cap_bt=64, cap_head=256, cap_red3=64, cap_ff=512)
    print("alone   GPU counts", res1[0][1], "err", res1[0][2])

    # Binary-search the batch size at which it breaks.
    for sz in (1, 2, 3, 5, 8, 16, 32, 64, 96):
        if ti_idx >= sz:
            continue
        r = L3._run_batch(geom_args[0:sz], cap_bt=64, cap_head=256, cap_red3=64, cap_ff=512)
        print(f"batchsize={sz}: target counts={r[ti_idx][1]} err={r[ti_idx][2]}")


if __name__ == "__main__":
    main()
