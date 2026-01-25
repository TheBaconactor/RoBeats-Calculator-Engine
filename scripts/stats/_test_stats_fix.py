import sqlite3
import json
import os

# Get a timestamp before the test
import time

test_start_time = time.time()

# Run optimizer with 1 song
os.environ["SONG_QUEUE_LIMIT"] = "1"
os.environ["GA_SEARCHDEPTH"] = "50"  # Quick run

print("=" * 70)
print("Running optimizer to test Stats persistence...")
print("=" * 70)

from gear_optimizer.app import GearOptimizerApp

app = GearOptimizerApp()
app.run()

print("\n" + "=" * 70)
print("Checking database for Stats...")
print("=" * 70)

# Check entries created/updated during this test
conn = sqlite3.connect("evolution.db")
conn.row_factory = sqlite3.Row

rows = conn.execute(
    """
    SELECT song_name, score, details_json, timestamp
    FROM loadouts 
    WHERE timestamp >= ?
    ORDER BY timestamp DESC
    LIMIT 5
""",
    (test_start_time,),
).fetchall()

if not rows:
    print("\n⚠️  No new entries found (test_start_time may be off or no updates)")
    # Fallback: check most recent entries
    rows = conn.execute("""
        SELECT song_name, score, details_json, timestamp
        FROM loadouts 
        ORDER BY timestamp DESC
        LIMIT 3
    """).fetchall()
    print(f"Checking {len(rows)} most recent entries instead...\n")

success_count = 0
fail_count = 0

for row in rows:
    song = row["song_name"]
    score = row["score"]
    details_raw = row["details_json"]

    print(f"\n--- {song} (Score: {score:,}) ---")

    if not details_raw:
        print("  ❌ details_json is NULL")
        fail_count += 1
        continue

    details = json.loads(details_raw)

    if "Stats" not in details:
        print("  ❌ Stats key missing in details_json")
        fail_count += 1
        continue

    stats = details["Stats"]

    if not stats or stats == {}:
        print("  ❌ Stats is EMPTY DICT {}")
        fail_count += 1
        continue

    # Check elemental stats
    elemental_stats = {k: stats.get(k, "MISSING") for k in ["Chill", "Vibe", "Beat", "Flow", "Rush"]}
    print(f"  ✅ Stats populated:")
    print(f"     Chill: {elemental_stats['Chill']}")
    print(f"     Vibe: {elemental_stats['Vibe']}")
    print(f"     Beat: {elemental_stats['Beat']}")
    print(f"     Flow: {elemental_stats['Flow']}")
    print(f"     Rush: {elemental_stats['Rush']}")
    success_count += 1

conn.close()

print("\n" + "=" * 70)
print(f"RESULTS: {success_count} success, {fail_count} fail")
print("=" * 70)

if fail_count == 0:
    print("✅ ALL ENTRIES HAVE VALID STATS!")
else:
    print(f"❌ {fail_count} entries still have empty/missing Stats")
