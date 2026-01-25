"""Find entries with missing/empty Stats."""

import sqlite3
import json

conn = sqlite3.connect('evolution.db')
conn.row_factory = sqlite3.Row

rows = conn.execute('SELECT rowid, song_name, details_json FROM loadouts').fetchall()

bad = []
for r in rows:
    details = json.loads(r['details_json']) if r['details_json'] else {}
    stats = details.get('Stats')
    if stats is None or (isinstance(stats, dict) and len(stats) == 0):
        bad.append(r)

print(f"Found {len(bad)} entries with empty/missing Stats:")
for r in bad:
    details = json.loads(r['details_json']) if r['details_json'] else {}
    stats = details.get('Stats')
    stats_type = "None" if stats is None else "{}"
    print(f"  rowid={r['rowid']}: {r['song_name']} (Stats={stats_type})")

conn.close()
