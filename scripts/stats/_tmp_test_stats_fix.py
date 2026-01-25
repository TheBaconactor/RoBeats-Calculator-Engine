"""
Test that Stats are computed and saved correctly after the fix.
"""
import sqlite3
import json

# Run a quick optimizer pass
import os
os.environ["SONG_QUEUE_LIMIT"] = "1"  # Just one song
os.environ["GA_SEARCHDEPTH"] = "100"  # Quick run

from gear_optimizer.app import GearOptimizerApp

print("Running quick optimizer test to verify Stats persistence...")
app = GearOptimizerApp()
app.run()

# Check if Stats are populated
conn = sqlite3.connect('evolution.db')
conn.row_factory = sqlite3.Row

rows = conn.execute("""
    SELECT song_name, score, details_json
    FROM loadouts 
    ORDER BY rowid DESC
    LIMIT 3
""").fetchall()

print(f"\nChecking last {len(rows)} entries...")
success = 0
fail = 0

for row in rows:
    song = row['song_name']
    details_raw = row['details_json']
    
    if not details_raw:
        print(f"❌ {song}: details_json is NULL")
        fail += 1
        continue
    
    details = json.loads(details_raw)
    
    if 'Stats' not in details:
        print(f"❌ {song}: Stats key missing")
        fail += 1
        continue
    
    stats = details['Stats']
    
    if not stats or stats == {}:
        print(f"❌ {song}: Stats is empty dict {{}}")
        fail += 1
        continue
    
    # Check for elemental stats
    has_chill = 'Chill' in stats
    if has_chill:
        print(f"✅ {song}: Stats populated (Chill={stats['Chill']})")
        success += 1
    else:
        print(f"❌ {song}: Stats exists but missing Chill")
        fail += 1

conn.close()

print(f"\nResults: {success} success, {fail} fail")
if fail == 0:
    print("✅ FIX VERIFIED: Stats are now being saved correctly!")
else:
    print("❌ Fix incomplete or additional issues remain")
