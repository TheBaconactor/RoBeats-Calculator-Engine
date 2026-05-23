"""
ForceGreats GPU implementation (Taichi/Vulkan).

Production FG uses the response-frontier solver in `response_frontier.py`.
"""

from .bellman_fixed import FgBellmanFixedStatsResult, solve_force_greats_bellman_fixed_stats_gpu
from .response_frontier import (
    FgResponseFrontierResult,
    FgResponseFrontierSolveResult,
    FgResponseInnerResult,
    FgResponseSurface,
    build_force_greats_response_frontier,
    optimize_response_frontier_inner_exact,
    optimize_response_frontier_inner_exact_gpu,
    reconstruct_force_greats_response_counts,
    response_surface_dominates,
    score_response_surface_exact,
    solve_force_greats_response_frontier_batch_gpu,
    solve_force_greats_response_frontier_exact,
    solve_force_greats_response_frontier_for_ftff,
)
from .response_build_gpu import build_force_greats_response_frontier_gpu, build_force_greats_response_frontiers_gpu_batch

__all__ = [
    "FgBellmanFixedStatsResult",
    "FgResponseFrontierResult",
    "FgResponseFrontierSolveResult",
    "FgResponseInnerResult",
    "FgResponseSurface",
    "build_force_greats_response_frontier",
    "build_force_greats_response_frontier_gpu",
    "build_force_greats_response_frontiers_gpu_batch",
    "optimize_response_frontier_inner_exact",
    "optimize_response_frontier_inner_exact_gpu",
    "reconstruct_force_greats_response_counts",
    "response_surface_dominates",
    "score_response_surface_exact",
    "solve_force_greats_response_frontier_batch_gpu",
    "solve_force_greats_response_frontier_exact",
    "solve_force_greats_response_frontier_for_ftff",
    "solve_force_greats_bellman_fixed_stats_gpu",
]
