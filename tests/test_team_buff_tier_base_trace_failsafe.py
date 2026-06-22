"""Fail-safe for the per-tier base TimelineFrontier (issue #38, base surface).

`_apply_details_delta` copies the baseline (T5) details verbatim except Stats, so a
tier-shifted row inherits the *baseline* TimelineFrontier — a per-note trace that is wrong
for the shifted tier. The postprocess must drop that inherited trace and only ever emit a
TimelineFrontier produced by a fresh per-tier exact recompute. If the recompute cannot
produce one, the row must carry no TimelineFrontier (so the consumer omits the graph)
rather than the stale baseline witness — never another tier's timing.

These tests mock both the leaderboard compute and the exact recompute, so they are pure
CPU unit tests (no Vulkan/GPU, no timeline prebuild).
"""

from __future__ import annotations

from unittest.mock import patch

import numpy as np


def _mock_song(name: str = "failsafe", n_notes: int = 12, duration: float = 10.0) -> dict:
    timestamps = np.linspace(0.0, float(duration), int(n_notes), dtype=np.float32)
    return {
        "metadata": {
            "Song Name": name,
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
            "Total Notes": int(timestamps.shape[0]),
        },
        "song_data": {
            "timestamps": timestamps,
            "note_types": np.ones(int(timestamps.shape[0]), dtype=np.int16),
        },
    }


def _ref_arrays(rows: int = 11) -> dict:
    keys = ("Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Fill Rate", "Fever Time")
    return {k: np.ones(rows, dtype=np.float64) for k in keys}


_STATS = {
    "Perfect Points": 100,
    "Combo Multiplier": 0,
    "Fever Multiplier": 0,
    "Fever Fill Rate": 0,
    "Fever Time": 0,
    "Rush": 150,
    "Flow": 0,
    "Beat": 0,
    "Vibe": 0,
    "Chill": 0,
}
# A baseline trace that `_apply_details_delta` would carry over onto the shifted tier.
_STALE_TRACE = {"frontier_trace": [{"section": 0, "stale": True}], "fever_duration_ms": 999}


def _entry() -> dict:
    return {
        "loadout_hash": "hash-x",
        "score": 100,
        "fg_score": 0,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {"Stats": dict(_STATS), "TimelineFrontier": dict(_STALE_TRACE)},
        "force": None,
    }


def _fake_leaderboards(**_kwargs) -> dict:
    return {
        "meta": {"base_team_buff": "T5", "team_color": "Rush", "primary_color": "Rush", "secondary_color": "Flow"},
        "tiers": {
            "T10": {
                "base_top51": [
                    {
                        "loadout_hash": "hash-x",
                        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
                        "minis": ["M1", "M2", "M3"],
                        "score": 200,
                        "fg_score": 0,
                    }
                ],
                "fg_top51": [],
            }
        },
        # The base-witness graft fails loud unless every hashed (tier, loadout) carries its
        # re-solved witness. The witness Stats are non-empty so the per-tier TimelineFrontier
        # recompute runs (it is what these tests assert on, via the mocked recompute) and its
        # gem counts are legal (FT + FF + PP + CM + FM + Element == 90).
        "resolved_base_by_tier_hash": {
            "T10": {
                "hash-x": {
                    "Stats": dict(_STATS),
                    "GemCounts": {
                        "Perfect Points": 30,
                        "Combo Multiplier": 0,
                        "Fever Multiplier": 0,
                        "Element": 50,
                    },
                    "FT": 5,
                    "FF": 5,
                    "Score": 200,
                    "Selected Element": "Rush",
                }
            }
        },
    }


_CFG = {"TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"}}


def test_failed_per_tier_recompute_drops_stale_baseline_timeline_frontier() -> None:
    from gear_optimizer.helpers.song_helpers import team_buff_tiers as tbt

    with patch.object(tbt, "compute_team_buff_tier_leaderboards", _fake_leaderboards), patch(
        "gear_optimizer.solver.scoring.exact_rescore.score_stats_exact_with_timeline_trace",
        return_value={},  # recompute produced no TimelineFrontier
    ):
        batches = tbt.build_team_buff_tier_db_batches(
            entries=[_entry()],
            calc_song=_mock_song(),
            ref_arrays=_ref_arrays(),
            cfg_dict=_CFG,
            tiers=("T10",),
            limit=1,
        )

    row = batches["T10"][0]
    # The inherited baseline trace must be gone — never served as this tier's timing.
    assert "TimelineFrontier" not in (row.get("details") or {})


def test_successful_per_tier_recompute_replaces_baseline_trace() -> None:
    from gear_optimizer.helpers.song_helpers import team_buff_tiers as tbt

    fresh = {"TimelineFrontier": {"frontier_trace": [{"section": 0, "fresh": True}]}}
    with patch.object(tbt, "compute_team_buff_tier_leaderboards", _fake_leaderboards), patch(
        "gear_optimizer.solver.scoring.exact_rescore.score_stats_exact_with_timeline_trace",
        return_value=fresh,
    ):
        batches = tbt.build_team_buff_tier_db_batches(
            entries=[_entry()],
            calc_song=_mock_song(),
            ref_arrays=_ref_arrays(),
            cfg_dict=_CFG,
            tiers=("T10",),
            limit=1,
        )

    trace = ((batches["T10"][0].get("details") or {}).get("TimelineFrontier") or {}).get("frontier_trace") or []
    assert trace and trace[0].get("fresh") is True
    # The stale baseline section must not survive.
    assert not any(sec.get("stale") for sec in trace)
