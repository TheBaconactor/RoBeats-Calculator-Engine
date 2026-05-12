from __future__ import annotations

import numpy as np

from gear_optimizer.solver.mini_response_prune import (
    _build_local_response_filter,
    _find_dominated_minis,
    prune_mini_response_envelope,
)
from gear_optimizer.solver.response_envelope_prune import (
    _TimingResponseIndex,
    _env_active_csr,
    _pack_dominance_csr,
)


def _ref_arrays() -> dict[str, np.ndarray]:
    idx = np.arange(161, dtype=np.float64)
    return {
        "Perfect Points": idx.copy(),
        "Combo Multiplier": 1.0 + (idx / 1000.0),
        "Fever Multiplier": 1.0 + (idx / 1000.0),
        "Fever Time": np.ones(161, dtype=np.float64),
        "Fever Fill Rate": np.ones(161, dtype=np.float64),
    }


def _calc_song() -> dict:
    timestamps = np.linspace(0.1, 12.0, 120, dtype=np.float64)
    return {
        "song_data": {"timestamps": timestamps},
        "metadata": {
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
        },
    }


def _rush_primary_flags() -> dict[str, int]:
    return {
        "is_p_ft": 0,
        "is_s_ft": 0,
        "is_p_ff": 0,
        "is_s_ff": 0,
        "is_p_pp": 0,
        "is_s_pp": 0,
        "is_p_cm": 0,
        "is_s_cm": 0,
        "is_p_fm": 1,
        "is_s_fm": 0,
        "is_p_ov": 1,
        "is_s_ov": 0,
    }


def test_mini_response_prunes_cross_timing_redundant_team() -> None:
    item_stats = np.zeros((7, 10), dtype=np.int32)

    out_points, out_codes, out_ids, stats, local_filter = prune_mini_response_envelope(
        gear_points=np.array([[0, 0, 0, 0, 0, 0]], dtype=np.int32),
        mini_points=np.array(
            [
                [0, 0, 0, 0, 10],
                [0, 0, 90, 0, 0],
            ],
            dtype=np.int32,
        ),
        mini_codes=np.array([11, 22], dtype=np.uint64),
        mini_ids=np.array([[1, 2, 3], [4, 5, 6]], dtype=np.int32),
        gpu_arrays={"item_stats": item_stats},
        base_fixed_stats_arr=np.zeros(10, dtype=np.int32),
        calc_song=_calc_song(),
        ref_arrays=_ref_arrays(),
        flags=_rush_primary_flags(),
    )

    assert stats.enabled
    assert stats.reason == "certified"
    assert stats.pruned == 1
    assert local_filter is None
    assert out_points.tolist() == [[0, 0, 0, 0, 10]]
    assert out_codes.tolist() == [11]
    assert out_ids.tolist() == [[1, 2, 3]]


def test_mini_response_timing_cover_vetoes_non_timing_dominance() -> None:
    env = np.array([[90, -1], [-1, 90]], dtype=np.int8)
    pack_dom = np.array([[True, False], [False, True]], dtype=np.bool_)
    pack_dom_offsets, pack_dom_targets = _pack_dominance_csr(pack_dom)
    needed_offsets, needed_packs, needed_requirements = _env_active_csr(env)
    timing = _TimingResponseIndex(
        cells=np.array([0, 1], dtype=np.int32),
        cell_to_row=np.array([0, 1], dtype=np.int32),
        env=env,
        pack_dom=pack_dom,
        pack_dom_offsets=pack_dom_offsets,
        pack_dom_targets=pack_dom_targets,
        best=np.array([[90, -1], [-1, 90]], dtype=np.int8),
        best_row_for_source_row=np.array([0, 1], dtype=np.int32),
        needed_offsets=needed_offsets,
        needed_packs=needed_packs,
        needed_requirements=needed_requirements,
        pack_count=2,
    )

    prune_mask, candidate_pairs, cover_hits = _find_dominated_minis(
        mini_points=np.array([[0, 0, 0, 0, 10], [0, 0, 0, 0, 0]], dtype=np.int32),
        start_rows_by_mini=np.array([[0], [1]], dtype=np.int32),
        timing=timing,
        raw_pack_by_row=np.array([0, 1], dtype=np.int32),
    )

    assert candidate_pairs == 1
    assert cover_hits == 0
    assert prune_mask.tolist() == [False, False]


