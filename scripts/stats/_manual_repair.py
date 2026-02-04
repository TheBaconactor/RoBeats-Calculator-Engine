"""Manually repair the 18 broken entries and verify."""

import sqlite3
import json
import sys

sys.path.insert(0, ".")

from gear_optimizer.core.stats_calculator import compute_full_stats
from gear_optimizer.data.csv_parser import parse_gear_rows, parse_mini_rows
from gear_optimizer.core.config import load_paths_cache

# Load gear/mini data
paths = load_paths_cache()
gears_list = parse_gear_rows(paths.get("Gears", ""))
minis_list = parse_mini_rows(paths.get("Minis", ""))
gears_by_name = {g["Name"]: g for g in gears_list}
minis_by_name = {m["Name"]: m for m in minis_list}

# Empty base stats
base_stats = {
    stat: 0
    for stat in [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Fill Rate",
        "Fever Time",
        "Chill",
        "Flow",
        "Rush",
        "Beat",
        "Vibe",
    ]
}

# Get all broken entries
conn = sqlite3.connect("evolution.db")
conn.row_factory = sqlite3.Row

print("Finding broken entries...")
rows = conn.execute("SELECT rowid, gear_json, minis_json, details_json FROM team_buff_loadouts").fetchall()

broken = []
for row in rows:
    details = json.loads(row["details_json"]) if row["details_json"] else {}
    stats = details.get("Stats")
    if stats is None or (isinstance(stats, dict) and len(stats) == 0):
        broken.append(row)

print(f"Found {len(broken)} broken entries")

# Repair each one
repaired = 0
for row in broken:
    details = json.loads(row["details_json"]) if row["details_json"] else {}
    gear_names = json.loads(row["gear_json"]) if row["gear_json"] else []
    mini_names_raw = json.loads(row["minis_json"]) if row["minis_json"] else []

    # Handle variant group format
    mini_names = []
    for item in mini_names_raw:
        if isinstance(item, list) and item:
            mini_names.append(item[0])
        elif isinstance(item, str):
            mini_names.append(item)

    gem_counts = dict(details.get("GemCounts", {}) or {})
    gem_counts["Fever Time"] = int(details.get("FT", 0) or 0)
    gem_counts["Fever Fill Rate"] = int(details.get("FF", 0) or 0)
    selected_element = details.get("SelectedElement") or details.get("Selected Element") or ""

    # Compute Stats
    computed = compute_full_stats(
        gear_names, mini_names, gem_counts, selected_element, gears_by_name, minis_by_name, base_stats
    )

    details["Stats"] = computed

    # Update
    conn.execute("UPDATE team_buff_loadouts SET details_json = ? WHERE rowid = ?", (json.dumps(details), row["rowid"]))
    repaired += 1

    if repaired <= 3:
        print(f"  Repaired rowid {row['rowid']}: Chill={computed.get('Chill', 0)}, Vibe={computed.get('Vibe', 0)}")

print(f"Repaired {repaired} entries")
print("Committing...")
conn.commit()
print("Committed!")

# Verify
print("\nVerifying repairs...")
verify = conn.execute("SELECT rowid, details_json FROM team_buff_loadouts WHERE rowid IN (16207, 16213)").fetchall()
for row in verify:
    d = json.loads(row[1])
    stats = d.get("Stats", {})
    print(f"  rowid {row[0]}: Stats has {len(stats)} keys, Vibe={stats.get('Vibe', 'MISSING')}")

conn.close()
print("\nDone!")
