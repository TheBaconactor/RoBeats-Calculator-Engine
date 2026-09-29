"""
Shared stats calculation utilities.

Consolidates shared stats computation logic so optimizer and maintenance tools
derive the same base stat surfaces.
"""

from .constants import (
    GEM_SCALE_NORMAL,
    GEM_SCALE_FEVER,
    ELEMENTAL_GEM_SCALE,
    GEM_STAT_TO_ELEMENT_SCALE,
    SKIP_ITEM_KEYS,
)
from .gem_defs import ELEMENT_STAT_KEYS, GemKey, element_gem_count


def compute_full_stats(gear_names, mini_names, gem_counts, selected_element, gears_by_name, minis_by_name, base_stats):
    """
    Compute full stats from gear + minis + gems + base stats.

    This is the canonical implementation used by:
    - backfill_stats.py (stats backfilling)
    - Any future stats computation needs

    Args:
        gear_names: List of gear names
        mini_names: List of mini names
        gem_counts: Dict with gem allocations (Perfect Points, Combo Multiplier, etc.)
        selected_element: Selected elemental color (Chill/Flow/Rush/Beat/Vibe)
        gears_by_name: Dict mapping gear names to full gear dicts
        minis_by_name: Dict mapping mini names to full mini dicts
        base_stats: Base stats dict (from config + team buffs)

    Returns:
        dict: Full computed stats including all contributions
    """
    stats = base_stats.copy()

    # Add gear stats
    for name in gear_names:
        item = gears_by_name.get(name, {})
        for k, v in item.items():
            if k not in SKIP_ITEM_KEYS and isinstance(v, (int, float)):
                stats[k] = stats.get(k, 0) + v

    # Add mini stats
    for name in mini_names:
        item = minis_by_name.get(name, {})
        for k, v in item.items():
            if k not in SKIP_ITEM_KEYS and isinstance(v, (int, float)):
                stats[k] = stats.get(k, 0) + v

    # Add gem contributions
    g_pp = gem_counts.get(GemKey.PP.value, 0) or 0
    g_cm = gem_counts.get(GemKey.CM.value, 0) or 0
    g_fm = gem_counts.get(GemKey.FM.value, 0) or 0
    g_ft = gem_counts.get(GemKey.FT.value, 0) or 0
    g_ff = gem_counts.get(GemKey.FF.value, 0) or 0
    g_ov = element_gem_count(gem_counts)

    # Stat gem scaling
    stats[GemKey.PP.value] = stats.get(GemKey.PP.value, 0) + g_pp * GEM_SCALE_NORMAL
    stats[GemKey.CM.value] = stats.get(GemKey.CM.value, 0) + g_cm * GEM_SCALE_NORMAL
    stats[GemKey.FM.value] = stats.get(GemKey.FM.value, 0) + g_fm * GEM_SCALE_FEVER
    stats[GemKey.FT.value] = stats.get(GemKey.FT.value, 0) + g_ft * GEM_SCALE_FEVER
    stats[GemKey.FF.value] = stats.get(GemKey.FF.value, 0) + g_ff * GEM_SCALE_FEVER

    # Stat-to-element conversion
    stats[ELEMENT_STAT_KEYS[0]] = stats.get(ELEMENT_STAT_KEYS[0], 0) + g_pp * GEM_STAT_TO_ELEMENT_SCALE
    stats[ELEMENT_STAT_KEYS[1]] = stats.get(ELEMENT_STAT_KEYS[1], 0) + g_cm * GEM_STAT_TO_ELEMENT_SCALE
    stats[ELEMENT_STAT_KEYS[2]] = stats.get(ELEMENT_STAT_KEYS[2], 0) + g_fm * GEM_STAT_TO_ELEMENT_SCALE
    stats[ELEMENT_STAT_KEYS[3]] = stats.get(ELEMENT_STAT_KEYS[3], 0) + g_ft * GEM_STAT_TO_ELEMENT_SCALE
    stats[ELEMENT_STAT_KEYS[4]] = stats.get(ELEMENT_STAT_KEYS[4], 0) + g_ff * GEM_STAT_TO_ELEMENT_SCALE

    # Elemental overflow
    if selected_element:
        stats[selected_element] = stats.get(selected_element, 0) + g_ov * ELEMENTAL_GEM_SCALE

    return stats
