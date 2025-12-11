"""
Gem Solver Math Analysis - Empirical Testing

This script runs the greedy gem solver on many configurations to:
1. Analyze marginal gain patterns
2. Test if saturation heuristic produces same results
3. Identify edge cases where greedy may be suboptimal
"""
import numpy as np
import sys
import os
from collections import defaultdict
from math import floor

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gear_optimizer.solver.scoring_core import (
    optimize_core_jit,
    fast_calculate_score,
    lookup_reference_jit,
)
from gear_optimizer.core.constants import (
    GEM_SCALE_NORMAL,
    GEM_SCALE_FEVER,
    GEM_STAT_TO_ELEMENT_SCALE,
    ELEMENTAL_GEM_SCALE,
    TOTAL_ROWS,
    MAX_STAT_INDEX,
)


def create_realistic_ref_arrays():
    """Create reference arrays matching typical game values."""
    # Perfect Points: roughly 2.5 per index
    pp = np.array([i * 2.5 for i in range(161)], dtype=np.float64)
    
    # Combo Multiplier: 1.0 to ~1.8 range
    cm = np.array([1.0 + i * 0.005 for i in range(161)], dtype=np.float64)
    
    # Fever Multiplier: 1.5 to ~3.1 range
    fm = np.array([1.5 + i * 0.01 for i in range(161)], dtype=np.float64)
    
    return {"Perfect Points": pp, "Combo Multiplier": cm, "Fever Multiplier": fm}


