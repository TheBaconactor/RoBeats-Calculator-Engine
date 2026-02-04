import sqlite3
import json

conn = sqlite3.connect("evolution.db")
rows = conn.execute(
    """
    SELECT score, fg_score, timestamp, gear_json, force_details_json
    FROM team_buff_fg_loadouts
    WHERE song_name=? AND team_buff=?
    ORDER BY fg_score DESC
    LIMIT 5
    """,
    ("Feeling Alright (Hard) by Rutra", "T5"),
).fetchall()

for i, r in enumerate(rows):
    gear = json.loads(r[3]) if r[3] else []
    force = json.loads(r[4]) if r[4] else {}
    print(f"--- Entry {i + 1} ---")
    print(f"  score={r[0]}, fg_score={r[1]}")
    print(f"  Gear: {gear}")
    if force:
        fg_meta = force.get("ForceGreats", {})
        print(f"  FG base_score: {fg_meta.get('base_score')}, FG final_score: {fg_meta.get('final_score')}")
        print(f"  FG config: {fg_meta.get('config')}")
    else:
        print("  No force_details_json")

conn.close()
