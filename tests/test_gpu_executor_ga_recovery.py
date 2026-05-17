import queue
from collections import deque

from gear_optimizer.solver.gpu_executor_lifecycle import prefetch_ga_recovery_requests, staged_ga_recovery_index
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType


def _request(request_type: GpuRequestType, request_id: int) -> GpuRequest:
    return GpuRequest(request_type=request_type, request_id=request_id, worker_id=1, payload={})


def test_staged_ga_recovery_index_requires_native_ga_first():
    requests = [
        _request(GpuRequestType.SOLVE_FORCE_GREATS_FINDER, 1),
        _request(GpuRequestType.GPU_NATIVE_GA_RUN, 2),
    ]

    assert staged_ga_recovery_index(requests, is_ga_recovery_request=lambda _req: True) is None


def test_staged_ga_recovery_index_returns_first_fg_recovery_after_native_ga():
    requests = [
        _request(GpuRequestType.GPU_NATIVE_GA_RUN, 1),
        _request(GpuRequestType.GPU_NATIVE_GA_RUN, 2),
        _request(GpuRequestType.SOLVE_FORCE_GREATS_FINDER, 3),
        _request(GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS, 4),
    ]

    def is_recovery(req):
        return req.request_type in {
            GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
            GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS,
        }

    assert staged_ga_recovery_index(requests, is_ga_recovery_request=is_recovery) == 2


def test_staged_ga_recovery_index_prioritizes_shutdown_after_native_ga():
    requests = [
        _request(GpuRequestType.GPU_NATIVE_GA_RUN, 1),
        _request(GpuRequestType.SHUTDOWN, 2),
        _request(GpuRequestType.SOLVE_FORCE_GREATS_FINDER, 3),
    ]

    assert staged_ga_recovery_index(requests, is_ga_recovery_request=lambda req: req.request_id == 3) == 1


def test_staged_ga_recovery_index_returns_none_without_recovery():
    requests = [
        _request(GpuRequestType.GPU_NATIVE_GA_RUN, 1),
        _request(GpuRequestType.GPU_NATIVE_GA_RUN, 2),
    ]

    assert staged_ga_recovery_index(requests, is_ga_recovery_request=lambda _req: False) is None


def test_prefetch_ga_recovery_requests_reads_until_recovery_request():
    staged = deque([_request(GpuRequestType.GPU_NATIVE_GA_RUN, 1)])
    source = deque(
        [
            _request(GpuRequestType.GPU_NATIVE_GA_RUN, 2),
            _request(GpuRequestType.SOLVE_FORCE_GREATS_FINDER, 3),
            _request(GpuRequestType.GPU_NATIVE_GA_RUN, 4),
        ]
    )

    def _pop(_timeout: float):
        if not source:
            raise queue.Empty
        return source.popleft()

    prefetch_ga_recovery_requests(
        in_process_queues=True,
        ga_owner_turn_streak=10,
        staged_requests=staged,
        deadline=100.0,
        batch_max_size=8,
        streak_cap=2,
        lookahead_limit=8,
        pop_queue_request=_pop,
        perf_counter_fn=lambda: 0.0,
        is_ga_recovery_request=lambda req: req.request_type == GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
        empty_exception=queue.Empty,
    )

    assert [req.request_id for req in staged] == [1, 2, 3]
    assert [req.request_id for req in source] == [4]


def test_prefetch_ga_recovery_requests_skips_when_recovery_already_staged():
    staged = deque(
        [
            _request(GpuRequestType.GPU_NATIVE_GA_RUN, 1),
            _request(GpuRequestType.SOLVE_FORCE_GREATS_FINDER, 2),
        ]
    )
    pop_calls = 0

    def _pop(_timeout: float):
        nonlocal pop_calls
        pop_calls += 1
        raise queue.Empty

    prefetch_ga_recovery_requests(
        in_process_queues=True,
        ga_owner_turn_streak=10,
        staged_requests=staged,
        deadline=100.0,
        batch_max_size=8,
        streak_cap=2,
        lookahead_limit=8,
        pop_queue_request=_pop,
        perf_counter_fn=lambda: 0.0,
        is_ga_recovery_request=lambda req: req.request_type == GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
        empty_exception=queue.Empty,
    )

    assert pop_calls == 0
    assert [req.request_id for req in staged] == [1, 2]
