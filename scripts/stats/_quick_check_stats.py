"""Quick validation: check recent DB entries for Stats."""

import sqlite3
import json

conn = sqlite3.connect("evolution.db")
conn.row_factory = sqlite3.Row

# Check most recent entries
rows = conn.execute("""
    SELECT song_name, score, details_json
    FROM team_buff_loadouts 
    ORDER BY timestamp DESC
    LIMIT 5
""").fetchall()

print("Checking most recent 5 database entries...\n")

for row in rows:
    song = row["song_name"]
    details_raw = row["details_json"]

    if not details_raw:
        print(f"❌ {song}: NULL details_json")
        continue

    details = json.loads(details_raw)
    stats = details.get("Stats", {})

    if not stats or stats == {}:
        print(f"❌ {song}: Empty Stats {{}}")
    else:
        chill = stats.get("Chill", "N/A")
        print(f"✅ {song}: Stats OK (Chill={chill})")

conn.close()
