"""
Enhanced Diagnostic: Compare GPU vs CPU scoring with intermediate values.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from gear_optimizer.csv_parser import load_all_gears_list, load_all_minis_list, read_table
from gear_optimizer.config import load_paths_cache
from gear_optimizer.song_processor import read_song_file
from gear_optimizer.scoring import solve_best_fever_combination, calculate_fever_timeline_indices
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
    
    song_path = r"<redacted-user-home>\Desktop\Top Secret\Beats\Gear Optimizer\Data\Hard\Euphoria (Hard) by Geoxor.txt"
    song_data = read_song_file(song_path)
    song_timestamps_np = np.array(song_data["timestamps"], dtype=np.float64)
    calc_song = {
        "metadata": song_data["song_details"],
        "song_data": {"timestamps": song_timestamps_np},
    }
    
    print(f"Song: {calc_song['metadata'].get('Song Name')}")
    print(f"Total Notes: {len(song_timestamps_np)}")
    print(f"Long Notes: {calc_song['metadata'].get('Long Notes')}")
    print(f"Primary: {calc_song['metadata'].get('Primary Color')}")
    print(f"Secondary: {calc_song['metadata'].get('Secondary Color')}")
    
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
    
    base_stats = {"Beat": 0, "Vibe": 0, "Chill": 0, "Flow": 0, "Rush": 0,
                  "Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0,
                  "Fever Time": 0, "Fever Fill Rate": 0}
    
    current_stats = base_stats.copy()
    for item in genome:
        for k, v in item.items():
            if k not in SKIP_ITEM_KEYS:
                current_stats[k] = current_stats.get(k, 0) + v
    
    selected_color = calc_song["metadata"].get("Primary Color", "Rush")
    
    print(f"\n=== Aggregated Stats ===")
    for k, v in sorted(current_stats.items()):
        print(f"  {k}: {v}")
    
    # === CPU SCORING ===
    print("\n" + "="*60)
    print("CPU SCORING - solve_best_fever_combination")
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
    cpu_ft = cpu_result.get("FT", 0)
    cpu_ff = cpu_result.get("FF", 0)
    cpu_gems = cpu_result.get("GemCounts", {})
    
    print(f"Score: {cpu_score:,}")
    print(f"FT: {cpu_ft}, FF: {cpu_ff}")
    print(f"Gems: {cpu_gems}")
    
    # Get fever timeline for these FT/FF values
    ft_factor = ref_arrays["Fever Time"][cpu_ft] if cpu_ft < len(ref_arrays["Fever Time"]) else 1.0
    ff_factor = ref_arrays["Fever Fill Rate"][cpu_ff] if cpu_ff < len(ref_arrays["Fever Fill Rate"]) else 1.0
    
    fever_mask_buffer = np.zeros(len(song_timestamps_np), dtype=np.bool_)
    cpu_fever_mask, cpu_body_fever, cpu_body_normal, _ = calculate_fever_timeline_indices(
        song_timestamps_np,
        len(song_timestamps_np),
        ff_factor,
        ft_factor,
        calc_song['metadata'].get('Long Notes', 0),
        calc_song['metadata'].get('Last Note Time', song_timestamps_np[-1]),
        fever_mask_buffer
    )
    
    print(f"Body Fever: {cpu_body_fever}, Body Normal: {cpu_body_normal}")
    print(f"Fever Mask (first 20): {cpu_fever_mask[:20].astype(int)}")
    
    # Calculate what GPU should produce with same inputs
    g_pp = cpu_gems.get("Perfect Points", 0)
    g_cm = cpu_gems.get("Combo Multiplier", 0)
    g_fm = cpu_gems.get("Fever Multiplier", 0)
    g_ov = cpu_gems.get("Element Overflow", 0)
    
    from gear_optimizer.constants import GEM_SCALE_NORMAL, GEM_SCALE_FEVER, GEM_STAT_TO_ELEMENT_SCALE, ELEMENTAL_GEM_SCALE
    
    # Reconstruct final stats
    final_pp = current_stats.get("Perfect Points", 0) + g_pp * GEM_SCALE_NORMAL
    final_cm = current_stats.get("Combo Multiplier", 0) + g_cm * GEM_SCALE_NORMAL
    final_fm = current_stats.get("Fever Multiplier", 0) + g_fm * GEM_SCALE_FEVER
    
    final_beat = current_stats.get("Beat", 0) + cpu_ft * GEM_STAT_TO_ELEMENT_SCALE
    final_vibe = current_stats.get("Vibe", 0) + cpu_ff * GEM_STAT_TO_ELEMENT_SCALE
    final_rush = current_stats.get(selected_color, 0) + g_ov * ELEMENTAL_GEM_SCALE
    
    pp_lookup = ref_arrays["Perfect Points"][int(final_pp)]
    cm_lookup = ref_arrays["Combo Multiplier"][int(final_cm)]
    fm_lookup = ref_arrays["Fever Multiplier"][int(final_fm)]
    
    # Calculate base value (as GPU does)
    p_val = final_rush if selected_color == "Rush" else current_stats.get(selected_color, 0)
    s_val = final_rush if selected_color == "Rush" else current_stats.get(selected_color, 0)  # Same for Rush/Rush
    
    base_val = (p_val * 2.0) + s_val + pp_lookup
    
    print(f"\n=== Intermediate Values (CPU reconstructed) ===")
    print(f"Final PP stat: {final_pp}, lookup: {pp_lookup}")
    print(f"Final CM stat: {final_cm}, lookup: {cm_lookup}")  
    print(f"Final FM stat: {final_fm}, lookup: {fm_lookup}")
    print(f"Final Beat: {final_beat}, Vibe: {final_vibe}, Rush: {final_rush}")
    print(f"P_val: {p_val}, S_val: {s_val}")
    print(f"Base value: {base_val}")
    
    # === GPU BATCH ===
    print("\n" + "="*60)
    print("GPU BATCH SCORING - score_batch_gpu")
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
    gpu_res = gpu_results[0]
    gpu_score = gpu_res['Score']
    gpu_ft = gpu_res['FT']
    gpu_ff = gpu_res['FF']
    gpu_gems = gpu_res['Gems']
    
    print(f"Score: {gpu_score:,}")
    print(f"FT: {gpu_ft}, FF: {gpu_ff}")
    print(f"Gems: {gpu_gems}")
    
    # === COMPARISON ===
    print("\n" + "="*60)
    print("COMPARISON")
    print("="*60)
    print(f"CPU Score: {cpu_score:,} | FT={cpu_ft}, FF={cpu_ff}")
    print(f"GPU Score: {gpu_score:,} | FT={gpu_ft}, FF={gpu_ff}")
    print(f"Diff: {gpu_score - cpu_score:,} ({(gpu_score - cpu_score) / cpu_score * 100:.2f}%)")
    print(f"\nCPU Gems: {cpu_gems}")
    print(f"GPU Gems: {gpu_gems}")
    
    if cpu_ft != gpu_ft or cpu_ff != gpu_ff:
        print("\n[!] FT/FF differ - greedy solver found different optimal point")
    
    if cpu_gems != dict(PP=gpu_gems['PP'], CM=gpu_gems['CM'], FM=gpu_gems['FM'], OV=gpu_gems.get('OV', g_ov)):
        print("\n[!] Gem allocation differs")


if __name__ == "__main__":
    main()
