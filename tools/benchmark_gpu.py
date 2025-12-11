"""
GPU Benchmark Tool: Compare discrete GPU vs integrated GPU performance.

Usage:
    python tools/benchmark_gpu.py [--iterations 5]
    
    # To select a specific GPU, set TI_VISIBLE_DEVICE before running:
    set TI_VISIBLE_DEVICE=0 && python tools/benchmark_gpu.py   # GPU 0 (usually dGPU)
    set TI_VISIBLE_DEVICE=1 && python tools/benchmark_gpu.py   # GPU 1 (usually iGPU)

This script runs a standardized workload on the selected GPU and reports timing metrics.
"""
import sys
import os
import time
import argparse

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np


def run_benchmark(iterations: int = 5):
    """Run benchmark on the default GPU."""
    import taichi as ti
    
    print(f"\n{'='*60}")
    print(f"Benchmarking: Default GPU (Vulkan)")
    print(f"{'='*60}")
    
    # Initialize Taichi
    ti.init(arch=ti.vulkan, offline_cache=True)
    print(f"[OK] Taichi initialized")
    
    # Import solver after Taichi init
    from gear_optimizer.taichi_accelerator import TaichiSolver
    from gear_optimizer.constants import TOTAL_GEM_BUDGET
    
    # Create solver
    solver = TaichiSolver()
    
    # Generate synthetic test data
    np.random.seed(42)
    num_notes = 2000
    timestamps = np.sort(np.random.uniform(0, 180, num_notes)).astype(np.float64)
    long_notes = 50
    last_note_time = timestamps[-1]
    
    # Reference arrays (must match TaichiSolver field sizes: TOTAL_ROWS + 1 = 161)
    ref_size = 161  # TOTAL_ROWS + 1
    ref_pp = np.linspace(100, 1000, ref_size).astype(np.float64)
    ref_cm = np.linspace(1.0, 5.0, ref_size).astype(np.float64)
    ref_fm = np.linspace(1.0, 3.0, ref_size).astype(np.float64)
    ref_arrays = {
        "Perfect Points": ref_pp,
        "Combo Multiplier": ref_cm,
        "Fever Multiplier": ref_fm,
    }
    
    ft_factor = np.ones(161, dtype=np.float32)
    ff_factor = np.ones(161, dtype=np.float32)
    
    # Batch input (250 genomes like a typical population)
    batch_size = 250
    batch_input = {
        'song_indices': np.zeros(batch_size, dtype=np.int32),
        'base_beat': np.random.uniform(500, 2000, batch_size).astype(np.float32),
        'base_vibe': np.random.uniform(500, 2000, batch_size).astype(np.float32),
        'cur_pp': np.random.randint(100, 500, batch_size).astype(np.int32),
        'cur_cm': np.random.randint(100, 500, batch_size).astype(np.int32),
        'cur_fm': np.random.randint(100, 300, batch_size).astype(np.int32),
        # New base stats for mask lookup
        'base_ft_stat': np.random.randint(0, 160, batch_size).astype(np.int32),
        'base_ff_stat': np.random.randint(0, 160, batch_size).astype(np.int32),
        'is_p_pp': np.zeros(batch_size, dtype=np.int32),
        'is_s_pp': np.zeros(batch_size, dtype=np.int32),
        'is_p_cm': np.ones(batch_size, dtype=np.int32),
        'is_s_cm': np.zeros(batch_size, dtype=np.int32),
        'is_p_fm': np.zeros(batch_size, dtype=np.int32),
        'is_s_fm': np.ones(batch_size, dtype=np.int32),
        'is_p_ov': np.zeros(batch_size, dtype=np.int32),
        'is_s_ov': np.zeros(batch_size, dtype=np.int32),
        'p_color_is_beat': np.ones(batch_size, dtype=np.int32),
        'p_color_is_vibe': np.zeros(batch_size, dtype=np.int32),
        's_color_is_beat': np.zeros(batch_size, dtype=np.int32),
        's_color_is_vibe': np.ones(batch_size, dtype=np.int32),
        'p_color_base_val': np.random.uniform(500, 2000, batch_size).astype(np.float32),
        's_color_base_val': np.random.uniform(500, 2000, batch_size).astype(np.float32),
    }

    # Dummy genomes data for metadata (required by solve_batch for song key)
    dummy_genomes = [{
        'metadata': {
            'Song Name': 'Benchmark',
            'Long Notes': long_notes,
            'Last Note Time': last_note_time
        },
        'song_data': {
            'timestamps': timestamps
        }
    }] * batch_size
    
    range_ft = 100
    max_ff = 100
    total_budget = TOTAL_GEM_BUDGET
    
    # Warmup
    print("Warming up (kernel compilation)...")
    warmup_start = time.perf_counter()
    solver.ensure_song_loaded(
        timestamps, long_notes, last_note_time,
        ref_arrays,
        song_key="benchmark_song",
    )
    solver.solve_batch(
        batch_input, 
        ref_arrays, 
        total_budget, 
        solver_cfg=None, 
        genomes_data=dummy_genomes
    )
    ti.sync()
    warmup_time = time.perf_counter() - warmup_start
    print(f"  Warmup completed in {warmup_time*1000:.2f} ms")
    
    # Benchmark
    times = []
    print(f"\nRunning {iterations} timed iterations...")
    for i in range(iterations):
        start = time.perf_counter()
        solver.solve_batch(
            batch_input, 
            ref_arrays, 
            total_budget, 
            solver_cfg=None, 
            genomes_data=dummy_genomes
        )
        ti.sync()
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        print(f"  Iteration {i+1}: {elapsed*1000:.2f} ms")
    
    avg_time = np.mean(times)
    std_time = np.std(times)
    min_time = np.min(times)
    max_time = np.max(times)
    
    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    print(f"Batch Size:  {batch_size} genomes")
    print(f"Grid Size:   {range_ft+1} x {max_ff+1} = {(range_ft+1)*(max_ff+1)} FT/FF combinations")
    print(f"Gem Budget:  {total_budget}")
    print(f"")
    print(f"Average:     {avg_time*1000:.2f} ms")
    print(f"Std Dev:     {std_time*1000:.2f} ms")
    print(f"Min:         {min_time*1000:.2f} ms")
    print(f"Max:         {max_time*1000:.2f} ms")
    print(f"Throughput:  {batch_size / avg_time:.1f} genomes/sec")
    print(f"             {(range_ft+1)*(max_ff+1)*batch_size / avg_time:.0f} FT/FF cells/sec")
    
    print(f"\n[DONE] Benchmark complete.")


def main():
    parser = argparse.ArgumentParser(description="GPU Benchmark")
    parser.add_argument('--iterations', type=int, default=5,
                        help='Number of benchmark iterations (default: 5)')
    args = parser.parse_args()
    
    print("=" * 60)
    print("GPU Benchmark Tool")
    print("=" * 60)
    print(f"Iterations: {args.iterations}")
    
    # Check if device is being forced
    ti_device = os.environ.get('TI_VISIBLE_DEVICE')
    if ti_device:
        print(f"TI_VISIBLE_DEVICE={ti_device} (forcing GPU device {ti_device})")
    else:
        print("")
        print("TIP: To select a specific GPU, set TI_VISIBLE_DEVICE:")
        print("  set TI_VISIBLE_DEVICE=0 && python tools/benchmark_gpu.py  # dGPU")
        print("  set TI_VISIBLE_DEVICE=1 && python tools/benchmark_gpu.py  # iGPU")
    
    run_benchmark(args.iterations)


if __name__ == "__main__":
    main()
