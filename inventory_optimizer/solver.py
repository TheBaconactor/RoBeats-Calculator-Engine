"""
ILP Solver - Finds the minimum set of items to cover all songs.

Uses the canonical gem distribution to identify unique item variants.
An item variant is defined by: (Name, PP, CM, FM, OV) gem counts.
"""


def create_item_key(gear_item):
    """Create a unique key for a gear item based on name and gem config."""
    name = gear_item.get("name", "")
    pp = gear_item.get("PP", 0)
    cm = gear_item.get("CM", 0)
    fm = gear_item.get("FM", 0)
    ft = gear_item.get("FT", 0)
    ff = gear_item.get("FF", 0)
    ov = gear_item.get("OV", 0)
    
    # Base key with all gem types
    key = f"{name}|PP{pp}|CM{cm}|FM{fm}|FT{ft}|FF{ff}|OV{ov}"
    
    # If using Element Overflow gems, the item is locked to that element.
    # If NO OV gems, the item is "Universal" (can be used by any element).
    if ov > 0:
        element = gear_item.get("element", "Unknown")
        key += f"|{element}"
    
    return key


def solve_minimum_inventory(canonical_loadouts):
    """
    Solve for the minimum inventory.
    
    Since each song has only 1 loadout (Top 1), we MUST include all items.
    This function identifies unique item variants and tracks which songs use them.
    
    Args:
        canonical_loadouts: Mapping of song_name -> canonical_loadout
    
    Returns:
        tuple: (inventory, song_assignments)
    """
    # Build universe of unique gear variants
    gear_inventory = {}  # item_key -> item_data
    mini_inventory = {}  # mini_name -> usage data
    song_assignments = {}  # song_name -> {"gear": [...], "minis": [...]}
    
    for song_name, loadout in canonical_loadouts.items():
        song_gear_keys = []
        song_mini_names = []
        
        # Process gear
        for gear_item in loadout.get("gear", []):
            name = gear_item.get("name", "")
            if not name or name == "(Empty)":
                continue
            
            item_key = create_item_key(gear_item)
            
            if item_key not in gear_inventory:
                gear_inventory[item_key] = {
                    "name": name,
                    "slot": gear_item.get("slot", ""),
                    "PP": gear_item.get("PP", 0),
                    "CM": gear_item.get("CM", 0),
                    "FM": gear_item.get("FM", 0),
                    "FT": gear_item.get("FT", 0),
                    "FF": gear_item.get("FF", 0),
                    "OV": gear_item.get("OV", 0),
                    "total_gems": gear_item.get("total", 0),
                    "used_by_songs": [],
                }
            
            gear_inventory[item_key]["used_by_songs"].append(song_name)
            song_gear_keys.append(item_key)
        
        # Process minis
        for mini_name in loadout.get("minis", []):
            if not mini_name or mini_name == "(Empty)":
                continue
            
            if mini_name not in mini_inventory:
                mini_inventory[mini_name] = {
                    "name": mini_name,
                    "used_by_songs": [],
                }
            
            mini_inventory[mini_name]["used_by_songs"].append(song_name)
            song_mini_names.append(mini_name)
        
        song_assignments[song_name] = {
            "gear": song_gear_keys,
            "minis": song_mini_names,
            "score": loadout.get("score", 0),
        }
    
    return {
        "gear": gear_inventory,
        "minis": mini_inventory,
    }, song_assignments
