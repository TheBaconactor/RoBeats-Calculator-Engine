"""Consolidated lifecycle helpers for the native in-flight optimizer."""

from __future__ import annotations

import concurrent.futures
import logging
import queue
import threading
import time
import traceback
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from gear_optimizer.core.parsing import env_flag, env_get
from gear_optimizer.domain.jobs import (
    extract_repeat_bundle,
    is_repeat_context,
    materialize_repeat_task,
    task_queue_label,
    task_song_name,
)
from gear_optimizer.solver.gpu_executor import get_gpu_executor
from gear_optimizer.solver.gpu_service import GpuServiceClient
from gear_optimizer.solver.native_inflight_completion import mark_song_completed
from gear_optimizer.solver.native_inflight_config import inflight_shutdown_debug_enabled
from gear_optimizer.solver.native_inflight_result_events import build_native_task_error_payload
from gear_optimizer.solver.native_inflight_scheduler import closed_loop_bubble_kpi
from gear_optimizer.solver.native_inflight_types import NativeSong, native_song_label

logger = logging.getLogger(__name__)

ProgressCallback = Callable[..., Any]


def _emit_startup_status(progress_cb: ProgressCallback | None, status: str) -> None:
    if progress_cb is None:
        return
    try:
        progress_cb(completed_delta=0, failed_delta=0, record_info={"status": status})
    except Exception as e:
        logger.debug(f"native_inflight_lifecycle:_emit_startup_status: {e}")


def start_native_inflight_gpu_client(icfg, *, progress_cb: ProgressCallback | None = None):
    """Start the native GPU executor and return its service client."""
    gpu_executor = get_gpu_executor()
    _emit_startup_status(progress_cb, "GPU init (Taichi/Vulkan)")
    gpu_executor.start(in_process=True)

    # GPU readiness includes Taichi/Vulkan init plus configured warmups. On cold
    # Windows/Vulkan caches this can be minute-scale; do not queue work behind
    # an owner that is not accepting requests yet.
    init_timeout = float(icfg.runtime.gpu_executor_init_timeout_sec)
    if not gpu_executor.wait_until_ready(timeout=init_timeout):
        err = getattr(gpu_executor, "last_init_error", None)
        msg = "[InFlight] GPU executor Taichi init failed or timed out"
        if err:
            msg = f"{msg} ({err})"
        try:
            gpu_executor.stop()
        except Exception as e:
            logger.debug(f"native_inflight_lifecycle:start_native_inflight_gpu_client: {e}")
        raise RuntimeError(msg)

    _emit_startup_status(progress_cb, "GPU warmup (Taichi JIT)")
    gpu_client = GpuServiceClient(gpu_executor)
    gpu_client.start(start_executor=False)
    return gpu_executor, gpu_client


@dataclass
class CachedRuntimeSignal:
    callback: Callable[[], bool] | None
    poll_interval_s: float = 0.05
    next_check_mono: float = 0.0
    cached_requested: bool = False
    monotonic: Callable[[], float] = field(default=time.monotonic, repr=False)

    def requested(self, now_mono: float | None = None) -> bool:
        if self.cached_requested:
            return True
        if self.callback is None or not callable(self.callback):
            return False
        now_val = float(self.monotonic() if now_mono is None else now_mono)
        if now_val < float(self.next_check_mono):
            return False
        self.cached_requested = bool(self.callback())
        if self.cached_requested:
            return True
        self.next_check_mono = now_val + float(self.poll_interval_s)
        return False


@dataclass
class GpuAbortRequester:
    gpu_executor: Any
    requested_once: bool = False

    def request(self, reason: str) -> bool:
        if self.requested_once:
            return False
        self.requested_once = True
        try:
            self.gpu_executor.request_abort(str(reason or "stop requested"))
        except Exception as e:
            logger.debug(f"native_inflight_lifecycle:GpuAbortRequester.request: {e}")
        return True


def is_stop_abort_exception(exc: BaseException) -> bool:
    if isinstance(exc, concurrent.futures.CancelledError):
        return True
    try:
        msg = str(exc or "")
    except Exception as e:
        logger.debug(f"native_inflight_lifecycle:is_stop_abort_exception: {e}")
        msg = ""
    return "GpuExecutor aborted:" in msg


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


def build_abort_queue_snapshot(
    *,
    pending_tasks: int,
    prepared: int,
    prep_inflight: int,
    ga_inflight: int,
    decode_inflight: int,
    pending_fg: int,
    fg_prep: int,
    fg_futures: int,
) -> str:
    return (
        f"pending={int(pending_tasks)} prepared={int(prepared)} prep_inflight={int(prep_inflight)} "
        f"ga_inflight={int(ga_inflight)} decode_inflight={int(decode_inflight)} "
        f"pending_fg={int(pending_fg)} fg_prep={int(fg_prep)} fg_futures={int(fg_futures)}"
    )


def native_abort_log_path() -> Path | None:
    try:
        from gear_optimizer.core.constants import PATHS

        return Path(PATHS.bin_path("inflight_native_abort.log"))
    except Exception as e:
        logger.debug(f"native_inflight_lifecycle:native_abort_log_path: {e}")
        return None


