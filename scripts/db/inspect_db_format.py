import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gear_optimizer.data.database import get_db_connection, get_evolution_db_path
from gear_optimizer.data.database import _load_piece_name_encoding_maps, _unpack_id_groups, _unpack_id_list

db_path = get_evolution_db_path()
conn = get_db_connection(db_path)
maps = _load_piece_name_encoding_maps(conn, db_path=str(db_path))

# Show schema
print("=" * 80)
print("DATABASE SCHEMA")
print("=" * 80)

cursor = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='songs'")
print("\n--- SONGS TABLE ---")
print(cursor.fetchone()[0])

cursor = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='team_buff_loadouts'")
print("\n--- TEAM_BUFF_LOADOUTS TABLE ---")
print(cursor.fetchone()[0])

cursor = conn.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name='idx_team_buff_loadouts_score'")
print("\n--- INDEX ---")
print(cursor.fetchone()[0])

# Show example data
print("\n" + "=" * 80)
print("EXAMPLE DATA: Bopeebo (Hard)")
print("=" * 80)

# Songs table example
cursor = conn.execute("SELECT * FROM songs WHERE name LIKE '%Bopeebo (Hard)%'")
song = cursor.fetchone()
if song:
    print("\n--- SONGS TABLE ROW ---")
    print(f"name: {song['name']}")
    print(f"best_score: {song['best_score']}")
    print(f"best_fg_score: {song['best_fg_score']}")
    print(f"last_updated: {song['last_updated']}")

# Loadouts table example
cursor = conn.execute("""
    SELECT * FROM team_buff_loadouts 
    WHERE song_name LIKE '%Bopeebo (Hard)%'
    ORDER BY fg_score DESC
    LIMIT 1
""")
loadout = cursor.fetchone()
if loadout:
    print("\n--- TEAM_BUFF_LOADOUTS TABLE ROW ---")
    print(f"song_name: {loadout['song_name']}")
    print(f"loadout_hash: {loadout['loadout_hash']}")
    print(f"score: {loadout['score']}")
    print(f"fg_score: {loadout['fg_score']}")
    print(f"timestamp: {loadout['timestamp']}")

    gear_ids = _unpack_id_list(loadout["gear_ids_blob"])
    gear = [maps.gear_id_to_name.get(int(i), "") for i in gear_ids if int(i) > 0]
    gear = [g for g in gear if g]
    print(f"\ngear_ids_blob bytes: {len(loadout['gear_ids_blob'] or b'')}")
    print(f"gear (decoded): {gear}")

    mini_id_groups = _unpack_id_groups(loadout["minis_ids_blob"])
    minis = [
        sorted({maps.mini_id_to_name.get(int(i), "") for i in g if int(i) > 0}) for g in (mini_id_groups or []) if g
    ]
    minis = [[n for n in g if n] for g in minis if g]
    print(f"\nminis_ids_blob bytes: {len(loadout['minis_ids_blob'] or b'')}")
    print(f"minis (decoded groups): {minis}")

    print(f"\ndetails_json (raw, first 200 chars): {(loadout['details_json'] or '')[:200]}...")
    if loadout["details_json"]:
        details = json.loads(loadout["details_json"])
        print(f"details_json keys: {list(details.keys())}")
        if "GemCounts" in details:
            print(f"  GemCounts: {details['GemCounts']}")

    print(f"\nforce_details_json (raw, first 200 chars): {(loadout['force_details_json'] or '')[:200]}...")
    if loadout["force_details_json"]:
        force = json.loads(loadout["force_details_json"])
        print(f"force_details_json (parsed): {json.dumps(force, indent=2)}")

conn.close()
