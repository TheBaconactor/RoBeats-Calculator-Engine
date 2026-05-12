from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType, GpuResponse


@dataclass(frozen=True)
class GpuExecutionUnit:
    request_type: GpuRequestType
    requests: tuple[GpuRequest, ...]
    grouped: bool


def execute_request_from_dispatch(
    request: GpuRequest,
    *,
    dispatch: Mapping[Any, Callable[[GpuRequest], GpuResponse]],
) -> GpuResponse:
    req_type = getattr(request, "request_type", None)
    request_id = int(getattr(request, "request_id", 0) or 0)
    if req_type == GpuRequestType.SHUTDOWN:
        return GpuResponse(request_id=request_id, success=True, result=None)

    handler = dispatch.get(req_type)
    if handler is None:
        return GpuResponse(
            request_id=request_id,
            success=False,
            error=f"Unsupported GPU request type: {req_type!r}",
        )

    try:
        return handler(request)
    except Exception as exc:
        return GpuResponse(
            request_id=request_id,
            success=False,
            error=f"GpuExecutor error: {type(exc).__name__}: {exc}",
        )


def plan_execution_units(
    batch: list[GpuRequest],
    *,
    grouped_request_types: set[GpuRequestType],
) -> list[GpuExecutionUnit]:
    execution_units: list[GpuExecutionUnit] = []
    for req in batch:
        request_type = req.request_type
        if request_type in grouped_request_types:
            if (
                execution_units
                and execution_units[-1].grouped
                and execution_units[-1].request_type == request_type
            ):
                prev = execution_units[-1]
                execution_units[-1] = GpuExecutionUnit(
                    request_type=prev.request_type,
                    requests=(*prev.requests, req),
                    grouped=True,
                )
            else:
                execution_units.append(
                    GpuExecutionUnit(
                        request_type=request_type,
                        requests=(req,),
                        grouped=True,
                    )
                )
        else:
            execution_units.append(
                GpuExecutionUnit(
                    request_type=request_type,
                    requests=(req,),
                    grouped=False,
                )
            )
    return execution_units
