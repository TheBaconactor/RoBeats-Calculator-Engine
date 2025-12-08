#!/usr/bin/env python3
"""
Temporary cleanup script to remove tie-breaker duplicates from the database.

This script:
1. Scans the database for duplicate loadouts (same score)
2. Removes tie-breakers, keeping only the best entry based on overflow
3. Creates a backup before any changes
4. Validates database integrity after cleanup

Run this once to clean existing data. Future runs will automatically
prevent duplicates via the updated save_loadouts_batch function.
"""
import os
import sys
import sqlite3
import json
import shutil
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gear_optimizer.database import (
    get_evolution_db_path,
    get_db_connection,
    _get_overflow_from_details,
)


def create_backup(db_path):
    """
    Create a backup of the database before making changes.

    Args:
        db_path: Path to database file

    Returns:
        str: Path to backup file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"
    print(f"[Backup] Creating backup: {backup_path}")
    shutil.copy2(db_path, backup_path)
    print(f"[Backup] Backup created successfully")
    return backup_path


def verify_database_integrity(db_path):
    """
    Verify database integrity using SQLite's integrity check.

    Args:
        db_path: Path to database file

    Returns:
        bool: True if database is healthy, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        conn.close()

        if result == "ok":
            print(f"[Integrity] Database integrity check: OK")
            return True
        else:
            print(f"[Integrity] Database integrity check FAILED: {result}")
            return False
    except Exception as e:
        print(f"[Integrity] Error checking database integrity: {e}")
        return False


def find_duplicate_loadouts(conn):
    """
    Find all songs with duplicate loadouts (same score).

    Args:
        conn: SQLite connection

    Returns:
        dict: Dictionary mapping song_name to list of duplicate groups
    """
    cursor = conn.execute("""
        SELECT DISTINCT name FROM songs
        ORDER BY name
    """)
    songs = [row[0] for row in cursor.fetchall()]

    duplicates = {}
    total_duplicates = 0

    for song_name in songs:
        cursor = conn.execute("""
            SELECT loadout_hash, score, details_json, fg_score
            FROM loadouts
            WHERE song_name = ?
            ORDER BY score DESC, fg_score DESC
        """, (song_name,))

        rows = cursor.fetchall()
        if not rows:
            continue

        # Group by score
        score_groups = {}
        for row in rows:
            score = row[1]  # score is at index 1
            if score not in score_groups:
                score_groups[score] = []
            score_groups[score].append({
                "loadout_hash": row[0],
                "score": row[1],
                "details_json": row[2],
                "fg_score": row[3],
            })

        # Find groups with duplicates
        song_duplicates = []
        for score, group in score_groups.items():
            if len(group) > 1:
                song_duplicates.append({
                    "score": score,
                    "count": len(group),
                    "loadouts": group,
                })
                total_duplicates += len(group) - 1  # -1 because we keep one

        if song_duplicates:
            duplicates[song_name] = song_duplicates

    print(f"\n[Scan] Found {len(duplicates)} songs with duplicates")
    print(f"[Scan] Total duplicate loadouts to remove: {total_duplicates}")

    return duplicates, total_duplicates


def cleanup_song_duplicates(conn, song_name):
    """
    Remove duplicate loadouts for a single song.

    Args:
        conn: SQLite connection
        song_name: Name of the song to clean

    Returns:
        int: Number of duplicates removed
    """
    cursor = conn.execute("""
        SELECT loadout_hash, score, details_json, fg_score
        FROM loadouts
        WHERE song_name = ?
        ORDER BY score DESC, fg_score DESC
    """, (song_name,))

    rows = cursor.fetchall()
    if not rows:
        return 0

    # Group by score
    score_groups = {}
    for row in rows:
        score = row[1]
        if score not in score_groups:
            score_groups[score] = []
        score_groups[score].append({
            "loadout_hash": row[0],
            "score": row[1],
            "details_json": row[2],
            "fg_score": row[3],
        })

    hashes_to_delete = set()

    for score, group in score_groups.items():
        if len(group) <= 1:
            continue  # No duplicates at this score level

        # Multiple loadouts with same score - keep best one based on overflow and fg_score
        loadouts_with_overflow = []
        for loadout in group:
            details = {}
            if loadout["details_json"]:
                try:
                    details = json.loads(loadout["details_json"])
                except Exception:
                    pass
            overflow = _get_overflow_from_details(details)
            loadouts_with_overflow.append({
                **loadout,
                "overflow": overflow,
            })

        # Sort by overflow (descending), then fg_score (descending)
        loadouts_with_overflow.sort(key=lambda x: (x["overflow"], x["fg_score"]), reverse=True)

        # Keep the best one, mark rest for deletion
        for loadout in loadouts_with_overflow[1:]:
            hashes_to_delete.add(loadout["loadout_hash"])

    # Delete duplicates
    if hashes_to_delete:
        placeholders = ",".join("?" * len(hashes_to_delete))
        conn.execute(f"""
            DELETE FROM loadouts
            WHERE song_name = ? AND loadout_hash IN ({placeholders})
        """, (song_name, *hashes_to_delete))
        return len(hashes_to_delete)

    return 0


