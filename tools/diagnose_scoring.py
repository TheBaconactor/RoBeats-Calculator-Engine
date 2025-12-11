"""
Diagnostic script to compare scoring behavior and identify discrepancies.

This script loads a song and compares different scoring paths to identify
where the unexpected score of 49947668 is coming from.
"""
import sys
import os
import configparser

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from gear_optimizer.song_processor import read_song_file
from gear_optimizer.csv_parser import get_fixed_stats, get_config_gear_stats, get_config_mini_stats, read_table
from gear_optimizer.scoring import (
    solve_best_fever_combination,
    evaluate_stats_score,
    fast_calculate_score,
    lookup_reference_py,
)
from gear_optimizer.fever_timeline import calculate_fever_timeline_indices
from gear_optimizer.constants import TOTAL_ROWS
from gear_optimizer.config import load_paths_cache

def load_ref_arrays(paths):
    """Load reference arrays for scoring."""
    stat_names = [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Fill Rate",
        "Fever Time",
    ]
    stats_path = paths.get("Stats", "data/Stats.csv")
    stats_table = read_table(stats_path)

    ref_arrays = {}
    for i, name in enumerate(stat_names):
        arr = []
        for v in range(TOTAL_ROWS + 1):
            lookup_index = TOTAL_ROWS - v
            try:
                val = stats_table[lookup_index][i]
            except:
                val = 0
            arr.append(val)
        ref_arrays[name] = np.array(arr, dtype=np.float64)
    return ref_arrays

