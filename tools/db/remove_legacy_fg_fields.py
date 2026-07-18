"""Remove retired Force Greats compatibility fields from an evolution database."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.helpers.song_helpers.fg_payload import strip_retired_fg_fields


TABLE_COLUMNS = {
    "team_buff_loadouts": ("details_json", "force_details_json"),
    "team_buff_fg_loadouts": ("details_json", "force_details_json"),
}
def clean_database(db_path: Path, *, dry_run: bool = False) -> tuple[int, int]:
    conn = sqlite3.connect(str(db_path))
    changed_rows = 0
    removed_fields = 0
    try:
        if not dry_run:
            conn.execute("BEGIN IMMEDIATE")
        for table, columns in TABLE_COLUMNS.items():
            if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is None:
                continue
            available = {str(row[1]) for row in conn.execute(f'PRAGMA table_info("{table}")')}
            for column in columns:
                if column not in available:
                    continue
                rows = conn.execute(
                    f'SELECT rowid, "{column}" FROM "{table}" WHERE "{column}" IS NOT NULL'
                ).fetchall()
                updates: list[tuple[str, int]] = []
                for rowid, raw in rows:
                    payload = json.loads(raw)
                    cleaned, count = strip_retired_fg_fields(payload)
                    if count <= 0:
                        continue
                    removed_fields += count
                    changed_rows += 1
                    updates.append((json.dumps(cleaned, separators=(",", ":")), int(rowid)))
                if updates and not dry_run:
                    conn.executemany(
                        f'UPDATE "{table}" SET "{column}"=? WHERE rowid=?',
                        updates,
                    )
        if not dry_run:
            conn.commit()
    except Exception:
        if not dry_run:
            conn.rollback()
        raise
    finally:
        conn.close()
    return changed_rows, removed_fields


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.db.is_file():
        raise SystemExit(f"Database not found: {args.db}")
    changed_rows, removed_fields = clean_database(args.db, dry_run=bool(args.dry_run))
    mode = "would remove" if args.dry_run else "removed"
    print(f"{mode} {removed_fields:,} legacy fields across {changed_rows:,} JSON rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
