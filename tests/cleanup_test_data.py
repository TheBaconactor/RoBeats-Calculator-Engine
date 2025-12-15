import os
import sys
import sqlite3

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gear_optimizer.data.database import get_db_connection

SONG_NAME = "Test Song (Hard)"

conn = get_db_connection() # Uses default (real) DB path
print(f"Cleaning up '{SONG_NAME}' from DB...")

# Check if exists
cur = conn.execute("SELECT count(*) FROM loadouts WHERE song_name = ?", (SONG_NAME,))
count = cur.fetchone()[0]
print(f"Found {count} loadouts to delete.")

if count > 0:
    conn.execute("DELETE FROM loadouts WHERE song_name = ?", (SONG_NAME,))
    conn.execute("DELETE FROM songs WHERE name = ?", (SONG_NAME,))
    conn.commit()
    print("Deleted.")
else:
    print("Nothing to delete.")

conn.close()
