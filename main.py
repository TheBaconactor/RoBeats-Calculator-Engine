#!/usr/bin/env python3
"""
Gear Optimizer - Main Entry Point

Refactored to use GearOptimizerApp.
"""

import os
import multiprocessing
import sys


def _apply_throughput_mode_env() -> None:
    throughput = str(os.environ.get("METAFINDER_THROUGHPUT", "") or "").strip().lower() in {"1", "true", "yes", "on"}
    throughput = throughput or (str(os.environ.get("THROUGHPUT_MODE", "") or "").strip().lower() in {"1", "true"})
    if not throughput:
        return

    # Disable sync-heavy profiling/instrumentation for real throughput runs.
    for k in (
        "PERF_TIMING",
        "GPU_SYNC_FOR_TIMING",
        "GPU_FORCE_SYNC",
        "TAICHI_KERNEL_PROFILER",
        "TAICHI_KERNEL_PROFILER_PRINT",
    ):
        os.environ.pop(k, None)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    try:
        _apply_throughput_mode_env()
        from gear_optimizer.app import GearOptimizerApp

        app = GearOptimizerApp()
        app.run()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Fatal Error: {e}")
        sys.exit(1)
