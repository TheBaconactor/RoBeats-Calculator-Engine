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
import threading
import time
import random
from concurrent.futures import Future
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Optional

from gear_optimizer.core.env_config import ENV, env_flag

from .gpu_executor import (
    GpuExecutor,
    GpuRequest,
    GpuRequestType,
    GpuResponse,
    get_gpu_executor,
)


_WIN_TIMER_LOCK = threading.Lock()
_WIN_TIMER_USERS = 0
_WIN_TIMER_ACTIVE = False


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
        # request_id -> Future, or (Future, request_type, submit_ts) when profiling is enabled.
        self._pending: dict[int, Any] = {}
        self._lock = threading.Lock()
        self._submit_lock = threading.Lock()
        self._rx_thread: Optional[threading.Thread] = None
        self._running = False
        self._in_process_queues = False

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
        self._fg_coalesce_enabled = env_flag("FG_COALESCE_BREAKPOINTS_BATCH", "1")
        try:
            self._fg_coalesce_max_payloads = int(os.environ.get("FG_COALESCE_BREAKPOINTS_MAX_PAYLOADS", "192") or "192")
        except Exception:
            self._fg_coalesce_max_payloads = 128
        try:
            self._fg_coalesce_max_wait_ms = int(os.environ.get("FG_COALESCE_BREAKPOINTS_MAX_WAIT_MS", "1") or "1")
        except Exception:
            self._fg_coalesce_max_wait_ms = 1
        self._fg_coalesce_max_payloads = max(1, int(self._fg_coalesce_max_payloads))
        self._fg_coalesce_max_wait_ms = max(0, int(self._fg_coalesce_max_wait_ms))
        self._fg_coalesce_payloads: list[dict[str, Any]] = []
        # (future, start, count, submit_ts)
        self._fg_coalesce_slices: list[tuple[Future, int, int, float]] = []
        self._fg_coalesce_first_ts: float | None = None
        self._fg_coalesce_lock = threading.Lock()
        self._fg_coalesce_event = threading.Event()
        self._fg_coalesce_thread: Optional[threading.Thread] = None
        self._fg_high_res_timer_enabled = False

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
        self._rx_thread = threading.Thread(
            target=self._rx_loop,
            name=f"GpuServiceClientRx[{self._worker_id}]",
            daemon=True,
        )
        self._rx_thread.start()

        if self._fg_coalesce_enabled and self._in_process_queues and self._fg_coalesce_thread is None:
            # On Windows the default timer quantum can stretch 1ms waits to ~15ms.
            # Request 1ms period for short coalescing windows.
            if int(self._fg_coalesce_max_wait_ms) <= 4:
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
            fut = None
            if isinstance(entry, tuple) and entry:
                fut = entry[0]
            else:
                fut = entry
            if not fut.done():
                fut.set_exception(RuntimeError("GPU client closed"))

    def submit(self, request_type: GpuRequestType, payload: dict[str, Any]) -> GpuJobHandle:
        if not self._running or self._worker_id is None:
            raise RuntimeError("GpuServiceClient not started")

        request_id = int(next(self._counter))
        t_submit = time.perf_counter() if self._profile_enabled else 0.0
        fut: Future = Future()
        with self._lock:
            if self._profile_enabled:
                self._pending[request_id] = (fut, request_type, float(t_submit))
            else:
                self._pending[request_id] = fut

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

    def submit_solve_genomes_from_registry(self, payload: dict[str, Any]) -> GpuJobHandle:
        return self.submit(GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY, dict(payload or {}))

    def submit_gpu_native_ga_run(self, payload: dict[str, Any]) -> GpuJobHandle:
        return self.submit(GpuRequestType.GPU_NATIVE_GA_RUN, dict(payload or {}))

    def submit_ga_stage_fg_genome_base_stats(self, *, table_slot: int, coords, n_slots: int = 9) -> GpuJobHandle:
        return self.submit(
            GpuRequestType.GA_STAGE_FG_GENOME_BASE_STATS,
            {"table_slot": int(table_slot), "coords": coords, "n_slots": int(n_slots)},
        )

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
    ) -> GpuJobHandle:
        # Accept either Python sequences or pre-packed numpy arrays to avoid per-item tuple packing in hot paths.
        return self.submit(
            GpuRequestType.FG_COMPUTE_BREAKPOINTS,
            {
                "ftff_pairs": ftff_pairs,
                "base_stats_pairs": base_stats_pairs,
                "n_sections": int(n_sections),
                "song_slot": int(song_slot),
                "gem_scale_fever": int(gem_scale_fever),
                "non_fever_base_by_ff": non_fever_base_by_ff,
                "fp_cap_table": fp_cap_table,
            },
        )

    def submit_fg_solve_with_breakpoints(self, payload: dict[str, Any]) -> GpuJobHandle:
        return self.submit(GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS, dict(payload or {}))

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

    def submit_process_force_greats(self, *args: Any, **kwargs: Any) -> GpuJobHandle:
        return self.submit(
            GpuRequestType.PROCESS_FORCE_GREATS,
            {"args": args, "kwargs": kwargs},
        )

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
                        wait_sec = max(0.001, max_wait - (now - float(self._fg_coalesce_first_ts)))
                else:
                    self._fg_coalesce_event.clear()

            if batch is not None:
                payloads_batch, slices_batch = batch
                self._submit_fg_coalesced_batch(payloads_batch, slices_batch)
                continue

            try:
                self._fg_coalesce_event.wait(timeout=wait_sec)
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

            fut = None
            req_type = None
            t_submit = None
            with self._lock:
                entry = self._pending.pop(int(resp.request_id), None)
                if self._profile_enabled and isinstance(entry, tuple) and len(entry) == 3:
                    fut, req_type, t_submit = entry
                else:
                    fut = entry
            if fut is None:
                continue

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
