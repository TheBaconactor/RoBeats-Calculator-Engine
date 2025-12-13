"""
Legacy compatibility wrapper.

Historically, `gear_optimizer.solver.taichi_gem_solver_impl` hosted a large Taichi
monolith (gem solver + ForceGreats). The maintained gem solver has long since
moved to `gear_optimizer.solver.taichi_gem`.

ForceGreatsFinder GPU has now been migrated into the modular subpackage:
  `gear_optimizer.solver.taichi_gem.force_greats`

This file remains ONLY to preserve import compatibility for:
  `from gear_optimizer.solver.taichi_gem_solver_impl import solve_force_greats_finder_gpu`
"""

from __future__ import annotations

from .taichi_gem.force_greats.api import solve_force_greats_finder_gpu

__all__ = ["solve_force_greats_finder_gpu"]






