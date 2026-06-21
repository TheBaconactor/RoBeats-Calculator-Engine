#!/usr/bin/env python3
"""Count current-main FG winners that use great95 from an isolated fresh DB.

The DB must come from a fresh current-main solve, not a stale historical snapshot.
For each song, this script picks the top persisted FG row and reports whether its
winner trace contains an early-Great boundary tail (`early_great_start/end`).
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path


def infer_difficulty(song_name: str) -> str:
    text = str(song_name or "")
    for diff in ("Easy", "Normal", "Hard"):
        if f"({diff})" in text:
            return diff
    return "Unknown"


def count_early_tail_notes(trace: list[dict[str, object]]) -> int:
    total = 0
    for sec in trace:
        start = int(sec.get("early_great_start", -1) or -1)
        end = int(sec.get("early_great_end", -1) or -1)
        if start >= 0 and end > start:
            total += end - start
    return int(total)


def main() -> int:
    ap = argparse.ArgumentParser(description="Count great95 usage from a fresh FG solve DB.")
    ap.add_argument("--db", required=True, help="Path to isolated fresh DB")
    args = ap.parse_args()

    db_path = Path(args.db).expanduser().resolve()
    if not db_path.exists():
        raise SystemExit(f"[count_fg_great95_usage] DB not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT f.song_name, f.fg_score, f.force_details_json
            FROM team_buff_fg_loadouts AS f
            JOIN (
                SELECT song_name, MAX(fg_score) AS max_fg
                FROM team_buff_fg_loadouts
                WHERE force_details_json IS NOT NULL
                GROUP BY song_name
            ) AS best
              ON best.song_name = f.song_name
             AND best.max_fg = f.fg_score
            WHERE f.force_details_json IS NOT NULL
            ORDER BY f.song_name
            """
        ).fetchall()

        if not rows:
            raise SystemExit("[count_fg_great95_usage] no FG rows found in DB")

        totals = Counter()
        hits = Counter()
        examples: list[tuple[str, int, int]] = []
        for row in rows:
            song_name = str(row["song_name"] or "")
            difficulty = infer_difficulty(song_name)
            force = json.loads(row["force_details_json"])
            fg = force.get("ForceGreats") or {}
            trace = list(fg.get("frontier_trace") or [])
            early_tail_notes = count_early_tail_notes(trace)
            totals[difficulty] += 1
            totals["All"] += 1
            if early_tail_notes > 0:
                hits[difficulty] += 1
                hits["All"] += 1
                examples.append((song_name, int(row["fg_score"] or 0), int(early_tail_notes)))

        print(f"DB: {db_path}")
        for difficulty in ("Easy", "Normal", "Hard", "Unknown", "All"):
            total = int(totals[difficulty])
            if total <= 0:
                continue
            hit = int(hits[difficulty])
            pct = (100.0 * float(hit) / float(total)) if total else 0.0
            print(f"{difficulty}: {hit}/{total} great95 winners ({pct:.1f}%)")

        print()
        print("Examples:")
        for song_name, fg_score, early_tail_notes in examples[:20]:
            print(f"  {song_name}  fg={fg_score:,}  early_tail_notes={early_tail_notes}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
