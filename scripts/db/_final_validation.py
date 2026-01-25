"""
Quick DB validation for frontend handoff.

For a deeper audit across frontend views (JSON parseability, Stats nonzero, minis corruption),
use the maintained tool:
  python tools/db/audit_frontend_db.py --db <path>
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.data.database import get_evolution_db_path


EXPECTED_TEAM_BUFFS = {"NONE", "T1", "T5", "T10", "T15"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Quick DB validation for frontend handoff.")
    parser.add_argument("--db", type=str, default="", help="DB path (defaults to EVOLUTION_DB_PATH / ./evolution.db).")
    args = parser.parse_args()

    db_path = Path(args.db).expanduser() if args.db else Path(get_evolution_db_path())
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    print("=" * 60)
    print("DB VALIDATION (QUICK)")
    print("=" * 60)

    version = c.execute("PRAGMA user_version").fetchone()[0]
    print(f"\n1) Schema Version: {version}")

    view_exists = c.execute("SELECT 1 FROM sqlite_master WHERE type='view' AND name='fg_loadouts_unified'").fetchone()
    print(f"\n2) Unified View fg_loadouts_unified: {'OK' if view_exists else 'MISSING'}")

    legacy_count = c.execute("SELECT COUNT(*) FROM fg_loadouts").fetchone()[0]
    tiered_count = c.execute("SELECT COUNT(*) FROM team_buff_fg_loadouts").fetchone()[0]
    unified_count = c.execute("SELECT COUNT(*) FROM fg_loadouts_unified").fetchone()[0]
    duplicates_removed = (legacy_count + tiered_count) - unified_count

    print("\n3) Deduplication:")
    print(f"   legacy fg_loadouts: {legacy_count:,}")
    print(f"   tiered team_buff_fg_loadouts: {tiered_count:,}")
    print(f"   unified fg_loadouts_unified: {unified_count:,}")
    print(f"   duplicates_removed: {duplicates_removed:,} ({'OK' if duplicates_removed >= 0 else 'BAD'})")

    print("\n4) Tier distribution (unified):")
    tier_counts = c.execute(
        """
        SELECT UPPER(team_buff) AS team_buff, COUNT(*)
        FROM fg_loadouts_unified
        GROUP BY UPPER(team_buff)
        ORDER BY UPPER(team_buff)
        """
    ).fetchall()
    for tier, count in tier_counts:
        flag = "OK" if tier in EXPECTED_TEAM_BUFFS else "UNEXPECTED"
        print(f"   {tier:4s}: {count:,} ({flag})")

    conn.close()

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
