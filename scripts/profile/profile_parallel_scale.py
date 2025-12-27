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
import os
import time
import multiprocessing
import sys

import numpy as np


# Add project root to path (so `gear_optimizer` imports work when running from /scripts)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


def _build_inputs(n_genomes: int = 500):
    from gear_optimizer.solver.fever_timeline import SongTimelineGrid

    ref_arrays = {
        "Perfect Points": np.linspace(0, 100, 161, dtype=np.float64),
        "Combo Multiplier": np.linspace(1, 2, 161, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.5, 3.1, 161, dtype=np.float64),
        "Fever Fill Rate": np.linspace(0.5, 1.8, 161, dtype=np.float64),
        "Fever Time": np.linspace(0.5, 1.8, 161, dtype=np.float64),
    }

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

    # Unique-ish song key per process so we can test worst-case (many songs) or best-case (same song).
    # The actual timestamps are constant; the cache_key is controlled by metadata Song Name.
    timestamps = np.linspace(0, 120, 800)
    calc_song = {
        "song_data": {"timestamps": timestamps},
        "metadata": {
            "Long Notes": 20,
            "Last Note Time": 120.0,
            "Primary Color": "Chill",
            "Secondary Color": "Flow",
            "Song Name": "PROFILE_SONG",
        },
    }
    grid = SongTimelineGrid(calc_song, ref_arrays)

    # Color flags
    flags = (0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0)
    return genome_stats, grid, flags, ref_arrays


def _worker_process(worker_id, req_queue, resp_queue, n_requests: int, song_suffix: str):
    from gear_optimizer.solver.gpu_executor import set_gpu_worker_mode, submit_gpu_solve_genomes

    set_gpu_worker_mode(worker_id, req_queue, resp_queue)

    genome_stats, grid, flags, ref_arrays = _build_inputs()
    # Ensure each process has a distinct cache_key if requested.
    grid.cache_key = (str(grid.cache_key[0]) + song_suffix, *grid.cache_key[1:])

    is_p_ft, is_s_ft, is_p_ff, is_s_ff, is_p_pp, is_s_pp, is_p_cm, is_s_cm, is_p_fm, is_s_fm, is_p_ov, is_s_ov = flags

    for _ in range(n_requests):
        submit_gpu_solve_genomes(
            genome_stats,
            grid,
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

    # Always enable executor profiling for this script unless user explicitly disabled it.
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
