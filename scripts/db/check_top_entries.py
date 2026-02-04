import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from gear_optimizer.data.database import get_evolution_db_path

db_path = get_evolution_db_path()
conn = sqlite3.connect(db_path)

# Get top base score entry
cur = conn.execute("""SELECT score, fg_score, gear_json FROM team_buff_loadouts 
                       WHERE song_name LIKE '%Feeling Alright%' ORDER BY score DESC LIMIT 1""")
row = cur.fetchone()
gear = json.loads(row[2]) if row[2] else []
print(f"TOP NON-FG: Score={row[0]}, FG_Score={row[1]}")
print(f"  Face gear: {gear[2] if len(gear) > 2 else '?'}")

# Get top fg score entry
cur = conn.execute("""SELECT score, fg_score, gear_json FROM team_buff_loadouts 
                       WHERE song_name LIKE '%Feeling Alright%' ORDER BY fg_score DESC LIMIT 1""")
row = cur.fetchone()
gear = json.loads(row[2]) if row[2] else []
print(f"TOP FG: Score={row[0]}, FG_Score={row[1]}")
print(f"  Face gear: {gear[2] if len(gear) > 2 else '?'}")

conn.close()
