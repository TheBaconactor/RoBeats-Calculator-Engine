"""
Output - Generate inventory reports from compressed gear list.
"""
import json


def print_inventory_report(compressed_gear, mini_inventory, total_songs):
    """
    Print a formatted inventory report from compressed gear.
    
    Args:
        compressed_gear: List of compressed physical gear items
        mini_inventory: dict of mini requirements
        total_songs: Total songs covered
    """
    print()
    print("=" * 75)
    print("INVENTORY OPTIMIZER RESULTS")
    print("=" * 75)
    
    print(f"\nTotal Songs Covered: {total_songs}")
    print(f"Physical Gear Items to Craft: {len(compressed_gear)}")
    print(f"Unique Minis Needed: {len(mini_inventory)}")
    
    # Sort gear by total gems descending
    sorted_gear = sorted(compressed_gear, key=lambda x: (-x.get("total", 0), x.get("name", "")))
    
    # Determine Color Name for Header (e.g. Vibe++)
    # Scan items to find the common element
    found_elements = [i.get("element") for i in compressed_gear if i.get("element")]
    unique_elements = list(set(found_elements))
    if len(unique_elements) == 1:
        color_header = f"{unique_elements[0]}++"
    else:
        color_header = "Color++"
    
    # === GEAR INVENTORY ===
    print("\n" + "=" * 80)
    print("GEAR TO CRAFT (Physical Items)")
    print("=" * 80)
    # Removed Elem and Tot columns, Renamed OV
    print(f"{'Item Name':<28} {'PP':>3} {'CM':>3} {'FM':>3} {'FT':>3} {'FF':>3} {color_header:>9} {'Songs':>6}")
    print("-" * 80)
    
    total_gems_needed = 0
    for item in sorted_gear:
        name = item.get("name", "")
        pp = item.get("PP", 0)
        cm = item.get("CM", 0)
        fm = item.get("FM", 0)
        ft = item.get("FT", 0)
        ff = item.get("FF", 0)
        ov = item.get("OV", 0)
        total = item.get("total", pp + cm + fm + ft + ff + ov)
        # element = item.get("element", "")[:4] if ov > 0 else "" # Hidden now
        songs_covered = len(item.get("covers_songs", []))
        
        total_gems_needed += total
        
        display_name = name[:26] + ".." if len(name) > 28 else name
        print(f"{display_name:<28} {pp:>3} {cm:>3} {fm:>3} {ft:>3} {ff:>3} {ov:>9} {songs_covered:>6}")
    
    # === MINI INVENTORY ===
    sorted_minis = sorted(
        mini_inventory.items(),
        key=lambda x: (-len(x[1].get("used_by_songs", [])), x[0])
    )
    
    print("\n" + "=" * 75)
    print("MINIS NEEDED")
    print("=" * 75)
    print(f"{'Mini Name':<55} {'Songs':>10}")
    print("-" * 75)
    
    for mini_name, mini_data in sorted_minis:
        song_count = len(mini_data.get("used_by_songs", []))
        display_name = mini_name[:53] + ".." if len(mini_name) > 55 else mini_name
        print(f"{display_name:<55} {song_count:>10}")
    
    # === SUMMARY ===
    print("\n" + "=" * 75)
    print("CRAFTING SUMMARY")
    print("=" * 75)
    print(f"Total Gear Pieces to Craft: {len(compressed_gear)}")
    print(f"Total Gem Upgrades to Apply: {total_gems_needed}")
    print(f"Total Minis Needed: {len(mini_inventory)}")
    
    if sorted_gear:
        best = sorted_gear[0]
        print(f"\nHighest Gem Item:")
        print(f"  {best['name']}")
        print(f"  Gems: PP={best['PP']} CM={best['CM']} FM={best['FM']} OV={best['OV']}")
        print(f"  Covers {len(best.get('covers_songs', []))} songs")
    
    print("=" * 75)
    
    # Save to CSV
    _save_csv(compressed_gear, mini_inventory)


def _save_csv(compressed_gear, mini_inventory):
    """Save compressed inventory to CSV files."""
    import csv
    
    # Save gear inventory
    gear_path = "inventory_gear.csv"
    with open(gear_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "PP", "CM", "FM", "FT", "FF", "OV", "Element", "Total", "Songs"])
        
        for item in compressed_gear:
            writer.writerow([
                item.get("name", ""),
                item.get("PP", 0),
                item.get("CM", 0),
                item.get("FM", 0),
                item.get("FT", 0),
                item.get("FF", 0),
                item.get("OV", 0),
                item.get("element", ""),
                item.get("total", 0),
                len(item.get("covers_songs", []))
            ])
    
    # Save mini inventory
    mini_path = "inventory_minis.csv"
    with open(mini_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Mini Name", "Songs"])
        
        for name, data in mini_inventory.items():
            writer.writerow([name, len(data.get("used_by_songs", []))])
    
    print(f"\nInventory saved to: {gear_path}, {mini_path}")
