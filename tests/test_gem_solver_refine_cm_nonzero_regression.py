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


pytestmark = pytest.mark.gpu


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gem_solver_refines_when_cm_nonzero_regression() -> None:
    """
    Regression guard: the refined gem allocator must still refine even when CM != 0.

    This test uses synthetic reference tables with step/plateau behavior:
    - CM multiplier plateaus at CM gems >= 12
    - FM multiplier plateaus at FM gems >= 2

    Given a suboptimal hint (CM=12, FM=3, OV=70) under a fixed budget (85),
    the refined allocator should reduce FM by 1 and reallocate that gem to OV.
    """
    import taichi as ti

    from gear_optimizer.solver.taichi_gem import fields
    from gear_optimizer.solver.taichi_gem.kernels import kernels_scoring

    fields.ensure_fields_allocated()

    # Synthetic reference tables (161 entries, 0..160).
    # Keep PP constant so PP gems are never attractive in this scenario.
    ref_pp = np.zeros(161, dtype=np.float32)

    # CM multiplier: 1.0 up to stat 23, then 2.0 from 24 onward.
    # With cur_cm=0 and GEM_SCALE_NORMAL=2, CM gems >= 12 reaches stat >= 24.
    ref_cm = np.ones(161, dtype=np.float32)
    ref_cm[24:] = 2.0

    # FM multiplier: 1.0 up to stat 5, then 2.0 from 6 onward.
    # With cur_fm=0 and GEM_SCALE_FEVER=3, FM gems >= 2 reaches stat >= 6.
    ref_fm = np.ones(161, dtype=np.float32)
    ref_fm[6:] = 2.0

    fields.ref_pp_field.from_numpy(ref_pp)
    fields.ref_cm_field.from_numpy(ref_cm)
    fields.ref_fm_field.from_numpy(ref_fm)

    out = np.zeros(7, dtype=np.int32)

    @ti.kernel
    def _run(out_arr: ti.types.ndarray(dtype=ti.i32, ndim=1)):
        # Fever mask bits: set all bits to 1 so every head note is a fever note.
        m0 = ti.u32(0xFFFFFFFF)
        m1 = ti.u32(0xFFFFFFFF)
        m2 = ti.u32(0xFFFFFFFF)
        m3 = ti.u32(0xFFFFFFFF)

        res = kernels_scoring._optimize_core_device_refined_from_hint_preloaded_bits_impl(
            ti.i32(85),  # budget (remaining after FT/FF)
            ti.i32(0),  # cur_pp
            ti.i32(0),  # cur_cm
            ti.i32(0),  # cur_fm
            ti.i32(1000),  # cur_p_val
            ti.i32(500),  # cur_s_val
            ti.i32(0),  # is_p_pp
            ti.i32(0),  # is_s_pp
            ti.i32(0),  # is_p_cm
            ti.i32(0),  # is_s_cm
            ti.i32(0),  # is_p_fm
            ti.i32(0),  # is_s_fm
            ti.i32(1),  # is_p_ov (OV contributes to primary)
            ti.i32(0),  # is_s_ov
            m0,
            m1,
            m2,
            m3,
            ti.i32(100),  # head_len
            ti.i32(0),  # count_fever (body)
            ti.i32(0),  # count_normal (body)
            ti.i32(0),  # hint_pp
            ti.i32(12),  # hint_cm
            ti.i32(3),  # hint_fm
            ti.i32(70),  # hint_ov
        )
        for i in ti.static(range(7)):
            out_arr[i] = res[i]

    _run(out)
    ti.sync()

    # Layout: [score, pp, cm, fm, ov, p_val, s_val]
    assert int(out[1]) == 0
    assert int(out[2]) == 12
    assert int(out[3]) == 2
    assert int(out[4]) == 71
