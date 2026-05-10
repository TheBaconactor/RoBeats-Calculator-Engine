"""
Scoring Package - Score Calculation and Gem Optimization.

This package splits the monolithic scoring.py (2,056 lines) into 5 focused modules:
1. gpu_solver.py - GPU solver initialization and global caches
2. stats_scoring.py - Stats evaluation helpers
3. fever_solver.py - Fever timeline and gem combination optimization
4. genome_evaluation.py - Batch genome evaluation for skyline candidates

This __init__.py defines the public scoring API surface.

Avoid duplicating gem search in pipeline/orchestrator code.
"""

# Import from gpu_solver
from .gpu_solver import (
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
    precompute_fever_timelines,
    solve_best_fever_combination,
)

# Import from genome_evaluation
from .genome_evaluation import (
    worker_coevolution_evaluate,
    batch_evaluate_genomes,
)

# Import from fg_utils (helper)
from ...helpers.fg_utils import generate_dynamic_fg_configs

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
    "precompute_fever_timelines",
    "solve_best_fever_combination",
    # Genome evaluation
    "worker_coevolution_evaluate",
    "batch_evaluate_genomes",
    # Helpers
    "generate_dynamic_fg_configs",
]
