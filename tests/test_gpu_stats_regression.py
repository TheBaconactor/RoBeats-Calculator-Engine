"""
Complex GPU Stats Regression Test

This test verifies precise parity between:
1. CPU Solver (solve_best_fever_combination)
2. GPU Solver (solve_best_fever_combination with use_gpu=True)
3. GPU Batch (batch_evaluate_genomes)

It uses scenarios with User Input Gems and specific Elemental Colors to catch
regressions in stats calculation, specifically the 'double deduction' bug.
"""

import numpy as np
import sys
import os
import json

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gear_optimizer.solver.scoring import batch_evaluate_genomes, solve_best_fever_combination
from gear_optimizer.core.constants import (
    TOTAL_ROWS,
    GEM_SCALE_NORMAL,
    GEM_SCALE_FEVER,
    GEM_STAT_TO_ELEMENT_SCALE,
    ELEMENTAL_GEM_SCALE,
)


def create_mock_song(primary="Beat", secondary="Flow"):
    timestamps = np.linspace(0, 120, 100).tolist()
    return {
        "metadata": {
            "Song Name": "Regression Test Song",
            "Difficulty": "Hard",
            "Primary Color": primary,
            "Secondary Color": secondary,
            "Long Notes": 0,
            "Last Note Time": 120.0,
            "Total Notes": 100,
        },
        "song_data": {"timestamps": timestamps},
    }


def create_mock_ref():
    rows = TOTAL_ROWS + 1
    return {
        "Perfect Points": np.linspace(1.0, 2.0, rows),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows),
        "Fever Time": np.linspace(1.0, 2.5, rows),
    }


def check_parity(name, base_stats, cfg_override, song_colors):
    print(f"\n[TEST] {name}")
    print("-" * 60)

    ref_arrays = create_mock_ref()
    calc_song = create_mock_song(*song_colors)

    # 1. Run CPU Solver
    print("Running CPU Solver...")
    cpu_cfg = {**cfg_override, "use_gpu": False}
    cpu_res = solve_best_fever_combination(
        None, base_stats.copy(), calc_song, ref_arrays, silent=True, override_cfg=cpu_cfg
    )

    # 2. Run GPU Solver
    print("Running GPU Solver...")
    gpu_cfg = {**cfg_override, "use_gpu": True}
    gpu_res = solve_best_fever_combination(
        None, base_stats.copy(), calc_song, ref_arrays, silent=True, override_cfg=gpu_cfg
    )

    # 3. Run GPU Batch
    print("Running GPU Batch...")
    # Construct genome from base_stats (flattened dict to list of 1 genome)
    genome_stats = {**base_stats}
    # Mock a genome object that would result in these stats
    mock_genome = [{"Name": "Mock", **base_stats}]

    # Batch evaluate uses a slightly different signature
    batch_res_list = batch_evaluate_genomes(
        [mock_genome],
        {k: 0 for k in base_stats},  # base_stats_fixed (all 0, as stats are in genome)
        gpu_cfg,
        calc_song,
        ref_arrays,
    )
    batch_res = batch_res_list[0] if batch_res_list else None

    # --- ASSERTIONS ---

    # Helper to print discrepancies
    def assert_eq(val1, val2, field, src1, src2):
        if val1 != val2:
            print(f"FAILED: {field} mismatch!")
            print(f"  {src1}: {val1}")
            print(f"  {src2}: {val2}")
            print(f"  Diff: {val1 - val2 if isinstance(val1, (int, float)) else 'N/A'}")
            return False
        return True

    all_passed = True

    # Compare CPU vs GPU Solver
    print("Comparing CPU vs GPU Solver...")
    if not assert_eq(cpu_res["Score"], gpu_res["Score"], "Score", "CPU", "GPU"):
        all_passed = False

    # Check Gem Counts deeply
    cpu_gems = cpu_res["GemCounts"]
    gpu_gems = gpu_res["GemCounts"]
    for k in cpu_gems:
        if not assert_eq(cpu_gems[k], gpu_gems.get(k, 0), f"Gem {k}", "CPU", "GPU"):
            all_passed = False

    # Check FT/FF
    if not assert_eq(cpu_res["FT"], gpu_res["FT"], "FT Gems", "CPU", "GPU"):
        all_passed = False
    if not assert_eq(cpu_res["FF"], gpu_res["FF"], "FF Gems", "CPU", "GPU"):
        all_passed = False

    # Compare GPU Solver vs GPU Batch
    print("Comparing GPU Solver vs GPU Batch...")
    if batch_res:
        if not assert_eq(gpu_res["Score"], batch_res["Score"], "Score", "GPU_Solver", "GPU_Batch"):
            all_passed = False

        # Batch result doesn't return full breakdown in Data currently, let's check what it has
        # It usually returns {Score, Genome, ..., Data: result_dict}
        # But for batch_evaluate_genomes, it might return a simplified structure or the full dict depending on implementation
        # Let's inspect the 'Data' key if present, or top level keys.

        # In scoring.py batch_evaluate_genomes returns list of dicts.
        # Check what fields are available
        # Based on scoring.py:
        # "Score": ..., "FT": ..., "FF": ..., "GemCounts": ..., "Stats": ...

        # Batch result returns simplified structure with "Data" containing full breakdown
        # result = { "Score": ..., "Genome": ..., "Data": { "Score": ..., "FT": ..., "GemCounts": ... } }

        batch_data = batch_res.get("Data", {})

        if not assert_eq(gpu_res["FT"], batch_data.get("FT"), "FT Gems", "GPU_Solver", "GPU_Batch"):
            all_passed = False
        if not assert_eq(gpu_res["FF"], batch_data.get("FF"), "FF Gems", "GPU_Solver", "GPU_Batch"):
            all_passed = False

        batch_gems = batch_data.get("GemCounts", {})
        for k in gpu_gems:
            if not assert_eq(gpu_gems[k], batch_gems.get(k, 0), f"Gem {k}", "GPU_Solver", "GPU_Batch"):
                all_passed = False
    else:
        print("FAILED: GPU Batch returned no result")
        all_passed = False

    if all_passed:
        print("PASSED")

    return all_passed


