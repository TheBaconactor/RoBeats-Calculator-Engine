import numpy as np


def _mock_song(*, n_notes: int = 80, duration: float = 120.0) -> dict:
    timestamps = np.linspace(0.0, float(duration), int(n_notes), dtype=np.float32)
    return {
        "metadata": {
            "Song Name": "FG Stats Persistence Song",
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
    return {
        "Perfect Points": np.linspace(1.0, 2.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=np.float64),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=np.float64),
        "Fever Time": np.linspace(1.0, 2.5, rows, dtype=np.float64),
    }


def test_apply_force_greats_to_result_updates_stats_and_gems_on_finder_cache_hit():
    """
    Regression: apply_force_greats_to_result() (finder mode) must return a variant whose
    Stats/GemCounts/FT/FF reflect the actual FG-optimized solution, not the base timeline
    gem allocation. This is important for DB/UI persistence.

    Use an explicit FG_CACHE entry to avoid the expensive hill-climb in this unit test.
    """
    from gear_optimizer.core.constants import (
        TOTAL_ROWS,
        GEM_SCALE_NORMAL,
        GEM_SCALE_FEVER,
        GEM_STAT_TO_ELEMENT_SCALE,
        ELEMENTAL_GEM_SCALE,
        FG_SEARCH_RADIUS,
    )
    from gear_optimizer.core.utils import stats_signature
    from gear_optimizer.solver.scoring import solve_best_fever_combination, apply_force_greats_to_result, FG_CACHE
    from gear_optimizer.solver.scoring.force_greats import _extract_base_stats

    calc_song = _mock_song()
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)

    base_stats = {
        "Perfect Points": 100,
        "Combo Multiplier": 100,
        "Fever Multiplier": 100,
        "Fever Fill Rate": 100,
        "Fever Time": 100,
        "Rush": 100,
        "Flow": 100,
        "Beat": 50,
        "Vibe": 50,
        "Chill": 50,
    }
    cfg_data = {
        "selected_color": "Rush",
        "user_ft": 0,
        "user_ff": 0,
        "user_pp": 0,
        "user_cm": 0,
        "user_fm": 0,
        "static_elem_input": 0,
        "use_gpu": False,
    }

    data_dict = solve_best_fever_combination(
        cfg=None,
        initial_stats=base_stats,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        silent=True,
        override_cfg=cfg_data,
    )

    sel = data_dict.get("Selected Element") or "Rush"
    ft0 = int(data_dict.get("FT", 0) or 0)
    ff0 = int(data_dict.get("FF", 0) or 0)

    # Precompute the base (pre-gem) stats so we can build an expected final Stats dict.
    base = _extract_base_stats(data_dict["Stats"], data_dict.get("GemCounts") or {}, sel, ft0, ff0)

    fake_fg = {
        "config_dict": {"NonFever1": 2, "NonFever2": 0},
        "final_score": 123456,
        "gem_counts": {
            "Perfect Points": 1,
            "Combo Multiplier": 2,
            "Fever Multiplier": 3,
            "Element": 4,
        },
        "FT": 5,
        "FF": 6,
    }

    # Populate FG_CACHE so apply_force_greats_to_result hits the cache and skips hill-climb.
    sig = stats_signature(data_dict["Stats"], calc_song, sel)
    cache_key = (sig, "finder", ft0, ff0, int(FG_SEARCH_RADIUS), False)
    FG_CACHE.clear()
    FG_CACHE[cache_key] = fake_fg

    fg_variant = apply_force_greats_to_result(
        data_dict.copy(),
        calc_song,
        ref_arrays,
        use_finder=True,
        use_gpu=False,
    )
    assert fg_variant is not None
    assert int(fg_variant.get("Score", 0)) == int(fake_fg["final_score"])
    assert int(fg_variant.get("FT", -1)) == int(fake_fg["FT"])
    assert int(fg_variant.get("FF", -1)) == int(fake_fg["FF"])
    assert (fg_variant.get("GemCounts") or {}) == fake_fg["gem_counts"]

    # Expected Stats = base + gem allocation described by the FG solution.
    g_pp = int(fake_fg["gem_counts"]["Perfect Points"])
    g_cm = int(fake_fg["gem_counts"]["Combo Multiplier"])
    g_fm = int(fake_fg["gem_counts"]["Fever Multiplier"])
    g_ov = int(fake_fg["gem_counts"]["Element"])
    ft = int(fake_fg["FT"])
    ff = int(fake_fg["FF"])

    expected = dict(base)
    expected["Perfect Points"] = expected.get("Perfect Points", 0) + g_pp * GEM_SCALE_NORMAL
    expected["Combo Multiplier"] = expected.get("Combo Multiplier", 0) + g_cm * GEM_SCALE_NORMAL
    expected["Fever Multiplier"] = expected.get("Fever Multiplier", 0) + g_fm * GEM_SCALE_FEVER
    expected["Fever Time"] = expected.get("Fever Time", 0) + ft * GEM_SCALE_FEVER
    expected["Fever Fill Rate"] = expected.get("Fever Fill Rate", 0) + ff * GEM_SCALE_FEVER

    expected["Chill"] = expected.get("Chill", 0) + g_pp * GEM_STAT_TO_ELEMENT_SCALE
    expected["Flow"] = expected.get("Flow", 0) + g_cm * GEM_STAT_TO_ELEMENT_SCALE
    expected["Rush"] = expected.get("Rush", 0) + g_fm * GEM_STAT_TO_ELEMENT_SCALE
    expected["Beat"] = expected.get("Beat", 0) + ft * GEM_STAT_TO_ELEMENT_SCALE
    expected["Vibe"] = expected.get("Vibe", 0) + ff * GEM_STAT_TO_ELEMENT_SCALE

    expected[sel] = expected.get(sel, 0) + g_ov * ELEMENTAL_GEM_SCALE

    got = fg_variant.get("Stats") or {}
    for k in (
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Time",
        "Fever Fill Rate",
        "Chill",
        "Flow",
        "Rush",
        "Beat",
        "Vibe",
    ):
        assert int(got.get(k, 0)) == int(expected.get(k, 0))
    assert int(got.get(sel, 0)) == int(expected.get(sel, 0))


