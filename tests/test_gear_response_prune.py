from __future__ import annotations

from typing import Any

import numpy as np

from gear_optimizer.solver.gear_response_prune import (
    _gear_non_timing_dominance_matrix,
    _prune_pairs_by_local_gear_response,
    prune_local_gear_response_pairs,
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


def test_local_gear_response_prunes_same_mini_same_response_dominated_gear() -> None:
    gear_points = np.array(
        [
            [0, 0, 0, 0, 0, 0],
            [10, 10, 10, 0, 0, 10],
        ],
        dtype=np.int32,
    )
    mini_points = np.array([[0, 0, 0, 0, 0]], dtype=np.int32)

    out_g, out_m, stats = prune_local_gear_response_pairs(
        pair_gear_idx=np.array([0, 1], dtype=np.int32),
        pair_mini_idx=np.array([0, 0], dtype=np.int32),
        gear_points=gear_points,
        mini_points=mini_points,
        base_fixed_stats_arr=np.zeros(10, dtype=np.int32),
        calc_song=_calc_song(),
        ref_arrays=_ref_arrays(),
        flags=_rush_primary_flags(),
    )

    assert stats.enabled
    assert stats.reason == "certified"
    assert stats.pruned == 1
    assert out_g.tolist() == [1]
    assert out_m.tolist() == [0]


def test_local_gear_response_keeps_different_response_bucket() -> None:
    gear_dom = np.array(
        [
            [False, False],
            [True, False],
        ],
        dtype=np.bool_,
    )

    keep, counts = _prune_pairs_by_local_gear_response(
        pair_gear_idx=np.array([0, 1], dtype=np.int32),
        pair_mini_idx=np.array([0, 0], dtype=np.int32),
        pair_response_ids=np.array([1, 2], dtype=np.int32),
        gear_dominates=gear_dom,
    )

    assert keep.tolist() == [True, True]
    assert counts["dominance_pairs"] == 0


def test_local_gear_response_keeps_cross_mini_bucket() -> None:
    gear_dom = np.array(
        [
            [False, False],
            [True, False],
        ],
        dtype=np.bool_,
    )

    keep, counts = _prune_pairs_by_local_gear_response(
        pair_gear_idx=np.array([0, 1], dtype=np.int32),
        pair_mini_idx=np.array([0, 1], dtype=np.int32),
        pair_response_ids=np.array([3, 3], dtype=np.int32),
        gear_dominates=gear_dom,
    )

    assert keep.tolist() == [True, True]
    assert counts["dominance_pairs"] == 0


def test_local_gear_response_blocks_when_timing_gems_affect_lane_base() -> None:
    flags = _rush_primary_flags()
    flags["is_p_ft"] = 1

    out_g, out_m, stats = prune_local_gear_response_pairs(
        pair_gear_idx=np.array([0, 1], dtype=np.int32),
        pair_mini_idx=np.array([0, 0], dtype=np.int32),
        gear_points=np.array([[0, 0, 0, 0, 0, 0], [10, 10, 10, 0, 0, 10]], dtype=np.int32),
        mini_points=np.array([[0, 0, 0, 0, 0]], dtype=np.int32),
        base_fixed_stats_arr=np.zeros(10, dtype=np.int32),
        calc_song=_calc_song(),
        ref_arrays=_ref_arrays(),
        flags=flags,
    )

    assert not stats.enabled
    assert stats.reason == "timing_ft_affects_lane_base"
    assert out_g.tolist() == [0, 1]
    assert out_m.tolist() == [0, 0]


def test_local_gear_response_bucket_limit_is_safe_noop() -> None:
    gear_dom = np.array(
        [
            [False, False],
            [True, False],
        ],
        dtype=np.bool_,
    )

    keep, counts = _prune_pairs_by_local_gear_response(
        pair_gear_idx=np.array([0, 1], dtype=np.int32),
        pair_mini_idx=np.array([0, 0], dtype=np.int32),
        pair_response_ids=np.array([7, 7], dtype=np.int32),
        gear_dominates=gear_dom,
        max_bucket_cells=0,
    )

    assert keep.tolist() == [True, True]
    assert counts["skipped_buckets"] == 1


def test_local_gear_response_random_certificate_property() -> None:
    rng = np.random.default_rng(20260512)
    gear_points = rng.integers(0, 50, size=(24, 6), dtype=np.int32)
    # Force a few chains so the experiment exercises actual deletions.
    gear_points[1] = gear_points[0] + np.array([2, 2, 2, 0, 0, 2], dtype=np.int32)
    gear_points[3] = gear_points[2] + np.array([1, 0, 3, 0, 0, 1], dtype=np.int32)
    minis = np.arange(4, dtype=np.int32)
    gears = np.arange(int(gear_points.shape[0]), dtype=np.int32)
    pair_g = np.repeat(gears, int(minis.shape[0]))
    pair_m = np.tile(minis, int(gears.shape[0]))
    response_ids = rng.integers(0, 6, size=int(pair_g.shape[0]), dtype=np.int32)
    response_ids[pair_g == 1] = response_ids[pair_g == 0]
    response_ids[pair_g == 3] = response_ids[pair_g == 2]

    dom = _gear_non_timing_dominance_matrix(gear_points, tie_index=gears)
    keep, counts = _prune_pairs_by_local_gear_response(
        pair_gear_idx=pair_g,
        pair_mini_idx=pair_m,
        pair_response_ids=response_ids,
        gear_dominates=dom,
    )

    assert counts["dominance_pairs"] > 0
    for target in np.flatnonzero(~keep).tolist():
        witnesses = np.flatnonzero(
            keep
            & (pair_m == pair_m[target])
            & (response_ids == response_ids[target])
            & dom[pair_g, pair_g[target]]
        )
        assert witnesses.size > 0


def test_local_gear_response_matrix_gate_runs_before_safety_scan() -> None:
    flags = _rush_primary_flags()
    flags["is_p_ft"] = 1
    gear_points = np.array(
        [
            [0, 0, 0, 0, 0, 0],
            [1, 1, 1, 0, 0, 1],
            [2, 2, 2, 0, 0, 2],
        ],
        dtype=np.int32,
    )

    out_g, out_m, stats = prune_local_gear_response_pairs(
        pair_gear_idx=np.array([0, 1, 2], dtype=np.int32),
        pair_mini_idx=np.array([0, 0, 0], dtype=np.int32),
        gear_points=gear_points,
        mini_points=np.array([[0, 0, 0, 0, 0]], dtype=np.int32),
        base_fixed_stats_arr=np.zeros(10, dtype=np.int32),
        calc_song=_calc_song(),
        ref_arrays=_ref_arrays(),
        flags=flags,
        max_matrix_cells=1,
    )

    assert not stats.enabled
    assert stats.reason == "gear_response_matrix_too_large"
    assert stats.gear_rows == 3
    assert stats.matrix_cells == 9
    assert stats.seconds_timing == 0.0
    assert stats.pruned == 0
    assert out_g.tolist() == [0, 1, 2]
    assert out_m.tolist() == [0, 0, 0]


def test_local_gear_response_no_dominance_skips_timing_signature(monkeypatch: Any) -> None:
    import gear_optimizer.solver.gear_response_prune as grp

    def fail_if_called(**_kwargs: Any) -> tuple[np.ndarray, int, int]:
        raise AssertionError("timing signatures are unnecessary when no gear dominates another")

    monkeypatch.setattr(grp, "_pair_response_signature_ids", fail_if_called)
    gear_points = np.array(
        [
            [10, 0, 0, 0, 0, 0],
            [0, 10, 0, 0, 0, 0],
        ],
        dtype=np.int32,
    )

    out_g, out_m, stats = grp.prune_local_gear_response_pairs(
        pair_gear_idx=np.array([0, 1], dtype=np.int32),
        pair_mini_idx=np.array([0, 0], dtype=np.int32),
        gear_points=gear_points,
        mini_points=np.array([[0, 0, 0, 0, 0]], dtype=np.int32),
        base_fixed_stats_arr=np.zeros(10, dtype=np.int32),
        calc_song=_calc_song(),
        ref_arrays=_ref_arrays(),
        flags=_rush_primary_flags(),
    )

    assert stats.enabled
    assert stats.reason == "no_gear_dominance"
    assert stats.seconds_timing == 0.0
    assert stats.pruned == 0
    assert out_g.tolist() == [0, 1]
    assert out_m.tolist() == [0, 0]


def test_local_gear_response_ignores_unused_negative_rows() -> None:
    gear_points = np.array(
        [
            [0, 0, 0, 0, 0, 0],
            [10, 10, 10, 0, 0, 10],
            [-1, -1, -1, 0, 0, -1],
        ],
        dtype=np.int32,
    )

    out_g, out_m, stats = prune_local_gear_response_pairs(
        pair_gear_idx=np.array([0, 1], dtype=np.int32),
        pair_mini_idx=np.array([0, 0], dtype=np.int32),
        gear_points=gear_points,
        mini_points=np.array([[0, 0, 0, 0, 0]], dtype=np.int32),
        base_fixed_stats_arr=np.zeros(10, dtype=np.int32),
        calc_song=_calc_song(),
        ref_arrays=_ref_arrays(),
        flags=_rush_primary_flags(),
    )

    assert stats.enabled
    assert stats.reason == "certified"
    assert out_g.tolist() == [1]
    assert out_m.tolist() == [0]
