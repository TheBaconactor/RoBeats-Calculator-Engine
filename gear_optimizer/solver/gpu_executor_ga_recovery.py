from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from gear_optimizer.solver.gpu_executor_types import GpuRequestType


def staged_ga_recovery_index(
    staged_requests: Sequence[Any],
    *,
    is_ga_recovery_request: Callable[[Any], bool],
) -> int | None:
    if not staged_requests:
        return None
    first_request = staged_requests[0]
    if getattr(first_request, "request_type", None) != GpuRequestType.GPU_NATIVE_GA_RUN:
        return None

    for idx, staged in enumerate(staged_requests):
        if idx == 0:
            continue
        request_type = getattr(staged, "request_type", None)
        if request_type == GpuRequestType.SHUTDOWN:
            return int(idx)
        if is_ga_recovery_request(staged):
            return int(idx)
    return None


def prefetch_ga_recovery_requests(
    *,
    in_process_queues: bool,
    ga_owner_turn_streak: int,
    staged_requests: Any,
    deadline: float,
    batch_max_size: int,
    streak_cap: int,
    lookahead_limit: int,
    pop_queue_request: Callable[[float], Any],
    perf_counter_fn: Callable[[], float],
    is_ga_recovery_request: Callable[[Any], bool],
    empty_exception: type[BaseException],
) -> None:
    if not bool(in_process_queues):
        return
    if int(ga_owner_turn_streak) < int(streak_cap):
        return
    if not staged_requests:
        return
    try:
        first_request = staged_requests[0]
    except (IndexError, AttributeError):
        return
    if getattr(first_request, "request_type", None) != GpuRequestType.GPU_NATIVE_GA_RUN:
        return
    if staged_ga_recovery_index(
        list(staged_requests),
        is_ga_recovery_request=is_ga_recovery_request,
    ) is not None:
        return

    target = max(0, int(lookahead_limit))
    if target <= 0:
        return

    while len(staged_requests) < int(target):
        remaining = float(deadline - perf_counter_fn())
        if remaining <= 0.0:
            break
        try:
            request = pop_queue_request(remaining)
        except empty_exception:
            break
        staged_requests.append(request)
        if request.request_type == GpuRequestType.SHUTDOWN:
            break
        if is_ga_recovery_request(request):
            break
