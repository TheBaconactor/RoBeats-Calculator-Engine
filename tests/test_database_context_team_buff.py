import configparser

from gear_optimizer.helpers.song_helpers.database_context import resolve_database_baseline_team_buff


def test_resolve_database_baseline_team_buff_uses_manual_cfg_tier():
    cfg = configparser.ConfigParser()
    cfg["IterationEngine"] = {"AutoSelectBuffAndColor": "False"}
    cfg["TeamContributionBuffConstant"] = {"TeamBuff": "T10"}

    assert resolve_database_baseline_team_buff(cfg) == "T10"


def test_resolve_database_baseline_team_buff_uses_auto_cfg_dict_t5():
    cfg_dict = {
        "IterationEngine": {"AutoSelectBuffAndColor": "True"},
        "TeamContributionBuffConstant": {"TeamBuff": "T20"},
    }

    assert resolve_database_baseline_team_buff(cfg_dict=cfg_dict) == "T5"


def test_resolve_database_baseline_team_buff_accepts_cfg_dict_as_first_arg():
    cfg_dict = {
        "IterationEngine": {"AutoSelectBuffAndColor": "False"},
        "TeamContributionBuffConstant": {"TeamBuff": "T50"},
    }

    assert resolve_database_baseline_team_buff(cfg_dict) == "T50"
