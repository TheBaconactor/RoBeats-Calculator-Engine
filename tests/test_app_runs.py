import types

import pytest

from gear_optimizer.core.timing_modes import PRECISE
from gear_optimizer.app import GearOptimizerApp
from gear_optimizer.domain.jobs import SharedRunContext, SongTask
from gear_optimizer.settings import RunSettings
from gear_optimizer.solver.gpu_executor import GpuFatalError, GpuServiceTimeoutError


def _app() -> GearOptimizerApp:
    app = object.__new__(GearOptimizerApp)
    app._progress_enabled = False
    app._progress = None
    app._hotkey_thread = None
    app._session_new_records = 0
    app._session_new_record_best_by_song = {}
    app._stop_requested_now = lambda: False
    return app


def _tasks(count: int) -> list[SongTask]:
    context = SharedRunContext(multi_start=3, curves={}, gears={}, minis={}, ga_depth=1)
    return [SongTask(f"song-{idx}.txt", f"Song {idx}", PRECISE, context) for idx in range(count)]


def _solve_queue(monkeypatch, outcome) -> list:
    """The app's worker pool replaced: `outcome(tasks, kwargs)` plays the run."""
    import gear_optimizer.app as app_module

    calls = []

    def solve_queue(tasks, **kwargs):
        calls.append(kwargs)
        return outcome(tasks, kwargs)

    monkeypatch.setattr(app_module, "solve_queue", solve_queue)
    return calls


def test_the_queue_goes_to_the_configured_workers_capped_by_its_size(monkeypatch):
    calls = _solve_queue(monkeypatch, lambda tasks, kw: [kw["on_done"](t.label, 0, 10) for t in tasks])
    app = _app()
    app._solve(_tasks(3), RunSettings(workers=8))
    app._solve(_tasks(9), RunSettings(workers=8))
    assert [call["workers"] for call in calls] == [3, 8]
    assert app._completed_tasks == 9 and app._session_new_records == 9


def test_without_a_workers_setting_the_machine_decides(monkeypatch):
    import gear_optimizer.app as app_module

    calls = _solve_queue(monkeypatch, lambda tasks, kw: 0)
    monkeypatch.setattr(app_module, "solve_worker_count", lambda: 5)
    _app()._solve(_tasks(9), RunSettings())
    assert calls[0]["workers"] == 5


def test_a_run_whose_songs_failed_raises_after_the_run(monkeypatch):
    def outcome(tasks, kw):
        kw["on_failed"](tasks[0].label)
        kw["on_done"](tasks[1].label, 5, 5)

    _solve_queue(monkeypatch, outcome)
    app = _app()
    with pytest.raises(RuntimeError, match="1 song\\(s\\) failed in this run"):
        app._solve(_tasks(2), RunSettings(workers=2))
    assert app._completed_tasks == 2


def test_a_lost_gpu_ends_the_run(monkeypatch):
    def outcome(tasks, kw):
        raise GpuFatalError("GPU call _ga_turn timed out after 240.0s")

    _solve_queue(monkeypatch, outcome)
    with pytest.raises(GpuFatalError, match="timed out"):
        _app()._solve(_tasks(2), RunSettings(workers=2))


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


def test_request_stop_goes_to_the_stop_control():
    app = object.__new__(GearOptimizerApp)
    calls = []
    app._stop_control = types.SimpleNamespace(request_stop=lambda reason, *, force=False: calls.append((reason, force)))
    app.request_stop("hotkey stop", force=True)
    assert calls == [("hotkey stop", True)]


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
