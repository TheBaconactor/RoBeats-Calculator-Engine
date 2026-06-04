"""PROBE: the two atomics the parallel-skyline scatter-max needs, on Vulkan.

  P1  ti.atomic_max(global_ndarray[idx], v) RETURNS THE OLD VALUE -> lets a
      thread detect "I am the first to push this pair this epoch" (old < stamp)
      so EXACTLY ONE thread appends the distinct pair_idx to the touched list.
      This is the race-free analogue of the oracle's pair_stamp claim.
  P2  block-shared ti.atomic_add(sh[cursor], 1) returns old -> touched-list slot.
  P3  COMBINED: many threads scatter (pair_idx, fever) over a contended set of
      pair indices; verify (a) best_fever_by_pair == max per pair, (b) touched
      list = the DISTINCT set of pairs, each appearing EXACTLY ONCE.

Run: python tools/dev/_fg_scatter_probe.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from gear_optimizer.solver.taichi_gem.runtime import init_taichi  # noqa: E402

init_taichi()
import taichi as ti  # noqa: E402

BD = 64


@ti.kernel
def p1_atomic_max_old(n_keys: ti.i32, m: ti.i32,
                      vals: ti.types.ndarray(dtype=ti.i32, ndim=2),
                      slot: ti.types.ndarray(dtype=ti.i32, ndim=2),
                      stamps: ti.types.ndarray(dtype=ti.i32, ndim=2),
                      touched: ti.types.ndarray(dtype=ti.i32, ndim=2),
                      tcount: ti.types.ndarray(dtype=ti.i32, ndim=1),
                      stamp: ti.i32):
    ti.loop_config(block_dim=BD)
    for gid in range(n_keys * BD):
        lane = gid // BD
        t = ti.simt.block.thread_idx()
        sh = ti.simt.block.SharedArray((1,), ti.i32)
        if t == 0:
            sh[0] = 0
        ti.simt.block.sync()
        # each thread scatters its assigned (pair_idx in [0,m)) -> value t (strided)
        j = t
        while j < m:
            pair = slot[lane, j]
            v = vals[lane, j]
            # scatter-MAX into best_fever_by_pair (global, contended)
            ti.atomic_max(vals[lane, m + pair], v)  # store maxed value at offset m+pair
            # claim the pair via stamp atomic_max returning OLD
            old = ti.atomic_max(stamps[lane, pair], stamp)
            if old < stamp:
                s = ti.atomic_add(sh[0], 1)
                touched[lane, s] = pair
            j += BD
        ti.simt.block.sync()
        if t == 0:
            tcount[lane] = sh[0]


def test():
    n_keys = 8
    m = 4000          # candidates per lane
    P = 50            # distinct pair indices (heavy contention: m/P ~ 80 per pair)
    rng = np.random.default_rng(7)
    slot = rng.integers(0, P, size=(n_keys, m)).astype(np.int32)
    vals = np.zeros((n_keys, m + P), dtype=np.int32)
    vals[:, :m] = rng.integers(-1000, 1000, size=(n_keys, m)).astype(np.int32)
    stamps = np.zeros((n_keys, P), dtype=np.int32)  # epoch 0 -> use stamp>=1
    touched = np.full((n_keys, P + 8), -1, dtype=np.int32)
    tcount = np.zeros(n_keys, dtype=np.int32)
    STAMP = 1
    # seed the scatter-max targets to INT_MIN so atomic_max is a clean max
    vals[:, m:] = np.iinfo(np.int32).min
    p1_atomic_max_old(n_keys, m, np.ascontiguousarray(vals), np.ascontiguousarray(slot),
                      np.ascontiguousarray(stamps), touched, tcount, STAMP)
    ti.sync()

    ok_all = True
    for k in range(n_keys):
        # reference: max value per pair + distinct pair set
        ref_max = {}
        for j in range(m):
            p = int(slot[k, j]); v = int(vals[k, j])
            ref_max[p] = max(ref_max.get(p, np.iinfo(np.int32).min), v)
        got_max = {p: int(vals[k, m + p]) for p in ref_max}
        max_ok = all(got_max[p] == ref_max[p] for p in ref_max)
        tc = int(tcount[k])
        tlist = sorted(int(touched[k, i]) for i in range(tc))
        # exactly-once + correct distinct set
        once_ok = (len(tlist) == len(set(tlist)) and set(tlist) == set(ref_max.keys()))
        if not (max_ok and once_ok):
            ok_all = False
            print(f"  key{k}: max_ok={max_ok} once_ok={once_ok} tcount={tc} "
                  f"n_distinct_ref={len(ref_max)} dup={tc - len(set(tlist))}")
    print(f"P1+P2+P3 scatter-max + exactly-once touched-append on Vulkan: {ok_all}")
    return ok_all


if __name__ == "__main__":
    ok = test()
    print("SCATTER PRIMITIVES USABLE:", ok)
    sys.exit(0 if ok else 1)