def test_apply_force_greats_to_result_does_not_mutate_input_on_cache_hit():
    """
    Regression: apply_force_greats_to_result() must not mutate the input result dict.

    Historically this function wrote ForceGreats metadata into the input dict even though it
    advertises returning a cloned variant.
    """
    from gear_optimizer.core.constants import TOTAL_ROWS, FG_SEARCH_RADIUS
    from gear_optimizer.core.utils import stats_signature
    from gear_optimizer.solver.scoring import solve_best_fever_combination, apply_force_greats_to_result, FG_CACHE

    calc_song = _mock_song()
    ref_arrays = _ref_arrays(TOTAL_ROWS + 1)

    data_dict = solve_best_fever_combination(
        cfg=None,
        initial_stats={
            "Perfect Points": 100,
            "Combo Multiplier": 100,
            "Fever Multiplier": 100,
            "Fever Fill Rate": 100,
            "Fever Time": 100,
            "Rush": 100,
            "Flow": 100,
            "Beat": 50,
            "Vibe": 50,
            "Chill": 50,
        },
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        silent=True,
        override_cfg={
            "selected_color": "Rush",
            "user_ft": 0,
            "user_ff": 0,
            "user_pp": 0,
            "user_cm": 0,
            "user_fm": 0,
            "static_elem_input": 0,
            "use_gpu": False,
        },
    )

    assert "ForceGreats" not in data_dict

    sel = data_dict.get("Selected Element") or "Rush"
    ft0 = int(data_dict.get("FT", 0) or 0)
    ff0 = int(data_dict.get("FF", 0) or 0)
    sig = stats_signature(data_dict["Stats"], calc_song, sel)
    cache_key = (sig, "finder", ft0, ff0, int(FG_SEARCH_RADIUS), False)
    FG_CACHE.clear()
    FG_CACHE[cache_key] = {
        "config_dict": {"NonFever1": 1},
        "final_score": int(data_dict.get("Score", 0) or 0),
        "gem_counts": dict(data_dict.get("GemCounts") or {}),
        "FT": ft0,
        "FF": ff0,
    }

    fg_variant = apply_force_greats_to_result(
        data_dict,
        calc_song,
        ref_arrays,
        use_finder=True,
        use_gpu=False,
    )
    assert fg_variant is not None
    assert "ForceGreats" not in data_dict


def test_extract_base_stats_detects_pre_gem_without_element_gems():
    """
    Regression: _extract_base_stats() must not corrupt pre-gem stats when Element gems are 0.

    Some GPU payload paths can supply base (pre-gem) stats alongside a gem allocation,
    and reversing those gems must be a no-op.
    """
    from gear_optimizer.core.constants import GEM_SCALE_NORMAL
    from gear_optimizer.solver.scoring.force_greats import _extract_base_stats

    stats = {
        "Perfect Points": 10,
        "Combo Multiplier": 10,
        "Fever Multiplier": 10,
        "Fever Time": 10,
        "Fever Fill Rate": 10,
        "Beat": 10,
        "Vibe": 10,
        "Rush": 10,
        "Flow": 10,
        "Chill": 10,
    }
    gem_counts = {
        # Use a large count so reversing would go strongly negative if applied.
        "Perfect Points": max(90, int(GEM_SCALE_NORMAL) * 50),
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Element": 0,
    }

    base = _extract_base_stats(stats, gem_counts, "Rush", 0, 0)
    assert base.get("Perfect Points") == stats.get("Perfect Points")
    assert base.get("Rush") == stats.get("Rush")
