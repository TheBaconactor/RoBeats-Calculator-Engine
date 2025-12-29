import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from gear_optimizer.data.database import get_evolution_db_path

db_path = get_evolution_db_path()
conn = sqlite3.connect(db_path)
cur = conn.execute(
    "SELECT song_name, score, fg_score, gear_json, force_details_json FROM loadouts ORDER BY fg_score DESC"
)
rows = cur.fetchall()
print(f"Total entries: {len(rows)}")
for i, row in enumerate(rows[:5]):
    print(f"--- Entry {i + 1} ---")
    print(f"Song: {row[0]}")
    print(f"Score: {row[1]}, FG Score: {row[2]}")
    gear = json.loads(row[3]) if row[3] else []
    print(f"Gear: {gear[2] if len(gear) > 2 else 'N/A'}")  # The Face slot differs
    force = json.loads(row[4]) if row[4] else {}
    force_gear = force.get("gear", [])
    print(f"Force Gear: {force_gear[2] if len(force_gear) > 2 else 'N/A'}")
conn.close()
