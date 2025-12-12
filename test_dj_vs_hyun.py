"""
Direct test: Does HyuN beat DJ Hiku for this song?
Uses the actual main.py evaluation path.
"""
import configparser
import numpy as np

from gear_optimizer.data.csv_parser import parse_gear_rows, parse_mini_rows, read_table
from gear_optimizer.core.constants import TOTAL_ROWS
from gear_optimizer.pipeline.song_processor import read_song_file
from gear_optimizer.solver.scoring import (
    worker_coevolution_evaluate, 
    GEM_SOLVER_CACHE, 
    FG_CACHE, 
    FEVER_TIMELINE_CACHE
)

def build_ref_arrays():
    stats_table = read_table("Data/Stats.csv")
    stat_names = ["Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Fill Rate", "Fever Time"]
    ref_arrays = {}
    for i, name in enumerate(stat_names):
        temp_list = []
        for v in range(TOTAL_ROWS + 1):
            lookup_index = TOTAL_ROWS - v
            try:
                val = stats_table[lookup_index][i] if stats_table else 0
            except:
                val = 0
            temp_list.append(val)
        ref_arrays[name] = np.array(temp_list, dtype=np.float64)
    return ref_arrays

print("Loading resources...")
gears = parse_gear_rows("Data/Gear/Gears.csv")
minis = parse_mini_rows("Data/Gear/Minis.csv")
gears_by_name = {g["Name"]: g for g in gears}
minis_by_name = {m["Name"]: m for m in minis}

print("Loading song...")
calc_song = read_song_file("Data/Hard/Take Your Time (Hard) by Rutra.txt")
print(f"Song metadata: {calc_song.get('metadata', {})}")

ref_arrays = build_ref_arrays()

# Best gear from GA
gear = [
    gears_by_name["Autumnal Adept's Bloom"],
    gears_by_name["Legendary Rebel's Scarf"], 
    gears_by_name["Legendary Marshall's Mask"],
    gears_by_name["Legendary Marshall's Coat"],
    gears_by_name["Legendary Rebel's Sash"],
    gears_by_name["Legendary Rebel's Trousers"],
]

base_stats = {
    "Fever Time": 100, "Fever Fill Rate": 50,
    "Chill": 0, "Flow": 0, "Rush": 0, "Beat": 0, "Vibe": 0,
    "Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0,
}

cfg_data = {
    "selected_color": "Chill", "use_gpu": False,
    "user_ft": 0, "user_ff": 0, "user_pp": 0, "user_cm": 0, "user_fm": 0,
    "static_elem_input": 0,
}

# Clear caches
GEM_SOLVER_CACHE.clear()
FG_CACHE.clear()
FEVER_TIMELINE_CACHE.clear()

print("\n=== Testing Mini Combinations ===")

test_combos = [
    ["DJ Hiku: Party Mode", "YooH", "Apocalypse Survivor Starlet"],
    ["HyuN", "YooH", "Apocalypse Survivor Starlet"],
    ["Trailblazing Trance Zara", "YooH", "Apocalypse Survivor Starlet"],
    ["HyuN", "Trailblazing Trance Zara", "Apocalypse Survivor Starlet"],
    ["DJ Hiku: Party Mode", "HyuN", "Apocalypse Survivor Starlet"],
    ["DJ Hiku: Party Mode", "HyuN", "YooH"],
]

results = []
for combo in test_combos:
    mini_objs = [minis_by_name[n] for n in combo]
    genome = gear + mini_objs
    
    result = worker_coevolution_evaluate((genome, base_stats, cfg_data, calc_song, ref_arrays))
    score = result["Score"]
    results.append((combo, score, result.get("Data", {})))
    print(f"{combo}: {score}")

print("\n=== RANKED RESULTS ===")
for combo, score, data in sorted(results, key=lambda x: x[1], reverse=True):
    gems = data.get("gems", {})
    print(f"{score:,}: {combo}")
    if gems:
        print(f"    Gems: FT={gems.get('Fever Time',0)}, FF={gems.get('Fever Fill',0)}, FM={gems.get('Fever Multiplier',0)}, PP={gems.get('Perfect Points',0)}, OV={gems.get('Overflow',0)}")
