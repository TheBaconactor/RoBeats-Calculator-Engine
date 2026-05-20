"""GPU solver runtime state.

This module owns the process-local `_GPU_LOCK` used to serialize Taichi
kernel execution plus the force-greats cache and version marker.
"""

from __future__ import annotations

import threading

from cachetools import LRUCache


_GPU_LOCK = threading.Lock()
FG_CACHE = LRUCache(maxsize=2000)

# Bump this whenever ForceGreats evaluation semantics change.
FORCE_GREATS_ALGO_VERSION = 3
