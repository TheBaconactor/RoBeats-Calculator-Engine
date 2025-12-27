from gear_optimizer.data.csv_parser import load_csv_db

gears = load_csv_db('Data/Gear/Gears.csv', 'gear')
minis = load_csv_db('Data/Gear/Minis.csv', 'mini')

gear_names = ['The Games: Hidden Shine', "Legendary Vibe Ringleader's Necktie", "Legendary Vibe Ringleader's Harmonica", "Legendary Marshall's Coat", "Legendary Vibe Ringleader's Band Kit", "Legendary Vibe Ringleader's Slacks"]
mini_names = ['Fusq', 'Trailblazing Trance Zara', 'Electroman']

stats = {k: 0 for k in ['Perfect Points', 'Combo Multiplier', 'Fever Multiplier', 'Fever Time', 'Fever Fill Rate', 'Beat', 'Vibe', 'Rush', 'Flow', 'Chill']}

print("=== GEAR ===")
for name in gear_names:
    g = gears.get(name, {})
    print(f"{name}: PP={g.get('Perfect Points',0)} CM={g.get('Combo Multiplier',0)} FM={g.get('Fever Multiplier',0)} FT={g.get('Fever Time',0)} FF={g.get('Fever Fill Rate',0)} Vibe={g.get('Vibe',0)}")
    for k in stats: stats[k] += g.get(k, 0)

print("\n=== MINIS ===")
for name in mini_names:
    m = minis.get(name, {})
    print(f"{name}: PP={m.get('Perfect Points',0)} CM={m.get('Combo Multiplier',0)} FM={m.get('Fever Multiplier',0)} FT={m.get('Fever Time',0)} FF={m.get('Fever Fill Rate',0)} Vibe={m.get('Vibe',0)}")
    for k in stats: stats[k] += m.get(k, 0)

print(f"\n=== TOTAL ===")
for k, v in stats.items():
    if v: print(f"  {k}: {v}")
