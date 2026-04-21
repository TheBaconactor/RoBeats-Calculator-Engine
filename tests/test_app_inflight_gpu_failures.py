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
    app._effective_total_tasks = lambda tasks: len(tasks or [])
    return app


def _build_tasks(*, inflight_songs: int = 2, inflight_instances: int = 1, count: int = 2):
    cfg = {"IterationEngine": {"inflightsongs": inflight_songs, "inflightinstances": inflight_instances}}
    return [(f"song-{idx}", None, None, cfg, None, None) for idx in range(count)]


def _build_calc_only_tasks(*, count: int = 1):
    cfg = {"IterationEngine": {"inflightsongs": 1, "MetaFinder": "false"}}
    return [(f"song-{idx}", f"Calc Song {idx}", "Hard", cfg, None, None) for idx in range(count)]


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


def test_calculate_only_skips_native_inflight_pipeline(monkeypatch):
    app = _make_minimal_app()
    tasks = _build_calc_only_tasks(count=1)
    native_calls: list[dict] = []
    consumed: list[dict] = []

    def _record_run(*args, **kwargs):
        native_calls.append({"args": args, "kwargs": kwargs})

    def _fake_safe_process(task):
        return {"song": task[1], "_queue_key": task[0], "_queue_label": task[1]}

    def _consume(results_iter, **_kwargs):
        consumed.extend(list(results_iter))

    app._consume_results = _consume

    monkeypatch.setattr("gear_optimizer.app.safe_process_song_task", _fake_safe_process)
    monkeypatch.setitem(
        sys.modules,
        "gear_optimizer.solver.native_inflight_orchestrator",
        types.SimpleNamespace(run_native_inflight_song_pipeline=_record_run),
    )

    app._run_sequential(tasks, completed_songs=set(), memory_resume_tracker=None)

    assert native_calls == []
    assert consumed == [{"song": "Calc Song 0", "_queue_key": "song-0", "_queue_label": "Calc Song 0"}]


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


def test_dual_process_inflight_is_quarantined_on_main_without_explicit_env(monkeypatch):
    app = _make_minimal_app()
    tasks = _build_tasks(inflight_songs=2, inflight_instances=2, count=2)
    native_calls: list[dict] = []
    dual_calls: list[dict] = []

    def _record_run(*args, **kwargs):
        native_calls.append({"args": args, "kwargs": kwargs})

    app._run_dual_process_inflight = lambda *args, **kwargs: dual_calls.append({"args": args, "kwargs": kwargs})

    monkeypatch.setitem(
        sys.modules,
        "gear_optimizer.solver.native_inflight_orchestrator",
        types.SimpleNamespace(run_native_inflight_song_pipeline=_record_run),
    )
    monkeypatch.delenv("INFLIGHT_ALLOW_DUAL_PROCESS", raising=False)

    app._run_sequential(tasks, completed_songs=set(), memory_resume_tracker=None)

    assert len(native_calls) == 1
    assert dual_calls == []


def test_dual_process_inflight_requires_explicit_allow_env(monkeypatch):
    app = _make_minimal_app()
    tasks = _build_tasks(inflight_songs=2, inflight_instances=2, count=2)
    dual_calls: list[dict] = []

    app._run_dual_process_inflight = lambda *args, **kwargs: dual_calls.append({"args": args, "kwargs": kwargs})

    monkeypatch.setenv("INFLIGHT_ALLOW_DUAL_PROCESS", "1")
    monkeypatch.setitem(
        sys.modules,
        "gear_optimizer.solver.native_inflight_orchestrator",
        types.SimpleNamespace(run_native_inflight_song_pipeline=lambda *_args, **_kwargs: None),
    )

    app._run_sequential(tasks, completed_songs=set(), memory_resume_tracker=None)

    assert len(dual_calls) == 1


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
