"""
Canonicalizer - Deterministic gem distribution for standardized items.

The database stores TOTAL gem counts per loadout. This module distributes
them across gear pieces using a deterministic filling order so that
identical gem requirements produce identical item definitions.

Rule: Fill slots in order (Hat -> Neck -> Face -> Shirt -> Back -> Pants),
      with a maximum of 15 gems per item.
      
Gem types are tracked separately: PP, CM, FM, OV (overflow), plus FT/FF fever gems.
"""

# Maximum gems per gear piece (game limit)
MAX_GEMS_PER_GEAR = 15

# Slot order for deterministic filling
SLOT_ORDER = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]


def distribute_gems_across_gear(gear_names, gem_counts, ft_gems, ff_gems, selected_element):
    """
    Distribute gems across gear pieces in a deterministic order.
    
    Args:
        gear_names: List of 6 gear names (one per slot)
        gem_counts: Dict with PP, CM, FM, OV gem counts
        ft_gems: Fever Time gem count (from details["FT"])
        ff_gems: Fever Fill gem count (from details["FF"])
        selected_element: The overflow element (e.g., "Rush")
    
    Returns:
        list: List of dicts, one per gear slot, with gem breakdown
    """
    # Total gems to distribute
    pp_gems = gem_counts.get("Perfect Points", 0)
    cm_gems = gem_counts.get("Combo Multiplier", 0)
    fm_gems = gem_counts.get("Fever Multiplier", 0)
    ov_gems = gem_counts.get("Element Overflow", 0)
    
    # Create list of gem counts
    gem_list = [
        ("OV", ov_gems),
        ("FM", fm_gems),
        ("FT", ft_gems),
        ("FF", ff_gems),
        ("CM", cm_gems),
        ("PP", pp_gems),
    ]
    
    # Initialize gear slots
    gear_gems = []
    
    # Strategy: "Pin-Mixed-Last"
    # 1. Allocate full chunks (15) of gems to slots starting from 0 (Hat).
    # 2. Collect all remainders (count % 15).
    # 3. Fill remainders into slots starting from LAST (Pants) backwards.
    # This maximizes Pure items at the start, and pins variance to the end.
    
    # Sort gems by count descending to keep biggest chunks together
    gem_list = [
        ("OV", ov_gems),
        ("FM", fm_gems),
        ("FT", ft_gems),
        ("FF", ff_gems),
        ("CM", cm_gems),
        ("PP", pp_gems),
    ]
    gem_list.sort(key=lambda x: x[1], reverse=True)
    
    # Strategy: Fixed Order Filling (Original)
    # This proved to be the most efficient (147 items) vs dynamic sorting (280+ items).
    # Consistency > optimization for this specific dataset.
    
    # Create queue of gems to distribute (order: PP, CM, FM, FT, FF, OV)
    gem_queue = []
    gem_queue.extend([("PP", 1)] * pp_gems)
    gem_queue.extend([("CM", 1)] * cm_gems)
    gem_queue.extend([("FM", 1)] * fm_gems)
    gem_queue.extend([("FT", 1)] * ft_gems)
    gem_queue.extend([("FF", 1)] * ff_gems)
    gem_queue.extend([("OV", 1)] * ov_gems)
    
    # Initialize gear slots
    gear_gems = []
    for i, gear_name in enumerate(gear_names):
        gear_gems.append({
            "slot": SLOT_ORDER[i] if i < len(SLOT_ORDER) else f"Slot{i}",
            "name": gear_name if gear_name else "(Empty)",
            "PP": 0, "CM": 0, "FM": 0, "FT": 0, "FF": 0, "OV": 0,
            "total": 0,
            "element": selected_element,
        })
        
    # Distribute gems greedily
    slot_idx = 0
    for gem_type, count in gem_queue:
        # Find next slot with capacity
        while slot_idx < len(gear_gems):
            if gear_gems[slot_idx]["total"] < MAX_GEMS_PER_GEAR:
                break
            slot_idx += 1
        
        if slot_idx >= len(gear_gems):
            # No more capacity (shouldn't happen with valid data)
            break
        
        gear_gems[slot_idx][gem_type] += count
        gear_gems[slot_idx]["total"] += count
    
    return gear_gems


def canonicalize_single_loadout(loadout_data):
    """
    Convert a loadout's gem counts into canonical per-item allocations.
    
    Args:
        loadout_data: Dict with 'gear', 'minis', 'details' keys
    
    Returns:
        dict: Canonical loadout with detailed gem breakdown per item
    """
    gear_names = loadout_data.get("gear", [])
    minis = loadout_data.get("minis", [])
    details = loadout_data.get("details", {})
    
    # Extract gem counts
    gem_counts = details.get("GemCounts", {})
    ft_gems = details.get("FT", 0)
    ff_gems = details.get("FF", 0)
    selected_element = details.get("SelectedElement", details.get("PrimaryColor", "Rush"))
    
    # Distribute gems to gear
    gear_with_gems = distribute_gems_across_gear(gear_names, gem_counts, ft_gems, ff_gems, selected_element)
    
    return {
        "song_name": loadout_data.get("song_name", ""),
        "score": loadout_data.get("score", 0),
        "gear": gear_with_gems,  # List of dicts with gem breakdown
        "minis": minis,          # List of mini names
        "selected_element": selected_element,
        "details": details,
    }


def canonicalize_loadouts(loadouts_dict):
    """
    Canonicalize all loadouts in the dictionary.
    
    Args:
        loadouts_dict: Mapping of song_name -> loadout_data
    
    Returns:
        dict: Mapping of song_name -> canonical_loadout
    """
    result = {}
    for song_name, loadout_data in loadouts_dict.items():
        result[song_name] = canonicalize_single_loadout(loadout_data)
    return result
