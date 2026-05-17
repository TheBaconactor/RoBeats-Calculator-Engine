from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from gear_optimizer.solver.gpu_executor_dispatch import order_responses_for_requests
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType, GpuResponse


@dataclass(frozen=True)
class GaFgFusedCoalescePlan:
    synthetic_batch_requests: list[GpuRequest]
    fallback_reason_by_id: dict[int, str]


def build_ga_fg_fused_batch_requests(requests: list[GpuRequest]) -> GaFgFusedCoalescePlan:
    synthetic_batch_requests: list[GpuRequest] = []
    fallback_reason_by_id: dict[int, str] = {}

    for req in requests:
        payload = req.payload
        if not isinstance(payload, dict):
            fallback_reason_by_id.setdefault(int(req.request_id), "invalid request payload type")
            continue
        synthetic_batch_requests.append(
            GpuRequest(
                request_type=GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH,
                request_id=int(req.request_id),
                worker_id=int(req.worker_id),
                payload={"payloads": [payload]},
            )
        )

    return GaFgFusedCoalescePlan(
        synthetic_batch_requests=synthetic_batch_requests,
        fallback_reason_by_id=fallback_reason_by_id,
    )


def unwrap_ga_fg_fused_batch_response(req: GpuRequest, resp: GpuResponse | None) -> tuple[GpuResponse | None, str | None]:
    if resp is None:
        return None, "missing coalesced response"
    if not bool(getattr(resp, "success", False)):
        return None, "coalesced response unsuccessful"
    result = getattr(resp, "result", None)
    if not isinstance(result, list) or len(result) != 1:
        return None, "unexpected coalesced result shape"
    return (
        GpuResponse(
            request_id=int(req.request_id),
            success=True,
            result=result[0],
        ),
        None,
    )


def coalesce_ga_fg_fused_requests(
    requests: list[GpuRequest],
    *,
    in_process_queues: bool,
    execute_request: Callable[[GpuRequest], GpuResponse],
    coalesce_fg_breakpoint_batch: Callable[[list[GpuRequest]], list[GpuResponse]],
    warn_fallback_fn: Callable[..., None],
) -> list[GpuResponse]:
    if not requests:
        return []
    if not bool(in_process_queues) or len(requests) <= 1:
        return [execute_request(req) for req in requests]

    plan = build_ga_fg_fused_batch_requests(requests)
    synthetic_batch_requests = plan.synthetic_batch_requests
    fallback_ids: set[int] = set(plan.fallback_reason_by_id)
    fallback_reason_by_id: dict[int, str] = dict(plan.fallback_reason_by_id)

    def _mark_fallback(req_id: int, reason: str) -> None:
        rid = int(req_id)
        fallback_ids.add(rid)
        if rid not in fallback_reason_by_id:
            fallback_reason_by_id[rid] = str(reason)

    out: list[GpuResponse] = []
    if synthetic_batch_requests:
        batch_responses = coalesce_fg_breakpoint_batch(synthetic_batch_requests)
        for req, resp in zip(synthetic_batch_requests, batch_responses):
            unwrapped, fallback_reason = unwrap_ga_fg_fused_batch_response(req, resp)
            if fallback_reason is not None:
                _mark_fallback(int(req.request_id), fallback_reason)
                continue
            out.append(unwrapped)

    if fallback_ids:
        for req in requests:
            if int(req.request_id) in fallback_ids:
                warn_fallback_fn(
                    "gpu_executor.ga_fg_fused_coalesce.request",
                    "coalesced fused request fallback to per-request execution",
                    context={
                        "request_id": int(req.request_id),
                        "reason": fallback_reason_by_id.get(int(req.request_id), "unknown"),
                    },
                )
                out.append(execute_request(req))

    return order_responses_for_requests(requests, out)
