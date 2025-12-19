import sqlite3
import json

conn = sqlite3.connect('evolution.db')
conn.row_factory = sqlite3.Row

cur = conn.execute("SELECT force_details_json FROM loadouts WHERE force_details_json IS NOT NULL LIMIT 1")
row = cur.fetchone()
if row:
    data = json.loads(row['force_details_json'])
    fg = data.get('details', {}).get('ForceGreats', {})
    print('=== ForceGreats structure ===')
    print(json.dumps(fg, indent=2))
conn.close()
