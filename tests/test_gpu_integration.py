"""
Integration test for GPU gem solver via scoring.py.

Tests that the GPU path produces the same result as CPU when called
through solve_best_fever_combination with use_gpu=True.
"""
import sys
import os
import numpy as np

# Ensure we can import gear_optimizer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gear_optimizer.solver.scoring import solve_best_fever_combination
from gear_optimizer.core.constants import TOTAL_ROWS


def run_integration_test():
    """Test GPU path produces same result as CPU through main solver."""
    print("=" * 60)
    print("GPU Integration Test - Via solve_best_fever_combination")
    print("=" * 60)
    
    # Mock Song (same as regression_fixed.py)
    timestamps = np.linspace(0, 120, 100).tolist()
    calc_song = {
        "metadata": {
            "Song Name": "GPU Integration Test Song",
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": 120.0,
            "Total Notes": 100,
        },
        "song_data": {
            "timestamps": timestamps,
        }
    }
    
    # Mock Stats
    base_stats_fixed = {
        "Perfect Points": 100,
        "Combo Multiplier": 100,
        "Fever Multiplier": 100,
        "Fever Fill Rate": 100,
        "Fever Time": 100,
        "Rush": 100,
        "Flow": 100,
        "Beat": 50,
        "Vibe": 50,
        "Chill": 50,
    }
    
    # Ref Arrays
    rows = TOTAL_ROWS + 1
    ref_arrays = {
        "Perfect Points": np.linspace(1.0, 2.0, rows),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows),
        "Fever Time": np.linspace(1.0, 2.5, rows),
    }

    # Base config
    base_cfg = {
        "selected_color": "Rush",
        "user_ft": 0,
        "user_ff": 0,
        "user_pp": 0,
        "user_cm": 0,
        "user_fm": 0,
        "static_elem_input": 0,
    }

    # CPU Path
    print("\nRunning CPU solver...")
    cpu_cfg = {**base_cfg, "use_gpu": False}
    cpu_result = solve_best_fever_combination(
        cfg=None,
        initial_stats=base_stats_fixed.copy(),
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        silent=True,
        override_cfg=cpu_cfg,
    )
    cpu_score = cpu_result.get("Score")
    print(f"  CPU Score: {cpu_score}")
    
    # GPU Path
    print("\nRunning GPU solver...")
    gpu_cfg = {**base_cfg, "use_gpu": True}
    gpu_result = solve_best_fever_combination(
        cfg=None,
        initial_stats=base_stats_fixed.copy(),
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        silent=True,
        override_cfg=gpu_cfg,
    )
    gpu_score = gpu_result.get("Score")
    print(f"  GPU Score: {gpu_score}")
    
    # Compare
    print("\n" + "=" * 60)
    if cpu_score == gpu_score:
        print(f"✓ PASSED: CPU ({cpu_score}) == GPU ({gpu_score})")
        print("=" * 60)
        return True
    else:
        print(f"✗ FAILED: CPU ({cpu_score}) != GPU ({gpu_score})")
        print("  Diff:", gpu_score - cpu_score)
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = run_integration_test()
    sys.exit(0 if success else 1)
