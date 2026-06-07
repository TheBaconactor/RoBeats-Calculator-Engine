from gear_optimizer.solver.gpu_executor_batching import (
    NativeGaBatchLimits,
    execute_gpu_native_ga_run_batch,
    execute_gpu_native_ga_run_chunk,
    load_native_ga_batch_limits,
    plan_native_ga_batch_chunks,
)
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType, GpuResponse


def _req(req_id: int) -> GpuRequest:
    return GpuRequest(
        request_type=GpuRequestType.GPU_NATIVE_GA_RUN,
        request_id=int(req_id),
        worker_id=1,
        payload={},
    )


def test_load_native_ga_batch_limits_are_hardwired():
    # Hardwired now (was GPU_NATIVE_GA_BATCH_COALESCE_MAX_REQS / _MAX_WORK_UNITS);
    # setting them -- including the old 0=unbounded -- is inert, and the per-dispatch
    # work-unit safety cap is never disabled.
    values = {
        "GPU_NATIVE_GA_BATCH_COALESCE_MAX_REQS": "999",
        "GPU_NATIVE_GA_BATCH_COALESCE_MAX_WORK_UNITS": "0",
    }

    limits = load_native_ga_batch_limits(env_get_fn=lambda key, default: values.get(key, default))

    assert limits.max_reqs == 2
    assert limits.max_work_units == 240000.0


def test_plan_native_ga_batch_chunks_splits_by_request_limit():
    requests = [_req(1), _req(2), _req(3), _req(4), _req(5)]

    chunks = plan_native_ga_batch_chunks(
        requests,
        limits=NativeGaBatchLimits(max_reqs=2, max_work_units=1000.0),
        estimate_work_units_fn=lambda _req: 1.0,
    )

    assert [[req.request_id for req in chunk] for chunk in chunks] == [[1, 2], [3, 4], [5]]


def test_plan_native_ga_batch_chunks_splits_by_work_units():
    requests = [_req(1), _req(2), _req(3)]
    units = {1: 4.0, 2: 5.0, 3: 4.0}

    chunks = plan_native_ga_batch_chunks(
        requests,
        limits=NativeGaBatchLimits(max_reqs=8, max_work_units=8.0),
        estimate_work_units_fn=lambda req: units[int(req.request_id)],
    )

    assert [[req.request_id for req in chunk] for chunk in chunks] == [[1], [2], [3]]


def test_plan_native_ga_batch_chunks_clamps_request_work_units_to_one():
    requests = [_req(1), _req(2), _req(3)]

    chunks = plan_native_ga_batch_chunks(
        requests,
        limits=NativeGaBatchLimits(max_reqs=8, max_work_units=2.0),
        estimate_work_units_fn=lambda _req: 0.0,
    )

    assert [[req.request_id for req in chunk] for chunk in chunks] == [[1, 2], [3]]


def test_execute_gpu_native_ga_run_chunk_aborts_remaining_requests():
    requests = [_req(1), _req(2), _req(3)]
    calls = []

    def _abort_requested() -> bool:
        return len(calls) >= 1

    responses = execute_gpu_native_ga_run_chunk(
        requests,
        abort_requested=_abort_requested,
        aborted_response=lambda req: GpuResponse(request_id=req.request_id, success=False, error="aborted"),
        execute_single=lambda req: calls.append(req.request_id)
        or GpuResponse(request_id=req.request_id, success=True),
    )

    assert calls == [1]
    assert [response.request_id for response in responses] == [1, 2, 3]
    assert responses[0].success is True
    assert [response.error for response in responses[1:]] == ["aborted", "aborted"]


def test_execute_gpu_native_ga_run_batch_uses_planned_chunks():
    requests = [_req(1), _req(2), _req(3), _req(4), _req(5)]
    chunks_seen = []

    responses = execute_gpu_native_ga_run_batch(
        requests,
        abort_requested=lambda: False,
        aborted_response=lambda req: GpuResponse(request_id=req.request_id, success=False),
        execute_single=lambda req: GpuResponse(request_id=req.request_id, success=True),
        execute_chunk=lambda chunk: chunks_seen.append([req.request_id for req in chunk])
        or [GpuResponse(request_id=req.request_id, success=True) for req in chunk],
        env_get_fn=lambda key, default: {"GPU_NATIVE_GA_BATCH_COALESCE_MAX_REQS": "2"}.get(key, default),
        estimate_work_units_fn=lambda _req: 1.0,
    )

    assert chunks_seen == [[1, 2], [3, 4], [5]]
    assert [response.request_id for response in responses] == [1, 2, 3, 4, 5]
