"""Minimal ForceGreats field/runtime stubs for response-frontier production FG."""
from __future__ import annotations

_response_frontier_warmed = False


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
    from gear_optimizer.helpers.song_helpers.force_greats.response_frontier_warmup import (
        warmup_force_greats_response_frontier_runtime_imports,
    )

    if not is_initialized():
        init_taichi()
    if not _response_frontier_warmed:
        warmup_force_greats_response_frontier_runtime_imports()
        _response_frontier_warmed = True
