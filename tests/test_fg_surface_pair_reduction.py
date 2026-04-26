import inspect

import numpy as np

from gear_optimizer.helpers.song_helpers.force_greats import gpu_dispatch
from gear_optimizer.helpers.song_helpers.force_greats.ftff_pairs import (
    reduce_ftff_pairs_by_max_fp_surface,
)
from gear_optimizer.solver import gpu_executor
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


def test_fg_pair_reduction_is_after_gpu_surface_not_before_payload() -> None:
    body = inspect.getsource(gpu_dispatch.process_force_greats_gpu_finder)
    chunk_pos = body.index("while idx0 < n_sig:")
    payload_pos = body.index("fused_payload_batch.append(fused_payload)", chunk_pos)
    surface_reduce_pos = body.index("reduce_ftff_pairs_by_max_fp_surface(", chunk_pos)
    max_fp_compute_pos = body.index("max_fp_matrix = _compute_max_fp_blocking()", chunk_pos)

    assert payload_pos < surface_reduce_pos
    assert max_fp_compute_pos < surface_reduce_pos
    assert "_reduce_ftff_pairs_by_resolved_stat_cost(" not in body
    assert "_filter_ftff_pairs_by_resolved_window_max(" not in body
    assert "FGPreSubmitReduceMs" not in body
    assert "FGSurfacePairReduceMs" in body


def test_fused_and_explicit_paths_use_shared_surface_reduction_contract() -> None:
    dispatch_body = inspect.getsource(gpu_dispatch.process_force_greats_gpu_finder)
    executor_body = inspect.getsource(gpu_executor.GpuExecutor._run_fg_solve_with_breakpoints_payload)

    assert "reduce_ftff_pairs_by_max_fp_surface(" in dispatch_body
    assert "reduce_ftff_pairs_by_max_fp_surface(" in executor_body
    assert "_reduce_ftff_pairs_by_max_fp_surface(" not in dispatch_body
    assert "_reduce_ftff_pairs_by_max_fp_surface(" not in executor_body
    assert "FG_FUSED_SURFACE_PAIR_REDUCTION" in executor_body


def test_surface_reduction_result_object_is_single_contract() -> None:
    pairs = np.asarray([(0, 0), (1, 0)], dtype=np.int32)
    max_fp = np.asarray([[2], [2]], dtype=np.int16)

    result = reduce_ftff_pairs_by_max_fp_surface(pairs, max_fp, n_sections=1, total_budget=90)

    assert result.dropped == 1
    assert result.pairs.tolist() == [[0, 0]]
    assert result.max_fp_matrix.tolist() == [[2]]


def test_base_stat_pairs_from_signature_rows_is_stable_and_unique() -> None:
    sig_rows = {
        "a": {"base_stats": {"Fever Time": 3, "Fever Fill Rate": 9}},
        "b": {"base_stats": {"Fever Time": 3, "Fever Fill Rate": 9}},
        "c": {"base_stats": {"Fever Time": 6, "Fever Fill Rate": 0}},
        "ignored": {},
    }

    assert gpu_dispatch._base_stat_pairs_from_signature_rows(["c", "a", "b", "missing"], sig_rows) == [
        (3, 9),
        (6, 0),
    ]


def test_gpu_surface_pair_reduction_runs_after_gpu_max_fp_before_stage1() -> None:
    body = inspect.getsource(fg_api.solve_force_greats_finder_gpu_tasks)
    cfg_len_pos = body.index("fg_compute_cfg_total_len_kernel(")
    reduce_pos = body.index("fg_zero_dominated_surface_pairs_kernel(")
    max_pos = body.index("fg_reduce_cfg_total_len_max_kernel(")
    stage1_pos = body.index("fg_stage1_init")

    assert cfg_len_pos < reduce_pos < max_pos < stage1_pos
    assert "_FG_GPU_SURFACE_PAIR_REDUCTION_MAX_PAIRS" in body


def test_gpu_surface_pair_reduction_kernel_uses_same_lossless_dominance_contract() -> None:
    body = inspect.getsource(fg_kernels.fg_zero_dominated_surface_pairs_kernel)

    assert "fg_cfg_max_fp[i, sec] != fg_cfg_max_fp[j, sec]" in body
    assert "budget_j >= budget_i and p_j >= p_i and s_j >= s_i" in body
    assert "fg_cfg_total_len_list[i] = 0" in body
    assert ".to_numpy" not in body
