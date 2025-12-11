"""
Database merge functionality for combining evolution databases.

Handles automatic merging of a secondary database (evo.db) into the main
evolution.db. Ensures data integrity, handles conflicts intelligently, and
provides comprehensive logging.
"""
import logging
import os
import sqlite3
import time
from typing import Tuple, Dict

from .database import get_evolution_db_path, get_db_connection, init_db


def find_secondary_databases():
    """
    Find all secondary databases in the same directory as evolution.db.

    Searches for any .db files that:
    - Are not the main evolution database
    - Are not backup files (.backup_*)
    - Are not WAL/SHM files
    - Have valid SQLite schema

    Returns:
        list: List of paths to secondary databases (sorted by modification time)
    """
    main_db_path = get_evolution_db_path()
    main_db_name = os.path.basename(main_db_path)
    db_dir = os.path.dirname(main_db_path) or "."

    secondary_dbs = []

    try:
        for filename in os.listdir(db_dir):
            # Check if it's a .db file
            if not filename.endswith('.db'):
                continue

            # Skip main database
            if filename == main_db_name:
                continue

            # Skip backup files
            if '.backup_' in filename:
                continue

            # Skip WAL/SHM files (they end with .db-wal, .db-shm)
            if filename.endswith(('.db-wal', '.db-shm', '.db-journal')):
                continue

            full_path = os.path.join(db_dir, filename)

            # Check if it's a file (not directory)
            if not os.path.isfile(full_path):
                continue

            # Quick validation - can we open it as SQLite?
            try:
                conn = sqlite3.connect(full_path, timeout=1.0)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
                cursor.fetchone()
                conn.close()

                # Add to list with modification time for sorting
                mtime = os.path.getmtime(full_path)
                secondary_dbs.append((full_path, mtime))
            except Exception:
                # Not a valid SQLite database, skip it
                continue

    except Exception as e:
        logging.warning(f"[DB Merge] Error scanning for databases: {e}")
        return []

    # Sort by modification time (newest first)
    secondary_dbs.sort(key=lambda x: x[1], reverse=True)

    return [path for path, _ in secondary_dbs]


def validate_database_schema(db_path: str) -> Tuple[bool, str]:
    """
    Validate that database has compatible schema.

    Args:
        db_path: Path to database to validate

    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        conn = sqlite3.connect(db_path, timeout=5.0)
        cursor = conn.cursor()

        # Check for required tables
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name IN ('songs', 'loadouts')
        """)
        tables = {row[0] for row in cursor.fetchall()}

        if 'songs' not in tables or 'loadouts' not in tables:
            conn.close()
            return False, "Missing required tables (songs or loadouts)"

        # Check loadouts table has required columns
        cursor.execute("PRAGMA table_info(loadouts)")
        columns = {row[1] for row in cursor.fetchall()}

        required_columns = {
            'song_name', 'loadout_hash', 'score', 'fg_score',
            'gear_json', 'minis_json', 'details_json',
            'force_details_json', 'timestamp'
        }

        missing_columns = required_columns - columns
        if missing_columns:
            conn.close()
            return False, f"Missing required columns: {', '.join(missing_columns)}"

        conn.close()
        return True, ""

    except Exception as e:
        return False, f"Validation error: {str(e)}"


def get_database_stats(db_path: str) -> Dict[str, int]:
    """
    Get statistics about database contents.

    Args:
        db_path: Path to database

    Returns:
        dict: Statistics (song_count, loadout_count, total_score)
    """
    try:
        conn = sqlite3.connect(db_path, timeout=5.0)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM songs")
        song_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM loadouts")
        loadout_count = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(best_score) FROM songs")
        result = cursor.fetchone()[0]
        total_score = result if result else 0

        conn.close()

        return {
            'song_count': song_count,
            'loadout_count': loadout_count,
            'total_score': total_score
        }
    except Exception as e:
        logging.warning(f"[DB Merge] Failed to get stats: {e}")
        return {'song_count': 0, 'loadout_count': 0, 'total_score': 0}


