"""Check entry counts."""

import sqlite3

c = sqlite3.connect("evolution.db")
print("Total entries:", c.execute("SELECT COUNT(*) FROM team_buff_loadouts").fetchone()[0])
print(
    "Entries with #include signal:",
    c.execute("SELECT COUNT(*) FROM team_buff_loadouts WHERE song_name LIKE '%signal%'").fetchone()[0],
)

# Check for the specific ones still broken
bad_rowids = [
    16207,
    16213,
    16214,
    16216,
    16221,
    16222,
    16228,
    16229,
    16230,
    122389,
    155653,
    155670,
    155671,
    155672,
    155678,
    155679,
    155710,
    155712,
]
print(f"\nChecking {len(bad_rowids)} previously broken rowids...")
for rid in bad_rowids:
    row = c.execute("SELECT rowid, details_json FROM team_buff_loadouts WHERE rowid=?", (rid,)).fetchone()
    if row:
        import json

        d = json.loads(row[1])
        stats = d.get("Stats", {})
        has_values = bool(stats) and any(v for v in stats.values())
        print(f"  rowid {rid}: {'OK' if has_values else 'STILL EMPTY'}")
    else:
        print(f"  rowid {rid}: NOT FOUND")

c.close()
