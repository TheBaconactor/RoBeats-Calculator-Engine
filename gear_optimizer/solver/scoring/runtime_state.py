"""GPU solver runtime state.

This module owns the process-local `_GPU_LOCK` used to serialize Taichi
kernel execution.
"""

from __future__ import annotations

import threading


_GPU_LOCK = threading.Lock()
