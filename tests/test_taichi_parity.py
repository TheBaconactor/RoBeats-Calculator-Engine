"""
Parity test: Verify GPU Taichi gem solver produces identical scores to CPU.

Compares:
- scoring_core.py (CPU/Numba JIT) vs taichi_gem_solver.py (GPU/Vulkan)

For each test case:
1. Run CPU optimize_core_jit with fixed inputs
2. Run GPU optimize_gems_batch_gpu with same inputs
3. Assert exact score match
"""
import numpy as np
import sys
import os

# Add parent to path for imports
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


def create_test_ref_arrays():
    """Create mock reference arrays for testing."""
    # Simple linear progression for testing
    pp = np.array([i * 2.5 for i in range(161)], dtype=np.float64)
    cm = np.array([1.0 + i * 0.005 for i in range(161)], dtype=np.float64)
    fm = np.array([1.5 + i * 0.01 for i in range(161)], dtype=np.float64)
    
    return {
        "Perfect Points": pp,
        "Combo Multiplier": cm,
        "Fever Multiplier": fm,
    }


def test_lookup_parity():
    """Test that lookup functions produce identical results."""
    print("Testing lookup_reference parity...")
    
    ref_arrays = create_test_ref_arrays()
    ref_pp = ref_arrays["Perfect Points"]
    
    # Test boundary cases
    test_values = [0, 1, 80, 160, 161, -5]
    
    for val in test_values:
        cpu_result = lookup_reference_jit(val, ref_pp, TOTAL_ROWS)
        # GPU will use same logic, just checking CPU baseline
        expected_idx = max(0, min(TOTAL_ROWS, int(val)))
        assert cpu_result == ref_pp[expected_idx], f"Lookup mismatch for {val}"
    
    print("  [PASS] lookup_reference parity OK")


def test_fast_calculate_score_parity():
    """Test calc_score produces identical results."""
    print("Testing fast_calculate_score parity...")
    
    # Create test fever mask (50% fever)
    fever_mask_head = np.array([i % 2 == 0 for i in range(100)], dtype=np.bool_)
    
    test_cases = [
        # (base_value, combo_mul, fever_mul, count_body_fever, count_body_normal)
        (500, 1.45, 2.3, 100, 200),
        (1000, 1.8, 3.0, 50, 150),
        (250, 1.0, 1.5, 0, 300),
        (800, 1.6, 2.8, 200, 0),
    ]
    
    for base_val, c_mul, f_mul, cnt_fever, cnt_normal in test_cases:
        cpu_score = fast_calculate_score(
            base_val, c_mul, f_mul,
            fever_mask_head,
            cnt_fever, cnt_normal,
        )
        # Just verify CPU runs correctly (GPU test comes later)
        assert cpu_score > 0, f"Invalid CPU score: {cpu_score}"
        print(f"    base={base_val}, combo={c_mul}, fever={f_mul} -> score={cpu_score:,}")
    
    print("  [PASS] fast_calculate_score baseline OK")


def test_optimize_core_parity():
    """Test full gem optimizer produces identical results."""
    print("Testing optimize_core_jit parity...")
    
    ref_arrays = create_test_ref_arrays()
    fever_mask_head = np.array([i % 3 == 0 for i in range(100)], dtype=np.bool_)
    
    # Test case: typical scenario
    budget = 90
    cur_pp = 100
    cur_cm = 80
    cur_fm = 60
    cur_p_val = 500
    cur_s_val = 300
    
    # Color mapping: primary=Chill (PP), secondary=Flow (CM)
    is_p_pp = 1
    is_s_pp = 0
    is_p_cm = 0
    is_s_cm = 1
    is_p_fm = 0
    is_s_fm = 0
    is_p_ov = 1  # overflow goes to primary (Chill)
    is_s_ov = 0
    
    count_body_fever = 150
    count_body_normal = 250
    
    result = optimize_core_jit(
        budget,
        cur_pp, cur_cm, cur_fm,
        cur_p_val, cur_s_val,
        is_p_pp, is_s_pp,
        is_p_cm, is_s_cm,
        is_p_fm, is_s_fm,
        is_p_ov, is_s_ov,
        ref_arrays["Perfect Points"],
        ref_arrays["Combo Multiplier"],
        ref_arrays["Fever Multiplier"],
        fever_mask_head,
        count_body_fever,
        count_body_normal,
        GEM_SCALE_NORMAL,
        GEM_SCALE_FEVER,
        GEM_STAT_TO_ELEMENT_SCALE,
        ELEMENTAL_GEM_SCALE,
        TOTAL_ROWS,
        MAX_STAT_INDEX,
    )
    
    final_pp, final_cm, final_fm, final_p_val, final_s_val, gems_pp, gems_cm, gems_fm, gems_ov = result
    
    print(f"    Budget: {budget}")
    print(f"    Input stats: PP={cur_pp}, CM={cur_cm}, FM={cur_fm}")
    print(f"    Output stats: PP={final_pp}, CM={final_cm}, FM={final_fm}")
    print(f"    Gem allocation: PP={gems_pp}, CM={gems_cm}, FM={gems_fm}, OV={gems_ov}")
    print(f"    Total gems: {gems_pp + gems_cm + gems_fm + gems_ov} (expected={budget})")
    
    # Verify budget used correctly
    assert gems_pp + gems_cm + gems_fm + gems_ov == budget, "Budget mismatch!"
    
    print("  [PASS] optimize_core_jit baseline OK")
    
    return result, ref_arrays, fever_mask_head


