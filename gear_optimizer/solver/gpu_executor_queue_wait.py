from __future__ import annotations

import queue
import time
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Callable, Literal


NowaitFollowupAction = Literal["request", "fallback", "continue", "break"]


@dataclass(frozen=True)
class NowaitFollowupPoll:
    action: NowaitFollowupAction
    request: Any | None
    yields_left: int


@dataclass(frozen=True)
class ShortWaitSpinSettings:
    short_wait_spin_sec: float
    short_wait_spin_yield_rounds: int


def load_short_wait_spin_settings(env_get_fn: Callable[[str, str], Any]) -> ShortWaitSpinSettings:
    try:
        short_wait_spin_ms = float(str(env_get_fn("GPU_EXECUTOR_SHORT_WAIT_SPIN_MS", "3.0") or "3.0").strip())
    except (ValueError, TypeError):
        short_wait_spin_ms = 3.0
    try:
        short_wait_spin_yields = int(str(env_get_fn("GPU_EXECUTOR_SHORT_WAIT_SPIN_YIELD_ROUNDS", "8") or "8").strip())
    except (ValueError, TypeError):
        short_wait_spin_yields = 8

    return ShortWaitSpinSettings(
        short_wait_spin_sec=max(0.0, float(short_wait_spin_ms) / 1000.0),
        short_wait_spin_yield_rounds=max(0, min(int(short_wait_spin_yields), 100_000)),
    )


def safe_qsize(request_queue: Any) -> int:
    if request_queue is None:
        return -1
    try:
        size = request_queue.qsize()
    except (NotImplementedError, AttributeError):
        return -1
    except (OSError, ValueError):
        return -1
    try:
        return max(0, int(size))
    except (ValueError, TypeError):
        return -1


def get_with_short_wait_spin(
    request_queue: Any,
    *,
    timeout: float,
    in_process_queues: bool,
    short_wait_spin_sec: float,
    short_wait_spin_yield_rounds: int,
    perf_counter_fn: Callable[[], float] = perf_counter,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> Any:
    wait_timeout = max(0.0, float(timeout))
    if wait_timeout <= 0.0:
        return request_queue.get(timeout=0.0)

    if not in_process_queues or wait_timeout > float(short_wait_spin_sec):
        return request_queue.get(timeout=wait_timeout)

    get_nowait = getattr(request_queue, "get_nowait", None)
    if not callable(get_nowait):
        return request_queue.get(timeout=wait_timeout)

    deadline = perf_counter_fn() + wait_timeout
    yields = 0
    max_yields = int(short_wait_spin_yield_rounds or 0)
    while True:
        try:
            return get_nowait()
        except queue.Empty:
            now = perf_counter_fn()
            if now >= deadline:
                raise
            remaining = float(deadline - now)
            if yields < max_yields:
                yields += 1
                sleep_fn(0)
                continue

            block_s = min(remaining, 0.001)
            if block_s <= 0.0:
                raise
            try:
                return request_queue.get(timeout=block_s)
            except queue.Empty:
                continue


def poll_inprocess_followup_nowait(
    request_queue: Any,
    *,
    deadline_s: float,
    yields_left: int,
    stamp_fn: Callable[[Any], Any],
    perf_counter_fn: Callable[[], float] = perf_counter,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> NowaitFollowupPoll:
    get_nowait = getattr(request_queue, "get_nowait", None)
    if not callable(get_nowait):
        return NowaitFollowupPoll(action="fallback", request=None, yields_left=int(yields_left))

    try:
        return NowaitFollowupPoll(
            action="request",
            request=stamp_fn(get_nowait()),
            yields_left=int(yields_left),
        )
    except queue.Empty:
        if perf_counter_fn() >= float(deadline_s) or int(yields_left) <= 0:
            return NowaitFollowupPoll(action="break", request=None, yields_left=int(yields_left))
        sleep_fn(0)
        return NowaitFollowupPoll(action="continue", request=None, yields_left=int(yields_left) - 1)
