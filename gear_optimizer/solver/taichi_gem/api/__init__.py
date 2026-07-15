"""
Taichi API Package - Python wrapper functions for GPU gem optimization.

This package exposes focused GPU solver modules:
1. initialization.py - Reference arrays, staging buffers, GPU initialization
2. timeline.py - GPU timeline precomputation and grid upload
3. skyline_operations.py - exact candidate evaluation

This __init__.py defines the public Taichi gem solver API surface.
"""

from .initialization import (
    ensure_ready,
    load_ref_arrays,
    hard_reset_taichi,
)
from .timeline import precompute_timeline_gpu
from .parallel_solvers import solve_loadouts_from_registry
from .skyline_operations import (
    skyline_upload_loadout_indices,
    skyline_upload_item_stats,
    skyline_upload_base_fixed_stats,
    skyline_evaluate_loadouts,
    skyline_download_scores,
    skyline_download_results,
)
# Public API
__all__ = [
    # Initialization
    "ensure_ready",
    "load_ref_arrays",
    "hard_reset_taichi",
    # Timeline
    "precompute_timeline_gpu",
    # Parallel solvers
    "solve_loadouts_from_registry",
    # Skyline operations
    "skyline_upload_loadout_indices",
    "skyline_upload_item_stats",
    "skyline_upload_base_fixed_stats",
    "skyline_evaluate_loadouts",
    "skyline_download_scores",
    "skyline_download_results",
]