def main():
    """Main cleanup function."""
    print("=" * 60)
    print("DATABASE DUPLICATE CLEANUP SCRIPT")
    print("=" * 60)
    print()

    # Get database path
    db_path = get_evolution_db_path()
    if not os.path.exists(db_path):
        print(f"[Error] Database not found: {db_path}")
        print("[Info] No cleanup needed - database doesn't exist yet")
        return

    print(f"[Database] Using database: {db_path}")

    # Step 1: Verify database integrity before changes
    print("\n[Step 1] Verifying database integrity...")
    if not verify_database_integrity(db_path):
        print("[Error] Database integrity check failed. Aborting cleanup.")
        return

    # Step 2: Create backup
    print("\n[Step 2] Creating backup...")
    backup_path = create_backup(db_path)

    # Step 3: Connect to database
    print("\n[Step 3] Connecting to database...")
    conn = get_db_connection(db_path)

    try:
        # Step 4: Scan for duplicates
        print("\n[Step 4] Scanning for duplicate loadouts...")
        duplicates, total_duplicates = find_duplicate_loadouts(conn)

        if not duplicates:
            print("\n[Success] No duplicates found! Database is already clean.")
            conn.close()
            return

        # Step 5: Show summary and ask for confirmation
        print("\n[Summary] Duplicate Analysis:")
        print("-" * 60)
        for song_name, dup_groups in list(duplicates.items())[:10]:  # Show first 10
            print(f"  {song_name}:")
            for group in dup_groups:
                print(f"    - Score {group['score']}: {group['count']} loadouts (removing {group['count'] - 1})")
        if len(duplicates) > 10:
            print(f"  ... and {len(duplicates) - 10} more songs with duplicates")
        print("-" * 60)
        print(f"\nTotal duplicates to remove: {total_duplicates}")
        print(f"Backup created at: {backup_path}")
        print()

        response = input("Proceed with cleanup? (yes/no): ").strip().lower()
        if response not in ("yes", "y"):
            print("[Cancelled] Cleanup cancelled by user")
            conn.close()
            return

        # Step 6: Clean up duplicates
        print("\n[Step 6] Cleaning up duplicates...")
        total_removed = 0
        for song_name in duplicates.keys():
            removed = cleanup_song_duplicates(conn, song_name)
            total_removed += removed
            if removed > 0:
                print(f"  {song_name}: Removed {removed} duplicates")

        conn.commit()
        print(f"\n[Success] Removed {total_removed} duplicate loadouts")

        # Step 7: Verify database integrity after changes
        print("\n[Step 7] Verifying database integrity after cleanup...")
        conn.close()
        if not verify_database_integrity(db_path):
            print("[Error] Database integrity check failed after cleanup!")
            print(f"[Recovery] Restoring from backup: {backup_path}")
            shutil.copy2(backup_path, db_path)
            print("[Recovery] Database restored from backup")
            return

        # Step 8: Run VACUUM to reclaim space
        print("\n[Step 8] Running VACUUM to reclaim space...")
        conn = get_db_connection(db_path)
        conn.execute("VACUUM")
        conn.close()
        print("[Success] Database optimized")

        # Final summary
        print("\n" + "=" * 60)
        print("CLEANUP COMPLETE")
        print("=" * 60)
        print(f"Removed: {total_removed} duplicate loadouts")
        print(f"Backup: {backup_path}")
        print("\nThe database will now automatically prevent duplicates")
        print("in future runs via the updated save_loadouts_batch function.")
        print()

    except Exception as e:
        print(f"\n[Error] Cleanup failed: {e}")
        print("[Recovery] Rolling back changes...")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        print(f"[Recovery] Restoring from backup: {backup_path}")
        shutil.copy2(backup_path, db_path)
        print("[Recovery] Database restored from backup")
        raise


if __name__ == "__main__":
    main()
