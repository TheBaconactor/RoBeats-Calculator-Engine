import sys
import types

import pytest

from gear_optimizer.app import GearOptimizerApp
from gear_optimizer.solver.gpu_service import GpuServiceTimeoutError


def _make_minimal_app() -> GearOptimizerApp:
    app = object.__new__(GearOptimizerApp)
    app._progress = None
    app._progress_counts_driven = False
    app._robeatsmeta_api = None
    app._stop_requested_now = lambda: False
    app._start_post_processor = lambda _total: (object(), object())
    app._stop_post_processor = lambda _queue, _proc: None
    app._set_runtime_progress_counts = lambda **_kwargs: None
    app._progress_event = lambda **_kwargs: None
    app._maybe_mark_robeatsmeta_song_batch_computed = lambda *_args, **_kwargs: None
    return app


def _build_tasks(*, inflight_songs: int = 2, count: int = 2):
    cfg = {"IterationEngine": {"inflightsongs": inflight_songs}}
    return [
        (f"song-{idx}", None, None, cfg, None, None)
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

    assert len(calls) == 1
    assert calls[0]["args"][0] == tasks
    assert calls[0]["kwargs"]["in_flight_songs"] == 1
    assert calls[0]["kwargs"]["total_tasks"] == 1


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

    with pytest.raises(RuntimeError, match="legacy sequential fallback has been removed"):
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
