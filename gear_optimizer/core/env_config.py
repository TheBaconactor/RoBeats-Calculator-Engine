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

from dataclasses import dataclass

from .parsing import env_flag, env_float, env_get, env_int, env_str


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
    gpu_timeline_only: bool  # GPU_TIMELINE_ONLY: Force GPU timeline (avoid CPU precompute_all)
    gpu_strict: bool  # GPU_STRICT: Fail fast on any CPU fallback

    # General Performance
    perf_timing: bool  # PERF_TIMING (gated): Enable performance timing globally
    perf_timing_unconditional: bool  # PERF_TIMING (ungated): used by perf print sites

    # ForceGreats
    fg_search_radius: int  # FG_SEARCH_RADIUS: default radius (env override)

    # JIT / profiling / memory helpers
    numba_cache_dir: str | None  # NUMBA_CACHE_DIR
    memory_guard_write_every_n: int  # MEMORY_GUARD_WRITE_EVERY_N
    memory_guard_write_every_sec: float  # MEMORY_GUARD_WRITE_EVERY_SEC
    profile_events_enabled: bool  # METAFINDER_PROFILE_EVENTS
    profile_events_path: str  # METAFINDER_PROFILE_EVENTS_PATH / PROFILE_EVENTS_PATH
    profile_run_id: str  # METAFINDER_PROFILE_RUN_ID / PROFILE_RUN_ID

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
        debug_profile = env_flag("DEBUG_PROFILE") or env_flag("METAFINDER_DEBUG_PROFILE")
        perf_timing_unconditional = env_flag("PERF_TIMING")
        output_enabled = env_flag("METAFINDER_OUTPUT") or env_flag("METAFINDER_VERBOSE")
        progress_enabled = env_flag("METAFINDER_PROGRESS", "1")
        progress_interval_sec = env_float("METAFINDER_PROGRESS_INTERVAL", 0.2)
        progress_bar_width = env_int("METAFINDER_PROGRESS_WIDTH", 24)
        return cls(
            debug_profile=debug_profile,
            # GPU Performance & Timing
            gpu_sync_for_timing=debug_profile and env_flag("GPU_SYNC_FOR_TIMING"),
            gpu_force_sync=debug_profile and env_flag("GPU_FORCE_SYNC"),
            gpu_executor_profile=debug_profile and env_flag("GPU_EXECUTOR_PROFILE"),
            gpu_executor_warmup_fg=env_flag("GPU_EXECUTOR_WARMUP_FG", "1"),
            gpu_profiler=debug_profile and env_flag("GPU_PROFILER"),
            gpu_timeline_only=env_flag("GPU_TIMELINE_ONLY", "1"),
            gpu_strict=env_flag("GPU_STRICT", "1"),
            # General Performance
            perf_timing=debug_profile and perf_timing_unconditional,
            perf_timing_unconditional=perf_timing_unconditional,
            # ForceGreats
            fg_search_radius=env_int("FG_SEARCH_RADIUS", 5),
            # JIT / profiling / memory helpers
            numba_cache_dir=env_str("NUMBA_CACHE_DIR") or None,
            memory_guard_write_every_n=max(1, env_int("MEMORY_GUARD_WRITE_EVERY_N", 1)),
            memory_guard_write_every_sec=max(0.0, env_float("MEMORY_GUARD_WRITE_EVERY_SEC", 0.0)),
            profile_events_path=env_str("METAFINDER_PROFILE_EVENTS_PATH") or env_str("PROFILE_EVENTS_PATH"),
            profile_events_enabled=env_flag("METAFINDER_PROFILE_EVENTS")
            or bool(env_str("METAFINDER_PROFILE_EVENTS_PATH") or env_str("PROFILE_EVENTS_PATH")),
            profile_run_id=env_str("METAFINDER_PROFILE_RUN_ID") or env_str("PROFILE_RUN_ID") or None,
        # Console output / progress
        output_enabled=output_enabled,
        progress_enabled=progress_enabled,
            progress_interval_sec=max(0.05, float(progress_interval_sec)),
            progress_bar_width=max(10, int(progress_bar_width)),
            # GPU Executor batching/IPC
            gpu_executor_batch_wait_ms=max(0, env_int("GPU_EXECUTOR_BATCH_WAIT_MS", 10)),
            gpu_executor_max_batch=max(1, env_int("GPU_EXECUTOR_MAX_BATCH", 8)),
            gpu_executor_pending_ttl_sec=max(0.0, env_float("GPU_EXECUTOR_PENDING_TTL_SEC", 300.0)),
            gpu_executor_pending_max=max(0, env_int("GPU_EXECUTOR_PENDING_MAX", 2048)),
        )


# Singleton instance - initialized once at module import
ENV = EnvConfig.from_environment()
