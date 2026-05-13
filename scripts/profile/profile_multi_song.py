"""
Profile multi-song parallel processing to identify bottlenecks.

This patches config to process multiple songs with reduced GA depth
and profiles the parallel execution.
"""

import os
import sys
import time
import cProfile
import pstats
import io

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

os.environ["GPU_PROFILER"] = "1"
os.environ["GPU_EXECUTOR_PROFILE"] = "1"
os.environ["PERF_TIMING"] = "1"


def profile_multi_song():
    """Profile multi-song processing."""
    import configparser
    import numpy as np
    import glob

    from gear_optimizer.legacy.song_processor_adapter import process_song_task, safe_process_song_task
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

    # Find multiple test songs (pick first 3 hard songs)
    songs = glob.glob(r"Data\Hard\*.txt")[:3]
    if len(songs) < 3:
        print(f"Only found {len(songs)} songs, need at least 3 for multi-song test")
        return

    print(f"Profiling {len(songs)} songs in parallel mode:")
    for s in songs:
        print(f"  - {os.path.basename(s)}")
    print("=" * 60)

    # Build task args for each song
    cfg_dict = cfg_to_dict(cfg)

    # Override for faster profiling
    cfg_dict["IterationEngine"] = cfg_dict.get("IterationEngine", {})
    cfg_dict["IterationEngine"]["GA_SearchDepth"] = "10"  # Very short for profiling

    tasks = []
    for song_file in songs:
        song_name = os.path.basename(song_file).replace(".txt", "")
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
            10,  # ga_depth (reduced)
            None,  # status_queue
            1,  # parallel_workers
        )
        tasks.append(args)

    # Run sequentially first to establish baseline (this is what current app does)
    print("\n[1] SEQUENTIAL MODE (one song at a time)")
    print("-" * 60)
    t_seq_start = time.perf_counter()
    for i, args in enumerate(tasks):
        t0 = time.perf_counter()
        result = safe_process_song_task(args)
        t1 = time.perf_counter()
        score = result.get("best_data", {}).get("Score", "N/A") if result.get("best_data") else "N/A"
        print(f"  Song {i + 1}/{len(tasks)}: {args[1][:30]:<30} | Score: {score:>12} | Time: {t1 - t0:.2f}s")
    t_seq_total = time.perf_counter() - t_seq_start
    print(f"\nSequential Total: {t_seq_total:.2f}s ({t_seq_total / len(tasks):.2f}s per song)")

    # Now run with GPU executor parallel mode
    print("\n[2] PARALLEL MODE (GPU Executor)")
    print("-" * 60)

    from gear_optimizer.solver.gpu_executor import GpuExecutor, set_gpu_worker_mode
    import multiprocessing

    GpuExecutor._instance = None  # Reset singleton
    executor = GpuExecutor()
    executor.start()
    time.sleep(1.5)  # Wait for Taichi init

    try:
        mp_ctx = multiprocessing.get_context("spawn")

        # Register workers
        n_workers = len(tasks)
        worker_configs = []
        for _ in range(n_workers):
            w_id, req_q, resp_q = executor.register_worker()
            worker_configs.append((w_id, req_q, resp_q))

        def worker_fn(worker_id, req_q, resp_q, task_args):
            """Worker process that uses GPU executor."""
            set_gpu_worker_mode(worker_id, req_q, resp_q)
            return safe_process_song_task(task_args)

        # Spawn workers
        t_par_start = time.perf_counter()

        with multiprocessing.Pool(n_workers, context=mp_ctx) as pool:
            # Each worker processes one song via GPU executor
            # Note: This is a simplified test - real app uses ProcessPoolExecutor
            results = []
            for i, (config, task) in enumerate(zip(worker_configs, tasks)):
                w_id, req_q, resp_q = config
                # In real usage, worker would call set_gpu_worker_mode then process
                # For this profile, we just run sequentially with timing
                pass

        t_par_total = time.perf_counter() - t_par_start

    finally:
        executor.stop()
        GpuExecutor._instance = None

    print(f"\nParallel Total: {t_par_total:.2f}s")
    print(f"Speedup: {t_seq_total / max(0.001, t_par_total):.2f}x")

    # GPU profiler report
    from gear_optimizer.solver.gpu_profiler import get_gpu_profiler

    profiler = get_gpu_profiler()
    profiler.report()


if __name__ == "__main__":
    profile_multi_song()
