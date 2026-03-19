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
from collections import defaultdict, OrderedDict
from dataclasses import dataclass
from typing import Any, Optional

from gear_optimizer.core.env_config import ENV, TRUTHY_ENV_VALUES, env_flag
from gear_optimizer.core.profile_events import emit_profile_event

from .gpu_executor import (
    GpuExecutor,
    GpuRequest,
    GpuRequestType,
    GpuResponse,
    get_gpu_executor,
    _registry_base_fixed_stats_sig,
)


_WIN_TIMER_LOCK = threading.Lock()
_WIN_TIMER_USERS = 0
_WIN_TIMER_ACTIVE = False


def _system_timer_override_allowed() -> bool:
    """
    Guard system-wide WinMM timer period changes behind an explicit opt-in.

    `timeBeginPeriod(1)` affects the entire OS timer resolution while active in this process.
    Keep this disabled by default to avoid unexpected system-wide side effects.
    """
    raw = str(os.environ.get("GPU_ALLOW_SYSTEM_TIMER_OVERRIDE", "0") or "").strip().lower()
    return raw in TRUTHY_ENV_VALUES


def _acquire_windows_timer_period_1ms() -> bool:
    """
    Request 1ms Windows timer granularity for low-latency coalescing.

    Scoped by reference counting so multiple clients can coexist safely.
    """
    if os.name != "nt":
        return False
    global _WIN_TIMER_USERS, _WIN_TIMER_ACTIVE
    with _WIN_TIMER_LOCK:
        _WIN_TIMER_USERS += 1
        if _WIN_TIMER_ACTIVE:
            return True
        try:
            import ctypes

            mmres = int(ctypes.windll.winmm.timeBeginPeriod(1))
            if mmres == 0:
                _WIN_TIMER_ACTIVE = True
                return True
        except Exception:
            pass
        _WIN_TIMER_USERS = max(0, int(_WIN_TIMER_USERS) - 1)
        return False


