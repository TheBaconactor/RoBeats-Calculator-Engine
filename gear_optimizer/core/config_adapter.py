from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

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
        from .utils import safe_int
        s = cfg_dict.get("UserInputStatsGems", {}) or {}
        if not isinstance(s, Mapping):
            s = {}
        elem = cfg_dict.get("ElementalGems", {}) or {}
        if not isinstance(elem, Mapping):
            elem = {}

        overflow: dict[str, int] = {}
        for el in ELEMENT_STAT_KEYS:
            val = safe_int(elem.get(el, elem.get(el.lower(), 0)))
            if val > 0:
                overflow[el] = val
        return cls(
            perfect_points=safe_int(s.get("perfect_points", 0)),
            combo_multiplier=safe_int(s.get("combo_multiplier", 0)),
            fever_multiplier=safe_int(s.get("fever_multiplier", 0)),
            fever_fill_rate=safe_int(s.get("fever_fill", s.get("fever_fill_rate", 0))),
            fever_time=safe_int(s.get("fever_time", 0)),
            elemental_overflow=overflow if overflow else None,
        )


