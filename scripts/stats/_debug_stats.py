"""
Debug: Check actual stats for a lonely stella loadout
"""

import sqlite3
import json
import sys

sys.path.insert(0, ".")

from gear_optimizer.data.csv_parser import load_csv_db
from gear_optimizer.core.constants import (
    GEM_SCALE_NORMAL,
    GEM_SCALE_FEVER,
    ELEMENTAL_GEM_SCALE,
    GEM_STAT_TO_ELEMENT_SCALE,
    SKIP_ITEM_KEYS,
)

# Load gear/mini data
gears = load_csv_db("Data/Gear/Gears.csv", "gear")
minis = load_csv_db("Data/Gear/Minis.csv", "mini")

conn = sqlite3.connect("evolution.db")
conn.row_factory = sqlite3.Row
from gear_optimizer.data.database import _load_piece_name_encoding_maps, _unpack_id_groups, _unpack_id_list, _unpack_stats_after_load

maps = _load_piece_name_encoding_maps(conn, db_path="evolution.db")

row = conn.execute("""
    SELECT song_name, gear_ids_blob, minis_ids_blob, details_json
    FROM team_buff_loadouts 
    WHERE song_name LIKE '%lonely stella%'
    ORDER BY score DESC
    LIMIT 1
""").fetchone()

gear_ids = _unpack_id_list(row["gear_ids_blob"])
gear_names = [maps.gear_id_to_name.get(int(i), "") for i in gear_ids if int(i) > 0]
gear_names = [g for g in gear_names if g]
mini_id_groups = _unpack_id_groups(row["minis_ids_blob"])
minis_raw = [
    sorted({maps.mini_id_to_name.get(int(i), "") for i in g if int(i) > 0}) for g in (mini_id_groups or []) if g
]
minis_raw = [[n for n in g if n] for g in minis_raw if g]
details = json.loads(row["details_json"])
details = _unpack_stats_after_load(details) or {}

# Extract first mini from each group
mini_names = []
for item in minis_raw:
    if isinstance(item, list) and item:
        mini_names.append(item[0])
    elif isinstance(item, str):
        mini_names.append(item)

print(f"Song: {row['song_name']}")
print(f"\nGear: {gear_names}")
print(f"Minis: {mini_names}")
print(f"\nGemCounts: {details.get('GemCounts', {})}")
print(f"SelectedElement: {details.get('SelectedElement', '')}")
print(f"FT: {details.get('FT', 0)}, FF: {details.get('FF', 0)}")

# Compute stats from JUST gear + minis (no config base stats)
print("\n=== GEAR STATS ===")
gear_stats = {}
for name in gear_names:
    g = gears.get(name, {})
    if not g:
        print(f"  ❌ {name}: NOT FOUND")
        continue
    print(f"  {name}:")
    for k, v in g.items():
        if k not in SKIP_ITEM_KEYS and isinstance(v, (int, float)) and v != 0:
            print(f"    {k}: {v}")
            gear_stats[k] = gear_stats.get(k, 0) + v

print("\n=== MINI STATS ===")
mini_stats = {}
for name in mini_names:
    m = minis.get(name, {})
    if not m:
        print(f"  ❌ {name}: NOT FOUND")
        continue
    print(f"  {name}:")
    for k, v in m.items():
        if k not in SKIP_ITEM_KEYS and isinstance(v, (int, float)) and v != 0:
            print(f"    {k}: {v}")
            mini_stats[k] = mini_stats.get(k, 0) + v

# Total from gear + minis only
total_stats = {}
for k in set(list(gear_stats.keys()) + list(mini_stats.keys())):
    total_stats[k] = gear_stats.get(k, 0) + mini_stats.get(k, 0)

print("\n=== GEAR + MINI TOTALS (no gems) ===")
for k in [
    "Perfect Points",
    "Combo Multiplier",
    "Fever Multiplier",
    "Fever Time",
    "Fever Fill Rate",
    "Chill",
    "Flow",
    "Rush",
    "Beat",
    "Vibe",
]:
    print(f"  {k}: {total_stats.get(k, 0)}")

