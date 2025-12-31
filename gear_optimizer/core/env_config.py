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


def _env_bool(key: str, default: str = "0") -> bool:
    """
    Parse boolean environment variable (0/1 or true/false).

    Args:
        key: Environment variable name
        default: Default value if not set (default: "0")

    Returns:
        True if value is "1" or "true" (case-insensitive), False otherwise
    """
    value = os.environ.get(key, default).lower()
    return value in ("1", "true")


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


@dataclass(frozen=True)
class EnvConfig:
    """
    Centralized environment configuration.

    All environment variables are read once at initialization and cached.
    This provides type safety, consistent access patterns, and makes it
    easy to see all available environment variables in one place.
    """

    # GPU Performance & Timing
    gpu_sync_for_timing: bool  # GPU_SYNC_FOR_TIMING: Force GPU sync for accurate timing
    gpu_force_sync: bool  # GPU_FORCE_SYNC: Force GPU synchronization
    gpu_executor_profile: bool  # GPU_EXECUTOR_PROFILE: Enable GPU executor profiling
    gpu_executor_warmup_fg: bool  # GPU_EXECUTOR_WARMUP_FG: Pre-warm FG Taichi kernels at executor startup
    gpu_profiler: bool  # GPU_PROFILER: Enable GPU profiler
    gpu_batch_log: bool  # GPU_BATCH_LOG: Log GPU batch operations
    gpu_service_profile: bool  # GPU_SERVICE_PROFILE: Track GpuServiceClient request latencies
    gpu_service_profile_print: bool  # GPU_SERVICE_PROFILE_PRINT: Print latency summary on close

    # General Performance
    perf_timing: bool  # PERF_TIMING: Enable performance timing globally

    # Genetic Algorithm
    ga_seed: Optional[str]  # GA_SEED: Seed for genetic algorithm RNG

    @classmethod
    def from_environment(cls) -> "EnvConfig":
        """
        Create EnvConfig from current environment variables.

        Returns:
            EnvConfig instance with all environment variables loaded
        """
        return cls(
            # GPU Performance & Timing
            gpu_sync_for_timing=_env_bool("GPU_SYNC_FOR_TIMING"),
            gpu_force_sync=_env_bool("GPU_FORCE_SYNC"),
            gpu_executor_profile=_env_bool("GPU_EXECUTOR_PROFILE"),
            gpu_executor_warmup_fg=_env_bool("GPU_EXECUTOR_WARMUP_FG", "1"),
            gpu_profiler=_env_bool("GPU_PROFILER"),
            gpu_batch_log=_env_bool("GPU_BATCH_LOG"),
            gpu_service_profile=_env_bool("GPU_SERVICE_PROFILE"),
            gpu_service_profile_print=_env_bool("GPU_SERVICE_PROFILE_PRINT"),
            # General Performance
            perf_timing=_env_bool("PERF_TIMING"),
            # Genetic Algorithm
            ga_seed=_env_str("GA_SEED"),
        )


# Singleton instance - initialized once at module import
ENV = EnvConfig.from_environment()
