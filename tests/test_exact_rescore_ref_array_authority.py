import numpy as np


def _mock_song(*, name: str, n_notes: int = 96, duration: float = 120.0) -> dict:
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
        "song_data": {"timestamps": timestamps},
    }


def _ref_arrays(rows: int, *, dtype) -> dict:
    return {
        "Perfect Points": np.linspace(1.0, 2.0, rows, dtype=dtype),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=dtype),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=dtype),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=dtype),
        "Fever Time": np.linspace(1.0, 2.5, rows, dtype=dtype),
    }


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


def _prebuild_timeline_frontier(calc_song: dict, ref_arrays: dict) -> None:
    from gear_optimizer.solver.taichi_gem.api.timeline import build_or_load_timeline_frontier_payload

    build_or_load_timeline_frontier_payload(calc_song, ref_arrays)


def _prebuild_team_buff_timeline_frontier(calc_song: dict, ref_arrays: dict) -> None:
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    apply_timing_envelope(calc_song)
    _prebuild_timeline_frontier(calc_song, ref_arrays)


def test_score_stats_exact_uses_exact_replay_ref_arrays_for_float32_callers(monkeypatch):
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers import ref_array_builder as rab
    from gear_optimizer.solver.scoring import exact_rescore as er

    authoritative = _ref_arrays(TOTAL_ROWS + 1, dtype=np.float64)
    caller_refs = _ref_arrays(TOTAL_ROWS + 1, dtype=np.float32)
    stats = _boundary_drift_stats()
    calc_song = _mock_song(name="pytest_exact_rescore_ref_authority")

    monkeypatch.setattr(er, "resolve_exact_replay_ref_arrays", lambda refs: refs)
    _prebuild_timeline_frontier(calc_song, caller_refs)
    raw_float32 = int(er.score_stats_exact(stats, calc_song, caller_refs))
    _prebuild_timeline_frontier(calc_song, authoritative)
    expected = int(er.score_stats_exact(stats, calc_song, authoritative))
    assert raw_float32 != expected

    monkeypatch.setattr(rab, "get_exact_replay_ref_arrays_cached", lambda: authoritative)
    monkeypatch.setattr(er, "resolve_exact_replay_ref_arrays", rab.resolve_exact_replay_ref_arrays)
    assert int(er.score_stats_exact(stats, calc_song, caller_refs)) == expected


def test_score_stats_exact_uses_legal_timing_frontier_not_fixed_chart_replay():
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.solver.scoring.exact_rescore import (
        score_fixed_value_exact,
        score_stats_exact,
        score_stats_exact_with_timeline_trace,
    )

    timestamps = np.linspace(0.0, 2.0, 101, dtype=np.float32)
    calc_song = {
        "metadata": {
            "Song Name": "pytest_timing_frontier_authority",
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
            "Total Notes": int(timestamps.shape[0]),
        },
        "song_data": {"timestamps": timestamps},
    }
    ref_arrays = {
        "Perfect Points": np.ones(TOTAL_ROWS + 1, dtype=np.float64),
        "Combo Multiplier": np.ones(TOTAL_ROWS + 1, dtype=np.float64) * 2.0,
        "Fever Multiplier": np.ones(TOTAL_ROWS + 1, dtype=np.float64) * 4.0,
        "Fever Fill Rate": np.ones(TOTAL_ROWS + 1, dtype=np.float64),
        "Fever Time": np.ones(TOTAL_ROWS + 1, dtype=np.float64),
    }
    stats = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 100,
        "Flow": 50,
    }

    _prebuild_timeline_frontier(calc_song, ref_arrays)
    fixed_chart = score_fixed_value_exact(
        base_value=251.0,
        combo_mul=2.0,
        fever_mul=4.0,
        ft_idx=0,
        ff_idx=0,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
    )
    assert int(fixed_chart) == 79568
    assert int(score_stats_exact(stats, calc_song, ref_arrays)) == 80336
    replay = score_stats_exact_with_timeline_trace(stats, calc_song, ref_arrays)
    assert int(replay["score"]) == 80336
    trace = replay["TimelineFrontier"]["frontier_trace"]
    assert trace
    assert all(row["activation_judgment"] == "perfect" for row in trace)
    assert any(float(row["activation_hit_offset_ms"]) != 0.0 for row in trace)


