import queue
import os

from gear_optimizer.solver.gpu_executor import (
    GpuExecutor,
    GpuRequest,
    GpuRequestType,
    _effective_owner_batch_max,
)


def test_effective_owner_batch_max_limits_inproc_default_breadth() -> None:
    assert _effective_owner_batch_max(8, in_process_queues=True, batch_max_overridden=False) == 24
    assert _effective_owner_batch_max(24, in_process_queues=True, batch_max_overridden=False) == 24
    assert _effective_owner_batch_max(32, in_process_queues=True, batch_max_overridden=False) == 32
    assert _effective_owner_batch_max(16, in_process_queues=True, batch_max_overridden=True) == 16
    assert _effective_owner_batch_max(8, in_process_queues=False, batch_max_overridden=False) == 8


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
