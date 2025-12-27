import sqlite3
import json
import time

conn = sqlite3.connect('evolution.db')
rows = conn.execute(
    'SELECT score, fg_score, timestamp, details_json, gear_json FROM loadouts WHERE song_name=? ORDER BY score DESC LIMIT 5',
    ('Feeling Alright (Hard) by Rutra',)
).fetchall()

for i, r in enumerate(rows):
    d = json.loads(r[3]) if r[3] else {}
    gear = json.loads(r[4]) if r[4] else []
    ts = time.strftime('%H:%M:%S', time.localtime(r[2])) if r[2] else 'N/A'
    gems = d.get('GemCounts', {})
    print(f"--- Entry {i+1} ---")
    print(f"  score={r[0]}, fg_score={r[1]}, time={ts}")
    print(f"  FT={d.get('FT', 'N/A')}, FF={d.get('FF', 'N/A')}")
    print(f"  GemCounts: FM={gems.get('Fever Multiplier', 'N/A')}, PP={gems.get('Perfect Points', 'N/A')}, CM={gems.get('Combo Multiplier', 'N/A')}, OV={gems.get('Element', 'N/A')}")
    print(f"  Gear: {gear[:2]}...")  # First 2 items

conn.close()
