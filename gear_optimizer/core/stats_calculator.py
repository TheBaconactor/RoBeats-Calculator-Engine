"""
Shared stats calculation utilities.

Consolidates stats computation logic from backfill_stats.py and song_preloader.py
to ensure consistency and reduce maintenance burden.
"""

from .constants import (
    GEM_SCALE_NORMAL,
    GEM_SCALE_FEVER,
    ELEMENTAL_GEM_SCALE,
    GEM_STAT_TO_ELEMENT_SCALE,
    SKIP_ITEM_KEYS,
)


def build_base_stats_from_config(cfg_dict):
    """
    Build base stats from config including user input gems, elemental gems, and team buffs.

    Args:
        cfg_dict: Config dictionary (from cfg_to_dict or similar)

    Returns:
        dict: Base stats with config contributions applied
    """
    s = cfg_dict.get("UserInputStatsGems", {}) or {}
    elem = cfg_dict.get("ElementalGems", {}) or {}

    def _to_int(v) -> int:
        try:
            if v is None:
                return 0
            text = str(v).strip()
            if not text:
                return 0
            return int(text)
        except Exception:
            return 0

    # UserInputStatsGems values are GEM COUNTS (not raw stats).
    g_pp = _to_int(s.get("perfect_points", 0))
    g_cm = _to_int(s.get("combo_multiplier", 0))
    g_fm = _to_int(s.get("fever_multiplier", 0))
    g_ff = _to_int(s.get("fever_fill", s.get("fever_fill_rate", 0)))
    g_ft = _to_int(s.get("fever_time", 0))

    base_stats = {
        # Stat gem scaling
        "Perfect Points": g_pp * GEM_SCALE_NORMAL,
        "Combo Multiplier": g_cm * GEM_SCALE_NORMAL,
        "Fever Multiplier": g_fm * GEM_SCALE_FEVER,
        "Fever Fill Rate": g_ff * GEM_SCALE_FEVER,
        "Fever Time": g_ft * GEM_SCALE_FEVER,
        # Stat-to-element conversion
        "Chill": g_pp * GEM_STAT_TO_ELEMENT_SCALE,
        "Flow": g_cm * GEM_STAT_TO_ELEMENT_SCALE,
        "Rush": g_fm * GEM_STAT_TO_ELEMENT_SCALE,
        "Beat": g_ft * GEM_STAT_TO_ELEMENT_SCALE,
        "Vibe": g_ff * GEM_STAT_TO_ELEMENT_SCALE,
    }

    # Elemental gems (overflow gems) for each element.
    elements = ["Chill", "Flow", "Rush", "Beat", "Vibe"]
    for el in elements:
        raw = elem.get(el, elem.get(el.lower(), 0))
        gem_val = _to_int(raw)
        if gem_val > 0:
            base_stats[el] = base_stats.get(el, 0) + gem_val * ELEMENTAL_GEM_SCALE

    # Apply Team Buffs
    team_section = cfg_dict.get("TeamContributionBuffConstant", {}) or {}
    team_buff = str(team_section.get("teambuff", team_section.get("TeamBuff", ""))).strip().upper()
    team_color = str(team_section.get("teamcolor", team_section.get("TeamColor", ""))).strip()

    buff_tiers = {
        "T1": {"PP": 25, "Elem": 35},
        "T5": {"PP": 25, "Elem": 30},
        "T10": {"PP": 20, "Elem": 25},
        "T15": {"PP": 15, "Elem": 20},
    }

    if team_buff in buff_tiers:
        buff_data = buff_tiers[team_buff]
        base_stats["Perfect Points"] += buff_data["PP"]
        valid_color_key = next((k for k in elements if k.lower() == team_color.lower()), None)
        if valid_color_key:
            base_stats[valid_color_key] += buff_data["Elem"]
        elif team_color:
            # Match legacy behavior in csv_parser.get_fixed_stats().
            base_stats["Perfect Points"] += buff_data["PP"]

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
    g_pp = gem_counts.get("Perfect Points", 0) or 0
    g_cm = gem_counts.get("Combo Multiplier", 0) or 0
    g_fm = gem_counts.get("Fever Multiplier", 0) or 0
    g_ft = gem_counts.get("Fever Time", 0) or 0
    g_ff = gem_counts.get("Fever Fill Rate", 0) or 0
    g_ov = gem_counts.get("Element", 0) or gem_counts.get("Element Overflow", 0) or 0

    # Stat gem scaling
    stats["Perfect Points"] = stats.get("Perfect Points", 0) + g_pp * GEM_SCALE_NORMAL
    stats["Combo Multiplier"] = stats.get("Combo Multiplier", 0) + g_cm * GEM_SCALE_NORMAL
    stats["Fever Multiplier"] = stats.get("Fever Multiplier", 0) + g_fm * GEM_SCALE_FEVER
    stats["Fever Time"] = stats.get("Fever Time", 0) + g_ft * GEM_SCALE_FEVER
    stats["Fever Fill Rate"] = stats.get("Fever Fill Rate", 0) + g_ff * GEM_SCALE_FEVER

    # Stat-to-element conversion
    stats["Chill"] = stats.get("Chill", 0) + g_pp * GEM_STAT_TO_ELEMENT_SCALE
    stats["Flow"] = stats.get("Flow", 0) + g_cm * GEM_STAT_TO_ELEMENT_SCALE
    stats["Rush"] = stats.get("Rush", 0) + g_fm * GEM_STAT_TO_ELEMENT_SCALE
    stats["Beat"] = stats.get("Beat", 0) + g_ft * GEM_STAT_TO_ELEMENT_SCALE
    stats["Vibe"] = stats.get("Vibe", 0) + g_ff * GEM_STAT_TO_ELEMENT_SCALE

    # Elemental overflow
    if selected_element:
        stats[selected_element] = stats.get(selected_element, 0) + g_ov * ELEMENTAL_GEM_SCALE

    return stats
