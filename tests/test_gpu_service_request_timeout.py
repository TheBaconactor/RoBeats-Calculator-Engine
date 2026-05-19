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
    monkeypatch.setenv("GPU_SERVICE_REQUEST_TIMEOUT_SEC", "0.1")
    monkeypatch.setenv("GPU_SERVICE_TIMEOUT_FATAL", "0")

    executor = _DummyExecutor()
    client = GpuServiceClient(executor=executor)
    client.start(start_executor=False, in_process_queues=True)

    try:
        job = client.submit(GpuRequestType.GPU_NATIVE_GA_RUN, {"song": "stuck"})
        req = executor._request_q.get(timeout=1.0)
        assert req.request_type == GpuRequestType.GPU_NATIVE_GA_RUN

        with pytest.raises(GpuServiceTimeoutError, match="timed out"):
            job.future.result(timeout=1.0)
    finally:
        client.close(timeout=0.5)


def test_gpu_service_enables_default_timeouts_for_service_mode_on_windows(monkeypatch):
    monkeypatch.delenv("GPU_SERVICE_REQUEST_TIMEOUT_SEC", raising=False)
    monkeypatch.delenv("GPU_SERVICE_TIMEOUT_FATAL", raising=False)
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", "1")

    client = GpuServiceClient(executor=_DummyExecutor())

    assert client._request_timeout_default_enabled is True
    assert client._timeout_fatal is True
    assert client._request_timeout_sec_for(GpuRequestType.GPU_NATIVE_GA_RUN) == pytest.approx(240.0)
