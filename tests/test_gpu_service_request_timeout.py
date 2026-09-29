import queue

import pytest

from gear_optimizer.solver.gpu_executor_types import GpuRequestType
from gear_optimizer.solver.gpu_service import GpuServiceClient, GpuServiceTimeoutError


class _DummyExecutor:
    def __init__(self):
        self.is_running = True
        self._request_q = queue.Queue()
        self._response_q = queue.Queue()

    def register_worker(self):
        return 0, self._request_q, self._response_q

    def unregister_worker(self, _worker_id: int):
        return None


def test_gpu_service_times_out_stuck_request(monkeypatch):
    executor = _DummyExecutor()
    client = GpuServiceClient(executor=executor)
    monkeypatch.setattr(client, "_request_timeout_sec_for", lambda _request_type: 0.1)
    monkeypatch.setattr(client, "_trigger_timeout_abort", lambda _message: None)
    client.start(start_executor=False, in_process_queues=True)

    try:
        job = client.submit(GpuRequestType.GPU_NATIVE_GA_RUN, {"song": "stuck"})
        req = executor._request_q.get(timeout=1.0)
        assert req.request_type == GpuRequestType.GPU_NATIVE_GA_RUN

        with pytest.raises(GpuServiceTimeoutError, match="timed out"):
            job.future.result(timeout=1.0)
    finally:
        client.close(timeout=0.5)


def test_gpu_service_request_timeouts_follow_service_mode(monkeypatch):
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", "1")
    client = GpuServiceClient(executor=_DummyExecutor())
    assert client._request_timeouts_enabled is True
    assert client._request_timeout_sec_for(GpuRequestType.GPU_NATIVE_GA_RUN) == pytest.approx(240.0)

    monkeypatch.delenv("ROBEATSMETA_OPTIMIZER_SERVICE_MODE")
    standalone = GpuServiceClient(executor=_DummyExecutor())
    assert standalone._request_timeouts_enabled is False
    assert standalone._request_timeout_sec_for(GpuRequestType.GPU_NATIVE_GA_RUN) == 0.0
