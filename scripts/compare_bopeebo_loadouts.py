import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gear_optimizer.data.database import get_db_connection, get_evolution_db_path

db_path = get_evolution_db_path()
conn = get_db_connection(db_path)

song_name = "Bopeebo (Hard) by Kawai Sprite"

print("=" * 80)
print(f"Comparing Top Loadouts for: {song_name}")
print("=" * 80)

# Get top BASE score loadout
print("\n### TOP BASE SCORE LOADOUT ###")
cursor = conn.execute("""
    SELECT score, fg_score, gear_json, minis_json, details_json, force_details_json
    FROM loadouts
    WHERE song_name = ?
    ORDER BY score DESC
    LIMIT 1
""", (song_name,))

base_loadout = cursor.fetchone()
if base_loadout:
    gear = json.loads(base_loadout['gear_json']) if base_loadout['gear_json'] else []
    minis = json.loads(base_loadout['minis_json']) if base_loadout['minis_json'] else []
    details = json.loads(base_loadout['details_json']) if base_loadout['details_json'] else {}
    
    print(f"\nBase Score: {base_loadout['score']:,}")
    print(f"FG Score: {base_loadout['fg_score']:,}")
    
    print(f"\nGear:")
    for i, g in enumerate(gear, 1):
        print(f"  {i}. {g}")
    
    print(f"\nMinis:")
    for i, m in enumerate(minis, 1):
        print(f"  {i}. {m}")
    
    if details and 'GemCounts' in details:
        gems = details['GemCounts']
        print(f"\nGem Upgrades:")
        for gem_type in ['Perfect Points', 'Combo Multiplier', 'Fever Multiplier', 'Fever Fill Rate', 'Fever Time']:
            if gem_type in gems:
                print(f"  {gem_type}: {gems[gem_type]}")
        
        print(f"\nElemental Gems:")
        for elem in ['Chill', 'Flow', 'Rush', 'Beat', 'Vibe']:
            if elem in gems:
                print(f"  {elem}: {gems[elem]}")
        
        if 'Element' in gems:
            print(f"  Overflow: {gems['Element']}")
    
    if details and 'Stats' in details:
        stats = details['Stats']
        print(f"\nFinal Stats:")
        for stat in ['Perfect Points', 'Combo Multiplier', 'Fever Multiplier', 'Fever Fill Rate', 'Fever Time']:
            if stat in stats:
                print(f"  {stat}: {stats[stat]}")

# Get top FG score loadout
print("\n\n### TOP FG SCORE LOADOUT ###")
cursor = conn.execute("""
    SELECT score, fg_score, gear_json, minis_json, details_json, force_details_json
    FROM loadouts
    WHERE song_name = ?
    ORDER BY fg_score DESC
    LIMIT 1
""", (song_name,))

fg_loadout = cursor.fetchone()
if fg_loadout:
    gear = json.loads(fg_loadout['gear_json']) if fg_loadout['gear_json'] else []
    minis = json.loads(fg_loadout['minis_json']) if fg_loadout['minis_json'] else []
    details = json.loads(fg_loadout['details_json']) if fg_loadout['details_json'] else {}
    force_details = json.loads(fg_loadout['force_details_json']) if fg_loadout['force_details_json'] else {}
    
    print(f"\nBase Score: {fg_loadout['score']:,}")
    print(f"FG Score: {fg_loadout['fg_score']:,}")
    
    print(f"\nGear:")
    for i, g in enumerate(gear, 1):
        print(f"  {i}. {g}")
    
    print(f"\nMinis:")
    for i, m in enumerate(minis, 1):
        print(f"  {i}. {m}")
    
    if details and 'GemCounts' in details:
        gems = details['GemCounts']
        print(f"\nGem Upgrades:")
        for gem_type in ['Perfect Points', 'Combo Multiplier', 'Fever Multiplier', 'Fever Fill Rate', 'Fever Time']:
            if gem_type in gems:
                print(f"  {gem_type}: {gems[gem_type]}")
        
        print(f"\nElemental Gems:")
        for elem in ['Chill', 'Flow', 'Rush', 'Beat', 'Vibe']:
            if elem in gems:
                print(f"  {elem}: {gems[elem]}")
        
        if 'Element' in gems:
            print(f"  Overflow: {gems['Element']}")
    
    if force_details and 'ForceGreats' in force_details:
        fg = force_details['ForceGreats']
        if 'config' in fg:
            print(f"\nForce Greats Config:")
            print(f"  Section 1: {fg['config'].get('NonFever1', 0)}")
            print(f"  Section 2: {fg['config'].get('NonFever2', 0)}")
            print(f"  Section 3: {fg['config'].get('NonFever3', 0)}")
            print(f"  Section 4: {fg['config'].get('NonFever4', 0)}")

print("\n" + "=" * 80)
print("COMPARISON")
print("=" * 80)
if base_loadout and fg_loadout:
    base_gear = json.loads(base_loadout['gear_json']) if base_loadout['gear_json'] else []
    fg_gear = json.loads(fg_loadout['gear_json']) if fg_loadout['gear_json'] else []
    
    if base_gear != fg_gear:
        print("\n❌ Different gear sets!")
        print(f"Base loadout gear: {base_gear}")
        print(f"FG loadout gear: {fg_gear}")
    else:
        print("\n✓ Same gear set")
    
    base_minis = json.loads(base_loadout['minis_json']) if base_loadout['minis_json'] else []
    fg_minis = json.loads(fg_loadout['minis_json']) if fg_loadout['minis_json'] else []
    
    if base_minis != fg_minis:
        print("\n❌ Different mini sets!")
        print(f"Base loadout minis: {base_minis}")
        print(f"FG loadout minis: {fg_minis}")
    else:
        print("\n✓ Same mini set")

conn.close()
