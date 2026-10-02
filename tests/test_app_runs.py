import os
import queue
import sys
import types

import pytest

from gear_optimizer.app import GearOptimizerApp
from gear_optimizer.domain.jobs import SharedRunContext, SongTask
from gear_optimizer.solver.gpu_executor import GpuFatalError, GpuServiceTimeoutError


def _make_minimal_app() -> GearOptimizerApp:
    app = object.__new__(GearOptimizerApp)
    app._progress = None
    app._stop_requested_now = lambda: False
    app._start_post_processor = lambda _total: (queue.Queue(), object())
    app._stop_post_processor = lambda _queue, _proc: True  # every song stored
    app._set_runtime_progress_counts = lambda **_kwargs: None
    app._progress_event = lambda **_kwargs: None
    return app


def _build_tasks(*, count: int = 2):
    context = SharedRunContext(multi_start=3, curves={}, gears={}, minis={}, ga_depth=1)
    return [SongTask(f"song-{idx}.txt", f"Song {idx}", context) for idx in range(count)]


def _patch_queue(monkeypatch, run_queue) -> dict:
    """The app's run with pipeline.solve.run_queue replaced: no GPU executor, no post-processor process."""
    from gear_optimizer.pipeline import solve as solve_module
    from gear_optimizer.solver import gpu_executor

    seen: dict = {}

    class _Executor:
        def start(self):
            seen["started"] = True

        def stop(self):
            seen["stopped"] = True

    monkeypatch.setattr(gpu_executor, "get_gpu_executor", _Executor)
    monkeypatch.setattr(solve_module, "run_queue", run_queue)
    return seen


def test_the_run_solves_the_queue_with_run_queue_posting_to_the_post_processor(monkeypatch):
    calls = []
    seen = _patch_queue(monkeypatch, lambda tasks, executor, *, post, **kwargs: calls.append((tasks, post)))
    tasks = _build_tasks(count=2)
    app = _make_minimal_app()
    post_queue: queue.Queue = queue.Queue()
    app._start_post_processor = lambda _total: (post_queue, object())

    app._run_sequential(tasks, completed_songs=set(), memory_resume_tracker=None)

    assert calls == [(tasks, post_queue.put)]
    assert seen["started"] and seen["stopped"]  # a batch run persists Taichi's offline cache


def test_a_failed_run_raises(monkeypatch):
    def _raise_runtime(*_args, **_kwargs):
        raise RuntimeError("boom")

    _patch_queue(monkeypatch, _raise_runtime)
    with pytest.raises(RuntimeError, match="boom"):
        _make_minimal_app()._run_sequential(_build_tasks(count=2), completed_songs=set(), memory_resume_tracker=None)


def test_a_run_whose_songs_failed_raises_after_the_run(monkeypatch):
    app = _make_minimal_app()
    app._stop_post_processor = lambda _queue, _proc: False  # the post-processor reported failed songs
    ran = []
    _patch_queue(monkeypatch, lambda *_a, **_k: ran.append(1))

    with pytest.raises(RuntimeError, match="failed in this run"):
        app._run_sequential(_build_tasks(count=2), completed_songs=set(), memory_resume_tracker=None)
    assert ran == [1]


def test_a_gpu_timeout_ends_the_run(monkeypatch):
    def _raise_timeout(*_args, **_kwargs):
        raise GpuServiceTimeoutError("GPU call _ga_turn timed out after 240.0s")

    _patch_queue(monkeypatch, _raise_timeout)
    with pytest.raises(GpuServiceTimeoutError, match="timed out"):
        _make_minimal_app()._run_sequential(_build_tasks(), completed_songs=set(), memory_resume_tracker=None)


def test_configure_execution_sizes_the_ga_buffers_and_starts_the_gpu_executor(monkeypatch):
    from gear_optimizer.solver import gpu_executor
    from gear_optimizer.solver.taichi_gem import fields as gpu_fields

    started = []
    # No real GPU: a started executor would keep initializing Taichi after the test, racing later tests' resets.
    monkeypatch.setattr(gpu_executor, "get_gpu_executor", lambda: types.SimpleNamespace(start=lambda: started.append(1)))
    app = object.__new__(GearOptimizerApp)
    app._materialize_gpu_runtime_on_main_thread = lambda: None
    gpu_fields._REQUESTED_MAX_GA_RUNS = None
    app._configure_execution_and_prewarm(3)

    # GA buffer sizing is recorded in-process now (was the GPU_NATIVE_GA_MAX_RUNS env bridge).
    assert gpu_fields._REQUESTED_MAX_GA_RUNS == 3
    assert started == [1]


