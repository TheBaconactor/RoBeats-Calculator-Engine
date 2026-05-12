import queue
import os
from types import SimpleNamespace

import pytest

from gear_optimizer.solver.gpu_executor import (
    GpuExecutor,
    GpuRequest,
    GpuRequestType,
)
from gear_optimizer.solver.gpu_executor_batching import (
    InProcessCoalesceSettings,
    batch_contains_fg_burst_work,
    effective_owner_batch_max,
    extend_inprocess_after_first_deadline,
    ga_recovery_lookahead_limit,
    ga_recovery_streak_cap,
    load_inprocess_coalesce_settings,
    load_loop_batch_settings,
    next_fg_burst_until,
    plan_loop_batch,
    select_inprocess_batch_timeout,
)


@pytest.fixture(autouse=True)
def _fresh_gpu_executor_singleton():
    GpuExecutor._instance = None
    yield
    GpuExecutor._instance = None


def test_effective_owner_batch_max_limits_inproc_default_breadth() -> None:
    assert effective_owner_batch_max(8, in_process_queues=True, batch_max_overridden=False) == 24
    assert effective_owner_batch_max(24, in_process_queues=True, batch_max_overridden=False) == 24
    assert effective_owner_batch_max(32, in_process_queues=True, batch_max_overridden=False) == 32
    assert effective_owner_batch_max(16, in_process_queues=True, batch_max_overridden=True) == 16
    assert effective_owner_batch_max(8, in_process_queues=False, batch_max_overridden=False) == 8


def test_inprocess_coalesce_settings_default_to_idle_safe_values() -> None:
    env: dict[str, str] = {}

    settings = load_inprocess_coalesce_settings(
        max_wait_ms=7,
        in_process_queues=True,
        env_get=lambda name, default=None: env.get(name, default),
        env_flag_fn=lambda name, default: str(env.get(name, default)).lower() in {"1", "true", "yes", "on"},
    )

    assert settings.enabled is True
    assert settings.idle_wait_s == 0.1
    assert settings.recent_idle_wait_s == 0.01
    assert settings.recent_idle_grace_s == 0.25
    assert settings.yields_left == 7
    assert settings.after_first_ms == 2


def test_inprocess_coalesce_settings_clamp_env_values() -> None:
    env = {
        "GPU_EXECUTOR_INPROC_COALESCE": "0",
        "GPU_EXECUTOR_INPROC_IDLE_WAIT_MS": "2000",
        "GPU_EXECUTOR_INPROC_IDLE_RECENT_WAIT_MS": "5000",
        "GPU_EXECUTOR_INPROC_IDLE_RECENT_GRACE_MS": "9000",
        "GPU_EXECUTOR_INPROC_COALESCE_YIELD_ROUNDS": "999",
        "GPU_EXECUTOR_INPROC_COALESCE_AFTER_FIRST_MS": "-5",
    }

    settings = load_inprocess_coalesce_settings(
        max_wait_ms=9,
        in_process_queues=True,
        env_get=lambda name, default=None: env.get(name, default),
        env_flag_fn=lambda name, default: str(env.get(name, default)).lower() in {"1", "true", "yes", "on"},
    )

    assert settings.enabled is False
    assert settings.idle_wait_s == 1.0
    assert settings.recent_idle_wait_s == 1.0
    assert settings.recent_idle_grace_s == 5.0
    assert settings.yields_left == 256
    assert settings.after_first_ms == 0


def test_loop_batch_settings_preserve_env_override_flags() -> None:
    env = {
        "GPU_EXECUTOR_BATCH_WAIT_MS": "12",
        "GPU_EXECUTOR_MAX_BATCH": "32",
        "GPU_EXECUTOR_FG_BURST_WINDOW_MS": "9",
        "GPU_EXECUTOR_FG_BURST_BATCH_WAIT_MS": "99",
    }

    settings = load_loop_batch_settings(
        env_config=SimpleNamespace(gpu_executor_batch_wait_ms=10, gpu_executor_max_batch=8),
        env_get=lambda name: env.get(name),
    )

    assert settings.wait_ms == 12
    assert settings.max_batch == 32
    assert settings.wait_overridden is True
    assert settings.max_overridden is True
    assert settings.fg_burst_window_ms == 9
    assert settings.fg_burst_wait_ms == 10


