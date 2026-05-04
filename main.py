#!/usr/bin/env python3
"""
Gear Optimizer - Main Entry Point

Refactored to use GearOptimizerApp.
"""

import os
import multiprocessing
import sys

from gear_optimizer.core.config import get_config_path, load_config
from gear_optimizer.core.parsing import config_bool, env_flag


def _read_config_path() -> str:
    return get_config_path("config.ini")


def _debug_profile_enabled(cfg_path: str) -> bool:
    # Env overrides win.
    if env_flag("DEBUG_PROFILE") or env_flag("METAFINDER_DEBUG_PROFILE"):
        return True
    try:
        cfg = load_config(cfg_path)
        if config_bool(cfg, "Debug", "DebugProfile", default=False):
            return True
        if config_bool(cfg, "IterationEngine", "DebugProfile", default=False):
            return True
    except Exception:
        pass
    return False


def _apply_debug_profile_env(cfg_path: str) -> None:
    """
    Gate all profiling/instrumentation behind DebugProfile.

    If DebugProfile is OFF, disable per-run overhead env toggles even if they were set externally.
    """
    if _debug_profile_enabled(cfg_path):
        os.environ.setdefault("METAFINDER_DEBUG_PROFILE", "1")
        return

    for k in (
        "PERF_TIMING",
        "GPU_SYNC_FOR_TIMING",
        "GPU_FORCE_SYNC",
        "GPU_EXECUTOR_PROFILE",
        "GPU_PROFILER",
        "GPU_SERVICE_PROFILE",
        "GPU_SERVICE_PROFILE_PRINT",
        "INFLIGHT_STAGE_PROFILE",
        "INFLIGHT_STAGE_PROFILE_EMIT_SEC",
        "TAICHI_KERNEL_PROFILER",
        "TAICHI_KERNEL_PROFILER_PRINT",
    ):
        os.environ.pop(k, None)


def _apply_throughput_mode_env() -> None:
    throughput = env_flag("METAFINDER_THROUGHPUT") or env_flag("THROUGHPUT_MODE")
    allow_profiling = env_flag("METAFINDER_ALLOW_PROFILING")
    if not throughput and allow_profiling:
        return

    # Disable sync-heavy profiling/instrumentation for real throughput runs.
    if throughput or not allow_profiling:
        for k in (
            "PERF_TIMING",
            "GPU_SYNC_FOR_TIMING",
            "GPU_FORCE_SYNC",
            "TAICHI_KERNEL_PROFILER",
            "TAICHI_KERNEL_PROFILER_PRINT",
        ):
            os.environ.pop(k, None)


def _apply_taichi_shell_env() -> None:
    """
    Silence Taichi's graphical shell detection banner.

    TI_ENABLE_PYBUF=0 disables the wrapped stdout path that emits the
    "Graphical python shell detected" info line.
    """
    os.environ.setdefault("TI_ENABLE_PYBUF", "0")


def _apply_gpu_song_slots_default() -> None:
    """
    Set a sensible default for `GPU_SONG_SLOTS` before Taichi initializes.

    This reduces slot contention/timeline reuploads when running in-flight with
    `InFlightSongs > 1`. Users can always override via the environment.
    """
    if "GPU_SONG_SLOTS" in os.environ:
        return

    cfg_path = _read_config_path()
    try:
        cfg = load_config(cfg_path)
        cfg_slots = int(str(cfg.get("IterationEngine", "GPU_SongSlots", fallback="0") or "0"))
    except Exception:
        cfg_slots = 0

    # Prefer the app-level autosizing logic, but honor an explicit config override here
    # so `GPU_SongSlots` takes effect even if something imports Taichi fields early.
    if int(cfg_slots) > 0:
        os.environ.setdefault("GPU_SONG_SLOTS", str(int(cfg_slots)))


def main() -> int:
    multiprocessing.freeze_support()
    try:
        cfg_path = _read_config_path()
        _apply_taichi_shell_env()
        _apply_debug_profile_env(cfg_path)
        _apply_gpu_song_slots_default()
        _apply_throughput_mode_env()
        from gear_optimizer.app import GearOptimizerApp

        app = GearOptimizerApp()
        app.run()
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as e:
        print(f"Fatal Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
