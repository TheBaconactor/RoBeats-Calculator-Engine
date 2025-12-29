import sqlite3
import json
import random

DB_PATH = "evolution.db"


def inspect_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    print(f"Tables found: {[t[0] for t in tables]}")
    print("-" * 20)

    for table_name in tables:
        table = table_name[0]
        if table == "sqlite_sequence":
            continue

        print(f"\nScanning Table: {table}")

        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"Total Rows: {count}")

        if count > 0:
            # Get a random sample
            cursor.execute(f"SELECT * FROM {table} ORDER BY RANDOM() LIMIT 1")
            row = cursor.fetchone()

            # Get column names
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [info[1] for info in cursor.fetchall()]

            print("Random Sample:")
            row_dict = dict(zip(columns, row))
            # Pretty print JSON fields if they exist and appear to be JSON
            for k, v in row_dict.items():
                if isinstance(v, str) and (v.startswith("{") or v.startswith("[")):
                    try:
                        parsed = json.loads(v)
                        # Truncate if too long for display
                        dumped = json.dumps(parsed, indent=2)
                        if len(dumped) > 500:
                            row_dict[k] = dumped[:500] + "... (truncated)"
                        else:
                            row_dict[k] = parsed
                    except:
                        pass

            print(json.dumps(row_dict, indent=2, default=str))
        else:
            print("Table is empty.")
        print("=" * 40)

    conn.close()


if __name__ == "__main__":
    inspect_db()
