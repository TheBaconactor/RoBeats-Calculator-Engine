"""Re-export shim for FG response frontier GPU build (see response_build_gpu_*.py)."""

from __future__ import annotations

import concurrent.futures  # noqa: F401

from .response_build_gpu_batch import (
    build_force_greats_response_first_frontiers_gpu_batch,
)
from .response_build_gpu_precompute import _first_only_chunks  # noqa: F401
from .response_build_gpu_reducer import (  # noqa: F401
    _first_frontier_reducer_executor,
    _first_frontier_result_from_precomputed_end_indices,
    _resolve_first_only_reducer_threads,
    configure_force_greats_response_first_frontier_threads,
)

__all__ = [
    "build_force_greats_response_first_frontiers_gpu_batch",
]
