"""Debug why #include signal.h has empty Stats after repair."""

import sqlite3
import json
import sys

sys.path.insert(0, ".")

from gear_optimizer.core.stats_calculator import compute_full_stats
from gear_optimizer.data.csv_parser import parse_gear_rows, parse_mini_rows
from gear_optimizer.core.config import load_paths_cache
from gear_optimizer.data.database import _load_piece_name_encoding_maps, _unpack_id_groups, _unpack_id_list, _unpack_stats_after_load

# Load gear/mini data
paths = load_paths_cache()
gears_list = parse_gear_rows(paths.get("Gears", ""))
minis_list = parse_mini_rows(paths.get("Minis", ""))
gears_by_name = {g["Name"]: g for g in gears_list}
minis_by_name = {m["Name"]: m for m in minis_list}

# Empty base stats
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

# Get a broken entry
conn = sqlite3.connect("evolution.db")
conn.row_factory = sqlite3.Row
maps = _load_piece_name_encoding_maps(conn, db_path="evolution.db")
row = conn.execute("SELECT * FROM team_buff_loadouts WHERE rowid=16207").fetchone()

print("=" * 60)
print("Debugging rowid 16207")
print("=" * 60)

details = json.loads(row["details_json"])
details = _unpack_stats_after_load(details) or {}
gear_ids = _unpack_id_list(row["gear_ids_blob"])
gear_names = [maps.gear_id_to_name.get(int(i), "") for i in gear_ids if int(i) > 0]
gear_names = [g for g in gear_names if g]
mini_id_groups = _unpack_id_groups(row["minis_ids_blob"])
mini_names_raw = [
    sorted({maps.mini_id_to_name.get(int(i), "") for i in g if int(i) > 0}) for g in (mini_id_groups or []) if g
]
mini_names_raw = [[n for n in g if n] for g in mini_names_raw if g]

print(f"Gear names: {gear_names}")
print(f"Minis raw: {mini_names_raw}")

# Handle variant group format
mini_names = []
for item in mini_names_raw:
    if isinstance(item, list) and item:
        mini_names.append(item[0])
    elif isinstance(item, str):
        mini_names.append(item)

print(f"Minis parsed: {mini_names}")

gem_counts = dict(details.get("GemCounts", {}) or {})
gem_counts["Fever Time"] = int(details.get("FT", 0) or 0)
gem_counts["Fever Fill Rate"] = int(details.get("FF", 0) or 0)
selected_element = details.get("SelectedElement") or ""

print(f"GemCounts: {gem_counts}")
print(f"SelectedElement: {selected_element}")
print()

# Check if all gears/minis exist
print("Checking gear lookup:")
for g in gear_names:
    found = g in gears_by_name
    print(f"  {g}: {'FOUND' if found else 'MISSING'}")

print("Checking mini lookup:")
for m in mini_names:
    found = m in minis_by_name
    print(f"  {m}: {'FOUND' if found else 'MISSING'}")

print()

# Compute stats
computed = compute_full_stats(
    gear_names, mini_names, gem_counts, selected_element, gears_by_name, minis_by_name, base_stats
)

print(f"Computed Stats: {computed}")
print()

# Check current DB state
print(f"Current DB Stats: {details.get('Stats')}")

conn.close()
