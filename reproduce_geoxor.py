import os
import sys
import numpy as np
import json

# Ensure package is resolvable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gear_optimizer.app import GearOptimizerApp
from gear_optimizer.song_processor import read_song_file
from gear_optimizer.helpers.song_helpers import setup_song_config
from gear_optimizer.scoring import worker_coevolution_evaluate
from gear_optimizer.database import get_best_loadouts

def run_geoxor_repro():
    app = GearOptimizerApp("config.ini")
    app.setup()
    
    # Target song: Euphoria (Hard) by Geoxor
    # Need to find the file
    base_dir = r"<redacted-user-home>\Desktop\Top Secret\Beats\Gear Optimizer\Data"
    song_path = None
    
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if "Euphoria" in f and "Geoxor" in f and "Hard" in f:
                song_path = os.path.join(root, f)
                break
        if song_path:
            break
            
    if not song_path:
        print("Could not find song file for Euphoria (Hard) by Geoxor")
        return

    print(f"Reading song data from {song_path}...")
    song_data = read_song_file(song_path)
    song_timestamps_np = np.array(song_data["timestamps"], dtype=np.float64)
    calc_song = {
        "metadata": song_data["song_details"],
        "song_data": {"timestamps": song_timestamps_np},
    }
    
    # Ensure AutoBuff is ON (T5 Rush likely)
    app.cfg.set("IterationEngine", "AutoBuff", "True")
    
    # Setup context
    (
        ga_settings,
        fixed_stats,
        current_gear_stats,
        current_gear_list,
        current_mini_stats,
        current_mini_list,
        meta_finder,
        enable_fever,
        enable_mini,
        enable_gear,
        force_greats_mode,
        force_greats_finder,
        force_greats_config,
        manual_force_greats,
    ) = setup_song_config(app.cfg, calc_song, True, app.paths, app.gears_by_name, app.minis_by_name)
    
    print(f"Fixed Stats: {fixed_stats}")

    # Fetch DB Record
    song_name = "Euphoria (Hard) by Geoxor"
    best_loadouts = get_best_loadouts(song_name, limit=1, gears_by_name=app.gears_by_name, minis_by_name=app.minis_by_name)
    
    if not best_loadouts:
        print("No DB record found for this song.")
        return

    db_entry = best_loadouts[0]
    print(f"DB Record Score: {db_entry['score']}")
    print(f"DB Details Used: {json.dumps(db_entry.get('details', {}).get('Stats', {}), indent=2)}")

    # Reconstruct genome
    gear_part = db_entry['gear']
    mini_part = db_entry['minis']
    genome = list(gear_part) + list(mini_part)
    
    # Evaluate
    sel_color = calc_song["metadata"].get("Primary Color", "Rush")
    cfg_data = {
        "selected_color": sel_color,
        "user_ft": 0, "user_ff": 0, "user_pp": 0, "user_cm": 0, "user_fm": 0,
        "static_elem_input": 0,
        "use_gpu": False,
    }
    
    print("\nRe-evaluating DB Loadout...")
    res = worker_coevolution_evaluate(
        (genome, fixed_stats, cfg_data, calc_song, app.ref_arrays)
    )
    
    local_score = res.get("Score", 0)
    print(f"Re-calculated Score: {local_score}")
    
    diff = db_entry['score'] - local_score
    print(f"Difference: {diff}")
    
    if diff > 100000:
        print("SIGNIFICANT DROP DETECTED!")
        # Analyze why
        # Comparison of Fixed Stats?
        # The DB entry might have details about what stats it had
        db_stats = db_entry.get('details', {}).get('Stats', {})
        
        # Compare key stats
        print("\n--- Stat Comparison ---")
        for key in ["Perfect Points", "Rush", "Beat", "Vibe", "Chill", "Flow"]:
            db_val = db_stats.get(key, 0)
            # For local run, we need to approximate the stats from the result
            # best_data -> Stats (base stats before gems)
            # The result from worker_coevolution_evaluate usually contains 'Stats' which is BASE stats of loadout + Fixed Stats
            local_stats = res.get("Stats", {})
            local_val = local_stats.get(key, 0)
            
            print(f"{key}: DB={db_val} | Local={local_val} | Diff={db_val - local_val}")
            
    else:
        print("Mismatch is negligible.")

if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()
    run_geoxor_repro()
