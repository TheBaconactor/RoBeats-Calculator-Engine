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
import time
import random
from concurrent.futures import Future
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Optional

from gear_optimizer.core.env_config import ENV

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
        # request_id -> Future, or (Future, request_type, submit_ts) when profiling is enabled.
        self._pending: dict[int, Any] = {}
        self._lock = threading.Lock()
        self._submit_lock = threading.Lock()
        self._rx_thread: Optional[threading.Thread] = None
        self._running = False

        # Optional latency profiling (end-to-end submit -> response).
        self._profile_enabled = bool(ENV.perf_timing or ENV.gpu_service_profile)
        self._profile_print = bool(ENV.perf_timing or ENV.gpu_service_profile_print)
        self._profile_counts: dict[GpuRequestType, int] = defaultdict(int)
        self._profile_total_sec: dict[GpuRequestType, float] = defaultdict(float)
        self._profile_max_sec: dict[GpuRequestType, float] = defaultdict(float)
        self._profile_samples: dict[GpuRequestType, list[float]] = defaultdict(list)
        self._profile_sample_cap = 5000

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
                    self._profile_counts[req_type] += 1
                    self._profile_total_sec[req_type] += float(latency)
                    if latency > float(self._profile_max_sec[req_type]):
                        self._profile_max_sec[req_type] = float(latency)

                    samples = self._profile_samples[req_type]
                    # Reservoir sampling to cap memory usage in long runs.
                    if len(samples) < int(self._profile_sample_cap):
                        samples.append(float(latency))
                    else:
                        n = int(self._profile_counts[req_type])
                        if n > 0:
                            j = random.randint(0, n - 1)
                            if j < int(self._profile_sample_cap):
                                samples[j] = float(latency)
                except Exception:
                    pass

            if resp.success:
                fut.set_result(resp.result)
            else:
                fut.set_exception(RuntimeError(resp.error or "GPU job failed"))

    def profile_summary(self) -> dict[str, Any]:
        if not self._profile_enabled:
            return {"enabled": False}

        out: dict[str, Any] = {"enabled": True, "by_type": {}}
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
        return line
