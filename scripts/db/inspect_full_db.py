import sqlite3
import os

db_path = "evolution.db"


def inspect_db():
    if not os.path.exists(db_path):
        print("DB not found.")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # 1. Schema
    print("=== SCHEMA ===")
    cursor = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name")
    for row in cursor:
        print(f"--- Table: {row['name']} ---")
        print(row["sql"])
        print("")

    # Indices
    print("=== INDICES ===")
    cursor = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL ORDER BY name")
    for row in cursor:
        print(f"Index: {row['name']}")
        print(f"{row['sql']}")
        print("")

    # 2. Tables Data
    tables = ["songs", "loadouts"]
    for t in tables:
        print(f"=== DATA SAMPLE: {t} ===")
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"Total Rows: {count}")

            row = conn.execute(f"SELECT * FROM {t} LIMIT 1").fetchone()
            if row:
                print("First Row Structure:")
                for k in row.keys():
                    val = row[k]
                    val_str = str(val)
                    if len(val_str) > 200:
                        val_str = val_str[:200] + "... (truncated)"
                    print(f"  {k} ({type(val).__name__}): {val_str}")
            else:
                print("  (Empty Table)")
        except Exception as e:
            print(f"  Error inspecting {t}: {e}")
        print("\n")

    conn.close()


if __name__ == "__main__":
    inspect_db()
