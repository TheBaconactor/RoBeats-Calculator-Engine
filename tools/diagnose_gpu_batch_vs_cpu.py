"""
Diagnostic: Compare score_batch_gpu vs CPU solve_best_fever_combination.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from gear_optimizer.csv_parser import load_all_gears_list, load_all_minis_list, read_table
from gear_optimizer.config import load_paths_cache
from gear_optimizer.song_processor import read_song_file
from gear_optimizer.scoring import solve_best_fever_combination
from gear_optimizer.helpers.ga_helpers import score_batch_gpu, SKIP_ITEM_KEYS
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
    all_gears = load_all_gears_list(paths)
    all_minis = load_all_minis_list(paths)
    gears_by_name = {g["Name"]: g for g in all_gears}
    minis_by_name = {m["Name"]: m for m in all_minis}
    
    # Load song
    song_path = r"<redacted-user-home>\Desktop\Top Secret\Beats\Gear Optimizer\Data\Hard\Euphoria (Hard) by Geoxor.txt"
    song_data = read_song_file(song_path)
    song_timestamps_np = np.array(song_data["timestamps"], dtype=np.float64)
    calc_song = {
        "metadata": song_data["song_details"],
        "song_data": {"timestamps": song_timestamps_np},
    }
    
    print(f"Song: {calc_song['metadata'].get('Song Name')}")
    print(f"Primary: {calc_song['metadata'].get('Primary Color')}")
    print(f"Secondary: {calc_song['metadata'].get('Secondary Color')}")
    
    # Build test loadout
    test_gear = [
        gears_by_name.get("Autumnal Adept's Bloom"),
        gears_by_name.get("Legendary Rush Chieftan's Beads"),
        gears_by_name.get("Legendary Rush Chieftan's Mask"),
        gears_by_name.get("Legendary Rush Chieftan's Garb"),
        gears_by_name.get("Legendary Rush Chieftan's Aura Band"),
        gears_by_name.get("Legendary Rush Chieftan's Pants"),
    ]
    test_minis = [
        minis_by_name.get("Voca-Hiku"),
        minis_by_name.get("Juggernaut"),
        minis_by_name.get("Kurante Metal Dimensions"),
    ]
    
    if None in test_gear or None in test_minis:
        print("Missing gear/minis")
        return
    
    genome = test_gear + test_minis
    
    # Calculate stats (same as worker_coevolution_evaluate)
    base_stats = {"Beat": 0, "Vibe": 0, "Chill": 0, "Flow": 0, "Rush": 0,
                  "Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0,
                  "Fever Time": 0, "Fever Fill Rate": 0}
    
    current_stats = base_stats.copy()
    for item in genome:
        for k, v in item.items():
            if k not in SKIP_ITEM_KEYS:
                current_stats[k] = current_stats.get(k, 0) + v
    
    print(f"\nAggregated stats: {current_stats}")
    
    selected_color = calc_song["metadata"].get("Primary Color", "Rush")
    
    # === CPU SCORING ===
    print("\n" + "="*60)
    print("CPU SCORING (solve_best_fever_combination)")
    print("="*60)
    
    cfg_cpu = {
        "use_gpu": False,
        "gem_budget": TOTAL_GEM_BUDGET,
        "selected_color": selected_color,
        "user_ft": 0, "user_ff": 0, "user_pp": 0, "user_cm": 0, "user_fm": 0,
        "static_elem_input": 0, "override_fever": None,
    }
    
    cpu_result = solve_best_fever_combination(
        None, current_stats.copy(), calc_song, ref_arrays,
        silent=True, override_cfg=cfg_cpu
    )
    cpu_score = cpu_result.get("Score", 0)
    print(f"CPU Score: {cpu_score:,}")
    print(f"CPU FT/FF: {cpu_result.get('FT')}/{cpu_result.get('FF')}")
    print(f"CPU GemCounts: {cpu_result.get('GemCounts')}")
    
    # === GPU BATCH SCORING ===
    print("\n" + "="*60)
    print("GPU SCORING (score_batch_gpu)")
    print("="*60)
    
    batch_payload = [{
        'stats': current_stats.copy(),
        'metadata': calc_song['metadata'],
        'song_data': calc_song['song_data'],
        'song_id': 0,
        'budget': TOTAL_GEM_BUDGET,
        'selected_color': selected_color,
    }]
    
    gpu_results = score_batch_gpu(batch_payload, ref_arrays)
    gpu_score = gpu_results[0]['Score']
    
    print(f"GPU Score: {gpu_score:,}")
    print(f"GPU FT/FF: {gpu_results[0].get('FT')}/{gpu_results[0].get('FF')}")
    print(f"GPU Gems: {gpu_results[0].get('Gems')}")

    
    # === COMPARISON ===
    print("\n" + "="*60)
    print("COMPARISON")
    print("="*60)
    diff = gpu_score - cpu_score
    pct = (diff / cpu_score * 100) if cpu_score else 0
    print(f"CPU: {cpu_score:,}")
    print(f"GPU: {gpu_score:,}")
    print(f"Diff: {diff:,} ({pct:.4f}%)")
    
    if abs(pct) > 1.0:
        print("\n[WARNING] GPU score differs by more than 1%!")
    else:
        print("\n[OK] Scores within expected tolerance")


if __name__ == "__main__":
    main()
