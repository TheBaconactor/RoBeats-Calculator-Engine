import pytest

from gear_optimizer.solver.gpu_executor_lifecycle import ExecutorAbortState
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType


def _request(request_id: int = 9) -> GpuRequest:
    return GpuRequest(
        request_type=GpuRequestType.GPU_NATIVE_GA_RUN,
        request_id=int(request_id),
        worker_id=0,
        payload={},
    )


def test_executor_abort_state_tracks_reason_and_clears():
    state = ExecutorAbortState()

    assert state.requested() is False
    assert state.error_message() == "GpuExecutor aborted: abort requested"

    state.request_abort(" hotkey stop ")

    assert state.requested() is True
    assert state.error_message() == "GpuExecutor aborted: hotkey stop"

    state.clear()

    assert state.requested() is False
    assert state.error_message() == "GpuExecutor aborted: abort requested"


def test_executor_abort_state_raises_and_shapes_response():
    state = ExecutorAbortState()
    state.request_abort("")

    with pytest.raises(RuntimeError, match="GpuExecutor aborted: abort requested"):
        state.raise_if_requested()

    response = state.response(_request(44))

    assert response.request_id == 44
    assert response.success is False
    assert response.error == "GpuExecutor aborted: abort requested"
