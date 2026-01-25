"""Check T1-T10 entries for various songs to verify Stats are populated."""

import sqlite3
import json

conn = sqlite3.connect('evolution.db')
conn.row_factory = sqlite3.Row

print("=" * 90)
print("CHECKING T1-T10 ENTRIES FOR STATS POPULATION")
print("=" * 90)

# Check a few songs
test_songs = [
    ("stella", "%stella%"),
    ("pixel war", "%pixel war%"),
    ("freedom dive", "%freedom dive%"),
]

for song_label, pattern in test_songs:
    print(f"\n--- {song_label.upper()} (Top 10) ---")
    rows = conn.execute(
        "SELECT song_name, score, details_json FROM loadouts WHERE song_name LIKE ? ORDER BY score DESC LIMIT 10",
        (pattern,)
    ).fetchall()
    
    if not rows:
        print("  No entries found")
        continue
        
    for i, row in enumerate(rows):
        details = json.loads(row["details_json"]) if row["details_json"] else {}
        stats = details.get("Stats")
        
        if stats is None:
            stats_status = "MISSING (None)"
        elif len(stats) == 0:
            stats_status = "EMPTY {}"
        else:
            chill = stats.get("Chill", "?")
            vibe = stats.get("Vibe", "?")
            rush = stats.get("Rush", "?")
            stats_status = f"Chill={chill}, Vibe={vibe}, Rush={rush}"
        
        print(f"  T{i+1}: Score {row['score']:>12,} | {stats_status}")

# Summary check
print("\n" + "=" * 90)
print("SUMMARY: Checking all entries for Stats issues")
print("=" * 90)

total = conn.execute("SELECT COUNT(*) FROM loadouts").fetchone()[0]
missing = 0
empty = 0
valid = 0

rows = conn.execute("SELECT details_json FROM loadouts").fetchall()
for row in rows:
    details = json.loads(row["details_json"]) if row["details_json"] else {}
    stats = details.get("Stats")
    
    if stats is None:
        missing += 1
    elif len(stats) == 0:
        empty += 1
    else:
        valid += 1

print(f"Total entries: {total:,}")
print(f"Valid Stats:   {valid:,}")
print(f"Missing Stats: {missing:,}")
print(f"Empty Stats:   {empty:,}")

if missing == 0 and empty == 0:
    print("\n[OK] All entries have valid Stats!")
else:
    print(f"\n[WARNING] {missing + empty:,} entries have Stats issues!")

conn.close()
