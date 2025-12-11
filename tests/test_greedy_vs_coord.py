"""
Test: Compare Greedy vs Coordinate Descent Gem Solver

This script runs the ACTUAL CPU gem solver on a real song, then
tests if coordinate descent can find a better allocation.
"""
import numpy as np
import os
import time

from gear_optimizer.scoring import (
    optimize_core_jit, fast_calculate_score, lookup_reference_jit,
    solve_best_fever_combination
)
from gear_optimizer.fever_timeline import calculate_fever_timeline_indices
from gear_optimizer.constants import (
    GEM_SCALE_NORMAL, GEM_SCALE_FEVER, MAX_STAT_INDEX,
    GEM_STAT_TO_ELEMENT_SCALE, ELEMENTAL_GEM_SCALE, TOTAL_ROWS, 
    TOTAL_GEM_BUDGET, PATHS
)
from gear_optimizer.csv_parser import read_table, load_all_gears_list, load_all_minis_list
from gear_optimizer.song_processor import read_song_file


def load_reference_arrays(script_dir):
    """Load the actual reference tables from CSV files."""
    return {
        'Perfect Points': np.array(read_table(os.path.join(script_dir, 'bin', 'Perfect Points.csv')), dtype=np.float64).flatten()[:161],
        'Combo Multiplier': np.array(read_table(os.path.join(script_dir, 'bin', 'Combo Multiplier.csv')), dtype=np.float64).flatten()[:161],
        'Fever Multiplier': np.array(read_table(os.path.join(script_dir, 'bin', 'Fever Multiplier.csv')), dtype=np.float64).flatten()[:161],
        'Fever Time': np.array(read_table(os.path.join(script_dir, 'bin', 'Fever Time.csv')), dtype=np.float64).flatten()[:161],
        'Fever Fill Rate': np.array(read_table(os.path.join(script_dir, 'bin', 'Fever Fill Rate.csv')), dtype=np.float64).flatten()[:161],
    }


