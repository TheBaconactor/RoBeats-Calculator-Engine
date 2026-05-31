from __future__ import annotations

import numpy as np

from gear_optimizer.core.constants import GEM_SCALE_FEVER, TOTAL_ROWS
from gear_optimizer.helpers.song_helpers.force_greats.candidate_certificate import (
    certified_fg_candidate_upper_bound,
)
from gear_optimizer.helpers.song_helpers.force_greats import response_frontier_adapter
from gear_optimizer.solver.taichi_gem.force_greats.response_inner_reference import (
    optimize_response_frontier_inner_exact,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseSurface


def _ref_arrays() -> dict[str, np.ndarray]:
    return {
        "Perfect Points": np.linspace(1.0, 2.0, TOTAL_ROWS + 1, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 2.0, TOTAL_ROWS + 1, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 2.0, TOTAL_ROWS + 1, dtype=np.float32),
    }


def _calc_song(note_count: int = 160) -> dict:
    timestamps = np.linspace(0.0, 60.0, int(note_count), dtype=np.float32)
    return {
        "metadata": {
            "Song Name": "certificate_test",
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]) if int(timestamps.shape[0]) else 0.0,
        },
        "song_data": {"timestamps": timestamps, "fg_timestamps": timestamps},
    }


def test_certified_fg_upper_bound_dominates_exact_response_inner_score():
    base_stats = {
        "Perfect Points": 20,
        "Combo Multiplier": 30,
        "Fever Multiplier": 40,
        "Fever Time": 10,
        "Fever Fill Rate": 10,
        "Rush": 50,
        "Flow": 35,
    }
    calc_song = _calc_song()
    ref_arrays = _ref_arrays()
    stats_after_ftff = {
        **base_stats,
        "Fever Time": base_stats["Fever Time"] + (5 * GEM_SCALE_FEVER),
        "Fever Fill Rate": base_stats["Fever Fill Rate"] + (7 * GEM_SCALE_FEVER),
    }
    surface = FgResponseSurface(
        0b101011,
        0,
        0,
        0,
        0b001001,
        0,
        0,
        0,
        22,
        3,
    )

    exact = optimize_response_frontier_inner_exact(
        [surface],
        total_notes=160,
        residual_budget=78,
        stats_after_ftff=stats_after_ftff,
        primary_color="Rush",
        secondary_color="Flow",
        selected_color="Rush",
        ref_arrays=ref_arrays,
    )
    upper = certified_fg_candidate_upper_bound(
        base_stats,
        calc_song,
        ref_arrays,
        selected_color="Rush",
    )

    assert int(exact.best_score) <= int(upper)


def test_response_frontier_plan_prunes_only_by_certificate(monkeypatch):
    seen: dict[str, list[dict]] = {}

    low = {"id": "low", "base_score": 1000, "stats": {"Rush": 1}}
    high = {"id": "high", "base_score": 100, "stats": {"Rush": 2}}

    monkeypatch.setattr(response_frontier_adapter, "eval_data_from_entry", lambda entry, _primary: entry)
    monkeypatch.setattr(response_frontier_adapter, "expected_selected_element", lambda _entry, _primary: "Rush")
    monkeypatch.setattr(
        response_frontier_adapter,
        "_base_stats_for_response_frontier",
        lambda eval_data, *, selected: dict(eval_data["stats"]),
    )
    monkeypatch.setattr(response_frontier_adapter, "entry_base_score", lambda entry: int(entry["base_score"]))
    monkeypatch.setattr(
        response_frontier_adapter,
        "certified_fg_candidate_upper_bound",
        lambda base_stats, *_args, **_kwargs: 1000 if int(base_stats["Rush"]) == 1 else 2000,
    )

    def _prepare_batch(*, base_stats_list, **_kwargs):
        seen["base_stats_list"] = list(base_stats_list)
        return "prepared-batch"

    monkeypatch.setattr(
        response_frontier_adapter,
        "prepare_force_greats_response_frontier_scoring_batch",
        _prepare_batch,
    )

    plan = response_frontier_adapter.prepare_force_greats_response_frontier_plan(
        {"low": low, "high": high},
        _calc_song(),
        _ref_arrays(),
        "Rush",
    )

    assert seen["base_stats_list"] == [{"Rush": 2}]
    assert len(plan.pending_jobs) == 1
    assert plan.pending_jobs[0][0] is high
    assert plan.certificate_lower_bound == 1000
    assert plan.certified_pruned_jobs == 1
    assert plan.certified_pruned_unique == 1
    assert plan.certificate_max_pruned_upper_bound == 1000
    assert plan.certificate_max_kept_upper_bound == 2000
