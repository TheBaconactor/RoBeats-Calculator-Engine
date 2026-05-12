from collections import deque

from gear_optimizer.solver.gpu_executor import GpuExecutor
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


def _executor_request(request_id: int, request_type: GpuRequestType) -> GpuRequest:
    return GpuRequest(
        request_type=request_type,
        request_id=request_id,
        worker_id=1,
        payload={},
    )


def _fresh_executor() -> GpuExecutor:
    GpuExecutor._instance = None
    return GpuExecutor()


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


def test_gpu_executor_pop_seed_request_pops_recovery_request_from_staged_queue():
    ex = _fresh_executor()
    ex._in_process_queues = True
    ex._ga_owner_turn_streak = 1
    ex._staged_requests = deque(
        [
            _executor_request(1, GpuRequestType.GPU_NATIVE_GA_RUN),
            _executor_request(2, GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS),
        ]
    )

    popped = ex._pop_seed_request(timeout=0.0, deadline=0.0, batch_max_size=8)

    assert popped.request_id == 2
    assert [req.request_id for req in ex._staged_requests] == [1]
