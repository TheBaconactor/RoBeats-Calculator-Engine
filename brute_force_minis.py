"""
Brute-force sweep of top mini combinations to find the true optimal.
Tests all C(20,3) = 1140 combinations of the top 20 minis.
"""
import itertools
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gear_optimizer.data.csv_parser import parse_gear_rows, parse_mini_rows
from gear_optimizer.pipeline.song_processor import process_song_task
from gear_optimizer.solver.scoring import worker_coevolution_evaluate, GEM_SOLVER_CACHE, FG_CACHE, FEVER_TIMELINE_CACHE
from gear_optimizer.data.csv_parser import read_table
from gear_optimizer.core.constants import TOTAL_ROWS
import numpy as np

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

def read_song(fp):
    """Parse song file into calc_song format."""
    calc_song = {"notes": [], "metadata": {}, "song_data": {"timestamps": [], "lanes": []}}
    
    with open(fp, "r", encoding="utf-8") as f:
        lines = [l.rstrip() for l in f]
    
    section = "header"
    for line in lines:
        if not line.strip():
            continue
        if line.startswith("Timing Points"):
            section = "timing"
            continue
        if line.startswith("Song Data"):
            section = "song_data"
            continue
        
        if section == "header":
            parts = line.split("\t", 1)
            if len(parts) == 2:
                calc_song["metadata"][parts[0].strip()] = parts[1].strip()
        elif section == "song_data":
            parts = line.split("\t")
            if len(parts) >= 2:
                try:
                    time = float(parts[0])
                    lane = int(parts[1]) if len(parts) > 1 else 0
                    calc_song["song_data"]["timestamps"].append(time)
                    calc_song["song_data"]["lanes"].append(lane)
                except:
                    pass
    
    return calc_song

# Load data
print("Loading data...")
gears = parse_gear_rows("Data/Gear/Gears.csv")
minis = parse_mini_rows("Data/Gear/Minis.csv")
gears_by_name = {g["Name"]: g for g in gears}
minis_by_name = {m["Name"]: m for m in minis}

# Load song
print("Loading song...")
calc_song = read_song("Data/Hard/Take Your Time (Hard) by Rutra.txt")
print(f"Song has {len(calc_song['song_data']['timestamps'])} notes")

# Build ref arrays
ref_arrays = build_ref_arrays()

# Best gear from GA
best_gear_names = [
    "Autumnal Adept's Bloom",
    "Legendary Rebel's Scarf", 
    "Legendary Marshall's Mask",
    "Legendary Marshall's Coat",
    "Legendary Rebel's Sash",
    "Legendary Rebel's Trousers",
]
best_gear = [gears_by_name.get(n, {}) for n in best_gear_names]

# Base stats (T5 team buff)
base_stats_fixed = {
    "Fever Time": 100,
    "Fever Fill Rate": 50,
    "Chill": 0, "Flow": 0, "Rush": 0, "Beat": 0, "Vibe": 0,
    "Perfect Points": 0,
    "Combo Multiplier": 0,
    "Fever Multiplier": 0,
}

cfg_data = {
    "selected_color": "Chill",
    "use_gpu": False,
    "user_ft": 0, "user_ff": 0, "user_pp": 0, "user_cm": 0, "user_fm": 0,
    "static_elem_input": 0,
}

# Rank minis by Chill heuristic
def score_mini(m):
    return m.get("Chill", 0) * 3 + m.get("Perfect Points", 0) * 2 + m.get("Combo Multiplier", 0) * 2 + m.get("Fever Multiplier", 0) * 2

ranked_minis = sorted(minis, key=score_mini, reverse=True)[:20]
print(f"Testing top {len(ranked_minis)} minis: {[m['Name'] for m in ranked_minis]}")

# Clear caches
GEM_SOLVER_CACHE.clear()
FG_CACHE.clear()
FEVER_TIMELINE_CACHE.clear()

# Brute force all combinations
print(f"\nTesting {len(list(itertools.combinations(ranked_minis, 3)))} mini combinations...")
best_score = 0
best_minis = []
best_result = None

for i, combo in enumerate(itertools.combinations(ranked_minis, 3)):
    mini_list = list(combo)
    genome = best_gear + mini_list
    
    result = worker_coevolution_evaluate((genome, base_stats_fixed, cfg_data, calc_song, ref_arrays))
    score = result["Score"]
    
    if score > best_score:
        best_score = score
        best_minis = [m["Name"] for m in mini_list]
        best_result = result
        print(f"  New best: {score} with {best_minis}")
    
    if (i + 1) % 100 == 0:
        print(f"  Tested {i+1} combinations...")

print(f"\n=== BRUTE FORCE RESULT ===")
print(f"Best Score: {best_score}")
print(f"Best Minis: {best_minis}")
if best_result and "Data" in best_result:
    data = best_result["Data"]
    if "gems" in data:
        print(f"Gem Allocation: {data['gems']}")
