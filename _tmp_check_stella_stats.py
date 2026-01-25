import sqlite3
import json

conn = sqlite3.connect('evolution.db')
conn.row_factory = sqlite3.Row

# Check for the "a lonely stella" song
rows = conn.execute("""
    SELECT song_name, score, fg_score, details_json, gear_json, minis_json
    FROM loadouts 
    WHERE song_name LIKE '%lonely stella%'
    ORDER BY fg_score DESC
    LIMIT 3
""").fetchall()

print(f"Found {len(rows)} entries for 'a lonely stella'\n")

for i, row in enumerate(rows, 1):
    print(f"{'='*70}")
    print(f"Entry #{i}: {row['song_name']}")
    print(f"Score: {row['score']:,}, FG Score: {row['fg_score']:,}")
    print(f"{'='*70}")
    
    if not row['details_json']:
        print("  ❌ details_json is NULL\n")
        continue
    
    details = json.loads(row['details_json'])
    
    print(f"\ndetails_json keys: {list(details.keys())}")
    
    # Check Stats
    if 'Stats' in details:
        stats = details['Stats']
        print(f"\n✓ Stats key EXISTS")
        print(f"  Type: {type(stats)}")
        print(f"  Is empty?: {not stats or stats == {}}")
        
        if isinstance(stats, dict):
            if stats:
                print(f"  Keys ({len(stats)}): {list(stats.keys())}")
                # Check for elemental stats
                for elem in ['Chill', 'Vibe', 'Beat', 'Flow', 'Rush']:
                    val = stats.get(elem, 'NOT_FOUND')
                    print(f"    {elem}: {val}")
            else:
                print(f"  ❌ Stats is EMPTY DICT {{}}")
    else:
        print(f"\n❌ Stats key NOT FOUND in details_json")
    
    # Check top-level keys for comparison
    print(f"\nOther details:")
    print(f"  GemCounts: {details.get('GemCounts', 'MISSING')}")
    print(f"  SelectedElement: {details.get('SelectedElement', 'MISSING')}")
    print(f"  Gear: {json.loads(row['gear_json']) if row['gear_json'] else []}")
    print(f"  Minis: {json.loads(row['minis_json']) if row['minis_json'] else []}")
    print()

conn.close()
