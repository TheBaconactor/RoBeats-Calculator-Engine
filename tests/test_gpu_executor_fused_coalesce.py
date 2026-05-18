from gear_optimizer.solver.gpu_executor_batching import (
    build_ga_fg_fused_batch_requests,
    coalesce_ga_fg_fused_requests,
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


def test_coalesce_ga_fg_fused_requests_routes_through_batch_handler():
    fallback_warnings = []
    direct_calls = []

    responses = coalesce_ga_fg_fused_requests(
        [_req(10, {"a": 1}), _req(11, {"b": 2})],
        in_process_queues=True,
        execute_request=lambda req: direct_calls.append(req.request_id)
        or GpuResponse(request_id=req.request_id, success=True, result={"direct": req.request_id}),
        coalesce_fg_breakpoint_batch=lambda reqs: [
            GpuResponse(request_id=reqs[0].request_id, success=True, result=[{"score": 10}]),
            GpuResponse(request_id=reqs[1].request_id, success=True, result=[{"score": 11}]),
        ],
        warn_fallback_fn=lambda *args, **kwargs: fallback_warnings.append((args, kwargs)),
    )

    assert direct_calls == []
    assert fallback_warnings == []
    assert [response.request_id for response in responses] == [10, 11]
    assert [response.result for response in responses] == [{"score": 10}, {"score": 11}]


def test_coalesce_ga_fg_fused_requests_falls_back_for_bad_batch_result():
    fallback_warnings = []
    direct_calls = []

    responses = coalesce_ga_fg_fused_requests(
        [_req(20, {"a": 1}), _req(21, {"b": 2})],
        in_process_queues=True,
        execute_request=lambda req: direct_calls.append(req.request_id)
        or GpuResponse(request_id=req.request_id, success=True, result={"direct": req.request_id}),
        coalesce_fg_breakpoint_batch=lambda reqs: [
            GpuResponse(request_id=reqs[0].request_id, success=True, result=[]),
            GpuResponse(request_id=reqs[1].request_id, success=True, result=[{"score": 21}]),
        ],
        warn_fallback_fn=lambda *args, **kwargs: fallback_warnings.append((args, kwargs)),
    )

    assert direct_calls == [20]
    assert [response.request_id for response in responses] == [20, 21]
    assert responses[0].result == {"direct": 20}
    assert responses[1].result == {"score": 21}
    assert fallback_warnings[0][0][:2] == (
        "gpu_executor.ga_fg_fused_coalesce.request",
        "coalesced fused request fallback to per-request execution",
    )
