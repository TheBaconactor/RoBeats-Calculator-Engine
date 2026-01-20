import numpy as np


def _mock_song(*, name: str, n_notes: int = 16, duration: float = 60.0) -> dict:
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


def _ref_arrays(rows: int) -> dict:
    # Force a sharp breakpoint on Perfect Points so tier deltas can reorder entries.
    pp = np.zeros(rows, dtype=np.float64)
    pp[110:] = 1000.0
    return {
        "Perfect Points": pp,
        "Combo Multiplier": np.ones(rows, dtype=np.float64),
        "Fever Multiplier": np.ones(rows, dtype=np.float64),
        "Fever Fill Rate": np.ones(rows, dtype=np.float64),
        "Fever Time": np.ones(rows, dtype=np.float64),
    }


def test_team_buff_tier_postprocess_reorders_top_entries_across_tiers():
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.helpers.song_helpers.team_buff_tiers import compute_team_buff_tier_leaderboards

    calc_song = _mock_song(name="pytest_team_buff_tiers", n_notes=12)
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)
    cfg_dict = {"TeamContributionBuffConstant": {"TeamBuff": "T5", "TeamColor": "Rush"}}

    # Stats here are assumed to already include the base TeamBuff=T5.
    # Under T15, PP decreases by 10 vs T5, pushing Entry A below the PP breakpoint
    # while keeping Entry B at/above it, which should flip the ordering.
    stats_a = {
        "Perfect Points": 119,  # T15 => 109 (below breakpoint), T5 => 119 (above)
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 200,
        "Flow": 0,
        "Beat": 0,
        "Vibe": 0,
        "Chill": 0,
    }
    stats_b = {
        "Perfect Points": 120,  # T15 => 110 (at breakpoint), T5 => 120 (above)
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Rush": 199,
        "Flow": 0,
        "Beat": 0,
        "Vibe": 0,
        "Chill": 0,
    }

    entry_a = {
        "score": 1,
        "fg_score": 1,
        "gear": ["A1", "A2", "A3", "A4", "A5", "A6"],
        "minis": ["A7", "A8", "A9"],
        "details": {"Stats": stats_a},
        "force": {
            "details": {
                "Stats": stats_a,
                "ForceGreats": {"mode": "manual", "config": {"NonFever1": 1}},
            }
        },
    }
    entry_b = {
        "score": 1,
        "fg_score": 1,
        "gear": ["B1", "B2", "B3", "B4", "B5", "B6"],
        "minis": ["B7", "B8", "B9"],
        "details": {"Stats": stats_b},
        "force": None,
    }

    out = compute_team_buff_tier_leaderboards(
        entries=[entry_a, entry_b], calc_song=calc_song, ref_arrays=ref_arrays, cfg_dict=cfg_dict
    )
    tiers = out["tiers"]

    assert "NONE" in tiers
    assert tiers["T5"]["base_top51"][0]["gear"] == entry_a["gear"]
    assert tiers["T15"]["base_top51"][0]["gear"] == entry_b["gear"]