def test_team_buff_tier_replay_uses_exact_replay_ref_arrays_for_float32_callers(monkeypatch):
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers import ref_array_builder as rab
    from gear_optimizer.helpers.song_helpers import team_buff_tiers as tbt
    from gear_optimizer.solver.scoring import exact_rescore as er
    from tests.test_team_buff_tier_postprocess import _install_synthetic_tier_resolve

    authoritative = _ref_arrays(TOTAL_ROWS + 1, dtype=np.float64)
    caller_refs = _ref_arrays(TOTAL_ROWS + 1, dtype=np.float32)
    stats = _boundary_drift_stats()
    cfg_dict = {"TeamContributionBuffConstant": {"TeamBuff": "NONE", "TeamColor": "Rush"}}
    entry = {
        "score": 1,
        "fg_score": 0,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {"Stats": stats},
        "force": None,
    }

    # The per-tier base re-solve now requires 6 gear + 3 mini stat-dicts and a GPU gem search;
    # the synthetic resolve replaces that GPU search with a deterministic CPU-exact witness whose
    # FINAL scoring step is score_stats_exact_batch -- the exact function under test. It honors the
    # resolved ref_arrays, so the f32-vs-f64 ref-array authority this test pins flows through it.
    monkeypatch.setattr(tbt, "resolve_exact_replay_ref_arrays", lambda refs: refs)
    monkeypatch.setattr(er, "resolve_exact_replay_ref_arrays", lambda refs: refs)
    raw_song = _mock_song(name="pytest_team_buff_float32_raw")
    _prebuild_team_buff_timeline_frontier(raw_song, caller_refs)
    _install_synthetic_tier_resolve(monkeypatch, calc_song=raw_song, ref_arrays=caller_refs)
    raw = tbt.compute_team_buff_tier_leaderboards(
        entries=[entry],
        calc_song=raw_song,
        ref_arrays=caller_refs,
        cfg_dict=cfg_dict,
        tiers=("NONE",),
    )
    raw_score = int(raw["tiers"]["NONE"]["base_top51"][0]["score"])

    expected_song = _mock_song(name="pytest_team_buff_float64_expected")
    _prebuild_team_buff_timeline_frontier(expected_song, authoritative)
    _install_synthetic_tier_resolve(monkeypatch, calc_song=expected_song, ref_arrays=authoritative)
    expected = tbt.compute_team_buff_tier_leaderboards(
        entries=[entry],
        calc_song=expected_song,
        ref_arrays=authoritative,
        cfg_dict=cfg_dict,
        tiers=("NONE",),
    )
    expected_score = int(expected["tiers"]["NONE"]["base_top51"][0]["score"])
    assert raw_score != expected_score

    monkeypatch.setattr(rab, "get_exact_replay_ref_arrays_cached", lambda: authoritative)
    monkeypatch.setattr(tbt, "resolve_exact_replay_ref_arrays", rab.resolve_exact_replay_ref_arrays)
    monkeypatch.setattr(er, "resolve_exact_replay_ref_arrays", rab.resolve_exact_replay_ref_arrays)
    resolved_song = _mock_song(name="pytest_team_buff_float32_resolved")
    _prebuild_team_buff_timeline_frontier(resolved_song, authoritative)
    _install_synthetic_tier_resolve(monkeypatch, calc_song=resolved_song, ref_arrays=authoritative)
    resolved = tbt.compute_team_buff_tier_leaderboards(
        entries=[entry],
        calc_song=resolved_song,
        ref_arrays=caller_refs,
        cfg_dict=cfg_dict,
        tiers=("NONE",),
    )
    assert int(resolved["tiers"]["NONE"]["base_top51"][0]["score"]) == expected_score
