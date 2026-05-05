"""
Repair songs.best_fg_score to match the canonical T5 leaderboard.

Background
----------
The optimizer's canonical persistence tier is T5. Historical DB state may contain "polluted"
values in `songs.best_fg_score` (commonly matching derived tiers like T1) due to legacy writes
from tier post-processing.

This tool recomputes the per-song T5 FG max and writes it back into the `songs` table:
- Preferred source: `team_buff_fg_loadouts` (T5) -> MAX(fg_score)
- Fallback: `team_buff_loadouts` (T5) -> MAX(fg_score)

Use --dry-run to audit without writing changes.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.core.utils import safe_int as _safe_int
from gear_optimizer.data.migrations import _table_exists

from gear_optimizer.data.database import get_evolution_db_path

@dataclass
class RepairCounts:
    scanned: int = 0
    updated: int = 0
    skipped_missing_t5: int = 0


def repair_songs_best_fg_score_t5(*, db_path: Path, song: str | None, dry_run: bool) -> RepairCounts:
    # Ensure any helpers that rely on EVOLUTION_DB_PATH use this DB.
    os.environ["EVOLUTION_DB_PATH"] = str(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        if not _table_exists(conn, "songs"):
            raise RuntimeError("Missing required table: songs")
        if not _table_exists(conn, "team_buff_loadouts"):
            raise RuntimeError("Missing required table: team_buff_loadouts")

        has_fg_table = _table_exists(conn, "team_buff_fg_loadouts")

        base_rows = conn.execute(
            """
            SELECT
                song_name,
                MAX(COALESCE(fg_score, 0)) AS max_fg
            FROM team_buff_loadouts
            WHERE UPPER(COALESCE(team_buff, 'UNKNOWN')) = 'T5'
            GROUP BY song_name
            """
        ).fetchall()
        t5_base_fg = {str(r["song_name"]): _safe_int(r["max_fg"]) for r in base_rows if r["song_name"]}

        t5_fg_table_fg: dict[str, int] = {}
        if has_fg_table:
            fg_rows = conn.execute(
                """
                SELECT
                    song_name,
                    MAX(COALESCE(fg_score, 0)) AS max_fg
                FROM team_buff_fg_loadouts
                WHERE UPPER(COALESCE(team_buff, 'UNKNOWN')) = 'T5'
                GROUP BY song_name
                """
            ).fetchall()
            t5_fg_table_fg = {str(r["song_name"]): _safe_int(r["max_fg"]) for r in fg_rows if r["song_name"]}

        counts = RepairCounts()

        if song:
            songs_rows = conn.execute(
                "SELECT name, best_fg_score FROM songs WHERE name = ?",
                (str(song),),
            ).fetchall()
        else:
            songs_rows = conn.execute("SELECT name, best_fg_score FROM songs").fetchall()

        for r in songs_rows:
            counts.scanned += 1
            name = str(r["name"])
            current = _safe_int(r["best_fg_score"])

            desired = t5_fg_table_fg.get(name)
            if desired is None:
                desired = t5_base_fg.get(name)
            if desired is None:
                counts.skipped_missing_t5 += 1
                continue

            if int(current) == int(desired):
                continue

            counts.updated += 1
            if not dry_run:
                conn.execute(
                    "UPDATE songs SET best_fg_score = ? WHERE name = ?",
                    (int(desired), name),
                )

        if not dry_run:
            conn.commit()

        return counts
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair songs.best_fg_score to match the canonical T5 leaderboard.")
    parser.add_argument("--db", type=str, default="", help="DB path (defaults to EVOLUTION_DB_PATH / ./evolution.db).")
    parser.add_argument("--song", type=str, default="", help="Optional exact song name key to repair.")
    parser.add_argument("--dry-run", action="store_true", help="Scan and report only; do not write changes.")
    args = parser.parse_args()

    db_path = Path(args.db).expanduser() if args.db else Path(get_evolution_db_path())
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    song = str(args.song).strip() or None
    counts = repair_songs_best_fg_score_t5(db_path=db_path, song=song, dry_run=bool(args.dry_run))

    title = "SONGS.BEST_FG_SCORE REPAIR (T5)" + (" (DRY RUN)" if args.dry_run else "")
    print("\n" + "=" * len(title))
    print(title)
    print("=" * len(title))
    print(f"DB: {db_path}")
    if song:
        print(f"Song: {song}")
    print(f"scanned: {counts.scanned:,}")
    print(f"updated: {counts.updated:,}")
    print(f"skipped_missing_t5: {counts.skipped_missing_t5:,}")


if __name__ == "__main__":
    main()
