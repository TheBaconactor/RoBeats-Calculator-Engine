import csv
import os
import sys
import sqlite3
import json

# Ensure root directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gear_optimizer.core.stats_calculator import compute_full_stats
from gear_optimizer.data.database import (
    _load_piece_name_encoding_maps,
    _pack_stats_for_storage,
    _unpack_id_groups,
    _unpack_id_list,
    get_evolution_db_path,
)
from gear_optimizer.core.config import load_paths_cache
from gear_optimizer.data.csv_parser import parse_gear_rows, parse_mini_rows


def main():
    print("Loading gear and mini data...")
    paths = load_paths_cache()

    # Load gears and minis from CSV using existing parsers
    gears_path = paths.get("Gears", "")
    minis_path = paths.get("Minis", "")

    gears_list = parse_gear_rows(gears_path)
    minis_list = parse_mini_rows(minis_path)
    gears_by_name = {g["Name"]: g for g in gears_list}
    minis_by_name = {m["Name"]: m for m in minis_list}
    print(f"Loaded {len(gears_by_name)} gears, {len(minis_by_name)} minis")

    # Base persistence assumes TeamBuff auto-mode (T5). Tier recomputation is expressed as a delta
    # vs this base, so if we backfill "loadout-only" Stats here, the frontend can display T5 as NONE
    # (missing +PP/+primary element), and NONE can go negative when deltas are applied.
    base_stats_zero = {
        "Perfect Points": 0,
        "Combo Multiplier": 0,
        "Fever Multiplier": 0,
        "Fever Fill Rate": 0,
        "Fever Time": 0,
        "Chill": 0,
        "Flow": 0,
        "Rush": 0,
        "Beat": 0,
        "Vibe": 0,
    }
    print(f"Using base TeamBuff=T5 effect (+25 PP, +30 primary element) for backfilled Stats.")

    db_path = get_evolution_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    total_updated = 0
    for table in ("team_buff_loadouts", "team_buff_fg_loadouts"):
        print(f"\nFetching entries from {table}...")
        cur = conn.execute(f"""
            SELECT rowid, song_name, gear_ids_blob, minis_ids_blob, details_json
            FROM {table}
        """)
        rows = cur.fetchall()
        maps = _load_piece_name_encoding_maps(conn, db_path=str(db_path))

        updated = 0
        print(f"Processing {len(rows)} entries from {table}... this may take a moment.")

        for i, row in enumerate(rows):
            if i % 10000 == 0:
                print(f"[{table}] Processed {i}/{len(rows)}...")

            details = json.loads(row["details_json"]) if row["details_json"] else {}
            gear_ids = _unpack_id_list(row["gear_ids_blob"])
            gear_names = [maps.gear_id_to_name.get(int(i), "") for i in gear_ids if int(i) > 0]
            gear_names = [g for g in gear_names if g]

            mini_id_groups = _unpack_id_groups(row["minis_ids_blob"])
            mini_groups = [
                sorted({maps.mini_id_to_name.get(int(i), "") for i in g if int(i) > 0})
                for g in (mini_id_groups or [])
                if g
            ]
            mini_groups = [[n for n in g if n] for g in mini_groups if g]
            # Extract first name from each group (representative)
            mini_names = [item[0] for item in mini_groups if isinstance(item, list) and item]

            gem_counts = dict(details.get("GemCounts", {}) or {})
            # DB stores FT/FF gem allocations at the top level (not inside GemCounts).
            # Include them so computed Stats match the score configuration.
            gem_counts["Fever Time"] = int(details.get("FT", 0) or 0)
            gem_counts["Fever Fill Rate"] = int(details.get("FF", 0) or 0)
            selected_element = details.get("SelectedElement") or details.get("Selected Element") or ""

            # Apply base TeamBuff=T5 effect (auto mode uses the song primary color).
            base_stats = dict(base_stats_zero)
            primary = str(details.get("PrimaryColor") or details.get("Primary Color") or "").strip()
            if primary in {"Chill", "Flow", "Rush", "Beat", "Vibe"}:
                base_stats[primary] = int(base_stats.get(primary, 0) or 0) + 30
            base_stats["Perfect Points"] = int(base_stats.get("Perfect Points", 0) or 0) + 25

            # Compute Stats (unconditionally recompute for consistency)
            computed_stats = compute_full_stats(
                gear_names, mini_names, gem_counts, selected_element, gears_by_name, minis_by_name, base_stats
            )

            # Update details with computed Stats (then pack to compact `st` array).
            details.pop("st", None)
            details["Stats"] = computed_stats
            details = _pack_stats_for_storage(details)

            # Write back
            conn.execute(f"UPDATE {table} SET details_json = ? WHERE rowid = ?", (json.dumps(details), row["rowid"]))
            updated += 1

        conn.commit()
        total_updated += updated
    conn.close()

    print(f"\nDone! Updated {total_updated} entries across team_buff_loadouts + team_buff_fg_loadouts.")


if __name__ == "__main__":
    main()