def test_loop_batch_settings_ignore_invalid_override_values() -> None:
    env = {
        "GPU_EXECUTOR_BATCH_WAIT_MS": "bad",
        "GPU_EXECUTOR_MAX_BATCH": "also-bad",
        "GPU_EXECUTOR_FG_BURST_WINDOW_MS": "-3",
        "GPU_EXECUTOR_FG_BURST_BATCH_WAIT_MS": "-4",
    }

    settings = load_loop_batch_settings(
        env_config=SimpleNamespace(gpu_executor_batch_wait_ms=11, gpu_executor_max_batch=7),
        env_get=lambda name: env.get(name),
    )

    assert settings.wait_ms == 11
    assert settings.max_batch == 7
    assert settings.wait_overridden is False
    assert settings.max_overridden is False
    assert settings.fg_burst_window_ms == 0
    assert settings.fg_burst_wait_ms == 0


def test_plan_loop_batch_applies_inproc_defaults_and_fg_burst_wait() -> None:
    settings = load_loop_batch_settings(
        env_config=SimpleNamespace(gpu_executor_batch_wait_ms=10, gpu_executor_max_batch=8),
        env_get=lambda _name: None,
    )

    plan = plan_loop_batch(
        settings,
        in_process_queues=True,
        queue_depth_hint=6,
        fg_burst_active=True,
    )

    assert plan.wait_ms == 2
    assert plan.max_batch == 24
    assert plan.mode == "fg_burst"
    assert plan.queue_depth_hint == 6
    assert plan.pressure_hint == 0.25


def test_plan_loop_batch_preserves_overridden_wait_and_zeros_under_pressure() -> None:
    settings = load_loop_batch_settings(
        env_config=SimpleNamespace(gpu_executor_batch_wait_ms=10, gpu_executor_max_batch=8),
        env_get=lambda name: {"GPU_EXECUTOR_BATCH_WAIT_MS": "12", "GPU_EXECUTOR_MAX_BATCH": "4"}.get(name),
    )

    plan = plan_loop_batch(
        settings,
        in_process_queues=True,
        queue_depth_hint=4,
        fg_burst_active=False,
    )

    assert plan.wait_ms == 0
    assert plan.max_batch == 4
    assert plan.mode == "inproc"
    assert plan.pressure_hint == 1.0


def test_batch_contains_fg_burst_work_ignores_shutdown_and_detects_fused_fg() -> None:
    batch = [
        GpuRequest(
            request_type=GpuRequestType.SHUTDOWN,
            request_id=-1,
            worker_id=-1,
            payload={},
        ),
        GpuRequest(
            request_type=GpuRequestType.LOAD_REF_ARRAYS,
            request_id=1,
            worker_id=1,
            payload={},
        ),
    ]

    assert batch_contains_fg_burst_work(batch) is False

    batch.append(
        GpuRequest(
            request_type=GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS,
            request_id=2,
            worker_id=1,
            payload={},
        )
    )

    assert batch_contains_fg_burst_work(batch) is True


def test_next_fg_burst_until_extends_only_for_inproc_fg_work() -> None:
    assert (
        next_fg_burst_until(
            10.0,
            saw_fg_work=True,
            in_process_queues=True,
            window_ms=6,
            now_s=11.0,
        )
        == pytest.approx(11.006)
    )
    assert (
        next_fg_burst_until(
            10.0,
            saw_fg_work=True,
            in_process_queues=False,
            window_ms=6,
            now_s=11.0,
        )
        == 10.0
    )
    assert (
        next_fg_burst_until(
            10.0,
            saw_fg_work=False,
            in_process_queues=True,
            window_ms=6,
            now_s=11.0,
        )
        == 10.0
    )
    assert (
        next_fg_burst_until(
            12.0,
            saw_fg_work=True,
            in_process_queues=True,
            window_ms=6,
            now_s=11.0,
        )
        == 12.0
    )


