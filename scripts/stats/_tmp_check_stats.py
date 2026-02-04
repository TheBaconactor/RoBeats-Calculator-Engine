import sqlite3
import json

conn = sqlite3.connect("evolution.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()

rows = c.execute("SELECT song_name, details_json FROM team_buff_loadouts LIMIT 5").fetchall()

for row in rows:
    song = row["song_name"]
    details_raw = row["details_json"]

    print(f"\n{'=' * 60}")
    print(f"Song: {song}")
    print(f"{'=' * 60}")

    if not details_raw:
        print("  details_json is NULL")
        continue

    details = json.loads(details_raw)

    # Check if Stats key exists
    if "Stats" in details:
        stats = details["Stats"]
        print(f"  Stats type: {type(stats)}")
        print(f"  Stats empty?: {not stats}")
        if isinstance(stats, dict):
            print(f"  Stats keys: {list(stats.keys())}")
            print(f"  Stats (first 3): {dict(list(stats.items())[:3])}")
            if "Chill" in stats:
                print(f"  Chill value: {stats['Chill']}")
            else:
                print(f"  Chill key: NOT FOUND in Stats")
    else:
        print(f"  Stats key: NOT FOUND in details_json")
        print(f"  details keys: {list(details.keys())}")

conn.close()
