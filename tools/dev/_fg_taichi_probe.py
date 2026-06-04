"""Throwaway probe: confirm the Option-A per-lane-scratch pattern runs on Vulkan.

Run: python tools/dev/_fg_taichi_probe.py   (delete after)
"""
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from gear_optimizer.solver.taichi_gem.runtime import init_taichi  # noqa: E402

init_taichi()
import taichi as ti  # noqa: E402

print("Taichi init OK")


@ti.kernel
def lane_scratch(
    n_lanes: ti.i32,
    width: ti.i32,
    scratch: ti.types.ndarray(dtype=ti.i32, ndim=2),
    masks: ti.types.ndarray(dtype=ti.u64, ndim=2),
    out: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    for lane in range(n_lanes):  # top-level range-for == GPU parallel domain
        acc = 0
        m = ti.u64(0)
        for j in range(width):  # per-lane SERIAL inner loop, dynamic indexing
            scratch[lane, j] = lane + j
            acc += scratch[lane, j]
            m = m | (ti.u64(1) << ti.u64(j & 63))  # uint64 bit ops (surface masks)
        masks[lane, 0] = m
        # subset test pattern (x & ~y) == 0 used by the dominance reduction
        if (m & ~m) == ti.u64(0):
            out[lane] = acc


def main():
    N, W = 200000, 64
    scratch = np.zeros((N, W), dtype=np.int32)
    masks = np.zeros((N, 1), dtype=np.uint64)
    out = np.zeros(N, dtype=np.int32)
    lane_scratch(N, W, scratch, masks, out)
    ti.sync()
    t = time.perf_counter()
    for _ in range(5):
        lane_scratch(N, W, scratch, masks, out)
        ti.sync()
    dt = (time.perf_counter() - t) / 5
    expect = W * (N - 1) + sum(range(W))
    print(
        "ran lanes=%d width=%d avg=%.5fs out[-1]=%d expect=%d match=%s mask[-1]=%d"
        % (N, W, dt, int(out[-1]), expect, int(out[-1]) == expect, int(masks[-1, 0]))
    )


if __name__ == "__main__":
    main()
