import queue
import os

from gear_optimizer.solver.gpu_executor import GpuExecutor, GpuRequest, GpuRequestType


def test_gather_batch_inproc_does_not_force_one_ms_wait(monkeypatch):
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
    assert abs(ex._request_queue.timeouts[0] - 0.001) < 1e-6
    assert 0.0 <= ex._request_queue.timeouts[1] < 0.001


def test_gather_batch_inproc_short_wait_uses_nonblocking_poll(monkeypatch):
    class _NowaitQueue:
        def __init__(self, first_req: GpuRequest):
            self._first_req = first_req
            self._returned = False
            self.get_calls: list[float] = []
            self.get_nowait_calls = 0

        def get(self, timeout=None):
            self.get_calls.append(float(timeout))
            raise AssertionError("blocking get() should not be used for short in-process waits")

        def get_nowait(self):
            self.get_nowait_calls += 1
            if not self._returned:
                self._returned = True
                return self._first_req
            raise queue.Empty()

    req = GpuRequest(
        request_type=GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
        request_id=202,
        worker_id=1,
        payload={},
    )

    ex = GpuExecutor()
    ex._in_process_queues = True
    ex._request_queue = _NowaitQueue(req)
    ex._short_wait_spin_sec = 0.01

    monkeypatch.setenv("GPU_EXECUTOR_INPROC_COALESCE", "1")
    monkeypatch.setenv("GPU_EXECUTOR_INPROC_COALESCE_AFTER_FIRST_MS", "0")

    batch = ex._gather_batch(max_wait_ms=1, max_batch_size=8)
    assert len(batch) == 1
    assert ex._request_queue.get_nowait_calls >= 1
    assert all(float(t or 0.0) <= 0.0 for t in ex._request_queue.get_calls)


def test_gather_batch_stops_when_no_batch_type_seen() -> None:
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
    # No-batch barrier types should NOT be batched behind unrelated work; they are deferred to
    # become the first item of the next batch.
    assert [r.request_id for r in batch] == [301]
    assert [r.request_type for r in batch] == [
        GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
    ]
    assert len(ex._request_queue.items) == 1

    batch2 = ex._gather_batch(max_wait_ms=0, max_batch_size=8)
    assert [r.request_id for r in batch2] == [302]
    assert [r.request_type for r in batch2] == [GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS]
    assert len(ex._request_queue.items) == 1

    batch3 = ex._gather_batch(max_wait_ms=0, max_batch_size=8)
    assert [r.request_id for r in batch3] == [303]
    assert [r.request_type for r in batch3] == [GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS]
    assert len(ex._request_queue.items) == 0


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
