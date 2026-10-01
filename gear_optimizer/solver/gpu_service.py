"""
In-process GPU Service client for Taichi jobs.

This is a lightweight async wrapper around `GpuExecutor` intended for future
multi-song in-flight orchestration, where one thread owns Taichi/Vulkan and
CPU orchestration can overlap GPU work.

Today, the app primarily uses `GpuExecutor` for cross-process GPU ownership.
This module provides an opt-in, in-process Future-based API without changing
the existing call sites.
"""

from __future__ import annotations

import itertools
import os
import queue
import signal
import threading
import time
from concurrent.futures import Future, InvalidStateError
from dataclasses import dataclass
from typing import Any, Optional
import logging

from gear_optimizer import settings

from .gpu_executor import GpuExecutor, get_gpu_executor
from .gpu_executor_types import GpuRequest, GpuRequestType, GpuResponse


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GpuJobHandle:
    """A submitted GPU job and its Future."""

    request_id: int
    future: Future


class GpuFatalError(RuntimeError):
    """The GPU can no longer serve this process (a hung request, a failed Taichi init); a service-mode run stops."""


class GpuServiceTimeoutError(GpuFatalError):
    """Raised when an in-process GPU service request exceeds its watchdog timeout."""


# GPU driver errors (raised through Taichi) that mean the device is gone; only their messages say so.
_FATAL_DRIVER_MARKERS = (
    "device lost",
    "device removed",
    "device hung",
    "dxgi_error_device_hung",
    "dxgi_error_device_removed",
    "cudaerrorlaunchtimeout",
    "watchdog timeout",
    "tdr",
    "waituntilcompleted",
    "metaldevice::wait_idle",
)


def is_fatal_gpu_error(exc: BaseException) -> bool:
    """Whether `exc`, or an exception it was raised from, means this process can no longer use its GPU: the engine's
    own GpuFatalError or a driver's device loss."""
    seen: set[int] = set()
    pending: list[BaseException | None] = [exc]
    while pending:
        current = pending.pop()
        if current is None or id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, GpuFatalError):
            return True
        if any(marker in f"{type(current).__name__}: {current}".lower() for marker in _FATAL_DRIVER_MARKERS):
            return True
        pending += [current.__cause__, current.__context__]
    return False


@dataclass
class _PendingGpuRequest:
    future: Future
    request_type: GpuRequestType
    submit_ts: float
    timeout_sec: float


