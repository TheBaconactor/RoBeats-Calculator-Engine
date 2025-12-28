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
import queue
import threading
from concurrent.futures import Future
from dataclasses import dataclass
from typing import Any, Optional

from .gpu_executor import (
    GpuExecutor,
    GpuRequest,
    GpuRequestType,
    GpuResponse,
    get_gpu_executor,
)


@dataclass(frozen=True)
class GpuJobHandle:
    """A submitted GPU job and its Future."""

    request_id: int
    future: Future


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
        self._pending: dict[int, Future] = {}
        self._lock = threading.Lock()
        self._rx_thread: Optional[threading.Thread] = None
        self._running = False

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

        self._running = True
        self._rx_thread = threading.Thread(
            target=self._rx_loop,
            name=f"GpuServiceClientRx[{self._worker_id}]",
            daemon=True,
        )
        self._rx_thread.start()

    def close(self, *, timeout: float = 2.0) -> None:
        if not self._running:
            return

        self._running = False
        if self._rx_thread is not None:
            self._rx_thread.join(timeout=max(0.0, float(timeout)))
        self._rx_thread = None

        if self._worker_id is not None:
            try:
                self._executor.unregister_worker(int(self._worker_id))
            except Exception:
                pass
        self._worker_id = None
        self._request_queue = None
        self._response_queue = None

        with self._lock:
            pending = list(self._pending.items())
            self._pending.clear()
        for _req_id, fut in pending:
            if not fut.done():
                fut.set_exception(RuntimeError("GPU client closed"))

    def submit(self, request_type: GpuRequestType, payload: dict[str, Any]) -> GpuJobHandle:
        if not self._running or self._worker_id is None:
            raise RuntimeError("GpuServiceClient not started")

        request_id = int(next(self._counter))
        fut: Future = Future()
        with self._lock:
            self._pending[request_id] = fut

        req = GpuRequest(
            request_type=request_type,
            request_id=request_id,
            worker_id=int(self._worker_id),
            payload=dict(payload or {}),
        )
        self._request_queue.put(req)
        return GpuJobHandle(request_id=request_id, future=fut)

    def submit_precompute_timeline(
        self,
        *,
        calc_song: dict,
        ref_arrays: dict,
        song_slot: int = 0,
    ) -> GpuJobHandle:
        return self.submit(
            GpuRequestType.PRECOMPUTE_TIMELINE,
            {"calc_song": calc_song, "ref_arrays": ref_arrays, "song_slot": int(song_slot)},
        )

    def submit_solve_genomes(self, payload: dict[str, Any]) -> GpuJobHandle:
        return self.submit(GpuRequestType.SOLVE_GENOMES_PARALLEL, dict(payload or {}))

    def submit_gpu_native_ga_run(self, payload: dict[str, Any]) -> GpuJobHandle:
        return self.submit(GpuRequestType.GPU_NATIVE_GA_RUN, dict(payload or {}))

    def submit_solve_force_greats_finder(self, *args: Any, **kwargs: Any) -> GpuJobHandle:
        return self.submit(
            GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
            {"args": args, "kwargs": kwargs},
        )

    def submit_process_force_greats(self, *args: Any, **kwargs: Any) -> GpuJobHandle:
        return self.submit(
            GpuRequestType.PROCESS_FORCE_GREATS,
            {"args": args, "kwargs": kwargs},
        )

    def _rx_loop(self) -> None:
        while self._running:
            try:
                resp: GpuResponse = self._response_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            except Exception:
                continue

            fut = None
            with self._lock:
                fut = self._pending.pop(int(resp.request_id), None)
            if fut is None:
                continue

            if resp.success:
                fut.set_result(resp.result)
            else:
                fut.set_exception(RuntimeError(resp.error or "GPU job failed"))
