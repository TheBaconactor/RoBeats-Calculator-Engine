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


def _loadout_items(name: str, **stats: int) -> list[dict]:
    gear = [{"Name": f"{name}-G1", **stats}]
    gear.extend({"Name": f"{name}-G{i}"} for i in range(2, 7))
    minis = [{"Name": f"{name}-M{i}"} for i in range(1, 4)]
    return gear + minis


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
        "song_data": {
            "timestamps": timestamps,
            # The production physical-replay contract owns chart note types and lanes even
            # though fixed chart-time timeline scoring itself does not consume either array.
            "note_types": np.ones(timestamps.shape[0], dtype=np.int16),
            "lanes": np.arange(timestamps.shape[0], dtype=np.int32) % 4,
        },
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
    # zero_ms re-solves the gem allocation from gear/mini item stats, not from already allocated Stats.
    # With the minimal cfg here, song fixed stats are zero, so the pre-gem row is just the item sum.
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


def test_zero_ms_batch_resolves_match_single_loadout_paths(tmp_path, monkeypatch):
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.core.utils import cfg_from_dict
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import (
        build_team_buff_tier_db_batches,
        resolve_tier_base,
        resolve_tier_base_batch,
        resolve_tier_fg_force,
        resolve_tier_fg_force_batch,
    )
    from gear_optimizer.solver.scoring.exact_rescore import score_stats_fixed_timing_exact
    from gear_optimizer.solver.taichi_gem.api.timeline import build_or_load_timeline_frontier_payload
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path / "fg_cache"))
    _reset_fg_cache()

    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)
    timestamps = np.asarray([0.0, 0.2, 0.5, 1.0, 1.2, 2.0, 3.4, 3.5, 3.6], dtype=np.float32)
    calc_song = {
        "metadata": {
            "Song Name": "pytest_zero_ms_batch_parity",
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
        },
        "song_data": {"timestamps": timestamps},
    }
    apply_timing_envelope(calc_song, mode="zero_ms")
    build_or_load_timeline_frontier_payload(calc_song, ref_arrays)

    cfg = cfg_from_dict({"TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"}})
    fixed_song_stats = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Time": 0,
        "Fever Fill Rate": 0,
        "Rush": 0,
        "Flow": 0,
        "Chill": 0,
        "Beat": 0,
        "Vibe": 0,
    }
    loadouts = [
        _loadout_items(
            "A",
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
        _loadout_items(
            "B",
            **{
                "Perfect Points": 100,
                "Combo Multiplier": 95,
                "Fever Multiplier": 50,
                "Fever Time": 90,
                "Fever Fill Rate": 75,
                "Rush": 180,
                "Flow": 170,
            },
        ),
    ]

    base_singles = [
        resolve_tier_base(
            cfg=cfg,
            fixed_song_stats=fixed_song_stats,
            loadout_items=loadout,
            calc_song=dict(calc_song),
            ref_arrays=ref_arrays,
            primary_color="Rush",
            secondary_color="Flow",
            selected_color="Rush",
        )
        for loadout in loadouts
    ]
    base_batch = resolve_tier_base_batch(
        cfg=cfg,
        fixed_song_stats=fixed_song_stats,
        loadouts=loadouts,
        calc_song=dict(calc_song),
        ref_arrays=ref_arrays,
        primary_color="Rush",
        secondary_color="Flow",
        selected_color="Rush",
    )

    assert [score for _payload, score in base_batch] == [score for _payload, score in base_singles]
    for (single_payload, _single_score), (batch_payload, _batch_score) in zip(base_singles, base_batch, strict=True):
        assert batch_payload["GemCounts"] == single_payload["GemCounts"]
        assert batch_payload["Stats"] == single_payload["Stats"]
        assert batch_payload["FT"] == single_payload["FT"]
        assert batch_payload["FF"] == single_payload["FF"]

    fg_singles = [
        resolve_tier_fg_force(
            fixed_song_stats=fixed_song_stats,
            loadout_items=loadout,
            calc_song=dict(calc_song),
            ref_arrays=ref_arrays,
            selected_color="Rush",
        )
        for loadout in loadouts
    ]
    fg_batch = resolve_tier_fg_force_batch(
        fixed_song_stats=fixed_song_stats,
        loadouts=loadouts,
        calc_song=dict(calc_song),
        ref_arrays=ref_arrays,
        selected_color="Rush",
    )

    assert [force["Score"] for force in fg_batch] == [force["Score"] for force in fg_singles]
    for single_force, batch_force in zip(fg_singles, fg_batch, strict=True):
        assert batch_force["GemCounts"] == single_force["GemCounts"]
        assert batch_force["Stats"] == single_force["Stats"]
        assert batch_force["BaseStats"] == single_force["BaseStats"]
        assert batch_force["BaseStats"] == batch_force["Stats"]
        assert batch_force["BaseScore"] == score_stats_fixed_timing_exact(
            batch_force["BaseStats"],
            calc_song,
            ref_arrays,
        )
        assert batch_force["ForceGreats"]["config"] == single_force["ForceGreats"]["config"]
        assert isinstance(batch_force["ForceGreats"].get("frontier_trace"), list)
        assert batch_force["ForceGreats"]["frontier_trace"] == single_force["ForceGreats"]["frontier_trace"]

    entry = {
        "loadout_hash": "pytest-zero-ms-fg-witness",
        "score": 1,
        "fg_score": 1,
        "gear": loadouts[0][:6],
        "minis": loadouts[0][6:],
        "details": {"Stats": dict(fg_singles[0]["Stats"])},
        "force": dict(fg_singles[0]),
    }
    batches = build_team_buff_tier_db_batches(
        entries=[entry],
        calc_song=dict(calc_song),
        ref_arrays=ref_arrays,
        cfg_dict={"TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"}},
        limit=1,
        tiers=("T5",),
        replay_surface="fg",
        timing_mode="zero_ms",
    )
    fg_row = batches["T5"][0]
    assert fg_row["fg_base_score"] == fg_row["force"]["BaseScore"]
    assert fg_row["force"]["BaseStats"] == fg_row["force"]["Stats"]
    assert fg_row["fg_base_score"] == score_stats_fixed_timing_exact(
        fg_row["force"]["BaseStats"],
        calc_song,
        ref_arrays,
    )
