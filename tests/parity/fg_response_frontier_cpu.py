"""CPU and GPU parity references for FG response-frontier tests."""

from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
    build_force_greats_response_frontier,
    reconstruct_force_greats_response_counts,
    response_surface_dominates,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_inner import (
    optimize_response_frontier_inner_exact,
    optimize_response_frontier_inner_exact_gpu,
    score_response_surface_exact,
)

__all__ = [
    "build_force_greats_response_frontier",
    "optimize_response_frontier_inner_exact",
    "optimize_response_frontier_inner_exact_gpu",
    "reconstruct_force_greats_response_counts",
    "response_surface_dominates",
    "score_response_surface_exact",
]
