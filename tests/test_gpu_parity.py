"""
GPU Parity Test - Verifies Taichi GPU gem solver matches CPU implementation.

Tests:
1. calc_score parity - same inputs produce same score
2. optimize_gems parity - same gem allocation results
"""
import sys
import os
import numpy as np

# Ensure we can import gear_optimizer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gear_optimizer.solver.scoring_core import (
    fast_calculate_score,
    optimize_core_jit,
)
from gear_optimizer.solver.taichi_gem_solver import (
    init_taichi_vulkan,
    calc_score_gpu,
    optimize_gems_gpu,
)
from gear_optimizer.core.constants import (
    TOTAL_ROWS,
    GEM_SCALE_NORMAL,
    GEM_SCALE_FEVER,
    GEM_STAT_TO_ELEMENT_SCALE,
    ELEMENTAL_GEM_SCALE,
)


def test_calc_score_parity():
    """Test that GPU and CPU calc_score produce identical results."""
    print("\n=== Test: calc_score parity ===")
    
    # Test case: typical scoring scenario
    base_value = 150.0
    combo_mul = 2.5
    fever_mul = 3.0
    
    # Fever mask: first 30 notes in fever, rest normal (for head portion)
    fever_mask_head = np.array([True] * 30 + [False] * 70, dtype=np.bool_)
    count_body_fever = 200
    count_body_normal = 300
    
    # CPU calculation
    cpu_score = fast_calculate_score(
        base_value,
        combo_mul,
        fever_mul,
        fever_mask_head,
        count_body_fever,
        count_body_normal,
    )
    
    # GPU calculation
    gpu_score = calc_score_gpu(
        base_value,
        combo_mul,
        fever_mul,
        fever_mask_head,
        count_body_fever,
        count_body_normal,
    )
    
    print(f"  CPU Score: {cpu_score}")
    print(f"  GPU Score: {gpu_score}")
    
    assert cpu_score == gpu_score, f"Parity mismatch! CPU={cpu_score}, GPU={gpu_score}"
    print("  ✓ PASSED")
    return True


def test_optimize_gems_parity():
    """Test that GPU and CPU gem optimization produce identical results."""
    print("\n=== Test: optimize_gems parity ===")
    
    # Reference arrays (simple linear scaling for testing)
    rows = TOTAL_ROWS + 1
    ref_arrays = {
        "Perfect Points": np.linspace(1.0, 2.0, rows).astype(np.float64),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows).astype(np.float64),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows).astype(np.float64),
    }
    
    # Fever mask
    fever_mask_head = np.array([True] * 30 + [False] * 70, dtype=np.bool_)
    count_body_fever = 200
    count_body_normal = 300
    
    # Initial state
    budget = 50
    cur_pp = 80
    cur_cm = 70
    cur_fm = 60
    cur_p_val = 100  # Primary color value
    cur_s_val = 50   # Secondary color value
    
    # Flags: which stat contributes to which color
    # Let's say PP contributes to primary, CM to secondary, FM to neither
    is_p_pp = 1
    is_s_pp = 0
    is_p_cm = 0
    is_s_cm = 1
    is_p_fm = 0
    is_s_fm = 0
    is_p_ov = 1  # Overflow goes to primary
    is_s_ov = 0
    
    # CPU calculation
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
        160,  # MAX_STAT_INDEX
    )
    
    # GPU calculation
    gpu_result = optimize_gems_gpu(
        budget,
        cur_pp, cur_cm, cur_fm,
        cur_p_val, cur_s_val,
        is_p_pp, is_s_pp,
        is_p_cm, is_s_cm,
        is_p_fm, is_s_fm,
        is_p_ov, is_s_ov,
        fever_mask_head,
        count_body_fever,
        count_body_normal,
        ref_arrays,
    )
    
    print(f"  CPU Result: {cpu_result}")
    print(f"  GPU Result: {gpu_result}")
    
    # Compare all 9 values
    labels = ["pp", "cm", "fm", "p_val", "s_val", "gems_pp", "gems_cm", "gems_fm", "gems_ov"]
    all_match = True
    for i, label in enumerate(labels):
        cpu_val = cpu_result[i]
        gpu_val = gpu_result[i]
        match = "✓" if cpu_val == gpu_val else "✗"
        if cpu_val != gpu_val:
            all_match = False
            print(f"    {match} {label}: CPU={cpu_val}, GPU={gpu_val}")
    
    assert all_match, "Gem allocation mismatch!"
    print("  ✓ PASSED")
    return True


def run_all_tests():
    """Run all GPU parity tests."""
    print("=" * 60)
    print("GPU Parity Tests - Taichi Gem Solver vs CPU")
    print("=" * 60)
    
    # Initialize Taichi
    init_taichi_vulkan()
    
    passed = 0
    failed = 0
    
    try:
        test_calc_score_parity()
        passed += 1
    except AssertionError as e:
        print(f"  ✗ FAILED: {e}")
        failed += 1
    
    try:
        test_optimize_gems_parity()
        passed += 1
    except AssertionError as e:
        print(f"  ✗ FAILED: {e}")
        failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
