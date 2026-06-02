import numpy as np

from gear_optimizer.core.constants import GEM_SCALE_NORMAL
from gear_optimizer.helpers.song_helpers.fg_candidate_stats import hydrate_fg_candidate_stats


def test_hydrate_fg_candidate_stats_uses_base_fixed_to_avoid_double_counting_user_gems():
    # base_stats_fixed includes "user fixed" gems already (a common non-auto-mode setup).
    # cfg_data tells us how many gems were embedded so we can subtract them before re-applying
    # the candidate's chosen allocation.
    user_pp = 7
    base_stats_fixed = {
        "Perfect Points": user_pp * GEM_SCALE_NORMAL,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Time": 0,
        "Fever Fill Rate": 0,
        "Beat": 0,
        "Vibe": 0,
        "Rush": 0,
        "Flow": 0,
        "Chill": 0,
    }
    cfg_data = {
        "user_pp": user_pp,
        "user_cm": 0,
        "user_fm": 0,
        "user_ft": 0,
        "user_ff": 0,
        "static_elem_input": 0,
        "selected_color": "Rush",
    }

    cand = {
        "Score": 123,
        "BaseScore": 123,
        "Gear": [],
        "Minis": [],
        "Genome": [],
        "Data": {
            "FT": 0,
            "FF": 0,
            "GemCounts": {"Perfect Points": user_pp, "Combo Multiplier": 0, "Fever Multiplier": 0, "Element": 0},
            "Selected Element": "Rush",
        },
    }
    hydrate_fg_candidate_stats([cand], base_stats_fixed=base_stats_fixed, selected_color="Rush", cfg_data=cfg_data)

    stats = cand["Data"]["Stats"]
    # If we double-counted, this would be 2x. Correct behavior: it stays at the original embedded total.
    assert stats["Perfect Points"] == user_pp * GEM_SCALE_NORMAL


def test_hydrate_fg_candidate_stats_prefers_base_stats_over_rebuilding_from_genome():
    cand = {
        "Score": 321,
        "BaseScore": 321,
        "Gear": [{"Name": "HugePP", "Perfect Points": 999}],
        "Minis": [],
        "Genome": [{"Name": "HugePP", "Perfect Points": 999}],
        "Data": {
            "BaseStats": {
                "Perfect Points": 10,
                "Combo Multiplier": 0,
                "Fever Multiplier": 0,
                "Fever Time": 0,
                "Fever Fill Rate": 0,
                "Beat": 0,
                "Vibe": 0,
                "Rush": 0,
                "Flow": 0,
                "Chill": 0,
            },
            "FT": 0,
            "FF": 0,
            "GemCounts": {"Perfect Points": 1, "Combo Multiplier": 0, "Fever Multiplier": 0, "Element": 0},
            "Selected Element": "Rush",
        },
    }

    hydrate_fg_candidate_stats([cand], base_stats_fixed={}, selected_color="Rush", cfg_data={"selected_color": "Rush"})

    stats = cand["Data"]["Stats"]
    assert cand["Data"]["BaseStats"]["Perfect Points"] == 10
    assert stats["Perfect Points"] == 10 + GEM_SCALE_NORMAL


def test_hydrate_fg_candidate_stats_canonicalizes_base_score_and_preserves_raw_ga_search_score():
    calc_song = {
        "metadata": {
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": 0.0,
        },
        "song_data": {"timestamps": [0.0]},
    }
    ref_arrays = {
        "Perfect Points": [1.0] * 161,
        "Combo Multiplier": [1.0] * 161,
        "Fever Multiplier": [1.0] * 161,
        "Fever Fill Rate": [1.0] * 161,
        "Fever Time": [1.0] * 161,
    }
    cand = {
        "Score": 999,
        "BaseScore": 999,
        "Data": {
            "BaseStats": {
                "Perfect Points": 0,
                "Combo Multiplier": 0,
                "Fever Multiplier": 0,
                "Fever Time": 0,
                "Fever Fill Rate": 0,
                "Beat": 0,
                "Vibe": 0,
                "Rush": 10,
                "Flow": 5,
                "Chill": 0,
            },
            "FT": 0,
            "FF": 0,
            "GemCounts": {"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0, "Element": 0},
            "Selected Element": "Rush",
        },
    }

    hydrate_fg_candidate_stats(
        [cand],
        base_stats_fixed={},
        selected_color="Rush",
        cfg_data={"selected_color": "Rush"},
        calc_song=calc_song,
        ref_arrays=ref_arrays,
    )

    assert cand["RawGASearchScore"] == 999
    assert cand["Data"]["RawGASearchScore"] == 999
    assert cand["BaseScore"] == 26
    assert cand["Score"] == 26
    assert cand["Data"]["BaseScore"] == 26


def test_hydrate_fg_candidate_stats_canonicalizes_existing_stats_payload():
    timestamps = np.linspace(0.0, 2.0, 101, dtype=np.float32)
    calc_song = {
        "metadata": {
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
        },
        "song_data": {"timestamps": timestamps},
    }
    ref_arrays = {
        "Perfect Points": [1.0] * 161,
        "Combo Multiplier": [2.0] * 161,
        "Fever Multiplier": [4.0] * 161,
        "Fever Fill Rate": [1.0] * 161,
        "Fever Time": [1.0] * 161,
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
    cand = {
        "Score": 999,
        "BaseScore": 999,
        "Data": {
            "Stats": dict(stats),
            "BaseStats": dict(stats),
            "FT": 0,
            "FF": 0,
            "GemCounts": {"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0, "Element": 0},
            "Selected Element": "Rush",
        },
    }

    hydrate_fg_candidate_stats(
        [cand],
        base_stats_fixed={},
        selected_color="Rush",
        cfg_data={"selected_color": "Rush"},
        calc_song=calc_song,
        ref_arrays=ref_arrays,
    )

    assert cand["RawGASearchScore"] == 999
    assert cand["BaseScore"] == 80336
    assert cand["Data"]["BaseScore"] == 80336
