"""Debug script to check what persist_entries should look like."""

import json
import sqlite3

# Check DB: which loadouts have non-zero fg_score?
conn = sqlite3.connect("evolution.db")
rows = conn.execute(
    """
    SELECT loadout_hash, score, fg_score, gear_json, force_details_json 
    FROM team_buff_loadouts 
    WHERE song_name=? AND team_buff=?
    ORDER BY score DESC
""",
    ("Feeling Alright (Hard) by Rutra", "T5"),
).fetchall()

print("=== All loadouts for song ===")
for r in rows:
    lhash = r[0][:16]
    gear = json.loads(r[3]) if r[3] else []
    force = json.loads(r[4]) if r[4] else None
    fg_config = None
    if force:
        fg_meta = force.get("ForceGreats", {})
        fg_config = fg_meta.get("config")

    print(f"hash={lhash}... score={r[1]:,}, fg_score={r[2]:,}")
    print(f"  gear[2:5]: {gear[2:5]}")
    print(f"  force_details: {'YES' if force else 'NO'}, fg_config={fg_config}")
    print()

conn.close()
