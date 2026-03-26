import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from gear_optimizer.data.database import (
    get_db_connection,
    get_evolution_db_path,
    _load_piece_name_encoding_maps,
    _unpack_id_list,
)

db_path = get_evolution_db_path()
conn = get_db_connection(db_path)
maps = _load_piece_name_encoding_maps(conn, db_path=str(db_path))

print("=== TOP NON-FG (by score) ===")
cur = conn.execute("""SELECT score, fg_score, gear_ids_blob FROM team_buff_loadouts
                       WHERE song_name LIKE '%Feeling Alright%' ORDER BY score DESC LIMIT 1""")
row = cur.fetchone()
gear_ids = _unpack_id_list(row[2]) if row else []
gear = [maps.gear_id_to_name.get(int(i), "") for i in gear_ids if int(i) > 0]
gear = [g for g in gear if g]
print(f"Score: {row[0]}, FG_Score: {row[1]}, Face: {gear[2] if len(gear) > 2 else '?'}")

print()
print("=== TOP FG (by fg_score) ===")
cur = conn.execute("""SELECT score, fg_score, gear_ids_blob FROM team_buff_loadouts
                       WHERE song_name LIKE '%Feeling Alright%' ORDER BY fg_score DESC LIMIT 1""")
row = cur.fetchone()
gear_ids = _unpack_id_list(row[2]) if row else []
gear = [maps.gear_id_to_name.get(int(i), "") for i in gear_ids if int(i) > 0]
gear = [g for g in gear if g]
print(f"Score: {row[0]}, FG_Score: {row[1]}, Face: {gear[2] if len(gear) > 2 else '?'}")
conn.close()
