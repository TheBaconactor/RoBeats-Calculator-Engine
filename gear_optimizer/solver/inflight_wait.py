from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable


def read_inflight_event_wait_gpu_cap_s() -> float:
    """
    Optional tighter cap for completion-event waits while GPU work is active.

    A small cap reduces GA->FG handoff latency jitter under Windows scheduler/timer noise.
    Set to 0 to disable this cap.
    """
    timeout_s = 0.01
    raw = os.environ.get("INFLIGHT_EVENT_WAIT_GPU_CAP_SEC")
    if raw is not None and str(raw).strip() != "":
        try:
            timeout_s = float(raw)
        except Exception:
            pass
    return max(0.0, min(float(timeout_s), 1.0))


def read_inflight_event_wait_short_spin_s() -> float:
    """
    Short-window polling threshold for completion-event waits.

    For very small waits, poll with zero-timeout checks to avoid coarse timed-wait
    quantization from stretching sub-ms/ms windows into multi-ms idle bubbles.
    """
    short_spin_ms = 3.0
    raw = os.environ.get("INFLIGHT_EVENT_WAIT_SHORT_SPIN_MS")
    if raw is not None and str(raw).strip() != "":
        try:
            short_spin_ms = float(raw)
        except Exception:
            pass
    return max(0.0, min(float(short_spin_ms) / 1000.0, 0.050))


def read_inflight_event_wait_spin_yield_rounds() -> int:
    """
    Upper bound for `time.sleep(0)` yield rounds in the short-spin path.

    On Windows, a pure `sleep(0)` loop can burn CPU. We yield a limited number of
    times, then fall back to a tiny blocking wait to reduce host overhead.
    """
    rounds = 8
    raw = os.environ.get("INFLIGHT_EVENT_WAIT_SPIN_YIELD_ROUNDS")
    if raw is not None and str(raw).strip() != "":
        try:
            rounds = int(raw)
        except Exception:
            pass
    return max(0, min(int(rounds), 100_000))


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
