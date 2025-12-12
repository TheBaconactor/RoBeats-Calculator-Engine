"""
Test parallel mode simulation - multiple workers submitting GPU requests.
"""
import pytest
import multiprocessing
import time
import numpy as np


def worker_task(worker_id, req_queue, resp_queue, genome_stats, grid_data, color_flags, ref_arrays):
    """Simulate a worker submitting GPU work."""
    from gear_optimizer.solver.gpu_executor import (
        set_gpu_worker_mode,
        submit_gpu_solve_genomes,
        is_gpu_worker_mode,
    )
    from gear_optimizer.solver.fever_timeline import SongTimelineGrid
    
    # Set worker mode
    set_gpu_worker_mode(worker_id, req_queue, resp_queue)
    assert is_gpu_worker_mode()
    
    # Reconstruct timeline grid from serialized data
    grid = SongTimelineGrid.__new__(SongTimelineGrid)
    grid.__dict__.update(grid_data)
    
    # Submit GPU work via IPC
    try:
        results = submit_gpu_solve_genomes(
            genome_stats_list=genome_stats,
            timeline_grid=grid,
            is_p_ft=color_flags["is_p_ft"],
            is_s_ft=color_flags["is_s_ft"],
            is_p_ff=color_flags["is_p_ff"],
            is_s_ff=color_flags["is_s_ff"],
            is_p_pp=color_flags["is_p_pp"],
            is_s_pp=color_flags["is_s_pp"],
            is_p_cm=color_flags["is_p_cm"],
            is_s_cm=color_flags["is_s_cm"],
            is_p_fm=color_flags["is_p_fm"],
            is_s_fm=color_flags["is_s_fm"],
            is_p_ov=color_flags["is_p_ov"],
            is_s_ov=color_flags["is_s_ov"],
            ref_arrays=ref_arrays,
            timeout=30.0,
        )
        return {"worker_id": worker_id, "success": True, "n_results": len(results)}
    except Exception as e:
        return {"worker_id": worker_id, "success": False, "error": str(e)}


def test_multi_worker_parallel_simulation():
    """
    Simulate multiple workers submitting GPU requests in parallel.
    
    This tests the full IPC flow:
    1. Main process starts GPU executor
    2. Workers are spawned and register with executor
    3. Workers submit GPU solve requests
    4. Results are returned via IPC
    """
    from gear_optimizer.solver.gpu_executor import GpuExecutor
    from gear_optimizer.solver.fever_timeline import SongTimelineGrid
    
    # Reset singleton
    GpuExecutor._instance = None
    executor = GpuExecutor()
    executor.start()
    time.sleep(1.5)  # Wait for Taichi init
    
    try:
        # Create minimal test data
        ref_arrays = {
            "Perfect Points": np.linspace(0, 100, 161, dtype=np.float64),
            "Combo Multiplier": np.linspace(1, 2, 161, dtype=np.float64),
            "Fever Multiplier": np.linspace(1, 2, 161, dtype=np.float64),
            "Fever Fill Rate": np.linspace(0.5, 1.5, 161, dtype=np.float64),
            "Fever Time": np.linspace(0.5, 1.5, 161, dtype=np.float64),
        }
        
        # Minimal genome stats
        genome_stats = [
            {"base_pp": 50, "base_cm": 50, "base_fm": 50, "base_p_val": 100, "base_s_val": 50, "base_ft_stat": 50, "base_ff_stat": 50},
            {"base_pp": 60, "base_cm": 60, "base_fm": 60, "base_p_val": 120, "base_s_val": 60, "base_ft_stat": 60, "base_ff_stat": 60},
        ]
        
        # Create a minimal calc_song structure for timeline grid
        timestamps = np.linspace(0, 100, 500)
        calc_song = {
            "song_data": {"timestamps": timestamps},
            "metadata": {
                "Long Notes": 10,
                "Last Note Time": 100.0,
                "Primary Color": "Chill",
                "Secondary Color": "Flow",
            }
        }
        
        grid = SongTimelineGrid(calc_song, ref_arrays)
        grid.precompute_all()
        
        # Serialize grid data for worker
        grid_data = grid.__dict__.copy()
        
        color_flags = {
            "is_p_ft": 0, "is_s_ft": 0,
            "is_p_ff": 0, "is_s_ff": 0,
            "is_p_pp": 0, "is_s_pp": 1,
            "is_p_cm": 0, "is_s_cm": 0,
            "is_p_fm": 0, "is_s_fm": 0,
            "is_p_ov": 1, "is_s_ov": 0,
        }
        
        # Register 2 workers
        n_workers = 2
        worker_configs = []
        for _ in range(n_workers):
            w_id, req_q, resp_q = executor.register_worker()
            worker_configs.append((w_id, req_q, resp_q))
        
        # Spawn worker processes
        mp_ctx = multiprocessing.get_context("spawn")
        
        processes = []
        for i, (w_id, req_q, resp_q) in enumerate(worker_configs):
            p = mp_ctx.Process(
                target=worker_task,
                args=(w_id, req_q, resp_q, genome_stats, grid_data, color_flags, ref_arrays),
            )
            processes.append(p)
        
        # Start all workers
        for p in processes:
            p.start()
        
        # Wait for completion
        for p in processes:
            p.join(timeout=30.0)
        
        # Check all completed
        for p in processes:
            assert not p.is_alive(), "Worker process hung"
            assert p.exitcode == 0, f"Worker exited with code {p.exitcode}"
        
        print(f"[TEST] All {n_workers} workers completed successfully!")
        
    finally:
        executor.stop()
        GpuExecutor._instance = None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
