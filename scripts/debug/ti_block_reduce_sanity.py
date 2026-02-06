"""
Sanity-check Taichi Vulkan block-per-owner mapping + shared reductions.

This does NOT use simt.block.thread_idx/global_thread_idx (not supported on Vulkan).
Instead it uses the same (tid -> work_idx,lane) mapping used by our FG block kernels.
"""

from __future__ import annotations

import numpy as np
import taichi as ti
from taichi.lang import simt


def _run(block_dim: int, n_work: int = 256) -> None:
    out_tree = ti.field(dtype=ti.i32, shape=(n_work,))
    out_wave = ti.field(dtype=ti.i32, shape=(n_work,))
    out_nd = ti.field(dtype=ti.i32, shape=(n_work,))
    waves = (int(block_dim) + 31) // 32

    @ti.kernel
    def k_tree():
        shared = simt.block.SharedArray((block_dim,), ti.i32)
        total_threads = n_work * block_dim
        ti.loop_config(block_dim=block_dim)
        for tid in range(total_threads):
            work_idx = tid // block_dim
            lane = tid - (work_idx * block_dim)

            shared[lane] = tid
            simt.block.sync()

            # Tree reduce max across the block.
            stride = block_dim // 2
            while stride > 0:
                if lane < stride:
                    other = shared[lane + stride]
                    if other > shared[lane]:
                        shared[lane] = other
                simt.block.sync()
                stride //= 2

            if lane == 0:
                out_tree[work_idx] = shared[0]

    @ti.kernel
    def k_wave():
        shared = simt.block.SharedArray((waves,), ti.i32)
        total_threads = n_work * block_dim
        ti.loop_config(block_dim=block_dim)
        for tid in range(total_threads):
            work_idx = tid // block_dim
            lane = tid - (work_idx * block_dim)

            if lane < waves:
                shared[lane] = -1
            simt.block.sync()

            best_wave = simt.subgroup.reduce_max(tid)
            if simt.subgroup.elect():
                wave_slot = lane >> 5  # lane//32, valid for wave32 and wave64 (wave64 uses even slots)
                if wave_slot < waves:
                    shared[wave_slot] = best_wave
            simt.block.sync()

            if lane == 0:
                best = shared[0]
                for i in range(1, waves):
                    v = shared[i]
                    if v > best:
                        best = v
                out_wave[work_idx] = best

    @ti.kernel
    def k_ndrange():
        shared = simt.block.SharedArray((block_dim,), ti.i32)
        ti.loop_config(block_dim=block_dim)
        for work_idx, lane in ti.ndrange(n_work, block_dim):
            # Emulate tid = work_idx*block_dim + lane (lane is the fastest-changing index).
            tid = work_idx * block_dim + lane
            shared[lane] = tid
            simt.block.sync()

            # Reduce max in the same way as the tree reduction above.
            stride = block_dim // 2
            while stride > 0:
                if lane < stride:
                    other = shared[lane + stride]
                    if other > shared[lane]:
                        shared[lane] = other
                simt.block.sync()
                stride //= 2

            if lane == 0:
                out_nd[work_idx] = shared[0]

    k_tree()
    k_wave()
    k_ndrange()
    got_tree = out_tree.to_numpy()
    got_wave = out_wave.to_numpy()
    got_nd = out_nd.to_numpy()
    exp = (np.arange(n_work, dtype=np.int32) * np.int32(block_dim)) + np.int32(block_dim - 1)
    ok_tree = np.array_equal(got_tree, exp)
    ok_wave = np.array_equal(got_wave, exp)
    ok_nd = np.array_equal(got_nd, exp)
    print(f"block_dim={block_dim} ok_tree={ok_tree} ok_wave={ok_wave} ok_ndrange={ok_nd}")
    if not ok_tree:
        idx = np.nonzero(got_tree != exp)[0][:8]
        print("  tree mismatches:")
        for i in idx:
            print(f"    work={int(i)} got={int(got_tree[i])} exp={int(exp[i])}")
    if not ok_wave:
        idx = np.nonzero(got_wave != exp)[0][:8]
        print("  wave mismatches:")
        for i in idx:
            print(f"    work={int(i)} got={int(got_wave[i])} exp={int(exp[i])}")
    if not ok_nd:
        idx = np.nonzero(got_nd != exp)[0][:8]
        print("  ndrange mismatches:")
        for i in idx:
            print(f"    work={int(i)} got={int(got_nd[i])} exp={int(exp[i])}")


def main() -> None:
    # Match the repo's runtime defaults as closely as possible.
    ti.init(arch=ti.vulkan, default_fp=ti.f32, default_ip=ti.i32, default_gpu_block_dim=256)
    for d in (32, 64, 128, 256):
        _run(d)


if __name__ == "__main__":
    main()
