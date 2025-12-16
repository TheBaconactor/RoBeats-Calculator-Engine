
import sys
import os
import json
import sqlite3

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gear_optimizer.data.database import get_evolution_db_path

def print_loadout(title, row):
    if not row:
        print(f"\n=== {title} ===")
        print("No data found.")
        return

    score = row['score']
    fg_score = row['fg_score']
    gear_json = row['gear_json']
    minis_json = row['minis_json']
    details_json = row['details_json']
    force_details_json = row['force_details_json'] if 'force_details_json' in row.keys() else None

    gear = json.loads(gear_json) if gear_json else []
    minis = json.loads(minis_json) if minis_json else []
    details = json.loads(details_json) if details_json else {}
    force_details = json.loads(force_details_json) if force_details_json else {}

    print(f"\n=== {title} ===")
    print(f"Score: {score:,}")
    print(f"FG Score: {fg_score:,}")
    
    print("\n[GEAR]")
    for g in gear:
        print(f" - {g}")
        
    print("\n[MINIS]")
    for m in minis:
        print(f" - {m}")
        
    print("\n[DETAILS DUMP]")
    # print(f"Keys in details: {list(details.keys())}")
    
    if "FT" in details:
        print(f" Fever Time (FT): {details['FT']}")
    if "FF" in details:
        print(f" Fever Fill (FF): {details['FF']}")
    
    if "Stats" in details:
        print(" Stats:")
        # Stats might be a dict or a list, handle carefully
        if isinstance(details['Stats'], dict):
             for k, v in details['Stats'].items():
                  print(f"   {k}: {v}")
        else:
             print(f"   {details['Stats']}")

    if "GemCounts" in details:
        print(" Gem Counts:")
        for k, v in details["GemCounts"].items():
            print(f"   {k}: {v}")
            
    print("\n[FORCE GREATS DETAILS]")
    if force_details:
        # print(f" Raw Keys: {list(force_details.keys())}")
        
        # Dig into details -> ForceGreats
        fd_details = force_details.get("details", {})
        fg_meta = fd_details.get("ForceGreats", {})
        
        if fg_meta:
             print(" Found ForceGreats Metadata!")
             
             # Check for 'config' (from Finder) or manual
             config = fg_meta.get("config")
             if config:
                 print(f" FG Config: {config}")
             else:
                 print(" No 'config' key found in ForceGreats meta.")
                 print(f" Valid keys: {list(fg_meta.keys())}")
                 
             if "total_penalty" in fg_meta:
                 print(f" Total Penalty: {fg_meta['total_penalty']}")
            
             # Print FG specific gems to see if they differ
             print(" [FG Specific Gems]")
             print(f"  FG FT: {fd_details.get('FT')} (Base: {details.get('FT')})")
             print(f"  FG FF: {fd_details.get('FF')} (Base: {details.get('FF')})")
             fg_gems = fd_details.get("GemCounts", {})
             base_gems = details.get("GemCounts", {})
             if fg_gems != base_gems:
                 print(f"  FG GemCounts: {fg_gems}")
             else:
                 print("  FG GemCounts: Matches Base")

        else:
             print(" No 'ForceGreats' key in force['details'].")
             # Fallback check
             if "FG_Configs" in force_details:
                 print(" Found top-level FG_Configs (Old format?)")
    else:
        print(" N/A (force_details is empty)")

def main():
    song_name = "Remember (Hard) by Juggernaut"
    db_path = get_evolution_db_path()
    
    print(f"Querying for '{song_name}'...")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    print("\n\nTOP 5 BY BASE SCORE:")
    cursor = conn.execute("""
        SELECT score, fg_score, gear_json, minis_json, details_json, force_details_json
        FROM loadouts
        WHERE song_name = ?
        ORDER BY score DESC
        LIMIT 5
    """, (song_name,))
    for i, row in enumerate(cursor):
        print(f"--- Rank {i+1} ---")
        print_loadout(f"Base Rank {i+1}", row)

    print("\n\nTOP 5 BY FG SCORE:")
    cursor = conn.execute("""
        SELECT score, fg_score, gear_json, minis_json, details_json, force_details_json
        FROM loadouts
        WHERE song_name = ?
        ORDER BY fg_score DESC
        LIMIT 5
    """, (song_name,))
    for i, row in enumerate(cursor):
        print(f"--- Rank {i+1} ---")
        print_loadout(f"FG Rank {i+1}", row)
    
    conn.close()

if __name__ == "__main__":
    main()
