"""Custom per-note baseline timing on the FG (force-greats) path (generalizes zero_ms). GPU.

The FG response-frontier search consumes its hit timeline from ``fg_timestamps``, which
``apply_timing_envelope(mode="zero_ms", baseline_offset=T)`` sets to ``chart + T``. These GPU
tests pin:
- an all-zero ``T`` reproduces the plain ``zero_ms`` surface bit-for-bit (the FG-path T==0 gate
  through the new param); and
- a non-zero per-note ``T`` re-optimizes to a VALID surface, exactly scored under ``chart + T``.

See docs/Implementation Records/CUSTOMIZABLE_TIMING_MODE.md.
"""

from __future__ import annotations

import numpy as np
import pytest

pytestmark = pytest.mark.gpu


def _reset_fg_cache() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
        reset_fg_response_frontier_payload_cache,
    )

    reset_fg_response_frontier_payload_cache()


def _ref_arrays(rows: int = 161) -> dict:
    return {
        "Perfect Points": np.linspace(0.0, 10.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(1.95, 2.72, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(2.95, 5.48, rows, dtype=np.float64),
        "Fever Fill Rate": np.full(rows, 0.5, dtype=np.float64),
        "Fever Time": np.full(rows, 0.5, dtype=np.float64),
    }


def _fg_stats() -> dict:
    return {
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


# Sparse, irregular timing so forcing greats can re-align a fever window with a note cluster.
_TIMESTAMPS = np.asarray([0.0, 0.2, 0.5, 1.0, 1.2, 2.0, 3.4, 3.5, 3.6], dtype=np.float32)


def _song() -> dict:
    return {
        "metadata": {
            "Song Name": "pytest_custom_timing_fg",
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(_TIMESTAMPS[-1]),
        },
        "song_data": {"timestamps": _TIMESTAMPS},
    }


def test_zero_offset_matches_plain_zero_ms_surface(tmp_path, monkeypatch):
    """An all-zero baseline offset reproduces the plain zero_ms FG surface bit-for-bit."""
    from gear_optimizer.solver.fg_response_scoring.fixed_timing import build_fixed_timing_response_surfaces
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path / "fg_cache"))
    ref_arrays = _ref_arrays()
    stats = _fg_stats()

    _reset_fg_cache()
    cs_plain = _song()
    apply_timing_envelope(cs_plain, mode="zero_ms")
    surf_plain = build_fixed_timing_response_surfaces([stats], cs_plain, ref_arrays, "Chill")[0]

    _reset_fg_cache()
    cs_zero_t = _song()
    apply_timing_envelope(cs_zero_t, mode="zero_ms", baseline_offset=np.zeros(9, dtype=np.float32))
    surf_zero_t = build_fixed_timing_response_surfaces([stats], cs_zero_t, ref_arrays, "Chill")[0]

    assert tuple(surf_zero_t) == tuple(surf_plain)


def test_nonzero_baseline_offset_reoptimizes_to_valid_surface(tmp_path, monkeypatch):
    """A non-zero per-note baseline T yields a valid surface, scored exactly under chart + T."""
    from gear_optimizer.solver.fg_response_scoring.fixed_timing import build_fixed_timing_response_surfaces
    from gear_optimizer.solver.scoring.exact_rescore import score_force_greats_response_surface_exact
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path / "fg_cache"))
    ref_arrays = _ref_arrays()
    stats = _fg_stats()

    _reset_fg_cache()
    cs_t = _song()
    # Per-note offsets that keep the hit timeline sorted (large gaps in this sparse song).
    offset = np.asarray([0.0, 0.03, 0.0, 0.05, 0.0, 0.04, 0.0, 0.02, 0.0], dtype=np.float32)
    apply_timing_envelope(cs_t, mode="zero_ms", baseline_offset=offset)

    # The FG search read the shifted hit timeline.
    np.testing.assert_allclose(
        np.asarray(cs_t["song_data"]["fg_timestamps"]), _TIMESTAMPS + offset, atol=1e-6
    )
    surf_t = build_fixed_timing_response_surfaces([stats], cs_t, ref_arrays, "Chill")[0]
    score_t = score_force_greats_response_surface_exact(stats, cs_t, ref_arrays, surf_t)
    assert int(score_t) > 0


def test_leaderboard_under_nonzero_baseline_offset_is_valid(tmp_path, monkeypatch):
    """End-to-end: a non-zero baseline T produces valid per-tier meta + FG leaderboards
    (replay AND optimize -- gems/greats re-solved, scores exact under chart + T)."""
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import compute_team_buff_tier_leaderboards
    from gear_optimizer.solver.taichi_gem.api.timeline import build_or_load_timeline_frontier_payload
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path / "fg_cache"))
    _reset_fg_cache()
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)
    calc_song = _song()
    offset = np.asarray([0.0, 0.03, 0.0, 0.05, 0.0, 0.04, 0.0, 0.02, 0.0], dtype=np.float32)

    stats = {
        "Perfect Points": 120,
        "Combo Multiplier": 80,
        "Fever Multiplier": 60,
        "Fever Time": 80,
        "Fever Fill Rate": 100,
        "Rush": 200,
        "Flow": 150,
        "Chill": 0,
        "Beat": 0,
        "Vibe": 0,
    }
    entry = {
        "loadout_hash": "pytest_custom_t_loadout",
        "score": 1,
        "fg_score": 1,
        "gear": [
            {
                "Name": "G1",
                "Perfect Points": 120,
                "Combo Multiplier": 80,
                "Fever Multiplier": 60,
                "Fever Time": 80,
                "Fever Fill Rate": 100,
                "Rush": 200,
                "Flow": 150,
            },
            {"Name": "G2"},
            {"Name": "G3"},
            {"Name": "G4"},
            {"Name": "G5"},
            {"Name": "G6"},
        ],
        "minis": [{"Name": "M1"}, {"Name": "M2"}, {"Name": "M3"}],
        "details": {"Stats": stats},
        "force": {
            "Stats": stats,
            "ForceGreats": {"config": {"NonFever1": 1}},
            "response_surface": [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
        },
    }

    # Prebuild the candidate-independent timeline-frontier cache for this prepared (chart + T)
    # song, mirroring the on-demand path (the base gem re-solve needs it).
    _pre = dict(calc_song)
    apply_timing_envelope(_pre, mode="zero_ms", baseline_offset=offset)
    build_or_load_timeline_frontier_payload(_pre, ref_arrays)

    out = compute_team_buff_tier_leaderboards(
        entries=[entry],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict={"TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"}},
        timing_mode="zero_ms",
        baseline_offset=offset,
    )

    tiers = out["tiers"]
    assert tiers, "custom-T tier replay produced no tiers"
    for tier_name, tier in tiers.items():
        assert tier["base_top51"], f"no base leaderboard for {tier_name}"
        assert int(tier["base_top51"][0]["score"]) > 0
        assert tier["fg_top51"], f"no FG leaderboard for {tier_name}"
        assert int(tier["fg_top51"][0]["fg_score"]) > 0
