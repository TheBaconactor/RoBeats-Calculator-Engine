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


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
@pytest.mark.skipif(sys.platform != "darwin", reason="Regression reproduces on macOS Vulkan")
def test_skyline_warmup_compiles_on_macos_vulkan() -> None:
    from gear_optimizer.solver.taichi_gem import fields as gpu_fields
    from gear_optimizer.solver.taichi_gem.api import hard_reset_taichi
    from gear_optimizer.solver.taichi_gem.api.skyline_operations import (
        SKYLINE_INIT_global_best,
        SKYLINE_INIT_runs_best,
        _warmup_calc_song,
        _warmup_ref_arrays,
        reset_skyline_upload_caches,
        skyline_evaluate_population,
        skyline_generate_initial_populations,
        skyline_load_initial_population,
        skyline_seed_rng_runs,
        skyline_upload_base_fixed_stats,
        skyline_upload_fg_effective_tables,
        skyline_upload_island_boundaries,
        skyline_upload_item_stats,
    )
    from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready
    from gear_optimizer.solver.taichi_gem.api.timeline import precompute_timeline_gpu_for_warmup
    from gear_optimizer.solver.taichi_gem.runtime import init_taichi
    import taichi as ti

    hard_reset_taichi(reason="pytest macOS Vulkan skyline warmup regression")
    reset_skyline_upload_caches()

    init_taichi()
    assert gpu_fields.IS_METAL is True

    ref_arrays = _warmup_ref_arrays()
    ensure_ready(ref_arrays)
    precompute_timeline_gpu_for_warmup(_warmup_calc_song(), ref_arrays, song_slot=0)

    item_stats_np = np.zeros((1, gpu_fields.ITEM_STAT_DIM), dtype=np.int32)
    slot_start_np = np.zeros((gpu_fields.MAX_SLOTS,), dtype=np.int32)
    slot_count_np = np.ones((gpu_fields.MAX_SLOTS,), dtype=np.int32)
    skyline_upload_item_stats(item_stats_np, slot_start_np, slot_count_np)
    skyline_upload_base_fixed_stats(np.zeros((gpu_fields.ITEM_STAT_DIM,), dtype=np.int32))
    skyline_upload_fg_effective_tables(np.zeros((1,), dtype=np.int32), np.zeros((1,), dtype=np.int32))

    n_genomes = min(64, int(getattr(gpu_fields, "MAX_SKYLINE_RUN_GENOMES", 250) or 250), int(gpu_fields.MAX_GENOMES))
    skyline_upload_island_boundaries(np.array([0, int(n_genomes)], dtype=np.int32))
    skyline_generate_initial_populations(run_idx_start=0, n_runs=1, n_genomes=int(n_genomes), n_slots=9, seed=12345)
    skyline_load_initial_population(run_idx=0, n_genomes=int(n_genomes), n_slots=9)
    skyline_seed_rng_runs(n_runs=1, n_genomes_per_run=int(n_genomes), seed=12345)
    SKYLINE_INIT_runs_best(run_idx_start=0, n_runs=1, n_slots=9)
    SKYLINE_INIT_global_best()

    skyline_evaluate_population(
        int(n_genomes),
        n_slots=9,
        total_budget=min(90, int(gpu_fields.MAX_TOTAL_BUDGET)),
        gem_scale_fever=3,
        song_slot=0,
        materialize_mode="none",
    )
    ti.sync()
