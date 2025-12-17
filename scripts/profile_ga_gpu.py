"""
Profile GA with GPU enabled to identify real bottlenecks.

This profiles the actual GPU code path used in production.
"""

import os
import sys
import cProfile
import pstats
import io
import time

# Enable GPU + timing
os.environ["GPU_MODE"] = "1"
os.environ["PERF_TIMING"] = "1"
os.environ["GPU_SYNC_FOR_TIMING"] = "1"

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def profile_ga_with_gpu():
    """Profile GA using GPU path."""
    import numpy as np
    import random
    from gear_optimizer.solver.genetic import solve_coevolution_genetic
    from gear_optimizer.core.constants import TOTAL_ROWS
    from gear_optimizer.data.models import GASettings
    
    print("=" * 70)
    print("GPU-ENABLED GA PROFILING")
    print("=" * 70)
    
    # Load real data from a song file if available
    # Otherwise use synthetic data
    SEED = 42
    np.random.seed(SEED)
    random.seed(SEED)
    
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    
    # Generate realistic gear items (50 per slot)
    all_gears = []
    gears_by_name = {}
    for slot in slots:
        for i in range(50):
            name = f"{slot}_{i}"
            item = {
                "Name": name,
                "type": slot,
                "Perfect Points": np.random.randint(0, 80),
                "Combo Multiplier": np.random.randint(0, 50),
                "Fever Multiplier": np.random.randint(0, 50),
                "Beat": np.random.randint(0, 150),
                "Vibe": np.random.randint(0, 150),
                "Rush": np.random.randint(0, 80),
                "Chill": np.random.randint(0, 80),
                "Flow": np.random.randint(0, 80),
                "Fever Time": np.random.randint(0, 30),
                "Fever Fill Rate": np.random.randint(0, 30),
            }
            all_gears.append(item)
            gears_by_name[name] = item
    
    # Generate minis
    all_minis = []
    minis_by_name = {}
    for i in range(30):
        name = f"Mini_{i}"
        item = {
            "Name": name,
            "type": "Mini",
            "Perfect Points": np.random.randint(50, 150),
            "Combo Multiplier": np.random.randint(30, 100),
            "Fever Multiplier": np.random.randint(30, 100),
            "Beat": np.random.randint(100, 300),
            "Vibe": np.random.randint(100, 300),
            "Rush": np.random.randint(50, 150),
            "Chill": np.random.randint(50, 150),
            "Flow": np.random.randint(50, 150),
            "Fever Time": np.random.randint(10, 50),
            "Fever Fill Rate": np.random.randint(10, 50),
        }
        all_minis.append(item)
        minis_by_name[name] = item

    # Realistic song (800 notes over 120s)
    timestamps = np.linspace(0, 120, 800).tolist()
    calc_song = {
        "metadata": {
            "Song Name": "Profile Song",
            "Difficulty": "Hard",
            "Primary Color": "Vibe",
            "Secondary Color": "Beat",
            "Long Notes": 50,
            "Last Note Time": 120.0,
            "Total Notes": 800,
        },
        "song_data": {
            "timestamps": timestamps,
        }
    }

    base_stats_fixed = {
        "Perfect Points": 100, "Combo Multiplier": 100, "Fever Multiplier": 100,
        "Fever Fill Rate": 100, "Fever Time": 100,
        "Rush": 100, "Flow": 100, "Beat": 150, "Vibe": 150, "Chill": 100,
    }
    
    rows = TOTAL_ROWS + 1
    ref_arrays = {
        "Perfect Points": np.linspace(1.0, 2.0, rows),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows),
        "Fever Time": np.linspace(1.0, 2.5, rows),
    }

    # Mock config that enables GPU
    class MockCfg:
        def get(self, section, option, fallback=None):
            if option == "GPU_Mode":
                return "True"
            if section == "IterationEngine":
                if option in ["MemeticElites", "MemeticSteps", "MemeticTopGear", "MemeticTopMinis"]:
                    return 0
                if option == "MultiStartRuns":
                    return 6  # Match production
                if option == "DeepMining":
                    return False
            return fallback

        def getboolean(self, section, option, fallback=False):
            if option == "GPU_Mode":
                return True
            val = self.get(section, option, fallback)
            if isinstance(val, bool): return val
            if str(val).lower() in ("true", "1", "yes"): return True
            return False
            
        def getint(self, section, option, fallback=0):
            try:
                return int(self.get(section, option, fallback))
            except:
                return int(fallback)

        def getfloat(self, section, option, fallback=0.0):
            try:
                return float(self.get(section, option, fallback))
            except:
                return float(fallback)

    cfg = MockCfg()
    
    # GA settings matching production
    ga_settings = GASettings(
        db_seed_prob=0.5,
        fixed_seed_copies=2,
        memetic_elites=4,
        memetic_steps=2,
        memetic_top_gear=4,
        memetic_top_minis=12,
        multi_start=6,  # Match production
        deep_mining_enabled=False,
        heuristic_mode="modern",
        allow_3_swap=True,
        gear_rank_max=40,
        mini_rank_max=40,
    )
    
    print(f"  Gear items: {len(all_gears)} ({len(all_gears)//6} per slot)")
    print(f"  Mini items: {len(all_minis)}")
    print(f"  Song notes: {len(timestamps)}")
    print(f"  Multi-start runs: {ga_settings.multi_start}")
    print(f"  ga_depth: 13")
    print()
    
    # Warmup Taichi
    print("Warming up Taichi GPU...")
    from gear_optimizer.solver.taichi_gem import api as gem_api
    gem_api.ensure_ready(ref_arrays)
    import taichi as ti
    ti.sync()
    print("GPU ready.\n")
    
    # Profile with timing breakdown
    phase_times = {}
    
    print("Running GA with profiling...")
    t0 = time.perf_counter()
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    best_data, best_gear, best_minis, _, _, _, _ = solve_coevolution_genetic(
        cfg=cfg,
        base_stats_fixed=base_stats_fixed,
        paths=None,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        all_gears=all_gears,
        all_minis=all_minis,
        gears_by_name=gears_by_name,
        minis_by_name=minis_by_name,
        optimize_gear=True,
        optimize_minis=True,
        ga_depth=13,  # Match production depth
        ga_settings=ga_settings,
    )
    
    profiler.disable()
    
    total_time = time.perf_counter() - t0
    
    print(f"\n{'='*70}")
    print(f"RESULT: Score={best_data['Score']} in {total_time:.2f}s")
    print(f"{'='*70}")
    
    # Print top functions by cumulative time
    print("\nTOP 25 FUNCTIONS (by cumulative time):")
    print("-" * 70)
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.strip_dirs()
    stats.sort_stats('cumulative')
    stats.print_stats(25)
    print(stream.getvalue())
    
    # Print top functions by total (self) time
    print("\nTOP 25 FUNCTIONS (by total/self time):")
    print("-" * 70)
    stream2 = io.StringIO()
    stats2 = pstats.Stats(profiler, stream=stream2)
    stats2.strip_dirs()
    stats2.sort_stats('tottime')
    stats2.print_stats(25)
    print(stream2.getvalue())
    
    # Save full results
    output_file = os.path.join(project_root, "tests", "ga_gpu_profile_results.txt")
    with open(output_file, "w") as f:
        f.write(f"GA GPU Profiling Results\n")
        f.write(f"Total time: {total_time:.2f}s\n")
        f.write(f"Final score: {best_data['Score']}\n")
        f.write("=" * 70 + "\n\n")
        
        f.write("TOP 50 BY CUMULATIVE TIME:\n")
        f.write("-" * 70 + "\n")
        stream3 = io.StringIO()
        stats3 = pstats.Stats(profiler, stream=stream3)
        stats3.strip_dirs()
        stats3.sort_stats('cumulative')
        stats3.print_stats(50)
        f.write(stream3.getvalue())
        
        f.write("\n\nTOP 50 BY TOTAL TIME:\n")
        f.write("-" * 70 + "\n")
        stream4 = io.StringIO()
        stats4 = pstats.Stats(profiler, stream=stream4)
        stats4.strip_dirs()
        stats4.sort_stats('tottime')
        stats4.print_stats(50)
        f.write(stream4.getvalue())
    
    print(f"\nFull results saved to: {output_file}")
    
    return best_data["Score"], total_time


if __name__ == "__main__":
    profile_ga_with_gpu()
