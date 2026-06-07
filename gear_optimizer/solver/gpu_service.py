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
import random
from concurrent.futures import Future
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Optional
import logging

from gear_optimizer.core.env_config import ENV
from gear_optimizer.core.parsing import env_flag, truthy
from gear_optimizer.core.profile_events import emit_profile_event

from .gpu_executor import GpuExecutor, get_gpu_executor
from .gpu_executor_types import GpuRequest, GpuRequestType, GpuResponse

from gear_optimizer.core.parsing import env_get

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GpuJobHandle:
    """A submitted GPU job and its Future."""

    request_id: int
    future: Future


class GpuServiceTimeoutError(RuntimeError):
    """Raised when an in-process GPU service request exceeds its watchdog timeout."""


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

        # Optional latency profiling (end-to-end submit -> response).
        self._profile_enabled = bool(ENV.perf_timing or ENV.gpu_service_profile)
        self._profile_print = bool(ENV.perf_timing or ENV.gpu_service_profile_print)
        self._profile_counts: dict[GpuRequestType, int] = defaultdict(int)
        self._profile_total_sec: dict[GpuRequestType, float] = defaultdict(float)
        self._profile_max_sec: dict[GpuRequestType, float] = defaultdict(float)
        self._profile_samples: dict[GpuRequestType, list[float]] = defaultdict(list)
        # Client-level profiling for Futures that do not correspond 1:1 with executor requests
        # (e.g., tiled FG solve batch handles).
        self._client_profile_counts: dict[str, int] = defaultdict(int)
        self._client_profile_total_sec: dict[str, float] = defaultdict(float)
        self._client_profile_max_sec: dict[str, float] = defaultdict(float)
        self._client_profile_samples: dict[str, list[float]] = defaultdict(list)
        self._profile_sample_cap = 5000

        timeout_default_enabled = env_flag("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", "0")
        timeout_fatal_default = timeout_default_enabled
        raw_timeout_fatal = str(env_get("GPU_SERVICE_TIMEOUT_FATAL", "") or "").strip().lower()
        if raw_timeout_fatal:
            self._timeout_fatal = truthy(raw_timeout_fatal)
        else:
            self._timeout_fatal = bool(timeout_fatal_default)
        self._request_timeout_default_enabled = bool(timeout_default_enabled)
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

        if self._profile_enabled and self._profile_print:
            try:
                self.report_profile()
            except Exception as e:
                logger.debug(f"gpu_service:close: {e}")

        if self._worker_id is not None:
            try:
                self._executor.unregister_worker(int(self._worker_id))
            except Exception as e:
                logger.debug(f"gpu_service:close: {e}")
        self._worker_id = None
        self._request_queue = None
        self._response_queue = None

        with self._lock:
            pending = list(self._pending.items())
            self._pending.clear()
        for _req_id, entry in pending:
            fut = entry.future if isinstance(entry, _PendingGpuRequest) else entry
            if not fut.done():
                fut.set_exception(RuntimeError("GPU client closed"))

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

    def _record_latency_sample(
        self,
        *,
        key: Any,
        latency_sec: float,
        counts: dict[Any, int],
        totals: dict[Any, float],
        maxes: dict[Any, float],
        samples: dict[Any, list[float]],
    ) -> None:
        try:
            latency = float(latency_sec)
        except Exception as e:
            logger.debug(f"gpu_service:_record_latency_sample: {e}")
            return
        if latency < 0.0:
            latency = 0.0
        try:
            counts[key] += 1
            totals[key] += float(latency)
            if latency > float(maxes[key]):
                maxes[key] = float(latency)
        except Exception as e:
            logger.debug(f"gpu_service:_record_latency_sample: {e}")
            return

        try:
            sample_list = samples[key]
            if len(sample_list) < int(self._profile_sample_cap):
                sample_list.append(float(latency))
            else:
                n = int(counts[key])
                if n > 0:
                    j = random.randint(0, n - 1)
                    if j < int(self._profile_sample_cap):
                        sample_list[j] = float(latency)
        except Exception as e:
            logger.debug(f"gpu_service:_record_latency_sample: {e}")
            return
        key_label = ""
        try:
            if isinstance(key, GpuRequestType):
                key_label = str(key.value)
            else:
                key_label = str(key)
        except Exception as e:
            logger.debug(f"gpu_service:_record_latency_sample: {e}")
            key_label = ""
        emit_profile_event(
            component="gpu_service",
            event="latency_sample",
            metrics={
                "key": key_label,
                "latency_sec": float(latency),
                "sample_count": int(counts.get(key, 0) or 0),
            },
        )

    def submit_gpu_native_ga_run(self, payload: dict[str, Any]) -> GpuJobHandle:
        return self.submit(GpuRequestType.GPU_NATIVE_GA_RUN, dict(payload or {}))

    def submit_force_greats_response_frontier_score_batch(self, payload: dict[str, Any]) -> GpuJobHandle:
        return self.submit(GpuRequestType.FORCE_GREATS_RESPONSE_FRONTIER_SCORE_BATCH, dict(payload or {}))

    def _rx_loop(self) -> None:
        while self._running:
            try:
                resp: GpuResponse = self._response_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            except Exception as e:
                logger.debug(f"gpu_service:_rx_loop: {e}")
                continue

            pending = None
            with self._lock:
                pending = self._pending.pop(int(resp.request_id), None)
            if pending is None:
                continue
            fut = pending.future
            req_type = pending.request_type
            t_submit = pending.submit_ts

            if self._profile_enabled and isinstance(req_type, GpuRequestType) and isinstance(t_submit, (int, float)):
                try:
                    latency = max(0.0, time.perf_counter() - float(t_submit))
                    self._record_latency_sample(
                        key=req_type,
                        latency_sec=float(latency),
                        counts=self._profile_counts,
                        totals=self._profile_total_sec,
                        maxes=self._profile_max_sec,
                        samples=self._profile_samples,
                    )
                except Exception as e:
                    logger.debug(f"gpu_service:_rx_loop: {e}")

            if resp.success:
                fut.set_result(resp.result)
            else:
                fut.set_exception(RuntimeError(resp.error or "GPU job failed"))

    def _request_timeout_sec_for(self, request_type: GpuRequestType) -> float:
        # Single canonical deployment-boundary timeout knob. The former
        # dynamically-constructed per-type GPU_SERVICE_REQUEST_TIMEOUT_<TYPE>_SEC
        # name was registry-invisible (a typo silently no-op'd it) and is removed.
        raw = str(env_get("GPU_SERVICE_REQUEST_TIMEOUT_SEC", "") or "").strip()

        if raw:
            try:
                return max(0.0, float(raw))
            except Exception as e:
                logger.debug(f"gpu_service:_request_timeout_sec_for: {e}")
                return 0.0

        if not self._request_timeout_default_enabled:
            return 0.0

        if request_type == GpuRequestType.GPU_NATIVE_GA_RUN:
            return 240.0
        return 120.0

    def _trigger_timeout_abort(self, message: str) -> None:
        if not self._timeout_fatal or self._timeout_abort_requested.is_set():
            return
        self._timeout_abort_requested.set()

        def _abort() -> None:
            try:
                print(f"[GpuService] Fatal request timeout: {message}")
            except Exception as e:
                logger.debug(f"gpu_service:_abort: {e}")
            try:
                time.sleep(0.1)
            except Exception as e:
                logger.debug(f"gpu_service:_abort: {e}")
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
                if not entry.future.done():
                    entry.future.set_exception(GpuServiceTimeoutError(message))
                emit_profile_event(
                    component="gpu_service",
                    event="timeout",
                    metrics={
                        "request_id": int(request_id),
                        "request_type": str(entry.request_type.value),
                        "elapsed_sec": float(elapsed_sec),
                        "timeout_sec": float(entry.timeout_sec),
                        "fatal": int(bool(self._timeout_fatal)),
                    },
                )
                self._trigger_timeout_abort(message)

            try:
                time.sleep(float(self._timeout_poll_sec))
            except Exception as e:
                logger.debug(f"gpu_service:_timeout_loop: {e}")
                time.sleep(0.25)

    def profile_summary(self) -> dict[str, Any]:
        if not self._profile_enabled:
            return {"enabled": False}

        out: dict[str, Any] = {"enabled": True, "by_type": {}, "client_jobs": {}}
        for req_type, count in sorted(self._profile_counts.items(), key=lambda kv: kv[0].value):
            total = float(self._profile_total_sec.get(req_type, 0.0) or 0.0)
            mx = float(self._profile_max_sec.get(req_type, 0.0) or 0.0)
            avg = (total / count) if count else 0.0
            samples = list(self._profile_samples.get(req_type, ()))
            p95 = None
            if samples:
                try:
                    samples_sorted = sorted(samples)
                    idx = int(round(0.95 * (len(samples_sorted) - 1)))
                    idx = max(0, min(idx, len(samples_sorted) - 1))
                    p95 = float(samples_sorted[idx])
                except Exception as e:
                    logger.debug(f"gpu_service:profile_summary: {e}")
                    p95 = None
            out["by_type"][req_type.value] = {
                "count": int(count),
                "avg_sec": float(avg),
                "p95_sec": p95,
                "max_sec": float(mx),
            }
        for name, count in sorted(self._client_profile_counts.items(), key=lambda kv: kv[0]):
            total = float(self._client_profile_total_sec.get(name, 0.0) or 0.0)
            mx = float(self._client_profile_max_sec.get(name, 0.0) or 0.0)
            avg = (total / count) if count else 0.0
            samples = list(self._client_profile_samples.get(name, ()))
            p95 = None
            if samples:
                try:
                    samples_sorted = sorted(samples)
                    idx = int(round(0.95 * (len(samples_sorted) - 1)))
                    idx = max(0, min(idx, len(samples_sorted) - 1))
                    p95 = float(samples_sorted[idx])
                except Exception as e:
                    logger.debug(f"gpu_service:profile_summary: {e}")
                    p95 = None
            out["client_jobs"][name] = {
                "count": int(count),
                "avg_sec": float(avg),
                "p95_sec": p95,
                "max_sec": float(mx),
            }
        return out

    def report_profile(self) -> str:
        summary = self.profile_summary()
        if not summary.get("enabled"):
            return ""

        by_type = summary.get("by_type") or {}
        # Keep output compact: sort by avg latency desc, show top 8.
        items = []
        for k, v in by_type.items():
            try:
                items.append((k, float(v.get("avg_sec", 0.0) or 0.0), v))
            except Exception as e:
                logger.debug(f"gpu_service:report_profile: {e}")
                continue
        items.sort(key=lambda t: t[1], reverse=True)
        items = items[:8]

        parts = []
        for name, _avg, v in items:
            try:
                parts.append(
                    f"{name}:n={int(v.get('count', 0))} avg={float(v.get('avg_sec', 0.0)):.3f}s "
                    f"p95={float(v.get('p95_sec') or 0.0):.3f}s max={float(v.get('max_sec', 0.0)):.3f}s"
                )
            except Exception as e:
                logger.debug(f"gpu_service:report_profile: {e}")
                continue
        line = "[GpuServiceClient][PROFILE] " + "; ".join(parts)
        try:
            print(line)
        except Exception as e:
            logger.debug(f"gpu_service:report_profile: {e}")
        client_jobs = summary.get("client_jobs") or {}
        if client_jobs:
            items2 = []
            for k, v in client_jobs.items():
                try:
                    items2.append((str(k), float(v.get("avg_sec", 0.0) or 0.0), v))
                except Exception as e:
                    logger.debug(f"gpu_service:report_profile: {e}")
                    continue
            items2.sort(key=lambda t: t[1], reverse=True)
            items2 = items2[:8]
            parts2 = []
            for name, _avg, v in items2:
                try:
                    parts2.append(
                        f"{name}:n={int(v.get('count', 0))} avg={float(v.get('avg_sec', 0.0)):.3f}s "
                        f"p95={float(v.get('p95_sec') or 0.0):.3f}s max={float(v.get('max_sec', 0.0)):.3f}s"
                    )
                except Exception as e:
                    logger.debug(f"gpu_service:report_profile: {e}")
                    continue
            line2 = "[GpuServiceClient][CLIENT_PROFILE] " + "; ".join(parts2)
            try:
                print(line2)
            except Exception as e:
                logger.debug(f"gpu_service:report_profile: {e}")
        return line
