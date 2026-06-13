"""Completion tracking and deferred post helpers for native in-flight orchestration."""
from __future__ import annotations

import concurrent.futures
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from gear_optimizer.core.result_payloads import build_error_payload
from gear_optimizer.solver.inflight_wait import wait_for_completion_event
from gear_optimizer.solver.native_inflight_config import NativeSong
from gear_optimizer.solver.native_inflight_fg_payload import build_deferred_post_payload

logger = logging.getLogger(__name__)


@dataclass
class CompletionTracker:
    event: threading.Event = field(default_factory=threading.Event)
    lock: threading.Lock = field(default_factory=threading.Lock)
    ids: set[int] = field(default_factory=set)

    def register(self, fut: concurrent.futures.Future | None) -> bool:
        if fut is None:
            return False
        fut_id = int(id(fut))
        with self.lock:
            if fut_id in self.ids:
                return False
            self.ids.add(fut_id)

        def _on_done(_fut: concurrent.futures.Future, *, _fut_id: int = fut_id) -> None:
            self.unregister(_fut_id)
            self.event.set()

        try:
            fut.add_done_callback(_on_done)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            self.unregister(fut_id)
            self.event.set()
            return False
        return True

    def unregister(self, fut_id: int) -> None:
        with self.lock:
            self.ids.discard(int(fut_id))

    def is_set(self) -> bool:
        return bool(self.event.is_set())

    def wait(self, timeout_s: float, *, short_spin_s: float = 0.0) -> bool:
        return bool(
            wait_for_completion_event(
                self.event,
                timeout_s=float(timeout_s),
                short_spin_s=float(short_spin_s),
                perf_counter=time.perf_counter,
                sleep=time.sleep,
            )
        )

    def clear(self) -> None:
        self.event.clear()


def has_waitable_work(*queue_groups: Iterable[Any], pending_fg: Iterable[Any] = ()) -> bool:
    for group in queue_groups:
        try:
            if group:
                return True
        except Exception as e:
            logger.debug(f"native_inflight_orchestrator:has_waitable_work: {e}")
            continue
    _ = pending_fg
    return False


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
        try:
            bundle_completed_cb(key, completed_songs)
        except Exception as e:
            logger.debug(f"native_inflight_orchestrator:mark_song_completed: {e}")


def emit_deferred_post_payload(
    song: NativeSong,
    *,
    post: Callable[[dict], None],
    persist_pending_fg_job: bool,
    completed_songs: set[str],
    memory_resume_tracker=None,
    bundle_completed_cb=None,
    advance_bundle: Callable[..., None],
    progress_tracker=None,
    progress_cb=None,
) -> bool:
    if bool(getattr(song.runtime.post, "deferred_post_emitted", False)):
        return False
    post(build_deferred_post_payload(song, persist_pending_fg_job=bool(persist_pending_fg_job)))
    song.runtime.post.deferred_post_emitted = True
    bundle_parent = getattr(song.runtime.bundle, "bundle_parent_task", None)
    needs_fg_stage = getattr(song.runtime.fg, "fg_variants", None) is None
    if bundle_parent is not None and needs_fg_stage:
        song.runtime.bundle.bundle_wait_for_fg = True
    elif bundle_parent is not None:
        advance_bundle(
            bundle_parent,
            song_name=str(song.config.song_name),
            record_info=getattr(song.runtime.db, "record_info", None),
            failed=False,
        )
    elif needs_fg_stage:
        song.runtime.post.await_fg_completion_progress = True
    else:
        mark_song_completed(
            completed_songs=completed_songs,
            task_key=song.config.task_key,
            song_name=song.config.song_name,
            song_path=song.config.fp,
            memory_resume_tracker=memory_resume_tracker,
            bundle_completed_cb=bundle_completed_cb,
        )
        if progress_tracker is not None:
            progress_tracker.emit_done_song_progress(progress_cb, song)
    return True


def finish_deferred_fg_completion(
    song: NativeSong,
    *,
    completed_songs: set[str],
    memory_resume_tracker=None,
    bundle_completed_cb=None,
    advance_bundle: Callable[..., None],
    progress_tracker=None,
    progress_cb=None,
) -> bool:
    bundle_parent = getattr(song.runtime.bundle, "bundle_parent_task", None)
    if bundle_parent is not None and bool(getattr(song.runtime.bundle, "bundle_wait_for_fg", False)):
        advance_bundle(
            bundle_parent,
            song_name=str(song.config.song_name),
            record_info=getattr(song.runtime.db, "record_info", None),
            failed=False,
        )
        song.runtime.bundle.bundle_wait_for_fg = False
        return True
    if bool(getattr(song.runtime.post, "await_fg_completion_progress", False)):
        mark_song_completed(
            completed_songs=completed_songs,
            task_key=song.config.task_key,
            song_name=song.config.song_name,
            song_path=song.config.fp,
            memory_resume_tracker=memory_resume_tracker,
            bundle_completed_cb=bundle_completed_cb,
        )
        if progress_tracker is not None:
            progress_tracker.emit_done_song_progress(progress_cb, song)
        song.runtime.post.await_fg_completion_progress = False
        return True
    return False


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
    if bool(suppress_for_bundle) and getattr(song.runtime.bundle, "bundle_parent_task", None) is not None:
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
