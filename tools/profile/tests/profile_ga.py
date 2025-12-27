"""
Profile the Genetic Algorithm to identify performance bottlenecks.
Uses cProfile and pstats to generate a detailed performance report.
"""
import sys
import os
import cProfile
import pstats
import io
import numpy as np
import random

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


def setup_ga_test_data():
    """Create mock data for GA profiling."""
    from gear_optimizer.core.constants import TOTAL_ROWS
    
    SEED = 42
    np.random.seed(SEED)
    random.seed(SEED)
    
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    
    # Generate 50 items per slot (300 total gear items)
    all_gears = []
    gears_by_name = {}
    for slot in slots:
        for i in range(50):
            name = f"{slot}_{i}"
            item = {
                "Name": name,
                "type": slot,
                "Perfect Points": np.random.randint(0, 50),
                "Combo Multiplier": np.random.randint(0, 30),
                "Fever Multiplier": np.random.randint(0, 30),
                "Beat": np.random.randint(0, 100),
                "Vibe": np.random.randint(0, 100),
                "Rush": np.random.randint(0, 50),
                "Chill": np.random.randint(0, 50),
                "Flow": np.random.randint(0, 50),
                "Fever Time": np.random.randint(0, 20),
                "Fever Fill Rate": np.random.randint(0, 20),
            }
            all_gears.append(item)
            gears_by_name[name] = item
    
    # Generate 20 minis
    all_minis = []
    minis_by_name = {}
    for i in range(20):
        name = f"Mini_{i}"
        item = {
            "Name": name,
            "type": "Mini",
            "Perfect Points": np.random.randint(0, 100),
            "Combo Multiplier": np.random.randint(0, 60),
            "Fever Multiplier": np.random.randint(0, 60),
            "Beat": np.random.randint(0, 200),
            "Vibe": np.random.randint(0, 200),
            "Rush": np.random.randint(0, 100),
            "Chill": np.random.randint(0, 100),
            "Flow": np.random.randint(0, 100),
            "Fever Time": np.random.randint(0, 30),
            "Fever Fill Rate": np.random.randint(0, 30),
        }
        all_minis.append(item)
        minis_by_name[name] = item

    # Mock Song Context - 100 notes over 120s
    timestamps = np.linspace(0, 120, 100).tolist()
    calc_song = {
        "metadata": {
            "Song Name": "Profile Song",
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
        "Perfect Points": 100, "Combo Multiplier": 100, "Fever Multiplier": 100,
        "Fever Fill Rate": 100, "Fever Time": 100,
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

    # Mock Config object
    class MockCfg:
        def get(self, section, option, fallback=None):
            if section == "UserInputStatsGems":
                return 0
            if section == "ElementalGems":
                return 0
            if section == "IterationEngine":
                if option in ["MemeticElites", "MemeticSteps", "MemeticTopGear", "MemeticTopMinis"]:
                    return 0
                if option == "MultiStartRuns":
                    return 1
                if option == "DeepMining":
                    return False
            return fallback

        def getboolean(self, section, option, fallback=False):
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
    
    return {
        "cfg": cfg,
        "base_stats_fixed": base_stats_fixed,
        "calc_song": calc_song,
        "ref_arrays": ref_arrays,
        "all_gears": all_gears,
        "all_minis": all_minis,
        "gears_by_name": gears_by_name,
        "minis_by_name": minis_by_name,
    }


def run_ga(data, ga_depth=50):
    """Run the GA solver."""
    from gear_optimizer.solver.genetic import solve_coevolution_genetic
    
    np.random.seed(42)
    random.seed(42)
    
    best_data, best_gear, best_minis, _, _, _, _ = solve_coevolution_genetic(
        cfg=data["cfg"],
        base_stats_fixed=data["base_stats_fixed"],
        paths=None,
        calc_song=data["calc_song"],
        ref_arrays=data["ref_arrays"],
        all_gears=data["all_gears"],
        all_minis=data["all_minis"],
        gears_by_name=data["gears_by_name"],
        minis_by_name=data["minis_by_name"],
        optimize_gear=True,
        optimize_minis=True,
        ga_depth=ga_depth,
    )
    
    return best_data["Score"]


def profile_ga(ga_depth=50):
    """Profile the GA and output stats."""
    print("=" * 70)
    print(f"Profiling Genetic Algorithm (ga_depth={ga_depth})")
    print("=" * 70)
    
    # Setup data outside of profiling
    print("\nSetting up test data...")
    data = setup_ga_test_data()
    print("Test data ready.\n")
    
    # Profile the GA run
    profiler = cProfile.Profile()
    profiler.enable()
    
    score = run_ga(data, ga_depth)
    
    profiler.disable()
    
    print(f"\nFinal Score: {score}")
    print("\n" + "=" * 70)
    print("PROFILING RESULTS (Top 30 by cumulative time)")
    print("=" * 70)
    
    # Sort by cumulative time
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.strip_dirs()
    stats.sort_stats('cumulative')
    stats.print_stats(30)
    print(stream.getvalue())
    
    print("\n" + "=" * 70)
    print("PROFILING RESULTS (Top 30 by total time)")
    print("=" * 70)
    
    stream2 = io.StringIO()
    stats2 = pstats.Stats(profiler, stream=stream2)
    stats2.strip_dirs()
    stats2.sort_stats('tottime')
    stats2.print_stats(30)
    print(stream2.getvalue())
    
    # Save to file
    output_file = os.path.join(os.path.dirname(__file__), "ga_profile_results.txt")
    with open(output_file, "w") as f:
        f.write(f"GA Profiling Results (ga_depth={ga_depth})\n")
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
    return score


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Profile the Genetic Algorithm")
    parser.add_argument("--depth", type=int, default=50, help="GA depth (generations)")
    args = parser.parse_args()
    
    profile_ga(ga_depth=args.depth)
