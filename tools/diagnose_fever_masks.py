"""
Diagnostic: Compare GPU body_fever/body_normal with CPU at specific FT/FF values.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from gear_optimizer.csv_parser import read_table
from gear_optimizer.config import load_paths_cache
from gear_optimizer.song_processor import read_song_file
from gear_optimizer.fever_timeline import calculate_fever_timeline_indices
from gear_optimizer.taichi_accelerator import init_taichi, TaichiSolver
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
    metadata = song_data["song_details"]
    
    total_notes = len(song_timestamps)
    long_notes = int(metadata.get("Long Notes", 0))
    last_note_time = float(metadata.get("Last Note Time", song_timestamps[-1]))
    
    print(f"Song: {metadata.get('Song Name')}")
    print(f"Total Notes: {total_notes}")
    print(f"Long Notes: {long_notes}")
    print(f"Last Note Time: {last_note_time}")
    
    # Test specific FT/FF values
    test_cases = [
        (0, 11),   # CPU optimal
        (14, 0),   # GPU "optimal"
        (0, 0),    # Baseline
        (5, 5),    # Middle
    ]
    
    ft_ref = ref_arrays["Fever Time"]
    ff_ref = ref_arrays["Fever Fill Rate"]
    
    print("\n" + "="*70)
    print("CPU FEVER TIMELINE (calculate_fever_timeline_indices)")
    print("="*70)
    
    fever_mask_buffer = np.zeros(total_notes, dtype=np.bool_)
    
    for ft, ff_val in test_cases:
        ft_factor = ft_ref[ft] if ft < len(ft_ref) else 1.0
        ff_factor = ff_ref[ff_val] if ff_val < len(ff_ref) else 1.0
        
        fever_mask_buffer[:] = False
        fever_mask, body_fever, body_normal, fever_acts = calculate_fever_timeline_indices(
            song_timestamps,
            total_notes,
            ff_factor,
            ft_factor,
            long_notes,
            last_note_time,
            fever_mask_buffer.copy()
        )
        
        head_fever = np.sum(fever_mask)
        head_normal = 100 - head_fever if total_notes >= 100 else len(fever_mask) - head_fever
        
        print(f"FT={ft:2d}, FF={ff_val:2d}: body_fever={body_fever:5d}, body_normal={body_normal:5d}, head_fever={head_fever:3d}, head_normal={head_normal:3d}")
    
    # Now GPU
    print("\n" + "="*70)
    print("GPU FEVER MASKS (TaichiSolver.build_fever_masks_kernel)")
    print("="*70)
    
    init_taichi()
    solver = TaichiSolver()
    
    # Load refs and build masks
    solver.ensure_song_loaded(
        song_timestamps,
        long_notes,
        last_note_time,
        ft_ref.astype(np.float32),
        ff_ref.astype(np.float32),
        ref_arrays,
        song_key="test_song",
        range_ft_hint=TOTAL_GEM_BUDGET,
        max_ff_hint=TOTAL_GEM_BUDGET,
        total_gem_budget=TOTAL_GEM_BUDGET
    )
    
    # Fetch GPU data
    gpu_body_fever = solver.body_fever.to_numpy()
    gpu_body_normal = solver.body_normal.to_numpy()
    gpu_fever_masks = solver.fever_masks.to_numpy()
    
    for ft, ff_val in test_cases:
        bf = gpu_body_fever[ft, ff_val]
        bn = gpu_body_normal[ft, ff_val]
        
        # Unpack fever mask for head notes
        mask_packed = gpu_fever_masks[ft, :, ff_val]  # [4] values
        head_fever = 0
        for i in range(100):
            vec_idx = i // 32
            bit_idx = i % 32
            if (mask_packed[vec_idx] >> bit_idx) & 1:
                head_fever += 1
        head_normal = 100 - head_fever
        
        print(f"FT={ft:2d}, FF={ff_val:2d}: body_fever={bf:5d}, body_normal={bn:5d}, head_fever={head_fever:3d}, head_normal={head_normal:3d}")
    
    print("\n" + "="*70)
    print("COMPARISON")
    print("="*70)
    print("If GPU values differ from CPU, that's the bug!")


if __name__ == "__main__":
    main()
