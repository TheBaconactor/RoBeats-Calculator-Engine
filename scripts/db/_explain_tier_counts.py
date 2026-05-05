"""Explain how many rows exist in each FG tier bucket."""

import sqlite3

conn = sqlite3.connect("evolution.db")
c = conn.cursor()

print("=" * 60)
print("FG TIER COUNT EXPLANATION")
print("=" * 60)

print("\n=== SOURCE TABLES ===\n")
tb_fg = c.execute("SELECT COUNT(*) FROM team_buff_fg_loadouts").fetchone()[0]
print(f"team_buff_fg_loadouts (explicit tiers): {tb_fg:,} rows")

print(f"\n=== BREAKDOWN BY TIER (team_buff_fg_loadouts only) ===\n")
tiers = c.execute(
    "SELECT team_buff, COUNT(*) FROM team_buff_fg_loadouts GROUP BY team_buff ORDER BY team_buff"
).fetchall()
for tier, cnt in tiers:
    print(f"{tier:4s}: {cnt:,} rows")

print(f"\n=== SONG COVERAGE ===\n")
total_songs = c.execute("SELECT COUNT(*) FROM songs").fetchone()[0]
tiered_songs = c.execute("SELECT COUNT(DISTINCT song_name) FROM team_buff_fg_loadouts").fetchone()[0]

print(f"Total songs in DB: {total_songs:,}")
print(f"Songs with explicit tier FG: {tiered_songs:,}")

print(f"\n=== THE SITUATION ===\n")
print(f"• team_buff_fg_loadouts has {tb_fg:,} rows spread across 5 tiers")
print(f"  - This means only ~{tiered_songs:,} songs were re-run with explicit tiers")
print(f"\n• To get 51k entries for NONE/T1/T10/T20/T50/T51:")
print(f"  - You would need to re-run the optimizer with each tier")
print(f"  - Each song would need 6 more runs (NONE, T1, T10, T20, T50, T51)")
print(f"  - OR implement auto-derivation (recompute existing loadouts under other tiers)")

conn.close()
