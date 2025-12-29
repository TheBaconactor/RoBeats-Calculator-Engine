"""
Test for batched parallel GPU gem solver.

Verifies that the batched kernel produces the same results as multiple
sequential single-item calls.
"""

import sys
import os
import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gear_optimizer.core.constants import TOTAL_ROWS


pytestmark = pytest.mark.gpu


def test_batch_parity():
    """Test that batched GPU produces same results as sequential calls."""
    print("=" * 60)
    print("Batched GPU Parity Test")
    print("=" * 60)

    pytest.importorskip("taichi")
    from gear_optimizer.solver.taichi_gem_solver import (
        init_taichi_vulkan,
        optimize_gems_gpu,
        optimize_gems_batch_gpu,
    )

    try:
        init_taichi_vulkan()
    except Exception as exc:
        pytest.skip(f"Taichi Vulkan init failed: {exc}")

    # Reference arrays
    rows = TOTAL_ROWS + 1
    ref_arrays = {
        "Perfect Points": np.linspace(1.0, 2.0, rows).astype(np.float64),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows).astype(np.float64),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows).astype(np.float64),
    }

    # Common parameters
    cur_pp = 80
    cur_cm = 70
    cur_fm = 60
    cur_p_val = 100
    cur_s_val = 50
    is_p_pp = 1
    is_s_pp = 0
    is_p_cm = 0
    is_s_cm = 1
    is_p_fm = 0
    is_s_fm = 0
    is_p_ov = 1
    is_s_ov = 0

    # Create batch of different timeline scenarios
    # Simulating different FT/FF gem allocations
    timeline_data = []

    for budget in [10, 20, 30, 40, 50]:
        for fever_ratio in [0.2, 0.5, 0.8]:
            n_fever = int(100 * fever_ratio)
            fever_mask = np.array([True] * n_fever + [False] * (100 - n_fever), dtype=np.bool_)
            body_fever = int(200 * fever_ratio)
            body_normal = 200 - body_fever

            timeline_data.append(
                {
                    "budget": budget,
                    "fever_mask_head": fever_mask,
                    "count_body_fever": body_fever,
                    "count_body_normal": body_normal,
                }
            )

    batch_size = len(timeline_data)
    print(f"\nTesting batch of {batch_size} timeline combinations...")

    # Run batched version
    print("\nRunning batched GPU kernel...")
    batch_results = optimize_gems_batch_gpu(
        timeline_data,
        cur_pp,
        cur_cm,
        cur_fm,
        base_p_val=cur_p_val,
        base_s_val=cur_s_val,
        is_p_ft=0,
        is_s_ft=0,
        is_p_ff=0,
        is_s_ff=0,
        is_p_pp=is_p_pp,
        is_s_pp=is_s_pp,
        is_p_cm=is_p_cm,
        is_s_cm=is_s_cm,
        is_p_fm=is_p_fm,
        is_s_fm=is_s_fm,
        is_p_ov=is_p_ov,
        is_s_ov=is_s_ov,
        ref_arrays=ref_arrays,
    )

    # Run sequential version for comparison
    print("Running sequential GPU calls...")
    sequential_results = []
    for t in timeline_data:
        result = optimize_gems_gpu(
            t["budget"],
            t["fever_mask_head"],
            t["count_body_fever"],
            t["count_body_normal"],
            cur_pp,
            cur_cm,
            cur_fm,
            cur_p_val,
            cur_s_val,
            is_p_pp,
            is_s_pp,
            is_p_cm,
            is_s_cm,
            is_p_fm,
            is_s_fm,
            is_p_ov,
            is_s_ov,
            ref_arrays,
        )
        # Both return:
        # (score, pp, cm, fm, p_val, s_val, gems_pp, gems_cm, gems_fm, gems_ov)
        sequential_results.append(result)

    # Compare results
    print("\nComparing results...")
    all_match = True
    mismatches = 0

    for i in range(batch_size):
        if batch_results[i] != sequential_results[i]:
            all_match = False
            mismatches += 1
            if mismatches <= 3:  # Show first 3 mismatches
                print(f"  [MISMATCH] at index {i}:")
                print(f"    Batch: {batch_results[i]}")
                print(f"    Sequential: {sequential_results[i]}")

    print("\n" + "=" * 60)
    if all_match:
        print(f"[PASS] All {batch_size} results match!")
        print(f"  Batch processing enables {batch_size}x parallelism")
    else:
        print(f"[FAIL] {mismatches}/{batch_size} mismatches")
    print("=" * 60)

    assert all_match, f"{mismatches}/{batch_size} mismatches"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v", "-s"]))
