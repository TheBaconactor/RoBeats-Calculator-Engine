"""Targeted single-geometry debug for the Layer 3 kernel parity probe."""
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
    if great_later:
        bump = rng.uniform(0.0, 0.12, size=n).astype(np.float32)
        great_ts = (ts + bump).astype(np.float32)
    else:
        great_ts = ts.copy()
    return ts, great_ts


def main():
    rng = np.random.default_rng(20260602)
    n = 40
    ts, great_ts = make_song(rng, n, True)
    a = build_kernel_args(
        timestamps=ts, great_candidate_timestamps=great_ts,
        raw_fever_fill=20.0, non_fever_base=4, real_fever_time=1.4,
        use_forced_great_timing=True,
    )
    print("n", a["n"], "action_count", a["action_count"])
    print("first_fill", a["first_fill"].tolist())
    print("later_fill", a["later_fill"].tolist())
    print("first_forced", a["first_forced"].tolist())
    print("later_forced", a["later_forced"].tolist())
    print("first_activation_forced", a["first_activation_forced"].tolist())
    print("later_activation_forced", a["later_activation_forced"].tolist())
    print("real_time_idx", a["real_time_idx"], "use_fgt", a["use_forced_great_timing_i"])
    print("timestamp_end_idx[rt]", a["timestamp_end_idx"][a["real_time_idx"]].tolist())
    print("great_end_idx[rt]", a["great_end_idx"][a["real_time_idx"]].tolist())

    o_out, o_se, o_gs, o_rt, o_msf = numba_first_frontier(a)
    print("ORACLE counts", [int(o_se), int(o_gs), int(o_rt), int(o_msf)])
    print("ORACLE out:")
    for row in np.asarray(o_out, dtype=np.uint64):
        print("  ", [int(x) for x in row], "fever_lo_hex", hex(int(row[0])), "great_lo_hex", hex(int(row[2])))

    res = L3._run_batch([a], cap_bt=64, cap_head=256, cap_red3=64, cap_ff=512)
    g_out, g_counts, g_err = res[0]
    print("GPU counts", g_counts, "err", g_err)
    print("GPU out:")
    for row in np.asarray(g_out, dtype=np.uint64):
        print("  ", [int(x) for x in row], "fever_lo_hex", hex(int(row[0])), "great_lo_hex", hex(int(row[2])))


if __name__ == "__main__":
    main()
