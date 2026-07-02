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
def test_exact_inner_bnb_scores_all_timeline_frontier_variants() -> None:
    import taichi as ti

    from gear_optimizer.solver.scoring.runtime_state import _GPU_LOCK
    from gear_optimizer.solver.taichi_gem import fields
    from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready
    from gear_optimizer.solver.taichi_gem.kernels.kernels_scoring import optimize_core_device_exact_bound

    ref_arrays = {
        "Perfect Points": np.full((161,), 10_000.0, dtype=np.float32),
        "Combo Multiplier": np.full((161,), 2.0, dtype=np.float32),
        "Fever Multiplier": np.full((161,), 5.0, dtype=np.float32),
        "Fever Fill Rate": np.ones((161,), dtype=np.float32),
        "Fever Time": np.ones((161,), dtype=np.float32),
    }

    with _GPU_LOCK:
        ensure_ready(ref_arrays)
        out = ti.field(dtype=ti.i32, shape=(2,))

        @ti.kernel
        def _run():
            song_slot = ti.i32(0)
            ft_idx = ti.i32(0)
            ff_idx = ti.i32(0)
            base_pool_idx = ti.i32(3)

            fields.grid_head_len[song_slot, ft_idx, ff_idx] = ti.cast(0, ti.i8)
            for word in ti.static(range(4)):
                fields.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, word] = ti.u32(0)

            # Primary/proxy timeline: all body notes are normal.
            fields.grid_count_body_fever[song_slot, ft_idx, ff_idx] = ti.cast(0, ti.i16)
            fields.grid_count_body_normal[song_slot, ft_idx, ff_idx] = ti.cast(10, ti.i16)
            fields.grid_frontier_count[song_slot, ft_idx, ff_idx] = ti.cast(0, ti.i32)
            fields.grid_frontier_offset[song_slot, ft_idx, ff_idx] = ti.cast(0, ti.i32)
            fallback = optimize_core_device_exact_bound(
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                10,
                song_slot,
                ft_idx,
                ff_idx,
            )

            # Frontier exposes five packed surfaces with an offset. The best
            # surface lives in the 5th packed slot, proving the consumer no
            # longer has a hard four-variant cap.
            fields.grid_frontier_count[song_slot, ft_idx, ff_idx] = ti.cast(5, ti.i32)
            fields.grid_frontier_offset[song_slot, ft_idx, ff_idx] = base_pool_idx
            for variant_idx in ti.static(range(5)):
                pool_idx = base_pool_idx + ti.cast(variant_idx, ti.i32)
                fields.grid_frontier_masks_bits_pool[song_slot, pool_idx, 0] = ti.u32(0)
                fields.grid_frontier_masks_bits_pool[song_slot, pool_idx, 1] = ti.u32(0)
                fields.grid_frontier_masks_bits_pool[song_slot, pool_idx, 2] = ti.u32(0)
                fields.grid_frontier_masks_bits_pool[song_slot, pool_idx, 3] = ti.u32(0)
                fields.grid_frontier_body_fever_pool[song_slot, pool_idx] = ti.cast(variant_idx, ti.i32)
                fields.grid_frontier_body_normal_pool[song_slot, pool_idx] = ti.cast(10 - variant_idx, ti.i32)
                for coeff in ti.static(range(4)):
                    # head_len == 0 -> all head coefficients are zero for every variant.
                    fields.grid_frontier_head_coeffs_pool[song_slot, pool_idx, coeff] = ti.cast(0, ti.i16)
            frontier = optimize_core_device_exact_bound(
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                10,
                song_slot,
                ft_idx,
                ff_idx,
            )

            out[0] = fallback[0]
            out[1] = frontier[0]

        _run()
        got = out.to_numpy()

        @ti.kernel
        def _disable_frontier():
            fields.grid_frontier_count[0, 0, 0] = ti.cast(0, ti.i32)
            fields.grid_frontier_offset[0, 0, 0] = ti.cast(0, ti.i32)

        _disable_frontier()

        expected_frontier = int((4 * 100_000) + (6 * 20_000))

    assert int(got[1]) > int(got[0])
    assert int(got[1]) == expected_frontier
