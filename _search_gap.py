"""Check if any gear combo can hit the frontend's implied gear stats."""
import sys, json, csv
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np

# Load gear/minis
gears = list(csv.DictReader(open("Data/Gear/Gears.csv", encoding="utf-8-sig")))
minis = list(csv.DictReader(open("Data/Gear/Minis.csv", encoding="utf-8-sig")))

minis_by_name = {m.get("Mini Name", ""): m for m in minis if m.get("Mini Name")}

# Frontend mini team contribution
mini_names = ["Juggernaut", "Lappy", "Kurante Metal Dimensions"]
total_mini = {"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0, "Fever Time": 0, "Fever Fill Rate": 0,
              "Chill": 0, "Flow": 0, "Rush": 0, "Beat": 0, "Vibe": 0}
for mn in mini_names:
    m = minis_by_name.get(mn)
    if m:
        for k in total_mini:
            total_mini[k] += int(m.get(k, 0) or 0)
        print(f"{mn}: PP={m.get('Perfect Points',0)} CM={m.get('Combo Multiplier',0)} FM={m.get('Fever Multiplier',0)} FT={m.get('Fever Time',0)} FF={m.get('Fever Fill Rate',0)} Rush={m.get('Rush',0)} Vibe={m.get('Vibe',0)} Beat={m.get('Beat',0)}")
    else:
        print(f"{mn}: NOT IN CSV!")

print(f"\nTotal mini: PP={total_mini['Perfect Points']} CM={total_mini['Combo Multiplier']} FM={total_mini['Fever Multiplier']} FT={total_mini['Fever Time']} FF={total_mini['Fever Fill Rate']} Rush={total_mini['Rush']} Vibe={total_mini['Vibe']} Beat={total_mini['Beat']}")

# Frontend final stats & gems
# FM=13 gems, FF=18, FT=1, Rush++=58
# T5 Rush buff: +30 Rush
fe_final = {"PP": 386, "CM": 66, "FM": 74, "FT": 31, "FF": 61, "Rush": 733}
gem_stats = {"FM": 13, "FF": 18, "FT": 1, "Rush": 58}
buff = {"Rush": 30}

implied_gear = {}
for k in ["PP", "CM", "FM", "FT", "FF", "Rush"]:
    v = fe_final[k]
    if k == "Rush":
        v -= buff["Rush"]
    v -= gem_stats.get(k, 0)
    v -= total_mini.get({"PP": "Perfect Points", "CM": "Combo Multiplier", "FM": "Fever Multiplier",
                          "FT": "Fever Time", "FF": "Fever Fill Rate", "Rush": "Rush"}[k], 0)
    implied_gear[k] = v

print(f"\nImplied gear-only stats: {json.dumps(implied_gear, indent=2)}")

# Now search gear pool for ANY 6-slot combination that matches or exceeds these stats
slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
stat_keys = {"PP": "Perfect Points", "CM": "Combo Multiplier", "FM": "Fever Multiplier",
             "FT": "Fever Time", "FF": "Fever Fill Rate", "Rush": "Rush"}

gear_by_slot = {s: [] for s in slots}
for g in gears:
    slot = g.get("Type", "")
    if slot in slots:
        # Get elementals - gears have element columns too
        gear_by_slot[slot].append(g)

print(f"\nGear by slot: { {s: len(v) for s, v in gear_by_slot.items()} }")

# Check each slot for items matching or exceeding implied stats
# Gear items only contribute to one or two stats typically
for slot in slots:
    items = gear_by_slot.get(slot, [])
    best = None
    best_sum = -999
    for g in items:
        score = 0
        for skey, sname in stat_keys.items():
            val = int(g.get(sname, 0) or 0)
            if val >= implied_gear.get(skey, 0):
                score += 1
        if score > best_sum:
            best_sum = score
            best = g
    if best:
        vals = {skey: int(best.get(sname, 0) or 0) for skey, sname in stat_keys.items()}
        print(f"\n{slot} best match ({best_sum}/6 stats match): {best.get('Name', '?')} -> {vals}")

# Also: can we achieve PP=??? 
print(f"\nImplied gear PP: {implied_gear['PP']}")
print(f"Max PP from single gear item: {max(int(g.get('Perfect Points',0) or 0) for g in gears)}")
print(f"Total PP across all 6 slots (sum of max per slot): {sum(max(int(g.get('Perfect Points',0) or 0) for g in gear_by_slot.get(s,[]) if g) for s in slots)}")
