import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gear_optimizer.data.database import get_db_connection, get_evolution_db_path

db_path = get_evolution_db_path()
conn = get_db_connection(db_path)

# Find Feeling Alright (Hard)
cursor = conn.execute(
    "SELECT name, best_score, best_fg_score FROM songs WHERE LOWER(name) LIKE ? ORDER BY name",
    ("%feeling alright%hard%",),
)

results = cursor.fetchall()
if not results:
    print("Song not found. Searching more broadly...")
    cursor = conn.execute(
        "SELECT name, best_score, best_fg_score FROM songs WHERE LOWER(name) LIKE ? ORDER BY name",
        ("%feeling alright%",),
    )
    results = cursor.fetchall()

if not results:
    print("No songs found matching 'feeling alright'")
    conn.close()
    exit()

song_name = results[0]["name"]
print(f"Found: {song_name}")
print(f"Best Score in DB: {results[0]['best_score']:,}")
print(f"Best FG Score in DB: {results[0]['best_fg_score']:,}")
print()

# Get top base score
cursor = conn.execute(
    """
    SELECT score, fg_score, gear_json, minis_json, details_json, force_details_json
    FROM loadouts
    WHERE song_name = ?
    ORDER BY score DESC
    LIMIT 1
""",
    (song_name,),
)

top_base = cursor.fetchone()

# Get top FG score
cursor = conn.execute(
    """
    SELECT score, fg_score, gear_json, minis_json, details_json, force_details_json
    FROM loadouts
    WHERE song_name = ?
    ORDER BY fg_score DESC
    LIMIT 1
""",
    (song_name,),
)

top_fg = cursor.fetchone()

print("=" * 80)
print("TOP BASE SCORE LOADOUT")
print("=" * 80)
if top_base:
    gear = json.loads(top_base["gear_json"]) if top_base["gear_json"] else []
    minis = json.loads(top_base["minis_json"]) if top_base["minis_json"] else []
    details = json.loads(top_base["details_json"]) if top_base["details_json"] else {}

    print(f"Base Score: {top_base['score']:,}")
    print(f"FG Score: {top_base['fg_score']:,}")
    print(f"\nGear: {', '.join(gear)}")
    print(f"Minis: {', '.join(minis)}")

    if details and "GemCounts" in details:
        gems = details["GemCounts"]
        print(
            f"\nGems: PP={gems.get('Perfect Points', 0)}, CM={gems.get('Combo Multiplier', 0)}, "
            f"FM={gems.get('Fever Multiplier', 0)}, Overflow={gems.get('Element', 0)}"
        )

print("\n" + "=" * 80)
print("TOP FG SCORE LOADOUT")
print("=" * 80)
if top_fg:
    gear = json.loads(top_fg["gear_json"]) if top_fg["gear_json"] else []
    minis = json.loads(top_fg["minis_json"]) if top_fg["minis_json"] else []
    details = json.loads(top_fg["details_json"]) if top_fg["details_json"] else {}
    force_details = json.loads(top_fg["force_details_json"]) if top_fg["force_details_json"] else {}

    print(f"Base Score: {top_fg['score']:,}")
    print(f"FG Score: {top_fg['fg_score']:,}")
    print(f"\nGear: {', '.join(gear)}")
    print(f"Minis: {', '.join(minis)}")

    if details and "GemCounts" in details:
        gems = details["GemCounts"]
        print(
            f"\nGems: PP={gems.get('Perfect Points', 0)}, CM={gems.get('Combo Multiplier', 0)}, "
            f"FM={gems.get('Fever Multiplier', 0)}, Overflow={gems.get('Element', 0)}"
        )

    if force_details and "ForceGreats" in force_details:
        fg = force_details["ForceGreats"]
        if "config" in fg:
            print(
                f"\nFG Config: [{fg['config'].get('NonFever1', 0)}, "
                f"{fg['config'].get('NonFever2', 0)}, "
                f"{fg['config'].get('NonFever3', 0)}, "
                f"{fg['config'].get('NonFever4', 0)}]"
            )

print("\n" + "=" * 80)
print("COMPARISON")
print("=" * 80)
if top_base and top_fg:
    same_loadout = top_base["gear_json"] == top_fg["gear_json"] and top_base["minis_json"] == top_fg["minis_json"]

    if same_loadout:
        print("✓ Same gear/mini loadout for both")
    else:
        print("❌ Different loadouts")

    score_diff = top_fg["fg_score"] - top_base["score"]
    print(f"\nFG Improvement: {score_diff:+,} points")
    print(f"  ({top_base['score']:,} → {top_fg['fg_score']:,})")

conn.close()
