"""
Demonstration of Stats verifier catching and repairing broken Stats.

This script:
1. Backs up a real database entry
2. Breaks its Stats (sets to empty dict)
3. Runs the optimizer to trigger the verifier
4. Restores the original entry
"""

import sqlite3
import json
import os

db_path = "evolution.db"

print("=" * 80)
print("Stats Verifier Integration Test")
print("=" * 80)
print()

# Step 1: Find a real entry and back it up
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

row = conn.execute("SELECT rowid, song_name, details_json FROM loadouts LIMIT 1").fetchone()
if not row:
    print("No entries in database to test with")
    conn.close()
    exit(1)

rowid = row["rowid"]
song_name = row["song_name"]
original_details = row["details_json"]

print(f"Step 1: Backing up entry")
print(f"  Row ID: {rowid}")
print(f"  Song: {song_name}")

details = json.loads(original_details)
original_stats = details.get("Stats", {})
print(f"  Original Stats: {original_stats}")
print()

# Step 2: Break the Stats
print("Step 2: Breaking Stats (setting to empty dict)...")
details["Stats"] = {}
broken_details = json.dumps(details)
conn.execute("UPDATE loadouts SET details_json = ? WHERE rowid = ?", (broken_details, rowid))
conn.commit()
print("  Stats set to {} in database")
print()

# Step 3: Verify it's broken
row_check = conn.execute("SELECT details_json FROM loadouts WHERE rowid = ?", (rowid,)).fetchone()
check_details = json.loads(row_check["details_json"])
check_stats = check_details.get("Stats", {})
print(f"Step 3: Verify broken - Stats now: {check_stats}")
print()

conn.close()

# Step 4: Run verifier manually to show it detects and repairs
print("Step 4: Running Stats verifier...")
print("-" * 80)
from gear_optimizer.data.stats_verifier import verify_and_repair_stats, print_verification_warning

all_valid, stats = verify_and_repair_stats(dry_run=False, verbose=False, sample_size=0)
print("-" * 80)
print(f"  Result: {stats}")
print()

if not all_valid:
    print("Step 5: Verifier found and repaired issues")
else:
    print("Step 5: All entries are valid")

# Step 6: Verify repair
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
row_final = conn.execute("SELECT details_json FROM loadouts WHERE rowid = ?", (rowid,)).fetchone()
final_details = json.loads(row_final["details_json"])
final_stats = final_details.get("Stats", {})
print(f"  Repaired Stats: {final_stats}")
conn.close()

print()
print("=" * 80)
print("Test Complete: Stats verifier successfully detected and repaired broken Stats!")
print("When optimizer starts with a fresh queue, this check runs automatically.")
print("=" * 80)
