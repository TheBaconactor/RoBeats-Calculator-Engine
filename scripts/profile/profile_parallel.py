"""
Profile parallel mode IPC overhead vs sequential direct calls.

Measures:
1. Direct GPU calls (sequential mode)
2. IPC queue overhead (parallel mode simulation)
"""

import os
import sys
import time
import multiprocessing

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

os.environ["GPU_PROFILER"] = "1"

import numpy as np


def run_sequential_benchmark(n_batches=5):
    """Benchmark direct GPU calls (no IPC)."""
    from gear_optimizer.solver.taichi_gem.api import solve_genomes_parallel
    from gear_optimizer.solver.fever_timeline import SongTimelineGrid
    
    ref_arrays = {
        "Perfect Points": np.linspace(0, 100, 161, dtype=np.float64),
        "Combo Multiplier": np.linspace(1, 2, 161, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.5, 3.1, 161, dtype=np.float64),
        "Fever Fill Rate": np.linspace(0.5, 1.8, 161, dtype=np.float64),
        "Fever Time": np.linspace(0.5, 1.8, 161, dtype=np.float64),
    }
    
    n_genomes = 500
    genome_stats = [
        {"base_pp": 50+i%20, "base_cm": 50+i%15, "base_fm": 50+i%10,
         "base_p_val": 100+i%30, "base_s_val": 50+i%20,
         "base_ft_stat": 30+i%40, "base_ff_stat": 30+i%40}
        for i in range(n_genomes)
    ]
    
    timestamps = np.linspace(0, 120, 800)
    calc_song = {
        "song_data": {"timestamps": timestamps},
        "metadata": {"Long Notes": 20, "Last Note Time": 120.0,
                     "Primary Color": "Chill", "Secondary Color": "Flow"}
    }
    grid = SongTimelineGrid(calc_song, ref_arrays)
    
    # Warmup
    _ = solve_genomes_parallel(genome_stats[:10], grid, 0,0,0,0,1,0,0,1,0,0,1,0, ref_arrays)
    
    times = []
    for i in range(n_batches):
        t0 = time.perf_counter()
        _ = solve_genomes_parallel(genome_stats, grid, 0,0,0,0,1,0,0,1,0,0,1,0, ref_arrays)
        times.append(time.perf_counter() - t0)
    
    return times


def worker_process(worker_id, req_queue, resp_queue, n_requests):
    """Simulate worker submitting GPU requests via IPC."""
    from gear_optimizer.solver.gpu_executor import set_gpu_worker_mode, submit_gpu_solve_genomes
    import numpy as np
    
    set_gpu_worker_mode(worker_id, req_queue, resp_queue)
    
    ref_arrays = {
        "Perfect Points": np.linspace(0, 100, 161, dtype=np.float64),
        "Combo Multiplier": np.linspace(1, 2, 161, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.5, 3.1, 161, dtype=np.float64),
        "Fever Fill Rate": np.linspace(0.5, 1.8, 161, dtype=np.float64),
        "Fever Time": np.linspace(0.5, 1.8, 161, dtype=np.float64),
    }
    
    n_genomes = 500
    genome_stats = [
        {"base_pp": 50+i%20, "base_cm": 50+i%15, "base_fm": 50+i%10,
         "base_p_val": 100+i%30, "base_s_val": 50+i%20,
         "base_ft_stat": 30+i%40, "base_ff_stat": 30+i%40}
        for i in range(n_genomes)
    ]
    
    timestamps = np.linspace(0, 120, 800)
    # In real parallel mode we pass `calc_song` (lightweight) and let the GPU
    # executor precompute the 161×161 timeline grid on GPU.
    calc_song = {
        "song_data": {"timestamps": timestamps},
        "metadata": {
            "Long Notes": 20,
            "Last Note Time": 120.0,
            "Primary Color": "Chill",
            "Secondary Color": "Flow",
            "Song Name": f"PROFILE_WORKER_{worker_id}",
        },
    }
    
    times = []
    for i in range(n_requests):
        t0 = time.perf_counter()
        _ = submit_gpu_solve_genomes(
            genome_stats, calc_song, 0,0,0,0,1,0,0,1,0,0,1,0, ref_arrays
        )
        times.append(time.perf_counter() - t0)
    
    return times


def run_parallel_benchmark(n_workers=3, n_requests_per_worker=2):
    """Benchmark IPC overhead with GPU executor."""
    from gear_optimizer.solver.gpu_executor import GpuExecutor
    
    GpuExecutor._instance = None
    executor = GpuExecutor()
    executor.start()
    time.sleep(1.5)  # Wait for Taichi init
    
    try:
        mp_ctx = multiprocessing.get_context("spawn")
        
        # Register workers
        worker_configs = []
        for _ in range(n_workers):
            w_id, req_q, resp_q = executor.register_worker()
            worker_configs.append((w_id, req_q, resp_q))
        
        # Spawn workers
        processes = []
        for w_id, req_q, resp_q in worker_configs:
            p = mp_ctx.Process(target=worker_process, args=(w_id, req_q, resp_q, n_requests_per_worker))
            processes.append(p)
        
        t0 = time.perf_counter()
        for p in processes:
            p.start()
        for p in processes:
            p.join(timeout=120)
        total_time = time.perf_counter() - t0
        
        return total_time, n_workers * n_requests_per_worker
        
    finally:
        executor.stop()
        GpuExecutor._instance = None


def main():
    print("=" * 60)
    print("SEQUENTIAL vs PARALLEL BENCHMARK")
    print("=" * 60)
    
    # Sequential
    print("\n[1] Sequential (Direct GPU calls)...")
    seq_times = run_sequential_benchmark(n_batches=6)
    seq_avg = np.mean(seq_times[1:])  # Skip first (JIT)
    print(f"    Avg per batch: {seq_avg:.3f}s")
    print(f"    Total 5 batches: {sum(seq_times[1:]):.3f}s")
    
    # Parallel
    print("\n[2] Parallel (3 workers x 2 requests via IPC)...")
    par_total, par_count = run_parallel_benchmark(n_workers=3, n_requests_per_worker=2)
    print(f"    Total time: {par_total:.3f}s")
    print(f"    Requests: {par_count}")
    print(f"    Avg per request: {par_total / par_count:.3f}s")
    
    # Compare
    print("\n" + "=" * 60)
    print("COMPARISON")
    print("=" * 60)
    seq_total_6 = sum(seq_times[1:]) + seq_times[0]  # 6 batches
    print(f"Sequential (6 batches): {seq_total_6:.3f}s")
    print(f"Parallel   (6 batches): {par_total:.3f}s")
    print(f"Overhead: {(par_total - seq_total_6):.3f}s ({(par_total/seq_total_6 - 1)*100:.1f}%)")


if __name__ == "__main__":
    main()
