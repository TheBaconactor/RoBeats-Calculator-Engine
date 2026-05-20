"""Scoring package public API surface.

The live package now exposes runtime state, stat helpers, and Force Greats
evaluation only.
"""

# Import from runtime_state
from .runtime_state import (
    _GPU_LOCK,
    FG_CACHE,
    FORCE_GREATS_ALGO_VERSION,
)

# Import from stats_scoring
from .stats_scoring import (
    evaluate_stats_score,
    build_great_penalty_table,
    fg_baseline_params,
    _force_greats_counts_to_dict,
    _song_cache_key,
)

# Import from force_greats
from .force_greats import (
    FG_TIMELINE_CACHE,
    _compute_force_greats_timeline,
    evaluate_force_greats,
    evaluate_fg_with_gem_iteration,
    run_force_greats_hill_climb,
    apply_force_greats_to_result,
    _extract_base_stats,
)

# Public API
__all__ = [
    # GPU solver
    "_GPU_LOCK",
    "FG_CACHE",
    "FORCE_GREATS_ALGO_VERSION",
    # Stats scoring
    "evaluate_stats_score",
    "build_great_penalty_table",
    "fg_baseline_params",
    "_force_greats_counts_to_dict",
    "_song_cache_key",
    # Force greats
    "FG_TIMELINE_CACHE",
    "_compute_force_greats_timeline",
    "evaluate_force_greats",
    "evaluate_fg_with_gem_iteration",
    "run_force_greats_hill_climb",
    "apply_force_greats_to_result",
    "_extract_base_stats",
]
