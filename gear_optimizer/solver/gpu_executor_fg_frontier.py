from __future__ import annotations

from collections.abc import Callable
from typing import Any

from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuResponse


def execute_fg_select_signature_frontier_batch(
    request: GpuRequest,
    *,
    in_process_queues: bool,
    select_fn: Callable[[list[dict[str, Any]]], Any],
) -> GpuResponse:
    if not in_process_queues:
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error="FG_SELECT_SIGNATURE_FRONTIER_BATCH requires in-process queues (avoid IPC pickling)",
        )

    payload = request.payload or {}
    payloads = payload.get("payloads")
    if not isinstance(payloads, list):
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error="FG_SELECT_SIGNATURE_FRONTIER_BATCH requires payload['payloads'] list",
        )

    result = select_fn(payloads)
    return GpuResponse(
        request_id=request.request_id,
        success=True,
        result=result,
    )
