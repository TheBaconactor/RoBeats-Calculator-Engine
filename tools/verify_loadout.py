"""
Verify exact score for a specific loadout using explicit gem counts.
"""
import sys
import os
import json
import numpy as np
import copy
sys.path.insert(0, '.')

from gear_optimizer.data.csv_parser import load_csv_db, read_table
from gear_optimizer.solver.scoring import evaluate_stats_score
from gear_optimizer.core.utils import safe_int, safe_float
from gear_optimizer.core.constants import (
    GEM_SCALE_FEVER, GEM_SCALE_NORMAL, GEM_STAT_TO_ELEMENT_SCALE, 
    ELEMENTAL_GEM_SCALE, MAX_STAT_INDEX, TOTAL_ROWS
)

# Hardcode paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
GEAR_CSV = os.path.join(PROJECT_ROOT, "Data", "Gear", "Gears.csv")
MINI_CSV = os.path.join(PROJECT_ROOT, "Data", "Gear", "Minis.csv")
SONGS_DIR = os.path.join(PROJECT_ROOT, "Data", "Hard")
STATS_TXT = os.path.join(PROJECT_ROOT, "Data", "Gear", "Stats.txt")

# --- Custom Song Parser for .txt files ---
def parse_song_file(filepath):
    meta = {}
    timestamps = []
    
    with open(filepath, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.readlines()]
        
    # Section pointers
    in_song_data = False
    
    for line in lines:
        if not line: continue
        
        if line.startswith("Song Data"):
            in_song_data = True
            continue
            
        if in_song_data:
            # Format: Timestamp <tab> ...
            parts = line.split('\t')
            if parts:
                try:
                    t = float(parts[0])
                    timestamps.append(t)
                except:
                    pass
        elif '\t' in line:
            # Metadata key-value
            k, v = line.split('\t', 1)
            meta[k.strip()] = v.strip()
            
    return {
        "metadata": meta,
        "song_data": {
            "timestamps": np.array(timestamps, dtype=np.float64)
        }
    }

def find_and_load_song(name_part):
    for f in os.listdir(SONGS_DIR):
        if name_part in f and f.endswith(".txt"):
            return parse_song_file(os.path.join(SONGS_DIR, f))
    return None

# --- Ref Arrays (Copied from app.py) ---
def preload_ref_arrays(stats_table):
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

# --- Load Data ---
gears = load_csv_db(GEAR_CSV, "gear")
minis = load_csv_db(MINI_CSV, "mini")

# --- User's Loadout ---
gear_names = [
    "The Games: Hidden Shine",
    "Legendary Vibe Ringleader's Necktie",
    "Legendary Vibe Ringleader's Harmonica",
    "Legendary Marshall's Coat",
    "Legendary Vibe Ringleader's Band Kit",
    "Legendary Vibe Ringleader's Slacks",
]
mini_names = ["Fusq", "Trailblazing Trance Zara", "Electroman"]

# --- Gem Allocation (from Run 1 / Config) ---
user_gems = {
    "Fever Time": 0,
    "Fever Fill Rate": 13,
    "Fever Multiplier": 5,
    "Combo Multiplier": 0,
    "Perfect Points": 0,
    "Element": 72  # Assumed Vibe
}

print("=== LOADOUT ===")
base_stats = {k: 0 for k in ['Perfect Points', 'Combo Multiplier', 'Fever Multiplier', 'Fever Time', 'Fever Fill Rate', 'Beat', 'Vibe', 'Rush', 'Flow', 'Chill']}

for n in gear_names:
    g = gears.get(n)
    if not g: print(f"MISSING GEAR: {n}")
    else:
        for k in base_stats: base_stats[k] += g.get(k, 0)
        
for n in mini_names:
    m = minis.get(n)
    if not m: print(f"MISSING MINI: {n}")
    else:
        for k in base_stats: base_stats[k] += m.get(k, 0)

print(f"Base Stats (Raw): {base_stats}")

# --- Apply Gems to Stats ---
calc_stats = copy.deepcopy(base_stats)
calc_stats["Fever Time"] += user_gems["Fever Time"] * GEM_SCALE_FEVER
calc_stats["Beat"] += user_gems["Fever Time"] * GEM_STAT_TO_ELEMENT_SCALE

