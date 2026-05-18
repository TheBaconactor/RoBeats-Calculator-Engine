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
from gear_optimizer.solver.native_inflight_config import inflight_shutdown_debug_enabled

from gear_optimizer.solver.native_inflight_config import NativeSong, native_song_label

logger = logging.getLogger(__name__)

ProgressCallback = Callable[..., Any]


def build_native_task_error_payload(*args, **kwargs):
    from gear_optimizer.solver.native_inflight_orchestrator import build_native_task_error_payload as _impl

    return _impl(*args, **kwargs)


def mark_song_completed(*args, **kwargs):
    from gear_optimizer.solver.native_inflight_orchestrator import mark_song_completed as _impl

    return _impl(*args, **kwargs)


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
            song.runtime.prep.cpu_prewarm_future = None
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
                song.runtime.prep.cpu_prewarm_future = None
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

# ---- merged from native_inflight_lifecycle.py ----


import logging
import time
from collections import OrderedDict
from typing import Optional

import numpy as np

from gear_optimizer.core.config import (
    GASettings as GARuntimeSettings,
    read_fg_candidate_limit,
)
from gear_optimizer.core.color_flags import build_color_flags
from gear_optimizer.core.constants import FG_CANDIDATE_LIMIT, LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.core.gem_defs import UserGemsSettings
from gear_optimizer.core.utils import cfg_from_dict
from gear_optimizer.domain.jobs import seed_plan_from_song_job, task_tuple_to_legacy_view
from gear_optimizer.solver.base_stats import build_base_fixed_stats_array
from gear_optimizer.solver.inflight_utils import (
    _truthy,
)
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.solver.song_preparation import build_prepared_song_core
from gear_optimizer.solver.native_inflight_pipeline import thread_cpu_time_s
from gear_optimizer.solver.native_inflight_config import (
    NativeSongConfig,
    NativeSongGPUInputs,
    NativeSongDBState,
    NativeSongRuntimeState,
)

logger = logging.getLogger(__name__)


_POOL_CACHE_MAX = 32
_REGISTRY_CACHE_MAX = 32
_INIT_HEURISTIC_CACHE_MAX = 64
_PREP_CACHE_LOCK = threading.Lock()
_POOL_CACHE: "OrderedDict[tuple[str, str, tuple[str, ...]], tuple[list, list]]" = OrderedDict()
_REGISTRY_GPU_CACHE: "OrderedDict[tuple[str, str, tuple[str, ...]], tuple[ItemRegistry, dict]]" = OrderedDict()
_INIT_HEURISTIC_TOPK_CACHE: "OrderedDict[tuple[tuple[str, str, tuple[str, ...]], int], np.ndarray]" = OrderedDict()

# Optional cache hit/miss stats (helps tune CPU requirements on low-end machines).
_CACHE_STATS = {
    "pools_hit": 0,
    "pools_miss": 0,
    "registry_hit": 0,
    "registry_miss": 0,
    "heur_hit": 0,
    "heur_miss": 0,
}
_CACHE_STATS_LOCK = threading.Lock()
_CACHE_STATS_LAST_EMIT = 0.0


def _lru_get(cache: OrderedDict, key: tuple):
    try:
        value = cache.get(key)
    except Exception as e:
        logger.debug(f"native_inflight_lifecycle:_lru_get: {e}")
        return None
    if value is not None:
        try:
            cache.move_to_end(key)
        except Exception as e:
            logger.debug(f"native_inflight_lifecycle:_lru_get: {e}")
    return value


def _lru_put(cache: OrderedDict, key: tuple, value, *, maxsize: int) -> None:
    try:
        cache[key] = value
        cache.move_to_end(key)
    except Exception as e:
        logger.debug(f"native_inflight_lifecycle:_lru_put: {e}")
        return
    try:
        while len(cache) > int(maxsize):
            cache.popitem(last=False)
    except Exception as e:
        logger.debug(f"native_inflight_lifecycle:_lru_put: {e}")


def _cache_stats_enabled() -> bool:
    return _truthy(env_get("INFLIGHT_CACHE_STATS", "0"))


def _cache_stats_emit_interval_s() -> float:
    try:
        return float(env_get("INFLIGHT_CACHE_STATS_EMIT_SEC", "30") or "30")
    except Exception as e:
        logger.debug(f"native_inflight_lifecycle:_cache_stats_emit_interval_s: {e}")
        return 30.0


def _cache_stats_inc(key: str) -> None:
    try:
        with _CACHE_STATS_LOCK:
            _CACHE_STATS[key] = int(_CACHE_STATS.get(key, 0) or 0) + 1
    except Exception as e:
        logger.debug(f"native_inflight_lifecycle:_cache_stats_inc: {e}")
        return


def _cache_stats_maybe_emit() -> None:
    if not _cache_stats_enabled():
        return
    interval = float(_cache_stats_emit_interval_s())
    if interval <= 0:
        return
    now = time.monotonic()
    global _CACHE_STATS_LAST_EMIT
    try:
        with _CACHE_STATS_LOCK:
            if (now - float(_CACHE_STATS_LAST_EMIT)) < interval:
                return
            _CACHE_STATS_LAST_EMIT = now
            snap = dict(_CACHE_STATS)
    except Exception as e:
        logger.debug(f"native_inflight_lifecycle:_cache_stats_maybe_emit: {e}")
        return
    try:
        pools_h = int(snap.get("pools_hit", 0) or 0)
        pools_m = int(snap.get("pools_miss", 0) or 0)
        reg_h = int(snap.get("registry_hit", 0) or 0)
        reg_m = int(snap.get("registry_miss", 0) or 0)
        heur_h = int(snap.get("heur_hit", 0) or 0)
        heur_m = int(snap.get("heur_miss", 0) or 0)
        logger.debug(
            "[InFlight][CacheStats] pools hit=%s miss=%s | registry hit=%s miss=%s | heur_topk hit=%s miss=%s",
            pools_h,
            pools_m,
            reg_h,
            reg_m,
            heur_h,
            heur_m,
        )
    except Exception as e:
        logger.debug(f"native_inflight_lifecycle:_cache_stats_maybe_emit: {e}")


