from __future__ import annotations

import pytest

from gear_optimizer.solver.scoring.runtime_state import _GPU_LOCK

pytestmark = pytest.mark.gpu


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_calc_score_with_grid_bits_preserves_large_integer_body_score() -> None:
    import taichi as ti

    from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready
    from gear_optimizer.solver.taichi_gem.kernels import kernels_helpers

    with _GPU_LOCK:
        ensure_ready()
        out = ti.field(dtype=ti.i32, shape=())

        @ti.kernel
        def _score():
            out[None] = kernels_helpers.calc_score_with_grid_bits(
                12345.0,
                1.0,
                1.0,
                ti.u32(0),
                ti.u32(0),
                ti.u32(0),
                ti.u32(0),
                0,
                0,
                1701,
            )

        _score()
        score = int(out[None])

    assert score == 12345 * 1701
