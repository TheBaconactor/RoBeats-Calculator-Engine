import inspect

import numpy as np

from gear_optimizer.helpers.song_helpers.force_greats import gpu_dispatch
from gear_optimizer.helpers.song_helpers.force_greats.ftff_pairs import _reduce_ftff_pairs_by_max_fp_surface


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

    reduced_pairs, reduced_max_fp, dropped = _reduce_ftff_pairs_by_max_fp_surface(
        pairs,
        max_fp,
        n_sections=3,
        total_budget=90,
    )

    assert dropped == 2
    assert reduced_pairs.tolist() == [[0, 0], [0, 1]]
    assert reduced_max_fp.tolist() == [[2, 3, 1], [9, 0, 1]]


def test_surface_pair_reducer_keeps_elemental_tradeoffs_on_same_surface() -> None:
    pairs = np.asarray([(1, 0), (2, 0), (0, 1), (0, 2)], dtype=np.int32)
    max_fp = np.asarray([[4, 4], [4, 4], [8, 1], [8, 1]], dtype=np.int16)

    reduced_pairs, _reduced_max_fp, dropped = _reduce_ftff_pairs_by_max_fp_surface(
        pairs,
        max_fp,
        n_sections=2,
        total_budget=90,
        is_p_ft=1,
    )

    assert (1, 0) in [tuple(x) for x in reduced_pairs.tolist()]
    assert (2, 0) in [tuple(x) for x in reduced_pairs.tolist()]
    assert (0, 1) in [tuple(x) for x in reduced_pairs.tolist()]
    assert (0, 2) not in [tuple(x) for x in reduced_pairs.tolist()]
    assert dropped == 1


def test_surface_pair_reducer_preserves_order_after_frontier_deletions() -> None:
    pairs = np.asarray([(3, 0), (0, 0), (2, 0), (0, 1)], dtype=np.int32)
    max_fp = np.asarray([[5], [5], [5], [7]], dtype=np.int16)

    reduced_pairs, reduced_max_fp, dropped = _reduce_ftff_pairs_by_max_fp_surface(
        pairs,
        max_fp,
        n_sections=1,
        total_budget=90,
    )

    assert dropped == 2
    assert reduced_pairs.tolist() == [[0, 0], [0, 1]]
    assert reduced_max_fp.tolist() == [[5], [7]]


def test_fg_pair_reduction_is_after_gpu_surface_not_before_payload() -> None:
    body = inspect.getsource(gpu_dispatch.process_force_greats_gpu_finder)
    chunk_pos = body.index("while idx0 < n_sig:")
    payload_pos = body.index("fused_payload_batch.append(fused_payload)", chunk_pos)
    surface_reduce_pos = body.index("_reduce_ftff_pairs_by_max_fp_surface(", chunk_pos)
    max_fp_compute_pos = body.index("max_fp_matrix = _compute_max_fp_blocking()", chunk_pos)

    assert payload_pos < surface_reduce_pos
    assert max_fp_compute_pos < surface_reduce_pos
    assert "_reduce_ftff_pairs_by_resolved_stat_cost(" not in body
    assert "_filter_ftff_pairs_by_resolved_window_max(" not in body
    assert "FGPreSubmitReduceMs" not in body
    assert "FGSurfacePairReduceMs" in body


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
