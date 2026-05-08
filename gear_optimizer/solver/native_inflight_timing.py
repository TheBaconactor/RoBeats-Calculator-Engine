from __future__ import annotations

import time
import logging



logger = logging.getLogger(__name__)
def _thread_cpu_time_s() -> float:
    """
    Best-effort per-thread CPU timer for CPU-only profiling.

    Uses `time.thread_time()` when available (Python 3.7+). Returns 0.0 on unsupported platforms.
    """
    try:
        return float(time.thread_time())
    except Exception as e:
        logger.debug(f"native_inflight_timing:_thread_cpu_time_s: {e}")
        return 0.0

