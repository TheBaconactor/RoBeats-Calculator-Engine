from __future__ import annotations

import sys
import types

from gear_optimizer.domain.jobs import SharedRunContext, SongJob, task_tuple_from_job_context
from gear_optimizer.engine.native import NativeOptimizationEngine, NativeOptimizationRequest


def _task() -> tuple:
    context = SharedRunContext(
        multi_start=3,
        ref_arrays={},
        all_gears=[],
        all_minis=[],
        gears_by_name={},
        minis_by_name={},
        ga_depth=1,
        parallel_workers=1,
    )
    job = SongJob(file_path="fp", song_name="song", difficulty="Hard")
    return task_tuple_from_job_context(job, context, {"repeat_index": 1, "repeat_total": 2, "ga_seed": 123})


def test_native_optimization_engine_delegates_to_native_inflight(monkeypatch):
    calls = []

    def _run_native_inflight_song_pipeline(tasks, **kwargs):
        calls.append((tasks, kwargs))

    monkeypatch.setitem(
        sys.modules,
        "gear_optimizer.solver.native_inflight_orchestrator",
        types.SimpleNamespace(run_native_inflight_song_pipeline=_run_native_inflight_song_pipeline),
    )

    completed: set[str] = set()
    task = _task()
    expected_task = NativeOptimizationEngine._canonical_task_tuple(task)
    NativeOptimizationEngine().run(
        NativeOptimizationRequest(
            tasks=[task],
            in_flight_songs=3,
            completed_songs=completed,
        )
    )

    assert calls == [
        (
            [expected_task],
            {
                "in_flight_songs": 3,
                "completed_songs": completed,
                "memory_resume_tracker": None,
                "post_queue": None,
                "stop_requested": None,
                "progress_cb": None,
                "bundle_completed_cb": None,
            },
        )
    ]


def test_native_optimization_engine_rejects_invalid_task_tuple():
    try:
        NativeOptimizationEngine().run(
            NativeOptimizationRequest(tasks=[("too", "short")], in_flight_songs=1, completed_songs=set())
        )
    except ValueError as exc:
        assert "song task must contain the fixed-field production prefix" in str(exc)
    else:
        raise AssertionError("expected invalid native task tuple to fail at engine boundary")
