import sys

import numpy as np
import pytest

pytestmark = pytest.mark.gpu


@pytest.mark.skipif(sys.platform != "darwin", reason="Regression reproduces on macOS Vulkan")
def test_skyline_warmup_compiles_on_macos_vulkan() -> None:
    from gear_optimizer.solver.taichi_gem import fields as gpu_fields
    from gear_optimizer.solver.taichi_gem.api import hard_reset_taichi
    from gear_optimizer.solver.taichi_gem.api.ga_operations import (
        _warmup_calc_song,
        _warmup_ref_arrays,
        reset_ga_upload_caches,
    )
    from gear_optimizer.solver.taichi_gem.api.skyline_operations import (
        skyline_download_results,
        skyline_evaluate_population,
        skyline_generate_initial_populations,
        skyline_load_initial_population,
        skyline_upload_base_fixed_stats,
        skyline_upload_fg_effective_tables,
        skyline_upload_item_stats,
        skyline_upload_population_indices,
    )
    from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready
    from gear_optimizer.solver.taichi_gem.api.timeline import precompute_timeline_gpu_for_warmup
    from gear_optimizer.solver.taichi_gem.runtime import init_taichi
    import taichi as ti

    hard_reset_taichi(reason="pytest macOS Vulkan skyline warmup regression")
    reset_ga_upload_caches()

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
    skyline_generate_initial_populations(run_idx_start=0, n_runs=1, n_genomes=int(n_genomes), n_slots=9, seed=12345)
    skyline_load_initial_population(run_idx=0, n_genomes=int(n_genomes), n_slots=9)

    evaluate = dict(
        n_slots=9,
        total_budget=min(90, int(gpu_fields.MAX_TOTAL_BUDGET)),
        gem_scale_fever=3,
        song_slot=0,
    )
    skyline_evaluate_population(int(n_genomes), materialize_mode="none", **evaluate)
    ti.sync()

    # The production registry solve: upload an encoded population, materialize, download.
    skyline_upload_population_indices(np.zeros((int(n_genomes), 9), dtype=np.int32), n_slots=9)
    skyline_evaluate_population(int(n_genomes), materialize_mode="results_only", **evaluate)
    assert skyline_download_results(int(n_genomes)).shape == (int(n_genomes), 7)
