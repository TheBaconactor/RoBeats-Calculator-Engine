import sqlite3
import json

conn = sqlite3.connect("evolution.db")
c = conn.cursor()

# Get top stella loadout
rows = c.execute("""
    SELECT song_name, score, fg_score, details_json 
    FROM loadouts 
    WHERE song_name LIKE "%stella%" 
    ORDER BY score DESC 
    LIMIT 1
""").fetchall()

if rows:
    song, score, fg_score, details_json = rows[0]
    details = json.loads(details_json)
    stats = details.get("Stats", {})

    print(f"=== FRESH OPTIMIZER RUN (Top Stella Loadout) ===")
    print(f"Song: {song}")
    print(f"Score: {score:,}")
    print(f"FG Score: {fg_score:,}")
    print(f"\n--- Stats ---")
    print(f"Chill: {stats.get('Chill', 0)}")
    print(f"Vibe: {stats.get('Vibe', 0)}")
    print(f"Beat: {stats.get('Beat', 0)}")
    print(f"Flow: {stats.get('Flow', 0)}")
    print(f"Rush: {stats.get('Rush', 0)}")
    print(f"Perfect Points: {stats.get('Perfect Points', 0)}")
    print(f"Combo Multiplier: {stats.get('Combo Multiplier', 0)}")
    print(f"Fever Multiplier: {stats.get('Fever Multiplier', 0)}")
    print(f"Fever Time: {stats.get('Fever Time', 0)}")
    print(f"Fever Fill Rate: {stats.get('Fever Fill Rate', 0)}")

    print(f"\n=== EXPECTED FROM BACKFILL ===")
    print(f"Chill: 740")
    print(f"Vibe: 21")
    print(f"Beat: 59")
    print(f"Flow: 3")
    print(f"Rush: 54")

    print(f"\n=== COMPARISON ===")
    expected = {"Chill": 740, "Vibe": 21, "Beat": 59, "Flow": 3, "Rush": 54}
    match = True
    for stat_name, expected_val in expected.items():
        actual_val = stats.get(stat_name, 0)
        status = "✅" if actual_val == expected_val else "❌"
        print(f"{stat_name}: {actual_val} vs {expected_val} {status}")
        if actual_val != expected_val:
            match = False

    if match:
        print(f"\n🎉 ALL STATS MATCH! Fresh optimizer run produces identical Stats to backfill.")
    else:
        print(f"\n⚠️ MISMATCH DETECTED! Stats differ between optimizer and backfill.")
else:
    print("No stella loadout found in database")

conn.close()
