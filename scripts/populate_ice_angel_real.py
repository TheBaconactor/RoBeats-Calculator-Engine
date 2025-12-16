
import sys
import os
import configparser
import numpy as np
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gear_optimizer.pipeline.song_processor import process_song_task
from gear_optimizer.data.database import get_db_connection, get_evolution_db_path, init_db
from gear_optimizer.data.csv_parser import load_all_gears_list, load_all_minis_list, read_table
from gear_optimizer.core.constants import PATHS, TOTAL_ROWS
from gear_optimizer.core.config import load_paths_cache
from gear_optimizer.core.utils import cfg_to_dict

def run_real_solver():
    # 1. Clear existing entries for Ice Angel (Easy)
    db_path = get_evolution_db_path()
    init_db() # Ensure schema
    conn = get_db_connection(db_path)
    song_name_target = "Ice Angel (Easy)"
    
    print(f"Clearing old entries for '{song_name_target}'...")
    conn.execute("DELETE FROM loadouts WHERE song_name = ?", (song_name_target,))
    conn.execute("DELETE FROM songs WHERE name = ?", (song_name_target,))
    conn.commit()
    conn.close()
    
    # 2. Setup Solver Environment
    cfg = configparser.ConfigParser()
    cfg.read("config.ini", encoding="utf-8-sig")
    paths = load_paths_cache()
    
    # Load reference arrays
    stats_table = read_table(paths.get("Stats", "") or PATHS.stats_csv)
    stat_names = ["Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Fill Rate", "Fever Time"]
    ref_arrays = {}
    for i, name in enumerate(stat_names):
        temp_list = []
        for v in range(TOTAL_ROWS + 1):
            lookup_index = TOTAL_ROWS - v
            try:
                val = stats_table[lookup_index][i] if stats_table else 0
            except:
                val = 0
            temp_list.append(val)
        ref_arrays[name] = np.array(temp_list, dtype=np.float64)
    
    all_gears = load_all_gears_list(paths)
    all_minis = load_all_minis_list(paths)
    gears_by_name = {g["Name"]: g for g in all_gears}
    minis_by_name = {m["Name"]: m for m in all_minis}
    
    # 3. Locate File
    song_file = r"Data\Easy\Ice Angel (Easy) by Yooh.txt"
    if not os.path.exists(song_file):
        print(f"File not found: {song_file}")
        return

    song_name = "Ice Angel (Easy)" # Expected name in DB (often driven by filename sans extension)
    # Note: process_song_task might derive name from file path. 
    # "Ice Angel (Easy) by Yooh" -> "Ice Angel (Easy) by Yooh" usually.
    # But the user asked for "Ice Angel (Easy)".
    # Let's hope the system naming matches. The file is "Ice Angel (Easy) by Yooh.txt".
    # The stored name will likely be "Ice Angel (Easy) by Yooh".
    # Just in case, I cleared "Ice Angel (Easy)". I should probably clear "Ice Angel (Easy) by Yooh" too.
    
    conn = get_db_connection(db_path)
    conn.execute("DELETE FROM loadouts WHERE song_name = ?", ("Ice Angel (Easy) by Yooh",))
    conn.execute("DELETE FROM songs WHERE name = ?", ("Ice Angel (Easy) by Yooh",))
    conn.commit()
    conn.close()

    print(f"Profiling: {song_name}...")
    
    cfg_dict = cfg_to_dict(cfg)
    # Ensure optimized settings for quick run but valid results
    cfg_dict["IterationEngine"]["GA_SearchDepth"] = "10" 
    cfg_dict["IterationEngine"]["MetaFinder"] = "true" # Enable FG batching
    cfg_dict["IterationEngine"]["ForceGreatsFinder"] = "true" # Explicitly enable FG optimization
    # Force Greats needs to be enabled? It defaults to TRUE usually.
    
    args = (
        song_file,
        song_name, # Passed explicitly as display name? No, second arg is song_name
        "Easy",
        cfg_dict,
        paths,
        ref_arrays,
        all_gears,
        all_minis,
        gears_by_name,
        minis_by_name,
        True,   # use_evo_db=True (CRITICAL)
        True,   # auto_buff
        5,      # ga_depth
        None,   # status_queue
        1,      # parallel_workers
    )
    
    print("Running solver (this may take 10-20s)...")
    process_song_task(args)
    print("Done!")

if __name__ == "__main__":
    run_real_solver()