# Now add gem contributions
gem_counts = details.get("GemCounts", {})
g_pp = gem_counts.get("Perfect Points", 0) or 0
g_cm = gem_counts.get("Combo Multiplier", 0) or 0
g_fm = gem_counts.get("Fever Multiplier", 0) or 0
g_ft = details.get("FT", 0) or 0
g_ff = details.get("FF", 0) or 0
g_ov = gem_counts.get("Element", 0) or 0
sel_elem = details.get("SelectedElement", "")

print(f"\n=== GEM CONTRIBUTIONS ===")
print(f"  PP gems ({g_pp}): +{g_pp * GEM_SCALE_NORMAL} PP, +{g_pp * GEM_STAT_TO_ELEMENT_SCALE} Chill")
print(f"  CM gems ({g_cm}): +{g_cm * GEM_SCALE_NORMAL} CM, +{g_cm * GEM_STAT_TO_ELEMENT_SCALE} Flow")
print(f"  FM gems ({g_fm}): +{g_fm * GEM_SCALE_FEVER} FM, +{g_fm * GEM_STAT_TO_ELEMENT_SCALE} Rush")
print(f"  FT gems ({g_ft}): +{g_ft * GEM_SCALE_FEVER} FT, +{g_ft * GEM_STAT_TO_ELEMENT_SCALE} Beat")
print(f"  FF gems ({g_ff}): +{g_ff * GEM_SCALE_FEVER} FF, +{g_ff * GEM_STAT_TO_ELEMENT_SCALE} Vibe")
print(f"  Overflow ({g_ov}) -> {sel_elem}: +{g_ov * ELEMENTAL_GEM_SCALE}")

# Final stats (gear + minis + gems, NO config base)
final_stats = dict(total_stats)
final_stats["Perfect Points"] = final_stats.get("Perfect Points", 0) + g_pp * GEM_SCALE_NORMAL
final_stats["Combo Multiplier"] = final_stats.get("Combo Multiplier", 0) + g_cm * GEM_SCALE_NORMAL
final_stats["Fever Multiplier"] = final_stats.get("Fever Multiplier", 0) + g_fm * GEM_SCALE_FEVER
final_stats["Fever Time"] = final_stats.get("Fever Time", 0) + g_ft * GEM_SCALE_FEVER
final_stats["Fever Fill Rate"] = final_stats.get("Fever Fill Rate", 0) + g_ff * GEM_SCALE_FEVER
final_stats["Chill"] = final_stats.get("Chill", 0) + g_pp * GEM_STAT_TO_ELEMENT_SCALE
final_stats["Flow"] = final_stats.get("Flow", 0) + g_cm * GEM_STAT_TO_ELEMENT_SCALE
final_stats["Rush"] = final_stats.get("Rush", 0) + g_fm * GEM_STAT_TO_ELEMENT_SCALE
final_stats["Beat"] = final_stats.get("Beat", 0) + g_ft * GEM_STAT_TO_ELEMENT_SCALE
final_stats["Vibe"] = final_stats.get("Vibe", 0) + g_ff * GEM_STAT_TO_ELEMENT_SCALE
if sel_elem:
    final_stats[sel_elem] = final_stats.get(sel_elem, 0) + g_ov * ELEMENTAL_GEM_SCALE

print(f"\n=== FINAL STATS (gear + minis + gems, NO config base) ===")
for k in [
    "Perfect Points",
    "Combo Multiplier",
    "Fever Multiplier",
    "Fever Time",
    "Fever Fill Rate",
    "Chill",
    "Flow",
    "Rush",
    "Beat",
    "Vibe",
]:
    print(f"  {k}: {final_stats.get(k, 0)}")

print(f"\n=== WHAT DB CURRENTLY HAS ===")
db_stats = details.get("Stats", {})
for k in [
    "Perfect Points",
    "Combo Multiplier",
    "Fever Multiplier",
    "Fever Time",
    "Fever Fill Rate",
    "Chill",
    "Flow",
    "Rush",
    "Beat",
    "Vibe",
]:
    print(f"  {k}: {db_stats.get(k, 0)}")

conn.close()
