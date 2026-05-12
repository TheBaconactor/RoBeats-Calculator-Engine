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
