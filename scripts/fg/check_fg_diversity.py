import sqlite3
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gear_optimizer.data.database import get_evolution_db_path
from gear_optimizer.data.database import _load_piece_name_encoding_maps, _unpack_id_list


def check_fg_diversity(song_name_filter=None):
    db_path = get_evolution_db_path()
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    maps = _load_piece_name_encoding_maps(conn, db_path=str(db_path))

    print(f"--- Checking FG Diversity in {os.path.basename(db_path)} ---")

    # Find a song with many loadouts if not specified
    if not song_name_filter:
        print("Finding song with most loadouts...")
        row = conn.execute(
            "SELECT song_name, COUNT(*) as c FROM team_buff_loadouts GROUP BY song_name ORDER BY c DESC LIMIT 1"
        ).fetchone()
        if not row:
            print("No loadouts found.")
            return
        song_name_filter = row["song_name"]
        print(f"Selected Song: {song_name_filter} (Count: {row['c']})")

    # Query top 51 FG
    rows = conn.execute(
        """
        SELECT rowid, score, fg_score, gear_ids_blob, minis_ids_blob, loadout_hash
        FROM team_buff_loadouts
        WHERE song_name = ?
        ORDER BY fg_score DESC
        LIMIT 51
    """,
        (song_name_filter,),
    ).fetchall()

    print(f"\nTop {len(rows)} entries by FG Score:")
    print(
        f"{'#':<3} | {'RowID':<6} | {'FG Score':<10} | {'Base Score':<10} | {'Hash (First 8)':<10} | {'Gear Summary'}"
    )
    print("-" * 100)

    unique_hashes = set()
    unique_fg = set()

    for i, r in enumerate(rows):
        l_hash = r["loadout_hash"]
        unique_hashes.add(l_hash)
        unique_fg.add(r["fg_score"])

        gear_ids = _unpack_id_list(r["gear_ids_blob"])
        gear = [str(maps.gear_id_to_name.get(int(i), "") or "").strip() for i in gear_ids if int(i) > 0]
        gear = [g for g in gear if g]
        # Summarize gear (first 2 items)
        gear_sum = ", ".join(gear[:2]) + ("..." if len(gear) > 2 else "")

        print(f"{i + 1:<3} | {r['rowid']:<6} | {r['fg_score']:<10} | {r['score']:<10} | {l_hash[:8]:<10} | {gear_sum}")

    print("-" * 100)
    print(f"Unique Loadout Hashes: {len(unique_hashes)} / {len(rows)}")
    print(f"Unique FG Scores:      {len(unique_fg)} / {len(rows)}")

    if len(unique_hashes) < len(rows):
        print("\n[WARNING] Duplicate hashes found! (This implies UNIQUE constraint is missing or violated)")
    else:
        print("\n[OK] All loadouts have unique hashes.")

    if len(unique_fg) == 1 and len(rows) > 1:
        print("\n[ISSUE] All entries have IDENTICAL FG Score. This confirms the user's suspicion.")
    elif len(unique_fg) < 5:
        print("\n[INFO] Very low FG score variance.")

    conn.close()


if __name__ == "__main__":
    song = None
    if len(sys.argv) > 1:
        song = sys.argv[1]
    check_fg_diversity(song)
