import numpy as np

from gear_optimizer.helpers.song_helpers.force_greats import gpu_dispatch
from gear_optimizer.helpers.song_helpers.force_greats.ftff_pairs import (
    reduce_ftff_pairs_by_max_fp_surface,
    reduce_ftff_pairs_by_surface_keys,
)
from gear_optimizer.solver import gpu_executor
from gear_optimizer.solver import gpu_executor_fg
from gear_optimizer.solver.taichi_gem.force_greats import api as fg_api
from gear_optimizer.solver.taichi_gem.force_greats import kernels as fg_kernels


def test_surface_pair_reducer_drops_only_same_surface_budget_dominated_pairs() -> None:
    pairs = np.asarray([(0, 0), (1, 0), (0, 1), (2, 0)], dtype=np.int32)
    max_fp = np.asarray(
        [
            [2, 3, 1],
            [2, 3, 1],
            [9, 0, 1],
            [2, 3, 1],
        ],
        dtype=np.int16,
    )

    result = reduce_ftff_pairs_by_max_fp_surface(
        pairs,
        max_fp,
        n_sections=3,
        total_budget=90,
    )

    assert result.dropped == 2
    assert result.pairs.tolist() == [[0, 0], [0, 1]]
    assert result.max_fp_matrix.tolist() == [[2, 3, 1], [9, 0, 1]]


def test_surface_pair_reducer_keeps_elemental_tradeoffs_on_same_surface() -> None:
    pairs = np.asarray([(1, 0), (2, 0), (0, 1), (0, 2)], dtype=np.int32)
    max_fp = np.asarray([[4, 4], [4, 4], [8, 1], [8, 1]], dtype=np.int16)

    result = reduce_ftff_pairs_by_max_fp_surface(
        pairs,
        max_fp,
        n_sections=2,
        total_budget=90,
        is_p_ft=1,
    )

    assert (1, 0) in [tuple(x) for x in result.pairs.tolist()]
    assert (2, 0) in [tuple(x) for x in result.pairs.tolist()]
    assert (0, 1) in [tuple(x) for x in result.pairs.tolist()]
    assert (0, 2) not in [tuple(x) for x in result.pairs.tolist()]
    assert result.dropped == 1


def test_surface_pair_reducer_preserves_order_after_frontier_deletions() -> None:
    pairs = np.asarray([(3, 0), (0, 0), (2, 0), (0, 1)], dtype=np.int32)
    max_fp = np.asarray([[5], [5], [5], [7]], dtype=np.int16)

    result = reduce_ftff_pairs_by_max_fp_surface(
        pairs,
        max_fp,
        n_sections=1,
        total_budget=90,
    )

    assert result.dropped == 2
    assert result.pairs.tolist() == [[0, 0], [0, 1]]
    assert result.max_fp_matrix.tolist() == [[5], [7]]


def test_fused_and_explicit_paths_use_shared_surface_reduction_contract() -> None:
    import inspect

    executor_body = inspect.getsource(gpu_executor.GpuExecutor._run_fg_solve_with_breakpoints_payload)
    executor_runner_body = inspect.getsource(gpu_executor_fg.run_fg_solve_with_breakpoints_payload)
    executor_task_body = inspect.getsource(gpu_executor_fg.build_fg_breakpoint_tasks)

    assert not hasattr(gpu_dispatch, "process_force_greats_gpu_finder")
    assert "run_fg_solve_with_breakpoints_payload(" in executor_body
    assert "build_fg_breakpoint_tasks(" in executor_runner_body
    assert "reduce_ftff_pairs_by_max_fp_surface(" in executor_task_body
    assert "_reduce_ftff_pairs_by_max_fp_surface(" not in executor_task_body


def test_surface_reduction_result_object_is_single_contract() -> None:
    pairs = np.asarray([(0, 0), (1, 0)], dtype=np.int32)
    max_fp = np.asarray([[2], [2]], dtype=np.int16)

    result = reduce_ftff_pairs_by_max_fp_surface(pairs, max_fp, n_sections=1, total_budget=90)

    assert result.dropped == 1
    assert result.pairs.tolist() == [[0, 0]]
    assert result.max_fp_matrix.tolist() == [[2]]


def test_surface_key_reducer_applies_base2_pareto_contract_without_maxfp_matrix() -> None:
    pairs = np.asarray([(3, 0), (0, 0), (2, 0), (0, 2), (0, 1)], dtype=np.int32)
    surface_keys = ["same-mask", "same-mask", "same-mask", "other-mask", "other-mask"]

    result = reduce_ftff_pairs_by_surface_keys(
        pairs,
        surface_keys,
        total_budget=90,
        is_p_ff=1,
    )

    assert result.dropped == 2
    assert result.pairs.tolist() == [[0, 0], [0, 2], [0, 1]]
    assert result.kept_indices.tolist() == [1, 3, 4]


def test_surface_key_reducer_noops_when_surface_keys_are_not_complete() -> None:
    pairs = np.asarray([(0, 0), (1, 0)], dtype=np.int32)

    result = reduce_ftff_pairs_by_surface_keys(pairs, ["only-one-key"], total_budget=90)

    assert result.dropped == 0
    assert result.pairs.tolist() == [[0, 0], [1, 0]]


def test_surface_key_reducer_accepts_structured_exact_keys() -> None:
    pairs = np.asarray([(2, 0), (0, 0), (1, 1)], dtype=np.int32)
    surface_keys = [[[1, 2], [3, 4]], [[1, 2], [3, 4]], np.asarray([[9, 8]], dtype=np.int16)]

    result = reduce_ftff_pairs_by_surface_keys(pairs, surface_keys, total_budget=90)

    assert result.dropped == 1
    assert result.pairs.tolist() == [[0, 0], [1, 1]]


def test_gpu_surface_pair_reduction_runs_after_gpu_max_fp_before_stage1() -> None:
    import inspect

    body = inspect.getsource(fg_api.solve_force_greats_finder_gpu_tasks)
    cfg_len_pos = body.index("fg_compute_cfg_total_len_kernel(")
    reduce_pos = body.index("fg_zero_dominated_surface_pairs_kernel(")
    max_pos = body.index("fg_reduce_cfg_total_len_max_kernel(")
    stage1_pos = body.index("fg_stage1_init")

    assert cfg_len_pos < reduce_pos < max_pos < stage1_pos
    assert "_FG_SURFACE_PAIR_REDUCTION_MAX_PAIRS" in body


def test_gpu_surface_pair_reduction_kernel_uses_same_lossless_dominance_contract() -> None:
    import inspect

    body = inspect.getsource(fg_kernels.fg_zero_dominated_surface_pairs_kernel)

    assert "fg_cfg_max_fp[i, sec] != fg_cfg_max_fp[j, sec]" in body
    assert "budget_j >= budget_i and p_j >= p_i and s_j >= s_i" in body
    assert "fg_cfg_total_len_list[i] = 0" in body
    assert ".to_numpy" not in body
