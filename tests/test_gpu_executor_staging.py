from collections import deque

from gear_optimizer.solver.gpu_executor_staging import (
    pop_staged_request,
    stage_request,
    stamp_request_dequeue,
)
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType


def _request(request_id: int, *, dequeue_perf_ns: int = 0) -> GpuRequest:
    return GpuRequest(
        request_type=GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
        request_id=request_id,
        worker_id=1,
        payload={},
        dequeue_perf_ns=dequeue_perf_ns,
    )


def test_stamp_request_dequeue_sets_missing_timestamp_once():
    req = _request(101)

    stamped = stamp_request_dequeue(req, perf_counter_ns_fn=lambda: 12345)
    stamped_again = stamp_request_dequeue(req, perf_counter_ns_fn=lambda: 67890)

    assert stamped is req
    assert stamped_again is req
    assert req.dequeue_perf_ns == 12345


def test_stage_request_preserves_front_and_back_order():
    staged = deque()
    first = _request(1)
    second = _request(2)
    front = _request(3)

    stage_request(staged, first, stamp_fn=lambda req: req)
    stage_request(staged, second, stamp_fn=lambda req: req)
    stage_request(staged, front, front=True, stamp_fn=lambda req: req)

    assert [req.request_id for req in staged] == [3, 1, 2]


def test_pop_staged_request_removes_index_and_restores_order():
    staged = deque([_request(1), _request(2), _request(3), _request(4)])

    popped = pop_staged_request(staged, index=2)

    assert popped.request_id == 3
    assert [req.request_id for req in staged] == [1, 2, 4]


def test_pop_staged_request_zero_index_pops_front():
    staged = deque([_request(1), _request(2)])

    popped = pop_staged_request(staged)

    assert popped.request_id == 1
    assert [req.request_id for req in staged] == [2]
