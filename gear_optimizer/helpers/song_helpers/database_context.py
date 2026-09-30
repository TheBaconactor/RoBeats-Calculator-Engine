"""Song Helpers - Database Context - Progress baseline loading."""

import logging
import sqlite3
import threading
import time

from ...data.database import (
    get_db_connection_cached,
    get_best_loadouts,
    get_song_counters,
)
from ...data.models import WarnOnce

# Global warn-once instance
logger = logging.getLogger(__name__)
WARN_ONCE = WarnOnce()

_WAL_MAINT_LOCK = threading.Lock()
_LAST_WAL_MAINT_TS = 0.0


def build_db_key(found_song_name: str) -> str:
    """A song's DB key: its name (timing models share one namespace)."""
    return str(found_song_name or "").strip()


def _maybe_wal_maintenance(conn) -> None:
    """
    Opportunistic WAL maintenance for long-running sessions.

    This MUST NOT run on every per-song DB read: TRUNCATE checkpoints can take locks
    and stall concurrent writers, which can indirectly starve the GPU pipeline.
    """
    interval_sec = 30.0
    global _LAST_WAL_MAINT_TS
    now = time.monotonic()
    with _WAL_MAINT_LOCK:
        if (now - _LAST_WAL_MAINT_TS) < interval_sec:
            return
        _LAST_WAL_MAINT_TS = now

    try:
        # PASSIVE is non-blocking; it won't force truncation, but it helps keep WAL
        # growth in check without taking disruptive locks.
        conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
    except sqlite3.Error:
        logger.debug("[DB] WAL checkpoint(PASSIVE) failed", exc_info=True)


def load_database_context(
    found_song_name,
    *,
    team_buff: str = "T5",
):
    """
    Load the previous best DB record used for progress and result display (items as names).

    Returns:
        previous record or None
    """
    prev_record = None
    best_loadouts = get_best_loadouts(
        found_song_name,
        limit=1,
        team_buff=str(team_buff or "T5"),
    )
    if best_loadouts:
        prev_record = best_loadouts[0]
    conn = get_db_connection_cached()
    _maybe_wal_maintenance(conn)

    return prev_record


def load_database_progress_baseline(
    found_song_name,
    *,
    team_buff: str = "T5",
):
    """
    Load the canonical progress baseline.

    Returns:
        tuple:
            (
                prev_record,
                db_best_score,
                db_best_fg_score,
                attempt_lifetime,
                prev_attempts_first,
                baseline_valid,
            )
    """
    prev_record = None
    db_best_score = 0
    db_best_fg_score = 0
    attempt_lifetime_prev = 0
    prev_attempts_first = 0
    baseline_valid = False

    def _invalid_baseline_result():
        if isinstance(prev_record, tuple) and len(prev_record) == 2:
            return prev_record[0], prev_record[1], 0, 0, 0, 0, False
        return None, {}, 0, 0, 0, 0, False

    try:
        prev_record = load_database_context(
            found_song_name,
            team_buff=str(team_buff or "T5"),
        )
    except sqlite3.Error:
        return _invalid_baseline_result()

    try:
        (
            attempt_lifetime_prev,
            prev_attempts_first,
            db_best_score,
            db_best_fg_score,
        ) = get_song_counters(str(found_song_name or "").strip())
        baseline_valid = True
        if not db_best_fg_score:
            conn = get_db_connection_cached()
            row = conn.execute(
                """
                SELECT MAX(fg_score)
                FROM team_buff_fg_loadouts
                WHERE song_name = ? AND team_buff = ?
                """,
                (str(found_song_name or "").strip(), str(team_buff or "T5")),
            ).fetchone()
            if row is not None:
                db_best_fg_score = int(row[0] or 0)
    except sqlite3.Error:
        return _invalid_baseline_result()

    if not db_best_score and isinstance(prev_record, dict):
        db_best_score = int(prev_record.get("score", 0) or 0)

    if not db_best_fg_score and isinstance(prev_record, dict):
        db_best_fg_score = int(prev_record.get("fg_score", 0) or 0)

    if isinstance(prev_record, dict) and "details" in prev_record:
        if int(attempt_lifetime_prev or 0) <= 0:
            attempt_lifetime_prev = int(prev_record["details"].get("attempt_lifetime", 0) or 0)
        if int(prev_attempts_first or 0) <= 0:
            prev_attempts_first = int(prev_record["details"].get("attempts_first", 0) or 0)

    attempt_lifetime = int(attempt_lifetime_prev) + 1
    return (
        prev_record,
        int(db_best_score or 0),
        int(db_best_fg_score or 0),
        int(attempt_lifetime or 0),
        int(prev_attempts_first or 0),
        bool(baseline_valid),
    )
