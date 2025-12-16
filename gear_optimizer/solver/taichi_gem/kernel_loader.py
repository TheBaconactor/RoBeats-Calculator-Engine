"""
Kernel Loader - Auto-selects appropriate kernel implementations based on platform.

On macOS (Metal backend): Uses kernels_metal.py for 64-bit atomic workarounds.
On Windows/Linux (Vulkan): Uses kernels.py with full 64-bit atomic support.

The Metal-safe kernels are created lazily by apply_metal_patches() which is called
AFTER fields have been allocated and bound. This ensures the fields are available
when Taichi JIT-compiles the kernels.

Usage:
    from .kernel_loader import get_kernels
    kernels = get_kernels()
"""
from __future__ import annotations

import sys

# Determine if we need Metal-safe kernels
IS_METAL = sys.platform == "darwin"

# Track if we've already patched Metal kernels
_metal_patched = False


def get_kernels():
    """
    Get the appropriate kernels module for the current platform.
    
    Returns the base kernels module. On Metal, the 64-bit atomic kernels
    will be replaced with Metal-safe versions when apply_metal_patches()
    is called (after field binding).
    """
    from . import kernels as base_kernels
    return base_kernels


def apply_metal_patches():
    """
    Apply Metal-safe kernel replacements to the base kernels module.
    
    This MUST be called AFTER:
    1. All fields have been allocated
    2. Fields have been bound to both kernels and kernels_metal modules
    
    Called automatically by fields.ensure_grid_fields_allocated() on macOS.
    """
    global _metal_patched
    
    if not IS_METAL:
        return
    
    if _metal_patched:
        return
    
    from . import kernels as base_kernels
    from . import kernels_metal
    
    # Create the Metal kernels (they're defined lazily to capture bound fields)
    kernels_metal.create_metal_kernels()
    
    # Override the 64-bit atomic kernels with Metal-safe versions
    base_kernels.init_chunk_best_key_kernel = kernels_metal.init_chunk_best_key_kernel
    base_kernels.reduce_chunk_to_best_key_kernel = kernels_metal.reduce_chunk_to_best_key_kernel
    base_kernels.merge_chunk_best_to_genomes_kernel = kernels_metal.merge_chunk_best_to_genomes_kernel
    base_kernels.ga_find_best_combo_key_kernel = kernels_metal.ga_find_best_combo_key_kernel
    base_kernels.ga_write_best_results_from_key_kernel = kernels_metal.ga_write_best_results_from_key_kernel
    base_kernels.ga_find_best_combo_warmstart_kernel = kernels_metal.ga_find_best_combo_warmstart_kernel
    
    _metal_patched = True
    print("[Metal] Applied 32-bit atomic kernel patches for macOS compatibility")
