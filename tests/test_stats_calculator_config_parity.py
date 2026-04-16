import configparser


def test_build_base_stats_from_config_matches_get_fixed_stats():
    """
    Regression: build_base_stats_from_config() must treat UserInputStatsGems as GEM COUNTS
    and apply the same scaling/mappings as csv_parser.get_fixed_stats().
    """
    from gear_optimizer.core.utils import cfg_to_dict
    from gear_optimizer.core.stats_calculator import build_base_stats_from_config
    from gear_optimizer.data.csv_parser import get_fixed_stats

    cfg = configparser.ConfigParser()
    cfg.read_string(
        """
[UserInputStatsGems]
perfect_points = 2
combo_multiplier = 3
fever_multiplier = 1
fever_fill = 4
fever_time = 5

[ElementalGems]
Chill = 1
Flow = 0
Rush = 0
Beat = 0
Vibe = 2

[TeamContributionBuffConstant]
TeamBuff = T5
TeamColor = Vibe
"""
    )

    cfg_dict = cfg_to_dict(cfg)
    assert build_base_stats_from_config(cfg_dict) == get_fixed_stats(cfg)


def test_build_base_stats_from_config_invalid_team_color_does_not_double_count_pp():
    from gear_optimizer.core.stats_calculator import build_base_stats_from_config

    cfg_dict = {
        "TeamContributionBuffConstant": {
            "TeamBuff": "T5",
            "TeamColor": "NotARealColor",
        }
    }

    stats = build_base_stats_from_config(cfg_dict)

    assert stats["Perfect Points"] == 25
    assert stats["Chill"] == 0
    assert stats["Flow"] == 0
    assert stats["Rush"] == 0
    assert stats["Beat"] == 0
    assert stats["Vibe"] == 0
