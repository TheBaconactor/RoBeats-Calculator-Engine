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
    bundle_completed_cb=None,
) -> None:
    key = str(task_key)
    completed_songs.add(key)
    if memory_resume_tracker:
        memory_resume_tracker.mark_completed(song_path=song_path, song_name=str(song_name))
    if bundle_completed_cb is not None:
        bundle_completed_cb(key, completed_songs)


def build_native_song_error_payload(
    song: NativeSong,
    *,
    exc: Exception,
    trace: str,
    suppress_for_bundle: bool = True,
) -> dict[str, Any]:
    payload = build_error_payload(
        song_name=str(song.config.song_name),
        queue_key=str(song.config.task_key),
        queue_label=str(song.config.task_key),
        exc=exc,
        trace=trace,
    )
    if bool(suppress_for_bundle) and song.runtime.bundle.bundle_parent_task is not None:
        payload["_suppress_progress"] = True
    return payload


def build_native_task_error_payload(
    *,
    song_name: str,
    queue_key: str,
    exc: Exception,
    trace: str,
    queue_label: str | None = None,
    suppress_progress: bool = False,
) -> dict[str, Any]:
    key = str(queue_key)
    payload = build_error_payload(
        song_name=str(song_name),
        queue_key=key,
        queue_label=str(queue_label if queue_label is not None else key),
        exc=exc,
        trace=trace,
    )
    if bool(suppress_progress):
        payload["_suppress_progress"] = True
    return payload
