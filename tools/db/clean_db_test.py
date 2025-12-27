"""Clean DB for Take Your Time and insert inferior record to test GA discovery."""
import os, sys
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from gear_optimizer.data.database import get_db_connection

conn = get_db_connection()
cursor = conn.cursor()

# List tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cursor.fetchall()]
print(f"Tables: {tables}")

# Find table with song data
for table in tables:
    cursor.execute(f"SELECT sql FROM sqlite_master WHERE name='{table}'")
    schema = cursor.fetchone()
    print(f"\n{table}: {schema[0][:200] if schema else 'no schema'}...")
    
# Delete data for our test song
for table in tables:
    try:
        cursor.execute(f"DELETE FROM {table} WHERE song_name LIKE '%Take Your Time%'")
        print(f"Deleted from {table}: {cursor.rowcount} rows")
    except Exception as e:
        pass

conn.commit()
print("\nDatabase cleaned for Take Your Time test.")
