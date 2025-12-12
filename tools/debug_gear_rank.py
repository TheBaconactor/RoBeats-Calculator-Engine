"""Debug: Check if the optimal gear items are in the top-ranked candidates."""
import os, sys
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from gear_optimizer.data.csv_parser import load_all_gears_list, load_all_minis_list
from gear_optimizer.core.config import load_paths_cache
from gear_optimizer.core.utils import prune_dominated_gear

paths = load_paths_cache()
all_gears = load_all_gears_list(paths)
all_minis = load_all_minis_list(paths)

p_color = "Chill"  # Take Your Time uses Chill
s_color = "Beat"   # Secondary color

all_colors = ["Chill", "Flow", "Rush", "Beat", "Vibe"]

def score_candidate(x):
    """Normalized average of ELEMENTAL, BASE STATS, and COMBINED scores."""
    # ELEMENTAL
    elemental = 0
    elemental += x.get(p_color, 0) * 3
    if s_color and s_color != p_color:
        elemental += x.get(s_color, 0) * 2
    for color in all_colors:
        if color != p_color and color != s_color:
            elemental += x.get(color, 0) * 1
    
    # BASE STATS
    base_stats = 0
    base_stats += x.get("Perfect Points", 0) * 3
    base_stats += x.get("Combo Multiplier", 0) * 3
    base_stats += x.get("Fever Multiplier", 0) * 3
    base_stats += x.get("Fever Time", 0) * 2
    base_stats += x.get("Fever Fill Rate", 0) * 2
    
    # COMBINED
    combined = elemental + base_stats
    
    # Normalize
    norm_elemental = elemental  # Keep raw for comparison
    norm_base = base_stats
    norm_combined = combined / 2
    
    return (norm_elemental + norm_base + norm_combined) / 3

slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
gear_pool = {s: [] for s in slots}
for g in all_gears:
    if g["type"] in gear_pool:
        gear_pool[g["type"]].append(g)

# Prune dominated
for s in slots:
    gear_pool[s] = prune_dominated_gear(gear_pool[s])

# Rank by heuristic
gear_rank_cache = {
    s: sorted(gear_pool[s], key=score_candidate, reverse=True)[:10]
    for s in slots
}

# Check specific items
targets = [
    ("Neck", "Legendary Vibe Ringleader's Necktie"),
    ("Neck", "Legendary Rebel's Scarf"),
    ("Face", "Legendary Rebel's Mask"),
    ("Face", "Legendary Marshall's Mask"),
    ("Back", "No-Scope Loadout"),
    ("Back", "Legendary Rebel's Sash"),
]

print("=== Gear Ranking Analysis ===\n")
for slot, name in targets:
    ranked = gear_rank_cache[slot]
    rank = next((i+1 for i, g in enumerate(ranked) if g.get("Name") == name), None)
    score = next((score_candidate(g) for g in ranked if g.get("Name") == name), "N/F")
    in_pool = any(g.get("Name") == name for g in gear_pool[slot])
    print(f"{slot:6} | {name:40} | Rank: {rank if rank else '>10 or pruned'} | Score: {score} | In pool: {in_pool}")

print("\n=== Top 10 for each relevant slot ===\n")
for slot in ["Neck", "Face", "Back"]:
    print(f"\n{slot}:")
    for i, g in enumerate(gear_rank_cache[slot][:10]):
        print(f"  {i+1}. {g.get('Name'):40} score={score_candidate(g)}")
