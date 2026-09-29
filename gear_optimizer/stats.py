"""Loadout stats: fixed stats, plus the six gear and three minis, plus gems."""

from __future__ import annotations

from collections.abc import Mapping

from .gamedata import ELEMENTS, Stats, empty_stats

GEM_BUDGET = 90
# A stat gem raises its stat and one element; an element gem raises the selected element.
STAT_GEMS: dict[str, tuple[int, str]] = {
    "Perfect Points": (2, "Chill"),
    "Combo Multiplier": (2, "Flow"),
    "Fever Multiplier": (3, "Rush"),
    "Fever Time": (3, "Beat"),
    "Fever Fill Rate": (3, "Vibe"),
}
STAT_GEM_ELEMENT_GAIN = 3
ELEMENT_GEM_GAIN = 6
# Gem counts are keyed by the stat a gem raises, plus "Element" for the selected element.
GEM_KINDS = (*STAT_GEMS, "Element")


def total(*parts: Mapping[str, int]) -> Stats:
    """Sum stat rows (fixed stats, item stats)."""
    out = empty_stats()
    for part in parts:
        for stat, value in part.items():
            out[stat] += value
    return out


def apply_gems(stats: Mapping[str, int], gems: Mapping[str, int], selected_element: str) -> Stats:
    unknown = set(gems) - set(GEM_KINDS)
    if unknown:
        raise ValueError(f"unknown gem kinds {sorted(unknown)}")
    out = dict(stats)
    for stat, (gain, element) in STAT_GEMS.items():
        count = gems.get(stat, 0)
        out[stat] += count * gain
        out[element] += count * STAT_GEM_ELEMENT_GAIN
    element_gems = gems.get("Element", 0)
    if element_gems:
        if selected_element not in ELEMENTS:
            raise ValueError(f"{element_gems} element gems need a selected element, got {selected_element!r}")
        out[selected_element] += element_gems * ELEMENT_GEM_GAIN
    return out
