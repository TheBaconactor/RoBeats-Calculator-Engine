from __future__ import annotations

import numpy as np


def _ref_arrays() -> dict[str, np.ndarray]:
    return {
        "Perfect Points": np.ones(161, dtype=np.float64),
        "Combo Multiplier": np.ones(161, dtype=np.float64),
        "Fever Multiplier": np.ones(161, dtype=np.float64),
        "Fever Fill Rate": np.ones(161, dtype=np.float64),
        "Fever Time": np.ones(161, dtype=np.float64),
    }


def _entry(loadout_hash: str) -> dict:
    stats = {
        "Perfect Points": 25,
        "Combo Multiplier": 50,
        "Fever Multiplier": 50,
        "Fever Fill Rate": 50,
        "Fever Time": 50,
        "Beat": 100,
        "Flow": 0,
    }
    return {
        "loadout_hash": loadout_hash,
        "score": 1,
        "fg_score": 2,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {"Stats": stats},
        "force": {
            "Stats": stats,
            "BaseStats": stats,
            "response_surface": [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
            "ForceGreats": {"config": {"NonFever1": 1}},
        },
    }


def test_zero_ms_fg_leaderboard_uses_force_witness_base_score(monkeypatch):
    from gear_optimizer.helpers.song_helpers import team_buff_tiers

    def fake_resolve_fg_force_for_loadouts(**kwargs):
        rows = list(kwargs["entries"])
        return [
            {
                "Score": 100,
                "BaseScore": 100,
                "Stats": {"Perfect Points": 25, "Beat": 100},
                "BaseStats": {"Perfect Points": 25, "Beat": 100},
                "ForceGreats": {"config": {"NonFever1": 0, "NonFever2": 0}},
            },
            {
                "Score": 90,
                "BaseScore": 80,
                "Stats": {"Perfect Points": 25, "Beat": 90},
                "BaseStats": {"Perfect Points": 25, "Beat": 90},
                "ForceGreats": {"config": {"NonFever1": 3}},
            },
        ][: len(rows)]

    def fail_if_old_persisted_snapshot_base_is_used(*_args, **_kwargs):
        raise AssertionError("zero_ms FG must use the resolved force witness BaseScore")

    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.fg_exact_resolve.resolve_fg_force_for_loadouts",
        fake_resolve_fg_force_for_loadouts,
    )
    monkeypatch.setattr(
        "gear_optimizer.solver.scoring.exact_rescore.score_stats_fixed_timing_exact_batch",
        fail_if_old_persisted_snapshot_base_is_used,
    )
    monkeypatch.setattr(
        "gear_optimizer.data.csv_parser.get_fixed_stats",
        lambda _cfg: {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Fever Fill Rate": 0,
            "Fever Time": 0,
            "Beat": 0,
            "Flow": 0,
        },
    )
    monkeypatch.setattr(
        "gear_optimizer.helpers.song_helpers.song_config.apply_baseline_team_buff_config",
        lambda _cfg, _calc_song: None,
    )

    out = team_buff_tiers.compute_team_buff_tier_leaderboards(
        entries=[_entry("noop"), _entry("real-fg")],
        calc_song={
            "metadata": {
                "Song Name": "pytest_zero_ms_fg_base_pairing",
                "Difficulty": "Hard",
                "Primary Color": "Beat",
                "Secondary Color": "Flow",
                "Long Notes": 0,
                "Last Note Time": 1.0,
                "Total Notes": 2,
            },
            "song_data": {"timestamps": np.array([0.0, 1.0]), "note_types": np.ones(2, dtype=np.int16)},
        },
        ref_arrays=_ref_arrays(),
        cfg_dict={"TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Beat"}},
        limit=2,
        tiers=("T5",),
        replay_surfaces=("fg",),
        timing_mode="zero_ms",
    )

    fg_rows = out["tiers"]["T5"]["fg_top51"]
    assert fg_rows == [
        {
            "loadout_hash": "real-fg",
            "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
            "minis": ["M1", "M2", "M3"],
            "fg_score": 90,
            "source_score": 1,
            "source_fg_base_score": 1,
            "source_fg_score": 2,
            "force_config": {"NonFever1": 1},
            "fg_base_score": 80,
        }
    ]
