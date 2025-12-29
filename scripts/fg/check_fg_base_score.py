import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gear_optimizer.data.database import get_db_connection, get_evolution_db_path

db_path = get_evolution_db_path()
conn = get_db_connection(db_path)

song_name = "Ice Angel (Easy) by Yooh"

# Get the loadout with base score 16,148,872
cursor = conn.execute(
    """
    SELECT score, fg_score, force_details_json
    FROM loadouts
    WHERE song_name = ? AND score = 16148872
""",
    (song_name,),
)

loadout = cursor.fetchone()

print("=" * 80)
print("CHECKING LOADOUT WITH BASE SCORE 16,148,872")
print("=" * 80)

if loadout:
    print(f"\nStored Base Score: {loadout['score']:,}")
    print(f"Stored FG Score: {loadout['fg_score']:,}")

    if loadout["force_details_json"]:
        force_details = json.loads(loadout["force_details_json"])
        print(f"\nForce Details JSON:")
        print(json.dumps(force_details, indent=2))

        if "ForceGreats" in force_details:
            fg = force_details["ForceGreats"]
            if "base_score" in fg:
                print(f"\n🔍 FOUND IT!")
                print(f"  FG base_score (pre-penalty): {fg['base_score']:,}")
                print(f"  Stored score (post-penalty): {loadout['score']:,}")
                print(f"  Penalty applied: {fg['base_score'] - loadout['score']:,}")

                # Check if this matches the songs table
                cursor2 = conn.execute("SELECT best_score FROM songs WHERE name = ?", (song_name,))
                song_best = cursor2.fetchone()["best_score"]

                if fg["base_score"] == song_best:
                    print(f"\n✓ This explains the songs table entry!")
                    print(f"  songs.best_score ({song_best:,}) = force_details.base_score ({fg['base_score']:,})")
                    print(f"\n  The songs table is storing the PRE-PENALTY score, which is incorrect.")
                    print(f"  It should store the POST-PENALTY score: {loadout['score']:,}")
    else:
        print("\nNo force_details_json found")
else:
    print("Loadout not found")

conn.close()
