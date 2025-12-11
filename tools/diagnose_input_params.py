"""
Diagnostic: Dump GPU batch input parameters to verify they match CPU.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from gear_optimizer.csv_parser import read_table
from gear_optimizer.config import load_paths_cache
from gear_optimizer.song_processor import read_song_file
from gear_optimizer.scoring import solve_best_fever_combination, score_batch_gpu
from gear_optimizer.constants import TOTAL_ROWS, TOTAL_GEM_BUDGET
from gear_optimizer.helpers.ga_helpers import SKIP_ITEM_KEYS


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
    metadata = song_data["song_details"]
    
    current_stats = {
        'Beat': 0, 'Vibe': 61, 'Chill': 10, 'Flow': 0, 'Rush': 311,
        'Perfect Points': 27, 'Combo Multiplier': 66, 'Fever Multiplier': 7,
        'Fever Time': 52, 'Fever Fill Rate': 7
    }
    
    p_color = metadata.get('Primary Color', '').strip()
    s_color = metadata.get('Secondary Color', '').strip()
    selected_color = p_color  # Default
    
    print("="*70)
    print("Input Parameters")
    print("="*70)
    print(f"Song: {metadata.get('Song Name')}")
    print(f"Primary: {p_color}")
    print(f"Secondary: {s_color}")
    print(f"Selected: {selected_color}")
    print(f"\nStats: {current_stats}")
    
    def _eq(a, b):
        return a.lower() == b.lower() if a and b else False
    
    # Compute flags as score_batch_gpu does
    is_p_pp = 1 if _eq(p_color, 'Chill') else 0
    is_s_pp = 1 if _eq(s_color, 'Chill') else 0
    is_p_cm = 1 if _eq(p_color, 'Flow') else 0
    is_s_cm = 1 if _eq(s_color, 'Flow') else 0
    is_p_fm = 1 if _eq(p_color, 'Rush') else 0
    is_s_fm = 1 if _eq(s_color, 'Rush') else 0
    is_p_ov = 1 if _eq(selected_color, p_color) else 0
    is_s_ov = 1 if _eq(selected_color, s_color) else 0
    
    p_elem_is_beat = 1 if _eq(p_color, 'Beat') else 0
    p_elem_is_vibe = 1 if _eq(p_color, 'Vibe') else 0
    s_elem_is_beat = 1 if _eq(s_color, 'Beat') else 0
    s_elem_is_vibe = 1 if _eq(s_color, 'Vibe') else 0
    
    p_elem_val = current_stats.get(p_color, 0)
    s_elem_val = current_stats.get(s_color, 0)
    
    print(f"\n=== Flags ===")
    print(f"is_p_pp={is_p_pp}, is_s_pp={is_s_pp}")
    print(f"is_p_cm={is_p_cm}, is_s_cm={is_s_cm}")
    print(f"is_p_fm={is_p_fm}, is_s_fm={is_s_fm}")
    print(f"is_p_ov={is_p_ov}, is_s_ov={is_s_ov}")
    print(f"p_elem_is_beat={p_elem_is_beat}, p_elem_is_vibe={p_elem_is_vibe}")
    print(f"s_elem_is_beat={s_elem_is_beat}, s_elem_is_vibe={s_elem_is_vibe}")
    print(f"p_elem_val={p_elem_val}, s_elem_val={s_elem_val}")
    print(f"base_beat={current_stats.get('Beat', 0)}, base_vibe={current_stats.get('Vibe', 0)}")
    
    print("\n" + "="*70)
    print("CPU Solve")
    print("="*70)
    
    cfg = {
        "use_gpu": False,
        "gem_budget": TOTAL_GEM_BUDGET,
        "selected_color": selected_color,
        "user_ft": 0, "user_ff": 0, "user_pp": 0, "user_cm": 0, "user_fm": 0,
        "static_elem_input": 0, "override_fever": None,
    }
    
    result = solve_best_fever_combination(
        None, current_stats.copy(), calc_song, ref_arrays,
        silent=True, override_cfg=cfg
    )
    print(f"Score: {result.get('Score', 0):,}")
    print(f"FT/FF: {result.get('FT')}/{result.get('FF')}")
    print(f"Gems: {result.get('GemCounts', {})}")
    
    print("\n" + "="*70)
    print("GPU Batch Solve")
    print("="*70)
    
    batch_payload = [{
        'stats': current_stats.copy(),
        'metadata': calc_song['metadata'],
        'song_data': calc_song['song_data'],
        'song_id': 0,
        'budget': TOTAL_GEM_BUDGET,
        'selected_color': selected_color,
    }]
    
    gpu_results = score_batch_gpu(batch_payload, ref_arrays)
    print(f"Score: {gpu_results[0]['Score']:,}")
    print(f"FT/FF: {gpu_results[0].get('FT')}/{gpu_results[0].get('FF')}")
    print(f"Gems: {gpu_results[0].get('Gems', {})}")


if __name__ == "__main__":
    main()
