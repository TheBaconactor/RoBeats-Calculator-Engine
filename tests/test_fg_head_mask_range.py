import os
import sys

import numpy as np
import pytest

# Ensure we can import gear_optimizer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


@pytest.mark.gpu
@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_fg_head_mask_range_matches_naive_loop():
    import taichi as ti

    from gear_optimizer.solver.taichi_gem.force_greats import fields as fg_fields
    from gear_optimizer.solver.taichi_gem.force_greats import kernels as fg_kernels

    fg_fields.ensure_fields_allocated()

    rng = np.random.default_rng(12345)
    n = 256
    starts = rng.integers(0, 129, size=n, dtype=np.int32)
    ends = rng.integers(0, 129, size=n, dtype=np.int32)

    # Normalize so start <= end
    lo = np.minimum(starts, ends)
    hi = np.maximum(starts, ends)

    out_naive = np.zeros((n, 4), dtype=np.uint32)
    out_fast = np.zeros((n, 4), dtype=np.uint32)

    @ti.kernel
    def _compute(
        start_arr: ti.types.ndarray(dtype=ti.i32, ndim=1),
        end_arr: ti.types.ndarray(dtype=ti.i32, ndim=1),
        naive: ti.types.ndarray(dtype=ti.u32, ndim=2),
        fast: ti.types.ndarray(dtype=ti.u32, ndim=2),
    ):
        for idx in range(start_arr.shape[0]):
            start = start_arr[idx]
            end = end_arr[idx]

            m0 = ti.u32(0)
            m1 = ti.u32(0)
            m2 = ti.u32(0)
            m3 = ti.u32(0)
            for i in range(128):
                if start <= i < end:
                    word = i >> 5
                    bit = ti.u32(1) << ti.cast(i & 31, ti.u32)
                    if word == 0:
                        m0 |= bit
                    elif word == 1:
                        m1 |= bit
                    elif word == 2:
                        m2 |= bit
                    else:
                        m3 |= bit

            naive[idx, 0] = m0
            naive[idx, 1] = m1
            naive[idx, 2] = m2
            naive[idx, 3] = m3

            masks = fg_kernels._or_head_mask_range(ti.u32(0), ti.u32(0), ti.u32(0), ti.u32(0), start, end)
            fast[idx, 0] = masks[0]
            fast[idx, 1] = masks[1]
            fast[idx, 2] = masks[2]
            fast[idx, 3] = masks[3]

    _compute(lo, hi, out_naive, out_fast)
    ti.sync()

    assert np.array_equal(out_naive, out_fast)
