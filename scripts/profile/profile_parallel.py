"""
Profile parallel mode IPC overhead vs sequential direct calls.

Measures:
1. Direct GPU calls (sequential mode)
2. IPC queue overhead (parallel mode simulation)
"""

import multiprocessing
import os
import sys
import time

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

os.environ["GPU_PROFILER"] = "1"

import numpy as np


def _mk_item(name: str, **stats: int) -> dict:
    out = {"Name": name}
    out.update({k: int(v) for k, v in (stats or {}).items()})
    return out


def _build_registry_inputs(n_genomes=500):
    from gear_optimizer.solver.base_stats import build_base_fixed_stats_array
    from gear_optimizer.solver.item_registry import ItemRegistry

    ref_arrays = {
        "Perfect Points": np.linspace(0, 100, 161, dtype=np.float64),
        "Combo Multiplier": np.linspace(1, 2, 161, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.5, 3.1, 161, dtype=np.float64),
        "Fever Fill Rate": np.linspace(0.5, 1.8, 161, dtype=np.float64),
        "Fever Time": np.linspace(0.5, 1.8, 161, dtype=np.float64),
    }

    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gear_pool = {
        slot: [
            _mk_item(
                f"{slot}_{i}",
                **{
                    "Perfect Points": 10 + i,
                    "Combo Multiplier": 5 + i,
                    "Fever Multiplier": 4 + i,
                    "Fever Time": 3 + i,
                    "Fever Fill Rate": 2 + i,
                    "Beat": 8 + i,
                    "Flow": 7 + i,
                },
            )
            for i in range(4)
        ]
        for slot in slots
    }
    mini_pool = [_mk_item(f"Mini_{i}", **{"Perfect Points": 2 + i, "Combo Multiplier": 1 + (i % 3), "Beat": 1 + (i % 2)}) for i in range(10)]
    registry = ItemRegistry(gear_pool, mini_pool, slots)

    genomes = []
    for i in range(n_genomes):
        genomes.append(
            [gear_pool[slot][i % len(gear_pool[slot])] for slot in slots]
            + [mini_pool[(i + 0) % len(mini_pool)], mini_pool[(i + 3) % len(mini_pool)], mini_pool[(i + 6) % len(mini_pool)]]
        )

    gpu_arrays = registry.to_gpu_arrays()
    population_indices = registry.encode_population(genomes)
    base_fixed_stats, _ = build_base_fixed_stats_array(
        {
            "Perfect Points": 100,
            "Combo Multiplier": 80,
            "Fever Multiplier": 70,
            "Fever Time": 60,
            "Fever Fill Rate": 50,
            "Beat": 90,
            "Vibe": 30,
            "Rush": 20,
            "Flow": 85,
            "Chill": 25,
        },
        {"selected_color": "Beat"},
    )

    timestamps = np.linspace(0, 120, 800, dtype=np.float32)
    calc_song = {
        "song_data": {"timestamps": timestamps},
        "metadata": {
            "Long Notes": 20,
            "Last Note Time": 120.0,
            "Primary Color": "Beat",
            "Secondary Color": "Flow",
            "Song Name": "PROFILE_WORKER",
        },
    }
    flags = (1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0)
    return population_indices, gpu_arrays["item_stats"], gpu_arrays["slot_start"], gpu_arrays["slot_count"], base_fixed_stats, calc_song, flags, ref_arrays


