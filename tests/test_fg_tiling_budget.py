from gear_optimizer.helpers.song_helpers.force_greats.gpu_dispatch import (
    _estimate_fg_task_threads,
    _estimate_fused_payload_threads,
    _split_items_by_work_budget,
)


def test_estimate_fg_task_threads_counts_cfgs_pairs_and_genomes():
    task = {
        "counts_list": [(0,), (1,), (2,)],
        "ftff_pairs": [(0, 0), (1, 0)],
    }
    assert _estimate_fg_task_threads(task, n_sections=1, n_genomes=5) == 30


def test_estimate_fg_task_threads_expands_counts_max_fp():
    task = {
        "counts_max_fp": [1, 2],
        "ftff_pairs": [(0, 0), (1, 0)],
    }
    # cfg_count=(1+1)*(2+1)=6, pair_count=2, genomes=4
    assert _estimate_fg_task_threads(task, n_sections=2, n_genomes=4) == 48


def test_estimate_fused_payload_threads_uses_n_genomes_override():
    payload = {
        "ftff_pairs": [(0, 0), (1, 0), (2, 0)],
        "base_stats_pairs": [(100, 100), (103, 100)],
        "solve_kwargs": {"n_genomes_override": 7},
    }
    assert _estimate_fused_payload_threads(payload) == 42


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
