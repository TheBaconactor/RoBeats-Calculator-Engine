import sqlite3
import json

conn = sqlite3.connect('evolution.db')
cur = conn.cursor()

# Get loadouts for these songs
cur.execute("""
    SELECT song_name, score, fg_score, gear, minis, force 
    FROM loadouts 
    WHERE song_name LIKE '%Feeling Alright%'
    ORDER BY song_name, score DESC
    LIMIT 20
""")

print("=== Top Loadouts in DB ===\n")
for row in cur.fetchall():
    song, score, fg_score, gear_json, minis_json, force_json = row
    
    # Parse gear names
    try:
        gear = json.loads(gear_json) if gear_json else []
        gear_names = [g.get("Name", "?") if isinstance(g, dict) else str(g) for g in gear]
    except:
        gear_names = ["parse_error"]
    
    # Check force data
    force_data = None
    if force_json:
        try:
            force_data = json.loads(force_json)
        except:
            force_data = "parse_error"
    
    print(f"Song: {song}")
    print(f"  Score: {score:,} | FG Score: {fg_score:,}")
    print(f"  Gear: {gear_names[:3]}...")
    print(f"  Force data exists: {force_data is not None and force_data != 'parse_error'}")
    if force_data and isinstance(force_data, dict):
        print(f"  Force score: {force_data.get('score', 'N/A')}")
    print()

conn.close()