def run_greedy_with_trace(
    budget, cur_pp, cur_cm, cur_fm, cur_p_val, cur_s_val,
    is_p_pp, is_s_pp, is_p_cm, is_s_cm, is_p_fm, is_s_fm, is_p_ov, is_s_ov,
    ref_pp, ref_cm, ref_fm, fever_mask_head, count_body_fever, count_body_normal
):
    """Run greedy solver and return trace of decisions."""
    trace = []
    gems_pp = gems_cm = gems_fm = gems_ov = 0
    
    for step in range(budget):
        best_score = -1
        best_opt = -1
        fill_budget = budget - step - 1
        fill_bonus = fill_budget * ELEMENTAL_GEM_SCALE if fill_budget > 0 else 0
        
        options = []
        
        # Option 0: PP gem
        if cur_pp < MAX_STAT_INDEX:
            t_pp = cur_pp + GEM_SCALE_NORMAL
            t_p = cur_p_val + GEM_STAT_TO_ELEMENT_SCALE * is_p_pp + fill_bonus * is_p_ov
            t_s = cur_s_val + GEM_STAT_TO_ELEMENT_SCALE * is_s_pp + fill_bonus * is_s_ov
            pp_factor = lookup_reference_jit(t_pp, ref_pp, TOTAL_ROWS)
            base = (t_p * 2) + t_s + int(pp_factor)
            c_mul = lookup_reference_jit(cur_cm, ref_cm, TOTAL_ROWS)
            f_mul = lookup_reference_jit(cur_fm, ref_fm, TOTAL_ROWS)
            score = fast_calculate_score(base, c_mul, f_mul, fever_mask_head, count_body_fever, count_body_normal)
            options.append(("PP", score))
            if score >= best_score:
                best_score = score
                best_opt = 0
        else:
            options.append(("PP", -1))  # Saturated
        
        # Option 1: CM gem
        if cur_cm < MAX_STAT_INDEX:
            t_cm = cur_cm + GEM_SCALE_NORMAL
            t_p = cur_p_val + GEM_STAT_TO_ELEMENT_SCALE * is_p_cm + fill_bonus * is_p_ov
            t_s = cur_s_val + GEM_STAT_TO_ELEMENT_SCALE * is_s_cm + fill_bonus * is_s_ov
            pp_factor = lookup_reference_jit(cur_pp, ref_pp, TOTAL_ROWS)
            base = (t_p * 2) + t_s + int(pp_factor)
            c_mul = lookup_reference_jit(t_cm, ref_cm, TOTAL_ROWS)
            f_mul = lookup_reference_jit(cur_fm, ref_fm, TOTAL_ROWS)
            score = fast_calculate_score(base, c_mul, f_mul, fever_mask_head, count_body_fever, count_body_normal)
            options.append(("CM", score))
            if score > best_score:
                best_score = score
                best_opt = 1
        else:
            options.append(("CM", -1))
        
        # Option 2: FM gem
        if cur_fm < MAX_STAT_INDEX:
            t_fm = cur_fm + GEM_SCALE_FEVER
            t_p = cur_p_val + GEM_STAT_TO_ELEMENT_SCALE * is_p_fm + fill_bonus * is_p_ov
            t_s = cur_s_val + GEM_STAT_TO_ELEMENT_SCALE * is_s_fm + fill_bonus * is_s_ov
            pp_factor = lookup_reference_jit(cur_pp, ref_pp, TOTAL_ROWS)
            base = (t_p * 2) + t_s + int(pp_factor)
            c_mul = lookup_reference_jit(cur_cm, ref_cm, TOTAL_ROWS)
            f_mul = lookup_reference_jit(t_fm, ref_fm, TOTAL_ROWS)
            score = fast_calculate_score(base, c_mul, f_mul, fever_mask_head, count_body_fever, count_body_normal)
            options.append(("FM", score))
            if score > best_score:
                best_score = score
                best_opt = 2
        else:
            options.append(("FM", -1))
        
        # Option 3: OV gem
        t_p = cur_p_val + ELEMENTAL_GEM_SCALE * is_p_ov + fill_bonus * is_p_ov
        t_s = cur_s_val + ELEMENTAL_GEM_SCALE * is_s_ov + fill_bonus * is_s_ov
        pp_factor = lookup_reference_jit(cur_pp, ref_pp, TOTAL_ROWS)
        base = (t_p * 2) + t_s + int(pp_factor)
        c_mul = lookup_reference_jit(cur_cm, ref_cm, TOTAL_ROWS)
        f_mul = lookup_reference_jit(cur_fm, ref_fm, TOTAL_ROWS)
        score = fast_calculate_score(base, c_mul, f_mul, fever_mask_head, count_body_fever, count_body_normal)
        options.append(("OV", score))
        if score >= best_score:
            best_score = score
            best_opt = 3
        
        # Apply best option
        choice = ["PP", "CM", "FM", "OV"][best_opt]
        trace.append({
            "step": step,
            "choice": choice,
            "score": best_score,
            "options": options,
            "state": (cur_pp, cur_cm, cur_fm, cur_p_val, cur_s_val),
        })
        
        if best_opt == 0:
            cur_pp += GEM_SCALE_NORMAL
            cur_p_val += GEM_STAT_TO_ELEMENT_SCALE * is_p_pp
            cur_s_val += GEM_STAT_TO_ELEMENT_SCALE * is_s_pp
            gems_pp += 1
        elif best_opt == 1:
            cur_cm += GEM_SCALE_NORMAL
            cur_p_val += GEM_STAT_TO_ELEMENT_SCALE * is_p_cm
            cur_s_val += GEM_STAT_TO_ELEMENT_SCALE * is_s_cm
            gems_cm += 1
        elif best_opt == 2:
            cur_fm += GEM_SCALE_FEVER
            cur_p_val += GEM_STAT_TO_ELEMENT_SCALE * is_p_fm
            cur_s_val += GEM_STAT_TO_ELEMENT_SCALE * is_s_fm
            gems_fm += 1
        else:
            cur_p_val += ELEMENTAL_GEM_SCALE * is_p_ov
            cur_s_val += ELEMENTAL_GEM_SCALE * is_s_ov
            gems_ov += 1
    
    return trace, (gems_pp, gems_cm, gems_fm, gems_ov)


