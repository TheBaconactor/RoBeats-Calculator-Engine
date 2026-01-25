"""Quick test to verify FG config persistence fix."""
import sqlite3
import json
import os
import sys

db_path = "evolution.db"

print("=" * 60)
print("FG Config Persistence Test")
print("=" * 60)

# Check current DB state
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
    SELECT COUNT(*) as total,
           SUM(CASE WHEN force_details_json IS NOT NULL THEN 1 ELSE 0 END) as with_config,
           SUM(CASE WHEN fg_score > score THEN 1 ELSE 0 END) as improving
    FROM loadouts
    WHERE fg_score > 0
""")
row = cursor.fetchone()
total_fg, with_config, improving = row

print(f"\nBefore test run:")
print(f"  Total FG entries: {total_fg}")
print(f"  With FG config: {with_config}")
print(f"  FG improving: {improving}")
print(f"  Config ratio: {with_config}/{total_fg} = {(with_config/total_fg*100 if total_fg else 0):.1f}%")

# Sample a few recent entries
cursor.execute("""
    SELECT song_name, fg_score, score, 
           CASE WHEN force_details_json IS NULL THEN 'NULL' ELSE 'present' END as config_status,
           length(force_details_json) as config_len
    FROM loadouts
    WHERE fg_score > 0
    ORDER BY timestamp DESC
    LIMIT 5
""")

print("\nRecent FG entries:")
for row in cursor.fetchall():
    print(f"  {row[0][:40]}: fg={row[1]}, base={row[2]}, config={row[3]} (len={row[4]})")

conn.close()

print("\n" + "=" * 60)
print("Ready to test. Run main.py with a small queue to verify fix.")
print("Expected: force_details_json should be populated after fix")
print("=" * 60)
