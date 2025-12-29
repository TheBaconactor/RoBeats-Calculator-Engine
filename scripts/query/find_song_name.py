import sys
import os
import sqlite3

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gear_optimizer.data.database import get_evolution_db_path


def list_songs():
    db_path = get_evolution_db_path()
    if not os.path.exists(db_path):
        print(f"Database not found at: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM songs ORDER BY name")
    songs = cursor.fetchall()
    conn.close()

    print("Available songs:")
    for song in songs:
        if "Remember" in song[0]:
            print(f"FOUND: {song[0]}")
        else:
            # print(song[0]) # Commented out to avoid clutter, only looking for Remember
            pass


if __name__ == "__main__":
    list_songs()
