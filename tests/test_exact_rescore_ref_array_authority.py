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


def test_score_stats_exact_uses_exact_replay_ref_arrays_for_float32_callers(monkeypatch):
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers import ref_array_builder as rab
    from gear_optimizer.solver.scoring import exact_rescore as er

    authoritative = _ref_arrays(TOTAL_ROWS + 1, dtype=np.float64)
    caller_refs = _ref_arrays(TOTAL_ROWS + 1, dtype=np.float32)
    stats = _boundary_drift_stats()
    calc_song = _mock_song(name="pytest_exact_rescore_ref_authority")

    monkeypatch.setattr(er, "resolve_exact_replay_ref_arrays", lambda refs: refs)
    raw_float32 = int(er.score_stats_exact(stats, calc_song, caller_refs))
    expected = int(er.score_stats_exact(stats, calc_song, authoritative))
    assert raw_float32 != expected

    monkeypatch.setattr(rab, "get_exact_replay_ref_arrays_cached", lambda: authoritative)
    monkeypatch.setattr(er, "resolve_exact_replay_ref_arrays", rab.resolve_exact_replay_ref_arrays)
    assert int(er.score_stats_exact(stats, calc_song, caller_refs)) == expected


def test_team_buff_tier_replay_uses_exact_replay_ref_arrays_for_float32_callers(monkeypatch):
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers import ref_array_builder as rab
    from gear_optimizer.helpers.song_helpers import team_buff_tiers as tbt

    authoritative = _ref_arrays(TOTAL_ROWS + 1, dtype=np.float64)
    caller_refs = _ref_arrays(TOTAL_ROWS + 1, dtype=np.float32)
    stats = _boundary_drift_stats()
    cfg_dict = {"TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"}}
    entry = {
        "score": 1,
        "fg_score": 0,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {"Stats": stats},
        "force": None,
    }

    monkeypatch.setattr(tbt, "resolve_exact_replay_ref_arrays", lambda refs: refs)
    raw = tbt.compute_team_buff_tier_leaderboards(
        entries=[entry],
        calc_song=_mock_song(name="pytest_team_buff_float32_raw"),
        ref_arrays=caller_refs,
        cfg_dict=cfg_dict,
        tiers=("T5",),
    )
    raw_score = int(raw["tiers"]["T5"]["base_top51"][0]["score"])

    expected = tbt.compute_team_buff_tier_leaderboards(
        entries=[entry],
        calc_song=_mock_song(name="pytest_team_buff_float64_expected"),
        ref_arrays=authoritative,
        cfg_dict=cfg_dict,
        tiers=("T5",),
    )
    expected_score = int(expected["tiers"]["T5"]["base_top51"][0]["score"])
    assert raw_score != expected_score

    monkeypatch.setattr(rab, "get_exact_replay_ref_arrays_cached", lambda: authoritative)
    monkeypatch.setattr(tbt, "resolve_exact_replay_ref_arrays", rab.resolve_exact_replay_ref_arrays)
    resolved = tbt.compute_team_buff_tier_leaderboards(
        entries=[entry],
        calc_song=_mock_song(name="pytest_team_buff_float32_resolved"),
        ref_arrays=caller_refs,
        cfg_dict=cfg_dict,
        tiers=("T5",),
    )
    assert int(resolved["tiers"]["T5"]["base_top51"][0]["score"]) == expected_score
