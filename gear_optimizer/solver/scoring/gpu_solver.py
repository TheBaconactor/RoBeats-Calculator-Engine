"""
GPU Solver Initialization and Global Caches.

This module handles lazy initialization of the GPU gem solver (Taichi)
and provides global LRU caches for performance optimization.
"""
import threading
from cachetools import LRUCache


# GPU Gem Solver (lazy import to avoid init overhead if not used)
_gpu_solver_loaded = False
_optimize_gems_gpu = None
_optimize_gems_batch_gpu = None
_GPU_LOCK = threading.Lock()  # Serialize GPU kernel calls


def _get_gpu_solver():
    """
    Lazy-load the GPU gem solver to avoid Taichi init on import.

    Returns:
        tuple: (optimize_gems_gpu, optimize_gems_batch_gpu) or (None, None) on failure
    """
    global _gpu_solver_loaded, _optimize_gems_gpu, _optimize_gems_batch_gpu
    if not _gpu_solver_loaded:
        try:
            from ..taichi_gem_solver import (
                optimize_gems_gpu,
                optimize_gems_batch_gpu,
            )
            _optimize_gems_gpu = optimize_gems_gpu
            _optimize_gems_batch_gpu = optimize_gems_batch_gpu
            _gpu_solver_loaded = True
        except ImportError as e:
            print(f"[GPU] Failed to load Taichi gem solver: {e}")
            _optimize_gems_gpu = None
            _optimize_gems_batch_gpu = None
            _gpu_solver_loaded = True  # Mark as attempted
    return _optimize_gems_gpu, _optimize_gems_batch_gpu


# Global caches for performance optimization
GEM_SOLVER_CACHE = LRUCache(maxsize=5000)
FEVER_TIMELINE_CACHE = LRUCache(maxsize=10000)
FG_CACHE = LRUCache(maxsize=2000)

# Bump this whenever ForceGreats evaluation semantics change, so we can invalidate
# stale DB-cached FG payloads (they can otherwise look like "score inflation").
FORCE_GREATS_ALGO_VERSION = 3
