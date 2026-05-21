from gear_optimizer.helpers.song_helpers.force_greats.work_budget import fused_payload_cfg_len_per_pair
from gear_optimizer.helpers.song_helpers.force_greats.work_budget import (
    estimate_fg_task_threads as _estimate_fg_task_threads,
    estimate_fused_payload_threads as _estimate_fused_payload_threads,
    split_items_by_work_budget as _split_items_by_work_budget,
)

import numpy as np


def test_estimate_fg_task_threads_counts_cfgs_pairs_and_genomes():
    task = {
        "counts_list": [(0,), (1,), (2,)],
        "ftff_pairs": [(0, 0), (1, 0)],
    }
    assert _estimate_fg_task_threads(task, n_sections=1, n_genomes=5) == 30


def test_estimate_fg_task_threads_rejects_removed_counts_max_fp_rectangles():
    task = {
        "counts_max_fp": [1, 2],
        "ftff_pairs": [(0, 0), (1, 0)],
    }
    import pytest

    with pytest.raises(ValueError, match="counts_max_fp rectangles were removed"):
        _estimate_fg_task_threads(task, n_sections=2, n_genomes=4)


def test_estimate_fg_task_threads_uses_prefix_frontier_for_gpu_counts():
    task = {
        "counts_max_fp": {"mode": "gpu", "n_sections": 3, "song_slot": 0, "gem_scale_fever": 3},
        "ftff_pairs": [(0, 0), (1, 0)],
    }
    assert _estimate_fg_task_threads(task, n_sections=3, n_genomes=4) == 4 * 2 * 8192


def test_estimate_fused_payload_threads_uses_n_genomes_override():
    payload = {
        "ftff_pairs": [(0, 0), (1, 0), (2, 0)],
        "base_stats_pairs": [(100, 100), (103, 100)],
        "solve_kwargs": {"n_genomes_override": 7},
    }
    assert _estimate_fused_payload_threads(payload) == 42


def test_estimate_fused_payload_threads_counts_forced_config_volume():
    payload = {
        "n_sections": 2,
        "ftff_pairs": np.asarray([(0, 0), (1, 0)], dtype=np.int32),
        "base_stats_pairs": np.asarray([(10, 0)], dtype=np.int32),
        "gem_scale_fever": 3,
        "solve_kwargs": {"n_genomes_override": 3},
    }
    assert _estimate_fused_payload_threads(payload) == 3 * 2 * 8192


def test_fused_payload_cfg_len_uses_prefix_frontier_estimate_per_pair():
    pairs = np.asarray([(0, 0), (1, 3), (5, 7), (13, 2), (21, 11), (34, 5), (55, 13)], dtype=np.int32)
    base_pairs = np.asarray([(10, 0), (12, 9), (14, 17), (16, 31)], dtype=np.int32)
    payload = {
        "n_sections": 4,
        "ftff_pairs": pairs,
        "base_stats_pairs": base_pairs,
        "gem_scale_fever": 3,
    }

    actual = fused_payload_cfg_len_per_pair(payload)
    assert actual is not None
    assert actual.tolist() == [8192] * int(pairs.shape[0])


def test_split_items_by_work_budget_preserves_order_and_splits():
    items = ["a", "b", "c", "d"]
    out = _split_items_by_work_budget(
        items,
        max_work=10,
        estimate_fn=lambda x: {"a": 4, "b": 4, "c": 6, "d": 3}[x],
    )
    assert out == [["a", "b"], ["c", "d"]]


def test_split_items_by_work_budget_disables_when_budget_zero():
    items = ["a", "b", "c"]
    out = _split_items_by_work_budget(
        items,
        max_work=0,
        estimate_fn=lambda _x: 100,
    )
    assert out == [["a", "b", "c"]]
