"""Scoring package public API surface.

The live package exposes runtime state, stat helpers, and Force Greats
evaluation for tooling/rescoring. Production FG uses the response-frontier GPU path.
"""

from .runtime_state import (
    _GPU_LOCK,
    FG_CACHE,
    FORCE_GREATS_ALGO_VERSION,
)
from .stats_scoring import (
    evaluate_stats_score,
    build_great_penalty_table,
    fg_baseline_params,
    _force_greats_counts_to_dict,
    _song_cache_key,
)
from .force_greats import (
    _compute_force_greats_timeline,
    evaluate_force_greats,
)

__all__ = [
    "_GPU_LOCK",
    "FG_CACHE",
    "FORCE_GREATS_ALGO_VERSION",
    "evaluate_stats_score",
    "build_great_penalty_table",
    "fg_baseline_params",
    "_force_greats_counts_to_dict",
    "_song_cache_key",
    "_compute_force_greats_timeline",
    "evaluate_force_greats",
]
