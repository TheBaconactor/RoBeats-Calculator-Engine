from __future__ import annotations

import time
from collections import deque
from typing import Any, Callable


def stamp_request_dequeue(
    request: Any,
    *,
    perf_counter_ns_fn: Callable[[], int] = time.perf_counter_ns,
) -> Any:
    try:
        if int(getattr(request, "dequeue_perf_ns", 0) or 0) <= 0:
            request.dequeue_perf_ns = int(perf_counter_ns_fn())
    except (ValueError, TypeError, AttributeError):
        pass
    return request


def stage_request(
    staged_requests: deque,
    request: Any,
    *,
    front: bool = False,
    stamp_fn: Callable[[Any], Any] = stamp_request_dequeue,
) -> None:
    stamped = stamp_fn(request)
    if front:
        staged_requests.appendleft(stamped)
    else:
        staged_requests.append(stamped)


def pop_staged_request(staged_requests: deque, *, index: int = 0) -> Any:
    if index <= 0:
        return staged_requests.popleft()
    rotate_by = int(index)
    staged_requests.rotate(-rotate_by)
    try:
        return staged_requests.popleft()
    finally:
        staged_requests.rotate(rotate_by)
