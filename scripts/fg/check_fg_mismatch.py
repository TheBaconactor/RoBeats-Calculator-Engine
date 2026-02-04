import sqlite3
import json

conn = sqlite3.connect("evolution.db")
rows = conn.execute("""
    SELECT score, fg_score, gear_json, minis_json, force_details_json 
    FROM team_buff_loadouts 
    WHERE song_name LIKE '%Feeling%' AND fg_score=33579863
""").fetchall()

print(f"Found {len(rows)} entries with FG=33,579,863")
for r in rows:
    print(f"\n{'=' * 50}")
    print(f"Base Score: {r[0]:,}")
    print(f"FG Score: {r[1]:,}")
    print(f"Loadout Gear: {r[2]}")
    print(f"Loadout Minis: {r[3]}")
    if r[4]:
        fd = json.loads(r[4])
        print(f"FG Details Gear: {fd.get('gear', 'N/A')}")
        print(f"FG Details Minis: {fd.get('minis', 'N/A')}")
        print(f"FG Details Score: {fd.get('score', 'N/A')}")
    else:
        print("FG Details: None")
