
import sys
import os
import sqlite3
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from gear_optimizer.data.database import get_db_connection, get_evolution_db_path

db_path = get_evolution_db_path()
conn = get_db_connection(db_path)
conn.row_factory = sqlite3.Row

song_name = "Ice Angel (Easy)"
cursor = conn.cursor()
cursor.execute("SELECT DISTINCT song_name FROM loadouts")
rows = cursor.fetchall()
print(f"Unique songs in DB: {[r['song_name'] for r in rows]}")
cursor.execute("SELECT * FROM loadouts")
rows = cursor.fetchall()

print(f"Database Path: {db_path}")
print(f"Rows found for '{song_name}': {len(rows)}")

for row in rows:
    # Convert Row object to dict
    row_dict = dict(row)
    print("\n--- RAW ROW ---")
    print(str(row_dict))
    print("\n--- JSON PRETTY ---")
    print(json.dumps(row_dict, default=str, indent=2))

conn.close()
