"""
Database Reader - Pulls Top 1 loadouts from the gear optimizer database.

This module connects to the existing evolution.db and retrieves
the best loadout for each song matching the filter criteria.
"""
import json
import os
import sqlite3


def get_evolution_db_path():
    """Get path to evolution database."""
    env_path = os.getenv("EVOLUTION_DB_PATH", "")
    if env_path:
        return env_path
    # Default location relative to script directory
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(script_dir, "evolution.db")


def get_top1_loadouts_for_all_songs(
    difficulty="Hard",
    target_primary="All",
    target_secondary="All",
):
    """
    Retrieve the Top 1 loadout for every song matching the filters.
    
    Args:
        difficulty: "Easy", "Normal", "Hard", or "All"
        target_primary: Primary color filter or "All"
        target_secondary: Secondary color filter or "All"
    
    Returns:
        dict: Mapping of song_name -> loadout_data
              loadout_data contains: gear (list of names), minis (list of names),
              details (gem counts), score
    """
    db_path = get_evolution_db_path()
    if not os.path.exists(db_path):
        print(f"ERROR: Database not found at {db_path}")
        return {}
    
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    
    try:
        # Get all songs with their best loadouts
        # We filter by difficulty using the song name patterns or metadata
        # For now, we'll get all songs and filter later if needed
        cursor = conn.execute("""
            SELECT 
                l.song_name,
                l.score,
                l.gear_json,
                l.minis_json,
                l.details_json
            FROM loadouts l
            INNER JOIN (
                SELECT song_name, MAX(score) as max_score
                FROM loadouts
                GROUP BY song_name
            ) best ON l.song_name = best.song_name AND l.score = best.max_score
        """)
        
        results = {}
        for row in cursor:
            song_name = row["song_name"]
            
            # Parse JSON fields
            gear_names = json.loads(row["gear_json"]) if row["gear_json"] else []
            mini_names = json.loads(row["minis_json"]) if row["minis_json"] else []
            details = json.loads(row["details_json"]) if row["details_json"] else {}
            
            # --- FILTERING ---
            # 1. Difficulty: Check against details["Difficulty"]
            song_diff = details.get("Difficulty", "Unknown").lower()
            target_diff = difficulty.lower().strip()
            
            if target_diff and target_diff != "all" and target_diff != "":
                if song_diff != target_diff:
                    continue  # Skip if difficulty doesn't match
            
            # 2. Colors: Check against details["PrimaryColor"] and ["SecondaryColor"]
            song_prim = details.get("PrimaryColor", "").lower()
            song_sec = details.get("SecondaryColor", "").lower()
            
            target_p = target_primary.lower().strip()
            target_s = target_secondary.lower().strip()
            
            # Primary Filter
            if target_p and target_p != "all":
                if song_prim != target_p:
                    continue
            
            # Secondary Filter
            if target_s and target_s != "all":
                if song_sec != target_s:
                    continue

            results[song_name] = {
                "song_name": song_name,
                "score": row["score"],
                "gear": gear_names,  # List of gear names
                "minis": mini_names,  # List of mini names
                "details": details,   # Contains GemCounts, stats, etc.
            }
        
        return results
        
    except Exception as e:
        print(f"ERROR reading database: {e}")
        return {}
    finally:
        conn.close()