if __name__ == "__main__":
    base_stats = {
        "Perfect Points": 100,
        "Combo Multiplier": 100,
        "Fever Multiplier": 100,
        "Fever Fill Rate": 100,
        "Fever Time": 100,
        "Rush": 100,
        "Flow": 100,
        "Beat": 100,
        "Vibe": 100,
        "Chill": 100,
    }

    # Scenario 1: No User Gems (Control)
    s1 = check_parity(
        "No User Gems",
        base_stats,
        {
            "selected_color": "Rush",
            "user_ft": 0,
            "user_ff": 0,
            "user_pp": 0,
            "user_cm": 0,
            "user_fm": 0,
            "static_elem_input": 0,
        },
        ("Rush", "Flow"),
    )

    # Scenario 2: User Gems Deductions (The Regression Case)
    # Deducting gems means 'base_stats' passed to solver has artificially high values that need to be reduced
    s2 = check_parity(
        "With User Gems (Deduction Check)",
        base_stats,
        {
            "selected_color": "Rush",
            "user_ft": 2,
            "user_ff": 2,
            "user_pp": 5,
            "user_cm": 5,
            "user_fm": 5,
            "static_elem_input": 10,
        },
        ("Rush", "Flow"),
    )

    # Scenario 3: Different Elemental Colors
    s3 = check_parity(
        "Elemental Colors (Beat/Vibe)",
        base_stats,
        {
            "selected_color": "Beat",
            "user_ft": 0,
            "user_ff": 0,
            "user_pp": 0,
            "user_cm": 0,
            "user_fm": 0,
            "static_elem_input": 0,
        },
        ("Beat", "Vibe"),
    )

    if s1 and s2 and s3:
        print("\nALL REGRESSION TESTS PASSED")
        sys.exit(0)
    else:
        print("\nREGRESSION TESTS FAILED")
        sys.exit(1)
