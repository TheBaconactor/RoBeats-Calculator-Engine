#!/usr/bin/env python3
"""
Gear Optimizer - Main Entry Point

Refactored to use GearOptimizerApp.
"""

import os
import multiprocessing
import sys
import configparser

from gear_optimizer.core.config import get_config_path, load_config


def _truthy_env(name: str, default: str = "0") -> bool:
    return str(os.environ.get(name, default) or "").strip().lower() in {"1", "true", "yes", "on"}


def _truthy_cfg(cfg: configparser.ConfigParser, section: str, key: str, default: bool = False) -> bool:
    try:
        return cfg.getboolean(section, key, fallback=default)
    except Exception:
        try:
            raw = str(cfg.get(section, key, fallback=str(int(default))) or "").strip().lower()
            return raw in {"1", "true", "yes", "on"}
        except Exception:
            return bool(default)


def _read_config_path() -> str:
    return get_config_path("config.ini")


def _debug_profile_enabled(cfg_path: str) -> bool:
    # Env overrides win.
    if _truthy_env("DEBUG_PROFILE", "0") or _truthy_env("METAFINDER_DEBUG_PROFILE", "0"):
        return True
    try:
        cfg = load_config(cfg_path)
        if _truthy_cfg(cfg, "Debug", "DebugProfile", False):
            return True
        if _truthy_cfg(cfg, "IterationEngine", "DebugProfile", False):
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
    throughput = _truthy_env("METAFINDER_THROUGHPUT", "0") or _truthy_env("THROUGHPUT_MODE", "0")
    allow_profiling = _truthy_env("METAFINDER_ALLOW_PROFILING", "0")
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
