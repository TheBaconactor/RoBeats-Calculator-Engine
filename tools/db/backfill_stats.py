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

    # Use EMPTY base stats - DB Stats should represent ONLY the loadout contribution
    # (gear + minis + gems for that specific entry), NOT user config settings.
    # User config (team buffs, user gems) varies per user and should be applied
    # at display time, not baked into the persisted Stats.
    base_stats = {
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
    print(f"Using empty base stats (loadout-only): {base_stats}")

    db_path = get_evolution_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    print("Fetching entries...")
    # Find entries to update
    cur = conn.execute("""
        SELECT rowid, song_name, gear_json, minis_json, details_json 
        FROM loadouts
    """)
    rows = cur.fetchall()

    updated = 0

    print(f"Processing {len(rows)} entries... this may take a moment.")

    for i, row in enumerate(rows):
        if i % 10000 == 0:
            print(f"Processed {i}/{len(rows)}...")

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

        # Compute Stats (Unconditionally recompute to ensure Team Buffs are added)
        computed_stats = compute_full_stats(
            gear_names, mini_names, gem_counts, selected_element, gears_by_name, minis_by_name, base_stats
        )

        # Update details with computed Stats
        details["Stats"] = computed_stats

        # Write back
        conn.execute("UPDATE loadouts SET details_json = ? WHERE rowid = ?", (json.dumps(details), row["rowid"]))
        updated += 1

    conn.commit()
    conn.close()

    print(f"Done! Updated {updated} entries.")


if __name__ == "__main__":
    main()
