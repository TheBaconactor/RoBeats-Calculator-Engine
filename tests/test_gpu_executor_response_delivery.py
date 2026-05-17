import queue

from gear_optimizer.solver.gpu_executor_dispatch import ResponseDeliveryTracker, order_responses_for_requests
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType, GpuResponse


def _request(worker_id: int = 3, request_id: int = 9) -> GpuRequest:
    return GpuRequest(
        request_type=GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
        request_id=request_id,
        worker_id=worker_id,
        payload={},
    )


def test_response_delivery_tracker_puts_response_without_failure():
    tracker = ResponseDeliveryTracker()
    response_q: queue.Queue = queue.Queue()
    response = GpuResponse(request_id=9, success=True, result="ok")

    assert tracker.try_put({3: response_q}, _request(), response) is True

    assert response_q.get_nowait() is response
    assert tracker.failures_total == 0


def test_response_delivery_tracker_records_full_queue_failure():
    tracker = ResponseDeliveryTracker()
    response_q: queue.Queue = queue.Queue(maxsize=1)
    response_q.put_nowait(object())

    assert tracker.try_put({3: response_q}, _request(), GpuResponse(request_id=9, success=True)) is False

    assert tracker.failures_total == 1
    assert tracker.failures_by_worker[3] == 1


def test_response_delivery_tracker_reset_clears_failures():
    tracker = ResponseDeliveryTracker()
    response_q: queue.Queue = queue.Queue(maxsize=1)
    response_q.put_nowait(object())
    tracker.try_put({3: response_q}, _request(), GpuResponse(request_id=9, success=True))

    tracker.reset()

    assert tracker.failures_total == 0
    assert dict(tracker.failures_by_worker) == {}


def test_order_responses_for_requests_restores_request_order_and_skips_bad_entries():
    requests = [
        _request(request_id=1),
        _request(request_id=2),
        _request(request_id=3),
    ]
    response_2 = GpuResponse(request_id=2, success=True, result="two")
    response_1 = GpuResponse(request_id=1, success=True, result="one")

    ordered = order_responses_for_requests(
        requests,
        [
            response_2,
            None,
            object(),
            response_1,
        ],
    )

    assert ordered == [response_1, response_2, None]
