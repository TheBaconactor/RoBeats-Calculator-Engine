"""
Environment Configuration - Centralized Environment Variable Access.

This module provides a centralized, type-safe way to access environment variables
throughout the application. All environment variable access should go through the
ENV singleton to ensure consistency and maintainability.

Usage:
    from gear_optimizer.core.env_config import ENV

    if ENV.gpu_sync_for_timing:
        # Do timing-related operations

    if ENV.perf_timing:
        # Enable performance timing
"""

import os
from dataclasses import dataclass
from typing import Optional

TRUTHY_ENV_VALUES = frozenset({"1", "true", "yes", "on"})


def _normalize_env_value(value: Optional[str]) -> str:
    return str(value or "").strip().lower()


def env_flag(key: str, default: str = "0") -> bool:
    """Parse a boolean environment variable using common truthy values."""
    return _normalize_env_value(os.environ.get(key, default)) in TRUTHY_ENV_VALUES


def _env_bool(key: str, default: str = "0") -> bool:
    """
    Parse boolean environment variable (1/true/yes/on).

    Args:
        key: Environment variable name
        default: Default value if not set (default: "0")

    Returns:
        True if value is a recognized truthy token (case-insensitive), False otherwise
    """
    return env_flag(key, default)


def _env_str(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get string environment variable.

    Args:
        key: Environment variable name
        default: Default value if not set

    Returns:
        Environment variable value or default
    """
    return os.environ.get(key, default)


def _env_int(key: str, default: int) -> int:
    """Parse int environment variable (best-effort, never raises)."""
    raw = os.environ.get(key, None)
    if raw is None:
        return int(default)
    try:
        return int(str(raw).strip())
    except Exception:
        return int(default)


def _env_float(key: str, default: float) -> float:
    """Parse float environment variable (best-effort, never raises)."""
    raw = os.environ.get(key, None)
    if raw is None:
        return float(default)
    try:
        return float(str(raw).strip())
    except Exception:
        return float(default)


@dataclass(frozen=True)
class EnvConfig:
    """
    Centralized environment configuration.

    All environment variables are read once at initialization and cached.
    This provides type safety, consistent access patterns, and makes it
    easy to see all available environment variables in one place.
    """

    # Master debug/profiling gate
    debug_profile: bool  # DEBUG_PROFILE / METAFINDER_DEBUG_PROFILE: enable profiling/instrumentation knobs

    # GPU Performance & Timing
    gpu_sync_for_timing: bool  # GPU_SYNC_FOR_TIMING: Force GPU sync for accurate timing
    gpu_force_sync: bool  # GPU_FORCE_SYNC: Force GPU synchronization
    gpu_executor_profile: bool  # GPU_EXECUTOR_PROFILE: Enable GPU executor profiling
    gpu_executor_warmup_fg: bool  # GPU_EXECUTOR_WARMUP_FG: Pre-warm FG Taichi kernels at executor startup
    gpu_profiler: bool  # GPU_PROFILER: Enable GPU profiler
    gpu_batch_log: bool  # GPU_BATCH_LOG: Log GPU batch operations
    gpu_service_profile: bool  # GPU_SERVICE_PROFILE: Track GpuServiceClient request latencies
    gpu_service_profile_print: bool  # GPU_SERVICE_PROFILE_PRINT: Print latency summary on close
    gpu_timeline_only: bool  # GPU_TIMELINE_ONLY: Force GPU timeline (avoid CPU precompute_all)
    gpu_strict: bool  # GPU_STRICT: Fail fast on any CPU fallback
    gpu_use_ftff_solver: bool  # GPU_USE_FTFF_SOLVER: Use FT/FF-on-GPU kernel for genome solves

    # General Performance
    perf_timing: bool  # PERF_TIMING (gated): Enable performance timing globally
    perf_timing_unconditional: bool  # PERF_TIMING (ungated): used by perf print sites

    # Genetic Algorithm
    ga_seed: Optional[str]  # GA_SEED: Seed for genetic algorithm RNG

    # ForceGreats
    fg_search_radius: int  # FG_SEARCH_RADIUS: default radius (env override)

    # Console output / progress
    output_enabled: bool  # METAFINDER_OUTPUT / METAFINDER_VERBOSE: enable verbose console output
    progress_enabled: bool  # METAFINDER_PROGRESS: enable CLI progress UI (default on)
    progress_interval_sec: float  # METAFINDER_PROGRESS_INTERVAL: UI refresh cadence
    progress_bar_width: int  # METAFINDER_PROGRESS_WIDTH: progress bar width in chars

    # GPU Executor batching/IPC (read once; restart to apply changes)
    gpu_executor_batch_wait_ms: int  # GPU_EXECUTOR_BATCH_WAIT_MS
    gpu_executor_max_batch: int  # GPU_EXECUTOR_MAX_BATCH
    gpu_executor_pending_ttl_sec: float  # GPU_EXECUTOR_PENDING_TTL_SEC
    gpu_executor_pending_max: int  # GPU_EXECUTOR_PENDING_MAX

    @classmethod
    def from_environment(cls) -> "EnvConfig":
        """
        Create EnvConfig from current environment variables.

        Returns:
            EnvConfig instance with all environment variables loaded
        """
        debug_profile = _env_bool("DEBUG_PROFILE") or _env_bool("METAFINDER_DEBUG_PROFILE")
        perf_timing_unconditional = _env_bool("PERF_TIMING")
        output_enabled = _env_bool("METAFINDER_OUTPUT") or _env_bool("METAFINDER_VERBOSE")
        progress_enabled = _env_bool("METAFINDER_PROGRESS", "1")
        progress_interval_sec = _env_float("METAFINDER_PROGRESS_INTERVAL", 0.2)
        progress_bar_width = _env_int("METAFINDER_PROGRESS_WIDTH", 24)
        return cls(
            debug_profile=debug_profile,
            # GPU Performance & Timing
            gpu_sync_for_timing=debug_profile and _env_bool("GPU_SYNC_FOR_TIMING"),
            gpu_force_sync=debug_profile and _env_bool("GPU_FORCE_SYNC"),
            gpu_executor_profile=debug_profile and _env_bool("GPU_EXECUTOR_PROFILE"),
            gpu_executor_warmup_fg=_env_bool("GPU_EXECUTOR_WARMUP_FG", "1"),
            gpu_profiler=debug_profile and _env_bool("GPU_PROFILER"),
            gpu_batch_log=debug_profile and _env_bool("GPU_BATCH_LOG"),
            gpu_service_profile=debug_profile and _env_bool("GPU_SERVICE_PROFILE"),
            gpu_service_profile_print=debug_profile and _env_bool("GPU_SERVICE_PROFILE_PRINT"),
            gpu_timeline_only=_env_bool("GPU_TIMELINE_ONLY", "1"),
            gpu_strict=_env_bool("GPU_STRICT", "1"),
            gpu_use_ftff_solver=_env_bool("GPU_USE_FTFF_SOLVER", "1"),
            # General Performance
            perf_timing=debug_profile and perf_timing_unconditional,
            perf_timing_unconditional=perf_timing_unconditional,
            # Genetic Algorithm
            ga_seed=_env_str("GA_SEED"),
            # ForceGreats
            fg_search_radius=_env_int("FG_SEARCH_RADIUS", 5),
            # Console output / progress
            output_enabled=output_enabled,
            progress_enabled=progress_enabled,
            progress_interval_sec=max(0.05, float(progress_interval_sec)),
            progress_bar_width=max(10, int(progress_bar_width)),
            # GPU Executor batching/IPC
            gpu_executor_batch_wait_ms=max(0, _env_int("GPU_EXECUTOR_BATCH_WAIT_MS", 10)),
            gpu_executor_max_batch=max(1, _env_int("GPU_EXECUTOR_MAX_BATCH", 8)),
            gpu_executor_pending_ttl_sec=max(0.0, _env_float("GPU_EXECUTOR_PENDING_TTL_SEC", 300.0)),
            gpu_executor_pending_max=max(0, _env_int("GPU_EXECUTOR_PENDING_MAX", 2048)),
        )


# Singleton instance - initialized once at module import
ENV = EnvConfig.from_environment()
