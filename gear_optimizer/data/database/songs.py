"""
Per-song counter reads/writes against the `songs` table.
"""
import sqlite3
import logging
from typing import Optional
from .connection import get_db_connection, get_db_connection_cached, get_evolution_db_path

logger = logging.getLogger(__name__)


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
        try:
            attempt_lifetime = int(row["attempt_lifetime"] or 0)
        except Exception as e:
            logger.warning(f"database:get_song_counters: {e}")
            attempt_lifetime = 0
        try:
            attempts_first = int(row["attempts_first"] or 0)
        except Exception as e:
            logger.warning(f"database:get_song_counters: {e}")
            attempts_first = 0
        try:
            best_score = int(row["best_score"] or 0)
        except Exception as e:
            logger.warning(f"database:get_song_counters: {e}")
            best_score = 0
        try:
            best_fg_score = int(row["best_fg_score"] or 0)
        except Exception as e:
            logger.warning(f"database:get_song_counters: {e}")
            best_fg_score = 0
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
