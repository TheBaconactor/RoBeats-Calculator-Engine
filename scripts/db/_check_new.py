import sqlite3, json

conn = sqlite3.connect('evolution.db')
conn.row_factory = sqlite3.Row

rows = conn.execute("""
    SELECT song_name, score, details_json, timestamp
    FROM loadouts 
    ORDER BY timestamp DESC
    LIMIT 10
""").fetchall()

print("Checking 10 most recent entries (sorted by timestamp):\n")

success = 0
fail = 0

for row in rows:
    details_raw = row['details_json']
    song = row['song_name'][:50]
    
    if not details_raw:
        print(f"❌ {song}: NULL details")
        fail += 1
        continue
    
    details = json.loads(details_raw)
    stats = details.get('Stats', {})
    
    if not stats or stats == {}:
        print(f"❌ {song}: Empty Stats")
        fail += 1
    else:
        chill = stats.get('Chill', 'N/A')
        print(f"✅ {song}: Chill={chill}")
        success += 1

conn.close()

print(f"\nResults: {success}/{success+fail} have valid Stats")
