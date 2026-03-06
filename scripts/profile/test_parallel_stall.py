"""
Minimal reproduction of multi-song parallel stall using PROCESSES (not threads).

This matches the real app's spawn-based ProcessPoolExecutor pattern.
"""

import multiprocessing
import os
import sys
import time

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

os.environ["GPU_EXECUTOR_PROFILE"] = "1"
os.environ["PERF_TIMING"] = "1"


def _mk_item(name: str, **stats: int) -> dict:
    out = {"Name": name}
    out.update({k: int(v) for k, v in (stats or {}).items()})
    return out


def _build_registry_inputs(num_notes: int):
    import numpy as np

    from gear_optimizer.solver.base_stats import build_base_fixed_stats_array
    from gear_optimizer.solver.item_registry import ItemRegistry

    ref_arrays = {
        "Perfect Points": np.arange(161, dtype=np.float64),
        "Combo Multiplier": np.arange(161, dtype=np.float64),
        "Fever Multiplier": np.arange(161, dtype=np.float64),
        "Fever Time": np.arange(161, dtype=np.float64),
        "Fever Fill Rate": np.arange(161, dtype=np.float64),
    }

    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gear_pool = {
        slot: [
            _mk_item(f"{slot}_{i}", **{"Perfect Points": 10 + i, "Combo Multiplier": 5 + i, "Rush": 3 + i, "Vibe": 2 + i})
            for i in range(3)
        ]
        for slot in slots
    }
    mini_pool = [_mk_item(f"Mini_{i}", **{"Perfect Points": 2 + i, "Combo Multiplier": 1 + (i % 2), "Rush": 1 + (i % 3)}) for i in range(6)]
    registry = ItemRegistry(gear_pool, mini_pool, slots)

    genomes = []
    for i in range(100):
        genomes.append(
            [gear_pool[slot][i % len(gear_pool[slot])] for slot in slots]
            + [mini_pool[(i + 0) % len(mini_pool)], mini_pool[(i + 2) % len(mini_pool)], mini_pool[(i + 4) % len(mini_pool)]]
        )

    gpu_arrays = registry.to_gpu_arrays()
    population_indices = registry.encode_population(genomes)
    base_fixed_stats, _ = build_base_fixed_stats_array(
        {
            "Perfect Points": 50,
            "Combo Multiplier": 50,
            "Fever Multiplier": 50,
            "Fever Time": 50,
            "Fever Fill Rate": 50,
            "Beat": 10,
            "Vibe": 60,
            "Rush": 70,
            "Flow": 10,
            "Chill": 10,
        },
        {"selected_color": "Rush"},
    )

    return population_indices, gpu_arrays["item_stats"], gpu_arrays["slot_start"], gpu_arrays["slot_count"], base_fixed_stats, ref_arrays


def worker_process_fn(worker_id, req_q, resp_q, song_name, num_notes):
    """Worker process that submits GPU request."""
    import numpy as np

    from gear_optimizer.solver.gpu_executor import set_gpu_worker_mode, submit_gpu_solve_genomes_from_registry

    set_gpu_worker_mode(worker_id, req_q, resp_q)

    population_indices, item_stats, slot_start, slot_count, base_fixed_stats, ref_arrays = _build_registry_inputs(num_notes)

    song = {
        "metadata": {
            "Song Name": song_name,
            "Long Notes": 10,
            "Last Note Time": 120.0,
            "Primary Color": "Rush",
            "Secondary Color": "Vibe",
        },
        "song_data": {
            "timestamps": np.asarray(list(range(num_notes)), dtype=np.float32),
        },
    }

    try:
        print(f"[Worker {worker_id}] Submitting {len(population_indices)} genomes for {song_name}...")

        total_dt = 0.0
        for i in range(3):
            t_sub = time.perf_counter()
            result = submit_gpu_solve_genomes_from_registry(
                population_indices=population_indices,
                item_stats=item_stats,
                slot_start=slot_start,
                slot_count=slot_count,
                base_fixed_stats=base_fixed_stats,
                timeline_grid=song,
                is_p_ft=0,
                is_s_ft=0,
                is_p_ff=0,
                is_s_ff=1,
                is_p_pp=0,
                is_s_pp=0,
                is_p_cm=0,
                is_s_cm=0,
                is_p_fm=1,
                is_s_fm=0,
                is_p_ov=1,
                is_s_ov=0,
                ref_arrays=ref_arrays,
                timeout=120.0,
            )
            dt_sub = time.perf_counter() - t_sub
            total_dt += dt_sub
            print(f"[Worker {worker_id}] Iter {i}: {len(result)} results in {dt_sub:.2f}s")

        print(f"[Worker {worker_id}] Total 3 iters in {total_dt:.2f}s")
        return {"worker_id": worker_id, "count": len(result), "time": total_dt}

    except Exception as e:
        print(f"[Worker {worker_id}] ERROR: {e}")
        return {"worker_id": worker_id, "error": str(e)}


def test_with_processes():
    """Test using actual spawn processes like the real app."""
    from gear_optimizer.solver.gpu_executor import GpuExecutor

    print("=" * 60)
    print("TEST: GPU Executor with SPAWN Processes (like real app)")
    print("=" * 60)

    GpuExecutor._instance = None
    executor = GpuExecutor()

    executor.start()
    time.sleep(2)

    if not executor.is_running:
        print("ERROR: Executor failed to start")
        return

    print(f"[OK] Executor started, Taichi ready: {executor._taichi_ready}")

    n_workers = 5

    registrations = []
    for i in range(n_workers):
        worker_id, req_q, resp_q = executor.register_worker()
        registrations.append((worker_id, req_q, resp_q))
        print(f"  Registered worker {worker_id}")

    print(f"\n[Test] Spawning {n_workers} processes...")

    mp_ctx = multiprocessing.get_context("spawn")

    try:
        t_start = time.perf_counter()

        processes = []
        for i, (worker_id, req_q, resp_q) in enumerate(registrations):
            song_name = f"Song_{i}"
            num_notes = 100 + i * 10
            p = mp_ctx.Process(target=worker_process_fn, args=(worker_id, req_q, resp_q, song_name, num_notes))
            processes.append(p)
            p.start()

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