def test_mini_response_local_filter_deletes_only_covered_gear_cell() -> None:
    env = np.array(
        [
            [90, -1],
            [-1, 90],
            [90, -1],
            [-1, 90],
        ],
        dtype=np.int8,
    )
    needed_offsets, needed_packs, needed_requirements = _env_active_csr(env)
    timing = _TimingResponseIndex(
        cells=np.array([0, 1, 2, 3], dtype=np.int32),
        cell_to_row=np.array([0, 1, 2, 3], dtype=np.int32),
        env=env,
        pack_dom=np.eye(2, dtype=np.bool_),
        pack_dom_offsets=np.array([0, 1, 2], dtype=np.int32),
        pack_dom_targets=np.array([0, 1], dtype=np.int32),
        best=env,
        best_row_for_source_row=np.array([0, 1, 2, 3], dtype=np.int32),
        needed_offsets=needed_offsets,
        needed_packs=needed_packs,
        needed_requirements=needed_requirements,
        pack_count=2,
    )

    local_filter, candidate_pairs, cover_hits = _build_local_response_filter(
        mini_points=np.array([[0, 0, 0, 0, 10], [0, 0, 0, 0, 0]], dtype=np.int32),
        start_rows_by_mini=np.array([[0, 2], [0, 3]], dtype=np.int32),
        timing=timing,
        raw_pack_by_row=np.array([0, 1, 0, 1], dtype=np.int32),
        gear_cell_to_row=np.array([0, 1], dtype=np.int32),
    )

    assert candidate_pairs == 2
    assert cover_hits == 1
    assert local_filter is not None
    assert local_filter.allowed.tolist() == [[True, False], [True, True]]


def test_mini_response_blocks_when_timing_gems_affect_lane_base() -> None:
    flags = _rush_primary_flags()
    flags["is_p_ft"] = 1

    _out_points, _out_codes, _out_ids, stats, local_filter = prune_mini_response_envelope(
        gear_points=np.array([[0, 0, 0, 0, 0, 0]], dtype=np.int32),
        mini_points=np.array([[0, 0, 0, 0, 10], [0, 0, 90, 0, 0]], dtype=np.int32),
        mini_codes=np.array([11, 22], dtype=np.uint64),
        mini_ids=np.array([[1, 2, 3], [4, 5, 6]], dtype=np.int32),
        gpu_arrays={"item_stats": np.zeros((7, 10), dtype=np.int32)},
        base_fixed_stats_arr=np.zeros(10, dtype=np.int32),
        calc_song=_calc_song(),
        ref_arrays=_ref_arrays(),
        flags=flags,
    )

    assert not stats.enabled
    assert stats.reason == "timing_ft_affects_lane_base"
    assert local_filter is None


def test_mini_response_blocks_when_mini_pp_is_not_in_frontier_state() -> None:
    item_stats = np.zeros((7, 10), dtype=np.int32)
    item_stats[4, 0] = 5

    _out_points, _out_codes, _out_ids, stats, local_filter = prune_mini_response_envelope(
        gear_points=np.array([[0, 0, 0, 0, 0, 0]], dtype=np.int32),
        mini_points=np.array([[0, 0, 0, 0, 10], [0, 0, 90, 0, 0]], dtype=np.int32),
        mini_codes=np.array([11, 22], dtype=np.uint64),
        mini_ids=np.array([[1, 2, 3], [4, 5, 6]], dtype=np.int32),
        gpu_arrays={"item_stats": item_stats},
        base_fixed_stats_arr=np.zeros(10, dtype=np.int32),
        calc_song=_calc_song(),
        ref_arrays=_ref_arrays(),
        flags=_rush_primary_flags(),
    )

    assert not stats.enabled
    assert stats.reason == "mini_pp_not_in_frontier_state"
    assert local_filter is None
