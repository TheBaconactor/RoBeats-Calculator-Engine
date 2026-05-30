"""
ForceGreats GPU implementation (Taichi/Vulkan).

Production FG uses the response-frontier solver in `response_frontier.py`.
"""

from .response_frontier import (
    FgResponseFrontierPackedScoringBatch,
    FgResponseFrontierResult,
    FgResponseFrontierSolveResult,
    FgResponseInnerResult,
    FgResponseSurface,
    prepare_force_greats_response_frontier_scoring_batch,
    reconstruct_force_greats_response_counts,
    materialize_prepared_force_greats_response_frontier_batch_results,
    score_prepared_force_greats_response_frontier_batch_gpu,
    score_prepared_force_greats_response_frontier_batch_raw_gpu,
    solve_force_greats_response_frontier_batch_gpu,
    solve_force_greats_response_frontier_many_gpu,
)
from .response_build_gpu import (
    build_force_greats_response_first_frontiers_gpu_batch,
    build_force_greats_response_frontiers_gpu_batch,
)

__all__ = [
    "FgResponseFrontierPackedScoringBatch",
    "FgResponseFrontierResult",
    "FgResponseFrontierSolveResult",
    "FgResponseInnerResult",
    "FgResponseSurface",
    "build_force_greats_response_first_frontiers_gpu_batch",
    "build_force_greats_response_frontiers_gpu_batch",
    "prepare_force_greats_response_frontier_scoring_batch",
    "reconstruct_force_greats_response_counts",
    "materialize_prepared_force_greats_response_frontier_batch_results",
    "score_prepared_force_greats_response_frontier_batch_gpu",
    "score_prepared_force_greats_response_frontier_batch_raw_gpu",
    "solve_force_greats_response_frontier_batch_gpu",
    "solve_force_greats_response_frontier_many_gpu",
]
