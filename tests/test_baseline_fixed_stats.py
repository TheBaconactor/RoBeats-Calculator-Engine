import pytest

from gear_optimizer.helpers.song_helpers.song_config import baseline_fixed_stats

_ELEMENTS = ("Chill", "Flow", "Rush", "Beat", "Vibe")


def _song(primary: str) -> dict:
    return {"metadata": {"Primary Color": primary}}


def test_baseline_fixed_stats_are_the_t5_team_buff_on_the_song_primary():
    assert baseline_fixed_stats(_song("Rush")) == {
        "Perfect Points": 25,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Chill": 0,
        "Flow": 0,
        "Rush": 30,
        "Beat": 0,
        "Vibe": 0,
    }


@pytest.mark.parametrize("primary", ["", "NotARealColor"])
def test_baseline_fixed_stats_without_a_known_primary_add_only_perfect_points(primary):
    stats = baseline_fixed_stats(_song(primary))
    assert stats["Perfect Points"] == 25
    assert all(stats[element] == 0 for element in _ELEMENTS)
