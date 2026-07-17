import configparser

from gear_optimizer.core.team_buff import (
    resolve_baseline_team_buff_from_cfg,
    resolve_baseline_team_buff_from_cfg_dict,
)


def test_optimizer_team_buff_policy_ignores_stale_config_entries():
    cfg = configparser.ConfigParser()
    cfg["TeamContributionBuffConstant"] = {"TeamBuff": "T50", "TeamColor": "Rush"}
    cfg_dict = {"TeamContributionBuffConstant": {"TeamBuff": "T20", "TeamColor": "Vibe"}}

    assert resolve_baseline_team_buff_from_cfg(cfg) == "T5"
    assert resolve_baseline_team_buff_from_cfg_dict(cfg_dict) == "T5"