def analyze_greedy_patterns():
    """Analyze patterns in greedy gem allocation."""
    print("=" * 70)
    print("GEM SOLVER MATH ANALYSIS - Empirical Testing")
    print("=" * 70)
    print()
    
    ref_arrays = create_realistic_ref_arrays()
    ref_pp = ref_arrays["Perfect Points"]
    ref_cm = ref_arrays["Combo Multiplier"]
    ref_fm = ref_arrays["Fever Multiplier"]
    
    # Test configurations
    test_cases = [
        # (pp, cm, fm, p_val, s_val, is_p_pp, is_s_pp, is_p_cm, is_s_cm, is_p_fm, is_s_fm, is_p_ov, is_s_ov, fever_ratio)
        # Standard case: primary=Chill (PP), secondary=Flow (CM), overflow to primary
        (80, 80, 80, 400, 300, 1, 0, 0, 1, 0, 0, 1, 0, 0.4, "Standard"),
        # High starting stats (near saturation)
        (150, 150, 150, 600, 500, 1, 0, 0, 1, 0, 0, 1, 0, 0.5, "Near Sat"),
        # Low fever song
        (80, 80, 80, 400, 300, 1, 0, 0, 1, 0, 0, 1, 0, 0.1, "Low Fever"),
        # High fever song
        (80, 80, 80, 400, 300, 1, 0, 0, 1, 0, 0, 1, 0, 0.8, "High Fever"),
        # Overflow to secondary
        (80, 80, 80, 400, 300, 1, 0, 0, 1, 0, 0, 0, 1, 0.4, "OV->Secondary"),
        # No color matches (pure stat gems)
        (80, 80, 80, 400, 300, 0, 0, 0, 0, 0, 0, 1, 0, 0.4, "No Match"),
    ]
    
    budget = 35  # Typical remaining budget after FT/FF allocation
    
    allocation_patterns = defaultdict(int)
    
    for pp, cm, fm, p_val, s_val, is_p_pp, is_s_pp, is_p_cm, is_s_cm, is_p_fm, is_s_fm, is_p_ov, is_s_ov, fever_ratio, name in test_cases:
        print(f"\n{'='*60}")
        print(f"Test Case: {name}")
        print(f"  Starting: PP={pp}, CM={cm}, FM={fm}, P={p_val}, S={s_val}")
        print(f"  Colors: is_p_pp={is_p_pp}, is_s_cm={is_s_cm}, is_p_ov={is_p_ov}")
        print(f"  Fever ratio: {fever_ratio:.0%}")
        print("-" * 60)
        
        # Create fever mask based on ratio
        fever_mask_head = np.array([i % int(1/fever_ratio) == 0 for i in range(100)] if fever_ratio > 0 else [False]*100, dtype=np.bool_)
        count_body_fever = int(300 * fever_ratio)
        count_body_normal = 300 - count_body_fever
        
        trace, allocation = run_greedy_with_trace(
            budget, pp, cm, fm, p_val, s_val,
            is_p_pp, is_s_pp, is_p_cm, is_s_cm, is_p_fm, is_s_fm, is_p_ov, is_s_ov,
            ref_pp, ref_cm, ref_fm, fever_mask_head, count_body_fever, count_body_normal
        )
        
        gems_pp, gems_cm, gems_fm, gems_ov = allocation
        print(f"\nFinal Allocation: PP={gems_pp}, CM={gems_cm}, FM={gems_fm}, OV={gems_ov}")
        print(f"Final Score: {trace[-1]['score']:,}")
        
        # Record pattern
        pattern_key = f"PP:{gems_pp//5*5}-{gems_pp//5*5+4},CM:{gems_cm//5*5}-{gems_cm//5*5+4},FM:{gems_fm//5*5}-{gems_fm//5*5+4},OV:{gems_ov//5*5}-{gems_ov//5*5+4}"
        allocation_patterns[pattern_key] += 1
        
        # Show first 5 decisions
        print("\nFirst 5 decisions:")
        for t in trace[:5]:
            opts = ", ".join([f"{o[0]}={o[1]:,}" if o[1] > 0 else f"{o[0]}=SAT" for o in t["options"]])
            print(f"  Step {t['step']:2d}: chose {t['choice']} | options: {opts}")
        
        # Analyze if there's a clear saturation pattern
        fm_saturated = None
        cm_saturated = None
        pp_saturated = None
        
        for t in trace:
            state = t["state"]
            if state[2] >= MAX_STAT_INDEX and fm_saturated is None:
                fm_saturated = t["step"]
            if state[1] >= MAX_STAT_INDEX and cm_saturated is None:
                cm_saturated = t["step"]
            if state[0] >= MAX_STAT_INDEX and pp_saturated is None:
                pp_saturated = t["step"]
        
        print(f"\nSaturation points: FM@{fm_saturated}, CM@{cm_saturated}, PP@{pp_saturated}")
    
    print("\n" + "=" * 70)
    print("PATTERN SUMMARY")
    print("=" * 70)
    for pattern, count in sorted(allocation_patterns.items()):
        print(f"  {pattern}: {count} occurrences")


