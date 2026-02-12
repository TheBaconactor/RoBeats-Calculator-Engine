"""Persistence DB auditing and synthetic bug injection helpers.

These utilities are intentionally lightweight so they can run across multiple
historical commits where schema details may differ slightly.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


def _table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {str(r[0]) for r in rows}


def _table_has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    try:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    except Exception:
        return False
    return any(str(r[1]) == str(column) for r in rows)


def _scalar(conn: sqlite3.Connection, sql: str) -> Any:
    try:
        row = conn.execute(sql).fetchone()
    except Exception:
        return None
    if not row:
        return None
    return row[0]


def _append_issue(issues: list[dict[str, Any]], code: str, detail: str, value: Any = None) -> None:
    issues.append({"code": str(code), "detail": str(detail), "value": value})


def audit_persistence_db(
    db_path: str | Path,
    *,
    expected_min_songs: int = 1,
    expected_pending_fg_jobs: int = 0,
) -> dict[str, Any]:
    """Audit a persistence DB for core FG/base invariants.

    Returns a JSON-serializable dict with `issues` and `metrics`.
    """

    path = Path(db_path)
    report: dict[str, Any] = {
        "db_path": str(path),
        "exists": path.exists(),
        "size_bytes": int(path.stat().st_size) if path.exists() else None,
        "tables": [],
        "metrics": {},
        "issues": [],
    }
    issues: list[dict[str, Any]] = report["issues"]
    metrics: dict[str, Any] = report["metrics"]

    if not path.exists():
        _append_issue(issues, "db_missing", "database file not found")
        return report
    if path.stat().st_size <= 0:
        _append_issue(issues, "db_empty", "database file is empty", int(path.stat().st_size))
        return report

    conn = sqlite3.connect(path)
    try:
        tables = _table_names(conn)
        report["tables"] = sorted(tables)

        integrity = _scalar(conn, "PRAGMA integrity_check")
        metrics["integrity_check"] = integrity
        if str(integrity).lower() != "ok":
            _append_issue(issues, "integrity_check_failed", "sqlite integrity check failed", integrity)

        songs_count = None
        if "songs" in tables:
            songs_count = _scalar(conn, "SELECT COUNT(*) FROM songs")
        metrics["songs_count"] = songs_count
        if isinstance(songs_count, int) and int(songs_count) < int(expected_min_songs):
            _append_issue(
                issues,
                "songs_below_expected",
                "songs count below expected threshold",
                {"songs_count": int(songs_count), "expected_min_songs": int(expected_min_songs)},
            )

        if "songs" in tables and _table_has_column(conn, "songs", "best_score"):
            negative_best = _scalar(conn, "SELECT COUNT(*) FROM songs WHERE COALESCE(best_score, 0) < 0")
            metrics["songs_negative_best_score"] = negative_best
            if isinstance(negative_best, int) and negative_best > 0:
                _append_issue(
                    issues,
                    "songs_negative_best_score",
                    "songs.best_score contains negative values",
                    int(negative_best),
                )

        pending_fg_jobs = None
        if "pending_fg_jobs" in tables:
            pending_fg_jobs = _scalar(conn, "SELECT COUNT(*) FROM pending_fg_jobs")
        metrics["pending_fg_jobs_count"] = pending_fg_jobs
        if isinstance(pending_fg_jobs, int) and int(pending_fg_jobs) > int(expected_pending_fg_jobs):
            _append_issue(
                issues,
                "pending_fg_jobs_nonzero",
                "pending FG jobs were not drained",
                {"pending_fg_jobs": int(pending_fg_jobs), "expected_max": int(expected_pending_fg_jobs)},
            )

        fg_tables = [t for t in ("team_buff_fg_loadouts", "fg_loadouts") if t in tables]

        for table in fg_tables:
            if _table_has_column(conn, table, "fg_score") and _table_has_column(conn, table, "score"):
                bad = _scalar(conn, f"SELECT COUNT(*) FROM {table} WHERE fg_score <= score")
                metrics[f"{table}.non_improving_rows"] = bad
                if isinstance(bad, int) and bad > 0:
                    _append_issue(
                        issues,
                        "fg_non_improving_rows",
                        f"{table} contains rows where fg_score <= score",
                        {"table": table, "count": int(bad)},
                    )

        # Song-level best-score consistency against persisted base rows.
        if "songs" in tables and "team_buff_loadouts" in tables:
            if (
                _table_has_column(conn, "songs", "name")
                and _table_has_column(conn, "songs", "best_score")
                and _table_has_column(conn, "team_buff_loadouts", "song_name")
                and _table_has_column(conn, "team_buff_loadouts", "score")
            ):
                if _table_has_column(conn, "team_buff_loadouts", "team_buff"):
                    underrun = _scalar(
                        conn,
                        """
                        SELECT COUNT(*)
                        FROM songs s
                        WHERE COALESCE(s.best_score, 0) < COALESCE(
                            (
                                SELECT MAX(l.score)
                                FROM team_buff_loadouts l
                                WHERE l.song_name = s.name AND l.team_buff = 'T5'
                            ),
                            0
                        )
                        """,
                    )
                else:
                    underrun = _scalar(
                        conn,
                        """
                        SELECT COUNT(*)
                        FROM songs s
                        WHERE COALESCE(s.best_score, 0) < COALESCE(
                            (
                                SELECT MAX(l.score)
                                FROM team_buff_loadouts l
                                WHERE l.song_name = s.name
                            ),
                            0
                        )
                        """,
                    )
                metrics["songs_best_score_underrun_base_rows"] = underrun
                if isinstance(underrun, int) and underrun > 0:
                    _append_issue(
                        issues,
                        "songs_best_score_underrun",
                        "songs.best_score is below persisted base leaderboard rows",
                        int(underrun),
                    )

        if "songs" in tables and "team_buff_fg_loadouts" in tables:
            if (
                _table_has_column(conn, "songs", "name")
                and _table_has_column(conn, "songs", "best_fg_score")
                and _table_has_column(conn, "team_buff_fg_loadouts", "song_name")
                and _table_has_column(conn, "team_buff_fg_loadouts", "fg_score")
            ):
                if _table_has_column(conn, "team_buff_fg_loadouts", "team_buff"):
                    fg_underrun = _scalar(
                        conn,
                        """
                        SELECT COUNT(*)
                        FROM songs s
                        WHERE COALESCE(s.best_fg_score, 0) < COALESCE(
                            (
                                SELECT MAX(l.fg_score)
                                FROM team_buff_fg_loadouts l
                                WHERE l.song_name = s.name AND l.team_buff = 'T5'
                            ),
                            0
                        )
                        """,
                    )
                else:
                    fg_underrun = _scalar(
                        conn,
                        """
                        SELECT COUNT(*)
                        FROM songs s
                        WHERE COALESCE(s.best_fg_score, 0) < COALESCE(
                            (
                                SELECT MAX(l.fg_score)
                                FROM team_buff_fg_loadouts l
                                WHERE l.song_name = s.name
                            ),
                            0
                        )
                        """,
                    )
                metrics["songs_best_fg_score_underrun_fg_rows"] = fg_underrun
                if isinstance(fg_underrun, int) and fg_underrun > 0:
                    _append_issue(
                        issues,
                        "songs_best_fg_score_underrun",
                        "songs.best_fg_score is below persisted FG leaderboard rows",
                        int(fg_underrun),
                    )
    finally:
        conn.close()

    return report


def inject_synthetic_persistence_bug(db_path: str | Path) -> dict[str, Any]:
    """Inject one synthetic persistence defect into a DB copy.

    Returns metadata describing the mutation operation.
    """

    path = Path(db_path)
    result: dict[str, Any] = {
        "db_path": str(path),
        "applied": False,
        "mutation": None,
        "table": None,
    }
    if not path.exists() or path.stat().st_size <= 0:
        result["error"] = "db_missing_or_empty"
        return result

    conn = sqlite3.connect(path)
    try:
        tables = _table_names(conn)

        for table in ("team_buff_fg_loadouts", "fg_loadouts"):
            if table not in tables:
                continue
            if (not _table_has_column(conn, table, "fg_score")) or (not _table_has_column(conn, table, "score")):
                continue

            before = int(conn.total_changes)
            conn.execute(
                f"UPDATE {table} SET fg_score = score WHERE rowid IN (SELECT rowid FROM {table} LIMIT 1)",
            )
            conn.commit()
            changed = int(conn.total_changes) - before
            if changed > 0:
                result.update(
                    {
                        "applied": True,
                        "mutation": "fg_score_not_improving",
                        "table": table,
                    }
                )
                return result

        if "pending_fg_jobs" in tables:
            cols = conn.execute("PRAGMA table_info(pending_fg_jobs)").fetchall()
            col_names = [str(c[1]) for c in cols]
            values: dict[str, Any] = {}
            for name in col_names:
                lowered = name.lower()
                if lowered == "song_name":
                    values[name] = "__synthetic_mutation__"
                elif lowered.endswith("_json") or "json" in lowered:
                    values[name] = json.dumps([])
                elif lowered.endswith("_ts") or "time" in lowered:
                    values[name] = 0
                else:
                    values[name] = 0

            columns_sql = ", ".join(values.keys())
            placeholders = ", ".join(["?"] * len(values))
            conn.execute(
                f"INSERT INTO pending_fg_jobs ({columns_sql}) VALUES ({placeholders})",
                tuple(values.values()),
            )
            conn.commit()
            result.update(
                {
                    "applied": True,
                    "mutation": "pending_fg_job_injected",
                    "table": "pending_fg_jobs",
                }
            )
            return result

        if "songs" in tables and _table_has_column(conn, "songs", "best_score"):
            before = int(conn.total_changes)
            conn.execute("UPDATE songs SET best_score = -1 WHERE rowid IN (SELECT rowid FROM songs LIMIT 1)")
            conn.commit()
            changed = int(conn.total_changes) - before
            if changed > 0:
                result.update(
                    {
                        "applied": True,
                        "mutation": "songs_negative_best_score",
                        "table": "songs",
                    }
                )
                return result
    finally:
        conn.close()

    result["error"] = "no_mutation_target"
    return result

