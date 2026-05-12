from __future__ import annotations

import numpy as np

from gear_optimizer.solver.response_envelope_prune import (
    _TimingResponseIndex,
    _env_active_csr,
    _fast_path_blocker,
    _pack_dominance_csr,
    _timing_covers_pairs,
    prune_response_envelope_pairs,
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


def test_response_envelope_prunes_certified_lane_dominated_candidate() -> None:
    item_stats = np.zeros((3, 10), dtype=np.int32)
    item_stats[1, [0, 1, 2, 7]] = [10, 10, 10, 10]
    item_stats[2, [0, 1, 2, 7]] = [10, 10, 10, 11]

    out_g, out_m, stats = prune_response_envelope_pairs(
        pair_gear_idx=np.array([0, 1], dtype=np.int32),
        pair_mini_idx=np.array([0, 0], dtype=np.int32),
        gear_ids=np.array([[1, 0, 0, 0, 0, 0], [2, 0, 0, 0, 0, 0]], dtype=np.int32),
        mini_ids=np.array([[0, 0, 0]], dtype=np.int32),
        gpu_arrays={"item_stats": item_stats},
        base_fixed_stats_arr=np.zeros(10, dtype=np.int32),
        calc_song=_calc_song(),
        ref_arrays=_ref_arrays(),
        flags=_rush_primary_flags(),
    )

    assert stats.enabled
    assert stats.pruned == 1
    assert out_g.tolist() == [1]
    assert out_m.tolist() == [0]


def test_timing_cover_vetoes_non_timing_dominance() -> None:
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

    covered = _timing_covers_pairs(
        source_cells=np.array([0], dtype=np.int32),
        target_cells=np.array([1], dtype=np.int32),
        timing=timing,
    )

    assert covered.tolist() == [False]


def test_fast_path_blocks_when_timing_gems_affect_lane_base() -> None:
    flags = _rush_primary_flags()
    flags["is_p_ft"] = 1

    assert _fast_path_blocker(flags=flags, ref_arrays=_ref_arrays()) == "timing_ft_affects_lane_base"
