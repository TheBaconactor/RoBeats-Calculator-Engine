from __future__ import annotations

import pytest

from gear_optimizer.gamedata import empty_stats
from gear_optimizer.solver.base_stats import COLOR_TO_STAT_INDEX, STAT_NAMES, build_stats_array, build_stats_dict


def test_stats_helpers_round_trip_in_stat_names_order() -> None:
    stats = {**empty_stats(), "Perfect Points": 11, "Rush": 77, "Chill": 99}
    arr = build_stats_array(stats)

    assert arr.tolist() == [11, 0, 0, 0, 0, 0, 0, 77, 0, 99]
    assert build_stats_dict(arr) == stats
    assert list(build_stats_dict(arr)) == list(STAT_NAMES)


def test_stats_helpers_reject_incomplete_rows() -> None:
    with pytest.raises(KeyError):
        build_stats_array({"Perfect Points": 11})
    with pytest.raises(IndexError):
        build_stats_dict([11, 0, 0])


def test_stat_schema_exports_stay_stable() -> None:
    assert STAT_NAMES[0] == "Perfect Points"
    assert STAT_NAMES[5:] == ("Beat", "Vibe", "Rush", "Flow", "Chill")
    assert COLOR_TO_STAT_INDEX == {"Beat": 5, "Vibe": 6, "Rush": 7, "Flow": 8, "Chill": 9}
