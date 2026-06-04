"""FEASIBILITY PROBE: can Taichi 1.7.4 on Vulkan express BLOCK-PER-KEY collaboration?

Mission gate #1: determine the concrete mechanism (or the blocker) for one GPU
workgroup handling ONE (ft,ff) key, with the block's threads collaborating via
block-local shared memory + barriers on the per-state O(L*rho^2) skyline work.

Tests, smallest first (TDR-safe, tiny launches):
  T1  ti.simt.block.thread_idx() + a 1D grid of n_keys*BD  -> per-block lane id
  T2  ti.simt.block.SharedArray   -> block-local scratch, write/sync/read
  T3  ti.simt.block.sync()        -> barrier correctness (producer/consumer)
  T4  block-collaborative reduction: BD threads cooperatively max-reduce an
      array in shared memory (tree reduction w/ barriers) -> vs CPU reference
  T5  subgroup reduce_max (Vulkan subgroup op) -> does it compile/run?

Run: python tools/dev/_fg_block_feasibility.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from gear_optimizer.solver.taichi_gem.runtime import init_taichi  # noqa: E402

init_taichi()
import taichi as ti  # noqa: E402

BD = 64  # block_dim (threads per key/workgroup)


def _hr(t):
    print("\n" + "=" * 72)
    print(t)
    print("=" * 72)


# --------------------------------------------------------------------------- #
# T1: per-block thread id via a flat grid of n_keys*BD threads.
# Taichi auto-parallelizes the outer range-for; loop_config(block_dim=BD) sets
# the workgroup size. block.thread_idx() = invocation id within the workgroup;
# the key index = global_id // BD.
# --------------------------------------------------------------------------- #
@ti.kernel
def t1_thread_idx(n_keys: ti.i32, out_lane: ti.types.ndarray(dtype=ti.i32, ndim=1),
                  out_key: ti.types.ndarray(dtype=ti.i32, ndim=1)):
    ti.loop_config(block_dim=BD)
    for gid in range(n_keys * BD):
        lane = ti.simt.block.thread_idx()
        out_lane[gid] = lane
        out_key[gid] = gid // BD


def test_t1():
    _hr("T1: block.thread_idx() + flat n_keys*BD grid")
    n_keys = 5
    out_lane = np.full(n_keys * BD, -7, dtype=np.int32)
    out_key = np.full(n_keys * BD, -7, dtype=np.int32)
    t1_thread_idx(n_keys, out_lane, out_key)
    ti.sync()
    # Expect: out_lane[gid] == gid % BD  (invocation id within block),
    #         out_key[gid] == gid // BD.
    exp_lane = np.arange(n_keys * BD) % BD
    exp_key = np.arange(n_keys * BD) // BD
    ok_lane = np.array_equal(out_lane, exp_lane)
    ok_key = np.array_equal(out_key, exp_key)
    print(f"  block.thread_idx == gid%BD : {ok_lane}")
    print(f"  key index == gid//BD       : {ok_key}")
    if not ok_lane:
        # show where it diverges (this is the load-bearing finding)
        bad = np.nonzero(out_lane != exp_lane)[0][:8]
        print(f"  FIRST DIVERGENCES idx={bad.tolist()}")
        print(f"    got ={out_lane[bad].tolist()}")
        print(f"    want={exp_lane[bad].tolist()}")
        print(f"  distinct lane values seen: {sorted(set(out_lane.tolist()))[:20]}")
    return ok_lane and ok_key


# --------------------------------------------------------------------------- #
# T2 + T3: SharedArray write/sync/read with a barrier between producer & consumer.
# Each block: thread t writes t*t into shared[t]; barrier; thread t reads
# shared[BD-1-t] (cross-thread read => REQUIRES the barrier + real shared mem).
# --------------------------------------------------------------------------- #
@ti.kernel
def t2_shared(n_keys: ti.i32, out: ti.types.ndarray(dtype=ti.i32, ndim=1)):
    ti.loop_config(block_dim=BD)
    for gid in range(n_keys * BD):
        smem = ti.simt.block.SharedArray((BD,), ti.i32)
        t = ti.simt.block.thread_idx()
        smem[t] = t * t
        ti.simt.block.sync()
        out[gid] = smem[BD - 1 - t]  # read a DIFFERENT thread's slot


def test_t2():
    _hr("T2+T3: SharedArray write -> block.sync() -> cross-thread read")
    n_keys = 4
    out = np.full(n_keys * BD, -7, dtype=np.int32)
    t2_shared(n_keys, out)
    ti.sync()
    # out[gid] should == (BD-1-(gid%BD))^2 if shared mem + barrier work.
    t = np.arange(n_keys * BD) % BD
    exp = (BD - 1 - t) ** 2
    ok = np.array_equal(out, exp)
    print(f"  cross-thread shared read after barrier correct: {ok}")
    if not ok:
        bad = np.nonzero(out != exp)[0][:8]
        print(f"  FIRST DIVERGENCES idx={bad.tolist()} got={out[bad].tolist()} want={exp[bad].tolist()}")
    return ok


# --------------------------------------------------------------------------- #
# T4: block-collaborative TREE reduction (the actual pattern we need for the
# per-state O(L*rho^2) skyline-union/sort work). BD threads load N values into
# shared mem, then cooperatively max-reduce with log(BD) barrier steps.
# One block per key; each key has its own random array -> compare vs numpy max.
# --------------------------------------------------------------------------- #
@ti.kernel
def t4_block_reduce(n_keys: ti.i32, m: ti.i32,
                    data: ti.types.ndarray(dtype=ti.i32, ndim=2),
                    out_max: ti.types.ndarray(dtype=ti.i32, ndim=1)):
    ti.loop_config(block_dim=BD)
    for gid in range(n_keys * BD):
        key = gid // BD
        t = ti.simt.block.thread_idx()
        red = ti.simt.block.SharedArray((BD,), ti.i32)
        # cooperative grid-stride load+max of the key's m values into BD slots
        local = ti.i32(-2147483648)
        j = t
        while j < m:
            v = data[key, j]
            if v > local:
                local = v
            j += BD
        red[t] = local
        ti.simt.block.sync()
        # tree reduction in shared memory
        stride = BD // 2
        while stride > 0:
            if t < stride:
                if red[t + stride] > red[t]:
                    red[t] = red[t + stride]
            ti.simt.block.sync()
            stride //= 2
        if t == 0:
            out_max[key] = red[0]


def test_t4():
    _hr("T4: block-collaborative tree max-reduction (1 block per key)")
    n_keys = 6
    m = 5000  # per-key array length (> BD so the grid-stride load matters)
    rng = np.random.default_rng(1234)
    data = rng.integers(-(10**6), 10**6, size=(n_keys, m)).astype(np.int32)
    out_max = np.full(n_keys, -7, dtype=np.int32)
    t4_block_reduce(n_keys, m, np.ascontiguousarray(data), out_max)
    ti.sync()
    ref = data.max(axis=1)
    ok = np.array_equal(out_max, ref)
    print(f"  block tree-reduce max == numpy max (per key): {ok}")
    if not ok:
        print(f"  got={out_max.tolist()}")
        print(f"  ref={ref.tolist()}")
    return ok


# --------------------------------------------------------------------------- #
# T5: Vulkan SUBGROUP reduce_max (subgroup = warp/wavefront-level op).
# This is the cheaper alternative to SharedArray+barriers for in-warp reductions.
# May NOT be supported on Vulkan in 1.7.4 -- this test reports the concrete result.
# --------------------------------------------------------------------------- #
@ti.kernel
def t5_subgroup(n_keys: ti.i32, data: ti.types.ndarray(dtype=ti.i32, ndim=1),
                out: ti.types.ndarray(dtype=ti.i32, ndim=1)):
    ti.loop_config(block_dim=BD)
    for gid in range(n_keys * BD):
        v = data[gid]
        r = ti.simt.subgroup.reduce_max(v)
        out[gid] = r


def test_t5():
    _hr("T5: ti.simt.subgroup.reduce_max on Vulkan (subgroup/wavefront op)")
    n_keys = 2
    total = n_keys * BD
    data = np.arange(total, dtype=np.int32)
    out = np.full(total, -7, dtype=np.int32)
    try:
        t5_subgroup(n_keys, data, out)
        ti.sync()
    except Exception as exc:
        print(f"  SUBGROUP COMPILE/RUN FAILED: {type(exc).__name__}: {str(exc)[:300]}")
        return None
    # subgroup size on AMD = 64 (wavefront). If subgroup==block==64, each block's
    # reduce_max == max over that block's 64 values. Report what we actually got.
    print(f"  ran OK. out[:4]={out[:4].tolist()} out[60:68]={out[60:68].tolist()}")
    # check if it looks like a per-64 block max
    blk_max = data.reshape(-1, BD).max(axis=1)
    looks_blockmax = all(out[k * BD] == blk_max[k] for k in range(n_keys))
    print(f"  out[block_start]==per-{BD}-block-max: {looks_blockmax} (blk_max={blk_max.tolist()})")
    print(f"  distinct out values: {sorted(set(out.tolist()))[:12]}")
    return True


def main():
    results = {}
    results["T1 thread_idx"] = test_t1()
    results["T2/T3 SharedArray+sync"] = test_t2()
    results["T4 block tree-reduce"] = test_t4()
    r5 = test_t5()
    results["T5 subgroup reduce_max"] = ("ran" if r5 else ("SKIP/FAIL" if r5 is None else r5))

    _hr("FEASIBILITY SUMMARY")
    for k, v in results.items():
        print(f"  {k:32s}: {v}")
    core_ok = results["T1 thread_idx"] and results["T2/T3 SharedArray+sync"] and results["T4 block tree-reduce"]
    print(f"\n  BLOCK-PER-KEY CORE MECHANISM USABLE ON VULKAN: {core_ok}")
    return 0 if core_ok else 1


if __name__ == "__main__":
    sys.exit(main())
