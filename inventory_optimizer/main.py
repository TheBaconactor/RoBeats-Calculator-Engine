"""
Inventory Optimizer - Main Entry Point

This is a standalone tool that analyzes your gear optimizer database
and determines the minimal set of gear items (with specific gem configurations)
needed to achieve the best loadout for all songs.

Usage:
    python -m inventory_optimizer.main

Reads config.ini for:
    - Difficulty (Easy/Normal/Hard)
    - TargetPrimary (color filter or All)
    - TargetSecondary (color filter or All)
"""
import configparser
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from inventory_optimizer.db_reader import get_top1_loadouts_for_all_songs
from inventory_optimizer.smart_solver import solve_smart_inventory
from inventory_optimizer.output import print_inventory_report


def main():
    print("=" * 60)
    print("INVENTORY OPTIMIZER (Smart Reuse)")
    print("Finds the minimum gear set to cover all songs")
    print("=" * 60)
    
    # Read config
    cfg = configparser.ConfigParser()
    cfg.read("config.ini", encoding="utf-8-sig")
    
    difficulty = cfg.get("CalculateSong", "Difficulty", fallback="Hard").strip()
    target_primary = cfg.get("CalculateSong", "TargetPrimary", fallback="All").strip()
    target_secondary = cfg.get("CalculateSong", "TargetSecondary", fallback="All").strip()
    
    print(f"\nFilters:")
    print(f"  Difficulty: {difficulty}")
    print(f"  Primary Color: {target_primary}")
    print(f"  Secondary Color: {target_secondary}")
    print()
    
    # Step 1: Pull Top 1 loadouts from database
    print("[1/4] Loading Top 1 loadouts from database...")
    loadouts = get_top1_loadouts_for_all_songs(
        difficulty=difficulty,
        target_primary=target_primary,
        target_secondary=target_secondary,
    )
    print(f"      Found {len(loadouts)} songs with loadouts.")
    
    if not loadouts:
        print("ERROR: No loadouts found. Run the gear optimizer first.")
        return
    
    # Step 2: Smart Solve
    print("[2/4] Solving inventory with reuse strategy...")
    result = solve_smart_inventory(loadouts)
    inventory = result["inventory"]
    
    # Collect minis (solver only handles gear)
    minis_needed = {}
    for loadout in loadouts.values():
        song_name = loadout["song_name"]
        for mini in loadout.get("minis", []):
            if mini and mini != "(Empty)":
                if mini not in minis_needed:
                    minis_needed[mini] = {"used_by_songs": []}
                if song_name not in minis_needed[mini]["used_by_songs"]:
                    minis_needed[mini]["used_by_songs"].append(song_name)
    
    # Format for output (convert dict to list of items)
    final_items = list(inventory.values())
    
    print(f"      Inventory Size: {len(final_items)} items")

    # Step 3: Verify & Simulate Swaps
    print("[3/4] Verifying and simulating swaps...")
    
    # Calculate swap stats
    song_names = sorted(result["song_allocations"].keys())
    allocations = result["song_allocations"]
    
    total_swaps = 0
    max_swaps = 0
    swap_counts = []
    current_keys = [] # Equipped gear
    
    for i, song in enumerate(song_names):
        next_keys = allocations[song]
        
        if i > 0:
            # Count differences
            current_set = set(current_keys)
            next_set = set(next_keys)
            added = next_set - current_set
            
            swaps = len(added)
            total_swaps += swaps
            swap_counts.append(swaps)
            
            if swaps > max_swaps:
                max_swaps = swaps
        
        current_keys = next_keys

    # Print Stats Report
    print(f"\n{'='*40}")
    print("VERIFICATION & SWAP STATS")
    print(f"{'='*40}")
    print(f"Total Songs Covered: {len(song_names)}")
    print(f"Total Transitions: {len(song_names) - 1}")
    print(f"Total Swaps Needed: {total_swaps}")
    
    if swap_counts:
        avg = total_swaps / len(swap_counts)
        print(f"Average Swaps per Song: {avg:.2f}")
        print(f"Max Swaps: {max_swaps}")
        
    print(f"Zero-Swap Transitions: {swap_counts.count(0)} ({swap_counts.count(0)/len(swap_counts)*100:.1f}%)")
    print(f"{'='*40}\n")

    # Step 4: Output results
    print("[4/4] Generating inventory report...")
    print_inventory_report(final_items, minis_needed, len(loadouts))


if __name__ == "__main__":
    main()