def _release_windows_timer_period_1ms() -> None:
    if os.name != "nt":
        return
    global _WIN_TIMER_USERS, _WIN_TIMER_ACTIVE
    with _WIN_TIMER_LOCK:
        if _WIN_TIMER_USERS <= 0:
            return
        _WIN_TIMER_USERS -= 1
        if _WIN_TIMER_USERS > 0:
            return
        if not _WIN_TIMER_ACTIVE:
            return
        try:
            import ctypes

            ctypes.windll.winmm.timeEndPeriod(1)
        except Exception:
            pass
        _WIN_TIMER_ACTIVE = False


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
        self._submit_lock = threading.Lock()
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
        # (e.g., coalesced FG solve batch handles).
        self._client_profile_counts: dict[str, int] = defaultdict(int)
        self._client_profile_total_sec: dict[str, float] = defaultdict(float)
        self._client_profile_max_sec: dict[str, float] = defaultdict(float)
        self._client_profile_samples: dict[str, list[float]] = defaultdict(list)
        self._profile_sample_cap = 5000

        # FG job coalescing (optional, in-process only).
        # Default to disabled: extra coalescing can create very large breakpoints batches that risk
        # multi-second continuous GPU work on Windows (TDR / UI freezes). Enable explicitly via env.
        self._fg_coalesce_enabled = env_flag("FG_COALESCE_BREAKPOINTS_BATCH", "0")
        try:
            self._fg_coalesce_max_payloads = int(os.environ.get("FG_COALESCE_BREAKPOINTS_MAX_PAYLOADS", "192") or "192")
        except Exception:
            self._fg_coalesce_max_payloads = 128
        try:
            executor_max_payloads = int(os.environ.get("FG_BREAKPOINTS_BATCH_COALESCE_MAX_PAYLOADS", "16") or "16")
        except Exception:
            executor_max_payloads = 16
        executor_max_payloads = max(1, min(int(executor_max_payloads), 512))
        try:
            self._fg_coalesce_max_wait_ms = int(os.environ.get("FG_COALESCE_BREAKPOINTS_MAX_WAIT_MS", "1") or "1")
        except Exception:
            self._fg_coalesce_max_wait_ms = 1
        self._fg_coalesce_max_payloads = max(1, int(self._fg_coalesce_max_payloads))
        self._fg_coalesce_max_payloads = min(int(self._fg_coalesce_max_payloads), int(executor_max_payloads))
        self._fg_coalesce_max_wait_ms = max(0, int(self._fg_coalesce_max_wait_ms))
        self._fg_coalesce_payloads: list[dict[str, Any]] = []
        # (future, start, count, submit_ts)
        self._fg_coalesce_slices: list[tuple[Future, int, int, float]] = []
        self._fg_coalesce_first_ts: float | None = None
        self._fg_coalesce_lock = threading.Lock()
        self._fg_coalesce_event = threading.Event()
        self._fg_coalesce_thread: Optional[threading.Thread] = None
        self._fg_high_res_timer_enabled = False
        try:
            short_wait_spin_ms = float(str(os.environ.get("GPU_SERVICE_SHORT_WAIT_SPIN_MS", "3.0") or "3.0").strip())
        except Exception:
            short_wait_spin_ms = 3.0
        self._short_wait_spin_sec = max(0.0, float(short_wait_spin_ms) / 1000.0)

        self._registry_static_handle_counter = 0
        self._registry_static_handle_cache: "OrderedDict[tuple[Any, ...], dict[str, Any]]" = OrderedDict()
        try:
            self._registry_static_handle_cache_max = int(
                os.environ.get("GPU_SERVICE_REGISTRY_STATIC_CACHE_MAX", "512") or "512"
            )
        except Exception:
            self._registry_static_handle_cache_max = 512
        self._registry_static_handle_cache_max = max(32, int(self._registry_static_handle_cache_max))

        timeout_default_enabled = env_flag("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", "0")
        timeout_fatal_default = timeout_default_enabled
        raw_timeout_fatal = str(os.environ.get("GPU_SERVICE_TIMEOUT_FATAL", "") or "").strip().lower()
        if raw_timeout_fatal:
            self._timeout_fatal = raw_timeout_fatal in TRUTHY_ENV_VALUES
        else:
            self._timeout_fatal = bool(timeout_fatal_default)
        self._request_timeout_default_enabled = bool(timeout_default_enabled)
        try:
            self._timeout_poll_sec = max(0.05, float(os.environ.get("GPU_SERVICE_TIMEOUT_POLL_SEC", "0.25") or "0.25"))
        except Exception:
            self._timeout_poll_sec = 0.25

    @property
    def executor(self) -> GpuExecutor:
        return self._executor

    @property
    def submit_lock(self) -> threading.Lock:
        """Serialize multi-request submit sequences (prevents interleaving across threads)."""
        return self._submit_lock

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

        if self._fg_coalesce_enabled and self._in_process_queues and self._fg_coalesce_thread is None:
            # On Windows the default timer quantum can stretch 1ms waits to ~15ms.
            # Request 1ms period for short coalescing windows.
            if int(self._fg_coalesce_max_wait_ms) <= 4 and _system_timer_override_allowed():
                self._fg_high_res_timer_enabled = bool(_acquire_windows_timer_period_1ms())
            self._fg_coalesce_thread = threading.Thread(
                target=self._fg_coalesce_loop,
                name=f"GpuServiceClientFgCoalesce[{self._worker_id}]",
                daemon=True,
            )
            self._fg_coalesce_thread.start()

    def close(self, *, timeout: float = 2.0) -> None:
        if not self._running:
            return

        # Cancel any pending coalesced FG batches.
        if self._fg_coalesce_thread is not None:
            with self._fg_coalesce_lock:
                pending = list(self._fg_coalesce_slices)
                self._fg_coalesce_payloads.clear()
                self._fg_coalesce_slices.clear()
                self._fg_coalesce_first_ts = None
            for fut, _start, _count, _submit_ts in pending:
                if not fut.done():
                    fut.set_exception(RuntimeError("GPU client closed"))
            try:
                self._fg_coalesce_event.set()
            except Exception:
                pass

        self._running = False
        if self._rx_thread is not None:
            self._rx_thread.join(timeout=max(0.0, float(timeout)))
        self._rx_thread = None
        if self._timeout_thread is not None:
            self._timeout_thread.join(timeout=max(0.0, float(timeout)))
        self._timeout_thread = None
        if self._fg_coalesce_thread is not None:
            self._fg_coalesce_thread.join(timeout=max(0.0, float(timeout)))
        self._fg_coalesce_thread = None
        if self._fg_high_res_timer_enabled:
            _release_windows_timer_period_1ms()
            self._fg_high_res_timer_enabled = False

        if self._profile_enabled and self._profile_print:
            try:
                self.report_profile()
            except Exception:
                pass

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
        except Exception:
            return
        if latency < 0.0:
            latency = 0.0
        try:
            counts[key] += 1
            totals[key] += float(latency)
            if latency > float(maxes[key]):
                maxes[key] = float(latency)
        except Exception:
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
        except Exception:
            return
        key_label = ""
        try:
            if isinstance(key, GpuRequestType):
                key_label = str(key.value)
            else:
                key_label = str(key)
        except Exception:
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

    def _registry_static_handle_entry(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None
        required = ("item_stats", "slot_start", "slot_count", "base_fixed_stats", "timeline_grid", "ref_arrays")
        for key in required:
            if key not in payload:
                return None
        item_stats = payload.get("item_stats")
        slot_start = payload.get("slot_start")
        slot_count = payload.get("slot_count")
        base_fixed_stats = payload.get("base_fixed_stats")
        timeline_grid = payload.get("timeline_grid")
        ref_arrays = payload.get("ref_arrays")
        key = (
            int(id(item_stats)),
            int(id(slot_start)),
            int(id(slot_count)),
            _registry_base_fixed_stats_sig(base_fixed_stats),
            int(id(timeline_grid)),
            int(id(ref_arrays)),
        )
        cached = self._registry_static_handle_cache.get(key)
        if cached is not None:
            self._registry_static_handle_cache.move_to_end(key)
            return cached

        self._registry_static_handle_counter += 1
        entry = {
            "handle": int(self._registry_static_handle_counter),
            "registered": False,
            "item_stats_ref": item_stats,
            "slot_start_ref": slot_start,
            "slot_count_ref": slot_count,
            "base_fixed_stats_ref": base_fixed_stats,
            "timeline_grid_ref": timeline_grid,
            "ref_arrays_ref": ref_arrays,
        }
        self._registry_static_handle_cache[key] = entry
        self._registry_static_handle_cache.move_to_end(key)
        while len(self._registry_static_handle_cache) > int(self._registry_static_handle_cache_max):
            self._registry_static_handle_cache.popitem(last=False)
        return entry

    @staticmethod
    def _attach_handle_failure_reset(fut: Future, entry: dict[str, Any]) -> None:
        if not isinstance(entry, dict):
            return

        def _on_done(f: Future) -> None:
            try:
                _ = f.result()
            except Exception:
                entry["registered"] = False

        try:
            fut.add_done_callback(_on_done)
        except Exception:
            pass

    def submit_solve_genomes_from_registry(self, payload: dict[str, Any]) -> GpuJobHandle:
        request_payload = dict(payload or {})
        entry = self._registry_static_handle_entry(request_payload)
        if entry is None:
            return self.submit(GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY, request_payload)

        handle = int(entry.get("handle", 0) or 0)
        inline_static = not bool(entry.get("registered", False))
        request_payload["registry_payload_handle"] = int(handle)
        request_payload["registry_payload_inline"] = bool(inline_static)
        if not inline_static:
            request_payload.pop("item_stats", None)
            request_payload.pop("slot_start", None)
            request_payload.pop("slot_count", None)
            request_payload.pop("base_fixed_stats", None)
            request_payload.pop("timeline_grid", None)
            request_payload.pop("ref_arrays", None)

        job = self.submit(GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY, request_payload)
        entry["registered"] = True
        self._attach_handle_failure_reset(job.future, entry)
        return job

    def submit_solve_genomes_from_registry_matrix(self, payload: dict[str, Any]) -> GpuJobHandle:
        return self.submit(GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY_MATRIX, dict(payload or {}))

    def submit_gpu_native_ga_run(self, payload: dict[str, Any]) -> GpuJobHandle:
        return self.submit(GpuRequestType.GPU_NATIVE_GA_RUN, dict(payload or {}))

    def submit_ga_fg_fused_solve_with_breakpoints(self, payload: dict[str, Any]) -> GpuJobHandle:
        return self.submit(GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS, dict(payload or {}))

    def submit_solve_force_greats_finder(self, *args: Any, **kwargs: Any) -> GpuJobHandle:
        return self.submit(
            GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
            {"args": args, "kwargs": kwargs},
        )

    def submit_fg_compute_breakpoints(
        self,
        *,
        ftff_pairs,
        base_stats_pairs,
        n_sections: int,
        song_slot: int = 0,
        gem_scale_fever: int = 3,
        non_fever_base_by_ff=None,
        fp_cap_table=None,
        ensure_timeline_precompute: bool = False,
        calc_song: Optional[dict[str, Any]] = None,
        ref_arrays: Optional[dict[str, Any]] = None,
    ) -> GpuJobHandle:
        # Accept either Python sequences or pre-packed numpy arrays to avoid per-item tuple packing in hot paths.
        request_payload: dict[str, Any] = {
            "ftff_pairs": ftff_pairs,
            "base_stats_pairs": base_stats_pairs,
            "n_sections": int(n_sections),
            "song_slot": int(song_slot),
            "gem_scale_fever": int(gem_scale_fever),
            "non_fever_base_by_ff": non_fever_base_by_ff,
            "fp_cap_table": fp_cap_table,
        }
        if ensure_timeline_precompute:
            request_payload["ensure_timeline_precompute"] = True
            request_payload["calc_song"] = calc_song
            request_payload["ref_arrays"] = ref_arrays
        return self.submit(
            GpuRequestType.FG_COMPUTE_BREAKPOINTS,
            request_payload,
        )

    def submit_fg_solve_with_breakpoints_batch(self, payloads: list[dict[str, Any]]) -> GpuJobHandle:
        payload_list = list(payloads or [])
        if (
            self._fg_coalesce_enabled
            and self._in_process_queues
            and payload_list
            and all(isinstance(p, dict) for p in payload_list)
        ):
            return self._submit_fg_batch_coalesced(payload_list)
        return self.submit(GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH, {"payloads": payload_list})

    def _submit_fg_batch_coalesced(self, payloads: list[dict[str, Any]]) -> GpuJobHandle:
        if not self._running or self._worker_id is None:
            raise RuntimeError("GpuServiceClient not started")
        fut: Future = Future()
        request_id = int(next(self._counter))
        t_submit = time.perf_counter() if self._profile_enabled else 0.0

        batch = None
        with self._fg_coalesce_lock:
            if not payloads:
                fut.set_result([])
                return GpuJobHandle(request_id=request_id, future=fut)
            if self._fg_coalesce_first_ts is None:
                self._fg_coalesce_first_ts = time.perf_counter()
            start = len(self._fg_coalesce_payloads)
            self._fg_coalesce_payloads.extend(payloads)
            self._fg_coalesce_slices.append((fut, int(start), int(len(payloads)), float(t_submit)))
            if (
                int(len(self._fg_coalesce_payloads)) >= int(self._fg_coalesce_max_payloads)
                or int(self._fg_coalesce_max_wait_ms) <= 0
            ):
                batch = self._pop_fg_coalesce_locked()
            else:
                self._fg_coalesce_event.set()

        if batch is not None:
            payloads_batch, slices_batch = batch
            self._submit_fg_coalesced_batch(payloads_batch, slices_batch)

        return GpuJobHandle(request_id=request_id, future=fut)

    def _pop_fg_coalesce_locked(self) -> tuple[list[dict[str, Any]], list[tuple[Future, int, int, float]]] | None:
        if not self._fg_coalesce_payloads:
            return None
        payloads = list(self._fg_coalesce_payloads)
        slices = list(self._fg_coalesce_slices)
        self._fg_coalesce_payloads.clear()
        self._fg_coalesce_slices.clear()
        self._fg_coalesce_first_ts = None
        return payloads, slices

    def _submit_fg_coalesced_batch(
        self,
        payloads: list[dict[str, Any]],
        slices: list[tuple[Future, int, int, float]],
    ) -> None:
        t_batch_submit = time.perf_counter() if self._profile_enabled else 0.0
        try:
            job = self.submit(GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH, {"payloads": payloads})
        except Exception as exc:
            if self._profile_enabled:
                now = time.perf_counter()
                for _fut, _start, _count, submit_ts in slices:
                    if not isinstance(submit_ts, (int, float)) or submit_ts <= 0.0:
                        continue
                    self._record_latency_sample(
                        key=f"client/{GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH.value}",
                        latency_sec=max(0.0, now - float(submit_ts)),
                        counts=self._client_profile_counts,
                        totals=self._client_profile_total_sec,
                        maxes=self._client_profile_max_sec,
                        samples=self._client_profile_samples,
                    )
                    self._record_latency_sample(
                        key=f"coalesce_wait/{GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH.value}",
                        latency_sec=max(0.0, float(t_batch_submit) - float(submit_ts)),
                        counts=self._client_profile_counts,
                        totals=self._client_profile_total_sec,
                        maxes=self._client_profile_max_sec,
                        samples=self._client_profile_samples,
                    )
            for fut, _start, _count, _submit_ts in slices:
                if not fut.done():
                    fut.set_exception(exc)
            return

        def _on_done(done_fut: Future) -> None:
            if self._profile_enabled:
                now = time.perf_counter()
                for _fut, _start, _count, submit_ts in slices:
                    if not isinstance(submit_ts, (int, float)) or submit_ts <= 0.0:
                        continue
                    self._record_latency_sample(
                        key=f"client/{GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH.value}",
                        latency_sec=max(0.0, now - float(submit_ts)),
                        counts=self._client_profile_counts,
                        totals=self._client_profile_total_sec,
                        maxes=self._client_profile_max_sec,
                        samples=self._client_profile_samples,
                    )
                    self._record_latency_sample(
                        key=f"coalesce_wait/{GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH.value}",
                        latency_sec=max(0.0, float(t_batch_submit) - float(submit_ts)),
                        counts=self._client_profile_counts,
                        totals=self._client_profile_total_sec,
                        maxes=self._client_profile_max_sec,
                        samples=self._client_profile_samples,
                    )

            try:
                result = done_fut.result()
            except Exception as exc2:
                for fut, _start, _count, _submit_ts in slices:
                    if not fut.done():
                        fut.set_exception(exc2)
                return
            if not isinstance(result, list):
                err = RuntimeError("FG coalesced batch returned non-list result")
                for fut, _start, _count, _submit_ts in slices:
                    if not fut.done():
                        fut.set_exception(err)
                return
            for fut, start, count, _submit_ts in slices:
                if fut.done():
                    continue
                try:
                    sub = result[int(start) : int(start) + int(count)]
                except Exception as exc3:
                    fut.set_exception(exc3)
                    continue
                fut.set_result(list(sub))

        job.future.add_done_callback(_on_done)

    def _coalesce_event_wait(self, timeout: float) -> bool:
        wait_timeout = max(0.0, float(timeout))
        if wait_timeout <= 0.0:
            return bool(self._fg_coalesce_event.wait(timeout=0.0))

        if wait_timeout > float(self._short_wait_spin_sec):
            return bool(self._fg_coalesce_event.wait(timeout=wait_timeout))

        deadline = time.perf_counter() + wait_timeout
        while True:
            if self._fg_coalesce_event.wait(timeout=0.0):
                return True
            if time.perf_counter() >= deadline:
                return False
            time.sleep(0)

    def _fg_coalesce_loop(self) -> None:
        while self._running and self._fg_coalesce_enabled and self._in_process_queues:
            batch = None
            wait_sec = 0.05
            with self._fg_coalesce_lock:
                if self._fg_coalesce_payloads:
                    now = time.perf_counter()
                    if self._fg_coalesce_first_ts is None:
                        self._fg_coalesce_first_ts = now
                    max_wait = float(self._fg_coalesce_max_wait_ms) / 1000.0
                    if max_wait <= 0.0 or (now - float(self._fg_coalesce_first_ts)) >= max_wait:
                        batch = self._pop_fg_coalesce_locked()
                    else:
                        # Keep the coalescing window precise in in-process mode.
                        # A hard 1ms floor here can inflate a sub-ms remaining window
                        # into ~1ms+, introducing avoidable GPU idle bubbles.
                        wait_sec = max(0.0, max_wait - (now - float(self._fg_coalesce_first_ts)))
                else:
                    self._fg_coalesce_event.clear()

            if batch is not None:
                payloads_batch, slices_batch = batch
                self._submit_fg_coalesced_batch(payloads_batch, slices_batch)
                continue

            try:
                self._coalesce_event_wait(wait_sec)
            except Exception:
                pass

    def _rx_loop(self) -> None:
        while self._running:
            try:
                resp: GpuResponse = self._response_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            except Exception:
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
                except Exception:
                    pass

            if resp.success:
                fut.set_result(resp.result)
            else:
                fut.set_exception(RuntimeError(resp.error or "GPU job failed"))

    def _request_timeout_sec_for(self, request_type: GpuRequestType) -> float:
        env_key = "GPU_SERVICE_REQUEST_TIMEOUT_" + "".join(
            ch if ch.isalnum() else "_" for ch in str(request_type.value or "").upper()
        ) + "_SEC"
        raw = str(os.environ.get(env_key, "") or "").strip()
        if not raw:
            raw = str(os.environ.get("GPU_SERVICE_REQUEST_TIMEOUT_SEC", "") or "").strip()

        if raw:
            try:
                return max(0.0, float(raw))
            except Exception:
                return 0.0

        if not self._request_timeout_default_enabled:
            return 0.0

        if request_type == GpuRequestType.GPU_NATIVE_GA_RUN:
            return 240.0
        if request_type in {
            GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
            GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS,
            GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH,
            GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS,
        }:
            return 180.0
        return 120.0

    def _trigger_timeout_abort(self, message: str) -> None:
        if not self._timeout_fatal or self._timeout_abort_requested.is_set():
            return
        self._timeout_abort_requested.set()

        def _abort() -> None:
            try:
                print(f"[GpuService] Fatal request timeout: {message}")
            except Exception:
                pass
            try:
                time.sleep(0.1)
            except Exception:
                pass
            try:
                os.kill(os.getpid(), signal.SIGTERM)
            except Exception:
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
            except Exception:
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
                except Exception:
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
                except Exception:
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
            except Exception:
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
            except Exception:
                continue
        line = "[GpuServiceClient][PROFILE] " + "; ".join(parts)
        try:
            print(line)
        except Exception:
            pass
        client_jobs = summary.get("client_jobs") or {}
        if client_jobs:
            items2 = []
            for k, v in client_jobs.items():
                try:
                    items2.append((str(k), float(v.get("avg_sec", 0.0) or 0.0), v))
                except Exception:
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
                except Exception:
                    continue
            line2 = "[GpuServiceClient][CLIENT_PROFILE] " + "; ".join(parts2)
            try:
                print(line2)
            except Exception:
                pass
        return line
