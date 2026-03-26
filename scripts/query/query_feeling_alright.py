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


def _minis_display(groups: list[list[str]]) -> str:
    # For legacy scripts, display one representative per slot.
    reps = [g[0] for g in groups if g]
    return ", ".join(reps)


# Find Feeling Alright (Hard)
cursor = conn.execute(
    "SELECT name, best_score, best_fg_score FROM songs WHERE LOWER(name) LIKE ? ORDER BY name",
    ("%feeling alright%hard%",),
)

results = cursor.fetchall()
if not results:
    print("Song not found. Searching more broadly...")
    cursor = conn.execute(
        "SELECT name, best_score, best_fg_score FROM songs WHERE LOWER(name) LIKE ? ORDER BY name",
        ("%feeling alright%",),
    )
    results = cursor.fetchall()

if not results:
    print("No songs found matching 'feeling alright'")
    conn.close()
    raise SystemExit(0)

song_name = results[0]["name"]
print(f"Found: {song_name}")
print(f"Best Score in DB: {int(results[0]['best_score'] or 0):,}")
print(f"Best FG Score in DB: {int(results[0]['best_fg_score'] or 0):,}")
print()


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


top_base = _fetch_top("score")
top_fg = _fetch_top("fg_score")

print("=" * 80)
print("TOP BASE SCORE LOADOUT")
print("=" * 80)
if top_base:
    gear = _decode_gear(top_base["gear_ids_blob"])
    minis = _decode_minis(top_base["minis_ids_blob"])
    details = json.loads(top_base["details_json"]) if top_base["details_json"] else {}
    details = _unpack_stats_after_load(details) or {}

    print(f"Base Score: {int(top_base['score'] or 0):,}")
    print(f"FG Score: {int(top_base['fg_score'] or 0):,}")
    print(f"\nGear: {', '.join(gear)}")
    print(f"Minis: {_minis_display(minis)}")

    gems = (details.get("GemCounts") or {}) if isinstance(details, dict) else {}
    if isinstance(gems, dict) and gems:
        print(
            f"\nGems: PP={gems.get('Perfect Points', 0)}, CM={gems.get('Combo Multiplier', 0)}, "
            f"FM={gems.get('Fever Multiplier', 0)}, Overflow={gems.get('Element', 0)}"
        )

print("\n" + "=" * 80)
print("TOP FG SCORE LOADOUT")
print("=" * 80)
if top_fg:
    gear = _decode_gear(top_fg["gear_ids_blob"])
    minis = _decode_minis(top_fg["minis_ids_blob"])
    details = json.loads(top_fg["details_json"]) if top_fg["details_json"] else {}
    details = _unpack_stats_after_load(details) or {}
    force_details = json.loads(top_fg["force_details_json"]) if top_fg["force_details_json"] else {}

    print(f"Base Score: {int(top_fg['score'] or 0):,}")
    print(f"FG Score: {int(top_fg['fg_score'] or 0):,}")
    print(f"\nGear: {', '.join(gear)}")
    print(f"Minis: {_minis_display(minis)}")

    gems = (details.get("GemCounts") or {}) if isinstance(details, dict) else {}
    if isinstance(gems, dict) and gems:
        print(
            f"\nGems: PP={gems.get('Perfect Points', 0)}, CM={gems.get('Combo Multiplier', 0)}, "
            f"FM={gems.get('Fever Multiplier', 0)}, Overflow={gems.get('Element', 0)}"
        )

    fg_meta = force_details.get("ForceGreats") if isinstance(force_details, dict) else None
    if isinstance(fg_meta, dict):
        cfg = fg_meta.get("config")
        if isinstance(cfg, dict):
            print(
                f"\nFG Config: [{cfg.get('NonFever1', 0)}, {cfg.get('NonFever2', 0)}, {cfg.get('NonFever3', 0)}, {cfg.get('NonFever4', 0)}]"
            )

print("\n" + "=" * 80)
print("COMPARISON")
print("=" * 80)
if top_base and top_fg:
    base_gear = _decode_gear(top_base["gear_ids_blob"])
    fg_gear = _decode_gear(top_fg["gear_ids_blob"])
    base_minis = _decode_minis(top_base["minis_ids_blob"])
    fg_minis = _decode_minis(top_fg["minis_ids_blob"])
    same_loadout = base_gear == fg_gear and base_minis == fg_minis

    print("SAME gear/mini loadout for both" if same_loadout else "DIFFERENT loadouts")

    score_diff = int(top_fg["fg_score"] or 0) - int(top_base["score"] or 0)
    print(f"\nFG Improvement: {score_diff:+,} points")
    print(f"  ({int(top_base['score'] or 0):,} -> {int(top_fg['fg_score'] or 0):,})")

conn.close()
