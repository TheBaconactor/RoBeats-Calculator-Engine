"""
Test GA with GPU Gem Solver enabled.

Verifies that the GPU gem solver produces the same results when used
through the full GA pipeline.
"""

import sys
from pathlib import Path
import numpy as np
import random

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def run_ga_gpu_test():
    print("=" * 60)
    print("GA GPU Integration Test")
    print("=" * 60)

    SEED = 42

    from gear_optimizer.solver.genetic_pipeline import solve_coevolution_genetic
    from gear_optimizer.core.constants import TOTAL_ROWS

    # Generate deterministic mock data
    np.random.seed(SEED)
    random.seed(SEED)

    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]

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

    timestamps = np.linspace(0, 120, 100).tolist()
    calc_song = {
        "metadata": {
            "Song Name": "GPU GA Test Song",
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

    rows = TOTAL_ROWS + 1
    ref_arrays = {
        "Perfect Points": np.linspace(1.0, 2.0, rows),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows),
        "Fever Time": np.linspace(1.0, 2.5, rows),
    }

    class MockCfgGPU:
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
            return fallback

        def getboolean(self, section, option, fallback=False):
            val = self.get(section, option, fallback)
            if isinstance(val, bool):
                return val
            if str(val).lower() in ("true", "1", "yes"):
                return True
            return False

        def getint(self, section, option, fallback=0):
            try:
                return int(self.get(section, option, fallback))
            except (TypeError, ValueError):
                return int(fallback)

        def getfloat(self, section, option, fallback=0.0):
            try:
                return float(self.get(section, option, fallback))
            except (TypeError, ValueError):
                return float(fallback)

    # Run with GPU
    print("\nRunning GA with GPU Gem Solver...")
    np.random.seed(SEED)
    random.seed(SEED)

    best_data, best_gear, best_minis, _, _, _, _ = solve_coevolution_genetic(
        cfg=MockCfgGPU(),
        base_stats_fixed=base_stats_fixed,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        all_gears=all_gears,
        all_minis=all_minis,
        optimize_gear=True,
        optimize_minis=True,
        ga_depth=10,
    )

    gpu_score = best_data["Score"]
    print(f"\nGPU GA Score: {gpu_score}")

    # Expected score from CPU regression
    expected_score = 1662978

    print("\n" + "=" * 60)
    if gpu_score == expected_score:
        print(f"[PASS] GPU GA ({gpu_score}) == expected ({expected_score})")
    else:
        print(f"[FAIL] GPU GA ({gpu_score}) != expected ({expected_score})")
        print(f"  Diff: {gpu_score - expected_score}")
        print("  (Note: Minor differences may be due to GPU floating point)")
    print("=" * 60)

    return gpu_score == expected_score


if __name__ == "__main__":
    success = run_ga_gpu_test()
    sys.exit(0 if success else 1)
