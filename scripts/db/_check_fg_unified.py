import sqlite3

conn = sqlite3.connect("evolution.db")
c = conn.cursor()

# Get a sample song
rows = c.execute("SELECT DISTINCT song_name FROM team_buff_loadouts LIMIT 1").fetchall()
if not rows:
    print("No songs found in team_buff_loadouts")
    exit()

song = rows[0][0]
print(f"Checking FG tier breakdown for: {song}\n")

# Check team_buff_fg_loadouts
print("=== team_buff_fg_loadouts (explicit tier FG) ===")
tiers = c.execute(
    """
    SELECT DISTINCT team_buff
    FROM team_buff_fg_loadouts 
    WHERE song_name = ?
    ORDER BY team_buff
""",
    (song,),
).fetchall()
print(f"Tiers present: {', '.join(t[0] for t in tiers)}")
print(f"Count: {len(tiers)}/5 expected\n")

# Check fg_loadouts_unified view
print("=== fg_loadouts_unified (what frontend sees) ===")
unified_tiers = c.execute(
    """
    SELECT DISTINCT team_buff, source_table
    FROM fg_loadouts_unified 
    WHERE song_name = ?
    ORDER BY team_buff
""",
    (song,),
).fetchall()
for tier, source in unified_tiers:
    print(f"  {tier:4s} (from {source})")
print(f"\nTotal unique tiers in unified view: {len(unified_tiers)}/5 expected")

conn.close()
