import inspect

import numpy as np

from gear_optimizer.helpers.song_helpers.force_greats.ftff_pairs import reduce_ftff_pairs_by_surface_keys
from gear_optimizer.solver import gpu_executor_fg


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


def test_fused_task_builder_uses_prefix_frontier_not_maxfp_matrix() -> None:
    body = inspect.getsource(gpu_executor_fg.build_fg_breakpoint_tasks)

    assert '"mode": "gpu"' in body
    assert "compute_max_fp" not in body
    assert "max_fp_matrix" not in body
