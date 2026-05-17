from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import logging

from .team_buff import (
    resolve_baseline_team_buff_from_cfg_dict,
    resolve_team_color_from_cfg_dict,
)



logger = logging.getLogger(__name__)
@dataclass(frozen=True, slots=True)
class TeamContributionBuffSettings:
    team_buff: str = "T5"
    team_color: str = ""

    @classmethod
    def from_cfg_dict(cls, cfg_dict: Mapping[str, Any] | None) -> TeamContributionBuffSettings:
        if not isinstance(cfg_dict, Mapping):
            return cls()
        team_buff = resolve_baseline_team_buff_from_cfg_dict(cfg_dict, default="T5")
        team_color = resolve_team_color_from_cfg_dict(cfg_dict)
        return cls(
            team_buff=str(team_buff),
            team_color=str(team_color),
        )

    @classmethod
    def from_cfg(cls, cfg: Any) -> TeamContributionBuffSettings:
        return cls(team_buff="T5", team_color="")


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
        if not isinstance(cfg_dict, Mapping):
            return cls()
        from .gem_defs import ELEMENT_STAT_KEYS
        s = cfg_dict.get("UserInputStatsGems", {}) or {}
        if not isinstance(s, Mapping):
            s = {}
        elem = cfg_dict.get("ElementalGems", {}) or {}
        if not isinstance(elem, Mapping):
            elem = {}

        def _to_int(v: Any) -> int:
            try:
                text = str(v or "").strip()
                if not text:
                    return 0
                return int(text)
            except (TypeError, ValueError):
                return 0

        overflow: dict[str, int] = {}
        for el in ELEMENT_STAT_KEYS:
            val = _to_int(elem.get(el, elem.get(el.lower(), 0)))
            if val > 0:
                overflow[el] = val
        return cls(
            perfect_points=_to_int(s.get("perfect_points", 0)),
            combo_multiplier=_to_int(s.get("combo_multiplier", 0)),
            fever_multiplier=_to_int(s.get("fever_multiplier", 0)),
            fever_fill_rate=_to_int(s.get("fever_fill", s.get("fever_fill_rate", 0))),
            fever_time=_to_int(s.get("fever_time", 0)),
            elemental_overflow=overflow if overflow else None,
        )

    @classmethod
    def from_cfg(cls, cfg: Any) -> UserGemSettings:
        if cfg is None:
            return cls()
        from .config import cfg_get_int
        from .gem_defs import ELEMENT_STAT_KEYS
        pp = cfg_get_int(cfg, "UserInputStatsGems", "Perfect_Points", 0)
        cm = cfg_get_int(cfg, "UserInputStatsGems", "Combo_Multiplier", 0)
        fm = cfg_get_int(cfg, "UserInputStatsGems", "Fever_Multiplier", 0)
        ff = cfg_get_int(cfg, "UserInputStatsGems", "Fever_Fill_Rate", 0, clamp_min=0)
        ft = cfg_get_int(cfg, "UserInputStatsGems", "Fever_Time", 0, clamp_min=0)
        overflow: dict[str, int] = {}
        for el in ELEMENT_STAT_KEYS:
            val = cfg_get_int(cfg, "ElementalGems", el, 0, clamp_min=0)
            if val > 0:
                overflow[el] = int(val)
        from .config import cfg_get
        pp_raw = cfg_get(cfg, "UserInputStatsGems", "perfect_points", str, "")
        if not pp_raw:
            pp_raw = cfg_get(cfg, "UserInputStatsGems", "Perfect_Points", str, "")
        return cls(
            perfect_points=int(pp) if pp_raw else 0,
            combo_multiplier=int(cm),
            fever_multiplier=int(fm),
            fever_fill_rate=int(ff),
            fever_time=int(ft),
            elemental_overflow=overflow if overflow else None,
        )




