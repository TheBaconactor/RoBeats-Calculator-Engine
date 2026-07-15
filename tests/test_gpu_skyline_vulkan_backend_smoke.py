import sys

import numpy as np
import pytest

pytestmark = pytest.mark.gpu


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


def _compile_exact_candidate_surface() -> bool:
    import taichi as ti

    from gear_optimizer.solver.taichi_gem import fields as gpu_fields
    from gear_optimizer.solver.taichi_gem.api import hard_reset_taichi
    from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready
    from gear_optimizer.solver.taichi_gem.api.skyline_operations import (
        _warmup_calc_song,
        _warmup_ref_arrays,
        reset_skyline_upload_caches,
        skyline_download_results,
        skyline_download_scores,
        skyline_evaluate_loadouts,
        skyline_upload_base_fixed_stats,
        skyline_upload_item_stats,
        skyline_upload_loadout_indices,
    )
    from gear_optimizer.solver.taichi_gem.api.timeline import (
        precompute_timeline_gpu_for_warmup,
    )
    from gear_optimizer.solver.taichi_gem.runtime import init_taichi

    hard_reset_taichi(reason="pytest exact candidate Vulkan warmup regression")
    reset_skyline_upload_caches()
    init_taichi()

    ref_arrays = _warmup_ref_arrays()
    ensure_ready(ref_arrays)
    precompute_timeline_gpu_for_warmup(_warmup_calc_song(), ref_arrays, song_slot=0)

    item_stats = np.zeros((1, gpu_fields.ITEM_STAT_DIM), dtype=np.int32)
    slot_start = np.zeros((gpu_fields.MAX_SLOTS,), dtype=np.int32)
    slot_count = np.ones((gpu_fields.MAX_SLOTS,), dtype=np.int32)
    skyline_upload_item_stats(item_stats, slot_start, slot_count)
    skyline_upload_base_fixed_stats(
        np.zeros((gpu_fields.ITEM_STAT_DIM,), dtype=np.int32)
    )

    n_candidates = min(64, int(gpu_fields.MAX_LOADOUTS))
    skyline_upload_loadout_indices(
        np.zeros((n_candidates, gpu_fields.MAX_SLOTS), dtype=np.int32)
    )
    skyline_evaluate_loadouts(
        n_candidates,
        n_slots=gpu_fields.MAX_SLOTS,
        total_budget=min(90, int(gpu_fields.MAX_TOTAL_BUDGET)),
        song_slot=0,
        materialize_mode="scores",
    )
    assert skyline_download_scores(n_candidates).shape == (n_candidates,)

    skyline_evaluate_loadouts(
        n_candidates,
        n_slots=gpu_fields.MAX_SLOTS,
        total_budget=min(90, int(gpu_fields.MAX_TOTAL_BUDGET)),
        song_slot=0,
        materialize_mode="results",
    )
    assert skyline_download_results(n_candidates).shape == (n_candidates, 7)
    ti.sync()
    return bool(gpu_fields.IS_METAL)


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
@pytest.mark.skipif(sys.platform != "darwin", reason="Regression reproduces on macOS Vulkan")
def test_exact_candidate_surface_compiles_on_macos_vulkan() -> None:
    assert _compile_exact_candidate_surface() is True


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
@pytest.mark.skipif(sys.platform == "darwin", reason="Metal-specific path is covered separately")
def test_exact_candidate_surface_compiles_on_vulkan() -> None:
    assert _compile_exact_candidate_surface() is False
