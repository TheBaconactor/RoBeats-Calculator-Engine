"""
ForceGreats GPU implementation (Taichi/Vulkan).

Production FG uses the response-frontier solver in `response_frontier.py`.
"""

from .response_frontier import (
    FgResponseFrontierSolveResult,
    FgResponseSurface,
    materialize_force_greats_response_frontier_owner_result,
    prepare_force_greats_response_frontier_scoring_batch,
    reconstruct_force_greats_response_counts,
    reconstruct_force_greats_response_trace,
    run_prepared_force_greats_response_frontier_batches_via_client,
    score_prepared_force_greats_response_frontier_batch_on_gpu_owner,
    score_prepared_force_greats_response_frontier_batch_sync,
)

__all__ = [
    "FgResponseFrontierSolveResult",
    "FgResponseSurface",
    "materialize_force_greats_response_frontier_owner_result",
    "prepare_force_greats_response_frontier_scoring_batch",
    "reconstruct_force_greats_response_counts",
    "reconstruct_force_greats_response_trace",
    "run_prepared_force_greats_response_frontier_batches_via_client",
    "score_prepared_force_greats_response_frontier_batch_on_gpu_owner",
    "score_prepared_force_greats_response_frontier_batch_sync",
]
