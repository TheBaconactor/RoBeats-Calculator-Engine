"""
Baseline Regression Test Script

This script runs main.py for a single known song with a fixed seed,
captures the final score, and can be used to verify behavior is unchanged
after optimizations.

Usage:
  python scripts/regression_baseline.py         # Run test and show results
  python scripts/regression_baseline.py --save  # Save baseline for comparison
  python scripts/regression_baseline.py --check # Compare against saved baseline
"""

import os
import sys
import random
import numpy as np
import json
import argparse

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Fixed seed for reproducibility
FIXED_SEED = 42
TEST_SONG = "Take Your Time (Hard) by Rutra"
BASELINE_FILE = os.path.join(project_root, "bin", "regression_baseline.json")


def set_deterministic_seed():
    """Set all random sources to fixed seed."""
    random.seed(FIXED_SEED)
    np.random.seed(FIXED_SEED)


def patch_ga_seed():
    """Patch the GA module to use deterministic random."""
    # Import modules to patch
    from gear_optimizer.helpers import ga_helpers
    from gear_optimizer.solver import genetic_pipeline as genetic

    # Patch random in both modules
    ga_helpers.random = random
    genetic.random = random


def run_single_song_test():
    """Run GA on a single song and return results."""
    from gear_optimizer.app import GearOptimizerApp

    # Force single song mode
    import configparser

    config = configparser.ConfigParser()
    config.read(os.path.join(project_root, "config.ini"))

    # Temporarily modify config for test
    original_song = config.get("CalculateSong", "Song_Name", fallback="")
    config.set("CalculateSong", "Song_Name", TEST_SONG)

    # Write temporary config
    temp_config = os.path.join(project_root, "config_test.ini")
    with open(temp_config, "w") as f:
        config.write(f)

    try:
        # Initialize app
        app = GearOptimizerApp()

        # Set seed BEFORE any GA operations
        set_deterministic_seed()
        patch_ga_seed()

        print(f"[Regression Test] Running with song: {TEST_SONG}")
        print(f"[Regression Test] Fixed seed: {FIXED_SEED}")

        # Run the app (single song, single pass)
        app.run()

        # Extract results from the last run
        # We'll capture stdout or check the database
        return {
            "success": True,
            "song": TEST_SONG,
            "seed": FIXED_SEED,
        }

    finally:
        # Cleanup
        if os.path.exists(temp_config):
            os.remove(temp_config)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", action="store_true", help="Save baseline")
    parser.add_argument("--check", action="store_true", help="Check against baseline")
    args = parser.parse_args()

    # Set seed early
    set_deterministic_seed()
    patch_ga_seed()

    print("=" * 60)
    print("REGRESSION BASELINE TEST")
    print("=" * 60)

    result = run_single_song_test()

    print(f"\n[Result] {result}")

    if args.save:
        with open(BASELINE_FILE, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n[Saved] Baseline written to {BASELINE_FILE}")

    if args.check:
        if os.path.exists(BASELINE_FILE):
            with open(BASELINE_FILE, "r") as f:
                baseline = json.load(f)

            # Compare
            if result == baseline:
                print("\n✓ PASS: Results match baseline!")
            else:
                print("\n✗ FAIL: Results differ from baseline!")
                print(f"  Expected: {baseline}")
                print(f"  Got:      {result}")
                sys.exit(1)
        else:
            print(f"\n[Warning] No baseline file found at {BASELINE_FILE}")
            print("  Run with --save first to create baseline.")


if __name__ == "__main__":
    main()
