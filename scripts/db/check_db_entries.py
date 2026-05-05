"""Inspect evolution DB entries with focused subcommands."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path("evolution.db")
DEFAULT_BAD_ROWIDS = [
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


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _cmd_counts(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    total = conn.execute("SELECT COUNT(*) FROM team_buff_loadouts").fetchone()[0]
    signal_count = conn.execute(
        "SELECT COUNT(*) FROM team_buff_loadouts WHERE song_name LIKE '%signal%'"
    ).fetchone()[0]
    print("Total entries:", total)
    print("Entries with #include signal:", signal_count)

    bad_rowids = list(DEFAULT_BAD_ROWIDS if args.rowid is None else args.rowid)
    print(f"\nChecking {len(bad_rowids)} previously broken rowids...")
    for rid in bad_rowids:
        row = conn.execute(
            "SELECT rowid, details_json FROM team_buff_loadouts WHERE rowid=?",
            (rid,),
        ).fetchone()
        if row:
            details = json.loads(row["details_json"])
            stats = details.get("Stats", {})
            has_values = bool(stats) and any(v for v in stats.values())
            print(f"  rowid {rid}: {'OK' if has_values else 'STILL EMPTY'}")
        else:
            print(f"  rowid {rid}: NOT FOUND")


def _cmd_recent(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    rows = conn.execute(
        """
        SELECT song_name, score, details_json, timestamp
        FROM team_buff_loadouts
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (int(args.limit),),
    ).fetchall()

    print(f"Checking {len(rows)} most recent entries (sorted by timestamp):\n")

    success = 0
    fail = 0
    for row in rows:
        details_raw = row["details_json"]
        song = str(row["song_name"] or "")[:50]

        if not details_raw:
            print(f"❌ {song}: NULL details")
            fail += 1
            continue

        details = json.loads(details_raw)
        stats = details.get("Stats", {})
        if not stats:
            print(f"❌ {song}: Empty Stats")
            fail += 1
            continue

        chill = stats.get("Chill", "N/A")
        print(f"✅ {song}: Chill={chill}")
        success += 1

    print(f"\nResults: {success}/{success + fail} have valid Stats")


def _cmd_ai_bomb(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    rows = conn.execute(
        """
        SELECT details_json
        FROM team_buff_loadouts
        WHERE song_name LIKE ?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (f"%{args.song_like}%", int(args.limit)),
    ).fetchall()
    for i, row in enumerate(rows):
        details = json.loads(row["details_json"]) if row["details_json"] else {}
        stats = details.get("Stats", {})
        print(f"Entry {i + 1}: Stats empty={not stats}, has_Chill={'Chill' in stats}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="Evolution DB path")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_counts = sub.add_parser("counts", help="Show aggregate counts and broken rowid checks")
    p_counts.add_argument("--rowid", type=int, nargs="*", help="Optional rowids to inspect")
    p_counts.set_defaults(func=_cmd_counts)

    p_recent = sub.add_parser("recent", help="Inspect recent loadout entries")
    p_recent.add_argument("--limit", type=int, default=10, help="Number of rows to inspect")
    p_recent.set_defaults(func=_cmd_recent)

    p_ai = sub.add_parser("ai-bomb", help="Inspect AI Bomb entries")
    p_ai.add_argument("--song-like", default="AI Bomb", help="Song name substring to filter on")
    p_ai.add_argument("--limit", type=int, default=5, help="Number of rows to inspect")
    p_ai.set_defaults(func=_cmd_ai_bomb)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    with _connect(args.db) as conn:
        args.func(conn, args)


if __name__ == "__main__":
    main()
