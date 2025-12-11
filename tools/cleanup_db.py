"""
Database cleanup script to remove loadouts with missing/empty details_json.

This forces the optimizer to regenerate complete records on the next run.
"""

import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from gear_optimizer.database import get_evolution_db_path, json_loads
except ImportError:
    # Fallback if running standalone
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "evolution.db")
    get_evolution_db_path = lambda: DB_PATH
    import json
    json_loads = json.loads


def scan_corrupted_entries():
    """Scan database for entries with empty or missing details_json."""
    db_path = get_evolution_db_path()
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return []
    
    print(f"📂 Scanning database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Find entries with NULL, empty string, or empty JSON object details
    cursor.execute("""
        SELECT song_name, loadout_hash, score, details_json
        FROM loadouts
        WHERE details_json IS NULL 
           OR details_json = '' 
           OR details_json = '{}'
           OR details_json = 'null'
        ORDER BY score DESC
    """)
    
    corrupted = cursor.fetchall()
    conn.close()
    
    return corrupted


def scan_entries_missing_stats():
    """Scan for entries that have details_json but are missing key Stats fields."""
    db_path = get_evolution_db_path()
    
    if not os.path.exists(db_path):
        return []
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all entries with non-empty details
    cursor.execute("""
        SELECT song_name, loadout_hash, score, details_json
        FROM loadouts
        WHERE details_json IS NOT NULL 
          AND details_json != '' 
          AND details_json != '{}'
        ORDER BY score DESC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    missing_stats = []
    for row in rows:
        try:
            details = json_loads(row["details_json"])
            # Check if Stats is missing or empty
            stats = details.get("Stats", {})
            if not stats or not any(k in stats for k in ["Chill", "Vibe", "Beat", "Flow", "Rush"]):
                missing_stats.append(row)
        except Exception:
            # JSON parse error - also corrupted
            missing_stats.append(row)
    
    return missing_stats


def delete_entries(entries, dry_run=True):
    """Delete the specified entries from the database."""
    if not entries:
        return 0
    
    db_path = get_evolution_db_path()
    conn = sqlite3.connect(db_path)
    
    if dry_run:
        print(f"\n🔍 DRY RUN - Would delete {len(entries)} entries:")
        for entry in entries[:10]:  # Show first 10
            print(f"   • {entry['song_name']}: score={entry['score']:,}")
        if len(entries) > 10:
            print(f"   ... and {len(entries) - 10} more")
        conn.close()
        return 0
    
    # Actually delete
    deleted = 0
    for entry in entries:
        try:
            conn.execute(
                "DELETE FROM loadouts WHERE song_name = ? AND loadout_hash = ?",
                (entry["song_name"], entry["loadout_hash"])
            )
            deleted += 1
        except Exception as e:
            print(f"   ⚠️ Failed to delete {entry['song_name']}: {e}")
    
    conn.commit()
    conn.close()
    return deleted


def main():
    print("=" * 60)
    print("🔧 Database Cleanup Tool - Corrupted Details Finder")
    print("=" * 60)
    
    # Scan for completely empty details
    empty_details = scan_corrupted_entries()
    print(f"\n📊 Found {len(empty_details)} entries with empty/null details_json")
    
    # Scan for entries missing Stats
    missing_stats = scan_entries_missing_stats()
    print(f"📊 Found {len(missing_stats)} entries with missing Stats fields")
    
    # Combine (deduplicate by hash)
    seen = set()
    all_corrupted = []
    for entry in empty_details + missing_stats:
        key = (entry["song_name"], entry["loadout_hash"])
        if key not in seen:
            seen.add(key)
            all_corrupted.append(entry)
    
    print(f"\n🔴 Total corrupted entries: {len(all_corrupted)}")
    
    if not all_corrupted:
        print("✅ No corrupted entries found! Database is healthy.")
        return
    
    # Show affected songs
    affected_songs = set(e["song_name"] for e in all_corrupted)
    print(f"\n📋 Affected songs ({len(affected_songs)}):")
    for song in sorted(affected_songs)[:15]:
        count = sum(1 for e in all_corrupted if e["song_name"] == song)
        print(f"   • {song} ({count} entries)")
    if len(affected_songs) > 15:
        print(f"   ... and {len(affected_songs) - 15} more songs")
    
    # Dry run first
    delete_entries(all_corrupted, dry_run=True)
    
    # Ask for confirmation
    print("\n" + "=" * 60)
    response = input("🗑️  Delete these corrupted entries? (yes/no): ").strip().lower()
    
    if response == "yes":
        deleted = delete_entries(all_corrupted, dry_run=False)
        print(f"\n✅ Deleted {deleted} corrupted entries.")
        print("💡 Run the optimizer again on affected songs to regenerate complete data.")
    else:
        print("\n⏸️  Aborted. No changes made.")


if __name__ == "__main__":
    main()
