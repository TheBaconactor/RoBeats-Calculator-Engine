import queue

from gear_optimizer.solver.gpu_service import GpuServiceClient


class _DummyExecutor:
    def __init__(self):
        self.is_running = True
        self._request_q = queue.Queue()
        self._response_q = queue.Queue()

    def register_worker(self):
        return 0, self._request_q, self._response_q

    def unregister_worker(self, _worker_id: int):
        return None


def test_fg_coalesce_timer_period_lifecycle(monkeypatch):
    calls = {"acquire": 0, "release": 0}

    def _fake_acquire() -> bool:
        calls["acquire"] += 1
        return True

    def _fake_release() -> None:
        calls["release"] += 1

    monkeypatch.setattr("gear_optimizer.solver.gpu_service._acquire_windows_timer_period_1ms", _fake_acquire)
    monkeypatch.setattr("gear_optimizer.solver.gpu_service._release_windows_timer_period_1ms", _fake_release)

    client = GpuServiceClient(executor=_DummyExecutor())
    client._fg_coalesce_enabled = True
    client._fg_coalesce_max_wait_ms = 1

    client.start(start_executor=False, in_process_queues=True)
    try:
        assert calls["acquire"] == 1
        assert client._fg_high_res_timer_enabled is True
    finally:
        client.close(timeout=0.2)

    assert calls["release"] == 1
    assert client._fg_high_res_timer_enabled is False
