"""Loadout stats: fixed stats, plus the six gear and three minis, plus gems."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from .gamedata import ELEMENTS, Gear, Mini, SongMini, Stats, empty_stats
from .rules import ELEMENT_GEM_GAIN, STAT_GEM_ELEMENT_GAIN, STAT_GEM_GAIN_FEVER, STAT_GEM_GAIN_NORMAL

# A stat gem raises its stat and one element; an element gem raises the selected element.
STAT_GEMS: dict[str, tuple[int, str]] = {
    "Perfect Points": (STAT_GEM_GAIN_NORMAL, "Chill"),
    "Combo Multiplier": (STAT_GEM_GAIN_NORMAL, "Flow"),
    "Fever Multiplier": (STAT_GEM_GAIN_FEVER, "Rush"),
    "Fever Time": (STAT_GEM_GAIN_FEVER, "Beat"),
    "Fever Fill Rate": (STAT_GEM_GAIN_FEVER, "Vibe"),
}
# Gem counts are keyed by the stat a gem raises, plus "Element" for the selected element.
GEM_KINDS = (*STAT_GEMS, "Element")


def gems(*, pp: int = 0, cm: int = 0, fm: int = 0, ft: int = 0, ff: int = 0, element: int = 0) -> dict[str, int]:
    """A gem allocation keyed by GEM_KINDS."""
    return {
        "Perfect Points": int(pp),
        "Combo Multiplier": int(cm),
        "Fever Multiplier": int(fm),
        "Fever Time": int(ft),
        "Fever Fill Rate": int(ff),
        "Element": int(element),
    }


def total(*parts: Mapping[str, int]) -> Stats:
    """Sum stat rows (fixed stats, item stats)."""
    out = empty_stats()
    for part in parts:
        for stat, value in part.items():
            out[stat] += value
    return out


def named_loadout_stats(
    fixed: Mapping[str, int],
    gear_names: Iterable[str],
    mini_names: Iterable[str],
    gears: Mapping[str, Gear],
    minis: Mapping[str, Mini | SongMini],
    allocation: Mapping[str, int],
    selected_element: str,
) -> Stats:
    """Stats of a loadout given by item names; a name the catalogs do not know adds nothing."""
    items = [gears[name].stats for name in gear_names if name in gears]
    items += [minis[name].stats for name in mini_names if name in minis]
    return apply_gems(total(fixed, *items), allocation, selected_element)


def apply_gems(stats: Mapping[str, int], allocation: Mapping[str, int], selected_element: str) -> Stats:
    unknown = set(allocation) - set(GEM_KINDS)
    if unknown:
        raise ValueError(f"unknown gem kinds {sorted(unknown)}")
    out = dict(stats)
    for stat, (gain, element) in STAT_GEMS.items():
        count = allocation.get(stat, 0)
        out[stat] += count * gain
        out[element] += count * STAT_GEM_ELEMENT_GAIN
    element_gems = allocation.get("Element", 0)
    if element_gems:
        if selected_element not in ELEMENTS:
            raise ValueError(f"{element_gems} element gems need a selected element, got {selected_element!r}")
        out[selected_element] += element_gems * ELEMENT_GEM_GAIN
    return out