def append_native_abort_log(
    exc: Exception,
    *,
    snapshot: str,
    trace: str,
    path: str | Path | None = None,
    timestamp: str | None = None,
) -> bool:
    log_path = Path(path) if path is not None else native_abort_log_path()
    if log_path is None:
        return False

    try:
        ts = str(timestamp or time.strftime("%Y-%m-%d %H:%M:%S"))
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(f"\n[{ts}] {type(exc).__name__}: {exc}\n")
            fh.write(str(snapshot) + "\n")
            fh.write(str(trace) + "\n")
        return True
    except Exception as e:
        logger.debug(f"native_inflight_lifecycle:append_native_abort_log: {e}")
        return False


def log_native_abort(
    exc: Exception,
    *,
    pending_tasks: int,
    prepared: int,
    prep_inflight: int,
    ga_inflight: int,
    decode_inflight: int,
    pending_fg: int,
    fg_prep: int,
    fg_futures: int,
    trace: str,
    path: str | Path | None = None,
    timestamp: str | None = None,
) -> bool:
    try:
        snapshot = build_abort_queue_snapshot(
            pending_tasks=pending_tasks,
            prepared=prepared,
            prep_inflight=prep_inflight,
            ga_inflight=ga_inflight,
            decode_inflight=decode_inflight,
            pending_fg=pending_fg,
            fg_prep=fg_prep,
            fg_futures=fg_futures,
        )
        return append_native_abort_log(exc, snapshot=snapshot, trace=trace, path=path, timestamp=timestamp)
    except Exception as e:
        logger.debug(f"native_inflight_lifecycle:log_native_abort: {e}")
        return False


def _shutdown_step(label: str, action: Callable[[], None], *, shutdown_debug: bool) -> None:
    try:
        if shutdown_debug:
            logger.debug("[InFlight][SHUTDOWN] %s", label)
        action()
    except Exception as e:
        logger.debug(f"native_inflight_lifecycle:_shutdown_step: {e}")


def shutdown_native_inflight_resources(
    *,
    fg_pipeline,
    decode_queue,
    db_persistence=None,
    cpu_prewarm_queue,
    prep_queue,
    post_sender,
    gpu_client,
    gpu_executor,
) -> None:
    """Shutdown native in-flight resources in dependency order."""
    shutdown_debug = inflight_shutdown_debug_enabled()
    _shutdown_step(
        "fg_executor.shutdown",
        lambda: fg_pipeline.shutdown_fg(wait=True, cancel_futures=True),
        shutdown_debug=shutdown_debug,
    )
    _shutdown_step(
        "decode_executor.shutdown",
        lambda: decode_queue.shutdown(wait=True, cancel_futures=True),
        shutdown_debug=shutdown_debug,
    )
    if db_persistence is not None:
        _shutdown_step(
            "db_prefetch.shutdown",
            lambda: db_persistence.shutdown_prefetch(wait=True, cancel_futures=True),
            shutdown_debug=shutdown_debug,
        )
    _shutdown_step(
        "fg_prep_executor.shutdown",
        lambda: fg_pipeline.shutdown_prep(wait=True, cancel_futures=True),
        shutdown_debug=shutdown_debug,
    )
    _shutdown_step(
        "cpu_prewarm_executor.shutdown",
        lambda: cpu_prewarm_queue.shutdown(wait=True, cancel_futures=True),
        shutdown_debug=shutdown_debug,
    )
    _shutdown_step(
        "prep_executor.shutdown",
        lambda: prep_queue.shutdown(wait=True, cancel_futures=True),
        shutdown_debug=shutdown_debug,
    )
    if post_sender is not None:
        _shutdown_step("post_sender.close", lambda: post_sender.close(timeout=10.0), shutdown_debug=shutdown_debug)
    _shutdown_step("gpu_client.close", lambda: gpu_client.close(timeout=2.0), shutdown_debug=shutdown_debug)

    def _stop_gpu_executor_if_running() -> None:
        if gpu_executor.is_running:
            gpu_executor.stop()

    _shutdown_step("gpu_executor.stop", _stop_gpu_executor_if_running, shutdown_debug=shutdown_debug)


