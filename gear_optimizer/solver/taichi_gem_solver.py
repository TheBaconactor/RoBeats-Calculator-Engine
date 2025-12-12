"""
Taichi Gem Solver - stable facade.

This module intentionally keeps the historical import surface:
    from gear_optimizer.solver.taichi_gem_solver import ...

The implementation for the gem solver lives in the modular subpackage:
    gear_optimizer.solver.taichi_gem

ForceGreatsFinder GPU support still lives in the legacy implementation module
until it is migrated into the subpackage.
"""

from __future__ import annotations

# Public/stable API surface (used by tests to guard against accidental breakage)
from .taichi_gem.runtime import init_taichi_vulkan
from .taichi_gem.api import (
    load_ref_arrays,
    optimize_gems_gpu,
    optimize_gems_batch_gpu,
    mega_batch_solve_population,
    solve_genomes_with_ftff,
    solve_genomes_parallel,
)

# ForceGreatsFinder GPU (temporarily implemented in the legacy module)
from .taichi_gem_solver_impl import solve_force_greats_finder_gpu

__all__ = [
    "init_taichi_vulkan",
    "load_ref_arrays",
    "optimize_gems_gpu",
    "optimize_gems_batch_gpu",
    "mega_batch_solve_population",
    "solve_genomes_with_ftff",
    "solve_genomes_parallel",
]


