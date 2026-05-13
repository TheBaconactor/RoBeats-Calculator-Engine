"""
Deep profile a real song to find where 40s is being spent.
"""

import os
import sys
import cProfile
import pstats
import io
import time

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

os.environ["GPU_PROFILER"] = "1"
os.environ["PERF_TIMING"] = "1"


def profile_real_song():
    """Profile processing a real song."""
    import configparser
    import numpy as np

    from gear_optimizer.data.song_io import read_song_file
    from gear_optimizer.legacy.song_processor_adapter import process_song_task
    from gear_optimizer.data.csv_parser import load_all_gears_list, load_all_minis_list, read_table
    from gear_optimizer.core.constants import PATHS, TOTAL_ROWS
    from gear_optimizer.core.config import load_paths_cache
    from gear_optimizer.core.utils import cfg_to_dict

    # Load config
    cfg = configparser.ConfigParser()
    cfg.read("config.ini", encoding="utf-8-sig")
    paths = load_paths_cache()

    # Load reference arrays
    stats_table = read_table(paths.get("Stats", "") or PATHS.stats_csv)
    stat_names = ["Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Fill Rate", "Fever Time"]
    ref_arrays = {}
    for i, name in enumerate(stat_names):
        temp_list = []
        for v in range(TOTAL_ROWS + 1):
            lookup_index = TOTAL_ROWS - v
            try:
                val = stats_table[lookup_index][i] if stats_table else 0
            except:
                val = 0
            temp_list.append(val)
        ref_arrays[name] = np.array(temp_list, dtype=np.float64)

    # Load gear/mini data
    all_gears = load_all_gears_list(paths)
    all_minis = load_all_minis_list(paths)
    gears_by_name = {g["Name"]: g for g in all_gears}
    minis_by_name = {m["Name"]: m for m in all_minis}

    # Find a test song
    song_file = r"Data\Hard\Guardian (Hard) by Hinkik.txt"
    if not os.path.exists(song_file):
        # Try another
        import glob

        songs = glob.glob(r"Data\Hard\*.txt")
        if songs:
            song_file = songs[0]
        else:
            print("No song files found!")
            return

    song_name = os.path.basename(song_file).replace(".txt", "")
    print(f"Profiling: {song_name}")
    print("=" * 60)

    # Build task args
    cfg_dict = cfg_to_dict(cfg)

    # Override for faster profiling
    cfg_dict["IterationEngine"] = cfg_dict.get("IterationEngine", {})
    cfg_dict["IterationEngine"]["GA_SearchDepth"] = "20"  # Reduce for profiling

    args = (
        song_file,
        song_name,
        "Hard",
        cfg_dict,
        paths,
        ref_arrays,
        all_gears,
        all_minis,
        gears_by_name,
        minis_by_name,
        True,  # auto_buff
        20,  # ga_depth (reduced)
        None,  # status_queue
        1,  # parallel_workers
        False,  # fg_debug
    )

    # Profile
    print(f"\nRunning with GA_SearchDepth=20...")
    t0 = time.perf_counter()

    pr = cProfile.Profile()
    pr.enable()

    result = process_song_task(args)

    pr.disable()

    elapsed = time.perf_counter() - t0

    print(f"\nCompleted in {elapsed:.2f}s")
    print(f"Score: {result.get('best_data', {}).get('Score', 'N/A')}")

    # Print top functions
    print("\n" + "=" * 60)
    print("TOP 30 FUNCTIONS BY CUMULATIVE TIME")
    print("=" * 60)

    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
    ps.print_stats(30)
    print(s.getvalue())

    # GPU profiler report
    from gear_optimizer.solver.gpu_profiler import get_gpu_profiler

    profiler = get_gpu_profiler()
    profiler.report()


if __name__ == "__main__":
    profile_real_song()
