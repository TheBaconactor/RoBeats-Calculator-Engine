"""Custom per-note baseline timing on the FG (force-greats) path (generalizes zero_ms). GPU.

The FG response-frontier search consumes the song's hit timeline, which
``time_song(chart, "zero_ms", baseline_offset=T)`` sets to ``chart + T``. These GPU
tests pin:
- an all-zero ``T`` reproduces the plain ``zero_ms`` surface bit-for-bit (the FG-path T==0 gate
  through the new param); and
- a non-zero per-note ``T`` re-optimizes to a VALID surface, exactly scored under ``chart + T``.

"""

from __future__ import annotations

import numpy as np
import pytest
from tests.curves_support import synthetic_curves
from tests.songs_support import make_chart
from tests.items_support import make_gear, make_song_mini

pytestmark = pytest.mark.gpu


def _reset_fg_cache() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
        reset_fg_response_frontier_payload_cache,
    )

    reset_fg_response_frontier_payload_cache()


def _inside_float32(values, box_max: float):
    """Clip the top value so its float32 rounding (what the dominance box reads) stays inside the box."""
    top = np.float32(box_max)
    if float(top) > box_max:
        top = np.nextafter(top, np.float32(0.0))
    return np.minimum(values, float(top))


def _curves(rows: int = 161) -> dict:
    return synthetic_curves({
        "Perfect Points": np.linspace(0.0, 10.0, rows, dtype=np.float64),
        "Combo Multiplier": _inside_float32(np.linspace(1.95, 2.72, rows, dtype=np.float64), 2.72),
        "Fever Multiplier": _inside_float32(np.linspace(2.95, 5.48, rows, dtype=np.float64), 5.48),
        "Fever Fill Rate": np.full(rows, 0.5, dtype=np.float64),
        "Fever Time": np.full(rows, 0.5, dtype=np.float64),
    })


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


def _song(baseline_offset=None):
    from gear_optimizer.solver.timing_envelope import time_song

    return time_song(make_chart(_TIMESTAMPS, name="pytest_custom_timing_fg"), "zero_ms", baseline_offset)


def test_zero_offset_matches_plain_zero_ms_surface(tmp_path, monkeypatch):
    """An all-zero baseline offset reproduces the plain zero_ms FG surface bit-for-bit."""
    from gear_optimizer.solver.fg_response_scoring.fixed_timing import _solve_fixed_timing_response_results

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path / "fg_cache"))
    curves = _curves()
    stats = _fg_stats()

    _reset_fg_cache()
    surf_plain = _solve_fixed_timing_response_results([stats], _song(), curves, "Chill")[0].surface

    _reset_fg_cache()
    song_zero_t = _song(np.zeros(9, dtype=np.float32))
    surf_zero_t = _solve_fixed_timing_response_results([stats], song_zero_t, curves, "Chill")[0].surface

    assert tuple(surf_zero_t) == tuple(surf_plain)


def test_nonzero_baseline_offset_reoptimizes_to_valid_surface(tmp_path, monkeypatch):
    """A non-zero per-note baseline T yields a valid surface, scored exactly under chart + T."""
    from gear_optimizer.solver.fg_response_scoring.fixed_timing import _solve_fixed_timing_response_results
    from gear_optimizer.solver.scoring.exact_rescore import score_force_greats_response_surface_exact

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path / "fg_cache"))
    curves = _curves()
    stats = _fg_stats()

    _reset_fg_cache()
    # Per-note offsets that keep the hit timeline sorted (large gaps in this sparse song).
    offset = np.asarray([0.0, 0.03, 0.0, 0.05, 0.0, 0.04, 0.0, 0.02, 0.0], dtype=np.float32)
    song_t = _song(offset)

    # The FG search reads the shifted hit timeline.
    np.testing.assert_allclose(song_t.fg_inputs.timestamps, _TIMESTAMPS + offset, atol=1e-6)
    surf_t = _solve_fixed_timing_response_results([stats], song_t, curves, "Chill")[0].surface
    score_t = score_force_greats_response_surface_exact(stats, song_t, curves, surf_t)
    assert int(score_t) > 0


def test_leaderboard_under_nonzero_baseline_offset_is_valid(tmp_path, monkeypatch):
    """End-to-end: a non-zero baseline T produces valid per-tier meta + FG leaderboards
    (replay AND optimize -- gems/greats re-solved, scores exact under chart + T)."""
    from gear_optimizer.rules import MAX_STAT
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import compute_team_buff_tier_leaderboards
    from gear_optimizer.solver.taichi_gem.api.timeline import build_or_load_timeline_frontier_payload

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path / "fg_cache"))
    _reset_fg_cache()
    curves = _curves(MAX_STAT + 1)
    offset = np.asarray([0.0, 0.03, 0.0, 0.05, 0.0, 0.04, 0.0, 0.02, 0.0], dtype=np.float32)
    song = _song(offset)

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
            make_gear(
                "G1",
                **{
                    "Perfect Points": 120,
                    "Combo Multiplier": 80,
                    "Fever Multiplier": 60,
                    "Fever Time": 80,
                    "Fever Fill Rate": 100,
                    "Rush": 200,
                    "Flow": 150,
                },
            ),
            *(make_gear(f"G{i}") for i in range(2, 7)),
        ],
        # Minis already as the song sees them (zero stats), so the pre-gem row is just the gear sum.
        "minis": [make_song_mini(f"M{i}") for i in range(1, 4)],
        "details": {"Stats": stats},
        "force": {
            "Stats": stats,
            "ForceGreats": {"config": {"NonFever1": 1}},
            "response_surface": [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
        },
    }

    # Prebuild the candidate-independent timeline-frontier cache for this prepared (chart + T)
    # song, mirroring the on-demand path (the base gem re-solve needs it).
    build_or_load_timeline_frontier_payload(song, curves)

    out = compute_team_buff_tier_leaderboards(
        entries=[entry],
        song=song,
        curves=curves,
    )

    tiers = out["tiers"]
    assert tiers, "custom-T tier replay produced no tiers"
    for tier_name, tier in tiers.items():
        assert tier["base_top51"], f"no base leaderboard for {tier_name}"
        assert int(tier["base_top51"][0]["score"]) > 0
        assert tier["fg_top51"], f"no FG leaderboard for {tier_name}"
        assert int(tier["fg_top51"][0]["fg_score"]) > 0
