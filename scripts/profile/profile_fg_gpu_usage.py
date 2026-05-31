"""
Profile Force Greats (FG) GPU usage with the in-process GPU executor.

This is intended to be run under `tools/profile/profile_system_run.py` so you get:
  - Windows GPU Engine utilization (typeperf)
  - GPU executor trace (request timings)

Example:
  python tools/profile/profile_system_run.py --enable-perf-defaults --typeperf-start-delay 1 --typeperf-interval 1 -- \
    python scripts/profile/profile_fg_gpu_usage.py
"""

from __future__ import annotations

import os
import sys
import time

import numpy as np


def _ensure_repo_root_on_path() -> None:
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


def main() -> int:
    _ensure_repo_root_on_path()

    # Profiling toggles (must be set before Taichi is initialized).
    os.environ.setdefault("PERF_TIMING", "1")
    os.environ.setdefault("GPU_EXECUTOR_PROFILE", "1")

    from gear_optimizer.solver.gpu_executor import get_gpu_executor
    from gear_optimizer.solver.gpu_service import GpuServiceClient

    gpu_client = GpuServiceClient()
    gpu_client.start(start_executor=True, in_process_queues=True)

    from gear_optimizer.solver.scoring.fever_solver import solve_best_fever_combination
    from gear_optimizer.helpers.song_helpers.force_greats import process_force_greats
    from gear_optimizer.core.constants import TOTAL_ROWS

    print("=== FG GPU Usage Profile (GpuExecutor + typeperf) ===")

    timestamps = np.linspace(0, 180, 1500).astype(np.float32)
    calc_song = {
        "metadata": {
            "Song Name": "FG GPU Usage Profile Song",
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": 180.0,
            "Total Notes": int(timestamps.shape[0]),
        },
        "song_data": {
            "timestamps": timestamps,
        },
    }

    base_stats_fixed = {
        "Perfect Points": 100,
        "Combo Multiplier": 100,
        "Fever Multiplier": 100,
        "Fever Fill Rate": 100,
        "Fever Time": 100,
        "Rush": 100,
        "Flow": 100,
        "Beat": 50,
        "Vibe": 50,
        "Chill": 50,
    }

    rows = int(TOTAL_ROWS) + 1
    ref_arrays = {
        "Perfect Points": np.linspace(1.0, 2.0, rows, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=np.float32),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=np.float32),
        "Fever Time": np.linspace(1.0, 2.5, rows, dtype=np.float32),
    }

    # Use CPU for the baseline solve so Taichi is only touched from the executor thread.
    cfg_data = {
        "selected_color": "Rush",
        "use_gpu": False,
        "user_ft": 0,
        "user_ff": 0,
        "user_pp": 0,
        "user_cm": 0,
        "user_fm": 0,
        "static_elem_input": 0,
    }

    print("Running baseline solver (CPU)...")
    data_dict = solve_best_fever_combination(
        cfg=None,
        initial_stats=base_stats_fixed,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        silent=True,
        override_cfg=cfg_data,
    )

    # Create a batch of slightly-varied loadouts to drive FG batching logic.
    loadout_entries = {}
    for i in range(64):
        stats = dict(base_stats_fixed)
        stats["Rush"] += i
        loadout_entries[f"hash_{i}"] = {
            "score": float(data_dict.get("Score", 0.0) or 0.0),
            "gear": [],
            "minis": [],
            "details": {"Stats": stats, "Selected Element": "Rush", "FT": 0, "FF": 0},
            "eval_data": {
                "Stats": stats,
                "Selected Element": "Rush",
                "FT": 0,
                "FF": 0,
                "GemCounts": data_dict.get("GemCounts") or {},
            },
        }

    print("Running Force Greats Finder (GPU via GpuExecutor)...")
    t0 = time.perf_counter()
    results = process_force_greats(
        loadout_entries=loadout_entries,
        manual_force_greats=False,
        force_greats_config=[],
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        meta_primary_color="Rush",
        build_details_fn=lambda x: x,
        use_gpu=True,
        perf_timing=True,
        gpu_client=gpu_client,
    )
    dt = time.perf_counter() - t0

    print(f"FG wall time: {dt:.3f}s; variants: {len(results)}")

    try:
        gpu_client.close()
    finally:
        get_gpu_executor().stop()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
