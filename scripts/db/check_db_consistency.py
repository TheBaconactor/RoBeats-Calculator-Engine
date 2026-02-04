import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gear_optimizer.data.database import get_db_connection, get_evolution_db_path

db_path = get_evolution_db_path()
conn = get_db_connection(db_path)

song_name = "Ice Angel (Easy) by Yooh"

# Get best scores from songs table
cursor = conn.execute("SELECT best_score, best_fg_score FROM songs WHERE name = ?", (song_name,))
song_record = cursor.fetchone()

print("=" * 80)
print("DATABASE CONSISTENCY CHECK: Ice Angel (Easy)")
print("=" * 80)

print(f"\nSONGS TABLE:")
print(f"  Best Score: {song_record['best_score']:,}")
print(f"  Best FG Score: {song_record['best_fg_score']:,}")

# Get ALL loadouts
cursor = conn.execute(
    """
    SELECT score, fg_score, gear_json, minis_json, details_json
    FROM team_buff_loadouts
    WHERE song_name = ?
    ORDER BY score DESC
""",
    (song_name,),
)

loadouts = cursor.fetchall()

print(f"\nLOADOUTS TABLE: {len(loadouts)} entries")
print("-" * 80)

max_base_score = 0
max_fg_score = 0

for i, loadout in enumerate(loadouts, 1):
    gear = json.loads(loadout["gear_json"]) if loadout["gear_json"] else []
    details = json.loads(loadout["details_json"]) if loadout["details_json"] else {}

    max_base_score = max(max_base_score, loadout["score"])
    max_fg_score = max(max_fg_score, loadout["fg_score"])

    ft = details.get("FT", "?")
    ff = details.get("FF", "?")

    print(f"#{i}: Base={loadout['score']:,}, FG={loadout['fg_score']:,}, FT={ft}, FF={ff}")
    print(f"    Gear: {', '.join(gear[:3])}...")

print("\n" + "=" * 80)
print("INCONSISTENCY ANALYSIS")
print("=" * 80)

print(f"\nExpected (from songs table):")
print(f"  Best Score: {song_record['best_score']:,}")
print(f"  Best FG Score: {song_record['best_fg_score']:,}")

print(f"\nActual (from team_buff_loadouts table):")
print(f"  Highest Base Score: {max_base_score:,}")
print(f"  Highest FG Score: {max_fg_score:,}")

print(f"\nDISCREPANCY:")
if max_base_score != song_record["best_score"]:
    diff = song_record["best_score"] - max_base_score
    print(f"  ❌ Base Score: {diff:+,} points MISSING!")
    print(f"     The songs table claims {song_record['best_score']:,}, but no loadout has this score.")
    print(f"     This suggests a loadout was DELETED or OVERWRITTEN without updating songs table.")
else:
    print(f"  ✓ Base Score: Consistent")

if max_fg_score != song_record["best_fg_score"]:
    diff = song_record["best_fg_score"] - max_fg_score
    print(f"  ❌ FG Score: {diff:+,} points MISSING!")
    print(f"     The songs table claims {song_record['best_fg_score']:,}, but no loadout has this score.")
else:
    print(f"  ✓ FG Score: Consistent")

conn.close()
