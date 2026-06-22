"""Fixed-timing (0ms) FG re-optimization + tier replay (issue #51). GPU.

Pins the two GPU-facing facts:
- the re-optimized 0ms FG surface (canonical builder on a chart-only calc_song) equals the
  brute-force forced-counts optimum (EXACT), and that optimum can EXCEED base 0ms -- forcing
  greats still helps at 0ms because it changes the fill length and shifts where fever activates
  (a count effect independent of hit-offset), so FG 0ms is NOT base 0ms and the surface must be
  rebuilt (guards against a wrong "FG 0ms == base 0ms" short-circuit); and
- a tier replay run produces per-tier top-N meta + FG leaderboards under timing_mode="zero_ms".
"""

from __future__ import annotations

import itertools

import numpy as np
import pytest

pytestmark = pytest.mark.gpu


def _reset_fg_cache() -> None:
    # The bundle memory cache is process-global and keyed by song timing/ref, not by the
    # per-test FG_RESPONSE_FRONTIER_CACHE_DIR. Reset it so each test rebuilds against its own
    # tmp cache dir (otherwise a sibling test's in-memory bundle points at a stale sidecar path).
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
        reset_fg_response_frontier_payload_cache,
    )

    reset_fg_response_frontier_payload_cache()


# combo/fever multipliers within the lossless head-dominance prune box (real game ranges).
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


def test_fixed_timing_fg_surface_matches_bruteforce_and_beats_base(tmp_path, monkeypatch):
    """The re-optimized 0ms surface == brute-force forced-counts optimum, and exceeds base 0ms."""
    from gear_optimizer.solver.scoring.exact_rescore import (
        evaluate_force_greats_exact,
        score_force_greats_response_surface_exact,
        score_stats_fixed_timing_exact,
    )
    from gear_optimizer.solver.fg_response_scoring.fixed_timing import build_fixed_timing_response_surfaces
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path / "fg_cache"))
    _reset_fg_cache()
    ref_arrays = _ref_arrays()
    # Sparse, irregular timing so forcing greats can re-align a fever window with a note cluster.
    timestamps = np.asarray([0.0, 0.2, 0.5, 1.0, 1.2, 2.0, 3.4, 3.5, 3.6], dtype=np.float32)

    def _song() -> dict:
        return {
            "metadata": {
                "Song Name": "pytest_zero_ms_fg",
                "Difficulty": "Hard",
                "Primary Color": "Rush",
                "Secondary Color": "Flow",
                "Long Notes": 0,
                "Last Note Time": float(timestamps[-1]),
            },
            "song_data": {"timestamps": timestamps},
        }

    stats = _fg_stats()
    base_0ms = score_stats_fixed_timing_exact(stats, _song(), ref_arrays)

    # Brute-force the 0ms forced-counts optimum on the chart-only song.
    zero = evaluate_force_greats_exact(stats, _song(), ref_arrays, [0] * 10)
    sections = int(zero["num_non_fever_sections"])
    cap = int(zero["non_fever_base"])
    best = -1
    for counts in itertools.product(range(cap + 1), repeat=sections):
        best = max(best, int(evaluate_force_greats_exact(stats, _song(), ref_arrays, counts)["final_score"]))

    # Re-optimized 0ms surface via the canonical builder on a zero_ms calc_song.
    cs_zero = _song()
    apply_timing_envelope(cs_zero, mode="zero_ms")
    surfaces = build_fixed_timing_response_surfaces([stats], cs_zero, ref_arrays, "Chill")
    assert len(surfaces) == 1
    surface_score = score_force_greats_response_surface_exact(stats, cs_zero, ref_arrays, surfaces[0])

    assert surface_score == best  # builder is exact vs the brute-force forced-counts optimum
    assert best > base_0ms  # forcing greats genuinely helps at 0ms -> FG 0ms is NOT base 0ms


def test_zero_ms_tier_replay_produces_meta_and_fg_leaderboards(tmp_path, monkeypatch):
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import compute_team_buff_tier_leaderboards

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path / "fg_cache"))
    _reset_fg_cache()
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)
    timestamps = np.asarray([0.0, 0.2, 0.5, 1.0, 1.2, 2.0, 3.4, 3.5, 3.6], dtype=np.float32)
    calc_song = {
        "metadata": {
            "Song Name": "pytest_zero_ms_tier",
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
        },
        "song_data": {"timestamps": timestamps},
    }
    # Persisted surface is head-only valid for a <100-note song; under zero_ms it is REBUILT,
    # so its exact value is irrelevant -- it only has to pass the require_response_surface guard.
    surface_fixture = [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]
    # Large element/PP values so tier deltas never drive the stats (or base value) negative.
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
    # zero_ms now RE-SOLVES the gem allocation, so gear/minis must be the genome (stat-dicts,
    # no gems) -- the gem-less identity the search re-allocates 90 gems onto. The loadout's stats
    # live in the genome; fixed_stats from the minimal cfg is ~0, so gem-less base == genome sum.
    entry = {
        "loadout_hash": "pytest_zero_ms_loadout",
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
            "response_surface": surface_fixture,
        },
    }

    # zero_ms now re-solves the BASE gems too (GPU exhaustive search), which needs the
    # candidate-independent timeline-frontier cache built first -- mirror the on-demand path.
    from gear_optimizer.solver.taichi_gem.api.timeline import build_or_load_timeline_frontier_payload
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    _cs_zero_ms = dict(calc_song)
    apply_timing_envelope(_cs_zero_ms, mode="zero_ms")
    build_or_load_timeline_frontier_payload(_cs_zero_ms, ref_arrays)

    out = compute_team_buff_tier_leaderboards(
        entries=[entry],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        cfg_dict={"TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"}},
        timing_mode="zero_ms",
    )

    tiers = out["tiers"]
    assert tiers, "tier replay produced no tiers"
    for tier_name, tier in tiers.items():
        assert tier["base_top51"], f"no base leaderboard for {tier_name}"
        assert int(tier["base_top51"][0]["score"]) > 0
        assert tier["fg_top51"], f"no FG leaderboard for {tier_name}"
        assert int(tier["fg_top51"][0]["fg_score"]) > 0
