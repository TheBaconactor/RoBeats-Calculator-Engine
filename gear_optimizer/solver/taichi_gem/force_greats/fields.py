"""Minimal ForceGreats field/runtime stubs for response-frontier production FG."""
from __future__ import annotations

from ..runtime import on_hard_reset

_response_frontier_warmed = False


@on_hard_reset
def reset_fields_state() -> None:
    """Reset module-level warmup state after `ti.reset()`."""
    global _response_frontier_warmed
    _response_frontier_warmed = False


def ensure_ready_with_warmup() -> None:
    """
    Ensure Taichi is initialized and response-frontier FG runtime imports are loaded.

    Production FG uses response-frontier search; legacy finder kernels/fields are gone.
    """
    global _response_frontier_warmed
    from ..runtime import init_taichi, is_initialized
    if not is_initialized():
        init_taichi()
    if not _response_frontier_warmed:
        from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
            FgResponseFrontierOwnerResult,
            score_prepared_force_greats_response_frontier_batch_on_cpu_owner,
        )

        _ = (
            FgResponseFrontierOwnerResult,
            score_prepared_force_greats_response_frontier_batch_on_cpu_owner,
        )
        _response_frontier_warmed = True
