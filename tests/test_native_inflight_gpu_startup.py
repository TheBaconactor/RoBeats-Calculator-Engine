from __future__ import annotations

from types import SimpleNamespace

from gear_optimizer.solver import native_inflight_lifecycle as startup


class _Executor:
    def __init__(self, *, ready: bool = True, error: str | None = None) -> None:
        self.ready = ready
        self.last_init_error = error
        self.start_calls = []
        self.wait_calls = []
        self.stop_calls = 0

    def start(self, **kwargs) -> None:
        self.start_calls.append(kwargs)

    def wait_until_ready(self, **kwargs) -> bool:
        self.wait_calls.append(kwargs)
        return self.ready

    def stop(self) -> None:
        self.stop_calls += 1


class _GpuClient:
    instances = []

    def __init__(self, executor: _Executor) -> None:
        self.executor = executor
        self.start_calls = []
        self.instances.append(self)

    def start(self, **kwargs) -> None:
        self.start_calls.append(kwargs)


def _icfg(timeout: float = 12.5):
    return SimpleNamespace(runtime=SimpleNamespace(gpu_executor_init_timeout_sec=timeout))


def test_start_native_inflight_gpu_client_starts_executor_and_client(monkeypatch):
    executor = _Executor()
    progress_events = []
    _GpuClient.instances = []

    monkeypatch.setattr(startup, "get_gpu_executor", lambda: executor)
    monkeypatch.setattr(startup, "GpuServiceClient", _GpuClient)

    result_executor, result_client = startup.start_native_inflight_gpu_client(
        _icfg(),
        progress_cb=lambda **kwargs: progress_events.append(kwargs),
    )

    assert result_executor is executor
    assert result_client is _GpuClient.instances[0]
    assert executor.start_calls == [{"in_process": True}]
    assert executor.wait_calls == [{"timeout": 12.5}]
    assert result_client.executor is executor
    assert result_client.start_calls == [{"start_executor": False}]
    assert progress_events == [
        {"completed_delta": 0, "failed_delta": 0, "record_info": {"status": "GPU init (Taichi/Vulkan)"}},
        {"completed_delta": 0, "failed_delta": 0, "record_info": {"status": "GPU warmup (Taichi JIT)"}},
    ]


def test_start_native_inflight_gpu_client_stops_executor_on_init_timeout(monkeypatch):
    executor = _Executor(ready=False, error="driver did not initialize")

    monkeypatch.setattr(startup, "get_gpu_executor", lambda: executor)
    monkeypatch.setattr(startup, "GpuServiceClient", _GpuClient)

    try:
        startup.start_native_inflight_gpu_client(_icfg(timeout=3))
    except RuntimeError as exc:
        assert "[InFlight] GPU executor Taichi init failed or timed out" in str(exc)
        assert "driver did not initialize" in str(exc)
    else:
        raise AssertionError("expected GPU startup timeout to fail")

    assert executor.start_calls == [{"in_process": True}]
    assert executor.wait_calls == [{"timeout": 3.0}]
    assert executor.stop_calls == 1
