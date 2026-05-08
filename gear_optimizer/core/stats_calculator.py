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
from .gem_defs import ELEMENT_STAT_KEYS, GemKey
from .team_buff import team_buff_effect, resolve_baseline_team_buff_from_cfg_dict, resolve_team_color_from_cfg_dict
from .config_adapter import UserGemSettings


def build_base_stats_from_config(cfg_dict):
    """
    Build base stats from config including user input gems, elemental gems, and team buffs.

    Args:
        cfg_dict: Config dictionary (from cfg_to_dict or similar)

    Returns:
        dict: Base stats with config contributions applied
    """
    gems = UserGemSettings.from_cfg_dict(cfg_dict)

    g_pp = gems.perfect_points
    g_cm = gems.combo_multiplier
    g_fm = gems.fever_multiplier
    g_ff = gems.fever_fill_rate
    g_ft = gems.fever_time

    base_stats = {
        "Perfect Points": g_pp * GEM_SCALE_NORMAL,
        "Combo Multiplier": g_cm * GEM_SCALE_NORMAL,
        "Fever Multiplier": g_fm * GEM_SCALE_FEVER,
        "Fever Fill Rate": g_ff * GEM_SCALE_FEVER,
        "Fever Time": g_ft * GEM_SCALE_FEVER,
        "Chill": g_pp * GEM_STAT_TO_ELEMENT_SCALE,
        "Flow": g_cm * GEM_STAT_TO_ELEMENT_SCALE,
        "Rush": g_fm * GEM_STAT_TO_ELEMENT_SCALE,
        "Beat": g_ft * GEM_STAT_TO_ELEMENT_SCALE,
        "Vibe": g_ff * GEM_STAT_TO_ELEMENT_SCALE,
    }

    if gems.elemental_overflow:
        for el, val in gems.elemental_overflow.items():
            if val > 0:
                base_stats[el] = base_stats.get(el, 0) + val * ELEMENTAL_GEM_SCALE

    team_buff = resolve_baseline_team_buff_from_cfg_dict(cfg_dict, default="T5")
    team_color = resolve_team_color_from_cfg_dict(cfg_dict)

    for stat_name, delta in team_buff_effect(team_buff, team_color).items():
        base_stats[stat_name] = base_stats.get(stat_name, 0) + int(delta)

    return base_stats


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
    g_ov = gem_counts.get(GemKey.ELEMENT.value, 0) or gem_counts.get("Element Overflow", 0) or 0

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
