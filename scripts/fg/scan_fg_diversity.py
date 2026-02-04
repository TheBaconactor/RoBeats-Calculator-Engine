import sqlite3
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gear_optimizer.data.database import get_evolution_db_path


def scan_all_songs():
    db_path = get_evolution_db_path()
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    print(f"--- Scanning ALL songs in {os.path.basename(db_path)} ---")

    # Get all songs with > 1 loadout
    songs = conn.execute("SELECT song_name, COUNT(*) as c FROM team_buff_loadouts GROUP BY song_name HAVING c > 1").fetchall()

    issues_found = 0

    for s in songs:
        name = s["song_name"]

        rows = conn.execute(
            """
            SELECT fg_score, loadout_hash
            FROM team_buff_loadouts
            WHERE song_name = ?
            ORDER BY fg_score DESC
            LIMIT 51
        """,
            (name,),
        ).fetchall()

        unique_hashes = set(r["loadout_hash"] for r in rows)
        unique_fg = set(r["fg_score"] for r in rows)

        if len(unique_hashes) < len(rows):
            print(f"[ERROR] {name}: Duplicate Hashes! ({len(unique_hashes)}/{len(rows)})")
            issues_found += 1

        if len(unique_fg) == 1 and len(rows) > 5:
            print(f"[WARN]  {name}: Identical FG Scores for Top {len(rows)} ({list(unique_fg)[0]})")
            issues_found += 1

    if issues_found == 0:
        print(f"Scanned {len(songs)} songs. No diversity issues found.")
    else:
        print(f"Found {issues_found} potential issues.")

    conn.close()


if __name__ == "__main__":
    scan_all_songs()
