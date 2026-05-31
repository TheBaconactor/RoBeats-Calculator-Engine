import sys
import os
import numpy as np
import logging

# Ensure we can import gear_optimizer
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from gear_optimizer.solver.scoring.fever_solver import solve_best_fever_combination
from gear_optimizer.core.constants import TOTAL_ROWS


def run_regression():
    logging.basicConfig(level=logging.ERROR)

    # 1. Mock Song
    # Simple song: 100 notes, 120 seconds.
    # Timestamps: 0, 1.2, 2.4, ...
    timestamps = np.linspace(0, 120, 100).tolist()
    calc_song = {
        "metadata": {
            "Song Name": "Regression Song",
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": 120.0,
            "Total Notes": 100,
        },
        "song_data": {
            "timestamps": timestamps,
        },
    }

    # 2. Mock Stats (All 100 to keep it simple)
    base_stats_fixed = {
        "Perfect Points": 100,
        "Combo Multiplier": 100,
        "Fever Multiplier": 100,
        "Fever Fill Rate": 100,
        "Fever Time": 100,
        "Rush": 100,  # Primary
        "Flow": 100,  # Secondary
        "Beat": 50,
        "Vibe": 50,
        "Chill": 50,
    }

    # 3. Ref Arrays (Linear scaling)
    # 0 to 160 index.
    # Value = index * 10 (just for simple math)
    # Actually, let's use real-ish scaling 1.0 to 3.0
    rows = TOTAL_ROWS + 1
    ref_arrays = {
        "Perfect Points": np.linspace(1.0, 2.0, rows),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows),
        "Fever Time": np.linspace(1.0, 2.5, rows),
    }

    # 4. Config
    cfg_data = {
        "selected_color": "Rush",
        "use_gpu": False,  # Force CPU for deterministic simple test
        "user_ft": 0,
        "user_ff": 0,
        "user_pp": 0,
        "user_cm": 0,
        "user_fm": 0,
        "static_elem_input": 0,
    }

    print("Running solver with fixed config...")
    result = solve_best_fever_combination(
        cfg=None,
        initial_stats=base_stats_fixed,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        silent=True,
        override_cfg=cfg_data,
    )

    score = result.get("Score")
    print(f"Regression Score: {score}")

    expected_score = 493177
    assert score == expected_score, f"Expected {expected_score}, got {score}"
    print("Regression Test Passed!")

    return score


if __name__ == "__main__":
    run_regression()