def test_ga_recovery_settings_use_defaults_and_clamps() -> None:
    empty_env: dict[str, str] = {}

    assert ga_recovery_streak_cap(env_get=lambda name, default=None: empty_env.get(name, default)) == 1
    assert ga_recovery_lookahead_limit(batch_max_size=3, env_get=lambda name, default=None: empty_env.get(name, default)) == 12
    assert ga_recovery_lookahead_limit(batch_max_size=99, env_get=lambda name, default=None: empty_env.get(name, default)) == 64

    env = {
        "GPU_EXECUTOR_GA_RECOVERY_STREAK_MAX": "999",
        "GPU_EXECUTOR_GA_RECOVERY_LOOKAHEAD_MAX_REQS": "999",
    }

    def env_get(name, default=None):
        return env.get(name, default)

    assert ga_recovery_streak_cap(env_get=env_get) == 128
    assert ga_recovery_lookahead_limit(batch_max_size=1, env_get=env_get) == 256


def test_select_inprocess_batch_timeout_uses_recent_idle_window() -> None:
    settings = InProcessCoalesceSettings(
        enabled=True,
        idle_wait_s=0.1,
        recent_idle_wait_s=0.01,
        recent_idle_grace_s=0.25,
        yields_left=8,
        after_first_ms=2,
    )

    timeout = select_inprocess_batch_timeout(
        [],
        max_wait_ms=5,
        remaining_s=0.005,
        settings=settings,
        last_work_end_ts=10.0,
        now_s=10.1,
        coalescable_request_types={GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY},
    )

    assert timeout == 0.01


def test_select_inprocess_batch_timeout_blocks_non_coalescable_followup() -> None:
    settings = InProcessCoalesceSettings(
        enabled=True,
        idle_wait_s=0.1,
        recent_idle_wait_s=0.01,
        recent_idle_grace_s=0.25,
        yields_left=8,
        after_first_ms=2,
    )
    batch = [
        GpuRequest(
            request_type=GpuRequestType.GPU_NATIVE_GA_RUN,
            request_id=901,
            worker_id=1,
            payload={},
        )
    ]

    timeout = select_inprocess_batch_timeout(
        batch,
        max_wait_ms=5,
        remaining_s=0.004,
        settings=settings,
        last_work_end_ts=None,
        now_s=None,
        coalescable_request_types={GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY},
    )

    assert timeout == 0.0


def test_select_inprocess_batch_timeout_allows_coalescable_followup() -> None:
    settings = InProcessCoalesceSettings(
        enabled=True,
        idle_wait_s=0.1,
        recent_idle_wait_s=0.01,
        recent_idle_grace_s=0.25,
        yields_left=8,
        after_first_ms=2,
    )
    batch = [
        GpuRequest(
            request_type=GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
            request_id=902,
            worker_id=1,
            payload={},
        )
    ]

    timeout = select_inprocess_batch_timeout(
        batch,
        max_wait_ms=5,
        remaining_s=0.004,
        settings=settings,
        last_work_end_ts=None,
        now_s=None,
        coalescable_request_types={GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY},
    )

    assert timeout == 0.004


def test_extend_inprocess_after_first_deadline_extends_for_first_coalescable_request() -> None:
    settings = InProcessCoalesceSettings(
        enabled=True,
        idle_wait_s=0.1,
        recent_idle_wait_s=0.01,
        recent_idle_grace_s=0.25,
        yields_left=8,
        after_first_ms=2,
    )

    deadline = extend_inprocess_after_first_deadline(
        10.0,
        in_process_queues=True,
        settings=settings,
        batch_size=1,
        request_type=GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
        coalescable_request_types={GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY},
        now_fn=lambda: 10.005,
    )

    assert deadline == pytest.approx(10.007)


