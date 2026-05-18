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


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_local_search_from_hint_cm_jump_breaks_plateau_trap() -> None:
    """
    Regression guard for warm-start scoring: +/-1 swaps can get stuck when CM needs multiple
    gems to cross a multiplier breakpoint. local_search_from_hint() should be able to jump
    CM across a short plateau window (<=10) when the hint has CM=0.
    """
    import taichi as ti

    from gear_optimizer.solver.scoring.runtime_state import _GPU_LOCK
    from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready
    from gear_optimizer.solver.taichi_gem.kernels.kernels_scoring import local_search_from_hint

    # Breakpoint: CM multiplier stays at 1.0 until stat >= 6, then jumps to 2.0.
    ref_cm = np.ones((161,), dtype=np.float32)
    ref_cm[:6] = 1.0
    ref_cm[6:] = 2.0
    ref_arrays = {
        "Perfect Points": np.zeros((161,), dtype=np.float32),
        "Combo Multiplier": ref_cm,
        "Fever Multiplier": np.ones((161,), dtype=np.float32),
        "Fever Fill Rate": np.ones((161,), dtype=np.float32),
        "Fever Time": np.ones((161,), dtype=np.float32),
    }

    budget = 10

    # Make the body dominate so head masks are irrelevant (head_len=0).
    head_len = 0
    count_fever = 0
    count_normal = 250_000

    # Hint starts at CM=0 and all OV. CM has no element delta, so single-step swaps to CM
    # are strictly worse until we cross the breakpoint (3 CM gems).
    hint_pp = 0
    hint_cm = 0
    hint_fm = 0
    hint_ov = budget

    with _GPU_LOCK:
        ensure_ready(ref_arrays)
        out = ti.field(dtype=ti.i32, shape=(7,))

        @ti.kernel
        def _run():
            res = local_search_from_hint(
                hint_pp,
                hint_cm,
                hint_fm,
                hint_ov,
                budget,
                0,  # cur_pp
                0,  # cur_cm
                0,  # cur_fm
                0,  # cur_p_val
                0,  # cur_s_val
                0,  # is_p_pp
                0,  # is_s_pp
                0,  # is_p_cm
                0,  # is_s_cm
                0,  # is_p_fm
                0,  # is_s_fm
                1,  # is_p_ov
                0,  # is_s_ov
                head_len,
                count_fever,
                count_normal,
                0,  # song_slot
                0,  # ft_idx
                0,  # ff_idx
            )
            for i in ti.static(range(7)):
                out[i] = res[i]

        _run()
        got = out.to_numpy()

    gems_cm = int(got[2])
    assert gems_cm >= 3, f"expected CM plateau jump to invest into CM, got gems_cm={gems_cm}"
