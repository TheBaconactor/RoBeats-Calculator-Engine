"""
Diagnostic: Compare CPU vs GPU score for EXACT SAME FT/FF/gems.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from gear_optimizer.csv_parser import read_table
from gear_optimizer.config import load_paths_cache
from gear_optimizer.song_processor import read_song_file
from gear_optimizer.fever_timeline import calculate_fever_timeline_indices
from gear_optimizer.scoring import fast_calculate_score, lookup_reference_py
from gear_optimizer.taichi_accelerator import init_taichi, TaichiSolver, calc_score_in_kernel
from gear_optimizer.constants import TOTAL_ROWS, TOTAL_GEM_BUDGET, FEVER_HEAD_NOTES
import taichi as ti


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
    
    ft_ref = ref_arrays["Fever Time"]
    ff_ref = ref_arrays["Fever Fill Rate"]
    ref_pp = ref_arrays["Perfect Points"]
    ref_cm = ref_arrays["Combo Multiplier"]
    ref_fm = ref_arrays["Fever Multiplier"]
    
    # Test at CPU's optimal: FT=0, FF=11
    # Test gear stats as from previous diagnostic
    test_ft = 0
    test_ff = 11
    
    # Stats after adding gear (from previous run)
    base_pp = 27  
    base_cm = 66
    base_fm = 7
    base_rush = 311  # Primary/Secondary
    
    # CPU optimal allocation: PP=0, CM=0, FM=22, OV=57
    g_pp = 0
    g_cm = 0
    g_fm = 22
    g_ov = 57
    
    from gear_optimizer.constants import GEM_SCALE_NORMAL, GEM_SCALE_FEVER, ELEMENTAL_GEM_SCALE
    
    # Final stats after gems
    final_pp = base_pp + g_pp * GEM_SCALE_NORMAL
    final_cm = base_cm + g_cm * GEM_SCALE_NORMAL
    final_fm = base_fm + g_fm * GEM_SCALE_FEVER
    final_rush = base_rush + g_ov * ELEMENTAL_GEM_SCALE
    
    # Primary=Rush, Secondary=Rush
    p_val = final_rush
    s_val = final_rush
    
    pp_lookup = lookup_reference_py(final_pp, ref_pp)
    cm_lookup = lookup_reference_py(final_cm, ref_cm)
    fm_lookup = lookup_reference_py(final_fm, ref_fm)
    
    base = (p_val * 2) + s_val + pp_lookup
    
    print(f"\n=== Scoring Parameters ===")
    print(f"FT={test_ft}, FF={test_ff}")
    print(f"PP={final_pp}, CM={final_cm}, FM={final_fm}")
    print(f"Primary={p_val}, Secondary={s_val}")
    print(f"PP_lookup={pp_lookup}, CM_lookup={cm_lookup}, FM_lookup={fm_lookup}")
    print(f"Base value: {base}")
    
    # Get fever timeline
    ft_factor = ft_ref[test_ft]
    ff_factor = ff_ref[test_ff]
    
    fever_mask_buffer = np.zeros(total_notes, dtype=np.bool_)
    fever_mask, body_fever, body_normal, _ = calculate_fever_timeline_indices(
        song_timestamps,
        total_notes,
        ff_factor,
        ft_factor,
        long_notes,
        last_note_time,
        fever_mask_buffer.copy()
    )
    
    print(f"\nFever timeline: body_fever={body_fever}, body_normal={body_normal}, head_fever={np.sum(fever_mask)}")
    
    # === CPU SCORE ===
    cpu_score = fast_calculate_score(
        base,
        cm_lookup,
        fm_lookup,
        fever_mask,
        body_fever,
        body_normal
    )
    print(f"\n=== CPU Score: {cpu_score:,} ===")
    
    # === GPU SCORE ===
    # Need to call the Taichi kernel directly with same parameters
    init_taichi()
    
    # Pack fever mask into vector of 4 i32s
    mask_packed = np.zeros(4, dtype=np.int32)
    for i in range(min(100, len(fever_mask))):
        if fever_mask[i]:
            vec_idx = i // 32
            bit_idx = i % 32
            mask_packed[vec_idx] |= (1 << bit_idx)
    
    print(f"Packed mask: {[bin(m) for m in mask_packed]}")
    
    # Create Taichi fields for test
    @ti.kernel
    def test_gpu_score(
        base_val: ti.f32,
        combo_mul: ti.f32,
        fever_mul: ti.f32,
        mask_0: ti.i32, mask_1: ti.i32, mask_2: ti.i32, mask_3: ti.i32,
        body_f: ti.i32,
        body_n: ti.i32,
        ft: ti.i32,
        ff: ti.i32,
        out_score: ti.types.ndarray()
    ):
        mask_vec = ti.Vector([mask_0, mask_1, mask_2, mask_3], dt=ti.i32)
        sc = calc_score_in_kernel(base_val, combo_mul, fever_mul, mask_vec, body_f, body_n, ft, ff)
        out_score[0] = sc
    
    out = np.zeros(1, dtype=np.int32)
    test_gpu_score(
        float(base),
        float(cm_lookup),
        float(fm_lookup),
        int(mask_packed[0]), int(mask_packed[1]), int(mask_packed[2]), int(mask_packed[3]),
        int(body_fever),
        int(body_normal),
        int(test_ft),
        int(test_ff),
        out
    )
    
    gpu_score = out[0]
    print(f"=== GPU Score: {gpu_score:,} ===")
    
    print(f"\n=== COMPARISON ===")
    print(f"CPU: {cpu_score:,}")
    print(f"GPU: {gpu_score:,}")
    diff = gpu_score - cpu_score
    pct = (diff / cpu_score * 100) if cpu_score else 0
    print(f"Diff: {diff:,} ({pct:.4f}%)")


if __name__ == "__main__":
    main()
