
"""
CPU Benchmark Tool: Test parallel CPU performance across cores.
Simulates the same workload as the GPU benchmark but using cpu process pool.
"""
import sys
import os
import time
import argparse
import numpy as np
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gear_optimizer.scoring import worker_coevolution_evaluate, GEM_SOLVER_CACHE
from gear_optimizer.constants import TOTAL_GEM_BUDGET

def run_benchmark(iterations: int = 5, num_workers: int = None):
    if num_workers is None:
        num_workers = multiprocessing.cpu_count()
        
    print(f"\n{'='*60}")
    print(f"Benchmarking: CPU (Numba JIT) with {num_workers} workers")
    print(f"{'='*60}")

    # Generate synthetic test data
    np.random.seed(42)
    
    # Reference arrays
    ref_size = 161
    ref_pp = np.linspace(100, 1000, ref_size).astype(np.float64)
    ref_cm = np.linspace(1.0, 5.0, ref_size).astype(np.float64)
    ref_fm = np.linspace(1.0, 3.0, ref_size).astype(np.float64)
    ref_arrays = {
        "Perfect Points": ref_pp,
        "Combo Multiplier": ref_cm,
        "Fever Multiplier": ref_fm,
        "Fever Time": np.ones(ref_size, dtype=np.float64),
        "Fever Fill Rate": np.ones(ref_size, dtype=np.float64)
    }
    
    # Batch input (250 genomes)
    batch_size = 250
    total_budget = TOTAL_GEM_BUDGET
    
    # Synthesize Song
    num_notes = 2000
    timestamps = np.sort(np.random.uniform(0, 180, num_notes)).astype(np.float64)
    calc_song = {
        "metadata": {
            "Long Notes": 50,
            "Last Note Time": 180.0,
            "Primary Color": "Beat",
            "Secondary Color": "Vibe"
        },
        "song_data": {
            "timestamps": timestamps
        }
    }
    
    # Synthesize Config
    cfg_data = {
        "selected_color": "Beat",
        "gem_count": total_budget,
        "use_gpu": False, # Enforce CPU
        "fever_mul_range": (1.0, 3.0),
        "skip_optimizer": False,
        "user_ft": -1, # Auto
        "user_ff": -1, # Auto
        "user_pp": 0,
        "user_cm": 0,
        "user_fm": 0,
        "static_elem_input": False,
        "force_gem_combo": None 
    }
    
    # Prepare payloads
    payloads = []
    base_stats_fixed = {
        "Beat": 1000, "Vibe": 1000, 
        "Perfect Points": 100,
        "Combo Multiplier": 100,
        "Fever Multiplier": 100,
        "Fever Time": 0,
        "Fever Fill Rate": 0,
        "Rush": 0, "Chill": 0, "Flow": 0, "Pop": 0
    }
    
    for _ in range(batch_size):
        # Randomize genome (list of 9 items)
        # Each item adds some random stats
        genome = []
        for _ in range(9):
            item = {
                "Name": f"Item_{np.random.randint(1000)}",
                "Beat": np.random.randint(10, 100),
                "Vibe": np.random.randint(10, 100),
                "Perfect Points": np.random.randint(1, 10),
                "Combo Multiplier": np.random.randint(1, 5),
                "Fever Multiplier": np.random.randint(1, 5)
            }
            genome.append(item)
            
        # (genome, base_stats_fixed, cfg_data, calc_song, ref_arrays)
        payload = (genome, base_stats_fixed, cfg_data, calc_song, ref_arrays)
        payloads.append(payload)

    # Benchmark
    times = []
    print(f"\nRunning {iterations} timed iterations...")
    
    # Ensure cache is clear so we actually compute
    GEM_SOLVER_CACHE.clear()

    # Pre-warm JIT in main process
    print("Warming JIT...")
    worker_coevolution_evaluate(payloads[0])
    
    # We use ProcessPoolExecutor to simulate true parallelism
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        for i in range(iterations):
            # Clear cache to force re-computation each iteration (if using thread pool this would matter)
            # With ProcessPool, memory is separate, but good to be safe if implementation changes
            GEM_SOLVER_CACHE.clear() 
            
            start = time.perf_counter()
            # We map the worker function over payloads
            # worker_coevolution_evaluate is pickleable so this works
            list(executor.map(worker_coevolution_evaluate, payloads))
            
            elapsed = time.perf_counter() - start
            times.append(elapsed)
            print(f"  Iteration {i+1}: {elapsed*1000:.2f} ms")

    avg_time = np.mean(times)
    
    print(f"\n{'='*60}")
    print(f"RESULTS (CPU - {num_workers} workers)")
    print(f"{'='*60}")
    print(f"Batch Size:  {batch_size} genomes")
    print(f"Average:     {avg_time*1000:.2f} ms")
    print(f"Throughput:  {batch_size / avg_time:.1f} genomes/sec")
    print(f"Speedup vs 1 core (est): {num_workers}x (theoretical)")
    print(f"")
    print(f"[DONE] Benchmark complete.")

def main():
    parser = argparse.ArgumentParser(description="CPU Benchmark")
    parser.add_argument('--iterations', type=int, default=5, help='Number of iterations')
    parser.add_argument('--workers', type=int, default=24, help='Number of CPU workers')
    args = parser.parse_args()
    
    run_benchmark(args.iterations, args.workers)

if __name__ == "__main__":
    main()
