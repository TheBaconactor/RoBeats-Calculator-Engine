from __future__ import annotations

from collections import deque
from queue import Queue
import threading
from time import perf_counter

from gear_optimizer.solver.gpu_executor import GpuExecutor
from gear_optimizer.solver.gpu_executor_lifecycle import staged_fg_continuation_index
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType


def _request(request_type: GpuRequestType, request_id: int) -> GpuRequest:
    return GpuRequest(
        request_type=request_type,
        request_id=int(request_id),
        worker_id=0,
        payload={},
    )


def test_staged_fg_continuation_can_precede_staged_ga_run():
    staged = [
        _request(GpuRequestType.GPU_NATIVE_GA_RUN, 1),
        _request(GpuRequestType.FORCE_GREATS_RESPONSE_FRONTIER_SCORE_BATCH, 2),
    ]

    assert staged_fg_continuation_index(staged) == 1


def test_staged_fg_continuation_does_not_cross_required_ref_load_boundary():
    staged = [
        _request(GpuRequestType.GPU_NATIVE_GA_RUN, 1),
        _request(GpuRequestType.LOAD_REF_ARRAYS, 2),
        _request(GpuRequestType.FORCE_GREATS_RESPONSE_FRONTIER_SCORE_BATCH, 3),
    ]

    assert staged_fg_continuation_index(staged) is None


def test_pop_seed_request_runs_ready_fg_continuation_before_ga():
    GpuExecutor._instance = None
    executor = GpuExecutor()
    executor._in_process_queues = True
    executor._request_queue = Queue()
    executor._staged_requests = deque()
    executor._request_queue.put(_request(GpuRequestType.GPU_NATIVE_GA_RUN, 1))
    executor._request_queue.put(_request(GpuRequestType.FORCE_GREATS_RESPONSE_FRONTIER_SCORE_BATCH, 2))

    selected = executor._pop_seed_request(
        timeout=0.0,
        deadline=perf_counter() + 1.0,
        batch_max_size=8,
    )

    assert selected.request_type == GpuRequestType.FORCE_GREATS_RESPONSE_FRONTIER_SCORE_BATCH
    assert selected.request_id == 2
    assert [request.request_id for request in executor._staged_requests] == [1]
    GpuExecutor._instance = None


def test_gather_batch_keeps_adjacent_ga_requests_in_one_owner_turn():
    GpuExecutor._instance = None
    executor = GpuExecutor()
    executor._in_process_queues = True
    executor._request_queue = Queue()
    executor._staged_requests = deque()
    executor._request_queue.put(_request(GpuRequestType.GPU_NATIVE_GA_RUN, 1))
    executor._request_queue.put(_request(GpuRequestType.GPU_NATIVE_GA_RUN, 2))

    batch = executor._gather_batch(max_wait_ms=10, max_batch_size=8)

    assert [request.request_id for request in batch] == [1, 2]
    GpuExecutor._instance = None


def test_ready_fg_continuation_can_cut_a_staged_ga_burst():
    GpuExecutor._instance = None
    executor = GpuExecutor()
    executor._in_process_queues = True
    executor._request_queue = Queue()
    executor._staged_requests = deque([_request(GpuRequestType.GPU_NATIVE_GA_RUN, 1)])
    executor._request_queue.put(_request(GpuRequestType.GPU_NATIVE_GA_RUN, 2))
    executor._request_queue.put(_request(GpuRequestType.FORCE_GREATS_RESPONSE_FRONTIER_SCORE_BATCH, 3))

    selected = executor._pop_ready_fg_continuation_nowait(batch_max_size=8)

    assert selected.request_type == GpuRequestType.FORCE_GREATS_RESPONSE_FRONTIER_SCORE_BATCH
    assert selected.request_id == 3
    assert [request.request_id for request in executor._staged_requests] == [1, 2]
    GpuExecutor._instance = None


def test_ready_fg_continuation_does_not_cross_ref_load_boundary():
    GpuExecutor._instance = None
    executor = GpuExecutor()
    executor._in_process_queues = True
    executor._request_queue = Queue()
    executor._staged_requests = deque([_request(GpuRequestType.GPU_NATIVE_GA_RUN, 1)])
    executor._request_queue.put(_request(GpuRequestType.LOAD_REF_ARRAYS, 2))
    executor._request_queue.put(_request(GpuRequestType.FORCE_GREATS_RESPONSE_FRONTIER_SCORE_BATCH, 3))

    selected = executor._pop_ready_fg_continuation_nowait(batch_max_size=8)

    assert selected is None
    assert [request.request_id for request in executor._staged_requests] == [1, 2]
    GpuExecutor._instance = None


def test_late_fg_continuation_gets_owner_grace_before_next_ga():
    GpuExecutor._instance = None
    executor = GpuExecutor()
    executor._in_process_queues = True
    executor._request_queue = Queue()
    executor._staged_requests = deque([_request(GpuRequestType.GPU_NATIVE_GA_RUN, 1)])

    timer = threading.Timer(
        0.01,
        lambda: executor._request_queue.put(
            _request(GpuRequestType.FORCE_GREATS_RESPONSE_FRONTIER_SCORE_BATCH, 2)
        ),
    )
    timer.start()
    try:
        selected = executor._pop_ready_fg_continuation(batch_max_size=8, grace_s=0.25)
    finally:
        timer.cancel()

    assert selected.request_type == GpuRequestType.FORCE_GREATS_RESPONSE_FRONTIER_SCORE_BATCH
    assert selected.request_id == 2
    assert [request.request_id for request in executor._staged_requests] == [1]
    GpuExecutor._instance = None


def test_late_fg_continuation_grace_keeps_ref_load_boundary():
    GpuExecutor._instance = None
    executor = GpuExecutor()
    executor._in_process_queues = True
    executor._request_queue = Queue()
    executor._staged_requests = deque([_request(GpuRequestType.GPU_NATIVE_GA_RUN, 1)])
    executor._request_queue.put(_request(GpuRequestType.LOAD_REF_ARRAYS, 2))
    executor._request_queue.put(_request(GpuRequestType.FORCE_GREATS_RESPONSE_FRONTIER_SCORE_BATCH, 3))

    selected = executor._pop_ready_fg_continuation(batch_max_size=8, grace_s=0.25)

    assert selected is None
    assert [request.request_id for request in executor._staged_requests] == [1, 2]
    GpuExecutor._instance = None
