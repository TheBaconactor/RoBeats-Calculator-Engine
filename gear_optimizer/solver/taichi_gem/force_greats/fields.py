"""Minimal ForceGreats field/runtime stubs for Bellman-only production FG."""
from __future__ import annotations

_bellman_warmed = False


def reset_fields_state() -> None:
    """Reset module-level warmup state after `ti.reset()`."""
    global _bellman_warmed
    _bellman_warmed = False


def ensure_ready_with_warmup() -> None:
    """
    Ensure Taichi is initialized and Bellman FG runtime imports are loaded.

    Production FG uses Bellman only; legacy finder kernels/fields are gone.
    """
    global _bellman_warmed
    from ..runtime import init_taichi, is_initialized
    from gear_optimizer.helpers.song_helpers.force_greats.bellman_warmup import (
        warmup_force_greats_bellman_runtime_imports,
    )

    if not is_initialized():
        init_taichi()
    if not _bellman_warmed:
        warmup_force_greats_bellman_runtime_imports()
        _bellman_warmed = True
