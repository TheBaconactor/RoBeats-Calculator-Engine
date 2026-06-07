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

Scope: the frozen ENV snapshot below holds IMPORT-TIME configuration only.
Per-call DEBUG/PROFILING/TELEMETRY flags (DB_TIMING, POST_TIMING,
INFLIGHT_STAGE_PROFILE*, GA_LOOP_PROFILE*, GPU_EXECUTOR_LIVE/HEARTBEAT*, the
INFLIGHT_*_DEBUG family, etc.) are intentionally read at call time via the
parsing.py helpers (env_flag/env_int/env_float/env_str) so dev tooling and
tests can toggle them at runtime. They are gated OFF by default and the full
surface is inventoried in docs/Implementation Records/ENV_FLAG_ELIMINATION.md.
No production code may read os.environ directly or parse with bare int()/float()
in a silent try/except -- always go through the parsing.py helpers.
"""

from dataclasses import dataclass

from .parsing import env_flag, env_float, env_int, env_str


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
    gpu_executor_warmup_fg: bool  # GPU_EXECUTOR_WARMUP_FG: Pre-warm FG Taichi kernels at executor startup
    gpu_service_profile: bool  # GPU_SERVICE_PROFILE: Track GpuServiceClient request latencies
    gpu_service_profile_print: bool  # GPU_SERVICE_PROFILE_PRINT: Print latency summary on close

    # Debug / profiling master gate
    debug_profile: bool  # DEBUG_PROFILE / METAFINDER_DEBUG_PROFILE: gates the whole profiling family

    # General Performance
    perf_timing: bool  # PERF_TIMING (gated): Enable performance timing globally
    perf_timing_unconditional: bool  # PERF_TIMING (ungated): used by perf print sites

    # JIT / profiling / memory helpers
    numba_cache_dir: str | None  # NUMBA_CACHE_DIR

    # Console output / progress
    output_enabled: bool  # METAFINDER_OUTPUT / METAFINDER_VERBOSE: enable verbose console output
    banner_env: str  # METAFINDER_BANNER: startup banner override ("" = auto by TTY)
    progress_enabled: bool  # METAFINDER_PROGRESS: enable CLI progress UI (default on)
    progress_interval_sec: float  # METAFINDER_PROGRESS_INTERVAL: UI refresh cadence
    progress_bar_width: int  # METAFINDER_PROGRESS_WIDTH: progress bar width in chars

    # GPU Executor batching/IPC (read once; restart to apply changes)
    gpu_executor_batch_wait_ms: int  # GPU_EXECUTOR_BATCH_WAIT_MS
    gpu_executor_max_batch: int  # GPU_EXECUTOR_MAX_BATCH

    @classmethod
    def from_environment(cls) -> "EnvConfig":
        """
        Create EnvConfig from current environment variables.

        Returns:
            EnvConfig instance with all environment variables loaded
        """
        debug_profile = env_flag("DEBUG_PROFILE") or env_flag("METAFINDER_DEBUG_PROFILE")
        perf_timing_unconditional = env_flag("PERF_TIMING")
        output_enabled = env_flag("METAFINDER_OUTPUT") or env_flag("METAFINDER_VERBOSE")
        progress_enabled = env_flag("METAFINDER_PROGRESS", "1")
        progress_interval_sec = env_float("METAFINDER_PROGRESS_INTERVAL", 0.2)
        progress_bar_width = env_int("METAFINDER_PROGRESS_WIDTH", 24)
        return cls(
            # GPU Performance & Timing
            gpu_sync_for_timing=debug_profile and env_flag("GPU_SYNC_FOR_TIMING"),
            gpu_force_sync=debug_profile and env_flag("GPU_FORCE_SYNC"),
            gpu_executor_warmup_fg=True,  # always pre-warm FG kernels (one-time, matches warmup_ga)
            gpu_service_profile=debug_profile and env_flag("GPU_SERVICE_PROFILE"),
            gpu_service_profile_print=debug_profile and env_flag("GPU_SERVICE_PROFILE_PRINT"),
            # Debug / profiling master gate
            debug_profile=debug_profile,
            # General Performance
            perf_timing=debug_profile and perf_timing_unconditional,
            perf_timing_unconditional=perf_timing_unconditional,
            # JIT / profiling / memory helpers
            numba_cache_dir=env_str("NUMBA_CACHE_DIR") or None,
            # Console output / progress
            output_enabled=output_enabled,
            banner_env=env_str("METAFINDER_BANNER"),
            progress_enabled=progress_enabled,
            progress_interval_sec=max(0.05, float(progress_interval_sec)),
            progress_bar_width=max(10, int(progress_bar_width)),
            # GPU Executor batching/IPC
            gpu_executor_batch_wait_ms=10,  # GPU-owner loop batch wait base (hardwired)
            gpu_executor_max_batch=8,  # GPU-owner loop batch base (effective owner-batch widened downstream)
        )


# Singleton instance - initialized once at module import
ENV = EnvConfig.from_environment()
