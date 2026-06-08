from __future__ import annotations


def warmup_force_greats_response_frontier_runtime_imports() -> None:
    """Load canonical FG response-frontier owner symbols before per-song prep starts."""
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        FgResponseFrontierOwnerResult,
        score_prepared_force_greats_response_frontier_batch_on_gpu_owner,
    )

    _ = (
        FgResponseFrontierOwnerResult,
        score_prepared_force_greats_response_frontier_batch_on_gpu_owner,
    )
