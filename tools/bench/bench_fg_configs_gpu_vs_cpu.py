"""
Side-by-side benchmark: CPU vs GPU FG breakpoint config materialization.

Focuses on the piece we just ported:
  - CPU: build `counts_list = list(itertools.product(*ranges))`
  - GPU: generate the same rectangular config table directly on GPU

Run:
  python tools/bench/bench_fg_configs_gpu_vs_cpu.py
"""

from __future__ import annotations

import time
import itertools
import os
import sys
from pathlib import Path

import numpy as np


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401

        return True
    except Exception:
        return False


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from gear_optimizer.solver.taichi_gem.api.timeline import precompute_timeline_gpu
    from gear_optimizer.solver.taichi_gem.force_greats import kernels as fg_kernels
    from gear_optimizer.solver.taichi_gem.force_greats import fields as fg_fields

    # Deterministic exact-f32 timestamps (avoid boundary drift).
    n_notes = 2000
    dt = np.float32(0.125)
    timestamps = (np.arange(n_notes, dtype=np.float32) * dt).astype(np.float32)
    last_note_time = float(timestamps[-1])

    calc_song = {
        "metadata": {
            "Song Name": "FG Config Bench",
            "Difficulty": "Bench",
            "Primary Color": "Rush",
            "Secondary Color": "Beat",
            "Long Notes": 0,
            "Last Note Time": last_note_time,
            "Total Notes": n_notes,
        },
        "song_data": {"timestamps": timestamps},
    }

    ref_arrays = {
        "Fever Time": np.linspace(0.8, 1.2, 161, dtype=np.float32),
        "Fever Fill Rate": np.linspace(0.8, 1.8, 161, dtype=np.float32),
        "Perfect Points": np.linspace(1.0, 2.0, 161, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 2.0, 161, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 2.0, 161, dtype=np.float32),
    }

    # Ensure timeline grids exist (needed for FG kernels in typical runs; also forces Taichi init).
    precompute_timeline_gpu(calc_song, ref_arrays, song_slot=0)
    fg_fields.ensure_ready_with_warmup()

    # Workloads: choose a few realistic max-fp vectors.
    cases = [
        ("2 sections, medium", [25, 25]),
        ("3 sections, medium", [15, 15, 10]),
        ("4 sections, small", [10, 8, 6, 4]),
        ("4 sections, larger", [20, 15, 10, 8]),
    ]

    print("== FG config materialization benchmark ==")
    for name, max_fp in cases:
        n_sections = len(max_fp)
        n_cfg = 1
        for v in max_fp:
            n_cfg *= int(v) + 1

        # CPU: materialize list(itertools.product(...)) + upload to GPU forced table
        ranges = [range(0, int(v) + 1) for v in max_fp]
        t0 = time.perf_counter()
        cfgs = list(itertools.product(*ranges))
        # pack to numpy and upload (mirrors reference path cost)
        cfg_np = np.asarray(cfgs, dtype=np.int32)
        # pad to FG_MAX_SECTIONS cols
        buf = np.zeros((int(min(int(n_cfg), 4096)), int(fg_fields.FG_MAX_SECTIONS)), dtype=np.int32)
        t1 = time.perf_counter()
        # upload in 4096-row chunks
        for off in range(0, int(n_cfg), 4096):
            n = min(4096, int(n_cfg) - int(off))
            buf[:n, :] = 0
            buf[:n, :n_sections] = cfg_np[int(off) : int(off) + int(n), :n_sections]
            fg_kernels.fg_upload_forced_counts_kernel(int(n), int(off), buf)
        try:
            import taichi as ti

            ti.sync()
        except Exception:
            pass
        t2 = time.perf_counter()
        cpu_sec = t2 - t0

        # GPU: generate directly into fg_forced_counts (write only)
        max_fp_arr = np.zeros((int(fg_fields.FG_MAX_SECTIONS),), dtype=np.int32)
        for i, v in enumerate(max_fp):
            max_fp_arr[i] = int(v)

        # Chunk to something representative of production limits.
        chunk = min(int(n_cfg), 4096)
        # Warm the kernel once (exclude compilation).
        fg_kernels.fg_generate_fp_targets_cartesian_kernel(
            int(min(1, int(n_cfg))),
            0,
            0,
            int(n_sections),
            max_fp_arr,
        )
        try:
            import taichi as ti

            ti.sync()
        except Exception:
            pass

        t3 = time.perf_counter()
        for off in range(0, int(n_cfg), int(chunk)):
            n = min(int(chunk), int(n_cfg) - int(off))
            fg_kernels.fg_generate_fp_targets_cartesian_kernel(
                int(n),
                int(0) + int(off),
                int(off),
                int(n_sections),
                max_fp_arr,
            )
        try:
            import taichi as ti

            ti.sync()
        except Exception:
            pass
        t4 = time.perf_counter()
        gpu_sec = t4 - t3

        # Use cfgs to avoid optimizing away
        _ = cfgs[0] if cfgs else None

        speedup = (cpu_sec / gpu_sec) if gpu_sec > 0 else float("inf")
        print(
            f"- {name}: n_cfg={n_cfg:,}  CPU={cpu_sec * 1000:.2f}ms  GPU-gen={gpu_sec * 1000:.2f}ms  speedup={speedup:.2f}x"
        )


if __name__ == "__main__":
    if not _has_taichi():
        raise SystemExit("Taichi not available")
    main()
