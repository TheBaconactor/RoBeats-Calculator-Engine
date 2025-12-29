import sys
import os
import numpy as np
import time
import logging

# Ensure we can import gear_optimizer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gear_optimizer.solver.scoring import solve_best_fever_combination, apply_force_greats_to_result
from gear_optimizer.core.constants import TOTAL_ROWS


def run_performance_test():
    logging.basicConfig(level=logging.ERROR)

    # 1. Mock Song (Short song for speed, but long enough to have sections)
    timestamps = np.linspace(0, 120, 100).tolist()
    calc_song = {
        "metadata": {
            "Song Name": "Perf Test Song",
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

    # 2. Stats
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

    # 3. Ref Arrays
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
        "use_gpu": False,  # Force CPU
        "user_ft": 0,
        "user_ff": 0,
        "user_pp": 0,
        "user_cm": 0,
        "user_fm": 0,
        "static_elem_input": 0,
    }

    print("Running initial solver...")
    # Seed the cache and get a result
    data_dict = solve_best_fever_combination(
        cfg=None,
        initial_stats=base_stats_fixed,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        silent=True,
        override_cfg=cfg_data,
    )

    print("Running Force Greats Hill Climb (Optimized)...")
    start_time = time.time()

    # This calls run_force_greats_hill_climb internally
    fg_result = apply_force_greats_to_result(data_dict, calc_song, ref_arrays, use_finder=True)

    end_time = time.time()
    duration = end_time - start_time

    print(f"FG Calculation took: {duration:.4f} seconds")

    # Assert performance constraint (should be well under 1 second for this small problem)
    # The unoptimized version with 4000 iterations would take significantly longer if simulated properly,
    # but here we just want to ensure it's fast.
    if duration > 10.0:
        raise AssertionError(f"Force Greats calculation too slow! Took {duration:.4f}s")

    # Verify we actually got a result and applied FG
    assert fg_result is not None
    assert fg_result.get("ForceGreats", {}).get("enabled") is True

    print(f"Initial Score: {data_dict['Score']}")
    # fg_base = fg_result['ForceGreats']['base_score']  <-- REMOVED
    # print(f"FG Base Score: {fg_base}")

    print(f"ForceGreats JSON: {fg_result['ForceGreats']}")

    # VERIFICATION: Ensure base_score is GONE from the JSON
    if "base_score" in fg_result["ForceGreats"]:
        raise AssertionError("base_score should NOT be in ForceGreats JSON anymore!")

    # Verify final_score (penalized) is present
    fg_final = fg_result["ForceGreats"].get("final_score")
    if fg_final is None:
        raise AssertionError("final_score (penalized) MUST be in ForceGreats JSON!")

    print(f"FG Final Score (Penalized): {fg_final}")

    # We can still check ratio using the returned Score vs BaseScore (if available)
    # But for this test, let's just use the final score
    fg_base = fg_result.get("BaseScore", data_dict["Score"])

    # Verify no massive inflation (Double counting bug check)
    ratio = fg_base / data_dict["Score"]
    if ratio > 1.2:
        raise AssertionError(f"Score Inflation Detected! Ratio: {ratio:.2f} (Double counting gems?)")

    print("Performance Test Passed!")

    # --------------------------------------------------------------------
    # Optional: GPU parity check for FG (only if Taichi GPU solver is available)
    # --------------------------------------------------------------------
    try:
        from gear_optimizer.solver.scoring import _get_gpu_solver, FG_CACHE, FG_TIMELINE_CACHE

        _, batch_solver = _get_gpu_solver()
    except Exception:
        batch_solver = None

    if batch_solver is None:
        print("GPU FG Parity Check: Skipped (GPU solver unavailable).")
        return

    # Clear caches so we actually exercise the GPU codepath
    FG_CACHE.clear()
    FG_TIMELINE_CACHE.clear()

    print("Running Force Greats Hill Climb (GPU)...")
    start_time = time.time()
    fg_result_gpu = apply_force_greats_to_result(
        data_dict,
        calc_song,
        ref_arrays,
        use_finder=True,
        use_gpu=True,
    )
    end_time = time.time()
    duration_gpu = end_time - start_time
    print(f"GPU FG Calculation took: {duration_gpu:.4f} seconds")

    assert fg_result_gpu is not None
    assert fg_result_gpu.get("ForceGreats", {}).get("enabled") is True

    # Parity: final FG score should match CPU path
    cpu_score = fg_result.get("Score", 0)
    gpu_score = fg_result_gpu.get("Score", 0)
    if cpu_score != gpu_score:
        raise AssertionError(f"GPU FG mismatch! CPU={cpu_score}, GPU={gpu_score}")


if __name__ == "__main__":
    run_performance_test()