def test_ga_buffer_config_restores_defaults_and_clears_request_on_reset():
    # reset_fields_state() restores GA buffer sizing to defaults AND clears the requested
    # record, so a stale session size never silently re-applies after a hard_reset_taichi
    # (CPU-level mirror of the gpu-marked test_gpu_ga_run_buffer_config_restores_defaults_
    # after_hard_reset). The GA recovery paths re-call configure_ga_run_buffers() to re-size.
    from gear_optimizer.solver.taichi_gem import fields as gpu_fields

    gpu_fields.reset_fields_state()
    try:
        gpu_fields.configure_ga_run_buffers(max_runs=7, max_genomes=705)
        assert gpu_fields.MAX_GA_RUNS == 7
        assert gpu_fields._REQUESTED_MAX_GA_RUNS == 7

        gpu_fields.reset_fields_state()
        assert gpu_fields.MAX_GA_RUNS == gpu_fields.DEFAULT_MAX_GA_RUNS
        assert gpu_fields.MAX_GA_RUN_GENOMES == gpu_fields.DEFAULT_MAX_GA_RUN_GENOMES
        assert gpu_fields._REQUESTED_MAX_GA_RUNS is None

        # A cleared record must NOT re-apply a stale size on the next allocation.
        gpu_fields._apply_requested_ga_run_buffers()
        assert gpu_fields.MAX_GA_RUNS == gpu_fields.DEFAULT_MAX_GA_RUNS
    finally:
        gpu_fields.reset_fields_state()


def test_request_stop_requests_gpu_abort(monkeypatch):
    import gear_optimizer.solver.gpu_executor as gpu_executor_module

    app = object.__new__(GearOptimizerApp)

    class _FakeStopControl:
        def __init__(self) -> None:
            self.calls: list[tuple[str, bool]] = []

        def request_stop(self, reason: str, *, force: bool = False):
            self.calls.append((str(reason), bool(force)))
            return "stop-set"

    class _FakeExecutor:
        def __init__(self) -> None:
            self.is_running = True
            self.abort_calls: list[str] = []

        def request_abort(self, reason: str) -> None:
            self.abort_calls.append(str(reason))

    stop_control = _FakeStopControl()
    fake_executor = _FakeExecutor()
    app._stop_control = stop_control

    monkeypatch.setattr(gpu_executor_module, "get_gpu_executor", lambda: fake_executor)

    out = app.request_stop("hotkey stop", force=True)

    assert out == "stop-set"
    assert stop_control.calls == [("hotkey stop", True)]
    assert fake_executor.abort_calls == ["stop requested (hotkey stop)"]


def _looping_app(monkeypatch, tmp_path, failure: BaseException):
    """A real app whose iteration fails right after reading LoopForever run settings."""
    import gear_optimizer.app as app_module
    from gear_optimizer.settings import RunSettings

    monkeypatch.setenv("EVOLUTION_DB_PATH", str(tmp_path / "results.db"))
    monkeypatch.setattr(app_module, "update_and_restart_client", lambda: None)
    monkeypatch.setattr(app_module, "sync_frontiers_from_server", lambda: types.SimpleNamespace(enabled=False))
    monkeypatch.setattr(app_module.settings, "read_run_settings", lambda: RunSettings(loop_forever=True))
    iterations = []

    def fail():
        iterations.append(1)
        if len(iterations) > 3:
            raise KeyboardInterrupt  # a non-fatal failure loops; end the loop for the test
        raise failure

    monkeypatch.setattr(app_module, "sync_exported_game_data", fail)
    monkeypatch.setattr(GearOptimizerApp, "_handle_loop_restart", lambda self: None)
    return GearOptimizerApp(), iterations


def test_a_fatal_gpu_failure_stops_a_looping_run_with_exit_status_1(monkeypatch, tmp_path):
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", "1")
    app, iterations = _looping_app(monkeypatch, tmp_path, GpuServiceTimeoutError("GPU service request timed out"))
    assert app.run() == 1
    assert iterations == [1]


def test_a_failed_iteration_keeps_a_looping_run_going_and_is_reported(monkeypatch, tmp_path):
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", "1")
    app, iterations = _looping_app(monkeypatch, tmp_path, RuntimeError("song(s) failed in this run"))
    assert app.run() == 1
    assert len(iterations) == 4


@pytest.mark.parametrize(
    ("failure", "fatal"),
    [
        (GpuFatalError("[InFlight] GPU executor Taichi init failed or timed out"), True),
        (RuntimeError("song failed"), False),
        (RuntimeError("Vulkan: VK_ERROR_DEVICE_LOST (device lost)"), True),
        # Only the engine's own GPU states are typed; any other timeout text is an ordinary failure.
        (RuntimeError("database lock timed out after 30s"), False),
    ],
)
def test_fatal_gpu_failures_are_the_typed_ones_and_the_drivers_device_losses(monkeypatch, failure, fatal):
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", "1")
    wrapped = RuntimeError("song failed")
    wrapped.__cause__ = failure
    assert GearOptimizerApp()._is_fatal_inflight_exception(wrapped) is fatal