def run_sequential_benchmark(n_batches=5):
    """Benchmark direct GPU calls (no IPC)."""
    from gear_optimizer.solver.fever_timeline import SongTimelineGrid
    from gear_optimizer.solver.taichi_gem.api import solve_genomes_with_ftff

    ref_arrays = {
        "Perfect Points": np.linspace(0, 100, 161, dtype=np.float64),
        "Combo Multiplier": np.linspace(1, 2, 161, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.5, 3.1, 161, dtype=np.float64),
        "Fever Fill Rate": np.linspace(0.5, 1.8, 161, dtype=np.float64),
        "Fever Time": np.linspace(0.5, 1.8, 161, dtype=np.float64),
    }

    n_genomes = 500
    genome_stats = [
        {
            "base_pp": 50 + i % 20,
            "base_cm": 50 + i % 15,
            "base_fm": 50 + i % 10,
            "base_p_val": 100 + i % 30,
            "base_s_val": 50 + i % 20,
            "base_ft_stat": 30 + i % 40,
            "base_ff_stat": 30 + i % 40,
        }
        for i in range(n_genomes)
    ]

    timestamps = np.linspace(0, 120, 800)
    calc_song = {
        "song_data": {"timestamps": timestamps},
        "metadata": {"Long Notes": 20, "Last Note Time": 120.0, "Primary Color": "Chill", "Secondary Color": "Flow"},
    }
    grid = SongTimelineGrid(calc_song, ref_arrays)

    _ = solve_genomes_with_ftff(genome_stats[:10], grid, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, ref_arrays)

    times = []
    for _ in range(n_batches):
        t0 = time.perf_counter()
        _ = solve_genomes_with_ftff(genome_stats, grid, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, ref_arrays)
        times.append(time.perf_counter() - t0)

    return times


def worker_process(worker_id, req_queue, resp_queue, n_requests):
    """Simulate worker submitting GPU requests via IPC."""
    from gear_optimizer.solver.gpu_executor import set_gpu_worker_mode, submit_gpu_solve_genomes_from_registry

    set_gpu_worker_mode(worker_id, req_queue, resp_queue)

    population_indices, item_stats, slot_start, slot_count, base_fixed_stats, calc_song, flags, ref_arrays = _build_registry_inputs()
    calc_song = {
        "song_data": dict(calc_song.get("song_data") or {}),
        "metadata": dict(calc_song.get("metadata") or {}),
    }
    calc_song["metadata"]["Song Name"] = f"PROFILE_WORKER_{worker_id}"

    times = []
    is_p_ft, is_s_ft, is_p_ff, is_s_ff, is_p_pp, is_s_pp, is_p_cm, is_s_cm, is_p_fm, is_s_fm, is_p_ov, is_s_ov = flags
    for _ in range(n_requests):
        t0 = time.perf_counter()
        _ = submit_gpu_solve_genomes_from_registry(
            population_indices,
            item_stats,
            slot_start,
            slot_count,
            base_fixed_stats,
            calc_song,
            is_p_ft,
            is_s_ft,
            is_p_ff,
            is_s_ff,
            is_p_pp,
            is_s_pp,
            is_p_cm,
            is_s_cm,
            is_p_fm,
            is_s_fm,
            is_p_ov,
            is_s_ov,
            ref_arrays,
        )
        times.append(time.perf_counter() - t0)

    return times


def run_parallel_benchmark(n_workers=3, n_requests_per_worker=2):
    """Benchmark IPC overhead with GPU executor."""
    from gear_optimizer.solver.gpu_executor import GpuExecutor

    GpuExecutor._instance = None
    executor = GpuExecutor()
    executor.start()
    time.sleep(1.5)

    try:
        mp_ctx = multiprocessing.get_context("spawn")

        worker_configs = []
        for _ in range(n_workers):
            w_id, req_q, resp_q = executor.register_worker()
            worker_configs.append((w_id, req_q, resp_q))

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

    print("\n[1] Sequential (Direct GPU calls)...")
    seq_times = run_sequential_benchmark(n_batches=6)
    seq_avg = np.mean(seq_times[1:])
    print(f"    Avg per batch: {seq_avg:.3f}s")
    print(f"    Total 5 batches: {sum(seq_times[1:]):.3f}s")

    print("\n[2] Parallel (3 workers x 2 requests via IPC)...")
    par_total, par_count = run_parallel_benchmark(n_workers=3, n_requests_per_worker=2)
    print(f"    Total time: {par_total:.3f}s")
    print(f"    Requests: {par_count}")
    print(f"    Avg per request: {par_total / par_count:.3f}s")

    print("\n" + "=" * 60)
    print("COMPARISON")
    print("=" * 60)
    seq_total_6 = sum(seq_times[1:]) + seq_times[0]
    print(f"Sequential (6 batches): {seq_total_6:.3f}s")
    print(f"Parallel   (6 batches): {par_total:.3f}s")
    print(f"Overhead: {(par_total - seq_total_6):.3f}s ({(par_total / seq_total_6 - 1) * 100:.1f}%)")


if __name__ == "__main__":
    main()
