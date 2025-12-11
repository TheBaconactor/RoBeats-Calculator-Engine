"""
Diagnostic: Compare CPU vs GPU scores at both optimal cells (0/11 and 14/0).
Run the full solve at specific FT/FF to see why GPU prefers 14/0.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from gear_optimizer.csv_parser import read_table
from gear_optimizer.config import load_paths_cache
from gear_optimizer.song_processor import read_song_file
from gear_optimizer.scoring import solve_best_fever_combination
from gear_optimizer.constants import TOTAL_ROWS, TOTAL_GEM_BUDGET


def build_ref_arrays(paths):
    from gear_optimizer.constants import PATHS
    stats_path = paths.get("Stats", PATHS.stats_csv)
    stats_table = read_table(stats_path)
    stat_names = ["Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Fill Rate", "Fever Time"]
    ref_arrays = {}
    for i, name in enumerate(stat_names):
        arr = []
        for v in range(TOTAL_ROWS + 1):
            lookup_index = TOTAL_ROWS - v
            try:
                val = stats_table[lookup_index][i] if stats_table else 0
            except:
                val = 0
            arr.append(val)
        ref_arrays[name] = np.array(arr, dtype=np.float64)
    return ref_arrays


def main():
    paths = load_paths_cache()
    ref_arrays = build_ref_arrays(paths)
    
    song_path = r"<redacted-user-home>\Desktop\Top Secret\Beats\Gear Optimizer\Data\Hard\Euphoria (Hard) by Geoxor.txt"
    song_data = read_song_file(song_path)
    song_timestamps = np.array(song_data["timestamps"], dtype=np.float64)
    calc_song = {
        "metadata": song_data["song_details"],
        "song_data": {"timestamps": song_timestamps},
    }
    
    # Stats from gear loadout
    current_stats = {
        'Beat': 0, 'Vibe': 61, 'Chill': 10, 'Flow': 0, 'Rush': 311,
        'Perfect Points': 27, 'Combo Multiplier': 66, 'Fever Multiplier': 7,
        'Fever Time': 52, 'Fever Fill Rate': 7
    }
    
    selected_color = "Rush"
    
    print("="*70)
    print("CPU Path - Testing at different FT/FF grid cells")
    print("="*70)
    
    # Test both cells with CPU solver by forcing override_fever
    for test_ft, test_ff in [(0, 11), (14, 0), (0, 0)]:
        cfg = {
            "use_gpu": False,
            "gem_budget": TOTAL_GEM_BUDGET,
            "selected_color": selected_color,
            "user_ft": 0, "user_ff": 0, "user_pp": 0, "user_cm": 0, "user_fm": 0,
            "static_elem_input": 0, 
            "override_fever": (test_ft, test_ff),  # Force specific FT/FF
        }
        
        result = solve_best_fever_combination(
            None, current_stats.copy(), calc_song, ref_arrays,
            silent=True, override_cfg=cfg
        )
        
        print(f"FT={test_ft:2d}, FF={test_ff:2d}: Score={result.get('Score', 0):>12,}  Gems={result.get('GemCounts', {})}")
    
    print("\n" + "="*70) 
    print("CPU Path - Full optimization (finds optimal FT/FF)")
    print("="*70)
    
    cfg_full = {
        "use_gpu": False,
        "gem_budget": TOTAL_GEM_BUDGET,
        "selected_color": selected_color,
        "user_ft": 0, "user_ff": 0, "user_pp": 0, "user_cm": 0, "user_fm": 0,
        "static_elem_input": 0, "override_fever": None,
    }
    
    result_full = solve_best_fever_combination(
        None, current_stats.copy(), calc_song, ref_arrays,
        silent=True, override_cfg=cfg_full
    )
    
    print(f"Optimal: FT={result_full.get('FT')}, FF={result_full.get('FF')}")
    print(f"Score: {result_full.get('Score', 0):,}")
    print(f"Gems: {result_full.get('GemCounts', {})}")


if __name__ == "__main__":
    main()
