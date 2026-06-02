import pytest

from gear_optimizer.solver.force_greats_common import STAT_KEYS, extract_base_stats
from gear_optimizer.solver.scoring.stats_ops import apply_gems_to_base_stats


def test_extract_base_stats_round_trips_when_overflow_overlaps_stat_gem_element():
    base_stats = {
        "Perfect Points": 52,
        "Combo Multiplier": 66,
        "Fever Multiplier": 35,
        "Fever Time": 28,
        "Fever Fill Rate": 7,
        "Beat": 15,
        "Vibe": 61,
        "Rush": 346,
        "Flow": 11,
        "Chill": 9,
    }
    gem_counts = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 13,
        "Element": 57,
    }
    stats = apply_gems_to_base_stats(
        base_stats,
        "Rush",
        1,
        19,
        0,
        0,
        13,
        57,
    )

    recovered = extract_base_stats(stats, gem_counts, "Rush", ft_gems=1, ff_gems=19)

    assert {key: int(recovered[key]) for key in STAT_KEYS} == {key: int(base_stats[key]) for key in STAT_KEYS}


def test_extract_base_stats_fails_loudly_when_gem_counts_cannot_match_stats():
    stats = {key: 0 for key in STAT_KEYS}

    with pytest.raises(ValueError, match="Cannot losslessly extract base stats"):
        extract_base_stats(
            stats,
            {"Fever Multiplier": 13, "Element": 57},
            "Rush",
            ft_gems=0,
            ff_gems=0,
        )
