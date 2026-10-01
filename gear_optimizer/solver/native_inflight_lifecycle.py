"""Consolidated lifecycle helpers for the native in-flight optimizer."""
from __future__ import annotations

import concurrent.futures
import logging
from collections.abc import Callable
from typing import Any

from gear_optimizer.solver.native_inflight_lifecycle_prepare import (
    _lru_get,
    _lru_put,
    prepare_native_song,
)
from gear_optimizer.solver.native_inflight_lifecycle_progress import (
    ProgressTracker,
    evaluate_fg_progress_record_update,
)
from gear_optimizer.solver.native_inflight_lifecycle_queues import PostSender

logger = logging.getLogger(__name__)

ProgressCallback = Callable[..., Any]


# Taichi/Vulkan init plus kernel warmup on a cold offline cache.
GPU_EXECUTOR_INIT_TIMEOUT_S = 600.0


def is_stop_abort_exception(exc: BaseException) -> bool:
    if isinstance(exc, concurrent.futures.CancelledError):
        return True
    msg = str(exc or "")
    return "GpuExecutor aborted:" in msg


__all__ = [
    "PostSender",
    "ProgressTracker",
    "_lru_get",
    "_lru_put",
    "evaluate_fg_progress_record_update",
    "is_stop_abort_exception",
    "prepare_native_song",
]
