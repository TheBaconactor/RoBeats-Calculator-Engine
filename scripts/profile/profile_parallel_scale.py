"""
Scale test for parallel GPU executor mode.

This simulates many song-worker processes submitting GPU solve requests through
the centralized `GpuExecutor` and reports:
- End-to-end wall time
- Per-request average latency
- Executor wait vs exec time (GPU_EXECUTOR_PROFILE=1)

Example:
  GPU_EXECUTOR_PROFILE=1 python scripts/profile_parallel_scale.py --workers 32 --requests 2
"""

from __future__ import annotations

import argparse
import multiprocessing
import os
import sys
import time

import numpy as np


project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


def _mk_item(name: str, **stats: int) -> dict:
    out = {"Name": name}
    out.update({k: int(v) for k, v in (stats or {}).items()})
    return out


def _build_inputs(n_genomes: int = 500):
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
                    "Vibe": 4 + i,
                    "Rush": 3 + i,
                    "Flow": 7 + i,
                    "Chill": 2 + i,
                },
            )
            for i in range(4)
        ]
        for slot in slots
    }
    mini_pool = [
        _mk_item(
            f"Mini_{i}",
            **{
                "Perfect Points": 2 + i,
                "Combo Multiplier": 1 + (i % 3),
                "Fever Multiplier": 1 + (i % 2),
                "Beat": 1 + (i % 4),
                "Flow": 1 + (i % 3),
            },
        )
        for i in range(10)
    ]
    registry = ItemRegistry(gear_pool, mini_pool, slots)

    genomes = []
    for i in range(n_genomes):
        genomes.append(
            [
                gear_pool[slot][i % len(gear_pool[slot])] for slot in slots
            ]
            + [
                mini_pool[(i + 0) % len(mini_pool)],
                mini_pool[(i + 3) % len(mini_pool)],
                mini_pool[(i + 6) % len(mini_pool)],
            ]
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
            "Song Name": "PROFILE_SONG",
        },
    }

    flags = (1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0)
    return (
        population_indices,
        gpu_arrays["item_stats"],
        gpu_arrays["slot_start"],
        gpu_arrays["slot_count"],
        base_fixed_stats,
        calc_song,
        flags,
        ref_arrays,
    )


def _worker_process(worker_id, req_queue, resp_queue, n_requests: int, song_suffix: str):
    from gear_optimizer.solver.gpu_executor import set_gpu_worker_mode, submit_gpu_solve_genomes_from_registry

    set_gpu_worker_mode(worker_id, req_queue, resp_queue)

    (
        population_indices,
        item_stats,
        slot_start,
        slot_count,
        base_fixed_stats,
        calc_song,
        flags,
        ref_arrays,
    ) = _build_inputs()
    if song_suffix:
        calc_song = {
            "song_data": dict(calc_song.get("song_data") or {}),
            "metadata": dict(calc_song.get("metadata") or {}),
        }
        calc_song["metadata"]["Song Name"] = f"{calc_song['metadata'].get('Song Name', 'PROFILE_SONG')}{song_suffix}"

    is_p_ft, is_s_ft, is_p_ff, is_s_ff, is_p_pp, is_s_pp, is_p_cm, is_s_cm, is_p_fm, is_s_fm, is_p_ov, is_s_ov = flags

    for _ in range(n_requests):
        submit_gpu_solve_genomes_from_registry(
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--requests", type=int, default=2)
    parser.add_argument(
        "--unique-songs",
        action="store_true",
        help="Make each worker use a distinct song key (worst-case grid uploads).",
    )
    args = parser.parse_args()

    from gear_optimizer.solver.gpu_executor import GpuExecutor

    os.environ.setdefault("GPU_EXECUTOR_PROFILE", "1")

    GpuExecutor._instance = None
    executor = GpuExecutor()
    executor.start()
    time.sleep(1.0)

    mp_ctx = multiprocessing.get_context("spawn")

    try:
        registrations = []
        for _ in range(args.workers):
            w_id, req_q, resp_q = executor.register_worker()
            registrations.append((w_id, req_q, resp_q))

        procs = []
        for idx, (w_id, req_q, resp_q) in enumerate(registrations):
            suffix = f"_{idx}" if args.unique_songs else ""
            p = mp_ctx.Process(
                target=_worker_process,
                args=(w_id, req_q, resp_q, args.requests, suffix),
            )
            procs.append(p)

        t0 = time.perf_counter()
        for p in procs:
            p.start()
        for p in procs:
            p.join(timeout=600)
        elapsed = time.perf_counter() - t0

        total_requests = args.workers * args.requests
        print()
        print("=" * 60)
        print("PARALLEL SCALE RESULT")
        print("=" * 60)
        print(f"Workers: {args.workers} | Requests/worker: {args.requests} | Total: {total_requests}")
        print(f"Unique songs: {bool(args.unique_songs)}")
        print(f"Total wall time: {elapsed:.3f}s")
        print(f"Avg per request: {elapsed / max(1, total_requests):.3f}s")
        return 0
    finally:
        executor.stop()
        GpuExecutor._instance = None


if __name__ == "__main__":
    raise SystemExit(main())
