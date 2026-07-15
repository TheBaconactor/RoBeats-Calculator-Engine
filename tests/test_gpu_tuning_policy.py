from gear_optimizer.solver.gpu_tuning_policy import (
    choose_fg_target_threads_per_kernel,
    plan_fg_stage1_cfg_chunk,
)


def test_choose_fg_target_threads_per_kernel_uses_thresholds_and_override():
    assert choose_fg_target_threads_per_kernel(n_work_items=30_000, is_metal=False) == 6_000_000
    assert choose_fg_target_threads_per_kernel(n_work_items=60_000, is_metal=False) == 4_000_000
    assert choose_fg_target_threads_per_kernel(n_work_items=200_000, is_metal=False) == 3_000_000
    assert choose_fg_target_threads_per_kernel(n_work_items=400_000, is_metal=False) == 2_000_000
    assert choose_fg_target_threads_per_kernel(n_work_items=30_000, is_metal=True) == 2_000_000
    assert (
        choose_fg_target_threads_per_kernel(
            n_work_items=30_000,
            is_metal=False,
            target_threads_override=7_000_000,
        )
        == 7_000_000
    )


def test_plan_fg_stage1_cfg_chunk_forces_single_band_for_small_work():
    plan = plan_fg_stage1_cfg_chunk(
        n_work_items=10_000,
        stage1_block_dim=64,
        cfg_chunk=None,
        max_cfg_len=2048,
        is_metal=False,
        target_threads_override=0,
        small_work_single_band=True,
        small_work_max_work_items=20_000,
        small_work_max_cfg_len=4096,
    )

    assert plan.target_threads == 6_000_000
    assert plan.target_cfg_per_thread == 9
    assert plan.requested_cfg_chunk == 576
    assert plan.cfg_chunk == 2048
    assert plan.single_band_forced is True


def test_plan_fg_stage1_cfg_chunk_keeps_nonzero_chunk_when_max_cfg_unknown():
    plan = plan_fg_stage1_cfg_chunk(
        n_work_items=80_000,
        stage1_block_dim=64,
        cfg_chunk=None,
        max_cfg_len=0,
        is_metal=False,
        target_threads_override=0,
        small_work_single_band=True,
        small_work_max_work_items=20_000,
        small_work_max_cfg_len=4096,
    )

    assert plan.target_threads == 4_000_000
    assert plan.target_cfg_per_thread == 1
    assert plan.requested_cfg_chunk == 256
    assert plan.cfg_chunk == 256
    assert plan.single_band_forced is False


def test_plan_fg_stage1_cfg_chunk_uses_metal_default_and_clamps():
    plan = plan_fg_stage1_cfg_chunk(
        n_work_items=5_000,
        stage1_block_dim=64,
        cfg_chunk=None,
        max_cfg_len=12,
        is_metal=True,
        target_threads_override=0,
        small_work_single_band=True,
        small_work_max_work_items=20_000,
        small_work_max_cfg_len=4096,
    )

    assert plan.target_threads == 2_000_000
    assert plan.target_cfg_per_thread == 0
    assert plan.requested_cfg_chunk == 16
    assert plan.cfg_chunk == 12
    assert plan.single_band_forced is True


def test_plan_fg_stage1_cfg_chunk_respects_explicit_chunk_when_single_band_disabled():
    plan = plan_fg_stage1_cfg_chunk(
        n_work_items=10_000,
        stage1_block_dim=64,
        cfg_chunk=384,
        max_cfg_len=512,
        is_metal=False,
        target_threads_override=0,
        small_work_single_band=False,
        small_work_max_work_items=20_000,
        small_work_max_cfg_len=4096,
    )

    assert plan.requested_cfg_chunk == 384
    assert plan.cfg_chunk == 384
    assert plan.single_band_forced is False