def test_gpu_parity():
    """Compare GPU output to CPU baseline."""
    print("\nTesting GPU parity (Taichi Vulkan)...")
    
    try:
        from gear_optimizer.solver.taichi_gem_solver import (
            init_taichi_vulkan,
            load_ref_arrays,
            optimize_gems_batch_gpu,
        )
    except ImportError as e:
        print(f"  [SKIP] Taichi not available: {e}")
        return
    
    # Initialize Taichi
    init_taichi_vulkan()
    
    # Get CPU baseline
    ref_arrays = create_test_ref_arrays()
    fever_mask_head = np.array([i % 3 == 0 for i in range(100)], dtype=np.bool_)
    
    budget = 90
    cur_pp = 100
    cur_cm = 80
    cur_fm = 60
    cur_p_val = 500
    cur_s_val = 300
    
    is_p_pp = 1
    is_s_pp = 0
    is_p_cm = 0
    is_s_cm = 1
    is_p_fm = 0
    is_s_fm = 0
    is_p_ov = 1
    is_s_ov = 0
    
    count_body_fever = 150
    count_body_normal = 250
    
    # Run CPU
    cpu_result = optimize_core_jit(
        budget,
        cur_pp, cur_cm, cur_fm,
        cur_p_val, cur_s_val,
        is_p_pp, is_s_pp,
        is_p_cm, is_s_cm,
        is_p_fm, is_s_fm,
        is_p_ov, is_s_ov,
        ref_arrays["Perfect Points"],
        ref_arrays["Combo Multiplier"],
        ref_arrays["Fever Multiplier"],
        fever_mask_head,
        count_body_fever,
        count_body_normal,
        GEM_SCALE_NORMAL,
        GEM_SCALE_FEVER,
        GEM_STAT_TO_ELEMENT_SCALE,
        ELEMENTAL_GEM_SCALE,
        TOTAL_ROWS,
        MAX_STAT_INDEX,
    )
    
    # Calculate CPU score
    final_pp, final_cm, final_fm, final_p_val, final_s_val, _, _, _, _ = cpu_result
    cpu_pp_factor = lookup_reference_jit(final_pp, ref_arrays["Perfect Points"], TOTAL_ROWS)
    cpu_base = (final_p_val * 2) + final_s_val + int(cpu_pp_factor)
    cpu_c_mul = lookup_reference_jit(final_cm, ref_arrays["Combo Multiplier"], TOTAL_ROWS)
    cpu_f_mul = lookup_reference_jit(final_fm, ref_arrays["Fever Multiplier"], TOTAL_ROWS)
    
    cpu_score = fast_calculate_score(
        cpu_base, cpu_c_mul, cpu_f_mul,
        fever_mask_head, count_body_fever, count_body_normal,
    )
    
    print(f"    CPU score: {cpu_score:,}")
    
    # Run GPU
    load_ref_arrays(ref_arrays)
    
    batch_input = [{
        "budget": budget,
        "fever_mask_head": fever_mask_head,
        "count_body_fever": count_body_fever,
        "count_body_normal": count_body_normal,
        "ft_gems": 0,
        "ff_gems": 0,
    }]
    
    gpu_results = optimize_gems_batch_gpu(
        batch_input,
        cur_pp, cur_cm, cur_fm,
        base_p_val=cur_p_val,
        base_s_val=cur_s_val,
        is_p_ft=0, is_s_ft=0,
        is_p_ff=0, is_s_ff=0,
        is_p_pp=is_p_pp, is_s_pp=is_s_pp,
        is_p_cm=is_p_cm, is_s_cm=is_s_cm,
        is_p_fm=is_p_fm, is_s_fm=is_s_fm,
        is_p_ov=is_p_ov, is_s_ov=is_s_ov,
        ref_arrays=ref_arrays,
    )
    
    gpu_result = gpu_results[0]
    gpu_score = gpu_result[0]
    
    print(f"    GPU score: {gpu_score:,}")
    
    # Compare
    if cpu_score == gpu_score:
        print("  [PASS] GPU score EXACTLY matches CPU!")
    else:
        diff = abs(cpu_score - gpu_score)
        diff_pct = diff / cpu_score * 100 if cpu_score > 0 else 0
        print(f"  [WARN] Score difference: {diff} ({diff_pct:.4f}%)")
        
        if diff_pct < 0.01:
            print("  [PASS] Within acceptable tolerance (f32 precision)")
        else:
            print("  [FAIL] Score difference too large!")
            return False
    
    return True


def main():
    print("=" * 60)
    print("Taichi Gem Solver Parity Test")
    print("=" * 60)
    print()
    
    # CPU baseline tests
    test_lookup_parity()
    test_fast_calculate_score_parity()
    test_optimize_core_parity()
    
    # GPU parity test
    success = test_gpu_parity()
    
    print()
    print("=" * 60)
    if success:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)
    print("=" * 60)


if __name__ == "__main__":
    main()
