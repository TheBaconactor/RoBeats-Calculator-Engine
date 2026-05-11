import sqlite3, csv, json

db = sqlite3.connect("evolution.db")

# Check mini_name_encoding table
c = db.execute("SELECT * FROM mini_name_encoding")
mini_enc = {row[1]: row[0] for row in c.fetchall()}
print(f"Mini encodings: {len(mini_enc)}")
for target in ["Juggernaut", "Lappy", "Kurante"]:
    found = [k for k in mini_enc if target.lower() in str(k).lower()]
    print(f"  '{target}': {found}")

# Check gear_name_encoding
c = db.execute("SELECT * FROM gear_name_encoding")
gear_enc = {row[1]: row[0] for row in c.fetchall()}
print(f"\nGear encodings: {len(gear_enc)}")

# Check songs table for garlagan with actual loadout data
c = db.execute("SELECT * FROM songs WHERE name LIKE '%00%Hard%' OR name LIKE '%00 %garlagan%'")
cols = [d[0] for d in c.description]
for row in c.fetchall():
    data = dict(zip(cols, row))
    for k, v in data.items():
        print(f"  {k}: {v}")
    print()

# Also check pending_fg_jobs
c = db.execute("SELECT name FROM pending_fg_jobs WHERE name LIKE '%garlagan%'")
for r in c.fetchall():
    print(f"Pending FG: {r[0]}")
