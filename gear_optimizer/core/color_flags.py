"""
Color flag helpers for scoring/gem allocation.

These flags are used by both CPU and GPU paths to determine which elemental lanes
receive stat-gem contributions and which lanes receive overflow gems.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Mapping


_COLOR_FLAG_KEYS = (
    "is_p_ft",
    "is_s_ft",
    "is_p_ff",
    "is_s_ff",
    "is_p_pp",
    "is_s_pp",
    "is_p_cm",
    "is_s_cm",
    "is_p_fm",
    "is_s_fm",
    "is_p_ov",
    "is_s_ov",
)


@dataclass(frozen=True, slots=True)
class ColorFlags:
    is_p_ft: int = 0
    is_s_ft: int = 0
    is_p_ff: int = 0
    is_s_ff: int = 0
    is_p_pp: int = 0
    is_s_pp: int = 0
    is_p_cm: int = 0
    is_s_cm: int = 0
    is_p_fm: int = 0
    is_s_fm: int = 0
    is_p_ov: int = 0
    is_s_ov: int = 0

    def as_dict(self) -> dict[str, int]:
        return {key: int(getattr(self, key)) for key in _COLOR_FLAG_KEYS}

    def as_tuple(self) -> tuple[int, ...]:
        return tuple(int(getattr(self, key)) for key in _COLOR_FLAG_KEYS)


@lru_cache(maxsize=64)
def _build_color_flags_tuple(p: str, s: str, sel: str) -> tuple[int, ...]:
    return (
        1 if p == "Beat" else 0,
        1 if s == "Beat" else 0,
        1 if p == "Vibe" else 0,
        1 if s == "Vibe" else 0,
        1 if p == "Chill" else 0,
        1 if s == "Chill" else 0,
        1 if p == "Flow" else 0,
        1 if s == "Flow" else 0,
        1 if p == "Rush" else 0,
        1 if s == "Rush" else 0,
        1 if sel and sel == p else 0,
        1 if sel and sel == s else 0,
    )


def normalize_color_flags(flags: ColorFlags | Mapping[str, Any] | None) -> ColorFlags:
    if isinstance(flags, ColorFlags):
        return flags
    source = flags or {}
    return ColorFlags(**{key: int(source.get(key, 0) or 0) for key in _COLOR_FLAG_KEYS})


def build_color_flag_values(p_color: str | None, s_color: str | None, selected_color: str | None) -> ColorFlags:
    p = str(p_color or "")
    s = str(s_color or "")
    sel = str(selected_color or "")
    vals = _build_color_flags_tuple(p, s, sel)
    return ColorFlags(**dict(zip(_COLOR_FLAG_KEYS, vals)))


def build_color_flags(p_color: str | None, s_color: str | None, selected_color: str | None) -> dict[str, int]:
    return build_color_flag_values(p_color, s_color, selected_color).as_dict()
