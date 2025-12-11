#!/usr/bin/env python3
"""
Main.py Profiling Harness

A standalone profiling tool that replicates main.py execution flow with fixed settings
to identify performance hotspots without modifying the production code.

Usage:
    python tools/profile_main.py                    # Run all tests (CPU + GPU)
    python tools/profile_main.py --cpu-only         # Run CPU tests only
    python tools/profile_main.py --gpu-only         # Run GPU tests only
    python tools/profile_main.py --song "Among Us"  # Use specific song

Output:
    bin/profile_cpu_metafinder_off.prof
    bin/profile_cpu_metafinder_on.prof
    bin/profile_gpu_metafinder_off.prof
    bin/profile_gpu_metafinder_on.prof
"""

import argparse
import configparser
import cProfile
import gc
import os
import pstats
import sys
import time
from io import StringIO

# Add project root to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)

import numpy as np

from gear_optimizer.constants import TOTAL_ROWS, BIN_DIR
from gear_optimizer.csv_parser import load_all_gears_list, load_all_minis_list, read_table
from gear_optimizer.config import load_paths_cache, find_and_cache_paths
from gear_optimizer.song_processor import process_song_task, scan_song_header
from gear_optimizer.database import init_db


# =============================================================================
# MOCK CONFIG BUILDER
# =============================================================================

def build_mock_config(
    metafinder: bool = False,
    use_gpu: bool = False,
    ga_depth: int = 50,
    force_greats: bool = False,
) -> dict:
    """
    Build a mock config dict that matches config.ini structure exactly.
    
    This replicates how main.py parses config.ini and converts it to a dict
    via cfg_to_dict() for passing to worker processes.
    """
    cfg = configparser.ConfigParser()
    
    # [IterationEngine] - Main control switches
    cfg.add_section("IterationEngine")
    cfg.set("IterationEngine", "MetaFinder", str(metafinder))
    cfg.set("IterationEngine", "UseEvolutionDB", "False")  # Don't touch real DB
    cfg.set("IterationEngine", "UseGPU", str(use_gpu))
    cfg.set("IterationEngine", "UseGPU_GA", str(use_gpu))  # GPU GA flag
    cfg.set("IterationEngine", "GA_SearchDepth", str(ga_depth))
    cfg.set("IterationEngine", "ForceGreatsMode", str(force_greats))
    cfg.set("IterationEngine", "ForceGreatsFinder", "False")
    cfg.set("IterationEngine", "AutoSelectBuffAndColor", "True")
    cfg.set("IterationEngine", "EvalCPUCores", "0")  # Use all cores
    cfg.set("IterationEngine", "LoopForever", "False")
    cfg.set("IterationEngine", "GA_ParallelSongs", "1")
    
    # [CalculateSong] - Song selection
    cfg.add_section("CalculateSong")
    cfg.set("CalculateSong", "Difficulty", "Normal")
    cfg.set("CalculateSong", "Song_Name", "")
    cfg.set("CalculateSong", "TargetPrimary", "All")
    cfg.set("CalculateSong", "TargetSecondary", "All")
    
    # [UserInputStats] - Base stats (zeros = let solver optimize)
    cfg.add_section("UserInputStats")
    cfg.set("UserInputStats", "pp", "0")
    cfg.set("UserInputStats", "cm", "0")
    cfg.set("UserInputStats", "fm", "0")
    cfg.set("UserInputStats", "ff", "0")
    cfg.set("UserInputStats", "ft", "0")
    
    # [UserInputStatsGems] - Gem allocations (zeros = let solver optimize)
    cfg.add_section("UserInputStatsGems")
    cfg.set("UserInputStatsGems", "perfect_points", "0")
    cfg.set("UserInputStatsGems", "combo_multiplier", "0")
    cfg.set("UserInputStatsGems", "fever_multiplier", "0")
    cfg.set("UserInputStatsGems", "fever_fill", "0")
    cfg.set("UserInputStatsGems", "fever_time", "0")
    
    # [ElementalGems] - Elemental gems (zeros)
    cfg.add_section("ElementalGems")
    cfg.set("ElementalGems", "Chill", "0")
    cfg.set("ElementalGems", "Flow", "0")
    cfg.set("ElementalGems", "Rush", "0")
    cfg.set("ElementalGems", "Beat", "0")
    cfg.set("ElementalGems", "Vibe", "0")
    
    # [UserInputPrimaryGear] - No fixed gear
    cfg.add_section("UserInputPrimaryGear")
    cfg.set("UserInputPrimaryGear", "enabled", "False")
    cfg.set("UserInputPrimaryGear", "Name", "")
    
    # [UserInputSecondaryGear] - No fixed gear
    cfg.add_section("UserInputSecondaryGear")
    cfg.set("UserInputSecondaryGear", "enabled", "False")
    cfg.set("UserInputSecondaryGear", "Name", "")
    
    # [UserInputMinis] - No fixed minis
    cfg.add_section("UserInputMinis")
    cfg.set("UserInputMinis", "enabled", "False")
    cfg.set("UserInputMinis", "Mini1", "")
    cfg.set("UserInputMinis", "Mini2", "")
    cfg.set("UserInputMinis", "Mini3", "")
    
    # [ForceGreats] - Force greats config (if enabled)
    cfg.add_section("ForceGreats")
    for i in range(10):
        cfg.set("ForceGreats", f"NonFever{i}", "0")
    
    # Convert to dict (matching cfg_to_dict from utils.py)
    cfg_dict = {}
    for section in cfg.sections():
        cfg_dict[section] = dict(cfg.items(section))
    
    return cfg_dict


