
import sys
import os
import time
import numpy as np
import logging

# Ensure we can import gear_optimizer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set env vars for profiling BEFORE importing taichi
os.environ["TAICHI_KERNEL_PROFILER"] = "1"

from gear_optimizer.solver.scoring import solve_best_fever_combination, apply_force_greats_to_result
from gear_optimizer.core.constants import TOTAL_ROWS

def run_measurement():
    print("=== Force Greats Performance Measurement ===")
    
    # 1. Setup Mock Song
    # Use a longer song to generate more work items
    timestamps = np.linspace(0, 180, 1500).tolist() 
    calc_song = {
        "metadata": {
            "Song Name": "Perf Measurement Song",
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": 180.0,
            "Total Notes": 1500,
        },
        "song_data": {
            "timestamps": timestamps,
        }
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

    # 4. Initial Solution
    cfg_data = {
        "selected_color": "Rush",
        "use_gpu": True, 
        "user_ft": 0,
        "user_ff": 0,
        "user_pp": 0,
        "user_cm": 0,
        "user_fm": 0,
        "static_elem_input": 0,
    }

    print("Running initial solver...")
    data_dict = solve_best_fever_combination(
        cfg=None,
        initial_stats=base_stats_fixed,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        silent=True,
        override_cfg=cfg_data,
    )
    
    # 5. Measure Force Greats (GPU)
    print("\nRunning Force Greats Finder (GPU)...")
    
    # Populate a fake cache of "loadout entries" to simulate batch processing
    # song_helpers processes loadout_entries, but apply_force_greats_to_result 
    # handles a single entry. 
    # To truly measure the BATCHING efficiency, we should call process_force_greats directly
    # or create a scenario that feeds many entries to it.
    
    try:
        from gear_optimizer.helpers.song_helpers import process_force_greats
        
        # Create 50 variations to trigger batching logic
        loadout_entries = {}
        for i in range(50):
            # Vary stats slightly to create unique signatures
            stats = base_stats_fixed.copy()
            stats["Rush"] += i 
            
            loadout_entries[f"hash_{i}"] = {
                "score": data_dict["Score"],
                "gear": [], "minis": [],
                "details": {
                    "Stats": stats,
                    "Selected Element": "Rush",
                    "FT": 0, "FF": 0
                },
                "eval_data": {
                    "Stats": stats,
                    "Selected Element": "Rush",
                    "FT": 0, "FF": 0,
                    "GemCounts": data_dict["GemCounts"]
                }
            }

        start_time = time.perf_counter()
        
        results = process_force_greats(
            loadout_entries=loadout_entries,
            manual_force_greats=False,
            force_greats_finder=True,
            force_greats_config=[],
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            meta_primary_color="Rush",
            build_details_fn=lambda x: x,
            db_loadouts_full_count=100,
            use_gpu=True,
            perf_timing=True, # Enable internal timing prints
        )
        
        end_time = time.perf_counter()
        print(f"\nTotal Wall Time: {end_time - start_time:.4f}s")
        print(f"Total Variants Generated: {len(results)}")
        
        # Print profiler info
        import taichi as ti
        ti.profiler.print_kernel_profiler_info()
        
    except ImportError:
        print("Could not import song_helpers, running single-shot via scoring...")
        start_time = time.perf_counter()
        apply_force_greats_to_result(
            data_dict,
            calc_song,
            ref_arrays,
            use_finder=True,
            use_gpu=True
        )
        print(f"Single-shot Time: {time.perf_counter() - start_time:.4f}s")

if __name__ == "__main__":
    run_measurement()
