from __future__ import annotations

from gear_optimizer.solver.base_stats import COLOR_TO_STAT_INDEX, STAT_NAMES, build_stats_array, build_stats_dict


def test_stats_helpers_round_trip_and_fill_missing_values() -> None:
    arr = build_stats_array(
        {
            "Perfect Points": 11,
            "Rush": 77,
            "Chill": "99",
        }
    )

    assert arr.tolist() == [11, 0, 0, 0, 0, 0, 0, 77, 0, 99]
    assert build_stats_dict(arr) == {
        "Perfect Points": 11,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Time": 0,
        "Fever Fill Rate": 0,
        "Beat": 0,
        "Vibe": 0,
        "Rush": 77,
        "Flow": 0,
        "Chill": 99,
    }


def test_stat_schema_exports_stay_stable() -> None:
    assert STAT_NAMES[0] == "Perfect Points"
    assert STAT_NAMES[5:] == ("Beat", "Vibe", "Rush", "Flow", "Chill")
    assert COLOR_TO_STAT_INDEX == {"Beat": 5, "Vibe": 6, "Rush": 7, "Flow": 8, "Chill": 9}
