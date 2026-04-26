from gear_optimizer.helpers.song_helpers.force_greats.gpu_dispatch import (
    _estimate_fg_task_threads,
    _estimate_fused_payload_threads,
    _split_items_by_work_budget,
)
from gear_optimizer.helpers.fg_utils import MAX_SECTION_CAPS
from gear_optimizer.helpers.song_helpers.force_greats.work_budget import fused_payload_cfg_len_per_pair

import numpy as np


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


def test_estimate_fused_payload_threads_counts_forced_config_volume():
    fp_cap_table = np.zeros((161, 51), dtype=np.int16)
    fp_cap_table[:, :] = np.arange(51, dtype=np.int16)
    payload = {
        "n_sections": 2,
        "ftff_pairs": np.asarray([(0, 0), (1, 0)], dtype=np.int32),
        "base_stats_pairs": np.asarray([(10, 0)], dtype=np.int32),
        "non_fever_base_by_ff": np.full((161,), 10, dtype=np.int16),
        "fp_cap_table": fp_cap_table,
        "gem_scale_fever": 3,
        "solve_kwargs": {"n_genomes_override": 3},
    }
    # sec0 cap=10 -> 11 configs; sec1 cap=(10*3)//5=6 -> 7 configs.
    # Work is genomes * pairs * (11*7).
    assert _estimate_fused_payload_threads(payload) == 3 * 2 * 77


def test_fused_payload_cfg_len_vectorized_matches_pairwise_reference():
    pairs = np.asarray([(0, 0), (1, 3), (5, 7), (13, 2), (21, 11), (34, 5), (55, 13)], dtype=np.int32)
    base_pairs = np.asarray([(10, 0), (12, 9), (14, 17), (16, 31)], dtype=np.int32)
    non_fever_base_by_ff = (np.arange(161, dtype=np.int16) % 37) + 3
    fp_cap_table = np.zeros((161, 51), dtype=np.int16)
    for ff in range(161):
        for cap in range(51):
            fp_cap_table[ff, cap] = (ff * 3 + cap * 5) % 17
    payload = {
        "n_sections": 4,
        "ftff_pairs": pairs,
        "base_stats_pairs": base_pairs,
        "non_fever_base_by_ff": non_fever_base_by_ff,
        "fp_cap_table": fp_cap_table,
        "gem_scale_fever": 3,
    }

    expected = []
    for _ft_g, ff_g in pairs:
        ff_idx = np.clip(base_pairs[:, 1] + int(ff_g) * 3, 0, 160).astype(np.int32)
        per_pair_cfg = 1
        for sec in range(4):
            base_notes = non_fever_base_by_ff[ff_idx].astype(np.int32)
            cap = base_notes
            if sec == 1:
                cap = (cap * 3) // 5
            elif sec >= 2:
                cap = (cap * 3) // 10
            hard_cap = int(MAX_SECTION_CAPS[sec]) if sec < len(MAX_SECTION_CAPS) else 4
            cap = np.clip(cap, 0, min(50, hard_cap)).astype(np.int32)
            max_fp = int(np.max(fp_cap_table[ff_idx, cap]))
            per_pair_cfg *= max(1, max_fp + 1)
        expected.append(per_pair_cfg)

    actual = fused_payload_cfg_len_per_pair(payload)
    assert actual is not None
    assert actual.tolist() == expected


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
