"""
Taichi Runtime - Initialization and configuration for GPU backend.

This module handles:
- Taichi initialization with auto-detected backend (Metal on macOS, Vulkan elsewhere)
- Environment variable configuration (kernel profiler, block dim)
- Global initialization state
"""

from __future__ import annotations

import os
import sys
import taichi as ti

# ============================================================================
# INITIALIZATION STATE
# ============================================================================

_ti_initialized = False


def is_initialized() -> bool:
    """Check if Taichi has been initialized."""
    return _ti_initialized


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _clamp_block_dim(x: int) -> int:
    # Conservative clamp; GPU backends typically like 64-512.
    if x < 1:
        return 1
    if x > 1024:
        return 1024
    return x


def _detect_backend() -> tuple:
    """
    Auto-detect the best GPU backend based on platform.

    Returns:
        tuple: (taichi_arch, backend_name)
    """
    if sys.platform == "darwin":
        return ti.metal, "Metal"
    else:
        return ti.vulkan, "Vulkan"


# IMPORTANT: These are read when init_taichi() is called, so callers can
# set env vars before initialization.
def get_kernel_profiler_enabled() -> bool:
    return bool(_env_int("TAICHI_KERNEL_PROFILER", 0))


def get_block_dim() -> int:
    # Empirically good defaults for this workload are 256.
    return _clamp_block_dim(_env_int("TAICHI_BLOCK_DIM", 256))


def _get_offline_cache_dir() -> str:
    """
    Return a stable on-disk cache directory for Taichi's offline cache.

    Keeping this inside the repo `bin/` avoids writing into user profile
    locations and makes cache cleanup straightforward.
    """
    try:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
        cache_dir = os.path.join(repo_root, "bin", "taichi_cache")
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir
    except Exception:
        # Fallback: let Taichi pick a default location.
        return "taichi_cache"


def init_taichi():
    """
    Initialize Taichi with auto-detected GPU backend.

    Called once by gpu_executor.py on the GPU thread, or lazily on first use.
    Uses f32 precision for performance (sufficient for score accuracy).

    Backend selection:
    - macOS: Metal
    - Windows/Linux: Vulkan
    """
    global _ti_initialized
    if not _ti_initialized:
        kernel_profiler = get_kernel_profiler_enabled()
        block_dim = get_block_dim()
        arch, backend_name = _detect_backend()

        init_kwargs = dict(
            arch=arch,
            default_fp=ti.f32,
            default_ip=ti.i32,
            kernel_profiler=kernel_profiler,
            default_gpu_block_dim=block_dim,
            # Huge win for repeated runs: avoid recompiling kernels each process.
            # This does not change algorithm results; it only caches compiled kernels on disk.
            offline_cache=True,
            offline_cache_file_path=_get_offline_cache_dir(),
        )
        try:
            ti.init(**init_kwargs)
        except Exception as e:
            # Be robust: if offline cache init fails for any reason, fall back to normal init.
            try:
                print(f"[Taichi] Offline cache init failed ({type(e).__name__}: {e}); retrying without offline cache.")
            except Exception:
                pass
            init_kwargs.pop("offline_cache", None)
            init_kwargs.pop("offline_cache_file_path", None)
            ti.init(**init_kwargs)
        _ti_initialized = True
        kp = "on" if kernel_profiler else "off"
        print(
            f"[Taichi] Initialized with {backend_name} backend - f32 precision (kernel_profiler={kp}, block_dim={block_dim})"
        )

        if kernel_profiler:
            try:
                ti.profiler.clear_kernel_profiler_info()
            except Exception:
                pass


# Backward-compatible alias
init_taichi_vulkan = init_taichi


def reset_taichi(*, reason: str | None = None) -> None:
    """
    Hard-reset Taichi runtime (frees Vulkan/Metal resources).

    This is intended as a recovery path for backend/driver failures (e.g. Vulkan
    semaphore allocation failures) and for long-running sessions where driver
    resources may leak.
    """
    global _ti_initialized

    if reason:
        print(f"[Taichi] Resetting runtime: {reason}")

    if not _ti_initialized:
        return

    try:
        ti.sync()
    except Exception:
        pass

    try:
        ti.reset()
    except Exception:
        # If reset fails, we'll still mark as uninitialized and let callers try
        # to re-init; worst case they crash again but with a clearer log path.
        pass

    _ti_initialized = False
