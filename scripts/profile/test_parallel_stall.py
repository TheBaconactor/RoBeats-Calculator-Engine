"""
Minimal reproduction of multi-song parallel stall using PROCESSES (not threads).

This matches the real app's spawn-based ProcessPoolExecutor pattern.
"""
import os
import sys
import time
import multiprocessing

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Enable verbose profiling
os.environ["GPU_EXECUTOR_PROFILE"] = "1"
os.environ["PERF_TIMING"] = "1"


def worker_process_fn(worker_id, req_q, resp_q, song_name, num_notes):
    """Worker process that submits GPU request."""
    from gear_optimizer.solver.gpu_executor import (
        set_gpu_worker_mode, submit_gpu_solve_genomes, clear_gpu_worker_mode
    )
    import numpy as np
    
    set_gpu_worker_mode(worker_id, req_q, resp_q)
    
    # Create fake data
    ref_arrays = {
        "Perfect Points": np.arange(161, dtype=np.float64),
        "Combo Multiplier": np.arange(161, dtype=np.float64),
        "Fever Multiplier": np.arange(161, dtype=np.float64),
        "Fever Time": np.arange(161, dtype=np.float64),
        "Fever Fill Rate": np.arange(161, dtype=np.float64),
    }
    
    song = {
        "metadata": {
            "Song Name": song_name,
            "Long Notes": 10,
            "Last Note Time": 120.0,
            "Primary Color": "Rush",
            "Secondary Color": "Vibe",
        },
        "song_data": {
            "timestamps": list(range(num_notes)),
        }
    }
    
    genomes = [
        {
            "base_pp": 50,
            "base_cm": 50,
            "base_fm": 50,
            "base_p_val": 100,
            "base_s_val": 50,
            "base_ft_stat": 0,
            "base_ff_stat": 0,
        }
        for _ in range(100)  # 100 genomes
    ]
    
    try:
        t0 = time.perf_counter()
        print(f"[Worker {worker_id}] Submitting {len(genomes)} genomes for {song_name}...")
        
        # Run 3 times to verify cache benefit
        total_dt = 0
        for i in range(3):
            t_sub = time.perf_counter()
            result = submit_gpu_solve_genomes(
                genome_stats_list=genomes,
                timeline_grid=song,
                is_p_ft=0, is_s_ft=0,
                is_p_ff=0, is_s_ff=0,
                is_p_pp=1, is_s_pp=0,
                is_p_cm=1, is_s_cm=0,
                is_p_fm=1, is_s_fm=0,
                is_p_ov=1, is_s_ov=0,
                ref_arrays=ref_arrays,
                timeout=120.0,
            )
            dt_sub = time.perf_counter() - t_sub
            total_dt += dt_sub
            print(f"[Worker {worker_id}] Iter {i}: {len(result)} results in {dt_sub:.2f}s")
            
        dt = total_dt
        print(f"[Worker {worker_id}] Total 3 iters in {dt:.2f}s")
        return {"worker_id": worker_id, "count": len(result), "time": dt}

        
    except Exception as e:
        print(f"[Worker {worker_id}] ERROR: {e}")
        return {"worker_id": worker_id, "error": str(e)}


def test_with_processes():
    """Test using actual spawn processes like the real app."""
    from gear_optimizer.solver.gpu_executor import GpuExecutor
    import concurrent.futures
    
    print("="*60)
    print("TEST: GPU Executor with SPAWN Processes (like real app)")
    print("="*60)
    
    # Reset singleton
    GpuExecutor._instance = None
    executor = GpuExecutor()
    
    # Start executor
    executor.start()
    time.sleep(2)  # Wait for Taichi init
    
    if not executor.is_running:
        print("ERROR: Executor failed to start")
        return
    
    print(f"[OK] Executor started, Taichi ready: {executor._taichi_ready}")
    
    n_workers = 5
    
    # Register workers (in main process)
    registrations = []
    for i in range(n_workers):
        worker_id, req_q, resp_q = executor.register_worker()
        registrations.append((worker_id, req_q, resp_q))
        print(f"  Registered worker {worker_id}")
    
    print(f"\n[Test] Spawning {n_workers} processes...")
    
    mp_ctx = multiprocessing.get_context("spawn")
    
    try:
        t_start = time.perf_counter()
        
        # Spawn processes
        processes = []
        for i, (worker_id, req_q, resp_q) in enumerate(registrations):
            song_name = f"Song_{i}"
            num_notes = 100 + i * 10
            p = mp_ctx.Process(
                target=worker_process_fn,
                args=(worker_id, req_q, resp_q, song_name, num_notes)
            )
            processes.append(p)
            p.start()
        
        # Wait for all processes
        for p in processes:
            p.join(timeout=180)
            if p.is_alive():
                print(f"WARNING: Process {p.pid} still running after 180s!")
                p.terminate()
        
        t_total = time.perf_counter() - t_start
        print(f"\n[Summary] Total time for {n_workers} spawned processes: {t_total:.2f}s")
        
    finally:
        executor.stop()
        GpuExecutor._instance = None


if __name__ == "__main__":
    test_with_processes()
