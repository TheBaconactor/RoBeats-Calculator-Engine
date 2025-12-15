"""
Scoring Package - Score Calculation and Gem Optimization.

This package splits the monolithic scoring.py (2,056 lines) into 5 focused modules:
1. gpu_solver.py - GPU solver initialization and global caches
2. stats_scoring.py - Stats evaluation helpers
3. fever_solver.py - Fever timeline and gem combination optimization
4. force_greats.py - Force greats timeline, evaluation, and hill climb (PENDING)
5. genome_evaluation.py - Batch genome evaluation for GA (PENDING)

This __init__.py provides backward-compatible imports so existing code continues to work.
"""

# Import from gpu_solver
try:
    from .gpu_solver import (
        _get_gpu_solver,
        _GPU_LOCK,
        GEM_SOLVER_CACHE,
        FEVER_TIMELINE_CACHE,
        FG_CACHE,
        FORCE_GREATS_ALGO_VERSION,
    )
except ImportError:
    pass

# Import from stats_scoring
try:
    from .stats_scoring import (
        evaluate_stats_score,
        build_great_penalty_table,
        fg_baseline_params,
        _force_greats_counts_to_dict,
        _song_cache_key,
    )
except ImportError:
    pass

# Import from fever_solver
try:
    from .fever_solver import (
        precompute_fever_timelines,
        solve_best_fever_combination,
    )
except ImportError:
    pass

# Export all public names for backward compatibility
__all__ = [
    # GPU solver
    "_get_gpu_solver",
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
    "precompute_fever_timelines",
    "solve_best_fever_combination",
]
