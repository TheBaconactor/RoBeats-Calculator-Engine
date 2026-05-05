"""Quick validation: Check recent DB entries for Stats."""

import sqlite3, json

conn = sqlite3.connect("evolution.db")
conn.row_factory = sqlite3.Row

print("Checking 10 most recent entries...\n")

rows = conn.execute("""
    SELECT song_name, score, details_json, timestamp
    FROM team_buff_loadouts 
    ORDER BY timestamp DESC
    LIMIT 10
""").fetchall()

success = 0
fail = 0

for row in rows:
    details_raw = row["details_json"]
    if not details_raw:
        print(f"❌ {row['song_name'][:40]}: NULL details")
        fail += 1
        continue

    details = json.loads(details_raw)
    stats = details.get("Stats", {})

    if not stats or stats == {}:
        print(f"❌ {row['song_name'][:40]}: Empty Stats")
        fail += 1
    else:
        print(f"✅ {row['song_name'][:40]}: Stats OK")
        success += 1

conn.close()

print(f"\nResults: {success}/{success + fail} have valid Stats")

if fail > 0:
    print(f"\n⚠️  {fail} entries still missing Stats - may need to run optimizer again or backfill")
else:
    print("\n✅ All entries have Stats!")
