"""
GPU solver runtime state.

This module owns:
- process-local `_GPU_LOCK` for Taichi kernel serialization
- global LRU caches for scoring/FG performance
- force-greats algorithm versioning
"""

from __future__ import annotations

import threading

from cachetools import LRUCache


_GPU_LOCK = threading.Lock()

GEM_SOLVER_CACHE = LRUCache(maxsize=5000)
FEVER_TIMELINE_CACHE = LRUCache(maxsize=10000)
FG_CACHE = LRUCache(maxsize=2000)

# Bump this whenever ForceGreats evaluation semantics change.
FORCE_GREATS_ALGO_VERSION = 3
