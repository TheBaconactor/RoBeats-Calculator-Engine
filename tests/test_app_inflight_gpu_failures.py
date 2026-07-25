import configparser
import os
import sys
import types

import pytest

from gear_optimizer.app import GearOptimizerApp
from gear_optimizer.core.config import DEFAULT_INFLIGHT_SONGS
from gear_optimizer.engine.native import NativeOptimizationEngine
from gear_optimizer.solver.native_inflight_config import CANONICAL_GA_QUEUE_MULT
from gear_optimizer.solver.gpu_service import GpuServiceTimeoutError


def _make_minimal_app() -> GearOptimizerApp:
    app = object.__new__(GearOptimizerApp)
    app._progress = None
    app._progress_counts_driven = False
    app._stop_requested_now = lambda: False
    app._start_post_processor = lambda _total: (object(), object())
    app._stop_post_processor = lambda _queue, _proc: None
    app._set_runtime_progress_counts = lambda **_kwargs: None
    app._progress_event = lambda **_kwargs: None
    app._effective_total_tasks = lambda tasks: len(tasks or [])
    return app


def _build_tasks(*, inflight_songs: int = 2, count: int = 2):
    cfg = {"IterationEngine": {"inflightsongs": inflight_songs}}
    return [
        (
            f"song-{idx}.txt",
            f"Song {idx}",
            "Hard",
            cfg,
            {},
            {},
            [],
            [],
            {},
            {},
            True,
            1,
            None,
            0,
            False,
        )
        for idx in range(count)
    ]


def test_single_song_still_uses_native_inflight_pipeline(monkeypatch):
    app = _make_minimal_app()
    tasks = _build_tasks(inflight_songs=1, count=1)
    calls: list[dict] = []

    def _record_run(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})

    monkeypatch.setitem(
        sys.modules,
        "gear_optimizer.solver.native_inflight_orchestrator",
        types.SimpleNamespace(run_native_inflight_song_pipeline=_record_run),
    )

    app._run_sequential(tasks, completed_songs=set(), memory_resume_tracker=None)

    expected_tasks = [NativeOptimizationEngine._canonical_task_tuple(task) for task in tasks]
    assert len(calls) == 1
    assert calls[0]["args"][0] == expected_tasks
    assert calls[0]["kwargs"]["in_flight_songs"] == 1
    assert "total_tasks" not in calls[0]["kwargs"]


def test_full_task_prefix_uses_native_inflight_pipeline(monkeypatch):
    app = _make_minimal_app()
    tasks = _build_tasks(inflight_songs=1, count=1)
    native_calls: list[dict] = []

    def _record_run(*args, **kwargs):
        native_calls.append({"args": args, "kwargs": kwargs})

    monkeypatch.setitem(
        sys.modules,
        "gear_optimizer.solver.native_inflight_orchestrator",
        types.SimpleNamespace(run_native_inflight_song_pipeline=_record_run),
    )

    app._run_sequential(tasks, completed_songs=set(), memory_resume_tracker=None)

    expected_tasks = [NativeOptimizationEngine._canonical_task_tuple(task) for task in tasks]
    assert len(native_calls) == 1
    assert native_calls[0]["args"][0] == expected_tasks


@pytest.mark.parametrize(
    ("configured", "count", "expected"),
    [(0, 2, 2), (1, 2, 1), (20, 2, 2)],
)
def test_native_execution_uses_canonical_inflight_resolution(monkeypatch, configured, count, expected):
    app = _make_minimal_app()
    tasks = _build_tasks(inflight_songs=configured, count=count)
    calls: list[dict] = []
    monkeypatch.delenv("IN_FLIGHT_SONGS", raising=False)

    def _record_run(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})

    monkeypatch.setitem(
        sys.modules,
        "gear_optimizer.solver.native_inflight_orchestrator",
        types.SimpleNamespace(run_native_inflight_song_pipeline=_record_run),
    )

    app._run_sequential(tasks, completed_songs=set(), memory_resume_tracker=None)

    assert calls[0]["kwargs"]["in_flight_songs"] == expected


def test_gpu_slot_auto_sizing_uses_canonical_inflight_default(monkeypatch):
    app = object.__new__(GearOptimizerApp)
    cfg = configparser.ConfigParser()
    monkeypatch.delenv("IN_FLIGHT_SONGS", raising=False)
    monkeypatch.delenv("GPU_SONG_SLOTS", raising=False)
    monkeypatch.delitem(sys.modules, "gear_optimizer.solver.taichi_gem.fields", raising=False)

    app._maybe_autoset_gpu_song_slots(cfg)

    expected = max(24, DEFAULT_INFLIGHT_SONGS * CANONICAL_GA_QUEUE_MULT + 2)
    assert int(os.environ["GPU_SONG_SLOTS"]) == expected


def test_inflight_failure_raises_instead_of_falling_back(monkeypatch):
    app = _make_minimal_app()
    tasks = _build_tasks(inflight_songs=2, count=2)

    def _raise_runtime(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setitem(
        sys.modules,
        "gear_optimizer.solver.native_inflight_orchestrator",
        types.SimpleNamespace(run_native_inflight_song_pipeline=_raise_runtime),
    )

    with pytest.raises(RuntimeError, match="Native in-flight pipeline failed; no sequential path remains."):
        app._run_sequential(tasks, completed_songs=set(), memory_resume_tracker=None)


def test_service_mode_re_raises_gpu_timeout_instead_of_falling_back(monkeypatch):
    app = _make_minimal_app()
    tasks = _build_tasks()

    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", "1")

    def _raise_timeout(*_args, **_kwargs):
        raise GpuServiceTimeoutError("GPU service request gpu_native_ga_run timed out after 240.0s")

    monkeypatch.setitem(
        sys.modules,
        "gear_optimizer.solver.native_inflight_orchestrator",
        types.SimpleNamespace(run_native_inflight_song_pipeline=_raise_timeout),
    )

    with pytest.raises(GpuServiceTimeoutError, match="timed out"):
        app._run_sequential(tasks, completed_songs=set(), memory_resume_tracker=None)


def test_configure_execution_prewarms_native_ga():
    from gear_optimizer.solver.taichi_gem import fields as gpu_fields

    app = object.__new__(GearOptimizerApp)
    gpu_fields._REQUESTED_MAX_GA_RUNS = None
    cfg = configparser.ConfigParser()
    cfg.read_dict({"IterationEngine": {"InFlightSongs": "0", "GA_MultiStart": "3"}})

    app._configure_execution_and_prewarm(cfg)

    # GA buffer sizing is recorded in-process now (was the GPU_NATIVE_GA_MAX_RUNS env bridge).
    assert gpu_fields._REQUESTED_MAX_GA_RUNS == 3


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
