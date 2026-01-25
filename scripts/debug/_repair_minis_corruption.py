#!/usr/bin/env python
"""Repair double-encoded minis_json corruption in team_buff tables."""

from __future__ import annotations

import ast
import json
import re
import sqlite3
import sys
from pathlib import Path

"""
Repair minis_json corruption in a SQLite DB.

Corruption pattern:
  Correct: [["Electroman"],["Fusq"]]
  Corrupt : [["['Electroman']"],["['Fusq']"]]

Usage:
  python scripts/debug/_repair_minis_corruption.py [path/to/evolution.db]

Defaults to ./evolution.db
"""

db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("evolution.db")
conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row

CORRUPT_PATTERN = re.compile(r"\['")


def repair_minis_json(mj_str: str) -> str | None:
    """Attempt to parse and re-encode corrupted minis_json."""
    if not mj_str or not CORRUPT_PATTERN.search(mj_str):
        return None  # Not corrupted

    try:
        groups = json.loads(mj_str)
    except Exception:
        return None

    if not isinstance(groups, list):
        return None

    # Iterate through groups and detect double-encoded strings.
    repaired = []
    changed = False
    for group in groups:
        if not isinstance(group, list):
            repaired.append(group if isinstance(group, list) else [group])
            continue

        new_group = []
        for item in group:
            if isinstance(item, str):
                s = item.strip()
            else:
                s = ""

            # Likely corrupted: stringified Python list, e.g.
            # - "['Name']"
            # - "['A', 'B']"
            # - "['Fusq', \"Santa's Helper Marsha\"]"
            if isinstance(item, str) and s.startswith("[") and s.endswith("]"):
                try:
                    parsed = ast.literal_eval(s)
                    if isinstance(parsed, (list, tuple)):
                        new_group.extend(str(x) for x in parsed if x)
                        changed = True
                    else:
                        new_group.append(str(item))
                except Exception:
                    new_group.append(str(item))
            else:
                new_group.append(str(item) if item else "")
        repaired.append(new_group)

    if not changed:
        return None

    return json.dumps(repaired, separators=(",", ":"))


tables = ["team_buff_loadouts", "team_buff_fg_loadouts"]
print(f"DB: {db_path}")
for table in tables:
    try:
        rows = conn.execute(f"SELECT rowid, minis_json FROM {table}").fetchall()
    except sqlite3.Error as e:
        print(f"{table}: table does not exist or error: {e}")
        continue

    repairs = []
    for row in rows:
        mj = row["minis_json"]
        fixed = repair_minis_json(mj)
        if fixed:
            repairs.append((fixed, row["rowid"]))

    if repairs:
        print(f"{table}: repairing {len(repairs)}/{len(rows)} rows...")
        conn.executemany(f"UPDATE {table} SET minis_json = ? WHERE rowid = ?", repairs)
        conn.commit()
        print(f"{table}: repaired {len(repairs)} rows")
    else:
        print(f"{table}: no corrupted rows found")

conn.close()
print("Done")
