import queue
from concurrent.futures import Future

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


def test_fg_coalesce_loop_uses_sub_ms_remaining_window(monkeypatch):
    client = GpuServiceClient(executor=_DummyExecutor())
    client._running = True
    client._in_process_queues = True
    client._fg_coalesce_enabled = True
    client._fg_coalesce_max_wait_ms = 1
    client._fg_coalesce_payloads = [{"payload": 1}]
    client._fg_coalesce_slices = [(Future(), 0, 1, 0.0)]
    client._fg_coalesce_first_ts = 0.0

    waits: list[float] = []

    class _RecordingEvent:
        def wait(self, timeout=None):
            waits.append(float(timeout))
            client._running = False
            return False

        def clear(self):
            return None

    client._fg_coalesce_event = _RecordingEvent()

    monkeypatch.setattr("gear_optimizer.solver.gpu_service.time.perf_counter", lambda: 0.00095)

    client._fg_coalesce_loop()

    assert len(waits) == 1
    assert 0.0 <= waits[0] < 0.001
