
import sys
import os
import importlib.util
import numpy as np
import logging

# Ensure we can import gear_optimizer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gear_optimizer.solver.scoring import solve_best_fever_combination as solve_new
from gear_optimizer.core.constants import TOTAL_ROWS

def compare_versions():
    # --- 1. Load Legacy Module ---
    legacy_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "legacy", "Manual_Calculator - Main.py")
    spec = importlib.util.spec_from_file_location("legacy_main", legacy_path)
    legacy_module = importlib.util.module_from_spec(spec)
    try:
        # Redirect stdout/stderr to suppress legacy script noise during import
        with open(os.devnull, 'w') as fnull:
            old_stdout = sys.stdout
            sys.stdout = fnull
            try:
                spec.loader.exec_module(legacy_module)
            finally:
                sys.stdout = old_stdout
    except Exception as e:
        print(f"Warning: Legacy import error (ignoring if functions loaded): {e}")

    solve_legacy = getattr(legacy_module, "solve_best_fever_combination", None)
    if not solve_legacy:
        print("Error: solve_best_fever_combination not found in legacy script.")
        return

    # --- 2. Setup Inputs ---
    # Same as regression_fixed.py
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
        }
    }
    
    base_stats_fixed = {
        "Perfect Points": 100,
        "Combo Multiplier": 100,
        "Fever Multiplier": 100,
        "Fever Fill Rate": 100,
        "Fever Time": 100,
        "Rush": 100, "Flow": 100, "Beat": 50, "Vibe": 50, "Chill": 50,
    }
    
    rows = TOTAL_ROWS + 1
    ref_arrays = {
        "Perfect Points": np.linspace(1.0, 2.0, rows),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows),
        "Fever Time": np.linspace(1.0, 2.5, rows),
    }

    cfg_data = {
        "selected_color": "Rush",
        "use_gpu": False, # CPU for fairness against legacy (usually CPU)
        "user_ft": 0, "user_ff": 0, "user_pp": 0, "user_cm": 0, "user_fm": 0,
        "static_elem_input": 0,
    }

    print("\n--- Running Comparisons ---")
    
    # Run Legacy
    print("Executing Legacy Solver...")
    # Legacy likely expects a tuple argument if it was consistent with worker, OR args.
    # We will try keyword args first as that mimics the new signature which was derived from it.
    # However, if legacy signature is different, we might trap an error.
    try:
        res_old = solve_legacy(
            cfg=None,
            initial_stats=base_stats_fixed,
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            silent=True,
            override_cfg=cfg_data,
        )
    except TypeError:
        # Fallback: maybe it expects a single payload tuple?
        print(" -> Legacy call failed with kwargs, trying tuple payload...")
        res_old = solve_legacy(
            (None, base_stats_fixed, cfg_data, calc_song, ref_arrays),
            silent=True
        )

    score_old = res_old.get("Score", 0)
    print(f"Legacy Score: {score_old}")

    # Run New
    print("Executing New Solver...")
    res_new = solve_new(
        cfg=None,
        initial_stats=base_stats_fixed,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        silent=True,
        override_cfg=cfg_data,
    )
    score_new = res_new.get("Score", 0)
    print(f"New Score:    {score_new}")

    diff = score_new - score_old
    print(f"Delta:        {diff}")

    if score_old == score_new:
        print("\nSUCCESS: Scores match exactly.")
    else:
        print(f"\nFAILURE: Score mismatch ({diff}).")

if __name__ == "__main__":
    compare_versions()
