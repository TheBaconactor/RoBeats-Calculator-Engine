"""
Audit a MetaFinder SQLite DB for frontend-facing integrity issues.

Focuses on the views that exporters/frontends typically consume:
  - frontend_best_base_loadouts / frontend_best_fg_loadouts
  - frontend_base_top51_by_song_tier / frontend_fg_top51_by_song_tier

This is intentionally a *read-only* audit script.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.data.database import get_evolution_db_path

EXPECTED_TEAM_BUFFS = {"NONE", "T1", "T5", "T10", "T15"}
STAT_KEYS = (
    "Chill",
    "Flow",
    "Rush",
    "Beat",
    "Vibe",
    "Perfect Points",
    "Combo Multiplier",
    "Fever Multiplier",
    "Fever Fill Rate",
    "Fever Time",
)


def _loads_json(s: Any, default: Any) -> Any:
    if s is None:
        return default
    if isinstance(s, (dict, list)):
        return s
    text = str(s).strip()
    if not text:
        return default
    try:
        return json.loads(text)
    except Exception:
        return default


def _is_stats_all_zero(stats: Any) -> bool:
    if not isinstance(stats, dict) or not stats:
        return True
    for k in STAT_KEYS:
        try:
            if float(stats.get(k, 0) or 0) != 0.0:
                return False
        except Exception:
            continue
    return True


def _minis_json_has_corruption_signature(minis_json: Any) -> bool:
    # Historic corruption signature: JSON strings like "['Electroman']".
    if not minis_json:
        return False
    return "['" in str(minis_json)


def _iter_rows(conn: sqlite3.Connection, query: str, params: tuple[Any, ...] = (), *, batch_size: int = 1000):
    cur = conn.execute(query, params)
    while True:
        rows = cur.fetchmany(batch_size)
        if not rows:
            break
        yield from rows


@dataclass
class AuditCounts:
    rows: int = 0
    bad_team_buff: int = 0
    json_parse_fail: int = 0
    missing_stats: int = 0
    zero_stats: int = 0
    corrupt_minis: int = 0
    bad_fg_invariant: int = 0
    missing_force_score: int = 0


def _audit_view(conn: sqlite3.Connection, *, view_name: str, is_fg: bool) -> AuditCounts:
    counts = AuditCounts()
    query = (
        f"SELECT song_name, team_buff, score, fg_score, gear_json, minis_json, details_json, force_details_json "
        f"FROM {view_name}"
    )

    for r in _iter_rows(conn, query):
        counts.rows += 1

        team_buff = str(r["team_buff"] or "").strip().upper()
        if team_buff not in EXPECTED_TEAM_BUFFS:
            counts.bad_team_buff += 1

        gear = _loads_json(r["gear_json"], None)
        minis = _loads_json(r["minis_json"], None)
        details = _loads_json(r["details_json"], None)
        force = _loads_json(r["force_details_json"], {} if not is_fg else None)

        if gear is None or minis is None or details is None or (is_fg and force is None):
            counts.json_parse_fail += 1
            continue

        stats = details.get("Stats") if isinstance(details, dict) else None
        if stats is None:
            counts.missing_stats += 1
        elif _is_stats_all_zero(stats):
            counts.zero_stats += 1

        if _minis_json_has_corruption_signature(r["minis_json"]):
            counts.corrupt_minis += 1

        score = int(r["score"] or 0)
        fg_score = int(r["fg_score"] or 0)
        if is_fg:
            if fg_score <= score:
                counts.bad_fg_invariant += 1

            # Consumers often key off top-level force score; ensure it exists somewhere obvious.
            force_score = 0
            if isinstance(force, dict):
                try:
                    force_score = int(force.get("score") or force.get("Score") or 0)
                except Exception:
                    force_score = 0
                if force_score <= 0 and isinstance(force.get("ForceGreats"), dict):
                    try:
                        force_score = int(force["ForceGreats"].get("final_score") or 0)
                    except Exception:
                        force_score = 0
            if force_score <= 0:
                counts.missing_force_score += 1

    return counts


def _print_counts(label: str, counts: AuditCounts) -> None:
    print(f"\n[{label}] rows={counts.rows:,}")
    print(f"  bad_team_buff: {counts.bad_team_buff:,}")
    print(f"  json_parse_fail: {counts.json_parse_fail:,}")
    print(f"  missing_stats: {counts.missing_stats:,}")
    print(f"  zero_stats: {counts.zero_stats:,}")
    print(f"  corrupt_minis_signature: {counts.corrupt_minis:,}")
    if counts.bad_fg_invariant:
        print(f"  bad_fg_invariant(fg_score<=score): {counts.bad_fg_invariant:,}")
    if counts.missing_force_score:
        print(f"  missing_force_score: {counts.missing_force_score:,}")


def _spot_check_song(conn: sqlite3.Connection, song_name: str) -> None:
    print(f"\n[SpotCheck] {song_name}")
    rows = conn.execute(
        """
        SELECT team_buff, rank, score, fg_score, details_json, source_table
        FROM frontend_fg_top51_by_song_tier
        WHERE song_name = ? AND rank = 1
        ORDER BY UPPER(team_buff)
        """,
        (song_name,),
    ).fetchall()
    if not rows:
        print("  (no rows found)")
        return

    for r in rows:
        details = _loads_json(r["details_json"], {})
        stats = details.get("Stats", {}) if isinstance(details, dict) else {}
        print(
            {
                "team_buff": r["team_buff"],
                "score": r["score"],
                "fg_score": r["fg_score"],
                "stats_vibe": stats.get("Vibe"),
                "stats_chill": stats.get("Chill"),
                "source_table": r["source_table"],
            }
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit DB integrity for frontend-facing views.")
    parser.add_argument(
        "--db",
        type=str,
        default="",
        help="Path to sqlite DB (defaults to EVOLUTION_DB_PATH / ./evolution.db).",
    )
    parser.add_argument("--song", type=str, default="", help="Optional song_name to spot-check (rank=1 across tiers).")
    args = parser.parse_args()

    db_path = Path(args.db).expanduser() if args.db else Path(get_evolution_db_path())
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    version = conn.execute("PRAGMA user_version").fetchone()[0]
    print(f"DB: {db_path}")
    print(f"PRAGMA user_version: {version}")

    views = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='view'")}
    required_views = [
        "frontend_best_base_loadouts",
        "frontend_best_fg_loadouts",
        "frontend_base_top51_by_song_tier",
        "frontend_fg_top51_by_song_tier",
    ]
    missing = [v for v in required_views if v not in views]
    if missing:
        print("\nMissing required views:")
        for v in missing:
            print(f"  - {v}")
        raise SystemExit(2)

    _print_counts(
        "frontend_best_base_loadouts",
        _audit_view(conn, view_name="frontend_best_base_loadouts", is_fg=False),
    )
    _print_counts(
        "frontend_best_fg_loadouts",
        _audit_view(conn, view_name="frontend_best_fg_loadouts", is_fg=True),
    )
    _print_counts(
        "frontend_base_top51_by_song_tier",
        _audit_view(conn, view_name="frontend_base_top51_by_song_tier", is_fg=False),
    )
    _print_counts(
        "frontend_fg_top51_by_song_tier",
        _audit_view(conn, view_name="frontend_fg_top51_by_song_tier", is_fg=True),
    )

    if args.song:
        _spot_check_song(conn, args.song)

    conn.close()


if __name__ == "__main__":
    main()
