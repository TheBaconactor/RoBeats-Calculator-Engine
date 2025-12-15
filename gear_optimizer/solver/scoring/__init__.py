"""
Scoring Package - Score Calculation and Gem Optimization.

This package splits the monolithic scoring.py (2,056 lines) into 5 focused modules:
1. gpu_solver.py - GPU solver initialization and global caches
2. stats_scoring.py - Stats evaluation helpers (PENDING)
3. fever_solver.py - Fever timeline and gem combination optimization (PENDING)
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

# Export all public names for backward compatibility
__all__ = [
    # GPU solver
    "_get_gpu_solver",
    "_GPU_LOCK",
    "GEM_SOLVER_CACHE",
    "FEVER_TIMELINE_CACHE",
    "FG_CACHE",
    "FORCE_GREATS_ALGO_VERSION",
]
