from gear_optimizer.solver.gpu_executor_dispatch import execute_request_from_dispatch, plan_execution_units
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType, GpuResponse


def _request(request_type: GpuRequestType, request_id: int = 1) -> GpuRequest:
    return GpuRequest(request_type=request_type, request_id=request_id, worker_id=0, payload={})


def test_execute_request_from_dispatch_returns_shutdown_success():
    response = execute_request_from_dispatch(_request(GpuRequestType.SHUTDOWN, 10), dispatch={})

    assert response == GpuResponse(request_id=10, success=True, result=None)


def test_execute_request_from_dispatch_routes_known_handler():
    seen = []

    def handler(request):
        seen.append(request.request_id)
        return GpuResponse(request_id=request.request_id, success=True, result="ok")

    response = execute_request_from_dispatch(
        _request(GpuRequestType.LOAD_REF_ARRAYS, 11),
        dispatch={GpuRequestType.LOAD_REF_ARRAYS: handler},
    )

    assert response.success is True
    assert response.result == "ok"
    assert seen == [11]


def test_execute_request_from_dispatch_reports_unsupported_type():
    response = execute_request_from_dispatch(_request(GpuRequestType.LOAD_REF_ARRAYS, 12), dispatch={})

    assert response.success is False
    assert response.request_id == 12
    assert "Unsupported GPU request type" in str(response.error)


def test_execute_request_from_dispatch_catches_handler_exception():
    def handler(_request):
        raise RuntimeError("boom")

    response = execute_request_from_dispatch(
        _request(GpuRequestType.LOAD_REF_ARRAYS, 13),
        dispatch={GpuRequestType.LOAD_REF_ARRAYS: handler},
    )

    assert response.success is False
    assert response.request_id == 13
    assert "RuntimeError: boom" in str(response.error)


def test_plan_execution_units_groups_only_adjacent_matching_grouped_types():
    batch = [
        _request(GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY, 1),
        _request(GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY, 2),
        _request(GpuRequestType.LOAD_REF_ARRAYS, 3),
        _request(GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY, 4),
        _request(GpuRequestType.GPU_NATIVE_GA_RUN, 5),
        _request(GpuRequestType.GPU_NATIVE_GA_RUN, 6),
    ]

    units = plan_execution_units(
        batch,
        grouped_request_types={
            GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
            GpuRequestType.GPU_NATIVE_GA_RUN,
        },
    )

    assert [(unit.grouped, unit.request_type, [req.request_id for req in unit.requests]) for unit in units] == [
        (True, GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY, [1, 2]),
        (False, GpuRequestType.LOAD_REF_ARRAYS, [3]),
        (True, GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY, [4]),
        (True, GpuRequestType.GPU_NATIVE_GA_RUN, [5, 6]),
    ]


def test_plan_execution_units_keeps_ungrouped_requests_single_even_when_adjacent():
    batch = [
        _request(GpuRequestType.LOAD_REF_ARRAYS, 1),
        _request(GpuRequestType.LOAD_REF_ARRAYS, 2),
    ]

    units = plan_execution_units(batch, grouped_request_types={GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY})

    assert [(unit.grouped, [req.request_id for req in unit.requests]) for unit in units] == [
        (False, [1]),
        (False, [2]),
    ]
