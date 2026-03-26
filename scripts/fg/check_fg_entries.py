import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from gear_optimizer.data.database import get_evolution_db_path, _load_piece_name_encoding_maps, _unpack_id_list

db_path = get_evolution_db_path()
conn = sqlite3.connect(db_path)
maps = _load_piece_name_encoding_maps(conn, db_path=str(db_path))
cur = conn.execute(
    "SELECT song_name, score, fg_score, gear_ids_blob, force_details_json FROM team_buff_loadouts ORDER BY fg_score DESC"
)
rows = cur.fetchall()
print(f"Total entries: {len(rows)}")
for i, row in enumerate(rows[:5]):
    print(f"--- Entry {i + 1} ---")
    print(f"Song: {row[0]}")
    print(f"Score: {row[1]}, FG Score: {row[2]}")
    gear_ids = _unpack_id_list(row[3]) if row[3] else []
    gear = [maps.gear_id_to_name.get(int(i), "") for i in gear_ids if int(i) > 0]
    gear = [g for g in gear if g]
    print(f"Gear: {gear[2] if len(gear) > 2 else 'N/A'}")  # The Face slot differs
    force = json.loads(row[4]) if row[4] else {}
    force_gear = force.get("gear", [])
    print(f"Force Gear: {force_gear[2] if len(force_gear) > 2 else 'N/A'}")
conn.close()
