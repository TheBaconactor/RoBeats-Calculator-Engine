import sqlite3
import os
import sys
import json

# Add project root to path for imports if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gear_optimizer.data.database import get_evolution_db_path, _load_piece_name_encoding_maps, _unpack_id_list

DB_PATH = get_evolution_db_path()
SONG_NAME = "RB Battles 2020 - The Songs [EXTENDED CUT] (Hard) by Various Artists (Arranged by AdasiekCat)"


def show_leaderboards():
    if not os.path.exists(DB_PATH):
        print("DB not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    maps = _load_piece_name_encoding_maps(conn, db_path=str(DB_PATH))

    print(f"=== LEADERBOARD: {SONG_NAME} ===\n")

    # --- BASE SCORE LEADERBOARD ---
    print(">>> BY BASE SCORE (Top 50 from 'team_buff_loadouts' table)")
    print(f"{'Rank':<5} {'Base Score':<12} {'FG Score':<12} {'Gear Summary'}")
    print("-" * 80)

    # Note: team_buff_loadouts is Base Score focused
    cursor.execute(
        """
        SELECT score, fg_score, gear_ids_blob
        FROM team_buff_loadouts 
        WHERE song_name = ? 
        ORDER BY score DESC 
        LIMIT 50
    """,
        (SONG_NAME,),
    )

    rows = cursor.fetchall()
    for i, row in enumerate(rows):
        gear_ids = _unpack_id_list(row["gear_ids_blob"])
        gear_list = [maps.gear_id_to_name.get(int(i), "") for i in gear_ids if int(i) > 0]
        gear_list = [g for g in gear_list if g]
        gear_short = ", ".join([g[:10] + ".." for g in gear_list[:2]])  # Brief summary
        print(f"{i + 1:<5} {row['score']:<12} {row['fg_score']:<12} {gear_short}")
    print("\n")

    # --- FORCE GREATS SCORE LEADERBOARD ---
    print(">>> BY FORCE GREATS SCORE (Top 50 from 'team_buff_fg_loadouts' table)")
    print(f"{'Rank':<5} {'FG Score':<12} {'Base Score':<12} {'Config Status'}")
    print("-" * 80)

    # Note: team_buff_fg_loadouts is FG Score focused
    cursor.execute(
        """
        SELECT score, fg_score, force_details_json 
        FROM team_buff_fg_loadouts 
        WHERE song_name = ? 
        ORDER BY fg_score DESC 
        LIMIT 50
    """,
        (SONG_NAME,),
    )

    rows = cursor.fetchall()
    if not rows:
        print(" [No entries in FG table yet]")

    for i, row in enumerate(rows):
        fg_score = row["fg_score"]
        score = row["score"]
        force_json = row["force_details_json"]

        config_status = "NULL (Clean)"
        if force_json:
            try:
                data = json.loads(force_json)
                details = data.get("details", {})
                if isinstance(details, dict):
                    config = details.get("ForceGreats", {}).get("config", {})
                    if config and sum(config.values()) > 0:
                        config_status = "Valid Config"
                    else:
                        config_status = "Invalid/Zero"
            except:
                config_status = "Error Parsing"

        print(f"{i + 1:<5} {fg_score:<12} {score:<12} {config_status}")

    conn.close()


if __name__ == "__main__":
    show_leaderboards()
