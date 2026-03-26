import json
import time

from gear_optimizer.data.database import (
    _load_piece_name_encoding_maps,
    _unpack_id_list,
    get_db_connection,
    get_evolution_db_path,
)

db_path = get_evolution_db_path()
conn = get_db_connection(db_path)
maps = _load_piece_name_encoding_maps(conn, db_path=str(db_path))

rows = conn.execute(
    """
    SELECT score, fg_score, timestamp, details_json, gear_ids_blob
    FROM team_buff_loadouts
    WHERE song_name=? AND team_buff=?
    ORDER BY score DESC
    LIMIT 5
    """,
    ("Feeling Alright (Hard) by Rutra", "T5"),
).fetchall()

for i, r in enumerate(rows):
    d = json.loads(r[3]) if r[3] else {}
    gear_ids = _unpack_id_list(r[4])
    gear = [maps.gear_id_to_name.get(int(i), "") for i in gear_ids if int(i) > 0]
    gear = [g for g in gear if g]
    ts = time.strftime("%H:%M:%S", time.localtime(r[2])) if r[2] else "N/A"
    gems = d.get("GemCounts", {})
    print(f"--- Entry {i + 1} ---")
    print(f"  score={r[0]}, fg_score={r[1]}, time={ts}")
    print(f"  FT={d.get('FT', 'N/A')}, FF={d.get('FF', 'N/A')}")
    print(
        f"  GemCounts: FM={gems.get('Fever Multiplier', 'N/A')}, PP={gems.get('Perfect Points', 'N/A')}, "
        f"CM={gems.get('Combo Multiplier', 'N/A')}, OV={gems.get('Element', 'N/A')}"
    )
    print(f"  Gear: {gear[:2]}...")  # First 2 items

conn.close()
