import os
import sys
import sqlite3
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gear_optimizer.data.database import get_db_connection

SONG_NAME = "Feeling Alright (Hard) by Rutra"

conn = get_db_connection()
try:
    print(f"Inspecting DB: {os.environ.get('EVOLUTION_DB_PATH', 'Default')}")
    
    # Check count
    count = conn.execute("SELECT count(*) FROM loadouts WHERE song_name = ?", (SONG_NAME,)).fetchone()[0]
    print(f"Total Loadouts for '{SONG_NAME}': {count}")

    if count > 0:
        # Get all entries
        df = pd.read_sql_query("SELECT score, fg_score, loadout_hash FROM loadouts WHERE song_name = ? ORDER BY score DESC", conn, params=(SONG_NAME,))
        
        print("\nTop 5 Raw Scores:")
        print(df[["score", "fg_score"]].head(5).to_string(index=False))

        print("\nTop 5 FG Scores:")
        print(df.sort_values("fg_score", ascending=False)[["score", "fg_score"]].head(5).to_string(index=False))

        # Check for non-zero FG scores
        non_zero_fg = df[df["fg_score"] > 0]
        print(f"\nEntries with Non-Zero FG Score: {len(non_zero_fg)}")
        
        # Check intersection
        top_50_raw = df.nlargest(50, "score")
        top_50_fg = df.nlargest(50, "fg_score")
        common = len(pd.merge(top_50_raw, top_50_fg, on="loadout_hash"))
        
        print(f"Overlap between Top 50 Raw and Top 50 FG: {common}")
        
        if len(df) > 50:
            print("SUCCESS: More than 50 entries preserved (Double Retention active).")
        else:
            print("Note: Count is <= 50, possibly because distinct Raw/FG sets overlap heavily or this is the first run.")

    else:
        print("FAIL: No entries found for the song.")

finally:
    conn.close()
