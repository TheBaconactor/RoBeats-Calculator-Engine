"""
Diagnostic script to compare GPU vs CPU scoring for the same loadout.
Identifies the source of the ~25% score inflation in GPU path.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from gear_optimizer.csv_parser import load_all_gears_list, load_all_minis_list, read_table
from gear_optimizer.config import load_paths_cache
from gear_optimizer.song_processor import read_song_file
from gear_optimizer.scoring import (
    solve_best_fever_combination,
    score_batch_gpu,
    get_gpu_solver,
)
from gear_optimizer.constants import TOTAL_ROWS
from gear_optimizer.helpers.ga_helpers import worker_coevolution_evaluate


def build_ref_arrays(paths):
    """Build reference arrays from Stats.csv."""
    from gear_optimizer.constants import PATHS
    stats_path = paths.get("Stats", PATHS.stats_csv)
    stats_table = read_table(stats_path)
    
    stat_names = [
        "Perfect Points",
        "Combo Multiplier", 
        "Fever Multiplier",
        "Fever Fill Rate",
        "Fever Time",
    ]
    
    ref_arrays = {}
    for i, name in enumerate(stat_names):
        arr = []
        for v in range(TOTAL_ROWS + 1):
            lookup_index = TOTAL_ROWS - v
            try:
                val = stats_table[lookup_index][i] if stats_table else 0
            except Exception:
                val = 0
            arr.append(val)
        ref_arrays[name] = np.array(arr, dtype=np.float64)
    
    return ref_arrays


def main():
    # Setup
    paths = load_paths_cache()
    ref_arrays = build_ref_arrays(paths)
    all_gears = load_all_gears_list(paths)
    all_minis = load_all_minis_list(paths)
    gears_by_name = {g["Name"]: g for g in all_gears}
    minis_by_name = {m["Name"]: m for m in all_minis}
    
    # Load a specific song for testing
    song_path = os.path.join(os.path.dirname(__file__), "..", "bin", "Euphoria.txt")
    if not os.path.exists(song_path):
        # Try alternate locations
        possible_paths = [
            r"<redacted-user-home>\Desktop\Top Secret\Beats\Gear Optimizer\Data\Hard\Euphoria (Hard) by Geoxor.txt",
            r"<redacted-user-home>\Desktop\Top Secret\Beats\Gear Optimizer\bin\Euphoria.txt",
        ]

        for p in possible_paths:
            if os.path.exists(p):
                song_path = p
                break
    
    if not os.path.exists(song_path):
        print(f"No song file found. Tried: {song_path}")
        return

    song_data = read_song_file(song_path)
    song_timestamps_np = np.array(song_data["timestamps"], dtype=np.float64)
    
    calc_song = {
        "metadata": song_data["song_details"],
        "song_data": {"timestamps": song_timestamps_np},
    }
    
    print(f"Song: {calc_song['metadata'].get('Song Name')}")
    print(f"Primary Color: {calc_song['metadata'].get('Primary Color')}")
    print(f"Secondary Color: {calc_song['metadata'].get('Secondary Color')}")
    print()
    
    # Pick a specific loadout
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
        print("Could not find all gear/minis")
        print(f"Test gear: {[g['Name'] if g else None for g in test_gear]}")
        print(f"Test minis: {[m['Name'] if m else None for m in test_minis]}")
        return
    
    genome = test_gear + test_minis
    
    # Calculate base stats
    base_stats = {"Beat": 0, "Vibe": 0, "Chill": 0, "Flow": 0, "Rush": 0,
                  "Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0,
                  "Fever Time": 0, "Fever Fill Rate": 0}
    
    for g in test_gear:
        for k in base_stats.keys():
            base_stats[k] = base_stats.get(k, 0) + g.get(k, 0)
    for m in test_minis:
        for k in base_stats.keys():
            base_stats[k] = base_stats.get(k, 0) + m.get(k, 0)
    
    print("Base stats:", base_stats)
    print()
    
    # CPU Scoring (the ground truth)
    print("=" * 60)
    print("CPU SCORING (Ground Truth)")
    print("=" * 60)
    
    cfg_cpu = {
        "use_gpu": False,
        "gem_budget": 90,
        "selected_color": calc_song["metadata"].get("Primary Color", "Rush"),
        "user_ft": 0,
        "user_ff": 0,
        "user_pp": 0,
        "user_cm": 0,
        "user_fm": 0,
        "static_elem_input": 0,
        "override_fever": None,
    }

    
    cpu_result = worker_coevolution_evaluate(
        (genome, base_stats.copy(), cfg_cpu, calc_song, ref_arrays)
    )
    cpu_score = cpu_result.get("Score", 0)
    cpu_data = cpu_result.get("Data", {})
    
    print(f"CPU Score: {cpu_score:,}")
    print(f"CPU FT: {cpu_data.get('FT')}, FF: {cpu_data.get('FF')}")
    print(f"CPU GemCounts: {cpu_data.get('GemCounts')}")
    print()
    
    # GPU Scoring
    print("=" * 60)
    print("GPU SCORING")
    print("=" * 60)
    
    cfg_gpu = {
        "use_gpu": True,
        "gem_budget": 90,
        "selected_color": calc_song["metadata"].get("Primary Color", "Rush"),
        "user_ft": 0,
        "user_ff": 0,
        "user_pp": 0,
        "user_cm": 0,
        "user_fm": 0,
        "static_elem_input": 0,
        "override_fever": None,
    }

    
    gpu_result = worker_coevolution_evaluate(
        (genome, base_stats.copy(), cfg_gpu, calc_song, ref_arrays)
    )
    gpu_score = gpu_result.get("Score", 0)
    gpu_data = gpu_result.get("Data", {})
    
    print(f"GPU Score: {gpu_score:,}")
    print(f"GPU FT: {gpu_data.get('FT')}, FF: {gpu_data.get('FF')}")
    print(f"GPU GemCounts: {gpu_data.get('GemCounts')}")
    print()
    
    # Comparison
    print("=" * 60)
    print("COMPARISON")
    print("=" * 60)
    diff = gpu_score - cpu_score
    pct = (diff / cpu_score * 100) if cpu_score else 0
    print(f"Difference: {diff:,} ({pct:.2f}%)")
    
    if abs(pct) > 1.0:
        print("\n[WARNING] GPU score differs from CPU by more than 1%!")
        print("This indicates a logic bug, not a precision issue.")
        
        # Compare stats
        print("\nDetailed stats comparison:")
        cpu_stats = cpu_data.get("Stats", {})
        gpu_stats = gpu_data.get("Stats", {})
        
        for key in sorted(set(cpu_stats.keys()) | set(gpu_stats.keys())):
            cv = cpu_stats.get(key, 0)
            gv = gpu_stats.get(key, 0)
            if cv != gv:
                print(f"  {key}: CPU={cv}, GPU={gv}, diff={gv-cv}")
    else:
        print("\n[OK] GPU and CPU scores are within expected FP32 tolerance")


if __name__ == "__main__":
    main()
