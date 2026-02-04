import sqlite3
import json
from gear_optimizer.data.database import get_evolution_db_path

db_path = get_evolution_db_path()
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# Check if there are any entries
cur = conn.execute("SELECT COUNT(*) as cnt FROM team_buff_loadouts")
count = cur.fetchone()["cnt"]
print(f"Total loadouts: {count}")

if count > 0:
    # Get a sample entry
    cur = conn.execute("SELECT song_name, score, fg_score, details_json, force_details_json FROM team_buff_loadouts LIMIT 1")
    row = cur.fetchone()
    print(f"Song: {row['song_name']}")
    print(f"Score: {row['score']}, FG Score: {row['fg_score']}")

    if row["details_json"]:
        details = json.loads(row["details_json"])
        print(f"GemCounts keys: {list(details.get('GemCounts', {}).keys())}")

    if row["force_details_json"]:
        force = json.loads(row["force_details_json"])
        if "details" in force and "ForceGreats" in force["details"]:
            fg = force["details"]["ForceGreats"]
            print(f"ForceGreats keys: {list(fg.keys())}")
            print(f"ForceGreats: {json.dumps(fg, indent=2)}")
else:
    print("Database is empty - run optimizer to generate new data")

conn.close()
