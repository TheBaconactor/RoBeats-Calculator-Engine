"""Consolidated lifecycle helpers for the native in-flight optimizer."""
from __future__ import annotations

import concurrent.futures
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from gear_optimizer.solver.gpu_executor import get_gpu_executor
from gear_optimizer.solver.gpu_service import GpuServiceClient
from gear_optimizer.solver.native_inflight_config import inflight_shutdown_debug_enabled
from gear_optimizer.solver.native_inflight_lifecycle_prepare import prepare_native_song
from gear_optimizer.solver.native_inflight_lifecycle_progress import (
    ActiveRuntimeProgressReporter,
    ProgressTracker,
    evaluate_fg_progress_record_update,
)
from gear_optimizer.solver.native_inflight_lifecycle_queues import (
    BubbleTracker,
    InflightBundleTracker,
    PostSender,
    SongPrepCompletion,
    SongPrepQueue,
)

logger = logging.getLogger(__name__)

ProgressCallback = Callable[..., Any]


def build_native_task_error_payload(*args, **kwargs):
    from gear_optimizer.solver.native_inflight_completion import build_native_task_error_payload as _impl

    return _impl(*args, **kwargs)


def mark_song_completed(*args, **kwargs):
    from gear_optimizer.solver.native_inflight_completion import mark_song_completed as _impl

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


def build_abort_queue_snapshot(
    *,
    pending_tasks: int,
    prepared: int,
    prep_inflight: int,
    base_inflight: int,
    decode_inflight: int,
    pending_fg: int,
    fg_prep: int,
    fg_futures: int,
) -> str:
    return (
        f"pending={int(pending_tasks)} prepared={int(prepared)} prep_inflight={int(prep_inflight)} "
        f"base_inflight={int(base_inflight)} decode_inflight={int(decode_inflight)} "
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
    base_inflight: int,
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
            base_inflight=base_inflight,
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
    prep_queue,
    post_sender,
    gpu_client,
    gpu_executor,
) -> None:
    """Shut down native in-flight resources: worker executors concurrently
    (ThreadPoolExecutor + as_completed), then post_sender / gpu_client /
    gpu_executor sequentially after the join."""
    import concurrent.futures

    shutdown_debug = inflight_shutdown_debug_enabled()
    parallel_steps: list[tuple[str, Callable[[], None]]] = [
        (
            "fg_executor.shutdown",
            lambda: fg_pipeline.shutdown_fg(wait=True, cancel_futures=True),
        ),
        (
            "decode_executor.shutdown",
            lambda: decode_queue.shutdown(wait=True, cancel_futures=True),
        ),
        (
            "fg_prep_executor.shutdown",
            lambda: fg_pipeline.shutdown_prep(wait=True, cancel_futures=True),
        ),
        (
            "prep_executor.shutdown",
            lambda: prep_queue.shutdown(wait=True, cancel_futures=True),
        ),
    ]
    if db_persistence is not None:
        parallel_steps.append(
            (
                "db_prefetch.shutdown",
                lambda: db_persistence.shutdown_prefetch(wait=True, cancel_futures=True),
            )
        )

    if parallel_steps:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(parallel_steps)) as pool:
            futures = {
                pool.submit(_shutdown_step, label, action, shutdown_debug=shutdown_debug): label
                for label, action in parallel_steps
            }
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.debug(f"native_inflight_lifecycle:shutdown_parallel: {e}")

    if post_sender is not None:
        _shutdown_step("post_sender.close", lambda: post_sender.close(timeout=10.0), shutdown_debug=shutdown_debug)
    _shutdown_step("gpu_client.close", lambda: gpu_client.close(timeout=2.0), shutdown_debug=shutdown_debug)

    def _stop_gpu_executor_if_running() -> None:
        if gpu_executor.is_running:
            gpu_executor.stop()

    _shutdown_step("gpu_executor.stop", _stop_gpu_executor_if_running, shutdown_debug=shutdown_debug)


__all__ = [
    "ActiveRuntimeProgressReporter",
    "BubbleTracker",
    "CachedRuntimeSignal",
    "GpuAbortRequester",
    "InflightBundleTracker",
    "PostSender",
    "ProgressTracker",
    "SongPrepCompletion",
    "SongPrepQueue",
    "append_native_abort_log",
    "build_abort_queue_snapshot",
    "build_native_task_error_payload",
    "evaluate_fg_progress_record_update",
    "is_stop_abort_exception",
    "log_native_abort",
    "mark_song_completed",
    "native_abort_log_path",
    "prepare_native_song",
    "shutdown_native_inflight_resources",
    "start_native_inflight_gpu_client",
]
