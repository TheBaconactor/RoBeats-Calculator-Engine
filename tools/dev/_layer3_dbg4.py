"""Diagnose the error_flag overflow on n=130 raw=20 geometries."""
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


def make_song(rng, n):
    gaps = rng.uniform(0.02, 0.2, size=n).astype(np.float32)
    ts = np.cumsum(gaps).astype(np.float32)
    bump = rng.uniform(0.0, 0.12, size=n).astype(np.float32)
    return ts, (ts + bump).astype(np.float32)


def main():
    # Rebuild song n=130 with the SAME rng draw order the probe used so the
    # song bytes match (songs are generated in order 40,90,130,...).
    rng = np.random.default_rng(20260602)
    for n in (40, 90, 130):
        ts, great_ts = make_song(rng, n)
    # now ts/great_ts == the probe's n=130 song

    a = build_kernel_args(timestamps=ts, great_candidate_timestamps=great_ts,
                          raw_fever_fill=20.0, non_fever_base=8, real_fever_time=1.0,
                          use_forced_great_timing=True)
    print("n", a["n"], "ac", a["action_count"], "first_fill[:5]", a["first_fill"][:5].tolist(),
          "later_fill[:5]", a["later_fill"][:5].tolist())
    lf0 = int(a["later_fill"][0])
    pm = L3._pair_mod_for(int(a["n"]), int(a["action_count"]), lf0)
    print("pair_mod", pm, "pair_size", (a["n"] + 1) * pm)

    o = numba_first_frontier(a)
    o_out = np.asarray(o[0], dtype=np.uint64).reshape(-1, 7)
    o_counts = [int(o[1]), int(o[2]), int(o[3]), int(o[4])]
    print("oracle counts", o_counts, "rows", o_out.shape[0])

    for caps in [(64, 256, 64, 512), (256, 1024, 256, 2048)]:
        cb, ch, cr, cf = caps
        res = L3._run_batch([a], [1.0], cap_bt=cb, cap_head=ch, cap_red3=cr, cap_ff=cf)
        g_out, g_counts, g_err = res[0]
        g_out = np.asarray(g_out, dtype=np.uint64).reshape(-1, 7)
        match = (g_out.shape == o_out.shape) and bool(np.array_equal(g_out, o_out)) and (g_counts == o_counts)
        print(f"caps(bt={cb},head={ch},red3={cr},ff={cf}): err={g_err} counts={g_counts} rows={g_out.shape[0]} MATCH={match}")


if __name__ == "__main__":
    main()
