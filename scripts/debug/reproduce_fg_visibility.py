import os
import sys
import sqlite3
import json

# Set env var first!
TEST_DB_PATH = "test_fg_visibility.db"
os.environ["EVOLUTION_DB_PATH"] = TEST_DB_PATH

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# NOW import database
from gear_optimizer.data.database import save_loadouts_batch, get_best_loadouts, get_db_connection, init_db
from gear_optimizer.core.constants import LOADOUTS_PER_SONG_LIMIT

# Cleanup previous run
if os.path.exists(TEST_DB_PATH):
    try:
        os.remove(TEST_DB_PATH)
    except Exception:
        pass

print(f"Initializing test DB: {TEST_DB_PATH}")
init_db()

SONG_NAME = "Test Song (Hard)"

# 1. Insert 50 "filler" loadouts with high base score, 0 FG score
print(f"Inserting {LOADOUTS_PER_SONG_LIMIT} filler loadouts...")
filler_entries = []
for i in range(LOADOUTS_PER_SONG_LIMIT):
    filler_entries.append(
        {
            "score": 1000 + i,  # High base score
            "fg_score": 0,
            "gear": [f"FillerGear{i}"],
            "minis": ["FillerMini"],
            "details": {"note": "filler"},
            "force": None,
        }
    )

save_loadouts_batch(SONG_NAME, filler_entries)

# 2. Insert 1 "target" loadout with LOW base score, but HIGH FG score
print("Inserting target loadout (Low Base, High FG)...")
target_entry = {
    "score": 500,  # Low base score (should be bottom of list)
    "fg_score": 5000,  # Huge FG score (should be kept as best FG)
    "gear": ["TargetGear"],
    "minis": ["TargetMini"],
    "details": {"note": "target"},
    "force": {"score": 5000, "details": "Awesome FG"},
}
save_loadouts_batch(SONG_NAME, [target_entry])

# 3. Retrieve best loadouts using normal API
print(f"Retrieving top {LOADOUTS_PER_SONG_LIMIT} loadouts...")
results = get_best_loadouts(SONG_NAME, limit=LOADOUTS_PER_SONG_LIMIT)

# 4. Check if target is in results
found = False
for res in results:
    if res["gear"] == ["TargetGear"]:
        found = True
        print(f"FOUND TARGET! Base: {res['score']}, FG: {res['fg_score']}")
        break

if not found:
    print("TARGET NOT FOUND in get_best_loadouts results!")
    print("Hypothesis CONFIRMED: High FG score items are hidden if base score is low.")
else:
    print("Success! Target found.")

# 5. Check if it actually exists in DB (direct query)
conn = get_db_connection(TEST_DB_PATH)
try:
    row = conn.execute("SELECT * FROM loadouts WHERE score=500").fetchone()
    if row:
        print(
            f"Target IS present in the database (verify persistence worked). Rows: {conn.execute('SELECT count(*) FROM loadouts WHERE song_name=?', (SONG_NAME,)).fetchone()[0]}"
        )
    else:
        print("Target is NOT present in the database (persistence failed).")
finally:
    conn.close()

# Cleanup
if os.path.exists(TEST_DB_PATH):
    try:
        os.remove(TEST_DB_PATH)
    except Exception:
        pass
    # verify removal
    if not os.path.exists(TEST_DB_PATH):
        print("Test DB removed.")