def test_saturation_heuristic():
    """Test if simple saturation heuristic matches greedy."""
    print("\n" + "=" * 70)
    print("SATURATION HEURISTIC TEST")
    print("=" * 70)
    
    ref_arrays = create_realistic_ref_arrays()
    ref_pp = ref_arrays["Perfect Points"]
    ref_cm = ref_arrays["Combo Multiplier"]
    ref_fm = ref_arrays["Fever Multiplier"]
    
    np.random.seed(42)
    matches = 0
    mismatches = 0
    
    for _ in range(100):
        # Random configuration
        pp = np.random.randint(60, 140)
        cm = np.random.randint(60, 140)
        fm = np.random.randint(60, 140)
        p_val = np.random.randint(300, 700)
        s_val = np.random.randint(200, 500)
        
        # Random color setup
        is_p_pp = np.random.choice([0, 1])
        is_s_pp = 1 - is_p_pp if np.random.random() < 0.3 else 0
        is_p_cm = np.random.choice([0, 1])
        is_s_cm = 1 - is_p_cm if np.random.random() < 0.3 else 0
        is_p_fm = 0  # FM rarely matches primary/secondary
        is_s_fm = 0
        is_p_ov = np.random.choice([0, 1])
        is_s_ov = 1 - is_p_ov
        
        budget = np.random.randint(20, 50)
        fever_ratio = np.random.uniform(0.2, 0.7)
        
        fever_mask_head = np.array([i < int(100 * fever_ratio) for i in range(100)], dtype=np.bool_)
        count_body_fever = int(300 * fever_ratio)
        count_body_normal = 300 - count_body_fever
        
        # Run greedy
        trace, greedy_alloc = run_greedy_with_trace(
            budget, pp, cm, fm, p_val, s_val,
            is_p_pp, is_s_pp, is_p_cm, is_s_cm, is_p_fm, is_s_fm, is_p_ov, is_s_ov,
            ref_pp, ref_cm, ref_fm, fever_mask_head, count_body_fever, count_body_normal
        )
        greedy_score = trace[-1]["score"]
        
        # Saturation heuristic: FM -> CM -> fill with OV/PP
        heur_fm = min(budget, (MAX_STAT_INDEX - fm) // GEM_SCALE_FEVER)
        remaining = budget - heur_fm
        heur_cm = min(remaining, (MAX_STAT_INDEX - cm) // GEM_SCALE_NORMAL)
        remaining -= heur_cm
        heur_pp = 0
        heur_ov = remaining  # All to overflow
        
        # Calculate heuristic score
        final_pp = pp + heur_pp * GEM_SCALE_NORMAL
        final_cm = cm + heur_cm * GEM_SCALE_NORMAL
        final_fm = fm + heur_fm * GEM_SCALE_FEVER
        final_p_val = p_val + heur_pp * GEM_STAT_TO_ELEMENT_SCALE * is_p_pp + \
                      heur_cm * GEM_STAT_TO_ELEMENT_SCALE * is_p_cm + \
                      heur_fm * GEM_STAT_TO_ELEMENT_SCALE * is_p_fm + \
                      heur_ov * ELEMENTAL_GEM_SCALE * is_p_ov
        final_s_val = s_val + heur_pp * GEM_STAT_TO_ELEMENT_SCALE * is_s_pp + \
                      heur_cm * GEM_STAT_TO_ELEMENT_SCALE * is_s_cm + \
                      heur_fm * GEM_STAT_TO_ELEMENT_SCALE * is_s_fm + \
                      heur_ov * ELEMENTAL_GEM_SCALE * is_s_ov
        
        pp_factor = lookup_reference_jit(final_pp, ref_pp, TOTAL_ROWS)
        base = (final_p_val * 2) + final_s_val + int(pp_factor)
        c_mul = lookup_reference_jit(final_cm, ref_cm, TOTAL_ROWS)
        f_mul = lookup_reference_jit(final_fm, ref_fm, TOTAL_ROWS)
        heur_score = fast_calculate_score(base, c_mul, f_mul, fever_mask_head, count_body_fever, count_body_normal)
        
        if heur_score >= greedy_score:
            matches += 1
        else:
            mismatches += 1
            diff = greedy_score - heur_score
            diff_pct = diff / greedy_score * 100
            if diff_pct > 0.1:  # Only report significant mismatches
                print(f"  Mismatch: greedy={greedy_score:,} vs heur={heur_score:,} (diff={diff_pct:.2f}%)")
    
    print(f"\nResults: {matches} matches, {mismatches} mismatches")
    print(f"Heuristic accuracy: {matches/(matches+mismatches)*100:.1f}%")


def main():
    analyze_greedy_patterns()
    test_saturation_heuristic()
    
    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
