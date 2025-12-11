
import sys
import os
import configparser
import numpy as np
import logging

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gear_optimizer import scoring, constants, config
from gear_optimizer.csv_parser import read_table
from gear_optimizer.song_processor import scan_song_header
from gear_optimizer.utils import safe_int, safe_float
from gear_optimizer.fever_timeline import lookup_reference_py, calculate_fever_timeline_indices

# Setup Logging
logging.basicConfig(level=logging.ERROR) 
logger = logging.getLogger("GemGraph")
logger.setLevel(logging.INFO)

def main():
    print("Initializing Gem Graph Generator (Default Solver Mode)...")
    
    # 1. Load Configuration
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.ini')
    cfg = configparser.ConfigParser()
    cfg.read(config_path, encoding='utf-8-sig')
    
    paths = config.load_paths_cache()
    
    logger.info("Loading Stats Table...")
    stats_path = paths.get("Stats", "")
    if not stats_path:
        stats_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Data", "Stats.txt")
        
    stats_table = read_table(stats_path)
    
    # Pre-load Ref Arrays
    stat_names = [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Fill Rate",
        "Fever Time",
    ]
    ref_arrays = {}
    for i, name in enumerate(stat_names):
        temp_list = []
        for v in range(constants.TOTAL_ROWS + 1):
            lookup_index = constants.TOTAL_ROWS - v
            try:
                row = stats_table[lookup_index]
                val = row[i] if i < len(row) else 0
            except: val = 0
            temp_list.append(val)
        ref_arrays[name] = np.array(temp_list, dtype=np.float64)

    # 3. Load Song
    # 3. Load Songs
    target_songs = [
        "-feeding- (Hard) by naruto2413 (feat. Aya Majiro)",
        "About U (Hard) by Aiobahn & Vin [Monstercat]",
        "AfterLife (Hard) by KepoWorld",
        "Afterwars -Infection- (Hard) by Se-U-Ra",
        "AI Bomb on vocal (revision 2) (Hard) by naruto2413 (feat. Aya Majiro)"
    ]
    
    song_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Data", "Hard")
    
    for target_pattern in target_songs:
        print(f"\n--- Processing Pattern: {target_pattern} ---")
        song_path = None
        if os.path.exists(song_dir):
            for f in os.listdir(song_dir):
                if target_pattern.lower() in f.lower():
                    song_path = os.path.join(song_dir, f)
                    break
        
        if not song_path:
            # Fallback search
            root_data = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Data")
            for root, _, files in os.walk(root_data):
                for f in files:
                    if target_pattern.lower() in f.lower():
                        song_path = os.path.join(root, f)
                        break
                if song_path: break
                
        if not song_path:
            print(f"Error: Could not find '{target_pattern}'")
            continue

        print(f"Processing Song File: {song_path}")
    
        # Parse Song
        metadata = scan_song_header(song_path)
        timestamps = []
        with open(song_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            in_song_data = False
            for line in lines:
                line = line.strip()
                if not line: continue
                if line == "Song Data":
                    in_song_data = True
                    continue
                if in_song_data:
                    parts = line.split()
                    try: timestamps.append(float(parts[0]))
                    except: pass
    
        np_timestamps = np.array(timestamps, dtype=np.float64)
        calc_song = {
            "metadata": metadata,
            "song_data": {"timestamps": np_timestamps}
        }
        
        # 4. Prepare Base Stats
        user_input_section = "UserInputStatsGems"
        base_stats_config = {
            "Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0,
            "Fever Fill Rate": 0, "Fever Time": 0,
            "Chill": 0, "Flow": 0, "Rush": 0, "Beat": 0, "Vibe": 0, "None": 0
        }
        
        if cfg.has_section(user_input_section):
            for k, v in cfg.items(user_input_section):
                k = k.lower()
                val = safe_int(v)
                if k == "perfect_points": base_stats_config["Perfect Points"] = val
                elif k == "combo_multiplier": base_stats_config["Combo Multiplier"] = val
                elif k == "fever_multiplier": base_stats_config["Fever Multiplier"] = val
                elif k == "fever_fill": base_stats_config["Fever Fill Rate"] = val
                elif k == "fever_time": base_stats_config["Fever Time"] = val
                
        elem_section = "ElementalGems"
        if cfg.has_section(elem_section):
            for k, v in cfg.items(elem_section):
                key = k.capitalize()
                if key in base_stats_config:
                    base_stats_config[key] = safe_int(v)
    
        # 5. Run Sweep
        song_name_safe = os.path.basename(song_path).replace(".txt", "").replace(" ", "_")
        output_file = os.path.join(os.getcwd(), f"gem_graph_data_{song_name_safe}.txt")
        song_p_color = metadata.get("Primary Color", "Rush")
        
        # 5a. Apply Production Scales
        # Production: PP/CM=2, FM/FT/FF=3, OV=6, Sec=3
        print("Applying Production Scales: PP/CM=2, FM/FT/FF=3, OV=6")
        scoring.GEM_SCALE_NORMAL = 2
        scoring.GEM_SCALE_FEVER = 3
        scoring.ELEMENTAL_GEM_SCALE = 6
        scoring.GEM_STAT_TO_ELEMENT_SCALE = 3
        
        # Range 0 to 90 (Prod Limit)
        max_budget = 90
        
        with open(output_file, "w") as out:
            out.write("Budget,Score,FT,FF,PP,CM,FM,Elemental\n")
            
            for budget in range(max_budget + 1):
                 # Progress update
                if budget % 20 == 0:
                    print(f"Processing Budget: {budget}")
                    
                # Monkeypatch Global Budget
                scoring.TOTAL_GEM_BUDGET = budget
                
                # Setup Override to use Base Stats directly
                override = {
                    "user_ft": 0, "user_ff": 0, "user_pp": 0, "user_cm": 0, "user_fm": 0,
                    "selected_color": song_p_color,
                    "static_elem_input": 0,
                    "use_gpu": False
                }
                
                # Run Standard Solver
                try:
                    res = scoring.solve_best_fever_combination(
                        None,
                        base_stats_config.copy(),
                        calc_song,
                        ref_arrays,
                        silent=True,
                        override_cfg=override
                    )
                except Exception as e:
                    # If lookup fails due to index > 160, log it
                    print(f"Error at budget {budget}: {e}")
                    res = {}
                
                score = res.get("Score", 0)
                ft = res.get("FT", 0)
                ff = res.get("FF", 0)
                gem_counts = res.get("GemCounts", {})
                pp = gem_counts.get("Perfect Points", 0)
                cm = gem_counts.get("Combo Multiplier", 0)
                fm = gem_counts.get("Fever Multiplier", 0)
                ov = gem_counts.get("Element Overflow", 0)
                
                out.write(f"{budget},{score},{ft},{ff},{pp},{cm},{fm},{ov}\n")
                out.flush()
    
        print(f"Gem graph data generated for {song_name_safe}.")
        
        # Plot Logic
        try:
            import matplotlib.pyplot as plt
            import pandas as pd
            
            print("Generating Plot...")
            df = pd.read_csv(output_file)
            
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10), sharex=True)
            
            # Plot 1: Score
            ax1.plot(df['Budget'], df['Score'], color='black', label='Score')
            ax1.set_ylabel('Score')
            ax1.set_title(f'{target_pattern} (0-{max_budget}) [Scales: Prod]')
            ax1.grid(True)
            ax1.legend()
            
            # Plot 2: Allocation
            ax2.plot(df['Budget'], df['PP'], label='PP')
            ax2.plot(df['Budget'], df['CM'], label='CM')
            ax2.plot(df['Budget'], df['FM'], label='FM')
            ax2.plot(df['Budget'], df['Elemental'], label='Elemental')
            ax2.plot(df['Budget'], df['FT'], label='FT', linestyle='--')
            ax2.plot(df['Budget'], df['FF'], label='FF', linestyle='--')
            
            ax2.set_xlabel('Total Gem Budget')
            ax2.set_ylabel('Gem Count')
            ax2.set_title('Gem Allocation Strategy')
            ax2.legend()
            ax2.grid(True)
            
            plot_path = os.path.join(os.getcwd(), f"gem_graph_{song_name_safe}.png")
            plt.tight_layout()
            plt.savefig(plot_path)
            print(f"Plot saved to {plot_path}")
            
        except Exception as e:
            print(f"Plotting failed: {e}")
            
    print("All songs processed.")

if __name__ == "__main__":
    main()
