import sqlite3
import json

conn = sqlite3.connect("evolution.db")
r = conn.execute(
    """
    SELECT force_details_json
    FROM team_buff_fg_loadouts
    WHERE song_name=? AND team_buff=? AND fg_score > 0
    """,
    ("Feeling Alright (Hard) by Rutra", "T5"),
).fetchone()

if r and r[0]:
    print(json.dumps(json.loads(r[0]), indent=2))
else:
    print("No force_details_json with fg_score > 0")

conn.close()
