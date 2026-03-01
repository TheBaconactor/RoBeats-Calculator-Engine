"""
GPU Solver Globals (Lock + Caches).

This module provides:
- a process-local `_GPU_LOCK` to serialize Taichi kernel calls
- global LRU caches for scoring/FG performance
"""

import threading
from cachetools import LRUCache


_GPU_LOCK = threading.Lock()  # Serialize GPU kernel calls


# Global caches for performance optimization
GEM_SOLVER_CACHE = LRUCache(maxsize=5000)
FEVER_TIMELINE_CACHE = LRUCache(maxsize=10000)
FG_CACHE = LRUCache(maxsize=2000)

# Bump this whenever ForceGreats evaluation semantics change, so we can invalidate
# stale DB-cached FG payloads (they can otherwise look like "score inflation").
FORCE_GREATS_ALGO_VERSION = 3
