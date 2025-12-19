import sys; sys.path.insert(0, '.')
import sqlite3; import json
from gear_optimizer.data.database import get_evolution_db_path
conn = sqlite3.connect(get_evolution_db_path())

# Get total count
cur = conn.execute('SELECT COUNT(*) FROM loadouts')
print(f'Total loadouts: {cur.fetchone()[0]}')

# Get a random FG entry to check structure
cur = conn.execute("""SELECT song_name, score, fg_score, details_json, force_details_json 
                       FROM loadouts WHERE fg_score > 0 LIMIT 1""")
row = cur.fetchone()
if row:
    print(f"Song: {row[0]}")
    print(f"Score: {row[1]}, FG Score: {row[2]}")
    d = json.loads(row[3]) if row[3] else {}
    print(f"GemCounts keys: {list(d.get('GemCounts', {}).keys())}")
    f = json.loads(row[4]) if row[4] else {}
    fg = f.get('details', {}).get('ForceGreats', {})
    print(f"ForceGreats: {fg}")
else:
    print("No FG entries found")
conn.close()
