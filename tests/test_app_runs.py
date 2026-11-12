"""The standalone loop (main.py -> cli.run -> GearOptimizerApp.run) with its queue, workers and charts replaced."""

import types

import pytest

from gear_optimizer.core.timing_modes import PRECISE
from gear_optimizer.app import GearOptimizerApp
from gear_optimizer.domain.jobs import SharedRunContext, SongTask
from gear_optimizer.settings import RunSettings
from gear_optimizer.gpu.executor import GpuFatalError, GpuServiceTimeoutError


def _tasks(count: int) -> list[SongTask]:
    context = SharedRunContext(multi_start=3, curves={}, gears={}, minis={}, ga_depth=1)
    return [SongTask(f"song-{idx}.txt", f"Song {idx}", PRECISE, context) for idx in range(count)]


def _app(monkeypatch, tmp_path, run: RunSettings, queues: list[list[SongTask]], outcome):
    """An app whose iterations queue `queues` in turn (then stop the loop) and whose worker pool plays
    `outcome(tasks, kwargs)`; returns the app and the pool's calls."""
    import gear_optimizer.app as app_module

    monkeypatch.setenv("EVOLUTION_DB_PATH", str(tmp_path / "results.db"))
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_BIN_DIR", str(tmp_path / "bin"))
    monkeypatch.setattr(app_module.settings, "read_run_settings", lambda: run)
    monkeypatch.setattr(app_module, "stat_curves", lambda: {})
    monkeypatch.setattr(app_module, "load_catalog", lambda _path: types.SimpleNamespace(gears={}, minis={}))
    monkeypatch.setattr(app_module, "run_startup_cpu_work", lambda **_kwargs: None)
    pending = list(queues)

    def build_queue(_run, _context):
        if not pending:
            raise KeyboardInterrupt  # ends a LoopForever run
        return pending.pop(0)

    calls = []

    def solve_queue(tasks, **kwargs):
        calls.append(kwargs)
        return outcome(tasks, kwargs)

    monkeypatch.setattr(app_module, "build_queue", build_queue)
    monkeypatch.setattr(app_module, "solve_queue", solve_queue)
    return GearOptimizerApp(), calls


def _all_done(tasks, kw):
    for task in tasks:
        kw["on_done"](task.label, 0, 10)


def test_the_queue_goes_to_the_configured_workers_capped_by_its_size(monkeypatch, tmp_path):
    run = RunSettings(workers=8, loop_forever=True)
    app, calls = _app(monkeypatch, tmp_path, run, [_tasks(3), _tasks(9)], _all_done)
    assert app.run() == 0
    assert [call["workers"] for call in calls] == [3, 8]


def test_without_a_workers_setting_the_machine_decides(monkeypatch, tmp_path):
    import gear_optimizer.app as app_module

    monkeypatch.setattr(app_module, "solve_worker_count", lambda: 5)
    app, calls = _app(monkeypatch, tmp_path, RunSettings(), [_tasks(9)], _all_done)
    assert app.run() == 0
    assert calls[0]["workers"] == 5


def test_a_run_whose_songs_failed_exits_with_status_1(monkeypatch, tmp_path):
    def outcome(tasks, kw):
        kw["on_failed"](tasks[0].label)
        kw["on_done"](tasks[1].label, 5, 5)

    app, calls = _app(monkeypatch, tmp_path, RunSettings(workers=2), [_tasks(2)], outcome)
    assert app.run() == 1
    assert len(calls) == 1


def _failing(failure: BaseException):
    def outcome(_tasks, _kw):
        raise failure

    return outcome


def test_a_lost_gpu_stops_a_looping_run_with_exit_status_1(monkeypatch, tmp_path):
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", "1")
    failure = GpuFatalError("GPU call _ga_turn timed out after 240.0s")
    app, calls = _app(monkeypatch, tmp_path, RunSettings(loop_forever=True), [_tasks(2)] * 4, _failing(failure))
    assert app.run() == 1
    assert len(calls) == 1


def _looping_app(monkeypatch, tmp_path, failure: BaseException):
    """A real app whose iteration fails right after reading LoopForever run settings."""
    import gear_optimizer.app as app_module

    monkeypatch.setenv("EVOLUTION_DB_PATH", str(tmp_path / "results.db"))
    monkeypatch.setattr(app_module.settings, "read_run_settings", lambda: RunSettings(loop_forever=True))
    iterations = []

    def fail(_path):
        iterations.append(1)
        if len(iterations) > 3:
            raise KeyboardInterrupt  # a non-fatal failure loops; end the loop for the test
        raise failure

    monkeypatch.setattr(app_module, "load_catalog", fail)
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
def test_fatal_gpu_failures_are_the_typed_ones_and_the_drivers_device_losses(monkeypatch, tmp_path, failure, fatal):
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", "1")
    wrapped = RuntimeError("song failed")
    wrapped.__cause__ = failure
    app, iterations = _looping_app(monkeypatch, tmp_path, wrapped)
    assert app.run() == 1
    assert len(iterations) == (1 if fatal else 4)
