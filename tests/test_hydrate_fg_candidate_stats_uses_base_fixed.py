from gear_optimizer.core.constants import GEM_SCALE_NORMAL
from gear_optimizer.helpers.song_helpers.fg_combo_booster import hydrate_fg_candidate_stats


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

