"""Queue and tracker helpers for native in-flight song preparation and posting."""
from __future__ import annotations

import concurrent.futures
import logging
import queue
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from gear_optimizer.core.parsing import env_flag, env_get
from gear_optimizer.domain.jobs import (
    extract_repeat_bundle,
    is_repeat_context,
    materialize_repeat_task,
    task_queue_label,
)
from gear_optimizer.solver.native_inflight_config import NativeSong
from gear_optimizer.solver.native_inflight_scheduler_policy import closed_loop_bubble_kpi

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SongPrepCompletion:
    task: tuple
    logical_task: tuple
    future: concurrent.futures.Future
    submit_t0: float


class SongPrepQueue:
    def __init__(self, *, max_workers: int, prep_fn: Callable[[tuple], Any]) -> None:
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max(1, int(max_workers)),
            thread_name_prefix="SongPrep",
        )
        self.prep_fn = prep_fn
        self.inflight: deque[tuple[tuple, tuple, concurrent.futures.Future, float]] = deque()

    def submit(
        self,
        task: tuple,
        logical_task: tuple,
        *,
        register_future: Callable[[concurrent.futures.Future | None], None],
    ) -> concurrent.futures.Future:
        future = self.executor.submit(self.prep_fn, logical_task)
        register_future(future)
        self.inflight.append((task, logical_task, future, time.perf_counter()))
        return future

    def pop_completed(self) -> list[SongPrepCompletion]:
        completions: list[SongPrepCompletion] = []
        for task, logical_task, future, submit_t0 in list(self.inflight):
            try:
                done = future.done()
            except Exception as e:
                logger.debug(f"native_inflight_lifecycle:SongPrepQueue.pop_completed: {e}")
                done = False
            if not done:
                continue
            self.inflight.remove((task, logical_task, future, submit_t0))
            completions.append(
                SongPrepCompletion(
                    task=task,
                    logical_task=logical_task,
                    future=future,
                    submit_t0=float(submit_t0),
                )
            )
        return completions

    def cancel_all(self) -> None:
        for _task, _logical_task, future, _submit_t0 in list(self.inflight):
            try:
                future.cancel()
            except Exception as e:
                logger.debug(f"native_inflight_lifecycle:SongPrepQueue.cancel_all: {e}")
        self.inflight.clear()

    def shutdown(self, *, wait: bool = True, cancel_futures: bool = True) -> None:
        self.executor.shutdown(wait=wait, cancel_futures=cancel_futures)


class PostSender:
    def __init__(self, post_queue, *, stop_requested=None) -> None:
        self._post_queue = post_queue
        self._stop_requested = stop_requested
        backlog = 0
        self._q: queue.Queue[Any] = queue.Queue(maxsize=backlog)
        self._sentinel = object()
        self._thread = threading.Thread(target=self._run, name="PostQueueSender", daemon=True)
        self._thread.start()

    def send(self, item: Any) -> None:
        if self._post_queue is None:
            return
        try:
            self._q.put(item, block=False)
        except queue.Full:
            self._q.put(item, block=True)

    def close(self, *, timeout: float = 30.0) -> None:
        if self._post_queue is None:
            return
        try:
            self._q.put(self._sentinel, block=True, timeout=max(0.0, float(timeout)))
        except Exception as e:
            logger.debug(f"native_inflight_lifecycle:PostSender.close: {e}")
            return
        try:
            self._thread.join(timeout=timeout)
        except Exception as e:
            logger.debug(f"native_inflight_lifecycle:PostSender.close: {e}")

    def _run(self) -> None:
        timing = env_flag("POST_TIMING")
        threshold_ms = 50.0
        try:
            threshold_ms = float(env_get("POST_TIMING_THRESHOLD_MS", str(threshold_ms)))
        except Exception as e:
            logger.debug(f"native_inflight_lifecycle:PostSender._run: {e}")
            threshold_ms = 50.0
        while True:
            item = self._q.get()
            if item is self._sentinel:
                return
            try:
                t0 = time.perf_counter()
                while True:
                    if self._stop_requested is not None and callable(self._stop_requested) and self._stop_requested():
                        return
                    try:
                        self._post_queue.put(item, block=True, timeout=0.5)
                        break
                    except Exception as e:
                        logger.debug(f"native_inflight_lifecycle:PostSender._run: {e}")
                        continue
                if timing:
                    ms = (time.perf_counter() - t0) * 1000.0
                    if ms >= threshold_ms:
                        kind = None
                        try:
                            kind = item.get("song") if isinstance(item, dict) else None
                        except Exception as e:
                            logger.debug(f"native_inflight_lifecycle:PostSender._run: {e}")
                            kind = None
                        prefix = f"[PostSender][TIMING] {kind} " if kind else "[PostSender][TIMING] "
                        print(f"{prefix}post_queue_put={ms:.1f}ms")
            except Exception as e:
                logger.debug(f"native_inflight_lifecycle:PostSender._run: {e}")


