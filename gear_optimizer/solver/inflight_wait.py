from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)


def read_inflight_event_wait_timeout_s() -> float:
    """
    Base scheduler wait timeout when waiting for in-flight futures to complete.

    Keep this modest to avoid long producer wake-up delays that can starve the
    GPU owner thread between Base/FG stage transitions.
    """
    return 0.05


def read_inflight_event_wait_gpu_cap_s() -> float:
    """
    Optional tighter cap for completion-event waits while GPU work is active.

    A small cap reduces Base-to-FG handoff latency jitter under Windows scheduler/timer noise.
    Set to 0 to disable this cap.
    """
    return 0.01


def read_inflight_event_wait_short_spin_s() -> float:
    """
    Short-window polling threshold for completion-event waits.

    For very small waits, poll with zero-timeout checks to avoid coarse timed-wait
    quantization from stretching sub-ms/ms windows into multi-ms idle bubbles.
    """
    return 0.003


def read_inflight_event_wait_spin_yield_rounds() -> int:
    """
    Upper bound for `time.sleep(0)` yield rounds in the short-spin path.

    On Windows, a pure `sleep(0)` loop can burn CPU. We yield a limited number of
    times, then fall back to a tiny blocking wait to reduce host overhead.
    """
    return 8


def wait_for_completion_event(
    completion_event: threading.Event,
    *,
    timeout_s: float,
    short_spin_s: float,
    spin_yield_rounds: int | None = None,
    perf_counter: Callable[[], float] | None = None,
    sleep: Callable[[float], object] | None = None,
) -> bool:
    perf_counter_fn = perf_counter or time.perf_counter
    sleep_fn = sleep or time.sleep

    wait_timeout = max(0.0, float(timeout_s))
    if wait_timeout <= 0.0:
        return bool(completion_event.wait(timeout=0.0))

    short_spin = max(0.0, float(short_spin_s))
    if wait_timeout > short_spin:
        return bool(completion_event.wait(timeout=wait_timeout))

    deadline = perf_counter_fn() + wait_timeout
    max_yields = (
        int(spin_yield_rounds)
        if spin_yield_rounds is not None
        else int(read_inflight_event_wait_spin_yield_rounds())
    )
    yields = 0

    while True:
        if completion_event.wait(timeout=0.0):
            return True

        now = perf_counter_fn()
        if now >= deadline:
            return False

        remaining = float(deadline - now)
        if yields < max_yields:
            yields += 1
            sleep_fn(0)
            continue

        # After a few yields, block in tiny chunks to avoid burning CPU.
        block_s = min(remaining, 0.001)  # 1ms cap
        if block_s <= 0.0:
            return False
        completion_event.wait(timeout=block_s)
