"""Debug script to inspect persisted entries for a single song."""

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
    SELECT loadout_hash, score, fg_score, gear_ids_blob, force_details_json
    FROM team_buff_loadouts
    WHERE song_name=? AND team_buff=?
    ORDER BY score DESC
    """,
    ("Feeling Alright (Hard) by Rutra", "T5"),
).fetchall()

print("=== All loadouts for song ===")
for r in rows:
    lhash = str(r[0] or "")[:16]
    gear_ids = _unpack_id_list(r[3])
    gear = [maps.gear_id_to_name.get(int(i), "") for i in gear_ids if int(i) > 0]
    gear = [g for g in gear if g]
    force = json.loads(r[4]) if r[4] else None
    fg_config = None
    if force:
        fg_meta = force.get("ForceGreats", {})
        fg_config = fg_meta.get("config")

    print(f"hash={lhash}... score={int(r[1] or 0):,}, fg_score={int(r[2] or 0):,}")
    print(f"  gear[2:5]: {gear[2:5]}")
    print(f"  force_details: {'YES' if force else 'NO'}, fg_config={fg_config}")
    print()

conn.close()
