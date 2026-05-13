from __future__ import annotations

from gear_optimizer.solver import native_inflight_shutdown as shutdown


class _FgPipeline:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def shutdown_fg(self, **kwargs) -> None:
        self.calls.append(f"fg:{kwargs}")

    def shutdown_prep(self, **kwargs) -> None:
        self.calls.append(f"fg_prep:{kwargs}")


class _ShutdownQueue:
    def __init__(self, calls: list[str], name: str, *, fail: bool = False) -> None:
        self.calls = calls
        self.name = name
        self.fail = fail

    def shutdown(self, **kwargs) -> None:
        self.calls.append(f"{self.name}:{kwargs}")
        if self.fail:
            raise RuntimeError(f"{self.name} failed")


class _DbPersistence:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def shutdown_prefetch(self, **kwargs) -> None:
        self.calls.append(f"db:{kwargs}")


class _PostSender:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def close(self, **kwargs) -> None:
        self.calls.append(f"post:{kwargs}")


class _GpuClient:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def close(self, **kwargs) -> None:
        self.calls.append(f"gpu_client:{kwargs}")


class _GpuExecutor:
    def __init__(self, calls: list[str], *, running: bool = True) -> None:
        self.calls = calls
        self.is_running = running

    def stop(self) -> None:
        self.calls.append("gpu_executor.stop")


def test_shutdown_native_inflight_resources_uses_dependency_order(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(shutdown, "inflight_shutdown_debug_enabled", lambda: False)

    shutdown.shutdown_native_inflight_resources(
        fg_pipeline=_FgPipeline(calls),
        decode_queue=_ShutdownQueue(calls, "decode"),
        db_persistence=_DbPersistence(calls),
        cpu_prewarm_queue=_ShutdownQueue(calls, "cpu_prewarm"),
        prep_queue=_ShutdownQueue(calls, "prep"),
        post_sender=_PostSender(calls),
        gpu_client=_GpuClient(calls),
        gpu_executor=_GpuExecutor(calls),
    )

    assert calls == [
        "fg:{'wait': True, 'cancel_futures': True}",
        "decode:{'wait': True, 'cancel_futures': True}",
        "db:{'wait': True, 'cancel_futures': True}",
        "fg_prep:{'wait': True, 'cancel_futures': True}",
        "cpu_prewarm:{'wait': True, 'cancel_futures': True}",
        "prep:{'wait': True, 'cancel_futures': True}",
        "post:{'timeout': 10.0}",
        "gpu_client:{'timeout': 2.0}",
        "gpu_executor.stop",
    ]


def test_shutdown_native_inflight_resources_continues_after_shutdown_failure(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(shutdown, "inflight_shutdown_debug_enabled", lambda: False)

    shutdown.shutdown_native_inflight_resources(
        fg_pipeline=_FgPipeline(calls),
        decode_queue=_ShutdownQueue(calls, "decode", fail=True),
        db_persistence=_DbPersistence(calls),
        cpu_prewarm_queue=_ShutdownQueue(calls, "cpu_prewarm"),
        prep_queue=_ShutdownQueue(calls, "prep"),
        post_sender=None,
        gpu_client=_GpuClient(calls),
        gpu_executor=_GpuExecutor(calls, running=False),
    )

    assert calls == [
        "fg:{'wait': True, 'cancel_futures': True}",
        "decode:{'wait': True, 'cancel_futures': True}",
        "db:{'wait': True, 'cancel_futures': True}",
        "fg_prep:{'wait': True, 'cancel_futures': True}",
        "cpu_prewarm:{'wait': True, 'cancel_futures': True}",
        "prep:{'wait': True, 'cancel_futures': True}",
        "gpu_client:{'timeout': 2.0}",
    ]