def test_extend_inprocess_after_first_deadline_leaves_non_coalescable_unchanged() -> None:
    settings = InProcessCoalesceSettings(
        enabled=True,
        idle_wait_s=0.1,
        recent_idle_wait_s=0.01,
        recent_idle_grace_s=0.25,
        yields_left=8,
        after_first_ms=2,
    )

    deadline = extend_inprocess_after_first_deadline(
        10.0,
        in_process_queues=True,
        settings=settings,
        batch_size=1,
        request_type=GpuRequestType.GPU_NATIVE_GA_RUN,
        coalescable_request_types={GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY},
        now_fn=lambda: 10.005,
    )

    assert deadline == 10.0


def test_gather_batch_inproc_uses_idle_wait_for_first_item(monkeypatch):
    import gear_optimizer.solver.gpu_executor as gpu_executor_mod

    class _RecordingQueue:
        def __init__(self, first_req: GpuRequest):
            self._first_req = first_req
            self._returned_first = False
            self.timeouts: list[float] = []

        def get(self, timeout=None):
            self.timeouts.append(float(timeout))
            if not self._returned_first:
                self._returned_first = True
                return self._first_req
            raise queue.Empty()

    req = GpuRequest(
        request_type=GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
        request_id=101,
        worker_id=1,
        payload={},
    )

    ex = GpuExecutor()
    ex._in_process_queues = True
    ex._request_queue = _RecordingQueue(req)

    monkeypatch.setenv("GPU_EXECUTOR_INPROC_IDLE_WAIT_MS", "100")
    monkeypatch.setenv("GPU_EXECUTOR_INPROC_COALESCE", "1")
    monkeypatch.setenv("GPU_EXECUTOR_INPROC_COALESCE_AFTER_FIRST_MS", "0")

    perf_values = iter((0.0, 0.0, 0.00095))

    def _fake_perf_counter():
        try:
            return next(perf_values)
        except StopIteration:
            return 0.00095

    monkeypatch.setattr(gpu_executor_mod, "perf_counter", _fake_perf_counter)

    batch = ex._gather_batch(max_wait_ms=1, max_batch_size=8)
    assert len(batch) == 1
    assert len(ex._request_queue.timeouts) >= 2
    assert abs(ex._request_queue.timeouts[0] - 0.1) < 1e-6
    assert 0.0 <= ex._request_queue.timeouts[1] < 0.001


def test_gather_batch_inproc_short_wait_uses_nonblocking_poll_after_first(monkeypatch):
    class _HybridQueue:
        def __init__(self, first_req: GpuRequest):
            self._first_req = first_req
            self._returned = False
            self.get_calls: list[float] = []
            self.get_nowait_calls = 0

        def get(self, timeout=None):
            self.get_calls.append(float(timeout))
            if not self._returned:
                self._returned = True
                return self._first_req
            raise queue.Empty()

        def get_nowait(self):
            self.get_nowait_calls += 1
            raise queue.Empty()

    req = GpuRequest(
        request_type=GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
        request_id=202,
        worker_id=1,
        payload={},
    )

    ex = GpuExecutor()
    ex._in_process_queues = True
    ex._request_queue = _HybridQueue(req)
    ex._short_wait_spin_sec = 0.01

    monkeypatch.setenv("GPU_EXECUTOR_INPROC_IDLE_WAIT_MS", "100")
    monkeypatch.setenv("GPU_EXECUTOR_INPROC_COALESCE", "1")
    monkeypatch.setenv("GPU_EXECUTOR_INPROC_COALESCE_AFTER_FIRST_MS", "0")

    batch = ex._gather_batch(max_wait_ms=1, max_batch_size=8)
    assert len(batch) == 1
    assert ex._request_queue.get_nowait_calls >= 1
    assert len(ex._request_queue.get_calls) == 1
    assert abs(ex._request_queue.get_calls[0] - 0.1) < 1e-6


