from __future__ import annotations

import sys
import types

from gear_optimizer.engine.native import NativeOptimizationEngine, NativeOptimizationRequest


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
    task = ("fp", "song", "Hard")
    NativeOptimizationEngine().run(
        NativeOptimizationRequest(
            tasks=[task],
            in_flight_songs=3,
            completed_songs=completed,
            total_tasks=1,
        )
    )

    assert calls == [
        (
            [task],
            {
                "in_flight_songs": 3,
                "completed_songs": completed,
                "memory_resume_tracker": None,
                "post_queue": None,
                "total_tasks": 1,
                "stop_requested": None,
                "progress_cb": None,
                "bundle_completed_cb": None,
            },
        )
    ]
