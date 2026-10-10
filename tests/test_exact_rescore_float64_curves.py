from tests.curves_support import synthetic_curves
from tests.songs_support import make_song
import numpy as np


def _mock_song(*, name: str, n_notes: int = 96, duration: float = 120.0):
    return make_song(
        np.linspace(0.0, float(duration), int(n_notes)),
        name=name,
        lanes=np.arange(int(n_notes), dtype=np.int32) % np.int32(4),
    )


def _curves(rows: int, *, dtype):
    return synthetic_curves({
        "Perfect Points": np.linspace(1.0, 2.0, rows, dtype=dtype),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=dtype),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=dtype),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=dtype) * 0.333,
        "Fever Time": np.linspace(1.0, 2.5, rows, dtype=dtype) * 0.15,
    })


def _float32_rounded(curves):
    """The same curves after a round trip through float32 (their f64 is the widened f32)."""
    from gear_optimizer.gamedata import StatCurves

    return StatCurves.from_mapping(curves.f32)


def _boundary_drift_stats() -> dict[str, int]:
    return {
        "Perfect Points": 0,
        "Combo Multiplier": 84,
        "Fever Multiplier": 103,
        "Fever Fill Rate": 85,
        "Fever Time": 93,
        "Rush": 144,
        "Flow": 111,
        "Beat": 76,
        "Vibe": 101,
        "Chill": 147,
    }


def _prebuild_timeline_frontier(song, curves) -> None:
    from gear_optimizer.solver.taichi_gem.api.timeline import build_or_load_timeline_frontier_payload

    build_or_load_timeline_frontier_payload(song, curves)


def test_score_stats_exact_scores_with_the_float64_curves():
    """Exact scores read curves.f64: rounding the curves to float32 changes this boundary score."""
    from gear_optimizer.rules import MAX_STAT
    from gear_optimizer.solver.scoring import exact_rescore as er

    exact_curves = _curves(MAX_STAT + 1, dtype=np.float64)
    rounded_curves = _float32_rounded(exact_curves)
    stats = _boundary_drift_stats()
    song = _mock_song(name="pytest_exact_rescore_float64_curves")

    _prebuild_timeline_frontier(song, exact_curves)
    exact = int(er.score_stats_exact(stats, song, exact_curves))
    _prebuild_timeline_frontier(song, rounded_curves)
    rounded = int(er.score_stats_exact(stats, song, rounded_curves))
    assert exact != rounded


def test_score_stats_exact_uses_legal_timing_frontier_not_fixed_chart_replay():
    from gear_optimizer.rules import MAX_STAT
    from gear_optimizer.solver.scoring.exact_rescore import (
        score_stats_exact,
        score_stats_exact_with_timeline_trace,
        score_stats_fixed_timing_exact,
    )

    song = _mock_song(name="pytest_timing_frontier_authority", n_notes=101, duration=2.0)
    curves = synthetic_curves({
        "Perfect Points": np.ones(MAX_STAT + 1, dtype=np.float64),
        "Combo Multiplier": np.ones(MAX_STAT + 1, dtype=np.float64) * 2.0,
        "Fever Multiplier": np.ones(MAX_STAT + 1, dtype=np.float64) * 4.0,
        "Fever Fill Rate": np.ones(MAX_STAT + 1, dtype=np.float64) * 0.333,
        "Fever Time": np.ones(MAX_STAT + 1, dtype=np.float64) * 0.15,
    })
    stats = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 100,
        "Flow": 50,
    }

    _prebuild_timeline_frontier(song, curves)
    # The fixed chart-time replay (deterministic chart timeline) scores strictly below the
    # legal Perfect-window timing frontier. stats -> base_value 251.0 (Rush 100*2 + Flow 50 +
    # PP factor 1.0), combo 2.0, fever 4.0, FT/FF idx 0 -- exactly the fixed-chart inputs.
    fixed_chart = score_stats_fixed_timing_exact(stats, song, curves)
    assert int(fixed_chart) == 79568
    # The legal Perfect-window timing frontier scores strictly higher than the fixed chart replay: its optimum ends
    # the first fever early (activation at its earliest Perfect hit), so the second one starts sooner.
    assert int(fixed_chart) < int(score_stats_exact(stats, song, curves)) == 80336
    replay = score_stats_exact_with_timeline_trace(stats, song, curves)
    assert int(replay["score"]) == 80336
    trace = replay["TimelineFrontier"]["frontier_trace"]
    assert trace
    assert all(row["activation_judgment"] == "perfect" for row in trace)
    assert any(float(row["activation_hit_offset_ms"]) != 0.0 for row in trace)


def test_team_buff_tier_replay_scores_with_the_float64_curves(monkeypatch):
    """The tier replay's exact base scores read curves.f64 too (same boundary case as above)."""
    from gear_optimizer.rules import MAX_STAT
    from gear_optimizer.helpers.song_helpers import team_buff_tiers as tbt
    from tests.test_team_buff_tier_postprocess import _install_synthetic_tier_resolve

    stats = _boundary_drift_stats()
    entry = {
        "score": 1,
        "fg_score": 0,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {"Stats": stats},
        "force": None,
    }

    def tier_score(curves, song_name: str) -> int:
        # The per-tier base re-solve needs 6 gear + 3 mini stat-dicts and a GPU gem search; the
        # synthetic resolve replaces it with a CPU-exact witness whose final step is
        # score_stats_exact_batch, the function whose precision this test pins.
        song = _mock_song(name=song_name)
        _prebuild_timeline_frontier(song, curves)
        _install_synthetic_tier_resolve(monkeypatch, song=song, curves=curves)
        result = tbt.compute_team_buff_tier_leaderboards(entries=[entry], song=song, curves=curves, tiers=("NONE",))
        return int(result["tiers"]["NONE"]["base_top51"][0]["score"])

    exact_curves = _curves(MAX_STAT + 1, dtype=np.float64)
    assert tier_score(exact_curves, "pytest_team_buff_float64") != tier_score(
        _float32_rounded(exact_curves), "pytest_team_buff_float32_rounded"
    )
