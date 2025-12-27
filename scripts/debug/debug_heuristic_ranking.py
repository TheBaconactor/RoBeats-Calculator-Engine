"""
Debug script to probe the heuristic ranking for gear items.
Checks what's in the top 10 for each slot on a Vibe primary song.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from gear_optimizer.data.csv_parser import parse_gear_rows
from gear_optimizer.core.utils import prune_dominated_gear

# Song colors for "Feeling Alright (Hard)"
P_COLOR = "Vibe"
S_COLOR = "Chill"  # Secondary color

# Reference gear items we're looking for
REFERENCE_ITEMS = [
    "Eternxlkz's Black17 Glasses",  # Face
    "The Games: Cape",               # Back
    "Legendary Vibe Ringleader's Slacks",  # Pants
]

def score_candidate_modern(x, p_color, s_color):
    """Modern heuristic scoring (default mode)."""
    pp = x.get("Perfect Points", 0)
    cm = x.get("Combo Multiplier", 0)
    fm = x.get("Fever Multiplier", 0)
    ft = x.get("Fever Time", 0)
    ff = x.get("Fever Fill Rate", 0)
    
    primary_val = x.get(p_color, 0) if p_color else 0
    secondary_val = x.get(s_color, 0) if (s_color and s_color != p_color) else 0
    
    modern_base = (pp * 3) + (cm * 3) + (fm * 3) + (ft * 2) + (ff * 2)
    modern_elemental_bonus = (primary_val * 2) + (secondary_val * 1)
    modern_score = modern_base + (modern_elemental_bonus // 2)
    
    return modern_score

def main():
    # Load paths
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gears_csv = os.path.join(base_path, "Data", "Gear", "Gears.csv")
    
    all_gears = parse_gear_rows(gears_csv)
    print(f"Loaded {len(all_gears)} gear items")
    
    # Group by slot
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gear_pool = {s: [] for s in slots}
    for g in all_gears:
        if g["type"] in gear_pool:
            gear_pool[g["type"]].append(g)
    
    print("\n=== BEFORE DOMINANCE PRUNING ===")
    for s in slots:
        print(f"  {s}: {len(gear_pool[s])} items")
    
    # Apply dominance pruning
    total_before = sum(len(gear_pool[s]) for s in slots)
    for s in slots:
        gear_pool[s] = prune_dominated_gear(gear_pool[s])
    total_after = sum(len(gear_pool[s]) for s in slots)
    
    print(f"\n=== AFTER DOMINANCE PRUNING ===")
    print(f"Removed {total_before - total_after} dominated items")
    for s in slots:
        print(f"  {s}: {len(gear_pool[s])} items")
    
    # Check if reference items survived pruning
    print(f"\n=== REFERENCE ITEM CHECK ===")
    for ref_item in REFERENCE_ITEMS:
        found = False
        for s in slots:
            for g in gear_pool[s]:
                if g.get("Name") == ref_item:
                    found = True
                    score = score_candidate_modern(g, P_COLOR, S_COLOR)
                    print(f"✓ '{ref_item}' survived in {s} pool (heuristic score: {score})")
                    break
            if found:
                break
        if not found:
            print(f"✗ '{ref_item}' was PRUNED!")
    
    # Show top 10 for key slots
    print(f"\n=== TOP 10 RANKINGS (Vibe primary, Chill secondary) ===")
    for slot in ["Face", "Back", "Pants"]:
        ranked = sorted(gear_pool[slot], key=lambda x: score_candidate_modern(x, P_COLOR, S_COLOR), reverse=True)
        print(f"\n{slot} slot:")
        for i, g in enumerate(ranked[:15]):  # Show top 15
            name = g.get("Name", "?")
            score = score_candidate_modern(g, P_COLOR, S_COLOR)
            marker = " <<<" if name in REFERENCE_ITEMS else ""
            in_top_10 = " [IN TOP 10]" if i < 10 else ""
            print(f"  {i+1:2}. {name:45} score={score:3}{in_top_10}{marker}")

if __name__ == "__main__":
    main()
