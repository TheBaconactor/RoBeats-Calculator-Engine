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


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_base_gpu_rescore_uses_best_retained_physical_surface() -> None:
    """The legacy single-grid representative must never replace frontier maximization."""
    import taichi as ti

    from gear_optimizer.solver.taichi_gem import fields
    from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready
    from gear_optimizer.solver.taichi_gem.kernels.kernels_scoring import (
        score_timeline_frontier_cached_device,
    )

    with _GPU_LOCK:
        ensure_ready()
        out = ti.field(dtype=ti.i32, shape=())
        fields.grid_head_len[0, 0, 0] = 1
        fields.grid_frontier_count[0, 0, 0] = 2
        fields.grid_frontier_offset[0, 0, 0] = 0

        # Representative row: fever on the first head note, normal body note => 503.
        fields.grid_fever_masks_bits[0, 0, 0, 0] = 1
        fields.grid_count_body_fever[0, 0, 0] = 0
        fields.grid_count_body_normal[0, 0, 0] = 1
        fields.grid_frontier_masks_bits_pool[0, 0, 0] = 1
        for word in range(1, 4):
            fields.grid_frontier_masks_bits_pool[0, 0, word] = 0
        fields.grid_frontier_body_fever_pool[0, 0] = 0
        fields.grid_frontier_body_normal_pool[0, 0] = 1

        # Alternate retained row: normal head note, fever body note => 701 (true optimum).
        fields.grid_frontier_masks_bits_pool[0, 1, 0] = 0
        for word in range(1, 4):
            fields.grid_frontier_masks_bits_pool[0, 1, word] = 0
        fields.grid_frontier_body_fever_pool[0, 1] = 1
        fields.grid_frontier_body_normal_pool[0, 1] = 0

        @ti.kernel
        def _score_frontier():
            out[None] = score_timeline_frontier_cached_device(
                100.0,
                2.0,
                3.0,
                0,
                0,
                0,
                1,
            )

        _score_frontier()
        score = int(out[None])

    assert score == 701
