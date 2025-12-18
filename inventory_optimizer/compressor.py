"""
Gear Compressor - Merges compatible gear requirements into minimal physical items.

Given all gear requirements from Top 1 loadouts, this module finds the
minimal set of "physical" gear items that can satisfy all requirements.

Algorithm: First-Fit Decreasing Bin Packing
- Group requirements by gear name
- For each gear name, merge compatible requirements (same element or universal)
- Each physical item has a max of 15 gems

Example:
  Song A needs "Wings + 10 PP"
  Song B needs "Wings + 5 CM"
  -> Craft ONE "Wings + 10 PP + 5 CM" (15 total, covers both)
"""

MAX_GEMS_PER_ITEM = 15


def can_merge(item1, item2):
    """
    Check if two gear requirements can be merged into one physical item.
    
    Requirements:
    1. Same gear name
    2. Combined gems <= 15
    3. If both use OV gems, they must have the same element
    """
    if item1["name"] != item2["name"]:
        return False
    
    # Calculate combined totals using MAX (not sum) for each gem type
    # This is because a song "needs" a certain level, and a higher level covers it
    combined_pp = max(item1["PP"], item2["PP"])
    combined_cm = max(item1["CM"], item2["CM"])
    combined_fm = max(item1["FM"], item2["FM"])
    combined_ft = max(item1.get("FT", 0), item2.get("FT", 0))
    combined_ff = max(item1.get("FF", 0), item2.get("FF", 0))
    combined_ov = max(item1["OV"], item2["OV"])
    
    combined_total = combined_pp + combined_cm + combined_fm + combined_ft + combined_ff + combined_ov
    
    if combined_total > MAX_GEMS_PER_ITEM:
        return False
    
    # Element compatibility: if both have OV gems, elements must match
    if item1["OV"] > 0 and item2["OV"] > 0:
        if item1.get("element", "") != item2.get("element", ""):
            return False
    
    return True


def merge_items(item1, item2):
    """
    Merge two compatible requirements into one physical item.
    Uses MAX for each gem type to create a "super item" that covers both.
    """
    merged = {
        "name": item1["name"],
        "PP": max(item1["PP"], item2["PP"]),
        "CM": max(item1["CM"], item2["CM"]),
        "FM": max(item1["FM"], item2["FM"]),
        "FT": max(item1.get("FT", 0), item2.get("FT", 0)),
        "FF": max(item1.get("FF", 0), item2.get("FF", 0)),
        "OV": max(item1["OV"], item2["OV"]),
        "slot": item1.get("slot", ""),
        "covers_songs": list(set(item1.get("covers_songs", []) + item2.get("covers_songs", []))),
    }
    merged["total"] = merged["PP"] + merged["CM"] + merged["FM"] + merged["FT"] + merged["FF"] + merged["OV"]
    
    # Preserve element if either has OV
    if item1["OV"] > 0:
        merged["element"] = item1.get("element", "")
    elif item2["OV"] > 0:
        merged["element"] = item2.get("element", "")
    else:
        merged["element"] = ""
    
    return merged


def compress_gear_inventory(raw_inventory):
    """
    Compress a raw inventory of gear requirements into minimal physical items.
    
    Args:
        raw_inventory: dict from solver.py, mapping item_key -> item_data
    
    Returns:
        list: Minimal list of physical items to craft
    """
    # Group requirements by gear name
    by_name = {}
    for item_key, item_data in raw_inventory.items():
        name = item_data["name"]
        if name not in by_name:
            by_name[name] = []
        
        # Normalize the requirement
        req = {
            "name": name,
            "PP": item_data.get("PP", 0),
            "CM": item_data.get("CM", 0),
            "FM": item_data.get("FM", 0),
            "FT": item_data.get("FT", 0),
            "FF": item_data.get("FF", 0),
            "OV": item_data.get("OV", 0),
            "slot": item_data.get("slot", ""),
            "element": "",  # Will be set below
            "covers_songs": item_data.get("used_by_songs", []),
        }
        req["total"] = req["PP"] + req["CM"] + req["FM"] + req["FT"] + req["FF"] + req["OV"]
        
        # Extract element from key or infer from data
        if req["OV"] > 0 and "|" in item_key:
            parts = item_key.split("|")
            if len(parts) > 4:  # Has element suffix
                req["element"] = parts[-1]
        
        by_name[name].append(req)
    
    # For each gear name, compress using First-Fit Decreasing
    compressed = []
    
    for gear_name, requirements in by_name.items():
        # Sort by total gems descending (larger first for better packing)
        requirements.sort(key=lambda x: -x["total"])
        
        # Initialize empty bins (physical items)
        physical_items = []
        
        for req in requirements:
            placed = False
            
            # Try to fit into an existing bin
            for i, p_item in enumerate(physical_items):
                if can_merge(p_item, req):
                    physical_items[i] = merge_items(p_item, req)
                    placed = True
                    break
            
            # If no fit, create a new bin
            if not placed:
                new_item = {
                    "name": req["name"],
                    "PP": req["PP"],
                    "CM": req["CM"],
                    "FM": req["FM"],
                    "FT": req.get("FT", 0),
                    "FF": req.get("FF", 0),
                    "OV": req["OV"],
                    "slot": req["slot"],
                    "element": req["element"],
                    "covers_songs": req.get("covers_songs", []),
                    "total": req["total"],
                }
                physical_items.append(new_item)
        
        compressed.extend(physical_items)
    
    return compressed
