"""Validate candidate FG futility certificates against persisted FG outcomes.

This verifier is intentionally offline/shadow-mode. It does not change production
behavior or submit GPU work. The goal is to test whether a proposed cheap skip
rule would have filtered any row whose persisted FG context beat the song's
current base winner.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
from gear_optimizer.core.config import load_config
from gear_optimizer.core.utils import cfg_to_dict
from gear_optimizer.data.database import _unpack_stats_after_load
from gear_optimizer.pipeline.song_processor import get_base_calc_song
from gear_optimizer.solver.fg_exact_dp import (
    prepare_force_greats_exact_dp_inputs,
    score_force_greats_exact_dp_bonus_from_prepared,
    solve_force_greats_exact_dp,
)


def _infer_difficulty(song_name: str) -> str:
    for diff in ("Easy", "Normal", "Hard"):
        if f" ({diff}) " in str(song_name or ""):
            return diff
    return "Normal"


def _bucket_for_fg_rows(fg_rows: int) -> str:
    if fg_rows <= 0:
        return "zero"
    if fg_rows <= 3:
        return "tiny"
    if fg_rows <= 25:
        return "medium"
    return "rich"


class CertificateValidator:
    def __init__(self, *, db_path: Path, team_buff: str) -> None:
        self.db_path = db_path
        self.team_buff = str(team_buff or "T5").strip().upper()
        self.cfg = cfg_to_dict(load_config())
        self.ref_arrays = _get_team_buff_ref_arrays_cached()
        self.calc_song_cache: dict[str, dict[str, Any] | None] = {}
        self.lift_cache: dict[tuple[str, str], int] = {}

    def calc_song_for(self, song_name: str) -> dict[str, Any] | None:
        if song_name in self.calc_song_cache:
            return self.calc_song_cache[song_name]

        path = PROJECT_ROOT / "Data" / _infer_difficulty(song_name) / f"{song_name}.txt"
        if not path.exists():
            self.calc_song_cache[song_name] = None
            return None

        self.calc_song_cache[song_name] = get_base_calc_song(str(path), self.cfg)
        return self.calc_song_cache[song_name]

    def exact_fixed_lift(self, *, song_name: str, loadout_hash: str, stats: dict[str, Any], calc_song: dict) -> int:
        key = (str(song_name), str(loadout_hash))
        cached = self.lift_cache.get(key)
        if cached is not None:
            return int(cached)

        prepared = prepare_force_greats_exact_dp_inputs(
            stats=stats,
            calc_song=calc_song,
            ref_arrays=self.ref_arrays,
        )
        if prepared is None:
            self.lift_cache[key] = 0
            return 0

        baseline_bonus = score_force_greats_exact_dp_bonus_from_prepared(
            prepared=prepared,
            section_counts=[],
        )
        solution = solve_force_greats_exact_dp(
            stats=stats,
            calc_song=calc_song,
            ref_arrays=self.ref_arrays,
            mode="timing_aware",
            prune=True,
        )
        lift = int(solution.best_delta) - int(baseline_bonus)
        self.lift_cache[key] = int(lift)
        return int(lift)

    def select_songs(self, conn: sqlite3.Connection, *, per_bucket: int) -> list[sqlite3.Row]:
        rows: list[sqlite3.Row] = []
        bucket_filters = {
            "zero": "fg_rows = 0",
            "tiny": "fg_rows BETWEEN 1 AND 3",
            "medium": "fg_rows BETWEEN 4 AND 25",
            "rich": "fg_rows >= 26",
        }
        for bucket, where_sql in bucket_filters.items():
            rows.extend(
                conn.execute(
                    f"""
                    WITH c AS (
                        SELECT
                            s.name,
                            s.best_score,
                            s.best_fg_score,
                            (
                                SELECT COUNT(*)
                                FROM team_buff_fg_loadouts f
                                WHERE f.song_name = s.name
                                  AND UPPER(COALESCE(f.team_buff, '')) = ?
                            ) AS fg_rows
                        FROM songs s
                        WHERE EXISTS (
                            SELECT 1
                            FROM team_buff_loadouts b
                            WHERE b.song_name = s.name
                              AND UPPER(COALESCE(b.team_buff, '')) = ?
                        )
                    )
                    SELECT *, ? AS bucket
                    FROM c
                    WHERE {where_sql}
                    ORDER BY name
                    LIMIT ?
                    """,
                    (self.team_buff, self.team_buff, bucket, int(per_bucket)),
                ).fetchall()
            )
        return rows

    def validate(self, *, per_bucket: int, max_rows_per_song: int, margins: list[int]) -> dict[str, Any]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        start = time.perf_counter()
        records: list[dict[str, Any]] = []
        skipped_missing_song = 0

        try:
            songs = self.select_songs(conn, per_bucket=per_bucket)
            for song in songs:
                song_name = str(song["name"])
                calc_song = self.calc_song_for(song_name)
                if calc_song is None:
                    skipped_missing_song += 1
                    continue

                rows = conn.execute(
                    """
                    SELECT loadout_hash, score, fg_score, details_json
                    FROM team_buff_loadouts
                    WHERE song_name = ?
                      AND UPPER(COALESCE(team_buff, '')) = ?
                    ORDER BY score DESC
                    LIMIT ?
                    """,
                    (song_name, self.team_buff, int(max_rows_per_song)),
                ).fetchall()

                for row in rows:
                    details = _unpack_stats_after_load(json.loads(row["details_json"]) if row["details_json"] else {})
                    stats = dict((details or {}).get("Stats") or {})
                    if not stats:
                        continue

                    lift = self.exact_fixed_lift(
                        song_name=song_name,
                        loadout_hash=str(row["loadout_hash"] or ""),
                        stats=stats,
                        calc_song=calc_song,
                    )
                    deficit = int(song["best_score"] or 0) - int(row["score"] or 0)
                    actual_fg_overall = int(row["fg_score"] or 0) > int(song["best_score"] or 0)
                    records.append(
                        {
                            "song": song_name,
                            "bucket": str(song["bucket"]),
                            "fg_rows": int(song["fg_rows"] or 0),
                            "score": int(row["score"] or 0),
                            "fg_score": int(row["fg_score"] or 0),
                            "deficit": int(deficit),
                            "fixed_lift": int(lift),
                            "actual_fg_overall": bool(actual_fg_overall),
                        }
                    )
        finally:
            conn.close()

        margin_results: dict[str, Any] = {}
        for margin in margins:
            by_bucket: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
            false_examples: list[dict[str, Any]] = []
            checked = skips = false_skips = 0
            for rec in records:
                would_skip = int(rec["fixed_lift"]) <= int(rec["deficit"]) - int(margin)
                checked += 1
                skips += int(would_skip)
                false_skips += int(would_skip and rec["actual_fg_overall"])
                bucket_counts = by_bucket[str(rec["bucket"])]
                bucket_counts[0] += 1
                bucket_counts[1] += int(would_skip)
                bucket_counts[2] += int(would_skip and rec["actual_fg_overall"])
                if would_skip and rec["actual_fg_overall"] and len(false_examples) < 10:
                    false_examples.append(rec)

            margin_results[str(margin)] = {
                "checked": checked,
                "would_skip": skips,
                "false_skips": false_skips,
                "by_bucket": {
                    key: {"checked": vals[0], "would_skip": vals[1], "false_skips": vals[2]}
                    for key, vals in sorted(by_bucket.items())
                },
                "false_examples": false_examples,
            }

        fixed_lifts = [int(rec["fixed_lift"]) for rec in records]
        return {
            "db": str(self.db_path),
            "team_buff": self.team_buff,
            "songs_requested_per_bucket": int(per_bucket),
            "loadouts_checked": len(records),
            "songs_cached": len([v for v in self.calc_song_cache.values() if v is not None]),
            "songs_missing_chart": int(skipped_missing_song),
            "elapsed_sec": round(time.perf_counter() - start, 3),
            "fixed_lift_mean": round(mean(fixed_lifts), 3) if fixed_lifts else 0,
            "margins": margin_results,
        }


def _parse_margins(raw: str) -> list[int]:
    out: list[int] = []
    for part in str(raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        out.append(max(0, int(part)))
    return out or [0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate candidate FG futility certificate safety.")
    parser.add_argument("--db", default=str(PROJECT_ROOT / "evolution.db"))
    parser.add_argument("--team-buff", default="T5")
    parser.add_argument("--per-bucket", type=int, default=40)
    parser.add_argument("--max-rows-per-song", type=int, default=51)
    parser.add_argument(
        "--margins",
        default="0,50000,100000,200000,500000,1000000",
        help="Comma-separated safety margins for fixed_lift <= deficit - margin.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON only.")
    args = parser.parse_args()

    db_path = Path(args.db)
    validator = CertificateValidator(db_path=db_path, team_buff=args.team_buff)
    report = validator.validate(
        per_bucket=max(1, int(args.per_bucket)),
        max_rows_per_song=max(1, int(args.max_rows_per_song)),
        margins=_parse_margins(args.margins),
    )

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return

    print("=" * 78)
    print("FG Futility Certificate Validation")
    print("=" * 78)
    print(f"DB: {report['db']}  TeamBuff: {report['team_buff']}")
    print(
        f"Checked {report['loadouts_checked']:,} loadouts across "
        f"{report['songs_cached']:,} chart-backed songs in {report['elapsed_sec']}s."
    )
    print()
    for margin, result in report["margins"].items():
        print(
            f"Margin {int(margin):,}: would_skip={result['would_skip']:,} / {result['checked']:,}; "
            f"false_skips={result['false_skips']:,}"
        )
        for bucket, vals in result["by_bucket"].items():
            print(
                f"  {bucket:<6} checked={vals['checked']:<5} "
                f"would_skip={vals['would_skip']:<5} false={vals['false_skips']}"
            )
        if result["false_examples"]:
            print("  examples:")
            for ex in result["false_examples"][:5]:
                print(
                    f"    {ex['song'][:54]} | def={ex['deficit']:,} "
                    f"fixed_lift={ex['fixed_lift']:,} fg={ex['fg_score']:,}"
                )
        print()


if __name__ == "__main__":
    main()
