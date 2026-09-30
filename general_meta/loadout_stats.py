from __future__ import annotations

from typing import Mapping, Sequence

from gear_optimizer.gamedata import ASCENSION_PERFECT_POINTS, Gear, Mini
from gear_optimizer.stats import named_loadout_stats, total


def _unconditional_mini_ascension_stats(
    mini_names: Sequence[str],
    minis_by_name: Mapping[str, Mini],
) -> dict[str, int]:
    missing = [name for name in mini_names if name not in minis_by_name]
    if missing:
        raise KeyError(f"Missing mini stats for General Meta loadout: {missing[0]}")
    ascended = [name for name in mini_names if not isinstance(minis_by_name[name], Mini)]
    if ascended:
        # A song's minis already include this Perfect Points; adding it again would count it twice.
        raise TypeError(f"General Meta needs base minis, got an ascended one: {ascended[0]}")
    return {"Perfect Points": ASCENSION_PERFECT_POINTS * len(mini_names)}


def build_general_meta_loadout_stats(
    *,
    gear_names: Sequence[str],
    mini_names: Sequence[str],
    gem_counts: Mapping[str, int],
    selected_element: str,
    gears_by_name: Mapping[str, Gear],
    minis_by_name: Mapping[str, Mini],
    team_buff_stats: Mapping[str, int],
) -> tuple[dict[str, int], dict[str, int]]:
    """Build the canonical aggregate stat surface for one General Meta loadout set.

    The aggregate has no single song context, so it includes only Mini Ascension's
    unconditional PP. Song-target elemental bonuses remain song-scoped and must not
    leak into this shared stat block.
    """
    ascension_stats = _unconditional_mini_ascension_stats(mini_names, minis_by_name)
    stats_base = named_loadout_stats(
        ascension_stats, gear_names, mini_names, gears_by_name, minis_by_name, gem_counts, selected_element
    )
    stats = named_loadout_stats(
        total(ascension_stats, team_buff_stats),
        gear_names,
        mini_names,
        gears_by_name,
        minis_by_name,
        gem_counts,
        selected_element,
    )
    return stats_base, stats
