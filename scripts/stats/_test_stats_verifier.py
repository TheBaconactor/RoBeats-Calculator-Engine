"""
Test script to verify Stats verifier warning display.
Creates a test database with intentionally broken Stats.
"""

import sqlite3
import json
import os
import tempfile

# Create a temporary test database
test_db = tempfile.mktemp(suffix=".db")
print(f"Creating test database: {test_db}")

conn = sqlite3.connect(test_db)
conn.execute(
    """
    CREATE TABLE IF NOT EXISTS team_buff_loadouts (
        song_name TEXT,
        team_buff TEXT,
        gear_json TEXT,
        minis_json TEXT,
        details_json TEXT,
        score INTEGER,
        fg_score INTEGER
    )
    """
)

# Insert test entries with various Stats issues
test_entries = [
    # Missing Stats (None)
    ("song1", '["Gear1"]', '[["Mini1"]]', json.dumps({"GemCounts": {}}), 1000, 1000),
    # Empty Stats
    ("song2", '["Gear2"]', '[["Mini2"]]', json.dumps({"Stats": {}, "GemCounts": {}}), 2000, 2000),
    # Valid Stats
    ("song3", '["Gear3"]', '[["Mini3"]]', json.dumps({"Stats": {"Chill": 100}, "GemCounts": {}}), 3000, 3000),
]

for song, gear, minis, details, score, fg_score in test_entries:
    conn.execute(
        """
        INSERT INTO team_buff_loadouts (song_name, team_buff, gear_json, minis_json, details_json, score, fg_score)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (song, "T5", gear, minis, details, score, fg_score),
    )

conn.commit()
conn.close()

print(f"Test database created with {len(test_entries)} entries")
print(f"  - 1 entry with missing Stats")
print(f"  - 1 entry with empty Stats")
print(f"  - 1 entry with valid Stats")
print()

# Now test the verifier
import sys

sys.path.insert(0, os.path.abspath("."))

# Temporarily override DB path
original_db_env = os.environ.get("EVOLUTION_DB_PATH")
os.environ["EVOLUTION_DB_PATH"] = test_db

try:
    from gear_optimizer.data.stats_verifier import verify_and_repair_stats, print_verification_warning

    print("=" * 80)
    print("Testing verifier (dry run)...")
    print("=" * 80)
    all_valid, stats = verify_and_repair_stats(dry_run=True, verbose=True, sample_size=0)

    print()
    print(f"Result: all_valid={all_valid}")
    print(f"Stats: {stats}")
    print()

    if not all_valid:
        print("Testing warning display...")
        print_verification_warning(stats)

finally:
    # Restore original DB path
    if original_db_env:
        os.environ["EVOLUTION_DB_PATH"] = original_db_env
    else:
        os.environ.pop("EVOLUTION_DB_PATH", None)

    # Clean up test DB
    try:
        os.unlink(test_db)
        print(f"Cleaned up test database: {test_db}")
    except Exception as e:
        print(f"Note: Could not delete test database: {e}")
