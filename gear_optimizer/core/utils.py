"""
Utility functions and helpers for the gear optimizer.
Pure functions with no external dependencies.
"""
import configparser
from .constants import SKIP_ITEM_KEYS


# --- STAT KEYS / HELPERS ---
STAT_KEYS = [
    "Perfect Points",
    "Combo Multiplier",
    "Fever Multiplier",
    "Fever Fill Rate",
    "Fever Time",
    "Chill",
    "Flow",
    "Rush",
    "Beat",
    "Vibe",
]

# Alias for gear dominance pruning (same keys used for dominance comparison)
DOMINANCE_KEYS = STAT_KEYS


def cfg_to_dict(cfg):
    """
    Serialize ConfigParser to a plain dict for safe process transport.

    Args:
        cfg: ConfigParser instance

    Returns:
        dict: Serialized configuration
    """
    return {section: dict(cfg.items(section)) for section in cfg.sections()}


def cfg_from_dict(cfg_dict):
    """
    Rehydrate ConfigParser from a plain dict copy.

    Args:
        cfg_dict: Dictionary with config sections

    Returns:
        ConfigParser: Reconstructed configuration object
    """
    cfg = configparser.ConfigParser()
    for section, items in cfg_dict.items():
        if not cfg.has_section(section):
            cfg.add_section(section)
        for k, v in items.items():
            cfg.set(section, k, v)
    return cfg


def empty_stats():
    """
    Return a fresh stats dict with all relevant keys initialized to 0.

    Returns:
        dict: Stats dictionary with all keys set to 0
    """
    return {k: 0 for k in STAT_KEYS}


def safe_int(val, default=0):
    """
    Safely convert a value to an integer with fallback.

    Args:
        val: Value to convert (str, int, float, or None)
        default: Default value if conversion fails

    Returns:
        int: Converted integer or default

    Examples:
        >>> safe_int("123")
        123
        >>> safe_int("invalid", 999)
        999
        >>> safe_int(None, 0)
        0
    """
    try:
        if val is None:
            return default
        s = str(val).strip()
        if not s:
            return default
        # Prefer direct int parsing to avoid float precision loss on large IDs
        try:
            return int(s, 10)
        except ValueError:
            return int(float(s))
    except Exception:
        return default


def safe_float(val, default=0.0):
    """
    Safely convert a value to a float with fallback.

    Args:
        val: Value to convert
        default: Default value if conversion fails

    Returns:
        float: Converted float or default

    Examples:
        >>> safe_float("3.14")
        3.14
        >>> safe_float("-")
        0.0
    """
    try:
        if not val or val == "-":
            return default
        return float(val)
    except Exception:
        return default


def stats_signature(stats, calc_song, selected_color):
    """
    Compute a cache key that captures exactly the inputs influencing the gem
    solver for a given song context. Two loadouts with the same signature will
    produce identical gem allocations and scores.

    Key insight: elemental stats only matter if they feed into the song's
    Primary/Secondary/Selected Element paths. Differences in other elements
    are irrelevant and should share the same cache entry.

    Args:
        stats: Stats dictionary
        calc_song: Song calculation context
        selected_color: Selected element color

    Returns:
        tuple: Hashable signature for caching
    """
    meta = calc_song["metadata"]
    p_color = meta.get("Primary Color", "")
    s_color = meta.get("Secondary Color", "")

    gs = stats.get

    # Mirror the same Beat/Vibe mapping the solver uses
    base_beat = gs("Beat", 0)
    base_vibe = gs("Vibe", 0)

    def get_val_inline(k):
        if k == "Beat":
            return base_beat
        if k == "Vibe":
            return base_vibe
        return gs(k, 0)

    # Only capture elemental values that actually feed into P/S lanes
    base_p_val = get_val_inline(p_color)
    base_s_val = get_val_inline(s_color)

    return (
        meta.get("Song Name", ""),
        meta.get("Difficulty", ""),
        selected_color,
        p_color,
        s_color,
        gs("Perfect Points", 0),
        gs("Combo Multiplier", 0),
        gs("Fever Multiplier", 0),
        gs("Fever Fill Rate", 0),
        gs("Fever Time", 0),
        base_p_val,
        base_s_val,
    )


def is_dominated_by(a, b):
    """
    Check if gear 'a' is strictly dominated by gear 'b'.

    Returns True if:
      - b[stat] >= a[stat] for ALL stats in DOMINANCE_KEYS, AND
      - b[stat] > a[stat] for AT LEAST ONE stat

    This means 'a' can never be optimal if 'b' is available.

    Args:
        a: First gear item (dict)
        b: Second gear item (dict)

    Returns:
        bool: True if 'a' is dominated by 'b'
    """
    dominated = all(b.get(k, 0) >= a.get(k, 0) for k in DOMINANCE_KEYS)
    if not dominated:
        return False
    strictly_better = any(b.get(k, 0) > a.get(k, 0) for k in DOMINANCE_KEYS)
    return strictly_better


def prune_dominated_gear(gear_list):
    """
    Remove gear items that are strictly dominated by another gear in the list.

    For each gear, check if any other gear in the list dominates it.
    Only keep gear that is NOT dominated by any other.

    Args:
        gear_list: List of gear dictionaries

    Returns:
        list: New list with dominated gear removed
    """
    if len(gear_list) <= 1:
        return gear_list

    pruned = []
    for g in gear_list:
        dominated = False
        for other in gear_list:
            if other is g:
                continue
            if is_dominated_by(g, other):
                dominated = True
                break
        if not dominated:
            pruned.append(g)
    return pruned