calc_stats["Fever Fill Rate"] += user_gems["Fever Fill Rate"] * GEM_SCALE_FEVER
calc_stats["Vibe"] += user_gems["Fever Fill Rate"] * GEM_STAT_TO_ELEMENT_SCALE

calc_stats["Fever Multiplier"] += user_gems["Fever Multiplier"] * GEM_SCALE_FEVER
calc_stats["Rush"] += user_gems["Fever Multiplier"] * GEM_STAT_TO_ELEMENT_SCALE

# Apply Overflow (Vibe)
calc_stats["Vibe"] += user_gems["Element"] * ELEMENTAL_GEM_SCALE

# Apply Team Buff (T5 Vibe) - HARDCODED as per log "[Auto-Config] Set Team Buff: T5 | Team Color: Vibe"
print("Applying Team Buff T5 (Vibe)...")
calc_stats["Perfect Points"] += 25
calc_stats["Vibe"] += 30

print(f"Stats with Gems & Buff (Before Cap): {calc_stats}")

# Cap (implicit in lookup, but good to visualize)
print(f"MAX_STAT_INDEX: {MAX_STAT_INDEX}")

# --- Load Song & Evaluate ---
song = find_and_load_song("Feeling Alright (Hard) by Rutra")
if not song:
    print("Song not found")
    exit(1)

stats_table = read_table(STATS_TXT)
ref_arrays = preload_ref_arrays(stats_table)

# DEBUG: Print intermediate values inside evaluate_stats_score simulation
timestamps = song["song_data"]["timestamps"]
total_notes = len(timestamps)
long_notes = safe_int(song["metadata"].get("Long Notes", 0))

p_color = song["metadata"].get("Primary Color", "")
s_color = song["metadata"].get("Secondary Color", "")
primary_val = calc_stats.get(p_color, 0)
secondary_val = calc_stats.get(s_color, 0)

# Lookup values
def lookup(val, arr, max_idx=TOTAL_ROWS):
    idx = int(val)
    if idx < 0: idx = 0
    if idx >= max_idx: idx = max_idx - 1
    return arr[idx]

base_pp = lookup(calc_stats["Perfect Points"], ref_arrays["Perfect Points"], TOTAL_ROWS)
combo_mul = lookup(calc_stats["Combo Multiplier"], ref_arrays["Combo Multiplier"], TOTAL_ROWS)
fever_mul = lookup(calc_stats["Fever Multiplier"], ref_arrays["Fever Multiplier"], TOTAL_ROWS)
ft_factor = lookup(calc_stats["Fever Time"], ref_arrays["Fever Time"], TOTAL_ROWS)
ff_factor = lookup(calc_stats["Fever Fill Rate"], ref_arrays["Fever Fill Rate"], TOTAL_ROWS)

total_base = (primary_val * 2) + secondary_val + base_pp

print(f"\n--- DEBUG VALUES ---")
print(f"Total Notes: {total_notes}")
print(f"Long Notes:  {long_notes}")
print(f"Primary ({p_color}): {primary_val} * 2 = {primary_val*2}")
print(f"Secondary ({s_color}): {secondary_val}")
print(f"Base PP ({calc_stats['Perfect Points']}): {base_pp}")
print(f"Total Base: {total_base}")
print(f"Combo Mul ({calc_stats['Combo Multiplier']}): {combo_mul}")
print(f"Fever Mul ({calc_stats['Fever Multiplier']}): {fever_mul}")
print(f"FT Factor ({calc_stats['Fever Time']}): {ft_factor}")
print(f"FF Factor ({calc_stats['Fever Fill Rate']}): {ff_factor}")
print(f"--------------------\n")

score = evaluate_stats_score(
    calc_stats,
    song,
    ref_arrays
)

print(f"\nCALCULATED SCORE: {score:,}")
print(f"Goal Score:       33,420,761")
diff = score - 33420761
print(f"Difference:       {diff:,}")
if abs(diff) < 100:
    print("MATCH CONFIRMED!")
else:
    print("MISMATCH!")
