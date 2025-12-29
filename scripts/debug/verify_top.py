import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import sqlite3
import json
from gear_optimizer.data.database import get_evolution_db_path

conn = sqlite3.connect(get_evolution_db_path())

print("=== TOP NON-FG (by score) ===")
cur = conn.execute("""SELECT score, fg_score, gear_json FROM loadouts 
                       WHERE song_name LIKE '%Feeling Alright%' ORDER BY score DESC LIMIT 1""")
row = cur.fetchone()
gear = json.loads(row[2]) if row[2] else []
print(f"Score: {row[0]}, FG_Score: {row[1]}, Face: {gear[2] if len(gear) > 2 else '?'}")

print()
print("=== TOP FG (by fg_score) ===")
cur = conn.execute("""SELECT score, fg_score, gear_json FROM loadouts 
                       WHERE song_name LIKE '%Feeling Alright%' ORDER BY fg_score DESC LIMIT 1""")
row = cur.fetchone()
gear = json.loads(row[2]) if row[2] else []
print(f"Score: {row[0]}, FG_Score: {row[1]}, Face: {gear[2] if len(gear) > 2 else '?'}")
conn.close()
