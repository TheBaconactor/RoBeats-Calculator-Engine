from gear_optimizer.solver.gpu_executor_fused_coalesce import (
    build_ga_fg_fused_batch_requests,
    unwrap_ga_fg_fused_batch_response,
)
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType, GpuResponse


def _req(req_id: int, payload) -> GpuRequest:
    return GpuRequest(
        request_type=GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS,
        request_id=int(req_id),
        worker_id=7,
        payload=payload,
    )


def test_build_ga_fg_fused_batch_requests_wraps_valid_payloads_and_marks_invalid():
    plan = build_ga_fg_fused_batch_requests([_req(1, {"a": 1}), _req(2, None)])

    assert plan.fallback_reason_by_id == {2: "invalid request payload type"}
    assert len(plan.synthetic_batch_requests) == 1
    synthetic = plan.synthetic_batch_requests[0]
    assert synthetic.request_type == GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH
    assert synthetic.request_id == 1
    assert synthetic.worker_id == 7
    assert synthetic.payload == {"payloads": [{"a": 1}]}


def test_unwrap_ga_fg_fused_batch_response_returns_original_request_result():
    response, reason = unwrap_ga_fg_fused_batch_response(
        _req(3, {"ok": True}),
        GpuResponse(request_id=3, success=True, result=[{"score": 123}]),
    )

    assert reason is None
    assert response is not None
    assert response.request_id == 3
    assert response.success is True
    assert response.result == {"score": 123}


def test_unwrap_ga_fg_fused_batch_response_reports_fallback_reasons():
    req = _req(4, {"ok": True})

    assert unwrap_ga_fg_fused_batch_response(req, None)[1] == "missing coalesced response"
    assert (
        unwrap_ga_fg_fused_batch_response(req, GpuResponse(request_id=4, success=False, error="bad"))[1]
        == "coalesced response unsuccessful"
    )
    assert (
        unwrap_ga_fg_fused_batch_response(req, GpuResponse(request_id=4, success=True, result=[]))[1]
        == "unexpected coalesced result shape"
    )
