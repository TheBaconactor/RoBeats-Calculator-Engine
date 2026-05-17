from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass
import logging
import queue
import time
from typing import Any

from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType, GpuResponse

logger = logging.getLogger(__name__)


FG_REQUEST_TYPES = frozenset(
    {
        GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
        GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS,
        GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH,
        GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS,
        GpuRequestType.FG_RESET_GLOBAL_BEST,
        GpuRequestType.FG_DOWNLOAD_GLOBAL_BEST,
        GpuRequestType.FG_SELECT_SIGNATURE_FRONTIER_BATCH,
        GpuRequestType.FG_COMPUTE_BREAKPOINTS,
    }
)

GA_RECOVERY_REQUEST_TYPES = frozenset(FG_REQUEST_TYPES)

COALESCABLE_REQUEST_TYPES = frozenset(
    {
        GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
        GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
        GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS,
        GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH,
        GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS,
    }
)

NO_BATCH_REQUEST_TYPES = frozenset({GpuRequestType.GPU_NATIVE_GA_RUN})
NO_BATCH_REQUEST_TYPE_VALUES = frozenset({str(rt.value) for rt in NO_BATCH_REQUEST_TYPES})
GA_RECOVERY_REQUEST_TYPE_VALUES = frozenset({str(rt.value) for rt in GA_RECOVERY_REQUEST_TYPES})


def request_type_in(request_type: Any, request_types: frozenset[GpuRequestType], request_type_values: frozenset[str]) -> bool:
    if request_type in request_types:
        return True
    try:
        value = str(getattr(request_type, "value", request_type))
    except (AttributeError, TypeError):
        value = ""
    return value in request_type_values


def is_no_batch_request_type(request_type: Any) -> bool:
    return request_type_in(request_type, NO_BATCH_REQUEST_TYPES, NO_BATCH_REQUEST_TYPE_VALUES)


def is_ga_recovery_request_type(request_type: Any) -> bool:
    return request_type_in(request_type, GA_RECOVERY_REQUEST_TYPES, GA_RECOVERY_REQUEST_TYPE_VALUES)


def is_ga_recovery_request(request: Any) -> bool:
    return is_ga_recovery_request_type(getattr(request, "request_type", None))


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


def order_responses_for_requests(
    requests: list[GpuRequest],
    responses: Any,
) -> list[GpuResponse | None]:
    by_id: dict[int, GpuResponse] = {}
    for response in responses or []:
        if response is None:
            continue
        try:
            by_id[int(response.request_id)] = response
        except (ValueError, TypeError, AttributeError):
            continue
    return [by_id.get(int(req.request_id)) for req in requests]


class ResponseDeliveryTracker:
    def __init__(self) -> None:
        self.failures_total = 0
        self.failures_by_worker = defaultdict(int)
        self.last_warn_monotonic = 0.0

    def reset(self) -> None:
        self.failures_total = 0
        self.failures_by_worker.clear()
        self.last_warn_monotonic = 0.0

    def try_put(
        self,
        response_queues: dict[int, Any],
        request: GpuRequest,
        response: GpuResponse,
    ) -> bool:
        try:
            q = response_queues.get(request.worker_id)
            if q is None:
                return False
            put_nowait = getattr(q, "put_nowait", None)
            if callable(put_nowait):
                put_nowait(response)
            else:
                q.put(response, block=False)
            return True
        except queue.Full:
            self._record_failure(request, "Response queue full; dropping response")
            return False
        except Exception as e:
            logger.debug(f"gpu_executor_dispatch:try_put: {e}")
            self._record_failure(request, "Failed to deliver response")
            return False

    def _record_failure(self, request: GpuRequest, message: str) -> None:
        try:
            self.failures_total += 1
            self.failures_by_worker[int(request.worker_id)] += 1
            now = time.monotonic()
            if (now - float(self.last_warn_monotonic or 0.0)) < 5.0:
                return
            self.last_warn_monotonic = now
            logger.warning(
                "[GpuExecutor] %s (worker_id=%s request_id=%s type=%s total_failures=%s)",
                str(message),
                int(request.worker_id),
                int(getattr(request, "request_id", 0) or 0),
                str(getattr(getattr(request, "request_type", None), "value", "") or ""),
                int(self.failures_total),
            )
        except Exception as e:
            logger.debug(f"gpu_executor_dispatch:_record_failure: {e}")
