import json
import os
import sys

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


def _decode_gear(blob) -> list[str]:
    ids = _unpack_id_list(blob)
    names = [str(maps.gear_id_to_name.get(int(i), "") or "").strip() for i in ids if int(i) > 0]
    return [n for n in names if n]


def _decode_minis(blob) -> list[list[str]]:
    groups = _unpack_id_groups(blob)
    out: list[list[str]] = []
    for g in groups or []:
        if not g:
            continue
        names = [str(maps.mini_id_to_name.get(int(i), "") or "").strip() for i in g if int(i) > 0]
        names = sorted({n for n in names if n})
        if names:
            out.append(names)
    return out


song_name = "Bopeebo (Hard) by Kawai Sprite"

print("=" * 80)
print(f"Comparing Top Loadouts for: {song_name}")
print("=" * 80)


def _fetch_top(order_by: str):
    return conn.execute(
        f"""
        SELECT score, fg_score, gear_ids_blob, minis_ids_blob, details_json, force_details_json
        FROM team_buff_loadouts
        WHERE song_name = ?
        ORDER BY {order_by} DESC
        LIMIT 1
        """,
        (song_name,),
    ).fetchone()


print("\n### TOP BASE SCORE LOADOUT ###")
base_loadout = _fetch_top("score")
if base_loadout:
    gear = _decode_gear(base_loadout["gear_ids_blob"])
    minis = _decode_minis(base_loadout["minis_ids_blob"])
    details = json.loads(base_loadout["details_json"]) if base_loadout["details_json"] else {}
    details = _unpack_stats_after_load(details) or {}

    print(f"\nBase Score: {int(base_loadout['score'] or 0):,}")
    print(f"FG Score: {int(base_loadout['fg_score'] or 0):,}")

    print("\nGear:")
    for i, g in enumerate(gear, 1):
        print(f"  {i}. {g}")

    print("\nMinis:")
    for i, m in enumerate(minis, 1):
        print(f"  {i}. {m}")

    gems = (details.get("GemCounts") or {}) if isinstance(details, dict) else {}
    if isinstance(gems, dict) and gems:
        print("\nGem Upgrades:")
        for gem_type in ("Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Fill Rate", "Fever Time"):
            if gem_type in gems:
                print(f"  {gem_type}: {gems[gem_type]}")
        print("\nElemental Gems:")
        for elem in ("Chill", "Flow", "Rush", "Beat", "Vibe"):
            if elem in gems:
                print(f"  {elem}: {gems[elem]}")
        if "Element" in gems:
            print(f"  Overflow: {gems['Element']}")

    stats = details.get("Stats") if isinstance(details, dict) else None
    if isinstance(stats, dict) and stats:
        print("\nFinal Stats:")
        for stat in ("Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Fill Rate", "Fever Time"):
            if stat in stats:
                print(f"  {stat}: {stats[stat]}")


print("\n\n### TOP FG SCORE LOADOUT ###")
fg_loadout = _fetch_top("fg_score")
if fg_loadout:
    gear = _decode_gear(fg_loadout["gear_ids_blob"])
    minis = _decode_minis(fg_loadout["minis_ids_blob"])
    details = json.loads(fg_loadout["details_json"]) if fg_loadout["details_json"] else {}
    details = _unpack_stats_after_load(details) or {}
    force_details = json.loads(fg_loadout["force_details_json"]) if fg_loadout["force_details_json"] else {}

    print(f"\nBase Score: {int(fg_loadout['score'] or 0):,}")
    print(f"FG Score: {int(fg_loadout['fg_score'] or 0):,}")

    print("\nGear:")
    for i, g in enumerate(gear, 1):
        print(f"  {i}. {g}")

    print("\nMinis:")
    for i, m in enumerate(minis, 1):
        print(f"  {i}. {m}")

    gems = (details.get("GemCounts") or {}) if isinstance(details, dict) else {}
    if isinstance(gems, dict) and gems:
        print("\nGem Upgrades:")
        for gem_type in ("Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Fill Rate", "Fever Time"):
            if gem_type in gems:
                print(f"  {gem_type}: {gems[gem_type]}")

    fg_meta = force_details.get("ForceGreats") if isinstance(force_details, dict) else None
    if isinstance(fg_meta, dict):
        cfg = fg_meta.get("config")
        if isinstance(cfg, dict) and cfg:
            print("\nForce Greats Config:")
            print(f"  Section 1: {cfg.get('NonFever1', 0)}")
            print(f"  Section 2: {cfg.get('NonFever2', 0)}")
            print(f"  Section 3: {cfg.get('NonFever3', 0)}")
            print(f"  Section 4: {cfg.get('NonFever4', 0)}")


print("\n" + "=" * 80)
print("COMPARISON")
print("=" * 80)
if base_loadout and fg_loadout:
    base_gear = _decode_gear(base_loadout["gear_ids_blob"])
    fg_gear = _decode_gear(fg_loadout["gear_ids_blob"])

    if base_gear != fg_gear:
        print("\nDIFFERENT gear sets!")
        print(f"Base loadout gear: {base_gear}")
        print(f"FG loadout gear: {fg_gear}")
    else:
        print("\nSAME gear set")

    base_minis = _decode_minis(base_loadout["minis_ids_blob"])
    fg_minis = _decode_minis(fg_loadout["minis_ids_blob"])

    if base_minis != fg_minis:
        print("\nDIFFERENT mini sets!")
        print(f"Base loadout minis: {base_minis}")
        print(f"FG loadout minis: {fg_minis}")
    else:
        print("\nSAME mini set")

conn.close()
