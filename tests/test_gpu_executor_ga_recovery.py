from gear_optimizer.solver.gpu_executor_ga_recovery import staged_ga_recovery_index
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