@dataclass
class BubbleTracker:
    total_idle_s: float = 0.0
    peak_kpi: float = 0.0
    peak_ready_ga: int = 0
    peak_ready_fg: int = 0
    peak_backlog: int = 0
    peak_oldest_fg_wait_s: float = 0.0
    active_started: float | None = None

    def snapshot(
        self,
        *,
        now_mono: float,
        ready_ga_count: int,
        ready_fg_count: int,
        backlog_count: int,
        active_song_lanes: int,
        gpu_idle: bool,
        last_progress: float,
        oldest_fg_wait_s: float = 0.0,
    ) -> dict[str, float | int]:
        idle_sec = max(0.0, float(now_mono) - float(last_progress)) if gpu_idle else 0.0
        bubble_kpi = closed_loop_bubble_kpi(
            idle_sec=float(idle_sec),
            ready_ga_count=int(ready_ga_count),
            ready_fg_count=int(ready_fg_count),
            backlog_count=int(backlog_count),
            oldest_fg_wait_s=float(oldest_fg_wait_s),
        )
        return {
            "idle_sec": float(idle_sec),
            "bubble_kpi": float(bubble_kpi),
            "ready_ga_count": int(ready_ga_count),
            "ready_fg_count": int(ready_fg_count),
            "active_song_lanes": int(active_song_lanes),
            "backlog_count": int(backlog_count),
            "gpu_idle": int(bool(gpu_idle)),
        }

    def snapshot_from_pipeline_counts(
        self,
        *,
        now_mono: float,
        prepared_count: int,
        ready_fg_count: int,
        active_song_lanes: int,
        pending_tasks_count: int,
        prep_inflight_count: int,
        decode_inflight_count: int,
        pending_fg_count: int,
        fg_prep_inflight_count: int,
        ga_inflight_count: int,
        fg_futures_count: int,
        last_progress: float,
        oldest_fg_wait_s: float = 0.0,
    ) -> dict[str, float | int]:
        backlog_count = int(
            prepared_count
            + pending_tasks_count
            + prep_inflight_count
            + decode_inflight_count
            + pending_fg_count
            + fg_prep_inflight_count
        )
        gpu_idle = int(ga_inflight_count) <= 0 and int(fg_futures_count) <= 0
        return self.snapshot(
            now_mono=float(now_mono),
            ready_ga_count=int(prepared_count),
            ready_fg_count=int(ready_fg_count),
            backlog_count=int(backlog_count),
            active_song_lanes=int(active_song_lanes),
            gpu_idle=bool(gpu_idle),
            last_progress=float(last_progress),
            oldest_fg_wait_s=float(oldest_fg_wait_s),
        )

    def note(self, snapshot: dict[str, float | int], *, now_mono: float, oldest_fg_wait_s: float) -> None:
        bubble_kpi = float(snapshot.get("bubble_kpi", 0.0) or 0.0)
        if bubble_kpi > 0.0:
            if self.active_started is None:
                self.active_started = float(now_mono)
            if bubble_kpi >= float(self.peak_kpi):
                self.peak_kpi = float(bubble_kpi)
                self.peak_ready_ga = int(snapshot.get("ready_ga_count", 0) or 0)
                self.peak_ready_fg = int(snapshot.get("ready_fg_count", 0) or 0)
                self.peak_backlog = int(snapshot.get("backlog_count", 0) or 0)
                self.peak_oldest_fg_wait_s = max(0.0, float(oldest_fg_wait_s))
            return
        if self.active_started is not None:
            self.total_idle_s += max(0.0, float(now_mono) - float(self.active_started))
            self.active_started = None

    def finish_active(self, *, now_mono: float) -> None:
        if self.active_started is None:
            return
        self.total_idle_s += max(0.0, float(now_mono) - float(self.active_started))
        self.active_started = None

    def summary(self, *, active_song_lanes: int) -> dict[str, float | int]:
        return {
            "bubble_total_idle_sec": float(self.total_idle_s),
            "bubble_peak_kpi": float(self.peak_kpi),
            "bubble_peak_ready_ga": int(self.peak_ready_ga),
            "bubble_peak_ready_fg": int(self.peak_ready_fg),
            "bubble_peak_backlog": int(self.peak_backlog),
            "bubble_peak_oldest_fg_wait_sec": float(self.peak_oldest_fg_wait_s),
            "active_song_lanes": int(active_song_lanes),
        }


