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

        ti.init(
            arch=arch,
            default_fp=ti.f32,
            default_ip=ti.i32,
            kernel_profiler=kernel_profiler,
        )
        _ti_initialized = True
        kp = "on" if kernel_profiler else "off"
        print(f"[Taichi] Initialized with {backend_name} backend - f32 precision (kernel_profiler={kp}, block_dim={block_dim})")

        if kernel_profiler:
            try:
                ti.profiler.clear_kernel_profiler_info()
            except Exception:
                pass


# Backward-compatible alias
init_taichi_vulkan = init_taichi
