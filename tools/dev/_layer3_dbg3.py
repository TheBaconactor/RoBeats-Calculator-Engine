"""Pin down whether the batch mismatch is lane-index or neighbor-data dependent."""
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
    rng = np.random.default_rng(20260602)
    n = 40
    ts, great_ts = make_song(rng, n)

    A0 = build_kernel_args(timestamps=ts, great_candidate_timestamps=great_ts,
                           raw_fever_fill=20.0, non_fever_base=4, real_fever_time=1.0,
                           use_forced_great_timing=True)  # lane0 in failing batch
    A1 = build_kernel_args(timestamps=ts, great_candidate_timestamps=great_ts,
                           raw_fever_fill=20.0, non_fever_base=4, real_fever_time=1.4,
                           use_forced_great_timing=True)  # the target

    def oc(a):
        o = numba_first_frontier(a)
        return [int(o[1]), int(o[2]), int(o[3]), int(o[4])]

    print("oracle A0", oc(A0), " A1", oc(A1))

    # target as lane 1 (failing layout)
    r = L3._run_batch([A0, A1], cap_bt=64, cap_head=256, cap_red3=64, cap_ff=512)
    print("[A0,A1] lane0", r[0][1], "lane1", r[1][1])

    # target as lane 0 (reordered)
    r = L3._run_batch([A1, A0], cap_bt=64, cap_head=256, cap_red3=64, cap_ff=512)
    print("[A1,A0] lane0", r[0][1], "lane1", r[1][1])

    # two copies of the SAME target -> both lanes identical input
    r = L3._run_batch([A1, A1], cap_bt=64, cap_head=256, cap_red3=64, cap_ff=512)
    print("[A1,A1] lane0", r[0][1], "lane1", r[1][1])

    # target + a DIFFERENT-n neighbor would change shared tables; keep same song.
    # target with a ge100 neighbor
    A2 = build_kernel_args(timestamps=ts, great_candidate_timestamps=great_ts,
                           raw_fever_fill=120.0, non_fever_base=4, real_fever_time=1.0,
                           use_forced_great_timing=True)
    print("oracle A2(ge100)", oc(A2))
    r = L3._run_batch([A2, A1], cap_bt=64, cap_head=256, cap_red3=64, cap_ff=512)
    print("[A2,A1] lane0", r[0][1], "lane1", r[1][1])


if __name__ == "__main__":
    main()
