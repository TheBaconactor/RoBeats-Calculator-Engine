"""
Verification Script - Validates that compressed gear covers all song requirements.

For each song, checks that the assigned physical gear items meet or exceed
the original gem requirements. Outputs a detailed verification report.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import configparser
from inventory_optimizer.db_reader import get_top1_loadouts_for_all_songs
from inventory_optimizer.canonicalizer import canonicalize_loadouts
from inventory_optimizer.solver import solve_minimum_inventory
from inventory_optimizer.compressor import compress_gear_inventory


def find_covering_item(requirement, compressed_items):
    """
    Find a physical item that covers this requirement.
    Returns the item if found, None otherwise.
    """
    req_name = requirement.get("name", "")
    req_pp = requirement.get("PP", 0)
    req_cm = requirement.get("CM", 0)
    req_fm = requirement.get("FM", 0)
    req_ov = requirement.get("OV", 0)
    req_element = requirement.get("element", "")
    
    for item in compressed_items:
        if item.get("name") != req_name:
            continue
        
        # Check if physical item covers all gem requirements
        if item.get("PP", 0) < req_pp:
            continue
        if item.get("CM", 0) < req_cm:
            continue
        if item.get("FM", 0) < req_fm:
            continue
        if item.get("OV", 0) < req_ov:
            continue
        
        # Check element compatibility
        if req_ov > 0 and req_element:
            item_elem = item.get("element", "")
            if item_elem and item_elem != req_element:
                continue
        
        return item
    
    return None


def verify_coverage(canonical_loadouts, compressed_gear):
    """
    Verify that all song requirements are covered by the compressed inventory.
    
    Returns:
        tuple: (passed, failures) where failures is a list of unmet requirements
    """
    failures = []
    
    for song_name, loadout in canonical_loadouts.items():
        for gear_item in loadout.get("gear", []):
            name = gear_item.get("name", "")
            if not name or name == "(Empty)":
                continue
            
            covering_item = find_covering_item(gear_item, compressed_gear)
            
            if covering_item is None:
                failures.append({
                    "song": song_name,
                    "requirement": gear_item,
                })
    
    passed = len(failures) == 0
    return passed, failures


def main():
    print("=" * 70)
    print("INVENTORY VERIFICATION")
    print("Checking that compressed gear covers all song requirements")
    print("=" * 70)
    
    # Load config
    cfg = configparser.ConfigParser()
    cfg.read("config.ini", encoding="utf-8-sig")
    
    difficulty = cfg.get("CalculateSong", "Difficulty", fallback="Hard").strip()
    target_primary = cfg.get("CalculateSong", "TargetPrimary", fallback="All").strip()
    target_secondary = cfg.get("CalculateSong", "TargetSecondary", fallback="All").strip()
    
    # Get loadouts
    print("\n[1/4] Loading loadouts...")
    loadouts = get_top1_loadouts_for_all_songs(
        difficulty=difficulty,
        target_primary=target_primary,
        target_secondary=target_secondary,
    )
    print(f"      {len(loadouts)} songs loaded.")
    
    # Canonicalize
    print("[2/4] Canonicalizing...")
    canonical = canonicalize_loadouts(loadouts)
    
    # Get raw requirements
    print("[3/4] Collecting requirements...")
    inventory, _ = solve_minimum_inventory(canonical)
    raw_count = len(inventory.get("gear", {}))
    
    # Compress
    print("[4/4] Compressing...")
    compressed = compress_gear_inventory(inventory.get("gear", {}))
    print(f"      {raw_count} raw → {len(compressed)} compressed")
    
    # Verify
    print("\n" + "=" * 70)
    print("VERIFICATION RESULTS")
    print("=" * 70)
    
    passed, failures = verify_coverage(canonical, compressed)
    
    if passed:
        print("\n✓ ALL REQUIREMENTS COVERED")
        print(f"  {len(canonical)} songs verified")
        print(f"  {len(compressed)} physical items sufficient")
        
        # Show sample verification
        print("\n" + "-" * 70)
        print("SAMPLE VERIFICATION (first 5 songs)")
        print("-" * 70)
        
        count = 0
        for song_name, loadout in list(canonical.items())[:5]:
            print(f"\n  Song: {song_name}")
            for gear_item in loadout.get("gear", []):
                name = gear_item.get("name", "")
                if not name or name == "(Empty)" or gear_item.get("total", 0) == 0:
                    continue
                
                covering = find_covering_item(gear_item, compressed)
                if covering:
                    print(f"    Needs: {name} (PP={gear_item['PP']} CM={gear_item['CM']} FM={gear_item['FM']} OV={gear_item['OV']})")
                    print(f"    Using: {covering['name']} (PP={covering['PP']} CM={covering['CM']} FM={covering['FM']} OV={covering['OV']}) ✓")
            count += 1
    else:
        print("\n✗ VERIFICATION FAILED")
        print(f"  {len(failures)} requirements not covered:")
        for fail in failures[:10]:
            req = fail["requirement"]
            print(f"    {fail['song']}: {req['name']} needs PP={req['PP']} CM={req['CM']} FM={req['FM']} OV={req['OV']}")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