def test_gather_batch_collects_coalescable_gpu_work() -> None:
    class _SeqQueue:
        def __init__(self, items: list[GpuRequest]):
            self.items = list(items)

        def get(self, timeout=None):
            if self.items:
                return self.items.pop(0)
            raise queue.Empty()

    req1 = GpuRequest(
        request_type=GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
        request_id=301,
        worker_id=1,
        payload={},
    )
    req2 = GpuRequest(
        request_type=GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS,
        request_id=302,
        worker_id=1,
        payload={},
    )
    req3 = GpuRequest(
        request_type=GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS,
        request_id=303,
        worker_id=1,
        payload={},
    )

    ex = GpuExecutor()
    ex._in_process_queues = True
    ex._request_queue = _SeqQueue([req1, req2, req3])

    batch = ex._gather_batch(max_wait_ms=1, max_batch_size=8)
    # Heavy families are now bounded by their family coalescers/chunk caps, not by
    # a hard one-request gather barrier.
    assert [r.request_id for r in batch] == [301, 302, 303]
    assert [r.request_type for r in batch] == [
        GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
        GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS,
        GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS,
    ]
    assert len(ex._request_queue.items) == 0


def test_gather_batch_treats_gpu_native_ga_as_no_batch() -> None:
    class _SeqQueue:
        def __init__(self, items: list[GpuRequest]):
            self.items = list(items)

        def get(self, timeout=None):
            if self.items:
                return self.items.pop(0)
            raise queue.Empty()

    requests = [
        GpuRequest(
            request_type=GpuRequestType.GPU_NATIVE_GA_RUN,
            request_id=req_id,
            worker_id=1,
            payload={},
        )
        for req_id in (401, 402, 403)
    ]

    ex = GpuExecutor()
    ex._in_process_queues = True
    ex._request_queue = _SeqQueue(requests)

    batch = ex._gather_batch(max_wait_ms=1, max_batch_size=8)
    assert [r.request_id for r in batch] == [401]
    assert len(ex._request_queue.items) == 2

    batch2 = ex._gather_batch(max_wait_ms=1, max_batch_size=8)
    assert [r.request_id for r in batch2] == [402]
    assert len(ex._request_queue.items) == 1


def test_gather_batch_defers_gpu_native_ga_behind_existing_work() -> None:
    class _SeqQueue:
        def __init__(self, items: list[GpuRequest]):
            self.items = list(items)

        def get(self, timeout=None):
            if self.items:
                return self.items.pop(0)
            raise queue.Empty()

    requests = [
        GpuRequest(
            request_type=GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
            request_id=411,
            worker_id=1,
            payload={},
        ),
        GpuRequest(
            request_type=GpuRequestType.GPU_NATIVE_GA_RUN,
            request_id=412,
            worker_id=1,
            payload={},
        ),
        GpuRequest(
            request_type=GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
            request_id=413,
            worker_id=1,
            payload={},
        ),
    ]

    ex = GpuExecutor()
    ex._in_process_queues = True
    ex._request_queue = _SeqQueue(requests)

    batch = ex._gather_batch(max_wait_ms=1, max_batch_size=8)
    assert [r.request_id for r in batch] == [411]
    assert [r.request_id for r in ex._request_queue.items] == [413]

    batch2 = ex._gather_batch(max_wait_ms=1, max_batch_size=8)
    assert [r.request_id for r in batch2] == [412]
    assert [r.request_id for r in ex._request_queue.items] == [413]

    batch3 = ex._gather_batch(max_wait_ms=1, max_batch_size=8)
    assert [r.request_id for r in batch3] == [413]
    assert len(ex._request_queue.items) == 0


