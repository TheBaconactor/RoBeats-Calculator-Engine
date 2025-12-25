#!/usr/bin/env python3
"""
Hot profiling for main (exclude cold start).

Runs one warm-up iteration in-process to compile Taichi/Numba, then profiles a
second iteration and captures per-process GPU Engine utilization via typeperf.

This does not modify any config/settings; it uses the normal config resolution
path (e.g., config.ini or METAFINDER_CONFIG_PATH if set by the user).
"""

from __future__ import annotations

import cProfile
import datetime as _dt
import os
import subprocess
import sys
import time
from pathlib import Path

# Enable profiling features (no algorithm changes).
os.environ.setdefault("PERF_TIMING", "1")
os.environ.setdefault("GPU_PROFILER", "1")
os.environ.setdefault("GPU_SYNC_FOR_TIMING", "1")
os.environ.setdefault("GPU_FORCE_SYNC", "1")
os.environ.setdefault("PYTHONUTF8", "1")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]

project_root = str(_repo_root())
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def _typeperf_start(counter: str, out_csv: Path, *, sample_interval_sec: int = 1, max_samples: int = 120) -> subprocess.Popen:
    args = [
        "typeperf",
        counter,
        "-si",
        str(int(sample_interval_sec)),
        "-sc",
        str(int(max_samples)),
        "-f",
        "CSV",
        "-o",
        str(out_csv),
    ]
    # Keep output quiet; typeperf writes CSV to disk when it exits.
    return subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _typeperf_stop(proc: subprocess.Popen | None) -> None:
    if not proc:
        return
    try:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except Exception:
            proc.kill()
    except Exception:
        pass


if __name__ == "__main__":
    from gear_optimizer.app import GearOptimizerApp

    root = _repo_root()
    bin_dir = root / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    prof_path = bin_dir / f"profile_main_hot_{ts}.prof"
    txt_path = bin_dir / f"profile_main_hot_{ts}.txt"
    gpu_csv = bin_dir / f"gpu_typeperf_all_hot_{ts}.csv"
    cpu_csv = bin_dir / f"cpu_typeperf_total_hot_{ts}.csv"

    print("=" * 70)
    print("GEAR OPTIMIZER - HOT PROFILING (Cold Start Excluded)")
    print("=" * 70)
    print(">> WARMUP: running one in-process iteration...")
    app = GearOptimizerApp()
    app._run_single_iteration()

    print("\n>> HOT RUN: starting typeperf + cProfile...")
    pid = os.getpid()
    # typeperf writes the output file when it exits; run it for a fixed window
    # (slightly longer than the expected hot run) so we always get CSVs.
    sample_interval = int(os.environ.get("TYPEPERF_SAMPLE_INTERVAL_SEC", "1"))
    max_samples = int(os.environ.get("TYPEPERF_MAX_SAMPLES", "60"))
    gpu_tp = _typeperf_start(
        rf"\GPU Engine(pid_{pid}*)\Utilization Percentage",
        gpu_csv,
        sample_interval_sec=sample_interval,
        max_samples=max_samples,
    )
    cpu_tp = _typeperf_start(
        r"\Processor(_Total)\% Processor Time",
        cpu_csv,
        sample_interval_sec=sample_interval,
        max_samples=max_samples,
    )

    profiler = cProfile.Profile()
    profiler.enable()
    t0 = time.perf_counter()
    try:
        app._run_single_iteration()
    finally:
        t1 = time.perf_counter()
        profiler.disable()
        # Wait for typeperf to finish its fixed sample window so it flushes CSV.
        tp_timeout = sample_interval * max_samples + 10
        for proc in (gpu_tp, cpu_tp):
            if not proc:
                continue
            try:
                proc.wait(timeout=tp_timeout)
            except Exception:
                _typeperf_stop(proc)

    profiler.dump_stats(str(prof_path))

    import pstats
    import io

    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.strip_dirs()
    stream.write(f"Hot run wall time: {t1 - t0:.3f}s\n")
    stream.write("\nTOP 30 BY CUMULATIVE TIME:\n")
    stats.sort_stats("cumulative").print_stats(30)
    stream.write("\nTOP 30 BY TOTAL (SELF) TIME:\n")
    stats.sort_stats("tottime").print_stats(30)
    txt_path.write_text(stream.getvalue(), encoding="utf-8")

    print(f"\nSaved: {prof_path}")
    print(f"Saved: {txt_path}")
    print(f"Saved: {gpu_csv}")
    print(f"Saved: {cpu_csv}")
