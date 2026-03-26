import json

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
    SELECT score, fg_score, timestamp, gear_ids_blob, force_details_json
    FROM team_buff_fg_loadouts
    WHERE song_name=? AND team_buff=?
    ORDER BY fg_score DESC
    LIMIT 5
    """,
    ("Feeling Alright (Hard) by Rutra", "T5"),
).fetchall()

for i, r in enumerate(rows):
    gear_ids = _unpack_id_list(r[3])
    gear = [maps.gear_id_to_name.get(int(i), "") for i in gear_ids if int(i) > 0]
    gear = [g for g in gear if g]
    force = json.loads(r[4]) if r[4] else {}
    print(f"--- Entry {i + 1} ---")
    print(f"  score={r[0]}, fg_score={r[1]}")
    print(f"  Gear: {gear}")
    if force:
        fg_meta = force.get("ForceGreats", {})
        print(f"  FG base_score: {fg_meta.get('base_score')}, FG final_score: {fg_meta.get('final_score')}")
        print(f"  FG config: {fg_meta.get('config')}")
    else:
        print("  No force_details_json")

conn.close()
