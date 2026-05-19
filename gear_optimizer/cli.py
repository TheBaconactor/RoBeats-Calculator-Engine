from __future__ import annotations

import multiprocessing
import os

from gear_optimizer.core.config import get_config_path, load_config
from gear_optimizer.core.parsing import config_bool, env_flag


def common_init() -> None:
    multiprocessing.freeze_support()


def _read_config_path() -> str:
    return get_config_path("config.ini")


def _debug_profile_enabled(cfg_path: str) -> bool:
    if env_flag("DEBUG_PROFILE") or env_flag("METAFINDER_DEBUG_PROFILE"):
        return True
    try:
        cfg = load_config(cfg_path)
        return config_bool(cfg, "Debug", "DebugProfile", default=False) or config_bool(
            cfg,
            "IterationEngine",
            "DebugProfile",
            default=False,
        )
    except Exception:
        return False


def _apply_debug_profile_env(cfg_path: str) -> None:
    if _debug_profile_enabled(cfg_path):
        os.environ.setdefault("METAFINDER_DEBUG_PROFILE", "1")
        return
    for key in (
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
        os.environ.pop(key, None)


def _apply_throughput_mode_env() -> None:
    throughput = env_flag("METAFINDER_THROUGHPUT") or env_flag("THROUGHPUT_MODE")
    allow_profiling = env_flag("METAFINDER_ALLOW_PROFILING")
    if not throughput and allow_profiling:
        return
    for key in (
        "PERF_TIMING",
        "GPU_SYNC_FOR_TIMING",
        "GPU_FORCE_SYNC",
        "TAICHI_KERNEL_PROFILER",
        "TAICHI_KERNEL_PROFILER_PRINT",
    ):
        os.environ.pop(key, None)


def _apply_taichi_shell_env() -> None:
    os.environ.setdefault("TI_ENABLE_PYBUF", "0")


def _apply_gpu_song_slots_default() -> None:
    if "GPU_SONG_SLOTS" in os.environ:
        return
    cfg_path = _read_config_path()
    try:
        cfg = load_config(cfg_path)
        cfg_slots = int(str(cfg.get("IterationEngine", "GPU_SongSlots", fallback="0") or "0"))
    except Exception:
        cfg_slots = 0
    if cfg_slots > 0:
        os.environ.setdefault("GPU_SONG_SLOTS", str(cfg_slots))


def run() -> int:
    common_init()
    try:
        cfg_path = _read_config_path()
        _apply_taichi_shell_env()
        _apply_debug_profile_env(cfg_path)
        _apply_gpu_song_slots_default()
        _apply_throughput_mode_env()
        from gear_optimizer.app import GearOptimizerApp

        GearOptimizerApp().run()
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(f"Fatal Error: {exc}")
        return 1
