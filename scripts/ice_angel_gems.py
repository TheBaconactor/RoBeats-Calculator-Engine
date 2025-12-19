import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gear_optimizer.data.database import get_db_connection, get_evolution_db_path

db_path = get_evolution_db_path()
conn = get_db_connection(db_path)

song_name = "Ice Angel (Easy) by Yooh"

# Get top base score
cursor = conn.execute("""
    SELECT score, fg_score, gear_json, minis_json, details_json, force_details_json
    FROM loadouts
    WHERE song_name = ?
    ORDER BY score DESC
    LIMIT 1
""", (song_name,))

top_base = cursor.fetchone()

# Get top FG score
cursor = conn.execute("""
    SELECT score, fg_score, gear_json, minis_json, details_json, force_details_json
    FROM loadouts
    WHERE song_name = ?
    ORDER BY fg_score DESC
    LIMIT 1
""", (song_name,))

top_fg = cursor.fetchone()

print("=" * 80)
print("ICE ANGEL (EASY) - DETAILED GEM BREAKDOWN")
print("=" * 80)

print("\n### TOP BASE SCORE LOADOUT (16,148,872) ###\n")
if top_base:
    details = json.loads(top_base['details_json']) if top_base['details_json'] else {}
    
    if 'FT' in details and 'FF' in details:
        print(f"FT (Fever Time gems): {details['FT']}")
        print(f"FF (Fever Fill gems): {details['FF']}")
    
    if 'GemCounts' in details:
        gems = details['GemCounts']
        print(f"\nAll Gem Allocations:")
        print(f"  Perfect Points: {gems.get('Perfect Points', 0)}")
        print(f"  Combo Multiplier: {gems.get('Combo Multiplier', 0)}")
        print(f"  Fever Multiplier: {gems.get('Fever Multiplier', 0)}")
        print(f"  Fever Fill Rate: {gems.get('Fever Fill Rate', 0)}")
        print(f"  Fever Time: {gems.get('Fever Time', 0)}")
        print(f"  Element: {gems.get('Element', 0)}")

print("\n### TOP FG SCORE LOADOUT (16,191,875) ###\n")
if top_fg:
    details = json.loads(top_fg['details_json']) if top_fg['details_json'] else {}
    
    if 'FT' in details and 'FF' in details:
        print(f"FT (Fever Time gems): {details['FT']}")
        print(f"FF (Fever Fill gems): {details['FF']}")
    
    if 'GemCounts' in details:
        gems = details['GemCounts']
        print(f"\nAll Gem Allocations:")
        print(f"  Perfect Points: {gems.get('Perfect Points', 0)}")
        print(f"  Combo Multiplier: {gems.get('Combo Multiplier', 0)}")
        print(f"  Fever Multiplier: {gems.get('Fever Multiplier', 0)}")
        print(f"  Fever Fill Rate: {gems.get('Fever Fill Rate', 0)}")
        print(f"  Fever Time: {gems.get('Fever Time', 0)}")
        print(f"  Element: {gems.get('Element', 0)}")
    
    force_details = json.loads(top_fg['force_details_json']) if top_fg['force_details_json'] else {}
    if force_details and 'ForceGreats' in force_details:
        fg = force_details['ForceGreats']
        if 'config' in fg:
            print(f"\nForce Greats Config: [{fg['config'].get('NonFever1', 0)}, "
                  f"{fg['config'].get('NonFever2', 0)}, "
                  f"{fg['config'].get('NonFever3', 0)}, "
                  f"{fg['config'].get('NonFever4', 0)}]")
        if 'center_ft' in fg and 'center_ff' in fg:
            print(f"\nFG Search Center:")
            print(f"  FT: {fg['center_ft']}")
            print(f"  FF: {fg['center_ff']}")

conn.close()
