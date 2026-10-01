"""Completion tracking and result posting for native in-flight orchestration."""
from __future__ import annotations

from typing import Any

from gear_optimizer.core.result_payloads import build_error_payload
from gear_optimizer.solver.native_inflight_config import NativeSong


def mark_song_completed(
    *,
    completed_songs: set[str],
    task_key: str,
    song_name: str,
    song_path: str | None = None,
    memory_resume_tracker=None,
) -> None:
    key = str(task_key)
    completed_songs.add(key)
    if memory_resume_tracker:
        memory_resume_tracker.mark_completed(song_path=song_path, song_name=str(song_name))


def build_native_song_error_payload(
    song: NativeSong,
    *,
    exc: Exception,
    trace: str,
) -> dict[str, Any]:
    return build_error_payload(
        song_name=str(song.config.song_name),
        queue_key=str(song.config.task_key),
        queue_label=str(song.config.task_key),
        exc=exc,
        trace=trace,
    )


def build_native_task_error_payload(
    *,
    song_name: str,
    queue_key: str,
    exc: Exception,
    trace: str,
    queue_label: str | None = None,
) -> dict[str, Any]:
    key = str(queue_key)
    return build_error_payload(
        song_name=str(song_name),
        queue_key=key,
        queue_label=str(queue_label if queue_label is not None else key),
        exc=exc,
        trace=trace,
    )
