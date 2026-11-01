"""Which gem kinds raise the song's elements, as the GA kernels read them (GpuColorFlags): is_<p|s>_<gem> says whether
a stat gem's element (stats.STAT_GEMS) is the song's primary / secondary element, is_<p|s>_ov whether the element gem's
selected element is."""

from __future__ import annotations

from ..stats import STAT_GEMS

_GEM_KEYS = {"Fever Time": "ft", "Fever Fill Rate": "ff", "Perfect Points": "pp", "Combo Multiplier": "cm",
             "Fever Multiplier": "fm"}
COLOR_FLAG_KEYS = tuple(f"is_{side}_{gem}" for gem in (*_GEM_KEYS.values(), "ov") for side in ("p", "s"))


def build_color_flags(primary: str, secondary: str, selected: str) -> dict[str, int]:
    flags = {}
    for stat, gem in _GEM_KEYS.items():
        element = STAT_GEMS[stat][1]
        flags[f"is_p_{gem}"] = int(primary == element)
        flags[f"is_s_{gem}"] = int(secondary == element)
    flags["is_p_ov"] = int(bool(selected) and selected == primary)
    flags["is_s_ov"] = int(bool(selected) and selected == secondary)
    return flags
