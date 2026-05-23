"""
ForceGreats GPU implementation (Taichi/Vulkan).

Production FG uses the fixed-stats Bellman solver in `bellman_fixed.py`.
"""

from .bellman_fixed import FgBellmanFixedStatsResult, solve_force_greats_bellman_fixed_stats_gpu

__all__ = [
    "FgBellmanFixedStatsResult",
    "solve_force_greats_bellman_fixed_stats_gpu",
]
