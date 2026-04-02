from gear_optimizer.helpers.song_helpers.force_greats.gpu_dispatch_async import (
    plan_fg_async_threshold_flush,
    resolve_fg_async_batching_settings,
)


class _FakeExecutor:
    def __init__(self, *, in_process: bool) -> None:
        self._in_process_queues = bool(in_process)


class _FakeGpuClient:
    def __init__(self, *, in_process: bool) -> None:
        self.executor = _FakeExecutor(in_process=in_process)


def test_resolve_fg_async_batching_settings_defaults_to_512_tasks_in_process(monkeypatch):
    monkeypatch.delenv("FG_ASYNC_TASKS_PER_REQUEST", raising=False)
    monkeypatch.delenv("FG_ASYNC_MAX_INFLIGHT", raising=False)

    settings = resolve_fg_async_batching_settings(
        gpu_client=_FakeGpuClient(in_process=True),
        song_slot=1,
        perf=False,
    )

    assert settings.in_process is True
    assert settings.max_inflight == 32
    assert settings.tasks_per_request == 512
    assert settings.enforce_single_request is False


def test_resolve_fg_async_batching_settings_keeps_ipc_default_at_256(monkeypatch):
    monkeypatch.delenv("FG_ASYNC_TASKS_PER_REQUEST", raising=False)
    monkeypatch.delenv("FG_ASYNC_MAX_INFLIGHT", raising=False)

    settings = resolve_fg_async_batching_settings(
        gpu_client=_FakeGpuClient(in_process=False),
        song_slot=1,
        perf=False,
    )

    assert settings.in_process is False
    assert settings.max_inflight == 32
    assert settings.tasks_per_request == 256
    assert settings.enforce_single_request is False


def test_plan_fg_async_threshold_flush_keeps_pending_tasks_below_threshold():
    plan = plan_fg_async_threshold_flush(pending_tasks=3, tasks_per_request=4)

    assert plan.submit_count == 0
    assert plan.keep_queued_count == 3


def test_plan_fg_async_threshold_flush_full_flushes_exact_boundary():
    plan = plan_fg_async_threshold_flush(pending_tasks=512, tasks_per_request=512)

    assert plan.submit_count == 512
    assert plan.keep_queued_count == 0


def test_plan_fg_async_threshold_flush_full_flushes_above_threshold():
    plan = plan_fg_async_threshold_flush(pending_tasks=513, tasks_per_request=512)

    assert plan.submit_count == 513
    assert plan.keep_queued_count == 0
