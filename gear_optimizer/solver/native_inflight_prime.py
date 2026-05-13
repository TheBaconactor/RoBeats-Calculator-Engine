"""Startup priming for the native in-flight optimizer."""

from __future__ import annotations

import logging
import time
import traceback
from typing import Any, Callable

from gear_optimizer.domain.jobs import task_queue_label, task_song_name
from gear_optimizer.solver.native_inflight_completion import mark_song_completed
from gear_optimizer.solver.native_inflight_result_events import build_native_task_error_payload

logger = logging.getLogger(__name__)


def prime_native_inflight_prepared_queue(
    *,
    prime_target: int,
    pending_tasks,
    prepared,
    completed_songs: set[str],
    next_logical_task: Callable[[tuple], tuple[tuple, dict | None]],
    bind_bundle_song: Callable[[Any, tuple, dict | None], None],
    prepare_song: Callable[[tuple], Any],
    post: Callable[[dict], None],
    advance_bundle: Callable[..., bool],
    stage_profiler,
    memory_resume_tracker=None,
) -> int:
    """Synchronously prepare the initial native in-flight backlog."""
    prepared_count = 0
    for _ in range(max(0, int(prime_target))):
        first = pending_tasks.popleft()
        song_name = task_song_name(first)
        bundle_key = task_queue_label(first)
        if bundle_key in completed_songs:
            continue
        logical_task, repeat_ctx = next_logical_task(first)
        task_key = task_queue_label(logical_task)
        try:
            t0 = time.perf_counter()
            prepared_song = prepare_song(logical_task)
            bind_bundle_song(prepared_song, first, repeat_ctx)
            prepared.append(prepared_song)
            prepared_count += 1
            stage_profiler.record(
                "prep",
                time.perf_counter() - t0,
                cpu_seconds=getattr(prepared_song.runtime.prep, "cpu_prep_s", None),
                song=task_key,
            )
        except Exception as exc:
            payload = build_native_task_error_payload(
                song_name=str(song_name),
                queue_key=str(task_key),
                exc=exc,
                trace=traceback.format_exc(),
                suppress_progress=repeat_ctx is not None,
            )
            post(payload)
            if repeat_ctx is not None:
                advance_bundle(first, song_name=str(song_name), failed=True)
            else:
                mark_song_completed(
                    completed_songs=completed_songs,
                    task_key=task_key,
                    song_name=song_name,
                    memory_resume_tracker=memory_resume_tracker,
                )
    return int(prepared_count)