def prepare_native_song(task: tuple) -> NativeSong:
    cpu_t0 = thread_cpu_time_s()
    from gear_optimizer.core.constants import GA_POPULATION_SIZE
    from gear_optimizer.helpers.ga_helpers import initialize_pools

    task_view = task_tuple_to_legacy_view(task)
    job = task_view.job
    seed_plan = seed_plan_from_song_job(job)
    task_key = seed_plan.queue_label
    ga_seed = seed_plan.ga_seed
    run_context = task_view.context
    fp = job.file_path
    found_song_name = job.song_name
    effective_difficulty = job.difficulty
    cfg_dict = run_context.cfg_dict
    paths = run_context.paths
    ref_arrays = run_context.ref_arrays
    all_gears = run_context.all_gears
    all_minis = run_context.all_minis
    gears_by_name = run_context.gears_by_name
    minis_by_name = run_context.minis_by_name
    ga_depth = run_context.ga_depth
    fg_debug = run_context.fg_debug

    cfg = cfg_from_dict(cfg_dict)

    prepared_core = build_prepared_song_core(
        fp=fp,
        found_song_name=found_song_name,
        cfg_dict=cfg_dict,
        paths=paths,
        gears_by_name=gears_by_name,
        minis_by_name=minis_by_name,
        cfg=cfg,
        allow_fallback=False,
        cache_db_context=True,
    )
    calc_song = prepared_core.calc_song
    meta_primary_color = prepared_core.meta_primary_color
    meta_secondary_color = prepared_core.meta_secondary_color
    prepared_config = prepared_core.prepared_config
    ga_settings = prepared_config.ga_settings
    fixed_stats = prepared_config.fixed_stats
    current_gear_list = prepared_config.current_gear_list
    current_mini_list = prepared_config.current_mini_list
    force_greats_config = prepared_config.force_greats_config
    manual_force_greats = prepared_config.manual_force_greats

    db_context = prepared_core.db_context
    db_key = db_context.db_key
    prev_record = db_context.prev_record
    db_best_score = db_context.db_best_score
    db_best_fg_score = db_context.db_best_fg_score
    attempt_lifetime = db_context.attempt_lifetime
    prev_attempts_first = db_context.prev_attempts_first
    db_baseline_valid = db_context.db_baseline_valid

    p_color = calc_song.get("metadata", {}).get("Primary Color", "Rush")
    s_color = calc_song.get("metadata", {}).get("Secondary Color", "")
    selected_color = p_color
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]

    pool_key = (str(p_color), str(s_color), tuple(slots))
    with _PREP_CACHE_LOCK:
        cached_pools = _lru_get(_POOL_CACHE, pool_key)
    if cached_pools is None:
        _cache_stats_inc("pools_miss")
        pools = initialize_pools(all_gears, all_minis, p_color, slots, s_color=s_color)
        if pools is None:
            raise RuntimeError("initialize_pools returned None")
        if len(pools) == 4:
            gear_pool, mini_pool, _total_before, _total_after = pools
        else:
            gear_pool, mini_pool, _total_before, _total_after, _whitelisted_minis = pools
        if gear_pool is None:
            raise RuntimeError("initialize_pools failed (gear_pool is None)")
        with _PREP_CACHE_LOCK:
            _lru_put(_POOL_CACHE, pool_key, (gear_pool, mini_pool), maxsize=_POOL_CACHE_MAX)
    else:
        _cache_stats_inc("pools_hit")
        gear_pool, mini_pool = cached_pools

    with _PREP_CACHE_LOCK:
        cached_registry = _lru_get(_REGISTRY_GPU_CACHE, pool_key)
    if cached_registry is None:
        _cache_stats_inc("registry_miss")
        registry = ItemRegistry(gear_pool, mini_pool, slots)
        gpu_data = registry.to_gpu_arrays()
        with _PREP_CACHE_LOCK:
            _lru_put(_REGISTRY_GPU_CACHE, pool_key, (registry, gpu_data), maxsize=_REGISTRY_CACHE_MAX)
    else:
        _cache_stats_inc("registry_hit")
        registry, gpu_data = cached_registry
    _cache_stats_maybe_emit()

    fg_candidate_limit = read_fg_candidate_limit(
        cfg,
        default=FG_CANDIDATE_LIMIT,
        min_limit=LOADOUTS_PER_SONG_LIMIT,
    )
    ga_runtime_settings = GARuntimeSettings.from_config(cfg)
    user_gems = UserGemsSettings.from_config(cfg, selected_color=selected_color)
    cfg_data = {
        "selected_color": selected_color,
        "primary_color": str(p_color or ""),
        "secondary_color": str(s_color or ""),
        "use_gpu": True,
        "fg_candidate_limit": int(fg_candidate_limit),
        "user_ft": int(user_gems.fever_time),
        "user_ff": int(user_gems.fever_fill),
        "user_pp": int(user_gems.perfect_points),
        "user_cm": int(user_gems.combo_multiplier),
        "user_fm": int(user_gems.fever_multiplier),
        "static_elem_input": int(user_gems.static_element),
    }
    cfg_data["ga_convergence_trace_enabled"] = bool(ga_runtime_settings.convergence_trace)
    cfg_data["ga_convergence_trace_every"] = int(ga_runtime_settings.convergence_trace_every)
    cfg_data["ga_convergence_trace_out_dir"] = str(ga_runtime_settings.convergence_trace_out_dir)
    cfg_data["ga_convergence_trace_song_filter"] = str(ga_runtime_settings.convergence_trace_song_filter)
    cfg_data["ga_novelty_repair_attempts"] = int(ga_runtime_settings.novelty_repair_attempts)

    # ForceGreatsFinder runs after GA and needs per-candidate BaseStats for signature grouping.
    # The GPU-native GA decode step keeps full post-gem Stats optional so the critical
    # GA->FG handoff does not spend CPU rebuilding data that the FG grouping path does not use.
    cfg_data["fg_require_stats"] = True

    base_fixed_stats_arr, _ = build_base_fixed_stats_array(fixed_stats, cfg_data)

    tournament_k = int(ga_runtime_settings.tournament_k)
    mutation_rate = float(ga_runtime_settings.mutation_rate)
    immigrant_rate = float(ga_runtime_settings.immigrant_rate)

    num_runs = int(getattr(ga_settings, "multi_start", 1) or 1)
    if num_runs <= 0:
        num_runs = 1

    ga_depth = int(ga_depth or 0)
    if ga_depth <= 0:
        ga_depth = 1
    gens_per_run = max(1, (ga_depth + num_runs - 1) // num_runs)
    n_genomes = int(GA_POPULATION_SIZE)

    init_heuristic_topk: Optional[np.ndarray] = None
    init_heuristic_k = 0
    try:
        init_heuristic_k = int(str(env_get("GPU_GA_INIT_HEURISTIC_K", "64") or "64"))
    except Exception as e:
        logger.debug(f"native_inflight_lifecycle:prepare_native_song: {e}")
        init_heuristic_k = 64
    init_heuristic_k = max(0, int(init_heuristic_k))
    init_heuristic_copies = 25

    try:
        from gear_optimizer.solver.genetic_pipeline import build_ga_init_heuristic_topk

        if init_heuristic_k > 0:
            cache_key = (pool_key, int(init_heuristic_k))
            with _PREP_CACHE_LOCK:
                init_heuristic_topk = _lru_get(_INIT_HEURISTIC_TOPK_CACHE, cache_key)
            if init_heuristic_topk is None:
                _cache_stats_inc("heur_miss")
            else:
                _cache_stats_inc("heur_hit")

            if init_heuristic_topk is None:
                init_heuristic_topk = build_ga_init_heuristic_topk(
                    item_stats=gpu_data["item_stats"],
                    slot_start=gpu_data["slot_start"],
                    slot_count=gpu_data["slot_count"],
                    primary_color=str(p_color or ""),
                    secondary_color=str(s_color or ""),
                    heuristic_k=int(init_heuristic_k),
                    n_slots=9,
                )
                if init_heuristic_topk is not None:
                    with _PREP_CACHE_LOCK:
                        _lru_put(
                            _INIT_HEURISTIC_TOPK_CACHE,
                            cache_key,
                            np.asarray(init_heuristic_topk, dtype=np.int32),
                            maxsize=_INIT_HEURISTIC_CACHE_MAX,
                        )
    except Exception as e:
        logger.debug(f"native_inflight_lifecycle:prepare_native_song: {e}")
        init_heuristic_topk = None

    if init_heuristic_topk is None or init_heuristic_k <= 0:
        init_heuristic_topk = None
        init_heuristic_k = 0
        init_heuristic_copies = 0

    color_flags = build_color_flags(p_color, s_color, selected_color)

    elite_count = max(0, int(ga_runtime_settings.elite_count))

    song = NativeSong(
        config=NativeSongConfig(
            fp=str(fp),
            song_name=str(found_song_name),
            task_key=str(task_key),
            ga_seed=int(ga_seed) if ga_seed is not None else None,
            db_key=str(db_key),
            effective_difficulty=str(effective_difficulty),
            cfg_dict=cfg_dict,
            cfg=cfg,
            paths=paths,
            ga_depth=int(ga_depth),
            fg_debug=bool(fg_debug),
        ),
        gpu_inputs=NativeSongGPUInputs(
            ref_arrays=ref_arrays,
            all_gears=all_gears,
            all_minis=all_minis,
            gears_by_name=gears_by_name,
            minis_by_name=minis_by_name,
            calc_song=calc_song,
            meta_primary_color=meta_primary_color,
            meta_secondary_color=meta_secondary_color,
            fixed_stats=fixed_stats,
            current_gear_list=current_gear_list,
            current_mini_list=current_mini_list,
            force_greats_config=force_greats_config,
            manual_force_greats=bool(manual_force_greats),
            registry=registry,
            cfg_data=cfg_data,
            color_flags=color_flags,
            gens_per_run=int(gens_per_run),
            num_runs=int(num_runs),
            n_genomes=int(n_genomes),
            item_stats=gpu_data["item_stats"],
            slot_start=gpu_data["slot_start"],
            slot_count=gpu_data["slot_count"],
            base_fixed_stats_arr=np.asarray(base_fixed_stats_arr, dtype=np.int32),
            elite_count=int(elite_count),
            mutation_rate=float(mutation_rate),
            immigrant_rate=float(immigrant_rate),
            tournament_k=int(tournament_k),
            init_heuristic_topk=init_heuristic_topk,
            init_heuristic_k=int(init_heuristic_k),
            init_heuristic_copies=int(init_heuristic_copies),
        ),
        runtime=NativeSongRuntimeState(
            db=NativeSongDBState(
                prev_record=prev_record,
                db_best_score=int(db_best_score),
                attempt_lifetime=int(attempt_lifetime),
                prev_attempts_first=int(prev_attempts_first),
                db_best_fg_score=int(db_best_fg_score),
                db_baseline_valid=bool(db_baseline_valid),
            ),
        ),
    )
    song.runtime.prep.cpu_prep_s = max(0.0, thread_cpu_time_s() - float(cpu_t0))
    return song

# ---- merged from native_inflight_lifecycle.py ----


import threading
from dataclasses import dataclass, field
from typing import Any, Callable
import logging

from gear_optimizer.helpers.song_helpers.persistence import evaluate_progress_record_update
from gear_optimizer.core.utils import safe_int


logger = logging.getLogger(__name__)


@dataclass
class ProgressTracker:
    lock: threading.Lock = field(default_factory=threading.Lock)
    best: dict[str, tuple[int, int]] = field(default_factory=dict)
    valid: set[str] = field(default_factory=set)

    def snapshot(self, db_key: str) -> tuple[int, int, bool]:
        key = str(db_key or "").strip()
        if not key:
            return (0, 0, False)
        with self.lock:
            score0, fg0 = self.best.get(key, (0, 0))
            return (int(score0), int(fg0), key in self.valid)

    def update(
        self,
        db_key: str,
        *,
        best_score: int | None = None,
        best_fg: int | None = None,
        mark_valid: bool = False,
    ) -> None:
        key = str(db_key or "").strip()
        if not key:
            return
        try:
            score_new = int(best_score) if best_score is not None else None
        except (TypeError, ValueError):
            score_new = None
        try:
            fg_new = int(best_fg) if best_fg is not None else None
        except (TypeError, ValueError):
            fg_new = None
        with self.lock:
            score0, fg0 = self.best.get(key, (0, 0))
            if score_new is not None and score_new > int(score0):
                score0 = int(score_new)
            if fg_new is not None and fg_new > int(fg0):
                fg0 = int(fg_new)
            self.best[key] = (int(score0), int(fg0))
            if mark_valid:
                self.valid.add(key)

    def seed_valid_baseline(self, db_key: str, *, best_score: int, best_fg: int, baseline_valid: bool) -> None:
        if not bool(baseline_valid):
            return
        self.update(
            db_key,
            best_score=int(best_score),
            best_fg=int(best_fg),
            mark_valid=True,
        )

    def evaluate_record_update(
        self,
        db_key: str,
        best_data: dict,
        fg_variants,
        *,
        fg_only: bool = False,
    ) -> dict | None:
        prev_best_score, prev_best_fg, baseline_valid = self.snapshot(db_key)
        record_info = evaluate_progress_record_update(
            best_data or {},
            {"score": int(prev_best_score)},
            fg_variants or [],
            db_best_fg_score=int(prev_best_fg),
            baseline_valid=bool(baseline_valid),
            fg_only=bool(fg_only),
        )
        if isinstance(record_info, dict) and record_info.get("is_better"):
            self.update(
                db_key,
                best_score=int(record_info.get("score", 0) or 0),
                best_fg=int(record_info.get("best_fg_score_run", 0) or 0),
                mark_valid=bool(baseline_valid),
            )
        elif isinstance(record_info, dict) and record_info.get("is_fg_better"):
            self.update(
                db_key,
                best_fg=int(record_info.get("best_fg_score_run", 0) or 0),
                mark_valid=bool(baseline_valid),
            )
        return record_info

    @staticmethod
    def error_item_song_label(item: dict) -> Any:
        return (
            item.get("song")
            or item.get("_song_name")
            or item.get("song_name")
            or item.get("_queue_label")
            or item.get("_queue_key")
        )

    def emit_error_item_progress(self, progress_cb: Callable[..., Any] | None, item: Any) -> bool:
        if not isinstance(item, dict) or not item.get("_error") or bool(item.get("_suppress_progress")):
            return False
        try:
            song_label = self.error_item_song_label(item)
        except Exception as e:
            logger.debug(f"native_inflight_lifecycle:emit_error_item_progress: {e}")
            song_label = None
        self.emit_progress(
            progress_cb,
            completed_delta=1,
            failed_delta=1,
            record_info={"song": song_label, "status": "FAILED"},
        )
        return True

    @staticmethod
    def done_record_info_for_song(song: Any) -> dict | None:
        try:
            record_info = dict(getattr(song.runtime.db, "record_info", None) or {})
            record_info.setdefault("song", native_song_label(song))
            record_info.setdefault("status", "DONE")
            return record_info
        except Exception as e:
            logger.debug(f"native_inflight_lifecycle:done_record_info_for_song: {e}")
            return None

    def emit_done_song_progress(
        self,
        progress_cb: Callable[..., Any] | None,
        song: Any,
        *,
        completed_delta: int = 1,
    ) -> None:
        self.emit_progress(
            progress_cb,
            completed_delta=int(completed_delta),
            record_info=self.done_record_info_for_song(song),
        )

    def emit_progress(
        self,
        progress_cb: Callable[..., Any] | None,
        *,
        completed_delta: int = 0,
        failed_delta: int = 0,
        record_info: dict | None = None,
    ) -> None:
        if progress_cb is None:
            return
        try:
            progress_cb(
                completed_delta=completed_delta,
                failed_delta=failed_delta,
                record_info=record_info,
            )
        except Exception as e:
            logger.debug(f"native_inflight_lifecycle:emit_progress: {e}")
            return


class ActiveRuntimeProgressReporter:
    def __init__(self, emit_progress: Callable[..., Any]) -> None:
        self._emit_progress = emit_progress
        self.active_label = ""

    @staticmethod
    def active_song_label(
        *,
        ga_inflight,
        decode_inflight,
        fg_futures,
    ) -> str:
        for source_name, source in (
            ("ga", ga_inflight),
            ("decode", decode_inflight),
        ):
            try:
                if source:
                    return native_song_label(source[0])
            except Exception as e:
                logger.debug(f"native_inflight_lifecycle:active_song_label:{source_name}: {e}")
        try:
            if fg_futures:
                return native_song_label(fg_futures[0][0])
        except Exception as e:
            logger.debug(f"native_inflight_lifecycle:active_song_label:fg: {e}")
        return ""

    def emit(
        self,
        *,
        ga_inflight,
        decode_inflight,
        fg_futures,
        force: bool = False,
    ) -> None:
        song_label = self.active_song_label(
            ga_inflight=ga_inflight,
            decode_inflight=decode_inflight,
            fg_futures=fg_futures,
        )
        if not force and song_label == self.active_label:
            return
        self.active_label = str(song_label or "").strip()
        if not self.active_label:
            return
        self._emit_progress(
            completed_delta=0,
            failed_delta=0,
            record_info={"song": self.active_label, "status": "RUNNING"},
        )


def evaluate_fg_progress_record_update(song: Any, progress_tracker: ProgressTracker | None) -> dict | None:
    try:
        key = str(getattr(song.config, "db_key", "") or "").strip()
        prev_best_score = safe_int(getattr(song.runtime.db, "db_best_score", 0), 0)
        prev_best_fg = safe_int(getattr(song.runtime.db, "db_best_fg_score", 0), 0)
        baseline_valid = bool(getattr(song.runtime.db, "db_baseline_valid", True))
        if progress_tracker is not None and key:
            prev_best_score, prev_best_fg, baseline_valid = progress_tracker.snapshot(key)

        record_info = evaluate_progress_record_update(
            getattr(song.runtime.decode, "best_data", None) or {},
            {"score": int(prev_best_score)},
            getattr(song.runtime.fg, "fg_variants", None) or [],
            db_best_fg_score=int(prev_best_fg),
            baseline_valid=bool(baseline_valid),
            fg_only=True,
        )
    except (ValueError, TypeError, KeyError):
        return None

    if not isinstance(record_info, dict):
        return None

    record_info = dict(record_info)
    record_info.setdefault("song", native_song_label(song))
    if record_info.get("is_fg_better") and progress_tracker is not None:
        best_fg_new = safe_int(record_info.get("best_fg_score_run", 0), 0)
        if best_fg_new > 0:
            key = str(getattr(song.config, "db_key", "") or "").strip()
            if key:
                progress_tracker.update(
                    key,
                    best_fg=best_fg_new,
                    mark_valid=bool(baseline_valid),
                )
    return record_info

# ---- merged from native_inflight_lifecycle.py ----


import time
from dataclasses import dataclass, field
from typing import Any, Callable
import logging

from gear_optimizer.core.utils import safe_float



logger = logging.getLogger(__name__)


@dataclass
class GAQueueLimitController:
    base_limit: int
    pressure_window_s: float
    extra_free_on_slot_pressure: int
    fg_slot_reserve: int
    song_slot_limit: int
    monotonic: Callable[[], float] = field(default=time.monotonic, repr=False)
    _cache_key: tuple[bool, int, int, int, int] | None = field(default=None, init=False, repr=False)
    _cache_value: int = field(default=1, init=False, repr=False)

    def __post_init__(self) -> None:
        self.base_limit = max(1, int(self.base_limit))
        self.pressure_window_s = max(0.0, float(self.pressure_window_s))
        self.extra_free_on_slot_pressure = max(0, int(self.extra_free_on_slot_pressure))
        self.fg_slot_reserve = max(0, int(self.fg_slot_reserve))
        self.song_slot_limit = max(1, int(self.song_slot_limit))
        self._cache_value = int(self.base_limit)

    def effective_limit(self, *, last_slot_block_t: float | None) -> int:
        extra_free = 0
        slot_pressure_active = False

        if last_slot_block_t is not None and float(self.pressure_window_s) > 0.0:
            try:
                if (float(self.monotonic()) - float(last_slot_block_t)) <= float(self.pressure_window_s):
                    slot_pressure_active = True
                    extra_free = max(int(extra_free), int(self.extra_free_on_slot_pressure))
            except Exception as e:
                logger.debug(f"native_inflight_lifecycle:GAQueueLimitController.effective_limit: {e}")

        cache_key = (
            bool(slot_pressure_active),
            int(extra_free),
            int(self.fg_slot_reserve),
            int(self.song_slot_limit),
            int(self.base_limit),
        )
        if cache_key == self._cache_key:
            return int(self._cache_value)

        min_free = int(self.fg_slot_reserve) + int(extra_free)
        min_free = max(0, min(int(min_free), max(0, int(self.song_slot_limit) - 1)))
        limit_from_free = max(1, int(self.song_slot_limit) - int(min_free))
        self._cache_value = max(1, min(int(self.base_limit), int(limit_from_free)))
        self._cache_key = cache_key
        return int(self._cache_value)


def _song_lane_key(song: Any) -> str:
    try:
        return native_song_label(song)
    except Exception as e:
        logger.debug(f"native_inflight_lifecycle:_song_lane_key: {e}")
        return ""


def count_active_song_lanes(
    *,
    ga_inflight,
    decode_inflight,
    fg_active_keys,
) -> int:
    keys: set[str] = set()
    for song in ga_inflight:
        key = _song_lane_key(song)
        if key:
            keys.add(key)
    for song in decode_inflight:
        key = _song_lane_key(song)
        if key:
            keys.add(key)
    keys.update(str(key).strip() for key in fg_active_keys if str(key).strip())
    return int(len(keys))


def default_prime_target(*, inflight_limit: int, prep_limit: int, pending_count: int) -> int:
    """
    Pick a startup prep backlog large enough to avoid the first GA/FG feed bubble.

    For smaller in-flight runs, priming only `inflight_limit` songs tends to leave the
    GPU queue shallow while prep/decode workers are still spinning up. We bias toward
    a modest 4-8 song startup backlog, but always cap by the prep buffer and pending queue.
    """
    inflight_limit = int(inflight_limit)
    prep_limit = int(prep_limit)
    pending_count = int(pending_count)

    inflight_limit = max(1, inflight_limit)
    prep_limit = max(1, prep_limit)
    pending_count = max(0, pending_count)
    if pending_count <= 0:
        return 0

    target = max(inflight_limit, min(8, max(4, inflight_limit * 2)))
    return max(1, min(target, prep_limit, pending_count))


def read_prime_target(
    cfg0: Any,
    *,
    inflight_limit: int,
    prep_limit: int,
    pending_count: int,
) -> int:
    target = 0
    try:
        if cfg0 is not None:
            target = safe_int(cfg0.get("IterationEngine", "InFlight_PrimeTarget", fallback="0"), 0)
    except Exception as e:
        logger.debug(f"native_inflight_lifecycle:read_prime_target: {e}")
        target = 0

    raw = env_get("INFLIGHT_PRIME_TARGET")
    if raw is not None and str(raw).strip() != "":
        try:
            target = int(raw)
        except Exception as e:
            logger.debug(f"native_inflight_lifecycle:read_prime_target: {e}")

    if int(target) <= 0:
        return default_prime_target(
            inflight_limit=int(inflight_limit),
            prep_limit=int(prep_limit),
            pending_count=int(pending_count),
        )
    return max(0, min(int(target), int(prep_limit), int(pending_count)))


def read_fg_scheduler_mode() -> str:
    """
    In-flight scheduler is intentionally fixed to continuous mode.

    We removed backlog/drain scheduler options to keep runtime behavior
    deterministic and easier to reason about.
    """
    return "continuous"


def read_fg_ga_credit_budget(cfg0: Any, *, default_budget: int) -> tuple[int, bool]:
    """
    GA-credit budget used by continuous FG scheduler.

    Returns: (budget, explicit)
    - budget: effective positive integer
    - explicit: True when user explicitly set the budget (config/env), False when defaulted
    """
    budget = max(1, int(default_budget))
    explicit = False

    try:
        if cfg0 is not None:
            if cfg0.has_option("IterationEngine", "InFlight_FGGACreditBudget"):
                budget = safe_int(
                    cfg0.get("IterationEngine", "InFlight_FGGACreditBudget", fallback=str(budget)),
                    budget,
                )
                explicit = True
    except Exception as e:
        logger.debug(f"native_inflight_lifecycle:read_fg_ga_credit_budget: {e}")

    raw = env_get("INFLIGHT_FG_GA_CREDIT_BUDGET")
    if raw is not None and str(raw).strip() != "":
        try:
            budget = int(raw)
            explicit = True
        except Exception as e:
            logger.debug(f"native_inflight_lifecycle:read_fg_ga_credit_budget: {e}")

    return max(1, int(budget)), bool(explicit)


def read_continuous_ga_dispatch_burst(cfg0: Any, *, default_burst: int = 2) -> int:
    """
    Max GA submissions per scheduler cycle when continuous GA/FG interleaving is active.

    Lower values reduce GA burstiness and give FG more frequent chances to submit,
    which smooths GPU utilization without changing GA/FG scoring behavior.
    """
    burst = max(1, int(default_burst))
    try:
        if cfg0 is not None and cfg0.has_option("IterationEngine", "InFlight_ContinuousGABurst"):
            burst = safe_int(
                cfg0.get("IterationEngine", "InFlight_ContinuousGABurst", fallback=str(burst)),
                burst,
            )
    except Exception as e:
        logger.debug(f"native_inflight_lifecycle:read_continuous_ga_dispatch_burst: {e}")

    raw = env_get("INFLIGHT_CONTINUOUS_GA_BURST")
    if raw is not None and str(raw).strip() != "":
        try:
            burst = int(raw)
        except Exception as e:
            logger.debug(f"native_inflight_lifecycle:read_continuous_ga_dispatch_burst: {e}")

    return max(1, min(int(burst), 32))


def read_continuous_fg_adaptive_max_burst(cfg0: Any) -> int:
    """
    Upper bound for adaptive FG submit burst size in continuous mode.
    """
    max_burst = 3

    try:
        if cfg0 is not None:
            if cfg0.has_option("IterationEngine", "InFlight_FGAdaptiveMaxBurst"):
                max_burst = safe_int(
                    cfg0.get("IterationEngine", "InFlight_FGAdaptiveMaxBurst", fallback=str(max_burst)),
                    max_burst,
                )
    except Exception as e:
        logger.debug(f"native_inflight_lifecycle:read_continuous_fg_adaptive_max_burst: {e}")

    raw = env_get("INFLIGHT_FG_ADAPTIVE_MAX_BURST")
    if raw is not None and str(raw).strip() != "":
        try:
            max_burst = int(raw)
        except Exception as e:
            logger.debug(f"native_inflight_lifecycle:read_continuous_fg_adaptive_max_burst: {e}")

    return max(1, min(int(max_burst), 16))


def read_fg_slot_reserve(
    cfg0: Any,
    *,
    inflight_limit: int,
    song_slot_limit: int,
) -> int:
    """
    Reserve a dedicated song-slot partition for FG work.

    This prevents GA from consuming all song slots and creating slot-pressure oscillation
    when FG submissions need to acquire slots.
    """
    if int(inflight_limit) <= 1 or int(song_slot_limit) <= 1:
        return 0

    reserve = 1
    reserve_ratio = 0.20
    absolute_explicit = False

    try:
        if cfg0 is not None:
            if cfg0.has_option("IterationEngine", "InFlight_FGSlotReserve"):
                reserve = safe_int(cfg0.get("IterationEngine", "InFlight_FGSlotReserve", fallback="1"), 1)
                absolute_explicit = True
            elif cfg0.has_option("IterationEngine", "InFlight_FGSlotReserveRatio"):
                reserve_ratio = safe_float(
                    cfg0.get("IterationEngine", "InFlight_FGSlotReserveRatio", fallback=str(reserve_ratio)),
                    reserve_ratio,
                )
    except Exception as e:
        logger.debug(f"native_inflight_lifecycle:read_fg_slot_reserve: {e}")

    raw = env_get("INFLIGHT_FG_SLOT_RESERVE")
    if raw is not None and str(raw).strip() != "":
        try:
            reserve = int(raw)
            absolute_explicit = True
        except Exception as e:
            logger.debug(f"native_inflight_lifecycle:read_fg_slot_reserve: {e}")

    raw = env_get("INFLIGHT_FG_SLOT_RESERVE_RATIO")
    if raw is not None and str(raw).strip() != "":
        try:
            reserve_ratio = float(raw)
        except Exception as e:
            logger.debug(f"native_inflight_lifecycle:read_fg_slot_reserve: {e}")

    reserve_cap = max(1, min(max(1, int(song_slot_limit) - 1), max(1, int(inflight_limit))))
    if absolute_explicit:
        if int(reserve) <= 0:
            return 0
        return max(1, min(int(reserve), int(reserve_cap)))

    reserve_ratio = max(0.0, min(float(reserve_ratio), 0.90))
    ratio_slots = int(round(float(song_slot_limit) * float(reserve_ratio)))
    reserve = max(int(reserve), int(ratio_slots))
    return max(1, min(int(reserve), int(reserve_cap)))


def read_inflight_target_song_lanes(cfg0: Any, *, inflight_limit: int) -> int:
    """
    Target number of concurrently active song lanes for the single-owner pipeline.

    Default to two lanes whenever overlap is enabled so GA/FG can interleave across
    songs instead of collapsing back into a single-song phase train.
    """
    inflight_limit_i = max(1, int(inflight_limit))

    target = 2 if int(inflight_limit_i) > 1 else 1
    try:
        if cfg0 is not None and cfg0.has_option("IterationEngine", "InFlight_TargetSongLanes"):
            target = safe_int(
                cfg0.get("IterationEngine", "InFlight_TargetSongLanes", fallback=str(target)),
                target,
            )
    except Exception as e:
        logger.debug(f"native_inflight_lifecycle:read_inflight_target_song_lanes: {e}")

    raw = env_get("INFLIGHT_TARGET_SONG_LANES")
    if raw is not None and str(raw).strip() != "":
        try:
            target = int(raw)
        except Exception as e:
            logger.debug(f"native_inflight_lifecycle:read_inflight_target_song_lanes: {e}")

    return max(1, min(int(target), int(inflight_limit_i)))


def continuous_ga_warm_queue_limit(
    *,
    ga_queue_limit: int,
    inflight_limit: int,
    prepared_count: int,
    prep_inflight_count: int,
    decode_inflight_count: int,
    pending_fg_count: int,
    fg_prep_inflight_count: int,
    fg_inflight_count: int,
    target_song_lanes: int,
    active_song_lanes: int,
    dispatch_burst: int,
) -> int:
    """
    Keep startup GA warmup bounded without starving the continuous conveyor.

    The original continuous architecture worked best when GA could keep a healthy
    runway of future songs behind the currently visible FG lanes. The important
    protection is only at startup: before any decode/FG work exists, avoid
    front-loading an arbitrarily deep GA tail that hides the first ready FG.

    Once decode/FG work exists, return the full GA queue limit and rely on owner
    turn discipline to surface ready FG promptly. Clamping GA to the visible lane
    count once the conveyor is full underfeeds fast GPUs because downstream decode/FG prep
    latency can exceed a two-lane runway.
    """
    limit = max(1, int(ga_queue_limit))
    inflight_limit = max(1, int(inflight_limit))
    if inflight_limit <= 1:
        return limit

    target_lanes = max(1, min(int(target_song_lanes), int(inflight_limit)))
    burst = max(1, int(dispatch_burst))
    warm_limit = max(1, min(int(limit), max(int(target_lanes), min(int(inflight_limit), int(burst)))))
    handoff_limit = max(
        int(warm_limit),
        min(int(limit), max(int(target_lanes) * 2, int(target_lanes) + int(burst))),
    )

    if max(0, int(fg_inflight_count)) > 0:
        return int(limit)

    handoff_fg_work = (
        max(0, int(decode_inflight_count)) + max(0, int(pending_fg_count)) + max(0, int(fg_prep_inflight_count))
    )
    if handoff_fg_work > 0:
        # Decode/pending FG means the first FG handoff is approaching, but if we
        # immediately reopen GA to the full queue depth we can bury that first FG
        # owner turn behind a long GA tail. Keep a modest GA runway until FG has
        # actually surfaced onto the owner, then restore the full continuous
        # limit.
        return int(handoff_limit)

    staging_depth = max(0, int(prepared_count)) + max(0, int(prep_inflight_count))
    if staging_depth >= int(warm_limit):
        return int(warm_limit)
    return int(limit)


def continuous_fg_should_fill_song_lanes(
    *,
    target_song_lanes: int,
    active_song_lanes: int,
    ready_ga_count: int,
    pending_fg_count: int = 0,
    ready_fg_count: int = 0,
    blocked_on_slot: bool,
    no_ga_remaining: bool,
    oldest_wait_s: float,
    aging_trigger_s: float = 0.0,
    aging_hard_s: float,
) -> bool:
    """
    Prefer filling the next GA song lane before starting FG when we have immediate GA work.

    This turns the in-flight queue into a real two-lane conveyor on one GPU owner:
    keep song B entering GA while song A is already headed toward FG, unless FG is
    already runnable or has aged enough that fairness must override the lane-fill
    preference.
    """
    if int(target_song_lanes) <= 1:
        return False
    if int(active_song_lanes) >= int(target_song_lanes):
        return False
    if int(ready_ga_count) <= 0:
        return False
    if bool(blocked_on_slot) or bool(no_ga_remaining):
        return False
    if int(pending_fg_count) > 0 and int(ready_fg_count) > 0:
        return False
    if int(pending_fg_count) > 0 and float(aging_trigger_s) > 0.0 and float(oldest_wait_s) >= float(aging_trigger_s):
        return False
    if float(aging_hard_s) > 0.0 and float(oldest_wait_s) >= float(aging_hard_s):
        return False
    return True


def continuous_ga_should_yield_to_fg(
    *,
    pending_fg_count: int,
    ready_fg_count: int,
    fg_prep_inflight_count: int,
    fg_inflight_count: int,
    fg_worker_count: int,
    target_song_lanes: int,
    oldest_wait_s: float,
    aging_trigger_s: float,
    blocked_on_slot: bool,
) -> bool:
    """
    Stop GA admission when FG has become the limiting queue.

    This is deliberately an admission rule, not a scoring shortcut. Existing GA
    work may finish, but the submit loop yields to the FG scheduler before it
    adds more GA jobs once FG is ready. Active-but-unready FG prep is not a
    runnable GPU lane, so it must not stop GA admission by itself.
    """
    pending = max(0, int(pending_fg_count))
    ready = max(0, int(ready_fg_count))
    prep = max(0, int(fg_prep_inflight_count))
    fg_inflight = max(0, int(fg_inflight_count))
    fg_workers = max(1, int(fg_worker_count))
    fg_pressure = int(pending) + int(prep) + int(fg_inflight)
    if fg_pressure <= 0:
        return False

    if bool(blocked_on_slot):
        return True
    if fg_inflight >= fg_workers:
        return False
    if ready > 0:
        return True
    return False


def continuous_fg_should_start(
    *,
    pending_fg_count: int,
    ready_fg_count: int,
    ga_credit: int,
    oldest_wait_s: float,
    blocked_on_slot: bool,
    no_ga_remaining: bool,
    aging_trigger_s: float,
    aging_hard_s: float,
    ga_queue_limit: int,
    fg_slot_reserve: int,
) -> bool:
    if int(pending_fg_count) <= 0:
        return False
    if bool(no_ga_remaining):
        return True
    if bool(blocked_on_slot):
        return True
    # Treat `ready_fg_count` as a hint, not a hard gate. The conveyor's real
    # readiness check lives in `_pop_next_fg(...)`; gating here on an exact
    # count can defer runnable FG work behind a full GA drain if bookkeeping
    # lags the actual collect/prep state.
    return True


def continuous_fg_allow_not_ready(
    *,
    blocked_on_slot: bool,
    no_ga_remaining: bool,
) -> bool:
    """
    Decide whether a pending FG song may be handed to a worker before prep is done.

    During the final FG drain there is no GA work left to protect. Keeping those
    pending songs in the scheduler until their prep futures finish serializes the
    last CPU prep/first-submit window and can leave the GPU owner empty.
    """
    if bool(blocked_on_slot):
        return True
    return bool(no_ga_remaining)


def continuous_fg_submit_budget(
    *,
    pending_fg_count: int,
    ready_fg_count: int,
    fg_inflight_count: int,
    fg_workers: int,
    fg_batch_max: int,
    no_ga_remaining: bool,
    blocked_on_slot: bool,
    oldest_wait_s: float,
    aging_trigger_s: float,
    aging_hard_s: float,
    ga_queue_limit: int,
    adaptive_max_burst: int,
    fg_slot_reserve: int,
) -> int:
    available_pending = int(pending_fg_count)
    if (not bool(no_ga_remaining)) and (not bool(blocked_on_slot)):
        ready_hint = max(0, int(ready_fg_count))
        if ready_hint > 0:
            available_pending = min(int(available_pending), int(ready_hint))
        else:
            # Probe one pending FG lane even when the ready hint is stale. The
            # submit loop still routes through `_pop_next_fg(...)`, so at worst
            # this is a cheap no-op; at best it lets a genuinely ready FG lane
            # surface immediately instead of waiting for GA to fully drain.
            available_pending = min(int(available_pending), 1)

    capacity = max(0, min(int(fg_workers) - int(fg_inflight_count), int(fg_batch_max), int(available_pending)))
    if capacity <= 0:
        return 0

    if bool(no_ga_remaining):
        return int(capacity)

    if int(pending_fg_count) > int(ready_fg_count):
        burst_cap = max(1, min(int(adaptive_max_burst), int(fg_batch_max), int(fg_workers)))
        capacity = min(int(capacity), int(burst_cap))

    return int(capacity)


def closed_loop_bubble_kpi(
    *,
    idle_sec: float,
    ready_ga_count: int,
    ready_fg_count: int,
    backlog_count: int,
    oldest_fg_wait_s: float,
) -> float:
    idle = max(0.0, float(idle_sec))
    if idle <= 0.0:
        return 0.0

    ready_depth = max(0, int(ready_ga_count)) + max(0, int(ready_fg_count))
    backlog_depth = max(0, int(backlog_count))
    fg_wait = max(0.0, float(oldest_fg_wait_s))

    if ready_depth <= 0 and backlog_depth <= 0 and fg_wait <= 0.0:
        return 0.0

    backlog_term = min(4.0, float(backlog_depth) / 4.0)
    fg_wait_term = min(5.0, float(fg_wait))
    pressure = 1.0 + float(ready_depth) + float(backlog_term) + float(fg_wait_term)
    return float(idle) * float(pressure)
