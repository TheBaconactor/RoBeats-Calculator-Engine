from __future__ import annotations

import numpy as np
import pytest

pytestmark = pytest.mark.gpu


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


def _run_gpu_exact_bound_preloaded(
    *,
    ref_pp: np.ndarray,
    ref_cm: np.ndarray,
    ref_fm: np.ndarray,
    budget: int,
    cur_pp: int,
    cur_cm: int,
    cur_fm: int,
    cur_p_val: int,
    cur_s_val: int,
    is_p_pp: int,
    is_s_pp: int,
    is_p_cm: int,
    is_s_cm: int,
    is_p_fm: int,
    is_s_fm: int,
    is_p_ov: int,
    is_s_ov: int,
    head_len: int,
    count_fever: int,
    count_normal: int,
) -> np.ndarray:
    import taichi as ti

    from gear_optimizer.solver.scoring.gpu_solver import _GPU_LOCK
    from gear_optimizer.solver.taichi_gem import fields
    from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready
    from gear_optimizer.solver.taichi_gem.kernels.kernels_scoring import optimize_core_device_exact_bound_preloaded_bits

    ref_arrays = {
        "Perfect Points": np.asarray(ref_pp, dtype=np.float32),
        "Combo Multiplier": np.asarray(ref_cm, dtype=np.float32),
        "Fever Multiplier": np.asarray(ref_fm, dtype=np.float32),
        "Fever Fill Rate": np.ones_like(ref_cm, dtype=np.float32),
        "Fever Time": np.ones_like(ref_cm, dtype=np.float32),
    }

    with _GPU_LOCK:
        ensure_ready(ref_arrays)
        fields.ref_pp_field.from_numpy(ref_arrays["Perfect Points"])
        fields.ref_cm_field.from_numpy(ref_arrays["Combo Multiplier"])
        fields.ref_fm_field.from_numpy(ref_arrays["Fever Multiplier"])
        out = ti.field(dtype=ti.i32, shape=(7,))

        @ti.kernel
        def _run():
            res = optimize_core_device_exact_bound_preloaded_bits(
                ti.i32(budget),
                ti.i32(cur_pp),
                ti.i32(cur_cm),
                ti.i32(cur_fm),
                ti.i32(cur_p_val),
                ti.i32(cur_s_val),
                ti.i32(is_p_pp),
                ti.i32(is_s_pp),
                ti.i32(is_p_cm),
                ti.i32(is_s_cm),
                ti.i32(is_p_fm),
                ti.i32(is_s_fm),
                ti.i32(is_p_ov),
                ti.i32(is_s_ov),
                ti.u32(0),
                ti.u32(0),
                ti.u32(0),
                ti.u32(0),
                ti.i32(head_len),
                ti.i32(count_fever),
                ti.i32(count_normal),
            )
            for i in ti.static(range(7)):
                out[i] = res[i]

        _run()
        ti.sync()
        return out.to_numpy()


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_exact_bound_crosses_cm_plateau_without_legacy_local_search() -> None:
    """
    Exact-bound scoring should cross CM breakpoints by enumeration, not by the
    removed warm-start local-search jump rule.
    """
    # Breakpoint: CM multiplier stays at 1.0 until stat >= 6, then jumps to 2.0.
    ref_cm = np.ones((161,), dtype=np.float32)
    ref_cm[:6] = 1.0
    ref_cm[6:] = 2.0
    got = _run_gpu_exact_bound_preloaded(
        ref_pp=np.zeros((161,), dtype=np.float32),
        ref_cm=ref_cm,
        ref_fm=np.ones((161,), dtype=np.float32),
        budget=10,
        cur_pp=0,
        cur_cm=0,
        cur_fm=0,
        cur_p_val=0,
        cur_s_val=0,
        is_p_pp=0,
        is_s_pp=0,
        is_p_cm=0,
        is_s_cm=0,
        is_p_fm=0,
        is_s_fm=0,
        is_p_ov=1,
        is_s_ov=0,
        head_len=0,
        count_fever=0,
        count_normal=250_000,
    )

    gems_cm = int(got[2])
    assert gems_cm >= 3


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_exact_bound_allows_cm_above_50_without_flow_lane() -> None:
    ref_cm = np.ones((161,), dtype=np.float32)
    ref_cm[62:] = np.float32(10.0)

    got = _run_gpu_exact_bound_preloaded(
        ref_pp=np.ones((161,), dtype=np.float32),
        ref_cm=ref_cm,
        ref_fm=np.ones((161,), dtype=np.float32),
        budget=1,
        cur_pp=0,
        cur_cm=60,
        cur_fm=0,
        cur_p_val=100,
        cur_s_val=0,
        is_p_pp=0,
        is_s_pp=0,
        is_p_cm=0,
        is_s_cm=0,
        is_p_fm=0,
        is_s_fm=0,
        is_p_ov=1,
        is_s_ov=0,
        head_len=0,
        count_fever=0,
        count_normal=8,
    )

    assert int(got[2]) == 1


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_exact_bound_allows_pp_without_chill_lane() -> None:
    ref_pp = np.ones((161,), dtype=np.float32)
    ref_pp[12:] = np.float32(1000.0)

    got = _run_gpu_exact_bound_preloaded(
        ref_pp=ref_pp,
        ref_cm=np.ones((161,), dtype=np.float32),
        ref_fm=np.ones((161,), dtype=np.float32),
        budget=1,
        cur_pp=10,
        cur_cm=0,
        cur_fm=0,
        cur_p_val=0,
        cur_s_val=0,
        is_p_pp=0,
        is_s_pp=0,
        is_p_cm=0,
        is_s_cm=0,
        is_p_fm=0,
        is_s_fm=0,
        is_p_ov=1,
        is_s_ov=0,
        head_len=0,
        count_fever=0,
        count_normal=8,
    )

    assert int(got[1]) == 1