class GpuServiceClient:
    """
    Async in-process client for the singleton `GpuExecutor`.

    The executor thread owns Taichi; this client submits requests and resolves
    Futures when responses arrive on the client's response queue.
    """

    def __init__(self, executor: Optional[GpuExecutor] = None):
        self._executor = executor or get_gpu_executor()
        self._worker_id: Optional[int] = None
        self._request_queue: Any = None
        self._response_queue: Any = None
        self._counter = itertools.count(1)
        self._pending: dict[int, _PendingGpuRequest] = {}
        self._lock = threading.Lock()
        self._rx_thread: Optional[threading.Thread] = None
        self._timeout_thread: Optional[threading.Thread] = None
        self._running = False
        self._in_process_queues = False
        self._timeout_abort_requested = threading.Event()

        # Under the :8765 service a stuck GPU request times out and stops the process (the service
        # then fails the solve); standalone runs wait indefinitely.
        self._request_timeouts_enabled = settings.service_mode()
        self._timeout_poll_sec = 0.25

    @property
    def executor(self) -> GpuExecutor:
        return self._executor

    def start(self, *, start_executor: bool = False, in_process_queues: bool = True) -> None:
        """
        Start the client, optionally starting the underlying executor thread.

        Args:
            start_executor: If True, starts the singleton executor if not running.
            in_process_queues: If starting the executor here, prefer thread queues.
        """
        if self._running:
            return

        if start_executor and not self._executor.is_running:
            self._executor.start(in_process=in_process_queues)

        worker_id, request_queue, response_queue = self._executor.register_worker()
        self._worker_id = int(worker_id)
        self._request_queue = request_queue
        self._response_queue = response_queue
        self._in_process_queues = bool(in_process_queues)

        self._running = True
        self._timeout_abort_requested.clear()
        self._rx_thread = threading.Thread(
            target=self._rx_loop,
            name=f"GpuServiceClientRx[{self._worker_id}]",
            daemon=True,
        )
        self._rx_thread.start()
        self._timeout_thread = threading.Thread(
            target=self._timeout_loop,
            name=f"GpuServiceClientTimeout[{self._worker_id}]",
            daemon=True,
        )
        self._timeout_thread.start()

    def close(self, *, timeout: float = 2.0) -> None:
        if not self._running:
            return

        self._running = False
        if self._rx_thread is not None:
            self._rx_thread.join(timeout=max(0.0, float(timeout)))
        self._rx_thread = None
        if self._timeout_thread is not None:
            self._timeout_thread.join(timeout=max(0.0, float(timeout)))
        self._timeout_thread = None

        if self._worker_id is not None:
            self._executor.unregister_worker(int(self._worker_id))
        self._worker_id = None
        self._request_queue = None
        self._response_queue = None

        with self._lock:
            pending = list(self._pending.items())
            self._pending.clear()
        for _req_id, entry in pending:
            fut = entry.future if isinstance(entry, _PendingGpuRequest) else entry
            try:
                if not fut.done():
                    fut.set_exception(RuntimeError("GPU client closed"))
            except InvalidStateError as e:
                logger.debug(f"gpu_service:close: future already resolved/cancelled: {e}")

    def submit(self, request_type: GpuRequestType, payload: dict[str, Any]) -> GpuJobHandle:
        if not self._running or self._worker_id is None:
            raise RuntimeError("GpuServiceClient not started")

        request_id = int(next(self._counter))
        t_submit = time.perf_counter()
        fut: Future = Future()
        with self._lock:
            self._pending[request_id] = _PendingGpuRequest(
                future=fut,
                request_type=request_type,
                submit_ts=float(t_submit),
                timeout_sec=float(self._request_timeout_sec_for(request_type)),
            )

        req = GpuRequest(
            request_type=request_type,
            request_id=request_id,
            worker_id=int(self._worker_id),
            payload=dict(payload or {}),
            submit_perf_ns=time.perf_counter_ns(),
        )
        self._request_queue.put(req)
        return GpuJobHandle(request_id=request_id, future=fut)

    def submit_gpu_native_ga_run(self, payload: dict[str, Any]) -> GpuJobHandle:
        # The GA run carries the fused GA->FG owner continuation (Slice 3): the owner
        # scores FG in the GA turn and returns {runs_payload, fg_owner_score}. There is
        # no separate FORCE_GREATS_RESPONSE_FRONTIER_BATCH submit anymore.
        return self.submit(GpuRequestType.GPU_NATIVE_GA_RUN, dict(payload or {}))

    def _rx_loop(self) -> None:
        while self._running:
            try:
                resp: GpuResponse = self._response_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            pending = None
            with self._lock:
                pending = self._pending.pop(int(resp.request_id), None)
            if pending is None:
                continue
            fut = pending.future

            # The pop-under-lock above makes this thread the sole owner of the
            # entry (the timeout loop can never see it), so the only competing
            # writer is a caller-side Future.cancel() (abort/shutdown). Losing
            # that race raises InvalidStateError; letting it propagate would
            # kill this rx thread and silently hang every later response.
            try:
                if resp.success:
                    fut.set_result(resp.result)
                else:
                    fut.set_exception(RuntimeError(resp.error or "GPU job failed"))
            except InvalidStateError as e:
                logger.debug(f"gpu_service:_rx_loop: future already resolved/cancelled: {e}")

    def _request_timeout_sec_for(self, request_type: GpuRequestType) -> float:
        if not self._request_timeouts_enabled:
            return 0.0

        if request_type == GpuRequestType.GPU_NATIVE_GA_RUN:
            return 240.0
        return 120.0

    def _trigger_timeout_abort(self, message: str) -> None:
        if not self._request_timeouts_enabled or self._timeout_abort_requested.is_set():
            return
        self._timeout_abort_requested.set()

        def _abort() -> None:
            print(f"[GpuService] Fatal request timeout: {message}")
            time.sleep(0.1)
            try:
                os.kill(os.getpid(), signal.SIGTERM)
            except Exception as e:
                logger.debug(f"gpu_service:_abort: {e}")
                os._exit(124)

        threading.Thread(target=_abort, name="GpuServiceTimeoutAbort", daemon=True).start()

    def _timeout_loop(self) -> None:
        while self._running:
            now = time.perf_counter()
            expired: list[tuple[int, _PendingGpuRequest, float]] = []
            with self._lock:
                for request_id, entry in list(self._pending.items()):
                    timeout_sec = max(0.0, float(entry.timeout_sec or 0.0))
                    if timeout_sec <= 0.0:
                        continue
                    elapsed_sec = max(0.0, float(now - float(entry.submit_ts)))
                    if elapsed_sec < timeout_sec:
                        continue
                    expired.append((int(request_id), entry, float(elapsed_sec)))
                    self._pending.pop(int(request_id), None)

            for request_id, entry, elapsed_sec in expired:
                message = (
                    f"GPU service request {entry.request_type.value} "
                    f"(request_id={request_id}) timed out after {elapsed_sec:.1f}s "
                    f"(limit {float(entry.timeout_sec):.1f}s)"
                )
                # Same ownership rule as _rx_loop: the pop-under-lock made this
                # thread the entry's sole owner; only a caller-side cancel can
                # race the set. Losing that race must not kill the timeout loop.
                try:
                    if not entry.future.done():
                        entry.future.set_exception(GpuServiceTimeoutError(message))
                except InvalidStateError as e:
                    logger.debug(f"gpu_service:_timeout_loop: future already resolved/cancelled: {e}")
                self._trigger_timeout_abort(message)

            time.sleep(float(self._timeout_poll_sec))
