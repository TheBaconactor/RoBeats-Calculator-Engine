import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gear_optimizer.data.database import (
    _load_piece_name_encoding_maps,
    _unpack_id_groups,
    _unpack_id_list,
    _unpack_stats_after_load,
    get_db_connection,
    get_evolution_db_path,
)

db_path = get_evolution_db_path()
conn = get_db_connection(db_path)
maps = _load_piece_name_encoding_maps(conn, db_path=str(db_path))

song_name = "Bopeebo (Hard) by Kawai Sprite"

print("=" * 80)
print(f"All Loadouts for: {song_name}")
print("=" * 80)

# Get ALL loadouts ordered by base score
cursor = conn.execute(
    """
    SELECT score, fg_score, gear_ids_blob, minis_ids_blob, details_json, force_details_json
    FROM team_buff_loadouts
    WHERE song_name = ?
    ORDER BY score DESC
""",
    (song_name,),
)

loadouts = cursor.fetchall()
print(f"\nFound {len(loadouts)} total loadout(s) in database\n")

for idx, loadout in enumerate(loadouts, 1):
    gear_ids = _unpack_id_list(loadout["gear_ids_blob"])
    gear = [maps.gear_id_to_name.get(int(i), "") for i in gear_ids if int(i) > 0]
    gear = [g for g in gear if g]
    mini_id_groups = _unpack_id_groups(loadout["minis_ids_blob"])
    minis = [
        sorted({maps.mini_id_to_name.get(int(i), "") for i in g if int(i) > 0}) for g in (mini_id_groups or []) if g
    ]
    minis = [[n for n in g if n] for g in minis if g]
    details = json.loads(loadout["details_json"]) if loadout["details_json"] else {}
    details = _unpack_stats_after_load(details) or {}
    force_details = json.loads(loadout["force_details_json"]) if loadout["force_details_json"] else {}

    print(f"{'=' * 80}")
    print(f"LOADOUT #{idx}")
    print(f"{'=' * 80}")
    print(f"Base Score: {loadout['score']:,}")
    print(f"FG Score: {loadout['fg_score']:,}")

    print(f"\nGear:")
    for i, g in enumerate(gear, 1):
        print(f"  {i}. {g}")

    print(f"\nMinis:")
    for i, m in enumerate(minis, 1):
        print(f"  {i}. {m}")

    if details and "GemCounts" in details:
        gems = details["GemCounts"]
        print(f"\nGem Upgrades:")
        for gem_type in ["Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Fill Rate", "Fever Time"]:
            if gem_type in gems:
                print(f"  {gem_type}: {gems[gem_type]}")

        print(f"\nElemental Gems:")
        for elem in ["Chill", "Flow", "Rush", "Beat", "Vibe"]:
            if elem in gems:
                print(f"  {elem}: {gems[elem]}")

        if "Element" in gems:
            print(f"  Overflow: {gems['Element']}")

    if details and "Stats" in details:
        stats = details["Stats"]
        print(f"\nFinal Stats:")
        for stat in ["Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Fill Rate", "Fever Time"]:
            if stat in stats:
                print(f"  {stat}: {stats[stat]}")

        # Show elemental stats too
        for elem in ["Chill", "Flow", "Rush", "Beat", "Vibe"]:
            if elem in stats:
                print(f"  {elem}: {stats[elem]}")

    if force_details and "ForceGreats" in force_details:
        fg = force_details["ForceGreats"]
        print(f"\nForce Greats Config:")
        if "config" in fg:
            print(f"  Section 1: {fg['config'].get('NonFever1', 0)}")
            print(f"  Section 2: {fg['config'].get('NonFever2', 0)}")
            print(f"  Section 3: {fg['config'].get('NonFever3', 0)}")
            print(f"  Section 4: {fg['config'].get('NonFever4', 0)}")
        if "base_score" in fg:
            print(f"  FG Base Score (before FG applied): {fg['base_score']:,}")

    print()

conn.close()
