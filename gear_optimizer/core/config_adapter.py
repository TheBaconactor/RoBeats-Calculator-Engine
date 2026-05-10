from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
@dataclass(frozen=True, slots=True)
class TeamContributionBuffSettings:
    team_buff: str = "T5"
    team_color: str = ""
    auto_select_buff_and_color: bool = False

    @classmethod
    def from_cfg_dict(cls, cfg_dict: Mapping[str, Any] | None) -> TeamContributionBuffSettings:
        del cfg_dict
        return cls(team_buff="T5", team_color="", auto_select_buff_and_color=True)

    @classmethod
    def from_cfg(cls, cfg: Any) -> TeamContributionBuffSettings:
        del cfg
        return cls(team_buff="T5", team_color="", auto_select_buff_and_color=True)


@dataclass(frozen=True, slots=True)
class UserGemSettings:
    perfect_points: int = 0
    combo_multiplier: int = 0
    fever_multiplier: int = 0
    fever_fill_rate: int = 0
    fever_time: int = 0
    elemental_overflow: dict[str, int] | None = None

    @classmethod
    def from_cfg_dict(cls, cfg_dict: Mapping[str, Any] | None) -> UserGemSettings:
        del cfg_dict
        return cls()

    @classmethod
    def from_cfg(cls, cfg: Any) -> UserGemSettings:
        del cfg
        return cls()


def read_team_contribution_buff_from_cfg_dict(cfg_dict: Mapping[str, Any] | None) -> TeamContributionBuffSettings:
    return TeamContributionBuffSettings.from_cfg_dict(cfg_dict)


def read_user_gem_settings_from_cfg_dict(cfg_dict: Mapping[str, Any] | None) -> UserGemSettings:
    return UserGemSettings.from_cfg_dict(cfg_dict)
