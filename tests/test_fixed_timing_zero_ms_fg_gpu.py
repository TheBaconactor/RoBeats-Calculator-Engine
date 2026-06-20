"""Guard for the fixed-timing (0ms) FG collapse (issue #51). GPU.

Tier replay scores FG under timing_mode="zero_ms" with the base 0ms scorer, on the proven
identity FG-0ms == base-0ms (a Great is unreachable at chart time, and forcing greats only ever
costs the great penalty with no fever reach to buy back, so the FG optimum forces zero greats).
This test pins that identity against the CANONICAL response-frontier builder: if a future FG
mechanic change ever made forcing greats profitable at 0ms, the builder's surface would beat base
and this guard would fail, flagging that the tier-replay short-circuit is no longer valid.
"""

from __future__ import annotations

import itertools

import numpy as np
import pytest

pytestmark = pytest.mark.gpu


def _ref_arrays() -> dict:
    # combo/fever multipliers within the lossless head-dominance prune box (real game ranges).
    rows = 161
    return {
        "Perfect Points": np.linspace(0.0, 10.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(1.95, 2.72, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(2.95, 5.48, rows, dtype=np.float64),
        "Fever Fill Rate": np.full(rows, 0.5, dtype=np.float64),
        "Fever Time": np.full(rows, 0.5, dtype=np.float64),
    }


def _song(timestamps: np.ndarray) -> dict:
    return {
        "metadata": {
            "Song Name": "pytest_zero_ms_fg_guard",
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
        },
        "song_data": {"timestamps": timestamps},
    }


def _build_0ms_surface(stats, calc_song, ref_arrays):
    """Re-optimized 0ms FG surface from the canonical builder on a chart-only calc_song."""
    from gear_optimizer.solver.taichi_gem.force_greats import response_frontier as rf
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
        build_or_load_response_frontier_payload,
        reset_fg_response_frontier_payload_cache,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_types import all_response_stat_keys

    reset_fg_response_frontier_payload_cache()
    build_or_load_response_frontier_payload(calc_song, ref_arrays, stat_keys=all_response_stat_keys())
    batch = rf.prepare_force_greats_response_frontier_scoring_batch(
        base_stats_list=[stats],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_color="Chill",
        total_budget=0,
    )
    results = rf.score_prepared_force_greats_response_frontier_batch_sync(batch, include_forced_counts=False)
    return results[0].surface


@pytest.mark.parametrize(
    "timestamps",
    [
        np.asarray([0.0, 0.2, 0.5, 1.0, 1.2, 2.0, 3.4, 3.5, 3.6], dtype=np.float32),
        np.round(np.arange(140, dtype=np.float32) * np.float32(0.12), 3).astype(np.float32),
    ],
    ids=["sparse9", "dense140"],
)
def test_fg_0ms_collapses_to_base_0ms(tmp_path, monkeypatch, timestamps):
    from gear_optimizer.solver.scoring.exact_rescore import (
        evaluate_force_greats_exact,
        score_force_greats_response_surface_exact,
        score_stats_fixed_timing_exact,
    )
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path / "fg_cache"))
    ref_arrays = _ref_arrays()
    stats = {
        "Perfect Points": 30,
        "Combo Multiplier": 40,
        "Fever Multiplier": 20,
        "Fever Time": 80,
        "Fever Fill Rate": 100,
        "Rush": 20,
        "Flow": 15,
        "Chill": 0,
        "Beat": 0,
        "Vibe": 0,
    }

    base_0ms = score_stats_fixed_timing_exact(stats, _song(timestamps), ref_arrays)

    # Brute-force the 0ms forced-counts optimum on the chart-only song.
    zero = evaluate_force_greats_exact(stats, _song(timestamps), ref_arrays, [0] * 10)
    sections = int(zero["num_non_fever_sections"])
    cap = int(zero["non_fever_base"])
    best = -1
    for counts in itertools.product(range(min(cap, 3) + 1), repeat=min(sections, 5)):
        best = max(best, int(evaluate_force_greats_exact(stats, _song(timestamps), ref_arrays, counts)["final_score"]))

    # Re-optimized surface from the canonical builder on a zero_ms calc_song.
    cs_zero = _song(timestamps)
    apply_timing_envelope(cs_zero, mode="zero_ms")
    surface = _build_0ms_surface(stats, cs_zero, ref_arrays)
    surface_score = score_force_greats_response_surface_exact(stats, cs_zero, ref_arrays, surface)

    # The whole chain: builder optimum == forced-counts optimum == base (forcing greats never helps).
    assert surface_score == best
    assert best == base_0ms
    # And the optimal surface forces zero greats.
    assert int(getattr(surface, "body_great", 0)) == 0
    assert int(getattr(surface, "body_fever_great", 0)) == 0