class PostSender:
    def __init__(self, post_queue, *, stop_requested=None) -> None:
        self._post_queue = post_queue
        self._stop_requested = stop_requested
        backlog = 0
        try:
            backlog = int(env_get("POST_LOCAL_BACKLOG", backlog))
        except Exception as e:
            logger.debug(f"native_inflight_lifecycle:PostSender.__init__: {e}")
            backlog = 0
        backlog = int(backlog)
        if backlog < 0:
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
        lane_fill_hold_count: int = 0,
        target_song_lanes: int = 0,
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
            "icfg.target_song_lanes": int(target_song_lanes),
            "lane_fill_hold_count": int(lane_fill_hold_count),
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
        cpu_prewarm_inflight_count: int,
        decode_inflight_count: int,
        pending_fg_count: int,
        fg_prep_inflight_count: int,
        ga_inflight_count: int,
        fg_futures_count: int,
        last_progress: float,
        oldest_fg_wait_s: float = 0.0,
        lane_fill_hold_count: int = 0,
        target_song_lanes: int = 0,
    ) -> dict[str, float | int]:
        backlog_count = int(
            prepared_count
            + pending_tasks_count
            + prep_inflight_count
            + cpu_prewarm_inflight_count
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
            lane_fill_hold_count=int(lane_fill_hold_count),
            target_song_lanes=int(target_song_lanes),
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

    def summary(self, *, active_song_lanes: int, target_song_lanes: int) -> dict[str, float | int]:
        return {
            "bubble_total_idle_sec": float(self.total_idle_s),
            "bubble_peak_kpi": float(self.peak_kpi),
            "bubble_peak_ready_ga": int(self.peak_ready_ga),
            "bubble_peak_ready_fg": int(self.peak_ready_fg),
            "bubble_peak_backlog": int(self.peak_backlog),
            "bubble_peak_oldest_fg_wait_sec": float(self.peak_oldest_fg_wait_s),
            "active_song_lanes": int(active_song_lanes),
            "icfg.target_song_lanes": int(target_song_lanes),
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


@dataclass(frozen=True)
class CpuPrewarmCompletion:
    song: NativeSong
    submit_t0: float
    label: str
    error: Exception | None = None


class CpuPrewarmQueue:
    def __init__(
        self,
        *,
        max_workers: int,
        lookahead: int,
        prewarm_fn: Callable[[NativeSong], None],
        label_for_song: Callable[[NativeSong], str] | None = None,
    ) -> None:
        self.executor = (
            concurrent.futures.ThreadPoolExecutor(
                max_workers=max(1, int(max_workers)),
                thread_name_prefix="CPUPrewarm",
            )
            if int(max_workers) > 0
            else None
        )
        self.lookahead = max(0, int(lookahead))
        self.prewarm_fn = prewarm_fn
        self.label_for_song = label_for_song or self.default_label_for_song
        self.inflight: deque[tuple[NativeSong, concurrent.futures.Future, float, str]] = deque()
        self.submitted: set[str] = set()

    def __len__(self) -> int:
        return int(len(self.inflight))

    def __bool__(self) -> bool:
        return bool(self.inflight)

    @staticmethod
    def default_label_for_song(song: NativeSong) -> str:
        return native_song_label(song, fallback_id=True)

    def submit(
        self,
        song: NativeSong,
        *,
        label: str | None = None,
        register_future: Callable[[concurrent.futures.Future | None], None],
    ) -> bool:
        if self.executor is None or int(self.lookahead) <= 0:
            return False
        task_key = str(label if label is not None else self.label_for_song(song))
        if task_key in self.submitted:
            return False
        if getattr(song.runtime.prep, "cpu_prewarm_future", None) is not None:
            return False
        self.submitted.add(task_key)
        try:
            future = self.executor.submit(self.prewarm_fn, song)
            song.runtime.prep.cpu_prewarm_future = future
            self.inflight.append((song, future, time.perf_counter(), task_key))
            register_future(future)
            return True
        except Exception as e:
            logger.debug(f"native_inflight_lifecycle:CpuPrewarmQueue.submit: {e}")
            self.submitted.discard(task_key)
            try:
                song.runtime.prep.cpu_prewarm_future = None
            except Exception as e:
                logger.debug(f"native_inflight_lifecycle:CpuPrewarmQueue.submit: {e}")
            return False

    def submit_prepared_backlog(
        self,
        prepared,
        *,
        register_future: Callable[[concurrent.futures.Future | None], None],
        extra_submit: Callable[[NativeSong], bool] | None = None,
    ) -> int:
        if int(self.lookahead) <= 0:
            return 0
        started = 0
        for idx, song in enumerate(list(prepared)):
            if idx >= int(self.lookahead):
                break
            if self.submit(song, register_future=register_future):
                started += 1
            if extra_submit is not None and extra_submit(song):
                started += 1
        return int(started)

    def finish_completed(self) -> list[CpuPrewarmCompletion]:
        completions: list[CpuPrewarmCompletion] = []
        for song, future, submit_t0, label in list(self.inflight):
            if not future.done():
                continue
            self.inflight.remove((song, future, submit_t0, label))
            error: Exception | None = None
            try:
                future.result()
            except Exception as exc:
                error = exc
                self.submitted.discard(str(label))
            finally:
                try:
                    song.runtime.prep.cpu_prewarm_future = None
                except Exception as e:
                    logger.debug(f"native_inflight_lifecycle:CpuPrewarmQueue.finish_completed: {e}")
            completions.append(
                CpuPrewarmCompletion(
                    song=song,
                    submit_t0=float(submit_t0),
                    label=str(label),
                    error=error,
                )
            )
        return completions

    def shutdown(self, *, wait: bool = True, cancel_futures: bool = True) -> None:
        if self.executor is not None:
            self.executor.shutdown(wait=wait, cancel_futures=cancel_futures)
