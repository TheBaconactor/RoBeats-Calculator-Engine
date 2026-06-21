"""Validate the soft-float surface upper-bound vs the original f64 one (Task A.2).

The UB only gates `ub > best_score` pruning, so it must be a *valid over-estimate*
(>= the true score) or it could prune the optimum. We check, on the Taichi CPU backend
(real f64, no GPU): the soft-float UB is always >= the original f64 UB, and stays within a
couple of points of it (tight enough that pruning stays effective).

    python tools/fg_gpu_port/check_ub.py
"""
import os
import sys

import numpy as np
import taichi as ti

sys.path.insert(0, os.path.dirname(__file__))


def main():
    ti.init(arch=ti.cpu, default_ip=ti.i64)
    import softfloat_taichi as sft
    from gear_optimizer.solver.taichi_gem.force_greats.response_inner_kernels import (
        _fg_response_surface_upper_bound as ref_ub,
    )

    @ti.kernel
    def ub_ref(base: ti.types.ndarray(dtype=ti.f64, ndim=1),
               cm: ti.types.ndarray(dtype=ti.f64, ndim=1),
               fm: ti.types.ndarray(dtype=ti.f64, ndim=1),
               cnt: ti.types.ndarray(dtype=ti.i32, ndim=2),
               out: ti.types.ndarray(dtype=ti.f64, ndim=1)):
        for t in range(base.shape[0]):
            out[t] = ref_ub(base[t], cm[t], fm[t],
                            cnt[t, 0], cnt[t, 1], cnt[t, 2], cnt[t, 3], cnt[t, 4], cnt[t, 5])

    @ti.kernel
    def ub_new(base: ti.types.ndarray(dtype=ti.i64, ndim=1),
               cmb: ti.types.ndarray(dtype=ti.i64, ndim=1),
               fmb: ti.types.ndarray(dtype=ti.i64, ndim=1),
               csb: ti.types.ndarray(dtype=ti.i64, ndim=1),
               cnt: ti.types.ndarray(dtype=ti.i32, ndim=2),
               out: ti.types.ndarray(dtype=ti.i64, ndim=1)):
        for t in range(base.shape[0]):
            out[t] = sft.surface_ub(base[t], sft.sf_decode(cmb[t]), sft.sf_decode(fmb[t]),
                                    sft.sf_decode(csb[t]),
                                    cnt[t, 0], cnt[t, 1], cnt[t, 2], cnt[t, 3], cnt[t, 4], cnt[t, 5])

    n = 200_000
    rng = np.random.default_rng(5)
    base = rng.integers(200, 3000, n).astype(np.float64)
    cm = rng.uniform(2.0, 2.67, n)
    fm = rng.uniform(3.0, 5.425, n)
    cs = (cm - 1.0) / 100.0
    cnt = np.zeros((n, 6), np.int32)
    cnt[:, 0] = rng.integers(0, 900, n)   # body_fever
    cnt[:, 1] = rng.integers(0, 900, n)   # body_normal
    cnt[:, 2] = rng.integers(0, 129, n)   # n_hn
    cnt[:, 3] = rng.integers(0, 129, n)   # n_hf
    cnt[:, 4] = rng.integers(0, 8001, n)  # sigma_hn
    cnt[:, 5] = rng.integers(0, 8001, n)  # sigma_hf
    out_ref = np.zeros(n, np.float64)
    out_new = np.zeros(n, np.int64)
    ub_ref(np.ascontiguousarray(base), np.ascontiguousarray(cm), np.ascontiguousarray(fm), cnt, out_ref)
    ub_new(base.astype(np.int64), cm.view(np.int64).copy(), fm.view(np.int64).copy(),
           cs.view(np.int64).copy(), cnt, out_new)
    ti.sync()
    # Correctness: the soft-float UB must NEVER be below the original f64 UB (which is itself a
    # valid over-estimate of the true score). Tightness (gap size) is perf-only, not correctness.
    under = int(np.sum(out_new.astype(np.float64) < out_ref))      # MUST be 0
    gap = out_new.astype(np.float64) - out_ref
    rel = gap / np.maximum(out_ref, 1.0)
    print(f"over-estimate violations (new < ref): {under}/{n}")
    print(f"gap new-ref: min {gap.min():.1f}  max {gap.max():.1f}  mean {gap.mean():.1f}  "
          f"mean_rel {rel.mean()*100:.2f}%")
    print("VALID (over-estimate holds)" if under == 0 else "PROBLEM: prunes the optimum")


if __name__ == "__main__":
    main()
