#!/usr/bin/env python
"""
Quick sanity check for FG persistence fields.

This was previously a module under `tests/` but it is not an automated pytest test
(it performs DB I/O + prints at import time), so it lives here as a script.

Usage:
  python scripts/db/check_fg_persistence.py [path/to/evolution.db]

Defaults:
  - argv[1] if provided
  - else EVOLUTION_DB_PATH if set
  - else ./evolution.db
"""

from __future__ import annotations

import os
import sqlite3
import sys


def main() -> int:
    db_path = ""
    if len(sys.argv) > 1:
        db_path = str(sys.argv[1] or "").strip()
    if not db_path:
        db_path = str(os.environ.get("EVOLUTION_DB_PATH", "") or "").strip()
    if not db_path:
        db_path = "evolution.db"

    print("=" * 60)
    print("FG Config Persistence Check")
    print("=" * 60)
    print(f"DB: {db_path}")

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN force_details_json IS NOT NULL THEN 1 ELSE 0 END) as with_config,
                   SUM(CASE WHEN fg_score > score THEN 1 ELSE 0 END) as improving
            FROM team_buff_loadouts
            WHERE fg_score > 0
            """
        )
        total_fg, with_config, improving = cursor.fetchone()

        print("\nSummary:")
        print(f"  Total rows with fg_score > 0: {total_fg}")
        print(f"  With force_details_json: {with_config}")
        print(f"  FG improving (fg_score > score): {improving}")
        ratio = (with_config / total_fg * 100.0) if total_fg else 0.0
        print(f"  Config ratio: {with_config}/{total_fg} = {ratio:.1f}%")

        cursor.execute(
            """
            SELECT song_name, fg_score, score,
                   CASE WHEN force_details_json IS NULL THEN 'NULL' ELSE 'present' END as config_status,
                   length(force_details_json) as config_len
            FROM team_buff_loadouts
            WHERE fg_score > 0
            ORDER BY timestamp DESC
            LIMIT 5
            """
        )
        print("\nRecent rows:")
        for song_name, fg_score, score, config_status, config_len in cursor.fetchall():
            song_disp = str(song_name or "")[:60]
            print(f"  {song_disp}: fg={fg_score}, base={score}, config={config_status} (len={config_len})")
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
