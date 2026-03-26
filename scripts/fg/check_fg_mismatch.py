import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gear_optimizer.data.database import (
    _load_piece_name_encoding_maps,
    _unpack_id_groups,
    _unpack_id_list,
    get_db_connection,
    get_evolution_db_path,
)

db_path = get_evolution_db_path()
conn = get_db_connection(db_path)
maps = _load_piece_name_encoding_maps(conn, db_path=str(db_path))
rows = conn.execute("""
    SELECT score, fg_score, gear_ids_blob, minis_ids_blob, force_details_json
    FROM team_buff_loadouts 
    WHERE song_name LIKE '%Feeling%' AND fg_score=33579863
""").fetchall()

print(f"Found {len(rows)} entries with FG=33,579,863")
for r in rows:
    print(f"\n{'=' * 50}")
    print(f"Base Score: {r[0]:,}")
    print(f"FG Score: {r[1]:,}")
    gear_ids = _unpack_id_list(r[2])
    gear = [maps.gear_id_to_name.get(int(i), "") for i in gear_ids if int(i) > 0]
    gear = [g for g in gear if g]
    mini_id_groups = _unpack_id_groups(r[3])
    minis = [
        sorted({maps.mini_id_to_name.get(int(i), "") for i in g if int(i) > 0}) for g in (mini_id_groups or []) if g
    ]
    minis = [[n for n in g if n] for g in minis if g]
    print(f"Loadout Gear: {gear}")
    print(f"Loadout Minis: {minis}")
    if r[4]:
        fd = json.loads(r[4])
        print(f"FG Details Gear: {fd.get('gear', 'N/A')}")
        print(f"FG Details Minis: {fd.get('minis', 'N/A')}")
        print(f"FG Details Score: {fd.get('score', 'N/A')}")
    else:
        print("FG Details: None")
