"""
Force test HyuN vs DJ Hiku to verify the optimal score.
"""
import numpy as np
from gear_optimizer.data.csv_parser import parse_gear_rows, parse_mini_rows, read_table
from gear_optimizer.solver.scoring import worker_coevolution_evaluate
from gear_optimizer.core.constants import TOTAL_ROWS

# Build ref_arrays like app.py does
def build_ref_arrays():
    stats_table = read_table("Data/Stats.csv")
    stat_names = [
        "Perfect Points", "Combo Multiplier", "Fever Multiplier",
        "Fever Fill Rate", "Fever Time",
    ]
    ref_arrays = {}
    for i, name in enumerate(stat_names):
        temp_list = []
        for v in range(TOTAL_ROWS + 1):
            lookup_index = TOTAL_ROWS - v
            try:
                val = stats_table[lookup_index][i] if stats_table else 0
            except Exception:
                val = 0
            temp_list.append(val)
        ref_arrays[name] = np.array(temp_list, dtype=np.float64)
    return ref_arrays

# Read song file  
def read_song_simple(fp):
    calc_song = {"notes": [], "metadata": {}}
    with open(fp, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    
    for line in lines:
        if "=" in line:
            key, val = line.split("=", 1)
            calc_song["metadata"][key.strip()] = val.strip()
        elif "," in line:
            parts = line.split(",")
            if len(parts) >= 2:
                try:
                    time = float(parts[0])
                    lane = int(parts[1]) if parts[1] else 0
                    calc_song["notes"].append({"time": time, "lane": lane})
                except:
                    pass
    return calc_song

# Load data
gears = parse_gear_rows("Data/Gear/Gears.csv")
minis = parse_mini_rows("Data/Gear/Minis.csv")
gears_by_name = {g["Name"]: g for g in gears}
minis_by_name = {m["Name"]: m for m in minis}

# Load song
calc_song = read_song_simple("Data/Hard/Take Your Time (Hard) by Rutra.txt")
print(f"Loaded song with {len(calc_song['notes'])} notes")
print(f"Metadata: {calc_song['metadata']}")

# Build ref arrays
ref_arrays = build_ref_arrays()

# Best gear from GA runs
current_gear_names = [
    "Autumnal Adept's Bloom",
    "Legendary Rebel's Scarf", 
    "Legendary Marshall's Mask",
    "Legendary Marshall's Coat",
    "Legendary Rebel's Sash",
    "Legendary Rebel's Trousers",
]
current_gear = [gears_by_name.get(n, {}) for n in current_gear_names]

# Alternative gear from claimed optimal
alt_gear_names = [
    "Autumnal Adept's Bloom",
    "Legendary Vibe Ringleader's Necktie",
    "Legendary Rebel's Mask",
    "Legendary Marshall's Coat",
    "No-Scope Loadout",
    "Legendary Rebel's Trousers",
]
alt_gear = [gears_by_name.get(n, {}) for n in alt_gear_names]
for n in alt_gear_names:
    if n not in gears_by_name:
        print(f"Missing gear: {n}")

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

print("\n=== Testing Mini Combinations ===")

# Test combinations
combos = [
    ("DJ Hiku + YooH + Apocalypse (current gear)", current_gear, ["DJ Hiku: Party Mode", "YooH", "Apocalypse Survivor Starlet"]),
    ("HyuN + YooH + Apocalypse (current gear)", current_gear, ["YooH", "HyuN", "Apocalypse Survivor Starlet"]),
    ("HyuN + YooH + Apocalypse (alt gear)", alt_gear, ["YooH", "HyuN", "Apocalypse Survivor Starlet"]),
    ("Zara + YooH + Apocalypse (current gear)", current_gear, ["YooH", "Trailblazing Trance Zara", "Apocalypse Survivor Starlet"]),
    ("DJ Hiku + YooH + Apocalypse (alt gear)", alt_gear, ["DJ Hiku: Party Mode", "YooH", "Apocalypse Survivor Starlet"]),
]

results = []
for name, gear, mini_names in combos:
    minis = [minis_by_name[n] for n in mini_names]
    genome = gear + minis
    result = worker_coevolution_evaluate((genome, base_stats_fixed, cfg_data, calc_song, ref_arrays))
    results.append((name, result['Score']))
    print(f"{name}: {result['Score']}")

print(f"\nBest: {max(results, key=lambda x: x[1])}")
