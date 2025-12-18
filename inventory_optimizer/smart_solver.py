"""
Smart Solver - Inventory-Aware Gear Allocation
Solves the "Slot Lottery" problem by allocating gems to gear slots dynamically
to maximize reuse of existing inventory items.
"""

MAX_GEMS_PER_SLOT = 15
SLOT_ORDER = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]

def solve_smart_inventory(loadouts):
    """
    Process all loadouts to build a minimal inventory by maximizing reuse.
    
    Args:
        loadouts (list): List of raw loadout dicts (from db_reader)
        
    Returns:
        dict: {
            "inventory": dict of item_key -> item_data,
            "song_allocations": dict of song_name -> list of item_keys
        }
    """
    # 1. Global Inventory: Maps "ItemSignature" -> ItemData
    # Signature: "Name|PP|CM|FM|FT|FF|OV|Elem"
    inventory = {} 
    
    # Track allocations for reporting
    song_allocations = {}
    
    # Sort loadouts? 
    # Processing "simple" or "common" songs first might help establish standard items.
    
    # loadouts is a dict of {song_name: data}, so iterate values
    loadout_list = list(loadouts.values())
    
    # Sort by total gems ascending (Simple First)
    # This prioritizes creating "Standard" (Pure) items first, which maximizes reuse.
    loadout_list.sort(key=lambda x: sum(x["details"].get("GemCounts", {}).values()))
    
    for loadout in loadout_list:
        song_name = loadout["song_name"]
        details = loadout["details"]
        gear_names = loadout["gear"]
        selected_element = details.get("SelectedElement", details.get("PrimaryColor", ""))
        
        # 1. Calculate Gem Needs
        gem_counts = details.get("GemCounts", {})
        ft = details.get("FT", 0)
        ff = details.get("FF", 0)
        
        # Current needs for this song
        needs = {
            "OV": gem_counts.get("Element Overflow", 0),
            "FM": gem_counts.get("Fever Multiplier", 0),
            "FT": ft,
            "FF": ff,
            "CM": gem_counts.get("Combo Multiplier", 0),
            "PP": gem_counts.get("Perfect Points", 0)
        }
        
        # Available slots
        # Map: index -> gear_name
        available_slots = {}
        for i, name in enumerate(gear_names):
            if name and name != "(Empty)":
                available_slots[i] = name
                
        # Assignment for this song: slot_idx -> gem_dict
        current_assignment = {} 
        
        # ---------------------------------------------------------
        # PHASE 1: REUSE EXISTING INVENTORY (if it covers our needs)
        # ---------------------------------------------------------
        # Only reuse items that provide >= what we need for a slot
        
        # We need to allocate gems across 6 slots to meet total needs
        # Each slot can provide at most 15 gems
        # Strategy: For each slot, find the best existing item OR create new
        
        # First, let's see what we need total
        total_needed = sum(needs.values())
        num_slots = len(available_slots)
        
        # We'll process slots and allocate gems
        # For now, simplified: just fill slots greedily with new items
        # The "reuse" happens at item KEY level - same gem config = same item
        
        remaining_slot_indices = list(available_slots.keys())
        
        # Sort gem needs desc
        gem_priority = sorted(needs.items(), key=lambda x: x[1], reverse=True)
        
        for idx in remaining_slot_indices:
            # Create a new item for this slot
            new_item_gems = {"PP":0, "CM":0, "FM":0, "FT":0, "FF":0, "OV":0}
            current_total = 0
            
            # Fill aggressively with highest priority need
            # Re-sort priority each time? Yes, needs change.
            gem_priority = sorted(needs.items(), key=lambda x: x[1], reverse=True)
            
            for gtype, amount in gem_priority:
                if amount <= 0: continue
                if current_total >= MAX_GEMS_PER_SLOT: break
                
                space = MAX_GEMS_PER_SLOT - current_total
                take = min(space, amount)
                
                new_item_gems[gtype] += take
                current_total += take
                needs[gtype] -= take
            
            # Save this new assignment
            gear_name = available_slots[idx]
            allocation = new_item_gems
            allocation["name"] = gear_name
            allocation["total"] = current_total
            allocation["element"] = selected_element if allocation["OV"] > 0 else ""
            
            current_assignment[idx] = allocation

        # ---------------------------------------------------------
        # PHASE 3: UPDATE INVENTORY
        # ---------------------------------------------------------
        # Convert assignments to keys and store
        song_keys = []
        for idx in sorted(current_assignment.keys()): 
            # Original slot order index
            item_data = current_assignment[idx]
            
            # Generate Key
            # Use '0' for slot for now, or maybe track it if needed?
            # Smart Solver treats slots as interchangeable for the purpose of matching,
            # but the gear NAME is what matters.
            
            key_parts = [
                item_data["name"],
                str(item_data["PP"]),
                str(item_data["CM"]),
                str(item_data["FM"]),
                str(item_data["FT"]),
                str(item_data["FF"]),
                str(item_data["OV"]),
                item_data["element"]
            ]
            key = "|".join(key_parts)
            
            song_keys.append(key)
            
            # Add to global inventory if new
            if key not in inventory:
                item_data["item_key"] = key
                item_data["covers_songs"] = []
                inventory[key] = item_data
            
            # Track usage
            if song_name not in inventory[key]["covers_songs"]:
                inventory[key]["covers_songs"].append(song_name)
                
        song_allocations[song_name] = song_keys

    return {
        "inventory": inventory,
        "song_allocations": song_allocations
    }
