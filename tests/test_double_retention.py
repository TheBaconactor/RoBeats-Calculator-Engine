import os
import sys
import sqlite3

# Set env var first!
TEST_DB_PATH = "test_double_retention.db"
os.environ["EVOLUTION_DB_PATH"] = TEST_DB_PATH

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gear_optimizer.data.database import save_loadouts_batch, get_db_connection, init_db, LOADOUTS_PER_SONG_LIMIT

if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)

init_db()

SONG_NAME = "Double Retention Test"

# 1. Insert 50 "Raw Best" (High Base: 2000+, Low FG: 0)
print(f"Inserting {LOADOUTS_PER_SONG_LIMIT} Raw Best items...")
raw_entries = []
for i in range(LOADOUTS_PER_SONG_LIMIT):
    raw_entries.append({
        "score": 2000 + i,
        "fg_score": 0,
        "gear": [f"RawGear{i}"],
        "minis": ["RawMini"],
        "details": {},
        "force": None
    })
save_loadouts_batch(SONG_NAME, raw_entries)

# 2. Insert 50 "FG Best" (Low Base: 500, High FG: 5000+)
print(f"Inserting {LOADOUTS_PER_SONG_LIMIT} FG Best items...")
fg_entries = []
for i in range(LOADOUTS_PER_SONG_LIMIT):
    fg_entries.append({
        "score": 500,
        "fg_score": 5000 + i,
        "gear": [f"FGGear{i}"],
        "minis": ["FGMini"],
        "details": {},
        "force": {"score": 5000 + i}
    })
save_loadouts_batch(SONG_NAME, fg_entries)

# 3. Verify counts
conn = get_db_connection(TEST_DB_PATH)
total = conn.execute("SELECT count(*) FROM loadouts WHERE song_name=?", (SONG_NAME,)).fetchone()[0]
count_raw = conn.execute("SELECT count(*) FROM loadouts WHERE song_name=? AND score >= 2000", (SONG_NAME,)).fetchone()[0]
count_fg = conn.execute("SELECT count(*) FROM loadouts WHERE song_name=? AND fg_score >= 5000", (SONG_NAME,)).fetchone()[0]
conn.close()

p_limit = LOADOUTS_PER_SONG_LIMIT
print(f"Total entries: {total}")
print(f"High Raw (>2000): {count_raw}/{p_limit}")
print(f"High FG (>5000): {count_fg}/{p_limit}")

if count_raw == p_limit and count_fg == p_limit:
    print("SUCCESS: Both groups preserved completely.")
else:
    print("FAIL: Some items were deleted.")

if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)