def diagnose_song(song_path, config_path="config.ini"):
    """Diagnose scoring for a specific song."""
    print(f"=== DIAGNOSING SONG: {song_path} ===\n")

    # Load config
    cfg = configparser.ConfigParser()
    cfg.read(config_path, encoding="utf-8-sig")

    # Load paths
    paths = load_paths_cache()

    # Load song
    song_data = read_song_file(song_path)
    song_timestamps = np.array(song_data["timestamps"], dtype=np.float64)

    calc_song = {
        "metadata": song_data["song_details"],
        "song_data": {"timestamps": song_timestamps},
    }

    print(f"Song: {calc_song['metadata']['Song Name']}")
    print(f"Total Notes: {len(song_timestamps)}")
    print(f"Primary Color: {calc_song['metadata']['Primary Color']}")
    print(f"Secondary Color: {calc_song['metadata']['Secondary Color']}")
    print()

    # Load reference arrays
    ref_arrays = load_ref_arrays(paths)

    # Load stats
    fixed_stats = get_fixed_stats(cfg)

    # For diagnosis, load configured gear/minis
    gears_by_name = {}  # TODO: Load if needed
    minis_by_name = {}  # TODO: Load if needed
    gear_stats, gear_list = get_config_gear_stats(cfg, paths, gears_by_name)
    mini_stats, mini_list = get_config_mini_stats(cfg, paths, minis_by_name)

    # Combine stats
    combined_stats = fixed_stats.copy()
    for k, v in gear_stats.items():
        combined_stats[k] = combined_stats.get(k, 0) + v
    for k, v in mini_stats.items():
        combined_stats[k] = combined_stats.get(k, 0) + v

    print("=== STATS SUMMARY ===")
    print(f"Perfect Points: {combined_stats.get('Perfect Points', 0)}")
    print(f"Combo Multiplier: {combined_stats.get('Combo Multiplier', 0)}")
    print(f"Fever Multiplier: {combined_stats.get('Fever Multiplier', 0)}")
    print(f"Fever Time: {combined_stats.get('Fever Time', 0)}")
    print(f"Fever Fill Rate: {combined_stats.get('Fever Fill Rate', 0)}")
    p_color = calc_song['metadata']['Primary Color']
    s_color = calc_song['metadata']['Secondary Color']
    print(f"{p_color} (Primary): {combined_stats.get(p_color, 0)}")
    print(f"{s_color} (Secondary): {combined_stats.get(s_color, 0)}")
    print()

    # Test 1: Direct score evaluation (no gem optimization)
    print("=== TEST 1: Direct Score Evaluation (No Gems) ===")
    score_no_gems = evaluate_stats_score(
        combined_stats,
        calc_song,
        ref_arrays,
    )
    print(f"Score (No Gem Optimization): {score_no_gems}")
    print()

    # Test 2: With gem optimization
    print("=== TEST 2: With Gem Optimization ===")
    result = solve_best_fever_combination(
        cfg,
        combined_stats,
        calc_song,
        ref_arrays,
        silent=False,
    )
    print(f"Optimized Score: {result.get('Score', 0)}")
    print(f"FT Gems: {result.get('FT', 0)}")
    print(f"FF Gems: {result.get('FF', 0)}")
    gem_counts = result.get('GemCounts', {})
    print(f"PP Gems: {gem_counts.get('Perfect Points', 0)}")
    print(f"CM Gems: {gem_counts.get('Combo Multiplier', 0)}")
    print(f"FM Gems: {gem_counts.get('Fever Multiplier', 0)}")
    print(f"OV Gems: {gem_counts.get('Element Overflow', 0)}")
    print()

    # Test 3: Manual fever timeline calculation
    print("=== TEST 3: Manual Fever Timeline Check ===")
    total_notes = len(song_timestamps)
    long_notes = int(calc_song['metadata'].get('Long Notes', 0))
    last_note_time = float(calc_song['metadata'].get('Last Note Time', song_timestamps[-1]))

    ft_val = combined_stats.get('Fever Time', 0)
    ff_val = combined_stats.get('Fever Fill Rate', 0)

    fever_fill_factor = lookup_reference_py(ff_val, ref_arrays["Fever Fill Rate"], TOTAL_ROWS)
    fever_time_factor = lookup_reference_py(ft_val, ref_arrays["Fever Time"], TOTAL_ROWS)

    fever_mask_buffer = np.zeros(total_notes, dtype=np.bool_)
    fever_mask_head, count_body_fever, count_body_normal, fever_activations = \
        calculate_fever_timeline_indices(
            song_timestamps,
            total_notes,
            fever_fill_factor,
            fever_time_factor,
            long_notes,
            last_note_time,
            fever_mask_buffer,
        )

    print(f"Fever Activations: {fever_activations}")
    print(f"Fever Notes in Head (0-100): {np.count_nonzero(fever_mask_head)}")
    print(f"Fever Notes in Body: {count_body_fever}")
    print(f"Normal Notes in Body: {count_body_normal}")
    print(f"Total Fever Notes: {np.count_nonzero(fever_mask_head) + count_body_fever}")
    print(f"Total Notes: {total_notes}")
    print()

    # Test 4: Manual score calculation
    print("=== TEST 4: Manual Score Calculation ===")
    pp_factor = lookup_reference_py(combined_stats['Perfect Points'], ref_arrays['Perfect Points'], TOTAL_ROWS)
    combo_mul = lookup_reference_py(combined_stats['Combo Multiplier'], ref_arrays['Combo Multiplier'], TOTAL_ROWS)
    fever_mul = lookup_reference_py(combined_stats['Fever Multiplier'], ref_arrays['Fever Multiplier'], TOTAL_ROWS)

    primary_val = combined_stats.get(p_color, 0)
    secondary_val = combined_stats.get(s_color, 0)
    base_value = (primary_val * 2) + secondary_val + pp_factor

    print(f"Base Value: {base_value}")
    print(f"Combo Multiplier: {combo_mul}")
    print(f"Fever Multiplier: {fever_mul}")

    manual_score = fast_calculate_score(
        base_value,
        combo_mul,
        fever_mul,
        fever_mask_head,
        count_body_fever,
        count_body_normal,
    )
    print(f"Manual Score: {manual_score}")
    print()

    # Summary
    print("=== SUMMARY ===")
    print(f"Score (No Gems): {score_no_gems}")
    print(f"Score (Optimized): {result.get('Score', 0)}")
    print(f"Score (Manual): {manual_score}")
    print()

    if result.get('Score', 0) > 45000000:
        print("⚠️ WARNING: Score is suspiciously high (>45M)")
        print("   Expected range for most songs: 20M-42M")
        print()

    return result

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python diagnose_scoring.py <path_to_song_file>")
        print("Example: python diagnose_scoring.py 'Songs/Euphoria (Hard) by Geoxor.txt'")
        sys.exit(1)

    song_path = sys.argv[1]
    if not os.path.exists(song_path):
        print(f"Error: Song file not found: {song_path}")
        sys.exit(1)

    diagnose_song(song_path)
