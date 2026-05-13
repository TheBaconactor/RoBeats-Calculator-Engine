from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence


@dataclass(frozen=True, slots=True)
class NativeOptimizationRequest:
    tasks: Sequence[tuple]
    in_flight_songs: int
    completed_songs: set[str]
    memory_resume_tracker: Any = None
    post_queue: Any = None
    total_tasks: int | None = None
    stop_requested: Callable[[], bool] | None = None
    progress_cb: Callable[..., Any] | None = None
    bundle_completed_cb: Callable[..., Any] | None = None


class NativeOptimizationEngine:
    """Public owner for the native in-flight production optimizer."""

    def run(self, request: NativeOptimizationRequest) -> None:
        from gear_optimizer.solver.native_inflight_orchestrator import run_native_inflight_song_pipeline

        run_native_inflight_song_pipeline(
            list(request.tasks),
            in_flight_songs=int(request.in_flight_songs),
            completed_songs=request.completed_songs,
            memory_resume_tracker=request.memory_resume_tracker,
            post_queue=request.post_queue,
            total_tasks=request.total_tasks,
            stop_requested=request.stop_requested,
            progress_cb=request.progress_cb,
            bundle_completed_cb=request.bundle_completed_cb,
        )
