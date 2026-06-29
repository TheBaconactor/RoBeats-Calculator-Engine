"""
Per-song counter reads/writes against the `songs` table, plus per-song
presence queries against `songs` and the loadout tables.
"""
import os
import sqlite3
import logging
from collections.abc import Iterable
from typing import Optional
from ...core.utils import require_int
from .connection import get_db_connection, get_db_connection_cached, get_evolution_db_path

logger = logging.getLogger(__name__)


def get_song_names_present_in_db(
    song_names: Iterable[str],
    db_path: Optional[str] = None,
    *,
    require_loadouts: bool = False,
) -> set[str]:
    """
    Return the subset of song names that are already present in the DB.

    By default, presence is defined as having a row in `songs` OR any row in the
    loadout tables. When ``require_loadouts=True``, only persisted loadout rows
    count as present so stub ``songs`` rows without optimization output are treated
    as missing.
    """
    names = [name for name in (song_names or []) if name]
    if not names:
        return set()

    if db_path is None:
        db_path = get_evolution_db_path()
    db_path = str(db_path)
    if not db_path or not os.path.exists(db_path):
        return set()

    conn = get_db_connection_cached(db_path)
    present: set[str] = set()
    batch_size = 900  # sqlite default parameter cap is commonly 999
    for offset in range(0, len(names), batch_size):
        batch = names[offset : offset + batch_size]
        placeholders = ",".join("?" for _ in batch)

        if not require_loadouts:
            try:
                rows = conn.execute(
                    f"SELECT name FROM songs WHERE name IN ({placeholders})",
                    batch,
                ).fetchall()
                present.update(row[0] for row in rows if row and row[0])
            except sqlite3.Error:
                pass

        for table in ("team_buff_loadouts", "team_buff_fg_loadouts"):
            try:
                rows = conn.execute(
                    f"SELECT DISTINCT song_name FROM {table} WHERE song_name IN ({placeholders})",
                    batch,
                ).fetchall()
                present.update(row[0] for row in rows if row and row[0])
            except sqlite3.Error:
                continue

    return present


def get_song_names_with_persisted_loadouts(
    song_names: Iterable[str],
    db_path: Optional[str] = None,
) -> set[str]:
    """Return song names that already have persisted base or FG loadout rows."""
    return get_song_names_present_in_db(song_names, db_path, require_loadouts=True)


def get_song_counters(
    song_name: str,
    *,
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[str] = None,
) -> tuple[int, int, int, int]:
    """
    Fetch per-song attempt counters and best scores from `songs`.
    Returns:
        (attempt_lifetime, attempts_first, best_score, best_fg_score)
    """
    song_name = str(song_name or "").strip()
    if not song_name:
        return (0, 0, 0, 0)
    if conn is None:
        conn = get_db_connection_cached(db_path or get_evolution_db_path())
    try:
        row = conn.execute(
            """
            SELECT attempt_lifetime, attempts_first, best_score, best_fg_score
            FROM songs
            WHERE name = ?
            """,
            (song_name,),
        ).fetchone()
        if not row:
            return (0, 0, 0, 0)
        # Authoritative per-song counters: fail loud on a non-int (DB corruption)
        # rather than silently masking it as 0. require_int still maps NULL/0 -> 0.
        attempt_lifetime = require_int(row["attempt_lifetime"], field="attempt_lifetime")
        attempts_first = require_int(row["attempts_first"], field="attempts_first")
        best_score = require_int(row["best_score"], field="best_score")
        best_fg_score = require_int(row["best_fg_score"], field="best_fg_score")
        return (attempt_lifetime, attempts_first, best_score, best_fg_score)
    except sqlite3.Error:
        raise


def update_song_counters(
    song_name: str,
    *,
    processed_run: bool,
    record_improved: bool,
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[str] = None,
) -> None:
    """
    Update per-song attempt counters.
    Semantics:
    - If `processed_run=True`: increment `attempt_lifetime` and `attempts_first`
    - If `record_improved=True`: reset `attempts_first = 1`
    - If `processed_run=False`: do not increment (used for deferred FG-only updates)
    """
    song_name = str(song_name or "").strip()
    if not song_name:
        return
    close_conn = False
    if conn is None:
        conn = get_db_connection(db_path or get_evolution_db_path())
        close_conn = True
    pr = 1 if processed_run else 0
    ri = 1 if record_improved else 0
    try:
        with conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO songs (name, best_score, best_fg_score, last_updated, attempt_lifetime, attempts_first)
                VALUES (?, 0, 0, 0, 0, 0)
                """,
                (song_name,),
            )
            conn.execute(
                """
                UPDATE songs
                SET
                    attempt_lifetime = CASE
                        WHEN ? THEN COALESCE(attempt_lifetime, 0) + 1
                        ELSE COALESCE(attempt_lifetime, 0)
                    END,
                    attempts_first = CASE
                        WHEN ? THEN 1
                        WHEN ? THEN COALESCE(attempts_first, 0) + 1
                        ELSE COALESCE(attempts_first, 0)
                    END,
                    last_updated = strftime('%s', 'now')
                WHERE name = ?
                """,
                (pr, ri, pr, song_name),
            )
    except sqlite3.Error:
        return
    finally:
        if close_conn:
            try:
                conn.close()
            except Exception as e:
                logger.warning(f"database:update_song_counters: {e}")
