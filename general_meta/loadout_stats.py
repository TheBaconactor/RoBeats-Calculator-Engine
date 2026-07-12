from __future__ import annotations

from typing import Any, Mapping, Sequence

from gear_optimizer.core.gem_defs import GemKey
from gear_optimizer.core.stats_calculator import compute_full_stats
from gear_optimizer.data.mini_ascension import mini_ascension_base_perfect_points_for_mini


def _unconditional_mini_ascension_stats(
    mini_names: Sequence[str],
    minis_by_name: Mapping[str, Mapping[str, Any]],
) -> dict[str, int]:
    perfect_points = 0
    for name in mini_names:
        mini = minis_by_name.get(name)
        if mini is None:
            raise KeyError(f"Missing mini stats for General Meta loadout: {name}")
        perfect_points += mini_ascension_base_perfect_points_for_mini(mini)
    return {GemKey.PP.value: perfect_points}


def build_general_meta_loadout_stats(
    *,
    gear_names: Sequence[str],
    mini_names: Sequence[str],
    gem_counts: Mapping[str, int],
    selected_element: str,
    gears_by_name: Mapping[str, Mapping[str, Any]],
    minis_by_name: Mapping[str, Mapping[str, Any]],
    team_buff_stats: Mapping[str, int],
) -> tuple[dict[str, int], dict[str, int]]:
    """Build the canonical aggregate stat surface for one General Meta loadout set.

    The aggregate has no single song context, so it includes only Mini Ascension's
    unconditional PP. Song-target elemental bonuses remain song-scoped and must not
    leak into this shared stat block.
    """
    ascension_stats = _unconditional_mini_ascension_stats(mini_names, minis_by_name)
    stats_base = compute_full_stats(
        list(gear_names),
        list(mini_names),
        gem_counts,
        selected_element,
        gears_by_name,
        minis_by_name,
        ascension_stats,
    )
    buffed_base = dict(ascension_stats)
    for stat_name, delta in team_buff_stats.items():
        buffed_base[str(stat_name)] = int(buffed_base.get(str(stat_name), 0)) + int(delta)
    stats = compute_full_stats(
        list(gear_names),
        list(mini_names),
        gem_counts,
        selected_element,
        gears_by_name,
        minis_by_name,
        buffed_base,
    )
    return stats_base, stats