class InflightBundleTracker:
    def __init__(
        self,
        *,
        pending_tasks: deque,
        completed_songs: set[str],
        memory_resume_tracker,
        bundle_completed_cb: Callable[[str, set[str]], object] | None,
        emit_progress: Callable,
    ) -> None:
        self.pending_tasks = pending_tasks
        self.completed_songs = completed_songs
        self.memory_resume_tracker = memory_resume_tracker
        self.bundle_completed_cb = bundle_completed_cb
        self.emit_progress = emit_progress
        self.progress: dict[int, int] = {}

    @staticmethod
    def bundle_runs(task: tuple) -> list[dict]:
        bundle = extract_repeat_bundle(task)
        if not isinstance(bundle, dict):
            return []
        runs = bundle.get("runs")
        if not isinstance(runs, list):
            return []
        out: list[dict] = []
        for ctx in runs:
            if is_repeat_context(ctx):
                out.append(dict(ctx))
        return out

    def next_logical_task(self, task: tuple) -> tuple[tuple, dict | None]:
        runs = self.bundle_runs(task)
        if not runs:
            return task, None
        cursor = max(0, int(self.progress.get(id(task), 0)))
        if cursor >= len(runs):
            cursor = len(runs) - 1
        repeat_ctx = dict(runs[cursor])
        return materialize_repeat_task(task, repeat_ctx), repeat_ctx

    def bind_song(self, song: NativeSong, parent_task: tuple, repeat_ctx: dict | None) -> None:
        if repeat_ctx is None or not self.bundle_runs(parent_task):
            return
        song.runtime.bundle.bundle_parent_task = parent_task
        song.runtime.bundle.bundle_task_key = task_queue_label(parent_task)
        try:
            song.runtime.bundle.bundle_repeat_index = int(repeat_ctx.get("repeat_index") or 0)
            song.runtime.bundle.bundle_repeat_total = int(repeat_ctx.get("repeat_total") or 0)
        except Exception as e:
            logger.debug(f"native_inflight_lifecycle:InflightBundleTracker.bind_song: {e}")
            song.runtime.bundle.bundle_repeat_index = 0
            song.runtime.bundle.bundle_repeat_total = 0

    def advance(
        self,
        parent_task: tuple,
        *,
        song_name: str,
        record_info: dict | None = None,
        failed: bool = False,
    ) -> bool:
        runs = self.bundle_runs(parent_task)
        if not runs:
            return False
        next_idx = max(0, int(self.progress.get(id(parent_task), 0))) + 1
        self.progress[id(parent_task)] = int(next_idx)
        info: dict = {}
        if isinstance(record_info, dict):
            try:
                info = dict(record_info)
            except Exception as e:
                logger.debug(f"native_inflight_lifecycle:InflightBundleTracker.advance: {e}")
                info = {}
        repeat_label = None
        try:
            ctx = runs[int(next_idx) - 1] if int(next_idx) > 0 and int(next_idx) <= len(runs) else None
            if is_repeat_context(ctx):
                ridx = int(ctx.get("repeat_index") or next_idx)
                rtotal = int(ctx.get("repeat_total") or len(runs))
                if ridx > 0 and rtotal > 1:
                    repeat_label = f"{song_name} (Run {ridx}/{rtotal})"
        except Exception as e:
            logger.debug(f"native_inflight_lifecycle:InflightBundleTracker.advance: {e}")
            repeat_label = None
        info.setdefault("song", repeat_label or song_name)
        info.setdefault("status", "FAILED" if failed else "DONE")
        self.emit_progress(
            completed_delta=1,
            failed_delta=1 if failed else 0,
            record_info=info,
        )
        if next_idx < len(runs):
            self.pending_tasks.appendleft(parent_task)
            return True
        bundle_key = task_queue_label(parent_task)
        self.completed_songs.add(bundle_key)
        if self.memory_resume_tracker:
            self.memory_resume_tracker.mark_completed(song_name)
        if self.bundle_completed_cb is not None:
            try:
                self.bundle_completed_cb(bundle_key, self.completed_songs)
            except Exception as e:
                logger.debug(f"native_inflight_lifecycle:InflightBundleTracker.advance: {e}")
        return True