# =============================================================================
# DATA LOADING (mirrors main.py)
# =============================================================================

def load_reference_arrays(stats_path: str) -> dict:
    """Load reference arrays exactly as main.py does."""
    stats_table = read_table(stats_path)
    
    stat_names = [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Fill Rate",
        "Fever Time",
    ]
    ref_arrays = {}
    for i, name in enumerate(stat_names):
        temp_list = []
        for v in range(TOTAL_ROWS + 1):
            lookup_index = TOTAL_ROWS - v
            try:
                val = stats_table[lookup_index][i] if stats_table else 0
            except Exception:
                val = 0
            temp_list.append(val)
        ref_arrays[name] = np.array(temp_list, dtype=np.float64)
    
    return ref_arrays


def find_song_file(paths: dict, song_filter: str = "") -> tuple:
    """
    Find a song file to use for profiling.
    
    Returns:
        Tuple of (file_path, song_name, difficulty)
    """
    # Try Normal difficulty first
    search_dirs = []
    for diff in ["Normal", "Hard", "Easy"]:
        if paths.get(diff):
            search_dirs.append((paths[diff], diff))
    
    # Also try Data folder structure
    data_dir = os.path.join(PROJECT_ROOT, "Data")
    for diff in ["Normal", "Hard", "Easy"]:
        diff_dir = os.path.join(data_dir, diff)
        if os.path.exists(diff_dir):
            search_dirs.append((diff_dir, diff))
    
    for search_dir, difficulty in search_dirs:
        if not os.path.exists(search_dir):
            continue
        
        for root, _, files in os.walk(search_dir):
            for f in files:
                if not f.lower().endswith(".txt"):
                    continue
                
                fp = os.path.join(root, f)
                meta = scan_song_header(fp)
                if not meta:
                    continue
                
                song_name = meta.get("Song Name", "")
                if not song_name:
                    continue
                
                # Match song filter if provided
                if song_filter and song_filter.lower() not in song_name.lower():
                    continue
                
                return fp, song_name, difficulty
    
    return None, None, None


# =============================================================================
# PROFILING RUNNER
# =============================================================================

def run_profile_test(
    name: str,
    cfg_dict: dict,
    paths: dict,
    ref_arrays: dict,
    all_gears: list,
    all_minis: list,
    gears_by_name: dict,
    minis_by_name: dict,
    song_file: str,
    song_name: str,
    difficulty: str,
) -> tuple:
    """
    Run a single profiling test.
    
    Returns:
        Tuple of (elapsed_time, result_dict, profile_stats)
    """
    print(f"\n{'='*60}")
    print(f"PROFILE TEST: {name}")
    print(f"{'='*60}")
    print(f"Song: {song_name}")
    print(f"Difficulty: {difficulty}")
    print(f"MetaFinder: {cfg_dict['IterationEngine']['metafinder']}")
    print(f"UseGPU: {cfg_dict['IterationEngine']['usegpu']}")
    
    # Build task args tuple (matching main.py exactly)
    args = (
        song_file,           # fp
        song_name,           # found_song_name
        difficulty,          # effective_difficulty
        cfg_dict,            # cfg_dict
        paths,               # paths
        ref_arrays,          # ref_arrays
        all_gears,           # all_gears
        all_minis,           # all_minis
        gears_by_name,       # gears_by_name
        minis_by_name,       # minis_by_name
        False,               # use_evo_db (don't touch real DB)
        True,                # auto_buff
        50,                  # ga_depth
        None,                # status_queue
        1,                   # parallel_workers
    )
    
    # Profile the task
    profiler = cProfile.Profile()
    
    gc.collect()
    start_time = time.perf_counter()
    
    profiler.enable()
    try:
        result = process_song_task(args)
    except Exception as e:
        print(f"ERROR: {e}")
        result = {"error": str(e)}
    profiler.disable()
    
    elapsed = time.perf_counter() - start_time
    
    # Get stats
    stats_stream = StringIO()
    stats = pstats.Stats(profiler, stream=stats_stream)
    stats.strip_dirs()
    stats.sort_stats("cumulative")
    stats.print_stats(30)  # Top 30 functions
    
    print(f"\nElapsed time: {elapsed:.2f}s")
    print(f"\nTop hotspots:")
    print(stats_stream.getvalue())
    
    # Save profile for snakeviz
    output_file = os.path.join(BIN_DIR, f"profile_{name}.prof")
    profiler.dump_stats(output_file)
    print(f"Profile saved to: {output_file}")
    print(f"View with: snakeviz {output_file}")
    
    return elapsed, result, stats