def merge_databases(
    main_db_path: str,
    secondary_db_path: str,
    delete_after_merge: bool = True,
    backup_before_merge: bool = True
) -> Tuple[bool, str, Dict]:
    """
    Merge secondary database into main database.

    Strategy:
    - Attach secondary database
    - Merge songs table (keep higher scores)
    - Merge loadouts table (upsert with conflict resolution)
    - Maintain data integrity (foreign keys, unique constraints)
    - Provide detailed statistics

    Args:
        main_db_path: Path to main evolution database
        secondary_db_path: Path to secondary database to merge
        delete_after_merge: Whether to delete secondary DB after successful merge
        backup_before_merge: Whether to create backup before merge

    Returns:
        tuple: (success, message, stats_dict)
    """
    start_time = time.time()

    try:
        # Validate secondary database
        is_valid, error_msg = validate_database_schema(secondary_db_path)
        if not is_valid:
            return False, f"Secondary database invalid: {error_msg}", {}

        # Get pre-merge stats
        main_stats_before = get_database_stats(main_db_path)
        secondary_stats = get_database_stats(secondary_db_path)

        logging.info(f"[DB Merge] Starting merge:")
        logging.info(f"  Main DB: {main_stats_before['song_count']} songs, {main_stats_before['loadout_count']} loadouts")
        logging.info(f"  Secondary DB: {secondary_stats['song_count']} songs, {secondary_stats['loadout_count']} loadouts")

        # Create backup if requested
        if backup_before_merge:
            backup_path = main_db_path + f".backup_{int(time.time())}"
            try:
                import shutil
                shutil.copy2(main_db_path, backup_path)
                logging.info(f"[DB Merge] Created backup: {backup_path}")
            except Exception as e:
                logging.warning(f"[DB Merge] Backup failed: {e}")

        # Connect to main database
        conn = get_db_connection(main_db_path)
        conn.execute("PRAGMA foreign_keys = OFF")  # Temporarily disable for merge

        try:
            # Attach secondary database
            conn.execute(f"ATTACH DATABASE ? AS secondary", (secondary_db_path,))

            # Start transaction for atomic merge
            conn.execute("BEGIN IMMEDIATE")

            # Merge songs table (keep higher scores)
            # If song exists in both, keep the higher best_score and best_fg_score
            # WORKAROUND: Python's sqlite3 doesn't support INSERT...SELECT...ON CONFLICT properly
            # Use two-step process: INSERT new songs, then UPDATE existing ones

            # Step 1: Insert new songs that don't exist in main database
            insert_new_songs_sql = """
                INSERT OR IGNORE INTO songs (name, best_score, best_fg_score, last_updated)
                SELECT name, best_score, best_fg_score, last_updated
                FROM secondary.songs
            """
            cursor = conn.execute(insert_new_songs_sql)
            new_songs_count = cursor.rowcount

            # Step 2: Update existing songs with better scores
            update_existing_songs_sql = """
                UPDATE songs
                SET
                    best_score = (
                        SELECT MAX(main.songs.best_score, secondary.songs.best_score)
                        FROM secondary.songs
                        WHERE secondary.songs.name = main.songs.name
                    ),
                    best_fg_score = (
                        SELECT MAX(main.songs.best_fg_score, secondary.songs.best_fg_score)
                        FROM secondary.songs
                        WHERE secondary.songs.name = main.songs.name
                    ),
                    last_updated = (
                        SELECT MAX(main.songs.last_updated, secondary.songs.last_updated)
                        FROM secondary.songs
                        WHERE secondary.songs.name = main.songs.name
                    )
                WHERE EXISTS (
                    SELECT 1 FROM secondary.songs WHERE secondary.songs.name = main.songs.name
                )
            """
            cursor = conn.execute(update_existing_songs_sql)
            updated_songs_count = cursor.rowcount
            songs_merged = new_songs_count + updated_songs_count

            # Merge loadouts table
            # Upsert: if loadout exists (same song_name + loadout_hash), keep higher score
            # WORKAROUND: Python's sqlite3 doesn't support INSERT...SELECT...ON CONFLICT properly
            # Use two-step process: INSERT new loadouts, then UPDATE existing ones with better scores

            # Step 1: Insert new loadouts that don't exist in main database
            insert_new_loadouts_sql = """
                INSERT OR IGNORE INTO loadouts (
                    song_name, loadout_hash, score, fg_score,
                    gear_json, minis_json, details_json, force_details_json, timestamp
                )
                SELECT
                    song_name, loadout_hash, score, fg_score,
                    gear_json, minis_json, details_json, force_details_json, timestamp
                FROM secondary.loadouts
            """
            cursor = conn.execute(insert_new_loadouts_sql)
            new_loadouts_count = cursor.rowcount

            # Step 2: Update existing loadouts where secondary has better scores
            update_existing_loadouts_sql = """
                UPDATE loadouts
                SET
                    score = (
                        SELECT CASE
                            WHEN secondary.loadouts.score > main.loadouts.score
                            THEN secondary.loadouts.score
                            ELSE main.loadouts.score
                        END
                        FROM secondary.loadouts
                        WHERE secondary.loadouts.song_name = main.loadouts.song_name
                        AND secondary.loadouts.loadout_hash = main.loadouts.loadout_hash
                    ),
                    fg_score = (
                        SELECT CASE
                            WHEN secondary.loadouts.fg_score > main.loadouts.fg_score
                            THEN secondary.loadouts.fg_score
                            ELSE main.loadouts.fg_score
                        END
                        FROM secondary.loadouts
                        WHERE secondary.loadouts.song_name = main.loadouts.song_name
                        AND secondary.loadouts.loadout_hash = main.loadouts.loadout_hash
                    ),
                    gear_json = (
                        SELECT CASE
                            WHEN secondary.loadouts.score > main.loadouts.score
                            THEN secondary.loadouts.gear_json
                            ELSE main.loadouts.gear_json
                        END
                        FROM secondary.loadouts
                        WHERE secondary.loadouts.song_name = main.loadouts.song_name
                        AND secondary.loadouts.loadout_hash = main.loadouts.loadout_hash
                    ),
                    minis_json = (
                        SELECT CASE
                            WHEN secondary.loadouts.score > main.loadouts.score
                            THEN secondary.loadouts.minis_json
                            ELSE main.loadouts.minis_json
                        END
                        FROM secondary.loadouts
                        WHERE secondary.loadouts.song_name = main.loadouts.song_name
                        AND secondary.loadouts.loadout_hash = main.loadouts.loadout_hash
                    ),
                    details_json = (
                        SELECT CASE
                            WHEN secondary.loadouts.score > main.loadouts.score
                            THEN secondary.loadouts.details_json
                            ELSE main.loadouts.details_json
                        END
                        FROM secondary.loadouts
                        WHERE secondary.loadouts.song_name = main.loadouts.song_name
                        AND secondary.loadouts.loadout_hash = main.loadouts.loadout_hash
                    ),
                    force_details_json = (
                        SELECT CASE
                            WHEN secondary.loadouts.score > main.loadouts.score
                            THEN secondary.loadouts.force_details_json
                            ELSE main.loadouts.force_details_json
                        END
                        FROM secondary.loadouts
                        WHERE secondary.loadouts.song_name = main.loadouts.song_name
                        AND secondary.loadouts.loadout_hash = main.loadouts.loadout_hash
                    ),
                    timestamp = (
                        SELECT MAX(main.loadouts.timestamp, secondary.loadouts.timestamp)
                        FROM secondary.loadouts
                        WHERE secondary.loadouts.song_name = main.loadouts.song_name
                        AND secondary.loadouts.loadout_hash = main.loadouts.loadout_hash
                    )
                WHERE EXISTS (
                    SELECT 1 FROM secondary.loadouts
                    WHERE secondary.loadouts.song_name = main.loadouts.song_name
                    AND secondary.loadouts.loadout_hash = main.loadouts.loadout_hash
                )
            """
            cursor = conn.execute(update_existing_loadouts_sql)
            updated_loadouts_count = cursor.rowcount
            loadouts_merged = new_loadouts_count + updated_loadouts_count

            # Commit transaction
            conn.commit()

            # Detach secondary database
            conn.execute("DETACH DATABASE secondary")

            # Re-enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")

            # Optimize database after merge
            conn.execute("PRAGMA optimize")

        except Exception as e:
            conn.rollback()
            conn.close()
            return False, f"Merge failed: {str(e)}", {}
        finally:
            conn.close()

        # Get post-merge stats
        main_stats_after = get_database_stats(main_db_path)

        # Calculate merge statistics
        merge_stats = {
            'songs_before': main_stats_before['song_count'],
            'songs_after': main_stats_after['song_count'],
            'songs_added': main_stats_after['song_count'] - main_stats_before['song_count'],
            'loadouts_before': main_stats_before['loadout_count'],
            'loadouts_after': main_stats_after['loadout_count'],
            'loadouts_added': main_stats_after['loadout_count'] - main_stats_before['loadout_count'],
            'secondary_songs': secondary_stats['song_count'],
            'secondary_loadouts': secondary_stats['loadout_count'],
            'duration': time.time() - start_time,
        }

        # Delete secondary database if requested and merge was successful
        if delete_after_merge:
            try:
                os.remove(secondary_db_path)
                logging.info(f"[DB Merge] Deleted secondary database: {secondary_db_path}")
            except Exception as e:
                logging.warning(f"[DB Merge] Failed to delete secondary DB: {e}")

        # Build success message
        message = (
            f"Database merge successful! "
            f"Added {merge_stats['songs_added']} songs, {merge_stats['loadouts_added']} loadouts. "
            f"Total: {merge_stats['songs_after']} songs, {merge_stats['loadouts_after']} loadouts. "
            f"Duration: {merge_stats['duration']:.2f}s"
        )

        logging.info(f"[DB Merge] {message}")

        return True, message, merge_stats

    except Exception as e:
        error_msg = f"Unexpected error during merge: {str(e)}"
        logging.error(f"[DB Merge] {error_msg}")
        return False, error_msg, {}


