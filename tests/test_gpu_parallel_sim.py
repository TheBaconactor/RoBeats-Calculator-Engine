"""
Test parallel mode simulation - multiple workers submitting GPU requests.
"""

import multiprocessing
import time

import numpy as np
import pytest

pytestmark = pytest.mark.gpu


def _mk_item(name: str, **stats: int) -> dict:
    out = {"Name": name}
    out.update({k: int(v) for k, v in (stats or {}).items()})
    return out


def worker_task(
    worker_id,
    req_queue,
    resp_queue,
    population_indices,
    item_stats,
    slot_start,
    slot_count,
    base_fixed_stats,
    calc_song,
    color_flags,
    ref_arrays,
):
    """Simulate a worker submitting GPU work."""
    import faulthandler
    import sys

    faulthandler.enable()
    # If the worker hangs (IPC deadlock / queue put stuck), dump a traceback to help root-cause.
    faulthandler.dump_traceback_later(15.0, file=sys.stderr, repeat=False)
    from gear_optimizer.solver.gpu_executor import (
        set_gpu_worker_mode,
        submit_gpu_solve_genomes_from_registry,
        is_gpu_worker_mode,
    )

    set_gpu_worker_mode(worker_id, req_queue, resp_queue)
    assert is_gpu_worker_mode()

    try:
        results = submit_gpu_solve_genomes_from_registry(
            population_indices=population_indices,
            item_stats=item_stats,
            slot_start=slot_start,
            slot_count=slot_count,
            base_fixed_stats=base_fixed_stats,
            timeline_grid=calc_song,
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


def test_multi_worker_parallel_simulation(monkeypatch):
    """
    Simulate multiple workers submitting GPU requests in parallel.

    This tests the full IPC flow:
    1. Main process starts GPU executor
    2. Workers are spawned and register with executor
    3. Workers submit GPU solve requests
    4. Results are returned via IPC
    """
    from gear_optimizer.solver.base_stats import build_base_fixed_stats_array
    from gear_optimizer.solver.gpu_executor import GpuExecutor
    from gear_optimizer.solver.item_registry import ItemRegistry

    # This test validates IPC correctness, not kernel JIT warmup behavior. Warmups can
    # delay queue consumption at startup and make spawn-based workers appear to "hang".
    monkeypatch.setenv("GPU_EXECUTOR_WARMUP_FG", "0")
    monkeypatch.setenv("GPU_EXECUTOR_WARMUP_GA", "0")
    try:
        from gear_optimizer.core.env_config import EnvConfig
        import gear_optimizer.solver.gpu_executor as gpu_executor_mod

        monkeypatch.setattr(gpu_executor_mod, "ENV", EnvConfig.from_environment())
    except Exception:
        pass

    GpuExecutor._instance = None
    executor = GpuExecutor()
    executor.start()
    assert executor.wait_until_ready(timeout=30.0), f"GpuExecutor not ready: {executor.last_init_error}"

    try:
        slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
        gear_pool = {
            slot: [
                _mk_item(f"{slot}_A", **{"Perfect Points": 10, "Combo Multiplier": 5, "Beat": 3}),
                _mk_item(f"{slot}_B", **{"Perfect Points": 12, "Combo Multiplier": 7, "Beat": 4}),
            ]
            for slot in slots
        }
        mini_pool = [
            _mk_item("Mini_A", **{"Perfect Points": 4, "Combo Multiplier": 2, "Beat": 1}),
            _mk_item("Mini_B", **{"Perfect Points": 5, "Combo Multiplier": 1, "Beat": 2}),
            _mk_item("Mini_C", **{"Perfect Points": 3, "Combo Multiplier": 3, "Beat": 1}),
        ]
        registry = ItemRegistry(gear_pool, mini_pool, slots)

        genomes = [
            [
                gear_pool["Hat"][0],
                gear_pool["Neck"][0],
                gear_pool["Face"][0],
                gear_pool["Shirt"][0],
                gear_pool["Back"][0],
                gear_pool["Pants"][0],
                mini_pool[0],
                mini_pool[1],
                mini_pool[2],
            ],
            [
                gear_pool["Hat"][1],
                gear_pool["Neck"][1],
                gear_pool["Face"][1],
                gear_pool["Shirt"][1],
                gear_pool["Back"][1],
                gear_pool["Pants"][1],
                mini_pool[2],
                mini_pool[1],
                mini_pool[0],
            ],
        ]
        population_indices = registry.encode_population(genomes)
        gpu_arrays = registry.to_gpu_arrays()

        ref_arrays = {
            "Perfect Points": np.linspace(0, 100, 161, dtype=np.float64),
            "Combo Multiplier": np.linspace(1, 2, 161, dtype=np.float64),
            "Fever Multiplier": np.linspace(1, 2, 161, dtype=np.float64),
            "Fever Fill Rate": np.linspace(0.5, 1.5, 161, dtype=np.float64),
            "Fever Time": np.linspace(0.5, 1.5, 161, dtype=np.float64),
        }

        timestamps = np.linspace(0, 100, 500, dtype=np.float32)
        calc_song = {
            "song_data": {"timestamps": timestamps},
            "metadata": {
                "Long Notes": 10,
                "Last Note Time": 100.0,
                "Primary Color": "Beat",
                "Secondary Color": "Flow",
            },
        }

        color_flags = {
            "is_p_ft": 1,
            "is_s_ft": 0,
            "is_p_ff": 0,
            "is_s_ff": 0,
            "is_p_pp": 0,
            "is_s_pp": 0,
            "is_p_cm": 0,
            "is_s_cm": 1,
            "is_p_fm": 0,
            "is_s_fm": 0,
            "is_p_ov": 1,
            "is_s_ov": 0,
        }

        base_fixed_stats, _ = build_base_fixed_stats_array(
            {
                "Perfect Points": 100,
                "Combo Multiplier": 50,
                "Fever Multiplier": 40,
                "Fever Time": 30,
                "Fever Fill Rate": 20,
                "Beat": 80,
                "Vibe": 10,
                "Rush": 10,
                "Flow": 60,
                "Chill": 10,
            },
            {"selected_color": "Beat"},
        )

        n_workers = 2
        worker_configs = []
        for _ in range(n_workers):
            w_id, req_q, resp_q = executor.register_worker()
            worker_configs.append((w_id, req_q, resp_q))

        mp_ctx = multiprocessing.get_context("spawn")

        processes = []
        for w_id, req_q, resp_q in worker_configs:
            p = mp_ctx.Process(
                target=worker_task,
                args=(
                    w_id,
                    req_q,
                    resp_q,
                    population_indices,
                    gpu_arrays["item_stats"],
                    gpu_arrays["slot_start"],
                    gpu_arrays["slot_count"],
                    base_fixed_stats,
                    calc_song,
                    color_flags,
                    ref_arrays,
                ),
            )
            processes.append(p)

        for p in processes:
            p.start()

        for p in processes:
            p.join(timeout=30.0)

        for p in processes:
            assert not p.is_alive(), "Worker process hung"
            assert p.exitcode == 0, f"Worker exited with code {p.exitcode}"

    finally:
        executor.stop()
        GpuExecutor._instance = None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
