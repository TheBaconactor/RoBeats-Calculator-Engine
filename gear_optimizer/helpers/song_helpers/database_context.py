"""
Song Helpers - Database Context - Database seeds and known loadouts loading.

This module provides database operations:
- load_database_context: Load database seeds and known loadouts
"""
import json

from ...data.database import (
    get_db_connection,
    get_best_loadouts,
    get_evolution_db_path,
    LOADOUTS_PER_SONG_LIMIT,
)
from ...data.models import WarnOnce

# Global warn-once instance
WARN_ONCE = WarnOnce()


def load_database_context(found_song_name, use_evo_db, gears_by_name, minis_by_name):
    """
    Load database seeds and known loadouts.

    Args:
        found_song_name: Name of the song
        use_evo_db: Whether to use evolution database
        gears_by_name: Dictionary of gears by name
        minis_by_name: Dictionary of minis by name

    Returns:
        tuple: (prev_record, known_loadouts)
    """
    db_seed = None
    prev_record = None
    known_loadouts = {}

    if use_evo_db:
        # Always print DB path + exact lookup key to make seeding issues obvious.
        # (repr shows hidden whitespace / mismatched suffixes that would otherwise be invisible.)
        try:
            print(f"[DB] Using DB: {get_evolution_db_path()} | lookup key: {found_song_name!r}")
        except Exception:
            print(f"[DB] Using DB: (unknown) | lookup key: {found_song_name!r}")

        # Load previous best for seeding
        best_loadouts = get_best_loadouts(
            found_song_name, limit=1, gears_by_name=gears_by_name, minis_by_name=minis_by_name
        )
        if best_loadouts:
            prev_record = best_loadouts[0]
            db_seed = prev_record

        if prev_record:
            print(f"[DB] Found previous best: {prev_record.get('score', 0)}")
        else:
            # If we expected a DB seed but didn't find one, show nearby candidates.
            # This catches cases where the song key differs by suffix/spacing.
            try:
                conn = get_db_connection()
                rows = conn.execute(
                    "SELECT DISTINCT song_name FROM loadouts WHERE song_name LIKE ? LIMIT 8",
                    (f"%{found_song_name.split('(')[0].strip()}%",),
                ).fetchall()
                conn.close()
                if rows:
                    print("[DB] No exact seed found. Similar keys in DB:")
                    for r in rows:
                        # sqlite3.Row supports index access in this connection setup
                        print(f"  - {str(r[0])!r}")
            except Exception:
                pass

        # Fetch known loadouts for persistent caching
        try:
            conn = get_db_connection()
            cursor = conn.execute(
                """SELECT loadout_hash, score, fg_score, force_details_json, details_json
                   FROM loadouts
                   WHERE song_name = ?
                   ORDER BY score DESC
                   LIMIT ?""",
                (found_song_name, LOADOUTS_PER_SONG_LIMIT),
            )
            for row in cursor:
                force_blob = row["force_details_json"]
                force_data = None
                if force_blob:
                    try:
                        force_data = json.loads(force_blob)
                    except Exception as exc:
                        WARN_ONCE.warn(
                            "force-loadout-json",
                            f"Invalid force JSON for {row.get('loadout_hash')}: {exc}",
                        )
                        force_data = None

                details_blob = row["details_json"]
                details_data = None
                if details_blob:
                    try:
                        details_data = json.loads(details_blob)
                    except Exception as exc:
                        WARN_ONCE.warn(
                            "details-loadout-json",
                            f"Invalid details JSON for {row.get('loadout_hash')}: {exc}",
                        )
                        details_data = None

                known_loadouts[row["loadout_hash"]] = (
                    row["score"],
                    row["fg_score"],
                    force_data,
                    details_data,
                )
            # Memory leak fix #2: Checkpoint WAL before closing connection
            # Prevents WAL file growth (5-50 MB per 1000 songs)
            try:
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                conn.execute("PRAGMA optimize")
            except Exception as e:
                # CRITICAL FIX: Log checkpoint failures (was silently suppressed)
                import logging
                logging.warning(f"[DB] WAL checkpoint/optimize failed: {e}")
            conn.close()
        except Exception as e:
            print(f"[DB] Error fetching known loadouts: {e}")

    return prev_record, known_loadouts