def auto_merge_secondary_databases(
    delete_after_merge: bool = True,
    backup_before_merge: bool = True
) -> Tuple[bool, str]:
    """
    Automatically find and merge all secondary databases.

    This is the main entry point called by main.py on startup.
    Scans for any .db files in the same directory and merges them sequentially.

    Args:
        delete_after_merge: Whether to delete secondary DBs after successful merge
        backup_before_merge: Whether to create backup before first merge

    Returns:
        tuple: (success, message)
    """
    try:
        # Find all secondary databases
        secondary_dbs = find_secondary_databases()

        if not secondary_dbs:
            # No secondary databases found - this is normal
            logging.debug("[DB Merge] No secondary databases found")
            return True, "No secondary databases to merge"

        # Get main database path
        main_path = get_evolution_db_path()

        # Ensure main database exists and is initialized
        if not os.path.exists(main_path):
            init_db()

        # Track overall results
        total_merged = 0
        total_failed = 0
        merge_details = []

        # Merge each secondary database
        for idx, secondary_path in enumerate(secondary_dbs):
            db_name = os.path.basename(secondary_path)

            # Check if secondary database is locked or in use
            try:
                test_conn = sqlite3.connect(secondary_path, timeout=1.0)
                test_conn.execute("SELECT 1")
                test_conn.close()
            except Exception as e:
                logging.warning(f"[DB Merge] {db_name} is locked or in use: {e}")
                total_failed += 1
                merge_details.append(f"✗ {db_name} (locked)")
                continue

            # Only backup before first merge
            do_backup = backup_before_merge and idx == 0

            # Perform merge
            logging.info(f"[DB Merge] Merging {idx + 1}/{len(secondary_dbs)}: {db_name}")
            success, message, stats = merge_databases(
                main_path,
                secondary_path,
                delete_after_merge=delete_after_merge,
                backup_before_merge=do_backup
            )

            if success:
                total_merged += 1
                detail = (
                    f"✓ {db_name}: "
                    f"+{stats.get('songs_added', 0)} songs, "
                    f"+{stats.get('loadouts_added', 0)} loadouts"
                )
                merge_details.append(detail)
            else:
                total_failed += 1
                merge_details.append(f"✗ {db_name}: {message}")
                logging.error(f"[DB Merge] Failed to merge {db_name}: {message}")

        # Build summary message
        if total_merged > 0:
            summary = (
                f"Database auto-merge complete! "
                f"Merged {total_merged}/{len(secondary_dbs)} databases"
            )
            if total_failed > 0:
                summary += f" ({total_failed} failed)"

            # Add details
            details_str = "\n  ".join(merge_details)
            full_message = f"{summary}\n  {details_str}"

            logging.info(f"[DB Merge] {summary}")
            return True, full_message
        else:
            return False, f"Failed to merge any databases ({total_failed} failed)"

    except Exception as e:
        error_msg = f"Auto-merge failed: {str(e)}"
        logging.error(f"[DB Merge] {error_msg}")
        return False, error_msg
