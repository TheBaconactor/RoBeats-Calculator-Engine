#!/usr/bin/env python
import json
import re
import sqlite3
import sys
from pathlib import Path

"""
Check for double-encoded minis_json corruption in a SQLite DB.

Corruption pattern:
  Correct: [["Electroman"],["Fusq"]]
  Corrupt : [["['Electroman']"],["['Fusq']"]]

Usage:
  python scripts/debug/_check_minis_corruption.py [path/to/evolution.db]

Defaults to ./evolution.db
"""

db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("evolution.db")
conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row

# Pattern: inner element is a stringified Python list like "['Name']" instead of just "Name"
# Correct: [["Electroman"],["Fusq"]]
# Corrupt: [["['Electroman']"],["['Fusq']"]]
CORRUPT_PATTERN = re.compile(r"\['")

tables = ["loadouts", "fg_loadouts", "team_buff_loadouts", "team_buff_fg_loadouts"]
print(f"DB: {db_path}")
for table in tables:
    try:
        rows = conn.execute(f"SELECT song_name, minis_json FROM {table}").fetchall()
    except sqlite3.Error:
        print(f"{table}: table does not exist")
        continue
    total = len(rows)
    corrupted = 0
    for row in rows:
        mj = row["minis_json"] or ""
        if CORRUPT_PATTERN.search(mj):
            corrupted += 1
            if corrupted <= 3:
                print(f"  Example ({table}): {row['song_name']}")
                print(f"    minis_json = {mj[:200]}")
    print(f"{table}: {corrupted}/{total} corrupted")

conn.close()