def run_all_profiles(song_filter: str = "", cpu_only: bool = False, gpu_only: bool = False):
    """Run all profiling tests (CPU and GPU, MetaFinder ON and OFF)."""
    
    print("="*60)
    print("MAIN.PY PROFILING HARNESS")
    print("="*60)
    
    # Ensure paths cache exists
    paths = load_paths_cache()
    if not paths:
        print("Discovering data paths...")
        paths = find_and_cache_paths()
    
    if not paths:
        print("ERROR: Could not find data paths. Ensure Data/ folder exists.")
        return
    
    # Find song file
    song_file, song_name, difficulty = find_song_file(paths, song_filter)
    if not song_file:
        print(f"ERROR: No song file found{' matching filter: ' + song_filter if song_filter else ''}")
        return
    
    print(f"Using song: {song_name} ({difficulty})")
    print(f"File: {song_file}")
    
    # Load data (once, shared across tests)
    stats_path = paths.get("Stats") or os.path.join(PROJECT_ROOT, "Data", "Gear", "Stats.txt")
    print(f"Loading reference arrays from: {stats_path}")
    ref_arrays = load_reference_arrays(stats_path)
    
    print("Loading gears and minis...")
    all_gears = load_all_gears_list(paths)
    all_minis = load_all_minis_list(paths)
    gears_by_name = {g["Name"]: g for g in all_gears}
    minis_by_name = {m["Name"]: m for m in all_minis}
    
    print(f"Loaded {len(all_gears)} gears, {len(all_minis)} minis")
    
    # Initialize database (needed for some code paths)
    init_db()
    
    # Ensure output directory exists
    os.makedirs(BIN_DIR, exist_ok=True)
    
    results = {}
    
    # Define test configurations
    tests = []
    
    if not gpu_only:
        tests.extend([
            ("cpu_metafinder_off", False, False),   # CPU, Calculate-only
            ("cpu_metafinder_on", True, False),     # CPU, Full GA
        ])
    
    if not cpu_only:
        tests.extend([
            ("gpu_metafinder_off", False, True),    # GPU, Calculate-only
            ("gpu_metafinder_on", True, True),      # GPU, Full GA
        ])
    
    for test_name, metafinder, use_gpu in tests:
        cfg_dict = build_mock_config(
            metafinder=metafinder,
            use_gpu=use_gpu,
            ga_depth=50,  # Standard depth
        )
        
        elapsed, result, stats = run_profile_test(
            name=test_name,
            cfg_dict=cfg_dict,
            paths=paths,
            ref_arrays=ref_arrays,
            all_gears=all_gears,
            all_minis=all_minis,
            gears_by_name=gears_by_name,
            minis_by_name=minis_by_name,
            song_file=song_file,
            song_name=song_name,
            difficulty=difficulty,
        )
        
        results[test_name] = {
            "elapsed": elapsed,
            "score": result.get("best_data", {}).get("Score", 0) if result else 0,
        }
        
        # Force cleanup between tests
        gc.collect()
    
    # Summary
    print("\n" + "="*60)
    print("PROFILING SUMMARY")
    print("="*60)
    
    for test_name, data in results.items():
        print(f"{test_name:30s}: {data['elapsed']:8.2f}s  Score: {data['score']:,.0f}")
    
    print("\nProfile files saved to bin/ directory.")
    print("View with: snakeviz bin/profile_<name>.prof")


def main():
    parser = argparse.ArgumentParser(
        description="Main.py Profiling Harness - Find hotspots without modifying production code"
    )
    parser.add_argument(
        "--song", "-s",
        type=str,
        default="",
        help="Song name filter (partial match)"
    )
    parser.add_argument(
        "--cpu-only",
        action="store_true",
        help="Run CPU tests only"
    )
    parser.add_argument(
        "--gpu-only",
        action="store_true",
        help="Run GPU tests only"
    )
    
    args = parser.parse_args()
    
    if args.cpu_only and args.gpu_only:
        print("ERROR: Cannot specify both --cpu-only and --gpu-only")
        return
    
    run_all_profiles(
        song_filter=args.song,
        cpu_only=args.cpu_only,
        gpu_only=args.gpu_only,
    )


if __name__ == "__main__":
    main()