def test_gather_batch_prioritizes_fg_recovery_after_ga_turn_streak(monkeypatch) -> None:
    class _SeqQueue:
        def __init__(self, items: list[GpuRequest]):
            self.items = list(items)

        def get(self, timeout=None):
            if self.items:
                return self.items.pop(0)
            raise queue.Empty()

    requests = [
        GpuRequest(
            request_type=GpuRequestType.GPU_NATIVE_GA_RUN,
            request_id=421,
            worker_id=1,
            payload={"song_slot": 1},
        ),
        GpuRequest(
            request_type=GpuRequestType.GPU_NATIVE_GA_RUN,
            request_id=422,
            worker_id=1,
            payload={"song_slot": 2},
        ),
        GpuRequest(
            request_type=GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
            request_id=423,
            worker_id=1,
            payload={},
        ),
    ]

    ex = GpuExecutor()
    ex._in_process_queues = True
    ex._request_queue = _SeqQueue(requests)
    ex._ga_owner_turn_streak = 1

    monkeypatch.setenv("GPU_EXECUTOR_GA_RECOVERY_STREAK_MAX", "1")
    monkeypatch.setenv("GPU_EXECUTOR_GA_RECOVERY_LOOKAHEAD_MAX_REQS", "8")

    batch = ex._gather_batch(max_wait_ms=1, max_batch_size=8)
    assert [r.request_id for r in batch] == [423]
    assert [r.request_id for r in ex._staged_requests] == [421, 422]

    batch2 = ex._gather_batch(max_wait_ms=1, max_batch_size=8)
    assert [r.request_id for r in batch2] == [421]
    batch3 = ex._gather_batch(max_wait_ms=1, max_batch_size=8)
    assert [r.request_id for r in batch3] == [422]


def test_gpu_executor_timer_period_lifecycle(monkeypatch):
    if os.name != "nt":
        return

    import gear_optimizer.solver.gpu_executor as gpu_executor_mod

    calls = {"acquire": 0, "release": 0}

    def _fake_acquire() -> bool:
        calls["acquire"] += 1
        return True

    def _fake_release() -> None:
        calls["release"] += 1

    monkeypatch.setattr(gpu_executor_mod, "_acquire_windows_timer_period_1ms", _fake_acquire)
    monkeypatch.setattr(gpu_executor_mod, "_release_windows_timer_period_1ms", _fake_release)

    def _fake_loop(self) -> None:
        while self._running:
            req = self._request_queue.get()
            if req.request_type == gpu_executor_mod.GpuRequestType.SHUTDOWN:
                break

    monkeypatch.setattr(GpuExecutor, "_executor_loop", _fake_loop)

    monkeypatch.setenv("GPU_ALLOW_SYSTEM_TIMER_OVERRIDE", "1")
    monkeypatch.delenv("GPU_EXECUTOR_BATCH_WAIT_MS", raising=False)
    monkeypatch.setenv("GPU_EXECUTOR_INPROC_COALESCE_AFTER_FIRST_MS", "2")

    ex = GpuExecutor()
    ex.start(in_process=True)
    ex.stop()

    assert calls["acquire"] == 1
    assert calls["release"] == 1


def test_gpu_executor_timer_period_requires_opt_in(monkeypatch):
    if os.name != "nt":
        return

    import gear_optimizer.solver.gpu_executor as gpu_executor_mod

    calls = {"acquire": 0, "release": 0}

    def _fake_acquire() -> bool:
        calls["acquire"] += 1
        return True

    def _fake_release() -> None:
        calls["release"] += 1

    monkeypatch.setattr(gpu_executor_mod, "_acquire_windows_timer_period_1ms", _fake_acquire)
    monkeypatch.setattr(gpu_executor_mod, "_release_windows_timer_period_1ms", _fake_release)

    def _fake_loop(self) -> None:
        while self._running:
            req = self._request_queue.get()
            if req.request_type == gpu_executor_mod.GpuRequestType.SHUTDOWN:
                break

    monkeypatch.setattr(GpuExecutor, "_executor_loop", _fake_loop)

    monkeypatch.delenv("GPU_ALLOW_SYSTEM_TIMER_OVERRIDE", raising=False)
    monkeypatch.delenv("GPU_EXECUTOR_BATCH_WAIT_MS", raising=False)
    monkeypatch.setenv("GPU_EXECUTOR_INPROC_COALESCE_AFTER_FIRST_MS", "2")

    ex = GpuExecutor()
    ex.start(in_process=True)
    ex.stop()

    assert calls["acquire"] == 0
    assert calls["release"] == 0
