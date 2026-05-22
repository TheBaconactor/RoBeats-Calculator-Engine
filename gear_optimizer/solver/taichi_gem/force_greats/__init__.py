"""
ForceGreatsFinder GPU implementation (Taichi/Vulkan).

This subpackage hosts the ForceGreats (FG) finder kernels + Python wrapper.
It is intentionally isolated from the main gem solver modules for maintainability.
"""

from .bellman_fixed import FgBellmanFixedStatsResult, solve_force_greats_bellman_fixed_stats_gpu

__all__ = [
    "FgBellmanFixedStatsResult",
    "solve_force_greats_bellman_fixed_stats_gpu",
]
