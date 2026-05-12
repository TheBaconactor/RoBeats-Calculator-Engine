from __future__ import annotations

import concurrent.futures
import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Any

logger = logging.getLogger(__name__)


@dataclass
class CachedRuntimeSignal:
    callback: Callable[[], bool] | None
    poll_interval_s: float = 0.05
    next_check_mono: float = 0.0
    cached_requested: bool = False
    monotonic: Callable[[], float] = field(default=time.monotonic, repr=False)

    def requested(self, now_mono: float | None = None) -> bool:
        if self.cached_requested:
            return True
        if self.callback is None or not callable(self.callback):
            return False
        now_val = float(self.monotonic() if now_mono is None else now_mono)
        if now_val < float(self.next_check_mono):
            return False
        self.cached_requested = bool(self.callback())
        if self.cached_requested:
            return True
        self.next_check_mono = now_val + float(self.poll_interval_s)
        return False


@dataclass
class GpuAbortRequester:
    gpu_executor: Any
    requested_once: bool = False

    def request(self, reason: str) -> bool:
        if self.requested_once:
            return False
        self.requested_once = True
        try:
            self.gpu_executor.request_abort(str(reason or "stop requested"))
        except Exception as e:
            logger.debug(f"native_inflight_runtime_signals:GpuAbortRequester.request: {e}")
        return True


def is_stop_abort_exception(exc: BaseException) -> bool:
    if isinstance(exc, concurrent.futures.CancelledError):
        return True
    try:
        msg = str(exc or "")
    except Exception as e:
        logger.debug(f"native_inflight_runtime_signals:is_stop_abort_exception: {e}")
        msg = ""
    return "GpuExecutor aborted:" in msg