def coordinate_descent_solver(
    budget, cur_pp, cur_cm, cur_fm, cur_p_val, cur_s_val,
    is_p_pp, is_s_pp, is_p_cm, is_s_cm, is_p_fm, is_s_fm, is_p_ov, is_s_ov,
    ref_pp, ref_cm, ref_fm, fever_mask_head, count_body_fever, count_body_normal,
):
    """
    Coordinate descent gem solver.
    
    Instead of greedy step-by-step, this starts from a guess and
    iteratively swaps gems between buckets to improve score.
    """
    def calc_score(pp_g, cm_g, fm_g, ov_g):
        pp_stat = min(cur_pp + pp_g * GEM_SCALE_NORMAL, MAX_STAT_INDEX)
        cm_stat = min(cur_cm + cm_g * GEM_SCALE_NORMAL, MAX_STAT_INDEX)
        fm_stat = min(cur_fm + fm_g * GEM_SCALE_FEVER, MAX_STAT_INDEX)
        
        p_val = cur_p_val
        p_val += pp_g * GEM_STAT_TO_ELEMENT_SCALE * is_p_pp
        p_val += cm_g * GEM_STAT_TO_ELEMENT_SCALE * is_p_cm
        p_val += fm_g * GEM_STAT_TO_ELEMENT_SCALE * is_p_fm
        p_val += ov_g * ELEMENTAL_GEM_SCALE * is_p_ov
        
        s_val = cur_s_val
        s_val += pp_g * GEM_STAT_TO_ELEMENT_SCALE * is_s_pp
        s_val += cm_g * GEM_STAT_TO_ELEMENT_SCALE * is_s_cm
        s_val += fm_g * GEM_STAT_TO_ELEMENT_SCALE * is_s_fm
        s_val += ov_g * ELEMENTAL_GEM_SCALE * is_s_ov
        
        pp_m = lookup_reference_jit(int(pp_stat), ref_pp, TOTAL_ROWS)
        cm_m = lookup_reference_jit(int(cm_stat), ref_cm, TOTAL_ROWS)
        fm_m = lookup_reference_jit(int(fm_stat), ref_fm, TOTAL_ROWS)
        
        base = p_val * 2 + s_val + pp_m
        return fast_calculate_score(base, cm_m, fm_m, fever_mask_head, count_body_fever, count_body_normal)
    
    # Start with balanced allocation
    max_cm = min((MAX_STAT_INDEX - cur_cm) // GEM_SCALE_NORMAL, budget)
    max_fm = min((MAX_STAT_INDEX - cur_fm) // GEM_SCALE_FEVER, budget)
    
    # Try multiple starting points
    best_alloc = (0, 0, 0, budget)  # All overflow
    best_score = calc_score(*best_alloc)
    
    for start_fm in range(0, min(max_fm + 1, budget + 1), 5):
        for start_cm in range(0, min(max_cm + 1, budget - start_fm + 1), 5):
            start_ov = budget - start_cm - start_fm
            if start_ov < 0:
                continue
            
            pp, cm, fm, ov = 0, start_cm, start_fm, start_ov
            score = calc_score(pp, cm, fm, ov)
            
            # Hill climb from this starting point
            improved = True
            while improved:
                improved = False
                for delta in [1, 2, 5]:
                    for from_t in ['pp', 'cm', 'fm', 'ov']:
                        for to_t in ['pp', 'cm', 'fm', 'ov']:
                            if from_t == to_t:
                                continue
                            
                            test = {'pp': pp, 'cm': cm, 'fm': fm, 'ov': ov}
                            if test[from_t] >= delta:
                                test[from_t] -= delta
                                test[to_t] += delta
                                
                                # Check caps
                                if test['pp'] * GEM_SCALE_NORMAL + cur_pp > MAX_STAT_INDEX:
                                    continue
                                if test['cm'] * GEM_SCALE_NORMAL + cur_cm > MAX_STAT_INDEX:
                                    continue
                                if test['fm'] * GEM_SCALE_FEVER + cur_fm > MAX_STAT_INDEX:
                                    continue
                                
                                new_score = calc_score(test['pp'], test['cm'], test['fm'], test['ov'])
                                if new_score > score:
                                    pp, cm, fm, ov = test['pp'], test['cm'], test['fm'], test['ov']
                                    score = new_score
                                    improved = True
            
            if score > best_score:
                best_score = score
                best_alloc = (pp, cm, fm, ov)
    
    # Return final stats (to match greedy's return format)
    pp_g, cm_g, fm_g, ov_g = best_alloc
    final_pp = cur_pp + pp_g * GEM_SCALE_NORMAL
    final_cm = cur_cm + cm_g * GEM_SCALE_NORMAL
    final_fm = cur_fm + fm_g * GEM_SCALE_FEVER
    
    final_p = cur_p_val
    final_p += pp_g * GEM_STAT_TO_ELEMENT_SCALE * is_p_pp
    final_p += cm_g * GEM_STAT_TO_ELEMENT_SCALE * is_p_cm
    final_p += fm_g * GEM_STAT_TO_ELEMENT_SCALE * is_p_fm
    final_p += ov_g * ELEMENTAL_GEM_SCALE * is_p_ov
    
    final_s = cur_s_val
    final_s += pp_g * GEM_STAT_TO_ELEMENT_SCALE * is_s_pp
    final_s += cm_g * GEM_STAT_TO_ELEMENT_SCALE * is_s_cm
    final_s += fm_g * GEM_STAT_TO_ELEMENT_SCALE * is_s_fm
    final_s += ov_g * ELEMENTAL_GEM_SCALE * is_s_ov
    
    return (final_pp, final_cm, final_fm, final_p, final_s, pp_g, cm_g, fm_g, ov_g)


def test_song(song_path, ref_arrays, base_stats):
    """Test greedy vs coord descent on a single song."""
    calc_song = read_song_file(song_path)
    song_meta = calc_song['song_details']
    timestamps = np.array(calc_song['timestamps'])
    total_notes = len(timestamps)
    
    if total_notes == 0:
        return None
    
    long_notes = int(song_meta.get('Long Notes', 0) or 0)
    last_note = float(song_meta.get('Last Note Time', timestamps[-1]) or timestamps[-1])
    p_color = song_meta.get('Primary Color', 'Beat')
    s_color = song_meta.get('Secondary Color', 'Vibe')
    
    # Color flags
    is_p_pp = 1 if 'Chill' == p_color else 0
    is_s_pp = 1 if 'Chill' == s_color else 0
    is_p_cm = 1 if 'Flow' == p_color else 0
    is_s_cm = 1 if 'Flow' == s_color else 0
    is_p_fm = 1 if 'Rush' == p_color else 0
    is_s_fm = 1 if 'Rush' == s_color else 0
    is_p_ov, is_s_ov = 1, 0
    
    ref_pp = ref_arrays['Perfect Points']
    ref_cm = ref_arrays['Combo Multiplier']
    ref_fm = ref_arrays['Fever Multiplier']
    ref_ft = ref_arrays['Fever Time']
    ref_ff = ref_arrays['Fever Fill Rate']
    
    # Test multiple FT/FF combinations
    results = []
    
    for ft_gems in [10, 20, 30]:
        for ff_gems in [5, 10, 15]:
            remaining_budget = TOTAL_GEM_BUDGET - ft_gems - ff_gems
            if remaining_budget <= 0:
                continue
            
            ft_stat = base_stats['Fever Time'] + ft_gems * GEM_SCALE_FEVER
            ff_stat = base_stats['Fever Fill Rate'] + ff_gems * GEM_SCALE_FEVER
            
            ft_factor = lookup_reference_jit(int(ft_stat), ref_ft, TOTAL_ROWS)
            ff_factor = lookup_reference_jit(int(ff_stat), ref_ff, TOTAL_ROWS)
            
            fever_mask_buffer = np.zeros(total_notes, dtype=np.bool_)
            fever_mask_head, count_body_fever, count_body_normal, _ = calculate_fever_timeline_indices(
                timestamps, total_notes, ff_factor, ft_factor, long_notes, last_note, fever_mask_buffer
            )
            
            cur_pp = base_stats['Perfect Points']
            cur_cm = base_stats['Combo Multiplier']
            cur_fm = base_stats['Fever Multiplier']
            cur_beat = base_stats['Beat'] + ft_gems * GEM_STAT_TO_ELEMENT_SCALE
            cur_vibe = base_stats['Vibe'] + ff_gems * GEM_STAT_TO_ELEMENT_SCALE
            
            color_map = {
                'Beat': cur_beat, 'Vibe': cur_vibe, 
                'Rush': base_stats['Rush'], 'Chill': base_stats['Chill'], 'Flow': base_stats['Flow']
            }
            cur_p_val = float(color_map.get(p_color, 0))
            cur_s_val = float(color_map.get(s_color, 0))
            
            # Run greedy
            greedy_result = optimize_core_jit(
                remaining_budget, cur_pp, cur_cm, cur_fm, cur_p_val, cur_s_val,
                is_p_pp, is_s_pp, is_p_cm, is_s_cm, is_p_fm, is_s_fm, is_p_ov, is_s_ov,
                ref_pp, ref_cm, ref_fm, fever_mask_head, count_body_fever, count_body_normal,
                GEM_SCALE_NORMAL, GEM_SCALE_FEVER, GEM_STAT_TO_ELEMENT_SCALE,
                ELEMENTAL_GEM_SCALE, TOTAL_ROWS, MAX_STAT_INDEX,
            )
            
            g_final_pp, g_final_cm, g_final_fm, g_final_p, g_final_s, g_pp, g_cm, g_fm, g_ov = greedy_result
            greedy_score = fast_calculate_score(
                g_final_p * 2 + g_final_s + lookup_reference_jit(int(g_final_pp), ref_pp, TOTAL_ROWS),
                lookup_reference_jit(int(g_final_cm), ref_cm, TOTAL_ROWS),
                lookup_reference_jit(int(g_final_fm), ref_fm, TOTAL_ROWS),
                fever_mask_head, count_body_fever, count_body_normal
            )
            
            # Run coord descent
            cd_result = coordinate_descent_solver(
                remaining_budget, cur_pp, cur_cm, cur_fm, cur_p_val, cur_s_val,
                is_p_pp, is_s_pp, is_p_cm, is_s_cm, is_p_fm, is_s_fm, is_p_ov, is_s_ov,
                ref_pp, ref_cm, ref_fm, fever_mask_head, count_body_fever, count_body_normal,
            )
            
            cd_final_pp, cd_final_cm, cd_final_fm, cd_final_p, cd_final_s, cd_pp, cd_cm, cd_fm, cd_ov = cd_result
            cd_score = fast_calculate_score(
                cd_final_p * 2 + cd_final_s + lookup_reference_jit(int(cd_final_pp), ref_pp, TOTAL_ROWS),
                lookup_reference_jit(int(cd_final_cm), ref_cm, TOTAL_ROWS),
                lookup_reference_jit(int(cd_final_fm), ref_fm, TOTAL_ROWS),
                fever_mask_head, count_body_fever, count_body_normal
            )
            
            diff = cd_score - greedy_score
            results.append({
                'ft': ft_gems, 'ff': ff_gems,
                'greedy': (g_pp, g_cm, g_fm, g_ov, greedy_score),
                'coord': (cd_pp, cd_cm, cd_fm, cd_ov, cd_score),
                'diff': diff
            })
    
    return {
        'song': os.path.basename(song_path),
        'p_color': p_color,
        's_color': s_color,
        'notes': total_notes,
        'results': results
    }


def main():
    print("=" * 70)
    print("REAL-WORLD TEST: Greedy vs Coordinate Descent Gem Solver")
    print("=" * 70)
    
    script_dir = PATHS.script_dir
    ref_arrays = load_reference_arrays(script_dir)
    
    # Base stats (simulating a mid-tier loadout)
    base_stats = {
        'Perfect Points': 60,
        'Combo Multiplier': 40,
        'Fever Multiplier': 35,
        'Beat': 200,
        'Vibe': 180,
        'Rush': 70,
        'Chill': 70,
        'Flow': 70,
        'Fever Time': 25,
        'Fever Fill Rate': 20,
    }
    
    song_dir = os.path.join(script_dir, 'Data', 'Normal')
    total_better = 0
    total_same = 0
    total_worse = 0
    total_improvement = 0
    
    songs_tested = 0
    combos_tested = 0
    
    for fname in sorted(os.listdir(song_dir))[:20]:
        if not fname.endswith('.txt'):
            continue
        
        result = test_song(os.path.join(song_dir, fname), ref_arrays, base_stats)
        if result is None:
            continue
        
        songs_tested += 1
        song_better = 0
        song_total_diff = 0
        
        for r in result['results']:
            combos_tested += 1
            if r['diff'] > 0:
                total_better += 1
                song_better += 1
            elif r['diff'] == 0:
                total_same += 1
            else:
                total_worse += 1
            
            song_total_diff += r['diff']
            total_improvement += r['diff']
        
        status = "BETTER" if song_better > 0 else "SAME"
        print(f"{result['song'][:40]:<42} P={result['p_color']:<5} {status:<6} diff={song_total_diff:+,}")
    
    print("=" * 70)
    print(f"Songs tested: {songs_tested}")
    print(f"FT/FF combos tested: {combos_tested}")
    print(f"Coord better: {total_better}, Same: {total_same}, Worse: {total_worse}")
    print(f"Total improvement: {total_improvement:+,} points")
    print("=" * 70)


if __name__ == "__main__":
    main()
