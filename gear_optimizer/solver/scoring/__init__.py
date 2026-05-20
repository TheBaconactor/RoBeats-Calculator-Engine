"""
Scoring Package - Score Calculation and Gem Optimization.

This package splits the monolithic scoring.py (2,056 lines) into 5 focused modules:
1. runtime_state.py - GPU solver runtime state and global caches
2. stats_scoring.py - Stats evaluation helpers
3. fever_solver.py - Fever timeline and gem combination optimization
4. force_greats.py - Force greats timeline, evaluation, and hill climb
5. genome_evaluation.py - Batch genome evaluation for GA

This __init__.py defines the public scoring API surface.

Avoid duplicating gem search or FG scoring in pipeline/orchestrator code.
"""

# Import from runtime_state
from .runtime_state import (
    _GPU_LOCK,
    GEM_SOLVER_CACHE,
    FEVER_TIMELINE_CACHE,
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

# Import from fever_solver
from .fever_solver import (
    solve_best_fever_combination,
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

# Import from genome_evaluation
from .genome_evaluation import (
    worker_coevolution_evaluate,
    batch_evaluate_genomes,
)

# Public API
__all__ = [
    # GPU solver
    "_GPU_LOCK",
    "GEM_SOLVER_CACHE",
    "FEVER_TIMELINE_CACHE",
    "FG_CACHE",
    "FORCE_GREATS_ALGO_VERSION",
    # Stats scoring
    "evaluate_stats_score",
    "build_great_penalty_table",
    "fg_baseline_params",
    "_force_greats_counts_to_dict",
    "_song_cache_key",
    # Fever solver
    "solve_best_fever_combination",
    # Force greats
    "FG_TIMELINE_CACHE",
    "_compute_force_greats_timeline",
    "evaluate_force_greats",
    "evaluate_fg_with_gem_iteration",
    "run_force_greats_hill_climb",
    "apply_force_greats_to_result",
    "_extract_base_stats",
    # Genome evaluation
    "worker_coevolution_evaluate",
    "batch_evaluate_genomes",
]
