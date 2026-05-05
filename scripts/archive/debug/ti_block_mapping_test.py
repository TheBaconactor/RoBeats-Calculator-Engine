"""
Debug script: validate Taichi Vulkan mapping for `ti.loop_config(block_dim=...)`.

We want to ensure that, for:

  ti.loop_config(block_dim=D)
  for tid in range(N):
      lane = tid % D
      block = tid // D

the SIMT intrinsics match the above assumptions:
  - simt.block.global_thread_idx() == tid
  - simt.block.thread_idx() == lane

This matters for block-per-owner kernels that derive (work_idx, lane) from the loop index.
"""

from __future__ import annotations

import taichi as ti
from taichi.lang import simt


def _check_dim(block_dim: int, blocks: int = 8) -> None:
    n = int(block_dim) * int(blocks)
    tid_f = ti.field(dtype=ti.i32, shape=(n,))
    lane_f = ti.field(dtype=ti.i32, shape=(n,))
    gid_f = ti.field(dtype=ti.i32, shape=(n,))

    @ti.kernel
    def k():
        ti.loop_config(block_dim=block_dim)
        for tid in range(n):
            tid_f[tid] = tid
            lane_f[tid] = simt.block.thread_idx()
            gid_f[tid] = simt.block.global_thread_idx()

    k()
    tid_np = tid_f.to_numpy()
    lane_np = lane_f.to_numpy()
    gid_np = gid_f.to_numpy()

    bad_gid = (gid_np != tid_np).sum()
    bad_lane = (lane_np != (tid_np % block_dim)).sum()
    print(f"block_dim={block_dim} blocks={blocks} n={n}: bad_gid={bad_gid} bad_lane={bad_lane}")

    if bad_gid or bad_lane:
        # Print a few mismatches to help diagnose swizzle/rounding behavior.
        import numpy as np

        idx = np.nonzero((gid_np != tid_np) | (lane_np != (tid_np % block_dim)))[0][:16]
        for i in idx:
            print(f"  tid={int(tid_np[i])} gid={int(gid_np[i])} lane={int(lane_np[i])} exp_lane={int(tid_np[i] % block_dim)}")


def main() -> None:
    ti.init(arch=ti.vulkan)
    for d in (32, 64, 128, 256):
        _check_dim(d)


if __name__ == "__main__":
    main()

