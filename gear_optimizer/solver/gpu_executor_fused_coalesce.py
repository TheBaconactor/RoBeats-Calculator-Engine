from __future__ import annotations

from dataclasses import dataclass

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
