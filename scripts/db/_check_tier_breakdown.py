"""Check if a song has all tier breakdowns populated."""

import sqlite3

conn = sqlite3.connect("evolution.db")
c = conn.cursor()

print("=== Checking tier breakdown for a sample song ===\n")

# Find a song with tier data
rows = c.execute("SELECT song_name, team_buff, score FROM team_buff_loadouts ORDER BY song_name LIMIT 1").fetchall()
if not rows:
    print("No tier data found in team_buff_loadouts")
    conn.close()
    exit()

song_name = rows[0][0]
print(f"Sample song: {song_name}\n")

# Check base loadout tiers
print("Base loadout tiers (team_buff_loadouts):")
tiers = c.execute(
    "SELECT team_buff, score, fg_score FROM team_buff_loadouts WHERE song_name=? ORDER BY team_buff", (song_name,)
).fetchall()
for tier, score, fg_score in tiers:
    print(f"  {tier:4s}: score={score:,}, fg_score={fg_score:,}")

# Check FG tiers
print("\nForce Greats tiers (team_buff_fg_loadouts):")
fg_tiers = c.execute(
    "SELECT team_buff, fg_score FROM team_buff_fg_loadouts WHERE song_name=? ORDER BY team_buff", (song_name,)
).fetchall()
if fg_tiers:
    for tier, fg_score in fg_tiers:
        print(f"  {tier:4s}: fg_score={fg_score:,}")
else:
    print("  (no FG tier data for this song)")

# Summary
print(f"\n=== Summary ===")
print(f"Base tiers present: {len(tiers)} / 5 expected")
print(f"FG tiers present: {len(fg_tiers)} / 5 expected")

if len(tiers) == 5 and len(fg_tiers) == 5:
    print("✓ Full tier breakdown is working!")
else:
    print("✗ Tier breakdown is incomplete")

conn.close()
