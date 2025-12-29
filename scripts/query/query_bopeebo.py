import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gear_optimizer.data.database import get_db_connection, get_evolution_db_path

db_path = get_evolution_db_path()
conn = get_db_connection(db_path)

# Search for Bopeebo
cursor = conn.execute(
    "SELECT name, best_score, best_fg_score FROM songs WHERE LOWER(name) LIKE ? ORDER BY name", ("%bopeebo%",)
)

results = cursor.fetchall()
print(f"Found {len(results)} song(s) matching 'bopeebo':\n")

for row in results:
    song_name = row["name"]
    print(f"=== {song_name} ===")
    print(f"Best Score: {row['best_score']:,}")
    print(f"Best FG Score: {row['best_fg_score']:,}\n")

    # Get top loadout with FG details
    loadout_cursor = conn.execute(
        """
        SELECT score, fg_score, gear_json, minis_json, details_json, force_details_json
        FROM loadouts
        WHERE song_name = ?
        ORDER BY fg_score DESC, score DESC
        LIMIT 1
    """,
        (song_name,),
    )

    loadout = loadout_cursor.fetchone()
    if loadout:
        gear = json.loads(loadout["gear_json"]) if loadout["gear_json"] else []
        minis = json.loads(loadout["minis_json"]) if loadout["minis_json"] else []
        details = json.loads(loadout["details_json"]) if loadout["details_json"] else {}
        force_details = json.loads(loadout["force_details_json"]) if loadout["force_details_json"] else {}

        print(f"Top FG Loadout:")
        print(f"  Score: {loadout['score']:,}")
        print(f"  FG Score: {loadout['fg_score']:,}")
        print(f"\n  Gear:")
        for i, g in enumerate(gear, 1):
            print(f"    {i}. {g}")
        print(f"\n  Minis:")
        for i, m in enumerate(minis, 1):
            print(f"    {i}. {m}")

        if force_details and "ForceGreats" in force_details:
            fg = force_details["ForceGreats"]
            print(f"\n  Force Greats Config:")
            if "config" in fg:
                print(f"    Section 1: {fg['config'].get('NonFever1', 0)}")
                print(f"    Section 2: {fg['config'].get('NonFever2', 0)}")
                print(f"    Section 3: {fg['config'].get('NonFever3', 0)}")
                print(f"    Section 4: {fg['config'].get('NonFever4', 0)}")

        if details and "GemCounts" in details:
            gems = details["GemCounts"]
            print(f"\n  Gem Upgrades:")
            for gem_type in ["Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Fill Rate", "Fever Time"]:
                if gem_type in gems:
                    print(f"    {gem_type}: {gems[gem_type]}")

            print(f"\n  Elemental Gems:")
            for elem in ["Chill", "Flow", "Rush", "Beat", "Vibe"]:
                if elem in gems:
                    print(f"    {elem}: {gems[elem]}")

            if "Element" in gems:
                print(f"    Overflow: {gems['Element']}")

conn.close()
