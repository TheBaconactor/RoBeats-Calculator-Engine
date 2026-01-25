import csv
import os
import sys
import sqlite3
import json

# Ensure root directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gear_optimizer.core.stats_calculator import compute_full_stats
from gear_optimizer.data.database import get_evolution_db_path
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
    for table in ("loadouts", "fg_loadouts"):
        print(f"\nFetching entries from {table}...")
        cur = conn.execute(f"""
            SELECT rowid, song_name, gear_json, minis_json, details_json
            FROM {table}
        """)
        rows = cur.fetchall()

        updated = 0
        print(f"Processing {len(rows)} entries from {table}... this may take a moment.")

        for i, row in enumerate(rows):
            if i % 10000 == 0:
                print(f"[{table}] Processed {i}/{len(rows)}...")

            details = json.loads(row["details_json"]) if row["details_json"] else {}
            gear_names = json.loads(row["gear_json"]) if row["gear_json"] else []
            mini_names_raw = json.loads(row["minis_json"]) if row["minis_json"] else []

            # Handle variant group format: [["MiniA", "MiniA2"], ["MiniB"]] -> ["MiniA", "MiniB"]
            # Extract first name from each group (representative)
            mini_names = []
            for item in mini_names_raw:
                if isinstance(item, list) and item:
                    mini_names.append(item[0])  # Take first variant as representative
                elif isinstance(item, str):
                    mini_names.append(item)  # Legacy flat format

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

            # Update details with computed Stats
            details["Stats"] = computed_stats

            # Write back
            conn.execute(f"UPDATE {table} SET details_json = ? WHERE rowid = ?", (json.dumps(details), row["rowid"]))
            updated += 1

        conn.commit()
        total_updated += updated
    conn.close()

    print(f"\nDone! Updated {total_updated} entries across loadouts + fg_loadouts.")


if __name__ == "__main__":
    main()
