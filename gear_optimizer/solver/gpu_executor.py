"""
GPU Executor - Cross-process GPU ownership for parallel song processing.

Architecture:
    Song Workers (CPU) --IPC Queue--> GpuExecutor (GPU owner) --> RX 7900 XTX

This ensures only ONE process initializes Taichi/Vulkan, preventing:
- Multiple GPU contexts fighting for resources
- Wasted GPU memory from duplicate Taichi inits
- Potential Vulkan driver conflicts

Usage:
    # In main process before spawning workers:
    executor = get_gpu_executor()
    executor.start()

    # In worker processes:
    if is_gpu_worker_mode():
        result = submit_gpu_work(...)

    # After workers complete:
    executor.stop()
"""

import multiprocessing
import threading
import queue
import os
import atexit
import traceback
import time
from pathlib import Path
from collections import defaultdict, OrderedDict
from time import perf_counter
from dataclasses import dataclass
from typing import Any, Optional, Dict
from enum import Enum

from gear_optimizer.core.env_config import ENV
from gear_optimizer.core.types import JsonDict


class GpuRequestType(Enum):
    """Types of GPU requests that can be submitted."""

    SOLVE_GENOMES_PARALLEL = "solve_genomes_parallel"
    SOLVE_GENOMES_FROM_REGISTRY = "solve_genomes_from_registry"
    OPTIMIZE_GEMS_BATCH = "optimize_gems_batch_gpu"
    LOAD_REF_ARRAYS = "load_ref_arrays"
    PRECOMPUTE_TIMELINE = "precompute_timeline_gpu"
    SOLVE_FORCE_GREATS_FINDER = "solve_force_greats_finder_gpu"
    PROCESS_FORCE_GREATS = "process_force_greats"
    GPU_NATIVE_GA_RUN = "gpu_native_ga_run"
    GA_STAGE_FG_GENOME_BASE_STATS = "ga_stage_fg_genome_base_stats"
    FG_RESET_GLOBAL_BEST = "fg_reset_global_best"
    FG_DOWNLOAD_GLOBAL_BEST = "fg_download_global_best"
    FG_COMPUTE_BREAKPOINTS = "fg_compute_breakpoints"
    FG_SOLVE_WITH_BREAKPOINTS = "fg_solve_with_breakpoints"
    FG_SOLVE_WITH_BREAKPOINTS_BATCH = "fg_solve_with_breakpoints_batch"
    SHUTDOWN = "shutdown"


@dataclass
class GpuRequest:
    """A request to execute on the GPU executor."""

    request_type: GpuRequestType
    request_id: int
    worker_id: int
    payload: JsonDict


@dataclass
class GpuResponse:
    """Response from GPU executor."""

    request_id: int
    success: bool
    result: Any = None
    error: Optional[str] = None


# Global state for worker processes
_WORKER_MODE = False
_WORKER_ID: Optional[int] = None
_REQUEST_QUEUE: Optional[multiprocessing.Queue] = None
_RESPONSE_QUEUE: Optional[multiprocessing.Queue] = None
_REQUEST_COUNTER = 0
_PENDING_RESPONSES: OrderedDict[int, tuple["GpuResponse", float]] = OrderedDict()
_PENDING_TTL_SEC = max(0.0, float(getattr(ENV, "gpu_executor_pending_ttl_sec", 300.0) or 0.0))
_PENDING_MAX = max(0, int(getattr(ENV, "gpu_executor_pending_max", 2048) or 0))


def _prune_pending_responses(now: float | None = None) -> None:
    if not _PENDING_RESPONSES:
        return
    if now is None:
        now = time.monotonic()
    if _PENDING_TTL_SEC > 0.0:
        while _PENDING_RESPONSES:
            _response, ts = next(iter(_PENDING_RESPONSES.values()))
            if (now - ts) <= _PENDING_TTL_SEC:
                break
            _PENDING_RESPONSES.popitem(last=False)
    if _PENDING_MAX > 0:
        while len(_PENDING_RESPONSES) > _PENDING_MAX:
            _PENDING_RESPONSES.popitem(last=False)


def _store_pending_response(response: "GpuResponse") -> None:
    now = time.monotonic()
    _PENDING_RESPONSES[response.request_id] = (response, now)
    _PENDING_RESPONSES.move_to_end(response.request_id)
    _prune_pending_responses(now)


def set_gpu_worker_mode(worker_id: int, request_queue, response_queue):
    """Configure this process as a GPU worker (called after fork/spawn)."""
    global _WORKER_MODE, _WORKER_ID, _REQUEST_QUEUE, _RESPONSE_QUEUE
    _WORKER_MODE = True
    _WORKER_ID = worker_id
    _REQUEST_QUEUE = request_queue
    _RESPONSE_QUEUE = response_queue


def is_gpu_worker_mode() -> bool:
    """Check if running in worker mode (should use IPC for GPU)."""
    return _WORKER_MODE


def is_in_process_gpu_request_queue() -> bool:
    """True when the worker's request/response queues are in-process (thread queues)."""
    return isinstance(_REQUEST_QUEUE, queue.Queue)


def clear_gpu_worker_mode():
    """Clear worker mode (for testing or process reuse)."""
    global _WORKER_MODE, _WORKER_ID, _REQUEST_QUEUE, _RESPONSE_QUEUE, _PENDING_RESPONSES
    _WORKER_MODE = False
    _WORKER_ID = None
    _REQUEST_QUEUE = None
    _RESPONSE_QUEUE = None
    _PENDING_RESPONSES = OrderedDict()


class GpuExecutor:
    """
    Single GPU owner process that handles all Taichi kernel execution.

    Song worker processes submit requests via IPC queue, which are executed
    serially on the GPU thread for maximum throughput.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._request_queue: Optional[multiprocessing.Queue] = None
        self._response_queues: Dict[int, multiprocessing.Queue] = {}
        self._executor_thread: Optional[threading.Thread] = None
        self._running = False
        self._next_worker_id = 0
        self._initialized = True
        self._taichi_ready = False
        self._ready_event = threading.Event()
        self._last_init_error: Optional[str] = None
        self._in_process_queues = False

        # Stats
        self._requests_processed = 0
        from gear_optimizer.core.env_config import ENV

        self._profile_enabled = ENV.gpu_executor_profile
        self._wait_sec = 0.0
        self._exec_sec = 0.0
        self._req_type_counts = defaultdict(int)
        self._req_type_exec_sec = defaultdict(float)
        self._req_type_pack_sec = defaultdict(float)
        self._pack_sec = 0.0
        self._batch_size_counts = defaultdict(int)
        self._batches_observed = 0
        self._batch_size_sum = 0
        self._idle_gaps: list[float] = []
        self._idle_sample_threshold_sec = 0.001
        self._profile_loop_start_ts: Optional[float] = None
        self._profile_first_work_ts: Optional[float] = None
        self._profile_last_work_end_ts: Optional[float] = None
        self._profile_shutdown_ts: Optional[float] = None
        self._idle_transitions_sec = defaultdict(float)
        self._idle_transitions_count = defaultdict(int)
        self._last_work_req_type: Optional[GpuRequestType] = None
        self._fg_tasks_batches = 0
        self._fg_tasks_total = 0
        self._fg_tasks_max = 0
        self._fg_tasks_batch_hist = defaultdict(int)

        # Optional live utilization/trace (opt-in via env vars)
        self._trace_fp = None
        self._trace_start_perf: Optional[float] = None
        self._trace_start_wall: Optional[float] = None
        self._live_enabled = False
        self._live_interval_sec = 1.0
        self._live_last_report_ts: Optional[float] = None
        self._live_wait_sec = 0.0
        self._live_exec_sec = 0.0
        self._live_type_counts = defaultdict(int)

        # Dispatch table (reduces branching in the hot loop and centralizes request routing).
        self._dispatch = {
            GpuRequestType.SOLVE_GENOMES_PARALLEL: self._handle_solve_genomes_parallel,
            GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY: self._handle_solve_genomes_from_registry,
            GpuRequestType.OPTIMIZE_GEMS_BATCH: self._execute_optimize_gems_batch,
            GpuRequestType.LOAD_REF_ARRAYS: self._execute_load_refs,
            GpuRequestType.PRECOMPUTE_TIMELINE: self._execute_precompute_timeline,
            GpuRequestType.SOLVE_FORCE_GREATS_FINDER: self._execute_solve_force_greats_finder,
            GpuRequestType.PROCESS_FORCE_GREATS: self._execute_process_force_greats,
            GpuRequestType.GPU_NATIVE_GA_RUN: self._execute_gpu_native_ga_run,
            GpuRequestType.GA_STAGE_FG_GENOME_BASE_STATS: self._execute_ga_stage_fg_genome_base_stats,
            GpuRequestType.FG_RESET_GLOBAL_BEST: self._execute_fg_reset_global_best,
            GpuRequestType.FG_DOWNLOAD_GLOBAL_BEST: self._execute_fg_download_global_best,
            GpuRequestType.FG_COMPUTE_BREAKPOINTS: self._execute_fg_compute_breakpoints,
            GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS: self._execute_fg_solve_with_breakpoints,
            GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH: self._execute_fg_solve_with_breakpoints_batch,
        }

    def _record_pack(self, request_type: GpuRequestType, dt_sec: float) -> None:
        try:
            dt = float(dt_sec)
        except Exception:
            return
        if dt <= 0.0:
            return
        self._pack_sec += dt
        self._req_type_pack_sec[request_type] += dt

    def _handle_solve_genomes_parallel(self, request: GpuRequest) -> GpuResponse:
        payload = request.payload or {}
        try:
            song_slot = int(payload.get("song_slot", 0) or 0)
        except Exception:
            song_slot = 0
        return self._execute_solve_genomes(request, song_slot=song_slot)

    def _handle_solve_genomes_from_registry(self, request: GpuRequest) -> GpuResponse:
        payload = request.payload or {}
        try:
            song_slot = int(payload.get("song_slot", 0) or 0)
        except Exception:
            song_slot = 0
        return self._execute_solve_genomes_from_registry(request, song_slot=song_slot)

        # Ref-array upload caching: avoid redundant `load_ref_arrays()` calls when inputs are identical.
        # This saves host work and can avoid implicit syncs inside Taichi APIs.
        self._last_ref_arrays_sig: bytes | None = None

    def start(self, *, in_process: bool = False):
        """Start the GPU executor thread in the main process."""
        if self._running:
            return

        # Reset per-run state (GpuExecutor is a singleton and may be started/stopped
        # multiple times within one Python process during profiling/benchmarks).
        self._requests_processed = 0
        self._wait_sec = 0.0
        self._exec_sec = 0.0
        try:
            self._req_type_counts.clear()
            self._req_type_exec_sec.clear()
            self._batch_size_counts.clear()
        except Exception:
            pass
        self._batches_observed = 0
        self._batch_size_sum = 0
        self._idle_gaps = []
        try:
            idle_ms = float(os.environ.get("GPU_EXECUTOR_IDLE_SAMPLE_THRESHOLD_MS", "1.0"))
        except Exception:
            idle_ms = 1.0
        self._idle_sample_threshold_sec = max(0.0, float(idle_ms) / 1000.0)
        self._profile_loop_start_ts = None
        self._profile_first_work_ts = None
        self._profile_last_work_end_ts = None
        self._profile_shutdown_ts = None
        self._idle_transitions_sec = defaultdict(float)
        self._idle_transitions_count = defaultdict(int)
        self._last_work_req_type = None
        self._fg_tasks_batches = 0
        self._fg_tasks_total = 0
        self._fg_tasks_max = 0
        self._fg_tasks_batch_hist = defaultdict(int)
        self._response_queues = {}
        self._next_worker_id = 0
        self._taichi_ready = False
        self._last_init_error = None
        self._ready_event.clear()

        # Optional: emit per-interval utilization and/or write a CSV trace.
        self._live_enabled = str(os.environ.get("GPU_EXECUTOR_LIVE", "0")).strip().lower() in {"1", "true", "yes", "on"}
        try:
            self._live_interval_sec = float(os.environ.get("GPU_EXECUTOR_LIVE_INTERVAL_SEC", "1.0"))
        except Exception:
            self._live_interval_sec = 1.0
        self._live_interval_sec = max(0.1, float(self._live_interval_sec))
        self._live_last_report_ts = None
        self._live_wait_sec = 0.0
        self._live_exec_sec = 0.0
        self._live_type_counts = defaultdict(int)

        self._trace_fp = None
        self._trace_start_perf = None
        self._trace_start_wall = None
        trace_path = str(os.environ.get("GPU_EXECUTOR_TRACE_PATH", "") or "").strip()
        if trace_path:
            try:
                Path(trace_path).parent.mkdir(parents=True, exist_ok=True)
                self._trace_fp = open(trace_path, "a", encoding="utf-8", buffering=1)
                if self._trace_fp.tell() == 0:
                    self._trace_fp.write("wall_ts,rel_ts,event,wait_sec,exec_sec,batch_size,types,in_process\n")
            except Exception:
                self._trace_fp = None

        self._in_process_queues = bool(in_process)
        self._request_queue = queue.Queue() if self._in_process_queues else multiprocessing.Queue()
        self._running = True

        # Run in thread (not process) so we stay in main process
        self._executor_thread = threading.Thread(
            target=self._executor_loop,
            name="GpuExecutorThread",
            daemon=True,
        )
        self._executor_thread.start()
        print("[GpuExecutor] Started")

    def stop(self):
        """Stop the GPU executor."""
        if not self._running:
            return

        # Send shutdown request
        shutdown_req = GpuRequest(
            request_type=GpuRequestType.SHUTDOWN,
            request_id=-1,
            worker_id=-1,
            payload={},
        )
        self._request_queue.put(shutdown_req)

        # Wait for thread to finish
        if self._executor_thread:
            self._executor_thread.join(timeout=10.0)

        self._running = False
        if self._trace_fp is not None:
            try:
                self._trace_fp.close()
            except Exception:
                pass
            self._trace_fp = None
        if self._profile_enabled:
            idle_total = float(sum(self._idle_gaps))
            idle_max = float(max(self._idle_gaps)) if self._idle_gaps else 0.0
            idle_p95 = 0.0
            if self._idle_gaps:
                gaps_sorted = sorted(self._idle_gaps)
                idx = int(round(0.95 * (len(gaps_sorted) - 1)))
                idx = max(0, min(idx, len(gaps_sorted) - 1))
                idle_p95 = float(gaps_sorted[idx])

            idle_initial = 0.0
            if self._profile_loop_start_ts is not None and self._profile_first_work_ts is not None:
                idle_initial = float(max(0.0, self._profile_first_work_ts - self._profile_loop_start_ts))

            idle_tail = 0.0
            if self._profile_shutdown_ts is not None and self._profile_last_work_end_ts is not None:
                idle_tail = float(max(0.0, self._profile_shutdown_ts - self._profile_last_work_end_ts))

            total = self._wait_sec + self._exec_sec
            util = (self._exec_sec / total * 100.0) if total > 0 else 0.0
            avg = (self._exec_sec / self._requests_processed) if self._requests_processed else 0.0
            avg_batch = (self._batch_size_sum / self._batches_observed) if self._batches_observed else 0.0
            top_types = sorted(self._req_type_exec_sec.items(), key=lambda kv: kv[1], reverse=True)[:6]
            top_types_str = ", ".join(f"{t.value}:{self._req_type_counts[t]} ({sec:.2f}s)" for t, sec in top_types)
            top_pack = sorted(self._req_type_pack_sec.items(), key=lambda kv: kv[1], reverse=True)[:6]
            top_pack_str = ", ".join(f"{t.value}:{sec:.2f}s" for t, sec in top_pack if sec > 0)
            top_batch_sizes = sorted(self._batch_size_counts.items(), key=lambda kv: kv[0])[:16]
            batch_hist_str = ", ".join(f"{sz}:{cnt}" for sz, cnt in top_batch_sizes if cnt)
            fg_tasks_avg = (self._fg_tasks_total / self._fg_tasks_batches) if self._fg_tasks_batches else 0.0
            fg_tasks_hist = ""
            if self._fg_tasks_batches:
                try:
                    top_fg = sorted(self._fg_tasks_batch_hist.items(), key=lambda kv: (-kv[1], kv[0]))[:8]
                    fg_tasks_hist = ", ".join(f"{sz}:{cnt}" for sz, cnt in top_fg if cnt)
                except Exception:
                    fg_tasks_hist = ""
            print(
                "[GpuExecutor][PROFILE] "
                f"wait={self._wait_sec:.2f}s exec={self._exec_sec:.2f}s busy={util:.1f}% (executor) "
                f"avg_exec_per_req={avg:.3f}s avg_batch={avg_batch:.2f} "
                f"pack={self._pack_sec:.2f}s pack_types=[{top_pack_str}] "
                f"idle_gaps={len(self._idle_gaps)} idle_sum={idle_total:.2f}s idle_max={idle_max:.3f}s idle_p95={idle_p95:.3f}s "
                f"idle_initial={idle_initial:.3f}s idle_tail={idle_tail:.3f}s "
                f"types=[{top_types_str}] batch_sizes=[{batch_hist_str}] "
                f"fg_task_batches={self._fg_tasks_batches} fg_tasks_total={self._fg_tasks_total} "
                f"fg_tasks_avg={fg_tasks_avg:.1f} fg_tasks_max={self._fg_tasks_max} fg_tasks_hist=[{fg_tasks_hist}]"
            )
            try:
                top_transitions = sorted(self._idle_transitions_sec.items(), key=lambda kv: kv[1], reverse=True)[:6]
                if top_transitions:
                    parts = []
                    for (prev_t, next_t), sec in top_transitions:
                        prev_s = prev_t.value if prev_t is not None else "<start>"
                        next_s = next_t.value if next_t is not None else "<none>"
                        cnt = int(self._idle_transitions_count.get((prev_t, next_t), 0))
                        parts.append(f"{prev_s}->{next_s}:{sec:.2f}s({cnt})")
                    print(f"[GpuExecutor][IDLE] transitions=[{', '.join(parts)}]")
            except Exception:
                pass

        if os.environ.get("TAICHI_KERNEL_PROFILER_PRINT", "0").strip().lower() in {"1", "true", "yes", "on"}:
            try:
                import taichi as ti

                ti.sync()
                ti.profiler.print_kernel_profiler_info()
            except Exception:
                pass

        # Surface transfer/throughput counters from the in-process GPU profiler.
        # (Especially useful in in-flight mode where Windows GPU Engine counters
        # can be noisy and queue/executor timings include host-side work.)
        if ENV.gpu_profiler:
            try:
                from gear_optimizer.solver.gpu_profiler import get_gpu_profiler

                get_gpu_profiler().report(verbose=True)
            except Exception:
                pass
        print(f"[GpuExecutor] Stopped. Processed {self._requests_processed} requests.")

    def register_worker(self) -> tuple:
        """
        Register a new worker and get its communication queues.

        Returns:
            (worker_id, request_queue, response_queue)
        """
        worker_id = self._next_worker_id
        self._next_worker_id += 1

        response_queue = queue.Queue() if self._in_process_queues else multiprocessing.Queue()
        self._response_queues[worker_id] = response_queue

        return worker_id, self._request_queue, response_queue

    def _trace_event(
        self,
        *,
        event: str,
        wait_sec: float = 0.0,
        exec_sec: float = 0.0,
        batch_size: int = 0,
        types: str = "",
    ) -> None:
        fp = self._trace_fp
        if fp is None:
            return
        if self._trace_start_perf is None:
            self._trace_start_perf = perf_counter()
        if self._trace_start_wall is None:
            self._trace_start_wall = time.time()
        rel_ts = perf_counter() - float(self._trace_start_perf)
        wall_ts = time.time()
        try:
            fp.write(
                f"{wall_ts:.6f},{rel_ts:.6f},{event},{float(wait_sec):.6f},{float(exec_sec):.6f},{int(batch_size)},"
                f"{types},{int(bool(self._in_process_queues))}\n"
            )
        except Exception:
            pass

    def _maybe_live_report(self) -> None:
        if not self._live_enabled:
            return
        now = perf_counter()
        if self._live_last_report_ts is None:
            self._live_last_report_ts = now
            return
        if (now - float(self._live_last_report_ts)) < float(self._live_interval_sec):
            return
        total = float(self._live_wait_sec) + float(self._live_exec_sec)
        util = (float(self._live_exec_sec) / total * 100.0) if total > 0 else 0.0
        top_types = sorted(self._live_type_counts.items(), key=lambda kv: kv[1], reverse=True)[:4]
        types_str = ",".join(f"{t.value}:{int(n)}" for t, n in top_types) if top_types else ""
        print(
            f"[GpuExecutor][LIVE] busy={util:.1f}% (executor) wait={self._live_wait_sec * 1000:.1f}ms "
            f"exec={self._live_exec_sec * 1000:.1f}ms types=[{types_str}]"
        )
        self._live_last_report_ts = now
        self._live_wait_sec = 0.0
        self._live_exec_sec = 0.0
        self._live_type_counts = defaultdict(int)

    def unregister_worker(self, worker_id: int):
        """Unregister a worker (cleanup)."""
        if worker_id in self._response_queues:
            del self._response_queues[worker_id]

    def _executor_loop(self):
        """Main GPU execution loop with batch coalescing."""
        # Initialize Taichi ONCE
        try:
            from .taichi_gem.runtime import init_taichi_vulkan

            init_taichi_vulkan()
            self._taichi_ready = True
            self._ready_event.set()
            print("[GpuExecutor] Taichi initialized")
        except Exception as e:
            self._taichi_ready = False
            self._last_init_error = f"{type(e).__name__}: {e}"
            self._running = False
            self._ready_event.set()
            print(f"[GpuExecutor] Taichi init failed: {e}")
            return
        # Warm up FG kernels up-front to avoid the first ForceGreatsFinder call
        # incurring multi-second Taichi JIT latency (which shows up as a GA→FG GPU idle gap).
        if ENV.gpu_executor_warmup_fg:
            try:
                t0 = perf_counter()
                from .taichi_gem.force_greats import fields as fg_fields

                fg_fields.ensure_ready_with_warmup()
                dt_ms = (perf_counter() - t0) * 1000.0
                if ENV.perf_timing:
                    print(f"[GpuExecutor] Warmed FG kernels in {dt_ms:.1f}ms")
            except Exception as e:
                try:
                    print(f"[GpuExecutor] FG warmup failed: {type(e).__name__}: {e}")
                except Exception:
                    pass

        def _try_put_response(req: GpuRequest, resp: GpuResponse) -> bool:
            try:
                q = self._response_queues.get(req.worker_id)
                if q is None:
                    return False
                q.put(resp)
                return True
            except Exception:
                return False

        while self._running:
            batch: list[GpuRequest] = []
            responded_ids: set[int] = set()
            try:
                # Gather batch of pending requests (wait up to 15ms for more)
                # Prefer runtime env overrides so batch sizing can be tuned without a restart.
                # (ENV is a cached snapshot read at import time.)
                # Increased from 10ms to 15ms to improve work coalescing and reduce GPU sync gaps.
                batch_wait_ms = int(getattr(ENV, "gpu_executor_batch_wait_ms", 15) or 15)
                batch_max = int(getattr(ENV, "gpu_executor_max_batch", 8) or 8)
                try:
                    raw = os.environ.get("GPU_EXECUTOR_BATCH_WAIT_MS")
                    if raw is not None and str(raw).strip() != "":
                        batch_wait_ms = int(str(raw).strip())
                except Exception:
                    pass
                try:
                    raw = os.environ.get("GPU_EXECUTOR_MAX_BATCH")
                    if raw is not None and str(raw).strip() != "":
                        batch_max = int(str(raw).strip())
                except Exception:
                    pass
                # In-process mode benefits if we allow larger batches (producer is local and can enqueue quickly).
                if self._in_process_queues and os.environ.get("GPU_EXECUTOR_MAX_BATCH") is None:
                    batch_max = max(int(batch_max), 32)
                if batch_wait_ms < 0:
                    batch_wait_ms = 0
                if batch_max <= 0:
                    batch_max = 1

                if self._profile_enabled and self._profile_loop_start_ts is None:
                    self._profile_loop_start_ts = perf_counter()

                t_wait0 = perf_counter()
                batch = self._gather_batch(max_wait_ms=batch_wait_ms, max_batch_size=batch_max)
                dt_wait = perf_counter() - t_wait0
                self._wait_sec += dt_wait
                self._live_wait_sec += float(dt_wait)

                type_counts = defaultdict(int)
                for r in batch or []:
                    if r.request_type == GpuRequestType.SHUTDOWN:
                        continue
                    type_counts[r.request_type] += 1
                types_str = ";".join(
                    f"{t.value}:{int(n)}" for t, n in sorted(type_counts.items(), key=lambda kv: kv[0].value)
                )
                self._trace_event(
                    event="wait",
                    wait_sec=float(dt_wait),
                    batch_size=len(batch or []),
                    types=types_str,
                )
                self._maybe_live_report()

                if self._profile_enabled:
                    if float(dt_wait) >= float(self._idle_sample_threshold_sec):
                        self._idle_gaps.append(float(dt_wait))
                        next_type = None
                        for r in batch or []:
                            if r.request_type == GpuRequestType.SHUTDOWN:
                                continue
                            next_type = r.request_type
                            break
                        self._idle_transitions_sec[(self._last_work_req_type, next_type)] += float(dt_wait)
                        self._idle_transitions_count[(self._last_work_req_type, next_type)] += 1
                    if (
                        self._profile_first_work_ts is None
                        and batch
                        and not any(r.request_type == GpuRequestType.SHUTDOWN for r in batch)
                    ):
                        self._profile_first_work_ts = perf_counter()

                if self._profile_enabled and batch:
                    bs = len(batch)
                    self._batch_size_counts[bs] += 1
                    self._batches_observed += 1
                    self._batch_size_sum += bs

                if not batch:
                    continue

                # Check for shutdown
                if any(r.request_type == GpuRequestType.SHUTDOWN for r in batch):
                    if self._profile_enabled:
                        self._profile_shutdown_ts = perf_counter()
                    break

                # Group by request type
                solve_requests = [r for r in batch if r.request_type == GpuRequestType.SOLVE_GENOMES_PARALLEL]
                other_requests = [r for r in batch if r.request_type != GpuRequestType.SOLVE_GENOMES_PARALLEL]

                # Execute solve_genomes requests (true batched kernel execution when possible)
                if solve_requests:
                    if len(solve_requests) > 1 and not ENV.gpu_use_ftff_solver:
                        t_exec0 = perf_counter()
                        responses = self._execute_solve_batch(solve_requests)
                        dt_exec = perf_counter() - t_exec0
                        # Attribute exec time proportionally (for profiling only)
                        per_req = dt_exec / max(1, len(solve_requests))
                        self._exec_sec += dt_exec
                        for _ in solve_requests:
                            self._req_type_counts[GpuRequestType.SOLVE_GENOMES_PARALLEL] += 1
                            self._req_type_exec_sec[GpuRequestType.SOLVE_GENOMES_PARALLEL] += per_req
                            self._last_work_req_type = GpuRequestType.SOLVE_GENOMES_PARALLEL

                        # Dispatch responses back to originating workers
                        for req, resp in zip(solve_requests, responses):
                            if resp is None:
                                resp = GpuResponse(
                                    request_id=req.request_id,
                                    success=False,
                                    error="GpuExecutor batch returned no response (internal error)",
                                )
                            if _try_put_response(req, resp):
                                responded_ids.add(int(req.request_id))
                            self._requests_processed += 1
                        self._trace_event(
                            event="exec",
                            exec_sec=float(dt_exec),
                            batch_size=len(solve_requests),
                            types=f"{GpuRequestType.SOLVE_GENOMES_PARALLEL.value}:{len(solve_requests)}",
                        )
                        self._live_exec_sec += float(dt_exec)
                        self._live_type_counts[GpuRequestType.SOLVE_GENOMES_PARALLEL] += len(solve_requests)
                        self._maybe_live_report()
                    else:
                        # FTFF solver mode (or single request): execute each request independently.
                        t_exec0 = perf_counter()
                        responses = []
                        for req in solve_requests:
                            responses.append(self._execute_request(req))
                        dt_exec = perf_counter() - t_exec0
                        self._exec_sec += dt_exec
                        per_req = dt_exec / max(1, len(solve_requests))
                        for _ in solve_requests:
                            self._req_type_counts[GpuRequestType.SOLVE_GENOMES_PARALLEL] += 1
                            self._req_type_exec_sec[GpuRequestType.SOLVE_GENOMES_PARALLEL] += per_req
                            self._last_work_req_type = GpuRequestType.SOLVE_GENOMES_PARALLEL

                        for req, resp in zip(solve_requests, responses):
                            if resp is None:
                                resp = GpuResponse(
                                    request_id=req.request_id,
                                    success=False,
                                    error="GpuExecutor returned no response (internal error)",
                                )
                            if _try_put_response(req, resp):
                                responded_ids.add(int(req.request_id))
                            self._requests_processed += 1
                        self._trace_event(
                            event="exec",
                            exec_sec=float(dt_exec),
                            batch_size=len(solve_requests),
                            types=f"{GpuRequestType.SOLVE_GENOMES_PARALLEL.value}:{len(solve_requests)}",
                        )
                        self._live_exec_sec += float(dt_exec)
                        self._live_type_counts[GpuRequestType.SOLVE_GENOMES_PARALLEL] += len(solve_requests)
                        self._maybe_live_report()

                # Coalesce FG task-only requests (amortize Python packing + dispatch overhead).
                fg_requests = [r for r in other_requests if r.request_type == GpuRequestType.SOLVE_FORCE_GREATS_FINDER]
                rest_requests = [
                    r for r in other_requests if r.request_type != GpuRequestType.SOLVE_FORCE_GREATS_FINDER
                ]

                if fg_requests:
                    t_exec0 = perf_counter()
                    responses = self._coalesce_fg_task_requests(fg_requests)
                    dt_exec = perf_counter() - t_exec0
                    self._exec_sec += dt_exec
                    per_req = dt_exec / max(1, len(fg_requests))
                    for _ in fg_requests:
                        self._req_type_counts[GpuRequestType.SOLVE_FORCE_GREATS_FINDER] += 1
                        self._req_type_exec_sec[GpuRequestType.SOLVE_FORCE_GREATS_FINDER] += per_req
                        self._last_work_req_type = GpuRequestType.SOLVE_FORCE_GREATS_FINDER

                    for req, resp in zip(fg_requests, responses):
                        if resp is None:
                            resp = GpuResponse(
                                request_id=req.request_id,
                                success=False,
                                error="GpuExecutor FG batch returned no response (internal error)",
                            )
                        if _try_put_response(req, resp):
                            responded_ids.add(int(req.request_id))
                        self._requests_processed += 1
                    self._trace_event(
                        event="exec",
                        exec_sec=float(dt_exec),
                        batch_size=len(fg_requests),
                        types=f"{GpuRequestType.SOLVE_FORCE_GREATS_FINDER.value}:{len(fg_requests)}",
                    )
                    self._live_exec_sec += float(dt_exec)
                    self._live_type_counts[GpuRequestType.SOLVE_FORCE_GREATS_FINDER] += len(fg_requests)
                    self._maybe_live_report()

                # Coalesce fused FG bundle requests (breakpoints + solve) to reduce per-request overhead.
                fg_bundle_requests = [
                    r for r in rest_requests if r.request_type == GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH
                ]
                rest_requests = [
                    r for r in rest_requests if r.request_type != GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH
                ]

                if fg_bundle_requests:
                    t_exec0 = perf_counter()
                    responses = self._coalesce_fg_solve_with_breakpoints_batch_requests(fg_bundle_requests)
                    dt_exec = perf_counter() - t_exec0
                    self._exec_sec += dt_exec
                    per_req = dt_exec / max(1, len(fg_bundle_requests))
                    for _ in fg_bundle_requests:
                        self._req_type_counts[GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH] += 1
                        self._req_type_exec_sec[GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH] += per_req
                        self._last_work_req_type = GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH

                    for req, resp in zip(fg_bundle_requests, responses):
                        if resp is None:
                            resp = GpuResponse(
                                request_id=req.request_id,
                                success=False,
                                error="GpuExecutor FG bundle batch returned no response (internal error)",
                            )
                        if _try_put_response(req, resp):
                            responded_ids.add(int(req.request_id))
                        self._requests_processed += 1
                    self._trace_event(
                        event="exec",
                        exec_sec=float(dt_exec),
                        batch_size=len(fg_bundle_requests),
                        types=f"{GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH.value}:{len(fg_bundle_requests)}",
                    )
                    self._live_exec_sec += float(dt_exec)
                    self._live_type_counts[GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH] += len(fg_bundle_requests)
                    self._maybe_live_report()

                # Coalesce solve_genomes_from_registry requests (concatenate small populations).
                reg_requests = [
                    r for r in rest_requests if r.request_type == GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY
                ]
                remaining = [r for r in rest_requests if r.request_type != GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY]

                if reg_requests:
                    t_exec0 = perf_counter()
                    responses = self._coalesce_solve_genomes_from_registry(reg_requests)
                    dt_exec = perf_counter() - t_exec0
                    self._exec_sec += dt_exec
                    per_req = dt_exec / max(1, len(reg_requests))
                    for _ in reg_requests:
                        self._req_type_counts[GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY] += 1
                        self._req_type_exec_sec[GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY] += per_req
                        self._last_work_req_type = GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY

                    for req, resp in zip(reg_requests, responses):
                        if resp is None:
                            resp = GpuResponse(
                                request_id=req.request_id,
                                success=False,
                                error="GpuExecutor registry batch returned no response (internal error)",
                            )
                        if _try_put_response(req, resp):
                            responded_ids.add(int(req.request_id))
                        self._requests_processed += 1
                    self._trace_event(
                        event="exec",
                        exec_sec=float(dt_exec),
                        batch_size=len(reg_requests),
                        types=f"{GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY.value}:{len(reg_requests)}",
                    )
                    self._live_exec_sec += float(dt_exec)
                    self._live_type_counts[GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY] += len(reg_requests)
                    self._maybe_live_report()

                # Process remaining request types individually
                for req in remaining:
                    t_exec0 = perf_counter()
                    response = self._execute_request(req)
                    dt_exec = perf_counter() - t_exec0
                    self._exec_sec += dt_exec
                    self._req_type_counts[req.request_type] += 1
                    self._req_type_exec_sec[req.request_type] += dt_exec
                    self._last_work_req_type = req.request_type

                    if response is None:
                        response = GpuResponse(
                            request_id=req.request_id,
                            success=False,
                            error="GpuExecutor returned no response (internal error)",
                        )
                    if _try_put_response(req, response):
                        responded_ids.add(int(req.request_id))
                    self._requests_processed += 1
                    self._trace_event(
                        event="exec",
                        exec_sec=float(dt_exec),
                        batch_size=1,
                        types=f"{req.request_type.value}:1",
                    )
                    self._live_exec_sec += float(dt_exec)
                    self._live_type_counts[req.request_type] += 1
                    self._maybe_live_report()

                if self._profile_enabled:
                    self._profile_last_work_end_ts = perf_counter()

            except Exception as e:
                # The executor loop must never "drop" a batch on exception; otherwise callers can
                # hang forever waiting for responses. Fail any un-answered requests in this batch.
                err = f"{type(e).__name__}: {e}"
                for req in batch or []:
                    try:
                        if req.request_type == GpuRequestType.SHUTDOWN:
                            continue
                        if int(req.request_id) in responded_ids:
                            continue
                        resp = GpuResponse(request_id=req.request_id, success=False, error=f"GpuExecutor error: {err}")
                        _try_put_response(req, resp)
                    except Exception:
                        continue
                try:
                    print(f"[GpuExecutor] Error: {e}")
                except Exception:
                    pass
                try:
                    traceback.print_exc()
                except Exception:
                    pass

    def _gather_batch(self, max_wait_ms: int = 10, max_batch_size: int = 8) -> list:
        """
        Gather pending requests into a batch for coalesced execution.

        Args:
            max_wait_ms: Max time to wait for additional requests (ms)
            max_batch_size: Max requests per batch

        Returns:
            List of GpuRequest objects
        """
        batch = []
        deadline = perf_counter() + (max_wait_ms / 1000.0)
        coalescable_types = {
            GpuRequestType.SOLVE_GENOMES_PARALLEL,
            GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
            GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
            # FG bundle requests: cheap to enqueue, expensive to dispatch repeatedly.
            GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS,
            GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH,
        }
        # Default to enabled for in-process queues; callers can opt out via env var.
        inproc_coalesce_enabled = str(os.environ.get("GPU_EXECUTOR_INPROC_COALESCE", "1") or "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        try:
            inproc_after_first_ms = int(os.environ.get("GPU_EXECUTOR_INPROC_COALESCE_AFTER_FIRST_MS", "2"))
        except Exception:
            inproc_after_first_ms = 0
        inproc_after_first_ms = max(0, int(inproc_after_first_ms))

        while len(batch) < max_batch_size:
            remaining = deadline - perf_counter()
            if remaining <= 0 and len(batch) > 0:
                break  # Deadline passed, return what we have

            try:
                if self._in_process_queues:
                    # In in-process mode, we generally prefer low latency because the producer is local.
                    # However, some request types are very cheap to enqueue but expensive to dispatch/pack
                    # repeatedly (FG tasks, registry solves, and multi-solve batches). For those, allow a
                    # short coalescing window so we can meaningfully batch/coalesce work.
                    if len(batch) == 0:
                        timeout = max(0.001, remaining)
                    else:
                        if not inproc_coalesce_enabled:
                            timeout = 0.0
                        else:
                            allow_coalesce = True
                            for r in batch:
                                if r.request_type == GpuRequestType.SHUTDOWN:
                                    continue
                                if r.request_type not in coalescable_types:
                                    allow_coalesce = False
                                    break
                            timeout = max(0.001, remaining) if allow_coalesce else 0.0
                else:
                    timeout = max(0.001, remaining) if len(batch) > 0 else 0.1
                request = self._request_queue.get(timeout=timeout)
                batch.append(request)

                # If shutdown, return immediately
                if request.request_type == GpuRequestType.SHUTDOWN:
                    return batch
                # In in-process mode, a lot of batching opportunity exists *after* the first coalescable
                # request arrives (producer is local and can enqueue multiple items quickly). If we spent
                # most of `max_wait_ms` waiting for the first item, refresh the deadline so we still have
                # a small window to grab additional coalescable work.
                if (
                    self._in_process_queues
                    and inproc_coalesce_enabled
                    and len(batch) == 1
                    and inproc_after_first_ms > 0
                    and request.request_type in coalescable_types
                ):
                    deadline = max(deadline, perf_counter() + (float(inproc_after_first_ms) / 1000.0))

            except queue.Empty:
                break  # No more pending requests

        return batch

    @staticmethod
    def _payload_dict(req: "GpuRequest") -> dict[str, Any]:
        payload = getattr(req, "payload", None)
        return payload if isinstance(payload, dict) else {}

    def _coalesce_fg_task_requests(self, requests: list["GpuRequest"]) -> list["GpuResponse"]:
        """
        Coalesce multiple SOLVE_FORCE_GREATS_FINDER requests into a single GPU call when they are task-only.

        This targets the common pattern where callers enqueue many small `fg_tasks` batches, each of which:
          - provides `kwargs['fg_tasks']`
          - does NOT request reset/download in the same call
          - shares the same song/genome inputs and scalar knobs

        IMPORTANT: preserve request ordering relative to "barrier" FG requests (reset/download).
        A download request must never be executed before earlier task-only requests in the same batch,
        or it can read a partial global-best state and return fewer/incorrect results.
        """
        from .taichi_gem.force_greats.api import solve_force_greats_finder_gpu_tasks

        def _extract_task_only(
            req: "GpuRequest",
        ) -> tuple[tuple[Any, ...], dict[str, Any], list[dict[str, Any]]] | None:
            payload = self._payload_dict(req)
            args = payload.get("args", ())
            kwargs = payload.get("kwargs", {})
            if not isinstance(args, (list, tuple)) or len(args) != 7 or not isinstance(kwargs, dict):
                return None
            fg_tasks = kwargs.get("fg_tasks")
            if not isinstance(fg_tasks, (list, tuple)) or not fg_tasks:
                return None
            if bool(kwargs.get("fg_reset_before", False)) or bool(kwargs.get("fg_download_after", False)):
                return None
            return tuple(args), dict(kwargs), list(fg_tasks)

        def _key_for_task_only(args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[Any, ...] | None:
            try:
                genome_stats_list, timestamps_np, great_candidate_timestamps_np, long_notes, last_note_time, _, _ = args
            except Exception:
                return None
            return (
                id(genome_stats_list),
                id(timestamps_np),
                id(great_candidate_timestamps_np),
                int(kwargs.get("n_sections", 0) or 0),
                int(kwargs.get("song_slot", 0) or 0),
                int(kwargs.get("total_budget", 90) or 90),
                int(kwargs.get("gem_scale_fever", 3) or 3),
                bool(kwargs.get("pair_caps_from_timeline", False)),
                id(kwargs.get("pair_caps_grid")),
                id(kwargs.get("ref_arrays")),
                int(kwargs.get("is_p_ft", 0) or 0),
                int(kwargs.get("is_s_ft", 0) or 0),
                int(kwargs.get("is_p_ff", 0) or 0),
                int(kwargs.get("is_s_ff", 0) or 0),
                int(kwargs.get("is_p_pp", 0) or 0),
                int(kwargs.get("is_s_pp", 0) or 0),
                int(kwargs.get("is_p_cm", 0) or 0),
                int(kwargs.get("is_s_cm", 0) or 0),
                int(kwargs.get("is_p_fm", 0) or 0),
                int(kwargs.get("is_s_fm", 0) or 0),
                int(kwargs.get("is_p_ov", 0) or 0),
                int(kwargs.get("is_s_ov", 0) or 0),
                int(kwargs.get("base_cfg_offset", 0) or 0),
                kwargs.get("cfg_chunk"),
                int(long_notes or 0),
                float(last_note_time or 0.0),
            )

        def _flush_task_only_segment(
            seg: list[tuple["GpuRequest", tuple[Any, ...], dict[str, Any], list[dict[str, Any]]]],
        ) -> dict[int, "GpuResponse"]:
            """
            Execute a contiguous segment of task-only requests.

            We can safely reorder within this segment because every request is task-only
            (accumulate_global, no reset/download). Barrier requests are executed by the
            caller outside this function in strict order.
            """
            if not seg:
                return {}

            groups: dict[
                tuple[Any, ...],
                list[tuple["GpuRequest", tuple[Any, ...], dict[str, Any], list[dict[str, Any]]]],
            ] = {}
            out_by_id: dict[int, GpuResponse] = {}

            for req, args, kwargs, fg_tasks in seg:
                k = _key_for_task_only(args, kwargs)
                if k is None:
                    # Shouldn't happen for task-only, but stay robust.
                    out_by_id[int(req.request_id)] = self._execute_request(req)
                    continue
                groups.setdefault(k, []).append((req, args, kwargs, fg_tasks))

            for _k, items in groups.items():
                if not items:
                    continue
                if len(items) == 1:
                    req0 = items[0][0]
                    out_by_id[int(req0.request_id)] = self._execute_request(req0)
                    continue

                req0, args0, kwargs0, _tasks0 = items[0]
                genome_stats_list, timestamps_np, great_candidate_timestamps_np, long_notes, last_note_time, _, _ = (
                    args0
                )

                merged_tasks: list[dict[str, Any]] = []
                upload_any = False
                for _req, _args, _kwargs, _fg_tasks in items:
                    merged_tasks.extend(list(_fg_tasks))
                    upload_any = upload_any or bool(_kwargs.get("upload_genome_stats", True))

                kwargs_local = dict(kwargs0)
                kwargs_local.pop("fg_tasks", None)
                kwargs_local["accumulate_global"] = True
                kwargs_local["return_raw"] = True
                kwargs_local["upload_genome_stats"] = bool(upload_any)
                kwargs_local.pop("fg_reset_before", None)
                kwargs_local.pop("fg_download_after", None)
                kwargs_local.pop("fg_download_topk", None)
                kwargs_local.pop("fg_download_base_scores", None)
                kwargs_local.pop("fg_download_keep_mask", None)

                t_pack0 = perf_counter()
                try:
                    solve_force_greats_finder_gpu_tasks(
                        genome_stats_list,
                        timestamps_np,
                        great_candidate_timestamps_np,
                        int(long_notes),
                        float(last_note_time),
                        fg_tasks=merged_tasks,
                        **kwargs_local,
                    )
                    self._record_pack(GpuRequestType.SOLVE_FORCE_GREATS_FINDER, perf_counter() - t_pack0)
                    for req, *_rest in items:
                        out_by_id[int(req.request_id)] = GpuResponse(
                            request_id=req.request_id, success=True, result=None
                        )
                except Exception as e2:
                    self._record_pack(GpuRequestType.SOLVE_FORCE_GREATS_FINDER, perf_counter() - t_pack0)
                    err = f"{type(e2).__name__}: {e2}"
                    for req, *_rest in items:
                        out_by_id[int(req.request_id)] = GpuResponse(
                            request_id=req.request_id, success=False, error=err
                        )

            return out_by_id

        # Execute in original request order, treating any non-task-only request as a barrier.
        # This preserves "reset -> tasks -> download" correctness while still coalescing
        # bursts of task-only work between barriers.
        responses_by_id: dict[int, GpuResponse] = {}
        segment: list[tuple["GpuRequest", tuple[Any, ...], dict[str, Any], list[dict[str, Any]]]] = []

        def _flush_segment() -> None:
            nonlocal segment
            if not segment:
                return
            seg_resps = _flush_task_only_segment(segment)
            responses_by_id.update({int(k): v for k, v in seg_resps.items() if v is not None})
            segment = []

        for req in requests:
            extracted = _extract_task_only(req)
            if extracted is not None:
                args, kwargs, fg_tasks = extracted
                segment.append((req, args, kwargs, fg_tasks))
                continue

            # Barrier: flush any prior coalescable task-only segment, then execute this request.
            _flush_segment()
            resp = self._execute_request(req)
            responses_by_id[int(req.request_id)] = resp

        _flush_segment()

        # Preserve original ordering in the return list.
        return [responses_by_id.get(int(req.request_id)) for req in requests]

    def _coalesce_fg_solve_with_breakpoints_batch_requests(self, requests: list["GpuRequest"]) -> list["GpuResponse"]:
        """
        Coalesce multiple `FG_SOLVE_WITH_BREAKPOINTS_BATCH` requests.

        Each request contains `payload['payloads'] = list[dict]` (one dict per fused solve). We flatten all
        payloads, execute them sequentially on the owner thread, and then split the results back into
        per-request slices.

        This reduces request queue overhead and prevents small FG jobs from creating GPU bubbles when many
        FG jobs are produced concurrently (in-flight drain mode).
        """
        if not requests:
            return []

        # Only valid in in-process mode; fall back gracefully otherwise.
        if not self._in_process_queues:
            return [self._execute_request(req) for req in requests]

        merged_payloads: list[dict[str, Any]] = []
        slices: list[tuple["GpuRequest", int, int]] = []
        fallback: list[GpuResponse] = []

        for req in requests:
            payload = self._payload_dict(req)
            payloads = payload.get("payloads")
            if not isinstance(payloads, (list, tuple)) or not payloads:
                fallback.append(self._execute_request(req))
                continue
            ok = True
            for p in payloads:
                if not isinstance(p, dict):
                    ok = False
                    break
            if not ok:
                fallback.append(self._execute_request(req))
                continue

            start = len(merged_payloads)
            merged_payloads.extend(list(payloads))
            slices.append((req, start, int(len(payloads))))

        out: list[GpuResponse] = []
        out.extend(fallback)

        # If nothing to coalesce, we're done.
        if not slices:
            by_id = {r.request_id: r for r in out if r is not None}
            return [by_id.get(req.request_id) for req in requests]

        # Single request: run it normally (avoids surprising behavior changes on edge cases).
        if len(slices) == 1:
            out.append(self._execute_request(slices[0][0]))
            by_id = {r.request_id: r for r in out if r is not None}
            return [by_id.get(req.request_id) for req in requests]

        try:
            merged_req = GpuRequest(
                request_type=GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH,
                request_id=-1,
                worker_id=-1,
                payload={"payloads": merged_payloads},
            )
            merged_resp = self._execute_fg_solve_with_breakpoints_batch(merged_req)
            if not getattr(merged_resp, "success", False):
                raise RuntimeError(f"merged FG bundle failed: {merged_resp.error}")
            merged_results = getattr(merged_resp, "result", None)
            if not isinstance(merged_results, list):
                raise TypeError("merged FG bundle returned non-list result")
            if int(len(merged_results)) != int(len(merged_payloads)):
                raise RuntimeError("merged FG bundle length mismatch")

            for req, start, n in slices:
                out.append(
                    GpuResponse(
                        request_id=req.request_id,
                        success=True,
                        result=list(merged_results[int(start) : int(start) + int(n)]),
                    )
                )
        except Exception:
            # Preserve robustness: if batching fails, execute each request independently.
            out = [self._execute_request(req) for req in requests]

        by_id = {r.request_id: r for r in out if r is not None}
        return [by_id.get(req.request_id) for req in requests]

    def _coalesce_solve_genomes_from_registry(self, requests: list["GpuRequest"]) -> list["GpuResponse"]:
        """
        Coalesce multiple SOLVE_GENOMES_FROM_REGISTRY requests by concatenating small population batches.

        This is conservative and only merges requests that share the same per-song inputs by object identity.
        """
        import numpy as np

        from .taichi_gem.api import (
            ga_upload_base_fixed_stats,
            ga_upload_item_stats,
            load_ref_arrays,
            solve_genomes_from_registry,
        )
        from .taichi_gem import fields as gem_fields

        def _key(req: "GpuRequest") -> tuple[Any, ...] | None:
            p = self._payload_dict(req)
            pop = p.get("population_indices")
            if pop is None:
                return None
            try:
                return (
                    int(p.get("song_slot", 0) or 0),
                    int(p.get("total_budget", 90) or 90),
                    int(p.get("gem_scale_fever", 3) or 3),
                    int(p.get("is_p_ft", 0) or 0),
                    int(p.get("is_s_ft", 0) or 0),
                    int(p.get("is_p_ff", 0) or 0),
                    int(p.get("is_s_ff", 0) or 0),
                    int(p.get("is_p_pp", 0) or 0),
                    int(p.get("is_s_pp", 0) or 0),
                    int(p.get("is_p_cm", 0) or 0),
                    int(p.get("is_s_cm", 0) or 0),
                    int(p.get("is_p_fm", 0) or 0),
                    int(p.get("is_s_fm", 0) or 0),
                    int(p.get("is_p_ov", 0) or 0),
                    int(p.get("is_s_ov", 0) or 0),
                    id(p.get("timeline_grid")),
                    id(p.get("ref_arrays")),
                    id(p.get("item_stats")),
                    id(p.get("slot_start")),
                    id(p.get("slot_count")),
                    id(p.get("base_fixed_stats")),
                )
            except Exception:
                return None

        groups: dict[tuple[Any, ...], list[GpuRequest]] = {}
        for req in requests:
            k = _key(req)
            groups.setdefault(k if k is not None else ("__solo__", req.request_id), []).append(req)

        out: list[GpuResponse] = []
        max_genomes = int(getattr(gem_fields, "MAX_GENOMES", 4096) or 4096)

        for k, group in groups.items():
            if not group:
                continue
            if len(group) == 1 or (isinstance(k, tuple) and k and k[0] == "__solo__"):
                out.append(self._execute_request(group[0]))
                continue

            p0 = self._payload_dict(group[0])
            song_slot = int(p0.get("song_slot", 0) or 0)
            total_budget = int(p0.get("total_budget", 90) or 90)
            gem_scale_fever = int(p0.get("gem_scale_fever", 3) or 3)

            ref_arrays = p0.get("ref_arrays")
            sig = self._ref_arrays_sig(ref_arrays) if isinstance(ref_arrays, dict) else None
            if sig is None or sig != self._last_ref_arrays_sig:
                if isinstance(ref_arrays, dict):
                    load_ref_arrays(ref_arrays)
                self._last_ref_arrays_sig = sig

            if "item_stats" in p0 and "slot_start" in p0 and "slot_count" in p0:
                ga_upload_item_stats(p0["item_stats"], p0["slot_start"], p0["slot_count"])
            if "base_fixed_stats" in p0:
                ga_upload_base_fixed_stats(p0["base_fixed_stats"])

            i = 0
            while i < len(group):
                chunk: list[GpuRequest] = []
                n_total = 0
                while i < len(group):
                    p = self._payload_dict(group[i])
                    pop_arr = np.asarray(p.get("population_indices"), dtype=np.int32)
                    if pop_arr.ndim != 2 or int(pop_arr.shape[1]) != 9:
                        break
                    n = int(pop_arr.shape[0])
                    if n <= 0:
                        break
                    if n_total + n > max_genomes and chunk:
                        break
                    if n_total + n > max_genomes and not chunk:
                        out.append(self._execute_request(group[i]))
                        i += 1
                        continue
                    chunk.append(group[i])
                    n_total += n
                    i += 1

                if not chunk:
                    break

                staging = np.empty((int(n_total), 9), dtype=np.int32)
                spans: list[tuple[int, int]] = []
                cur = 0
                ok = True
                t_pack0 = perf_counter()
                for req in chunk:
                    p = self._payload_dict(req)
                    pop_arr = np.asarray(p.get("population_indices"), dtype=np.int32)
                    n = int(pop_arr.shape[0])
                    if pop_arr.ndim != 2 or int(pop_arr.shape[1]) != 9 or n <= 0:
                        ok = False
                        break
                    staging[cur : cur + n, :] = pop_arr[:n, :]
                    spans.append((cur, cur + n))
                    cur += n

                if not ok or cur <= 0:
                    for req in chunk:
                        out.append(self._execute_request(req))
                    continue

                try:
                    t_kernel0 = perf_counter()
                    merged = solve_genomes_from_registry(
                        population_indices=staging,
                        timeline_grid=p0["timeline_grid"],
                        is_p_ft=p0["is_p_ft"],
                        is_s_ft=p0["is_s_ft"],
                        is_p_ff=p0["is_p_ff"],
                        is_s_ff=p0["is_s_ff"],
                        is_p_pp=p0["is_p_pp"],
                        is_s_pp=p0["is_s_pp"],
                        is_p_cm=p0["is_p_cm"],
                        is_s_cm=p0["is_s_cm"],
                        is_p_fm=p0["is_p_fm"],
                        is_s_fm=p0["is_s_fm"],
                        is_p_ov=p0["is_p_ov"],
                        is_s_ov=p0["is_s_ov"],
                        ref_arrays=p0["ref_arrays"],
                        total_budget=total_budget,
                        gem_scale_fever=gem_scale_fever,
                        song_slot=song_slot,
                    )
                    dt_kernel = perf_counter() - t_kernel0
                    dt_total = perf_counter() - t_pack0
                    self._record_pack(GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY, max(0.0, dt_total - dt_kernel))
                    for req, (a, b) in zip(chunk, spans):
                        out.append(GpuResponse(request_id=req.request_id, success=True, result=merged[a:b]))
                except Exception as e2:
                    self._record_pack(GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY, perf_counter() - t_pack0)
                    err = f"{type(e2).__name__}: {e2}"
                    for req in chunk:
                        out.append(GpuResponse(request_id=req.request_id, success=False, error=err))

        by_id = {r.request_id: r for r in out}
        return [by_id.get(req.request_id) for req in requests]

    def _execute_solve_batch(self, requests: list) -> list:
        """
        Execute multiple SOLVE_GENOMES_PARALLEL requests in a single batched kernel.

        Each request gets assigned a song_slot (0-7) for its grid data.
        All requests' genomes are combined into a mega-batch.

        Args:
            requests: List of GpuRequest objects (all SOLVE_GENOMES_PARALLEL)

        Returns:
            List of GpuResponse objects, one per request
        """
        from .taichi_gem.api import solve_genomes_parallel_merged

        # If callers provide explicit `song_slot` allocations (in-flight pipeline),
        # don't merge: merged solver assigns slots 0..N-1 and would defeat slot-local
        # caching / VRAM residency.
        def _nonzero_slot(req: GpuRequest) -> bool:
            try:
                payload = req.payload or {}
                return int(payload.get("song_slot", 0) or 0) != 0
            except Exception:
                return False

        if any(_nonzero_slot(r) for r in requests):
            out: list[GpuResponse] = []
            for req in requests:
                try:
                    slot = 0
                    try:
                        slot = int((req.payload or {}).get("song_slot", 0) or 0)
                    except Exception:
                        slot = 0
                    out.append(self._execute_solve_genomes(req, song_slot=slot))
                except Exception as e2:
                    out.append(
                        GpuResponse(
                            request_id=req.request_id,
                            success=False,
                            error=f"{type(e2).__name__}: {e2}",
                        )
                    )
            return out

        # Partition into compatible batches (same budget/scales; ref arrays are checked by content in merged solver).
        groups: dict[tuple[int, int], list[GpuRequest]] = {}
        for req in requests:
            p = req.payload
            key = (int(p.get("total_budget", 90)), int(p.get("gem_scale_fever", 3)))
            groups.setdefault(key, []).append(req)

        out: list[GpuResponse] = []
        log_batches = ENV.gpu_batch_log
        for key, group in groups.items():
            # If group is too large for available slots, split further.
            try:
                from .taichi_gem import fields as _gem_fields

                max_slots = int(getattr(_gem_fields, "MAX_SONG_SLOTS", 8) or 8)
            except Exception:
                max_slots = 8
            for start in range(0, len(group), max_slots):
                sub = group[start : start + max_slots]
                try:
                    t_pack0 = perf_counter()
                    if log_batches and len(sub) > 1:
                        print(
                            f"[GpuExecutor][BATCH] requests={len(sub)} budget={int(sub[0].payload.get('total_budget', 90))} scale={int(sub[0].payload.get('gem_scale_fever', 3))}"
                        )
                    # Require calc_song dict inputs for true batching; otherwise fall back.
                    if any(not isinstance(r.payload.get("timeline_grid"), dict) for r in sub):
                        raise ValueError("non-dict timeline_grid in batch")

                    total_budget = int(sub[0].payload.get("total_budget", 90))
                    gem_scale_fever = int(sub[0].payload.get("gem_scale_fever", 3))
                    t_kernel0 = perf_counter()
                    merged_results = solve_genomes_parallel_merged(
                        [r.payload for r in sub],
                        total_budget=total_budget,
                        gem_scale_fever=gem_scale_fever,
                    )
                    dt_kernel = perf_counter() - t_kernel0
                    dt_total = perf_counter() - t_pack0
                    self._record_pack(GpuRequestType.SOLVE_GENOMES_PARALLEL, max(0.0, dt_total - dt_kernel))
                    for req, res in zip(sub, merged_results):
                        out.append(
                            GpuResponse(
                                request_id=req.request_id,
                                success=True,
                                result=res,
                            )
                        )
                except Exception:
                    # Count the time spent trying to pack/merge even if we fall back.
                    try:
                        self._record_pack(GpuRequestType.SOLVE_GENOMES_PARALLEL, perf_counter() - t_pack0)
                    except Exception:
                        pass
                    # Conservative fallback: process each request individually.
                    for req in sub:
                        try:
                            out.append(self._execute_solve_genomes(req, song_slot=0))
                        except Exception as e2:
                            out.append(
                                GpuResponse(
                                    request_id=req.request_id,
                                    success=False,
                                    error=f"{type(e2).__name__}: {e2}",
                                )
                            )

        # Preserve original request order for caller.
        by_id = {r.request_id: r for r in out}
        return [by_id.get(req.request_id) for req in requests]

    def _default_song_slot_for_worker(self, worker_id: int) -> int:
        """
        Pick a stable per-worker song_slot in [1, MAX_SONG_SLOTS-1].

        Motivation: in spawn-based parallel processing, different workers submit interleaved
        `calc_song` dict requests. If everything uses song_slot=0, the timeline cache in
        `precompute_timeline_gpu()` thrashes (cache is keyed by (song_slot, song_key)),
        forcing repeated recomputation and leaving the GPU underfed by avoidable work.
        """
        try:
            from .taichi_gem.fields import MAX_SONG_SLOTS

            max_slots = int(MAX_SONG_SLOTS)
        except Exception:
            max_slots = 8

        if max_slots <= 1:
            return 0

        try:
            wid = int(worker_id)
        except Exception:
            return 0

        return 1 + (wid % (max_slots - 1))

    def _execute_request(self, request: GpuRequest) -> GpuResponse:
        """Execute a single GPU request."""
        try:
            handler = self._dispatch.get(request.request_type)
            if handler is None:
                return GpuResponse(
                    request_id=request.request_id,
                    success=False,
                    error=f"Unknown request type: {request.request_type}",
                )
            return handler(request)
        except Exception as e:
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error=f"{type(e).__name__}: {e}",
            )

    def _execute_solve_genomes(self, request: GpuRequest, song_slot: int = 0) -> GpuResponse:
        """Execute solve_genomes_parallel on GPU.

        Args:
            request: The GPU request
            song_slot: Grid slot to use for this song (0-7, default 0)
        """
        from .taichi_gem.api import solve_genomes_parallel, solve_genomes_with_ftff, load_ref_arrays

        payload = request.payload

        # Load ref arrays if provided (skip redundant reloads by fingerprint).
        if "ref_arrays" in payload:
            ref_arrays = payload["ref_arrays"]
            sig = self._ref_arrays_sig(ref_arrays)
            if sig is None or sig != self._last_ref_arrays_sig:
                load_ref_arrays(ref_arrays)
                self._last_ref_arrays_sig = sig

        # Run the solver with song_slot
        song_slot = int(payload.get("song_slot", song_slot) or 0)
        # IPC optimization: choose a stable per-worker song_slot so timeline precompute caches
        # don't thrash across interleaved songs (precompute_timeline_gpu caches per slot).
        if (
            song_slot == 0
            and (not self._in_process_queues)
            and request.worker_id is not None
            and isinstance(payload.get("timeline_grid"), dict)
        ):
            song_slot = int(self._default_song_slot_for_worker(int(request.worker_id)))
        solve_fn = solve_genomes_with_ftff if ENV.gpu_use_ftff_solver else solve_genomes_parallel
        results = solve_fn(
            genome_stats_list=payload["genome_stats_list"],
            timeline_grid=payload["timeline_grid"],
            is_p_ft=payload["is_p_ft"],
            is_s_ft=payload["is_s_ft"],
            is_p_ff=payload["is_p_ff"],
            is_s_ff=payload["is_s_ff"],
            is_p_pp=payload["is_p_pp"],
            is_s_pp=payload["is_s_pp"],
            is_p_cm=payload["is_p_cm"],
            is_s_cm=payload["is_s_cm"],
            is_p_fm=payload["is_p_fm"],
            is_s_fm=payload["is_s_fm"],
            is_p_ov=payload["is_p_ov"],
            is_s_ov=payload["is_s_ov"],
            ref_arrays=payload["ref_arrays"],
            total_budget=payload.get("total_budget", 90),
            gem_scale_fever=payload.get("gem_scale_fever", 3),
            song_slot=song_slot,  # Pass song slot for batch coalescing
        )

        return GpuResponse(
            request_id=request.request_id,
            success=True,
            result=results,
        )

    def _execute_solve_genomes_from_registry(self, request: GpuRequest, song_slot: int = 0) -> GpuResponse:
        """Execute solve_genomes_from_registry on GPU (GPU-resident stat aggregation path)."""
        from .taichi_gem.api import (
            ga_upload_base_fixed_stats,
            ga_upload_item_stats,
            load_ref_arrays,
            solve_genomes_from_registry,
        )

        payload = request.payload or {}

        if "ref_arrays" in payload:
            ref_arrays = payload["ref_arrays"]
            sig = self._ref_arrays_sig(ref_arrays)
            if sig is None or sig != self._last_ref_arrays_sig:
                load_ref_arrays(ref_arrays)
                self._last_ref_arrays_sig = sig

        if "item_stats" in payload and "slot_start" in payload and "slot_count" in payload:
            ga_upload_item_stats(payload["item_stats"], payload["slot_start"], payload["slot_count"])

        if "base_fixed_stats" in payload:
            ga_upload_base_fixed_stats(payload["base_fixed_stats"])

        song_slot = int(payload.get("song_slot", song_slot) or 0)
        if (
            song_slot == 0
            and (not self._in_process_queues)
            and request.worker_id is not None
            and isinstance(payload.get("timeline_grid"), dict)
        ):
            song_slot = int(self._default_song_slot_for_worker(int(request.worker_id)))
        results = solve_genomes_from_registry(
            population_indices=payload["population_indices"],
            timeline_grid=payload["timeline_grid"],
            is_p_ft=payload["is_p_ft"],
            is_s_ft=payload["is_s_ft"],
            is_p_ff=payload["is_p_ff"],
            is_s_ff=payload["is_s_ff"],
            is_p_pp=payload["is_p_pp"],
            is_s_pp=payload["is_s_pp"],
            is_p_cm=payload["is_p_cm"],
            is_s_cm=payload["is_s_cm"],
            is_p_fm=payload["is_p_fm"],
            is_s_fm=payload["is_s_fm"],
            is_p_ov=payload["is_p_ov"],
            is_s_ov=payload["is_s_ov"],
            ref_arrays=payload["ref_arrays"],
            total_budget=payload.get("total_budget", 90),
            gem_scale_fever=payload.get("gem_scale_fever", 3),
            song_slot=song_slot,
        )

        return GpuResponse(
            request_id=request.request_id,
            success=True,
            result=results,
        )

    def _execute_solve_force_greats_finder(self, request: GpuRequest) -> GpuResponse:
        """Execute solve_force_greats_finder_gpu on GPU."""
        from .taichi_gem.force_greats.api import (
            fg_download_global_best,
            fg_reset_global_best,
            solve_force_greats_finder_gpu,
            solve_force_greats_finder_gpu_tasks,
        )

        payload = request.payload or {}
        args = payload.get("args", ())
        kwargs = payload.get("kwargs", {})

        if not isinstance(args, (list, tuple)):
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="Invalid payload for SOLVE_FORCE_GREATS_FINDER (expected args list/tuple)",
            )
        if not isinstance(kwargs, dict):
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="Invalid payload for SOLVE_FORCE_GREATS_FINDER (expected kwargs dict)",
            )

        fg_tasks = kwargs.pop("fg_tasks", None)
        if fg_tasks is not None:
            if not isinstance(fg_tasks, (list, tuple)):
                return GpuResponse(
                    request_id=request.request_id,
                    success=False,
                    error="Invalid payload for SOLVE_FORCE_GREATS_FINDER (fg_tasks must be list/tuple)",
                )

            reset_before = bool(kwargs.pop("fg_reset_before", False))
            download_after = bool(kwargs.pop("fg_download_after", False))
            if self._profile_enabled:
                try:
                    task_count = int(len(fg_tasks))
                except Exception:
                    task_count = 0
                self._fg_tasks_batches += 1
                self._fg_tasks_total += task_count
                if task_count > self._fg_tasks_max:
                    self._fg_tasks_max = task_count
                self._fg_tasks_batch_hist[task_count] += 1

            if len(args) != 7:
                return GpuResponse(
                    request_id=request.request_id,
                    success=False,
                    error="Invalid payload for SOLVE_FORCE_GREATS_FINDER (expected 7 positional args)",
                )

            (
                genome_stats_list,
                timestamps_np,
                great_candidate_timestamps_np,
                long_notes,
                last_note_time,
                _fg_configs,
                _ftff_pairs,
            ) = args

            try:
                if genome_stats_list is None:
                    n_genomes = int(kwargs.get("n_genomes_override", 0) or 0)
                else:
                    n_genomes = int(len(genome_stats_list))
            except Exception:
                n_genomes = 0
            if n_genomes <= 0:
                return GpuResponse(
                    request_id=request.request_id,
                    success=False,
                    error="Invalid payload for SOLVE_FORCE_GREATS_FINDER (n_genomes <= 0)",
                )

            kwargs_local = dict(kwargs)
            # Optional reduced-download knobs (consumed only at download_after time).
            # Pop these so they are NOT forwarded into solve_force_greats_finder_gpu_tasks.
            download_topk = kwargs_local.pop("fg_download_topk", None)
            download_base_scores = kwargs_local.pop("fg_download_base_scores", None)
            download_keep_mask = kwargs_local.pop("fg_download_keep_mask", None)
            kwargs_local["accumulate_global"] = True
            kwargs_local["return_raw"] = True
            # Allow callers to keep genome stats GPU-resident across multiple requests.
            # Default remains True for safety.
            kwargs_local["upload_genome_stats"] = bool(kwargs_local.get("upload_genome_stats", True))
            try:
                fg_session_slot = int(kwargs_local.get("song_slot", 0) or 0)
            except Exception:
                fg_session_slot = 0

            if reset_before:
                fg_reset_global_best(int(n_genomes), session_slot=int(fg_session_slot))

            if fg_tasks:
                solve_force_greats_finder_gpu_tasks(
                    genome_stats_list,
                    timestamps_np,
                    great_candidate_timestamps_np,
                    int(long_notes),
                    float(last_note_time),
                    fg_tasks=fg_tasks,
                    **kwargs_local,
                )

            result = None
            if download_after:
                try:
                    if download_topk is not None and download_base_scores is not None:
                        result = fg_download_global_best(
                            int(n_genomes),
                            session_slot=int(fg_session_slot),
                            topk=int(download_topk),
                            base_scores=download_base_scores,
                            keep_mask=download_keep_mask,
                        )
                    else:
                        result = fg_download_global_best(int(n_genomes), session_slot=int(fg_session_slot))
                except Exception:
                    # Fall back to full download for robustness.
                    result = fg_download_global_best(int(n_genomes), session_slot=int(fg_session_slot))

            return GpuResponse(request_id=request.request_id, success=True, result=result)

        ftff_chunks = kwargs.pop("ftff_chunks", None)
        if ftff_chunks is not None:
            if not isinstance(ftff_chunks, (list, tuple)):
                return GpuResponse(
                    request_id=request.request_id,
                    success=False,
                    error="Invalid payload for SOLVE_FORCE_GREATS_FINDER (ftff_chunks must be list/tuple)",
                )
            base_args = list(args)
            if len(base_args) < 7:
                return GpuResponse(
                    request_id=request.request_id,
                    success=False,
                    error="Invalid payload for SOLVE_FORCE_GREATS_FINDER (ftff_chunks requires >=7 args)",
                )
            result = None
            for chunk in ftff_chunks:
                base_args[6] = chunk
                result = solve_force_greats_finder_gpu(*base_args, **kwargs)
        else:
            result = solve_force_greats_finder_gpu(*args, **kwargs)
        return GpuResponse(
            request_id=request.request_id,
            success=True,
            result=result,
        )

    def _execute_process_force_greats(self, request: GpuRequest) -> GpuResponse:
        """
        Execute the full `process_force_greats()` helper on the GPU-owner thread.

        This is only supported when using in-process (thread) queues because the
        payload can contain large Python objects and closures that are not
        pickle-safe over multiprocessing IPC.
        """
        if not self._in_process_queues:
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="PROCESS_FORCE_GREATS is only supported with in-process queues",
            )

        from gear_optimizer.helpers.song_helpers.force_greats import process_force_greats

        payload = request.payload or {}
        args = payload.get("args", ())
        kwargs = payload.get("kwargs", {})

        if not isinstance(args, (list, tuple)):
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="Invalid payload for PROCESS_FORCE_GREATS (expected args list/tuple)",
            )
        if not isinstance(kwargs, dict):
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="Invalid payload for PROCESS_FORCE_GREATS (expected kwargs dict)",
            )

        result = process_force_greats(*args, **kwargs)
        return GpuResponse(
            request_id=request.request_id,
            success=True,
            result=result,
        )

    def _execute_precompute_timeline(self, request: GpuRequest) -> GpuResponse:
        """Execute precompute_timeline_gpu on GPU (for slot warmup/prefetch)."""
        from .taichi_gem.api.timeline import precompute_timeline_gpu

        payload = request.payload or {}
        calc_song = payload.get("calc_song")
        ref_arrays = payload.get("ref_arrays")
        song_slot = int(payload.get("song_slot", 0) or 0)
        if not isinstance(calc_song, dict) or not isinstance(ref_arrays, dict):
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="Invalid payload for PRECOMPUTE_TIMELINE (expected calc_song/ref_arrays dicts)",
            )

        precompute_timeline_gpu(calc_song, ref_arrays, song_slot=song_slot)
        return GpuResponse(
            request_id=request.request_id,
            success=True,
            result=None,
        )

    def _execute_gpu_native_ga_run(self, request: GpuRequest) -> GpuResponse:
        """
        Execute a full GPU-native GA run on the GPU-owner thread.

        This request is intended for the GPU-native in-flight pipeline where
        CPU-side population building is done elsewhere and the GPU thread
        stays busy running Taichi kernels back-to-back.
        """
        if not self._in_process_queues:
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="GPU_NATIVE_GA_RUN requires in-process queues (avoid IPC pickling)",
            )

        payload = request.payload or {}
        calc_song = payload.get("calc_song")
        ref_arrays = payload.get("ref_arrays")
        item_stats = payload.get("item_stats")
        slot_start = payload.get("slot_start")
        slot_count = payload.get("slot_count")
        base_fixed_stats_arr = payload.get("base_fixed_stats_arr")
        initial_populations = payload.get("initial_populations")
        num_runs = payload.get("num_runs")
        n_genomes = payload.get("n_genomes")
        init_heuristic_topk = payload.get("init_heuristic_topk")
        init_heuristic_k = payload.get("init_heuristic_k", 0)
        init_heuristic_copies = payload.get("init_heuristic_copies", 25)
        db_seed_ids = payload.get("db_seed_ids")
        db_seed_prob = payload.get("db_seed_prob", 0.0)
        db_seed_copies = payload.get("db_seed_copies", 1)
        db_seed_mutations = payload.get("db_seed_mutations", 1)
        song_slot = int(payload.get("song_slot", 0) or 0)
        n_generations = int(payload.get("n_generations", 1) or 1)
        elite_count = int(payload.get("elite_count", 2) or 2)
        mutation_rate = float(payload.get("mutation_rate", 0.02) or 0.02)
        immigrant_rate = float(payload.get("immigrant_rate", 0.0) or 0.0)
        tournament_k = int(payload.get("tournament_k", 3) or 3)
        color_flags = payload.get("color_flags") or {}
        cfg_data = payload.get("cfg_data") or {}
        ga_seed = payload.get("ga_seed")

        if not isinstance(calc_song, dict) or not isinstance(ref_arrays, dict):
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="Invalid payload for GPU_NATIVE_GA_RUN (expected calc_song/ref_arrays dicts)",
            )

        try:
            from gear_optimizer.solver.genetic import run_gpu_native_ga_runs_payload_prebuilt

            kwargs = dict(
                calc_song=calc_song,
                ref_arrays=ref_arrays,
                song_slot=song_slot,
                item_stats=item_stats,
                slot_start=slot_start,
                slot_count=slot_count,
                base_fixed_stats_arr=base_fixed_stats_arr,
                n_generations=n_generations,
                initial_populations=initial_populations,
                num_runs=int(num_runs) if num_runs is not None else None,
                init_heuristic_topk=init_heuristic_topk,
                init_heuristic_k=int(init_heuristic_k or 0),
                init_heuristic_copies=int(init_heuristic_copies or 0),
                db_seed_ids=db_seed_ids,
                db_seed_prob=float(db_seed_prob or 0.0),
                db_seed_copies=int(db_seed_copies or 0),
                db_seed_mutations=int(db_seed_mutations or 0),
                elite_count=elite_count,
                mutation_rate=mutation_rate,
                immigrant_rate=immigrant_rate,
                tournament_k=tournament_k,
                color_flags=dict(color_flags),
                cfg_data=dict(cfg_data),
                ga_seed=int(ga_seed) if ga_seed is not None else None,
            )
            if n_genomes is not None:
                kwargs["n_genomes"] = int(n_genomes)
            runs_payload = run_gpu_native_ga_runs_payload_prebuilt(**kwargs)
        except Exception as e:
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error=f"{type(e).__name__}: {e}",
            )

        return GpuResponse(
            request_id=request.request_id,
            success=True,
            result=runs_payload,
        )

    def _execute_ga_stage_fg_genome_base_stats(self, request: GpuRequest) -> GpuResponse:
        """
        Stage shared `genome_base_stats` from the GPU-native GA -> FG candidate table.

        This enables a GPU-resident GA→FG pipeline: GA packs the candidate table on GPU,
        callers select candidates on CPU, then send only small (run,row) coordinates to
        stage the per-genome base stats for FG without host->device uploads.
        """
        if not self._in_process_queues:
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="GA_STAGE_FG_GENOME_BASE_STATS requires in-process queues (avoid IPC pickling)",
            )

        payload = request.payload or {}
        table_slot = int(payload.get("table_slot", 0) or 0)
        n_slots = int(payload.get("n_slots", 9) or 9)
        coords = payload.get("coords")

        try:
            from .taichi_gem.api import ga_stage_genome_base_stats_from_fg_candidates_table

            n = ga_stage_genome_base_stats_from_fg_candidates_table(
                table_slot=int(table_slot),
                coords=coords,
                n_slots=int(n_slots),
            )
        except Exception as e:
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error=f"{type(e).__name__}: {e}",
            )

        return GpuResponse(
            request_id=request.request_id,
            success=True,
            result=int(n),
        )

    def _execute_fg_reset_global_best(self, request: GpuRequest) -> GpuResponse:
        """Reset FG global-best accumulation fields on the GPU."""
        if not self._in_process_queues:
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="FG_RESET_GLOBAL_BEST requires in-process queues (avoid IPC pickling)",
            )

        payload = request.payload or {}
        try:
            n_genomes = int(payload.get("n_genomes", 0) or 0)
        except Exception:
            n_genomes = 0
        try:
            song_slot = int(payload.get("song_slot", 0) or 0)
        except Exception:
            song_slot = 0

        from .taichi_gem.force_greats.api import fg_reset_global_best

        fg_reset_global_best(int(n_genomes), session_slot=int(song_slot))
        return GpuResponse(
            request_id=request.request_id,
            success=True,
            result=None,
        )

    def _execute_fg_download_global_best(self, request: GpuRequest) -> GpuResponse:
        """Download FG global-best accumulation results from the GPU."""
        if not self._in_process_queues:
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="FG_DOWNLOAD_GLOBAL_BEST requires in-process queues (avoid IPC pickling)",
            )

        payload = request.payload or {}
        try:
            n_genomes = int(payload.get("n_genomes", 0) or 0)
        except Exception:
            n_genomes = 0
        try:
            song_slot = int(payload.get("song_slot", 0) or 0)
        except Exception:
            song_slot = 0

        from .taichi_gem.force_greats.api import fg_download_global_best

        download_topk = payload.get("topk")
        download_base_scores = payload.get("base_scores")
        download_keep_mask = payload.get("keep_mask")
        if download_topk is not None and download_base_scores is not None:
            result = fg_download_global_best(
                int(n_genomes),
                session_slot=int(song_slot),
                topk=int(download_topk),
                base_scores=download_base_scores,
                keep_mask=download_keep_mask,
            )
        else:
            result = fg_download_global_best(int(n_genomes), session_slot=int(song_slot))
        return GpuResponse(
            request_id=request.request_id,
            success=True,
            result=result,
        )

    def _execute_fg_compute_breakpoints(self, request: GpuRequest) -> GpuResponse:
        """
        Compute per-FT/FF breakpoint ranges for ForceGreatsFinder on the GPU-owner thread.

        Returns an (n_pairs, n_sections) int16 array of max fill-penalty caps (FP caps).
        Callers can convert this to `section_breakpoints` by using `range(0, fp + 1)` per section.
        """
        import numpy as np

        payload = request.payload or {}

        # NOTE: `ftff_pairs`/`base_stats_pairs` may be numpy arrays; never use `or []` which
        # triggers `ValueError: The truth value of an array with more than one element...`.
        ftff_pairs = payload.get("ftff_pairs", None)
        if ftff_pairs is None:
            ftff_pairs = []
        base_stats_pairs = payload.get("base_stats_pairs", None)
        if base_stats_pairs is None:
            base_stats_pairs = []
        n_sections = int(payload.get("n_sections", 0) or 0)
        song_slot = int(payload.get("song_slot", 0) or 0)
        gem_scale_fever = int(payload.get("gem_scale_fever", 3) or 3)

        # Optional precomputed tables (recommended; avoids repeated ceil math).
        non_fever_base_by_ff = payload.get("non_fever_base_by_ff")
        fp_cap_table = payload.get("fp_cap_table")

        if n_sections <= 0:
            return GpuResponse(request_id=request.request_id, success=True, result=np.zeros((0, 0), dtype=np.int16))

        # Accept either Python sequences of (ft, ff) tuples or packed (n,2) int arrays.
        pairs_arr = None
        base_arr = None
        try:
            if isinstance(ftff_pairs, np.ndarray):
                pairs_arr = np.asarray(ftff_pairs, dtype=np.int32)
                if pairs_arr.ndim != 2 or int(pairs_arr.shape[1]) < 2:
                    pairs_arr = None
            if isinstance(base_stats_pairs, np.ndarray):
                base_arr = np.asarray(base_stats_pairs, dtype=np.int32)
                if base_arr.ndim != 2 or int(base_arr.shape[1]) < 2:
                    base_arr = None
        except Exception:
            pairs_arr = None
            base_arr = None

        if pairs_arr is not None and int(pairs_arr.shape[0]) <= 0:
            return GpuResponse(
                request_id=request.request_id,
                success=True,
                result=np.zeros((0, int(n_sections)), dtype=np.int16),
            )
        if pairs_arr is not None and (base_arr is not None and int(base_arr.shape[0]) <= 0):
            # No base FT/FF stats to consider -> max FP is 0 everywhere.
            return GpuResponse(
                request_id=request.request_id,
                success=True,
                result=np.zeros((int(pairs_arr.shape[0]), int(n_sections)), dtype=np.int16),
            )

        if pairs_arr is None:
            try:
                pairs_list = list(ftff_pairs)
            except Exception:
                pairs_list = []
            if not pairs_list:
                return GpuResponse(
                    request_id=request.request_id,
                    success=True,
                    result=np.zeros((0, int(n_sections)), dtype=np.int16),
                )
        else:
            pairs_list = None

        if base_arr is None:
            try:
                base_list = list(base_stats_pairs)
            except Exception:
                base_list = []
            if not base_list:
                # No base FT/FF stats to consider -> max FP is 0 everywhere.
                n_pairs = int(pairs_arr.shape[0]) if pairs_arr is not None else int(len(pairs_list))
                return GpuResponse(
                    request_id=request.request_id,
                    success=True,
                    result=np.zeros((n_pairs, int(n_sections)), dtype=np.int16),
                )
        else:
            base_list = None

        # Build pair arrays.
        if pairs_arr is not None:
            try:
                pair_ft = np.ascontiguousarray(pairs_arr[:, 0], dtype=np.int32)
                pair_ff = np.ascontiguousarray(pairs_arr[:, 1], dtype=np.int32)
            except Exception:
                pair_ft = np.asarray([], dtype=np.int32)
                pair_ff = np.asarray([], dtype=np.int32)
        else:
            try:
                pair_ft = np.asarray([int(p[0]) for p in pairs_list], dtype=np.int32)
                pair_ff = np.asarray([int(p[1]) for p in pairs_list], dtype=np.int32)
            except Exception:
                return GpuResponse(
                    request_id=request.request_id,
                    success=False,
                    error="FG_COMPUTE_BREAKPOINTS invalid ftff_pairs (expected list of (ft, ff))",
                )

        # Build base arrays.
        if base_arr is not None:
            try:
                base_ft = np.ascontiguousarray(base_arr[:, 0], dtype=np.int32)
                base_ff = np.ascontiguousarray(base_arr[:, 1], dtype=np.int32)
            except Exception:
                base_ft = np.asarray([], dtype=np.int32)
                base_ff = np.asarray([], dtype=np.int32)
        else:
            try:
                base_ft = np.asarray([int(p[0]) for p in base_list], dtype=np.int32)
                base_ff = np.asarray([int(p[1]) for p in base_list], dtype=np.int32)
            except Exception:
                return GpuResponse(
                    request_id=request.request_id,
                    success=False,
                    error="FG_COMPUTE_BREAKPOINTS invalid base_stats_pairs (expected list of (ft_stat, ff_stat))",
                )

        # Validate tables.
        if non_fever_base_by_ff is None or fp_cap_table is None:
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="FG_COMPUTE_BREAKPOINTS missing non_fever_base_by_ff/fp_cap_table",
            )

        non_fever_base_by_ff = np.asarray(non_fever_base_by_ff, dtype=np.int16)
        fp_cap_table = np.asarray(fp_cap_table, dtype=np.int16)
        if non_fever_base_by_ff.ndim != 1 or int(non_fever_base_by_ff.shape[0]) < 161:
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="FG_COMPUTE_BREAKPOINTS non_fever_base_by_ff must be shape (>=161,)",
            )
        if fp_cap_table.ndim != 2 or fp_cap_table.shape[0] < 161 or fp_cap_table.shape[1] < 51:
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="FG_COMPUTE_BREAKPOINTS fp_cap_table must be shape (>=161, >=51)",
            )

        try:
            out = self._compute_fg_breakpoints_max_fp_matrix(
                pair_ft=pair_ft,
                pair_ff=pair_ff,
                base_ft=base_ft,
                base_ff=base_ff,
                n_sections=int(n_sections),
                song_slot=int(song_slot),
                gem_scale_fever=int(gem_scale_fever),
                non_fever_base_by_ff=non_fever_base_by_ff,
                fp_cap_table=fp_cap_table,
            )
        except Exception as e:
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error=f"FG_COMPUTE_BREAKPOINTS kernel failed: {type(e).__name__}: {e}",
            )

        return GpuResponse(request_id=request.request_id, success=True, result=out)

    @staticmethod
    def _compute_fg_breakpoints_max_fp_matrix(
        *,
        pair_ft,
        pair_ff,
        base_ft,
        base_ff,
        n_sections: int,
        song_slot: int,
        gem_scale_fever: int,
        non_fever_base_by_ff,
        fp_cap_table,
    ):
        import numpy as np

        # Taichi ndarrays require contiguous host buffers.
        pair_ft = np.ascontiguousarray(pair_ft, dtype=np.int32)
        pair_ff = np.ascontiguousarray(pair_ff, dtype=np.int32)
        base_ft = np.ascontiguousarray(base_ft, dtype=np.int32)
        base_ff = np.ascontiguousarray(base_ff, dtype=np.int32)
        non_fever_base_by_ff = np.ascontiguousarray(non_fever_base_by_ff, dtype=np.int16)
        fp_cap_table = np.ascontiguousarray(fp_cap_table, dtype=np.int16)

        out = np.zeros((int(pair_ft.shape[0]), int(n_sections)), dtype=np.int16)
        from .taichi_gem.kernels import kernels_breakpoints

        kernels_breakpoints.fg_compute_max_fp_by_pair_kernel(
            int(pair_ft.shape[0]),
            int(base_ft.shape[0]),
            int(n_sections),
            int(song_slot),
            int(gem_scale_fever),
            pair_ft,
            pair_ff,
            base_ft,
            base_ff,
            non_fever_base_by_ff,
            fp_cap_table,
            out,
        )
        return out

    @staticmethod
    def _decode_cfg_counts_from_windows(cfg_idx, cfg_windows: list[dict], n_sections: int):
        import numpy as np

        if cfg_idx is None or not cfg_windows or int(n_sections) <= 0:
            return None
        try:
            cfg_idx_np = np.asarray(cfg_idx, dtype=np.int32)
        except Exception:
            return None
        try:
            n_out = int(cfg_idx_np.shape[0])
        except Exception:
            return None
        if n_out <= 0:
            return None

        cfg_counts = np.zeros((int(n_out), int(n_sections)), dtype=np.int32)
        bases = [int(w.get("base", 0) or 0) for w in cfg_windows]
        lens = [int(w.get("len", 0) or 0) for w in cfg_windows]
        ends = [base + length for base, length in zip(bases, lens)]

        for gi in range(int(n_out)):
            x = int(cfg_idx_np[gi])
            window_index = -1
            for wi, (b, e) in enumerate(zip(bases, ends)):
                if int(b) <= x < int(e):
                    window_index = wi
                    break
            if window_index < 0:
                continue

            w = cfg_windows[window_index]
            base = int(w.get("base", 0) or 0)
            local = int(x - base)
            if str(w.get("kind") or "") == "list":
                lst = w.get("counts_list") or []
                if 0 <= local < len(lst):
                    row = lst[local]
                    for s in range(int(n_sections)):
                        cfg_counts[gi, s] = int(row[s]) if s < len(row) else 0
                continue

            max_fp_vec = list(w.get("max_fp") or [])
            rem = int(local)
            for s in range(int(n_sections) - 1, -1, -1):
                try:
                    basev = int(max(0, int(max_fp_vec[s] if s < len(max_fp_vec) else 0))) + 1
                except Exception:
                    basev = 1
                if basev <= 0:
                    basev = 1
                val = rem % basev
                rem //= basev
                cfg_counts[gi, s] = int(val)
        return cfg_counts

    @staticmethod
    def _decode_cfg_counts_from_max_fp_matrix(
        cfg_idx,
        ft_vals,
        ff_vals,
        max_fp_matrix,
        ftff_pairs,
        n_sections: int,
    ):
        import numpy as np

        if cfg_idx is None or max_fp_matrix is None or ft_vals is None or ff_vals is None:
            return None
        try:
            n_sections_i = int(n_sections)
        except Exception:
            return None
        if n_sections_i <= 0:
            return None

        try:
            cfg_idx_np = np.asarray(cfg_idx, dtype=np.int64)
            ft_np = np.asarray(ft_vals, dtype=np.int32)
            ff_np = np.asarray(ff_vals, dtype=np.int32)
        except Exception:
            return None
        if cfg_idx_np.shape[0] != ft_np.shape[0] or cfg_idx_np.shape[0] != ff_np.shape[0]:
            return None

        try:
            pairs_arr = np.asarray(ftff_pairs, dtype=np.int32)
        except Exception:
            return None
        if pairs_arr.ndim != 2 or int(pairs_arr.shape[1]) < 2:
            return None

        try:
            max_fp_arr = np.asarray(max_fp_matrix, dtype=np.int32)
        except Exception:
            return None
        if max_fp_arr.ndim != 2 or int(max_fp_arr.shape[0]) != int(pairs_arr.shape[0]):
            return None

        # Build mapping from (ft, ff) -> row index.
        try:
            pair_index: dict[tuple[int, int], int] = {}
            for i in range(int(pairs_arr.shape[0])):
                ft_i = int(pairs_arr[i, 0])
                ff_i = int(pairs_arr[i, 1])
                pair_index[(ft_i, ff_i)] = int(i)
        except Exception:
            return None

        n_out = int(cfg_idx_np.shape[0])
        cfg_counts = np.zeros((int(n_out), int(n_sections_i)), dtype=np.int32)
        for gi in range(int(n_out)):
            row = pair_index.get((int(ft_np[gi]), int(ff_np[gi])), -1)
            if row < 0:
                continue
            idx = int(cfg_idx_np[gi])
            if idx < 0:
                continue
            try:
                max_fp_row = max_fp_arr[row]
            except Exception:
                continue
            for s in range(int(n_sections_i) - 1, -1, -1):
                try:
                    basev = int(max(0, int(max_fp_row[s] if s < len(max_fp_row) else 0))) + 1
                except Exception:
                    basev = 1
                if basev <= 0:
                    basev = 1
                val = idx % basev
                idx //= basev
                cfg_counts[gi, s] = int(val)
        return cfg_counts

    def _execute_fg_solve_with_breakpoints(self, request: GpuRequest) -> GpuResponse:
        """
        Fused FG path for in-process mode:
          - compute max-FP breakpoint caps on-GPU (no host download)
          - group FT/FF pairs by max-FP row on the executor thread
          - run FG tasks with GPU accumulation
          - download global best and return `cfg_counts` directly (avoid host-side cfg decoding)

        This removes a whole request boundary (FG_COMPUTE_BREAKPOINTS + SOLVE_FORCE_GREATS_FINDER)
        and keeps the intermediate max-FP matrix off the CPU.
        """
        if not self._in_process_queues:
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="FG_SOLVE_WITH_BREAKPOINTS requires in-process queues (avoid IPC pickling)",
            )

        import numpy as np

        try:
            result = self._run_fg_solve_with_breakpoints_payload(request.payload or {})
            return GpuResponse(request_id=request.request_id, success=True, result=result)
        except Exception as e:
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error=f"FG_SOLVE_WITH_BREAKPOINTS: {type(e).__name__}: {e}",
            )

    def _execute_fg_solve_with_breakpoints_batch(self, request: GpuRequest) -> GpuResponse:
        """
        Batch multiple `FG_SOLVE_WITH_BREAKPOINTS` payloads into a single executor request.

        This reduces request/lock overhead when the FG pipeline must split work into multiple
        genome batches (signature chunks) for the same song/group.
        """
        if not self._in_process_queues:
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="FG_SOLVE_WITH_BREAKPOINTS_BATCH requires in-process queues (avoid IPC pickling)",
            )

        payload = request.payload or {}
        payloads = payload.get("payloads")
        if not isinstance(payloads, (list, tuple)):
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="FG_SOLVE_WITH_BREAKPOINTS_BATCH requires payloads: list[dict]",
            )

        debug_batch_pack = str(os.environ.get("FG_BREAKPOINTS_BATCH_PACK_DEBUG", "0") or "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        try:
            min_pack_payloads = int(os.environ.get("FG_BREAKPOINTS_BATCH_PACK_MIN_PAYLOADS", "2") or "2")
        except Exception:
            min_pack_payloads = 2
        min_pack_payloads = max(1, min(int(min_pack_payloads), 128))
        if debug_batch_pack:
            try:
                print(f"[FG][BatchPack] request payloads={len(payloads)}")
            except Exception:
                pass

        # Fast path: batch-pack top-K results into a staging field, then download once.
        try:
            want_batch_pack = bool(payloads) and int(len(payloads)) >= int(min_pack_payloads)
            if want_batch_pack:
                for p in payloads:
                    if not isinstance(p, dict):
                        raise TypeError("FG_SOLVE_WITH_BREAKPOINTS_BATCH payload item must be dict")
                    # Only support the reduced-download top-K mode (default for the fast path).
                    if p.get("fg_download_topk") is None or p.get("fg_download_base_scores") is None:
                        want_batch_pack = False
                        break

            if want_batch_pack:
                import numpy as np

                try:
                    from .taichi_gem.force_greats import fields as fg_fields

                    max_batch = int(getattr(fg_fields, "FG_DOWNLOAD_BATCH_MAX", 0) or 0)
                except Exception:
                    max_batch = 0
                if max_batch <= 0:
                    max_batch = 1

                from .taichi_gem.force_greats.api import fg_download_packed_topk_batch

                results: list[Any] = []
                for chunk_start in range(0, int(len(payloads)), int(max_batch)):
                    chunk = list(payloads[chunk_start : chunk_start + int(max_batch)])
                    if not chunk:
                        continue

                    decode_ctx: list[dict[str, Any]] = []
                    for i, p in enumerate(chunk):
                        ctx = self._run_fg_solve_with_breakpoints_payload(p, batch_pack_idx=int(i))
                        if not isinstance(ctx, dict) or not ctx.get("_packed_batch"):
                            raise RuntimeError("FG batch-pack expected packed ctx dict")
                        decode_ctx.append(ctx)

                    chunk_results = fg_download_packed_topk_batch(int(len(chunk)))

                    # Ensure cfg_counts present (defensive; most paths include it in the packed payload).
                    for ctx, result in zip(decode_ctx, chunk_results):
                        if not isinstance(result, dict):
                            continue
                        cfg_counts = result.get("cfg_counts")
                        if cfg_counts is None:
                            # Match single-payload behavior for legacy callers.
                            n_sections = int(ctx.get("n_sections", 0) or 0)
                            implicit_cfgs = bool(ctx.get("implicit_cfgs", False))
                            cfg_windows = ctx.get("cfg_windows")
                            if implicit_cfgs:
                                try:
                                    result_ft = np.asarray(result.get("FT"), dtype=np.int32)
                                    result_ff = np.asarray(result.get("FF"), dtype=np.int32)
                                    if (
                                        result_ft.ndim == 1
                                        and result_ff.ndim == 1
                                        and int(result_ft.shape[0]) == int(result_ff.shape[0])
                                    ):
                                        max_fp_rows = self._compute_fg_breakpoints_max_fp_matrix(
                                            pair_ft=result_ft,
                                            pair_ff=result_ff,
                                            base_ft=np.asarray(ctx.get("base_ft"), dtype=np.int32),
                                            base_ff=np.asarray(ctx.get("base_ff"), dtype=np.int32),
                                            n_sections=int(n_sections),
                                            song_slot=int(ctx.get("song_slot", 0) or 0),
                                            gem_scale_fever=int(ctx.get("gem_scale_fever", 0) or 0),
                                            non_fever_base_by_ff=ctx.get("non_fever_base_by_ff"),
                                            fp_cap_table=ctx.get("fp_cap_table"),
                                        )
                                        result_pairs = np.stack([result_ft, result_ff], axis=1)
                                        cfg_counts = self._decode_cfg_counts_from_max_fp_matrix(
                                            result.get("cfg_idx"),
                                            result_ft,
                                            result_ff,
                                            max_fp_rows,
                                            result_pairs,
                                            int(n_sections),
                                        )
                                except Exception:
                                    cfg_counts = None
                            elif cfg_windows:
                                try:
                                    cfg_counts = self._decode_cfg_counts_from_windows(
                                        result.get("cfg_idx"),
                                        cfg_windows,
                                        int(n_sections),
                                    )
                                except Exception:
                                    cfg_counts = None
                            if cfg_counts is not None:
                                result = dict(result)
                                result["cfg_counts"] = cfg_counts
                        results.append(result)

                return GpuResponse(request_id=request.request_id, success=True, result=results)
            elif debug_batch_pack:
                try:
                    reason = f"payloads<{int(min_pack_payloads)}"
                    if int(len(payloads)) >= int(min_pack_payloads):
                        reason = "unknown"
                        for idx, p in enumerate(payloads):
                            if not isinstance(p, dict):
                                reason = f"payload[{idx}] not dict"
                                break
                            if p.get("fg_download_topk") is None:
                                reason = f"payload[{idx}] fg_download_topk=None"
                                break
                            if p.get("fg_download_base_scores") is None:
                                reason = f"payload[{idx}] fg_download_base_scores=None"
                                break
                    print(f"[FG][BatchPack] skipped: {reason} (payloads={len(payloads)})")
                except Exception:
                    pass
        except Exception as exc:
            if debug_batch_pack:
                try:
                    import traceback

                    print(f"[FG][BatchPack] disabled: {type(exc).__name__}: {exc}")
                    print(traceback.format_exc())
                except Exception:
                    pass
            # Fall through to legacy per-payload download path.
            pass

        results: list[Any] = []
        try:
            for p in payloads:
                if not isinstance(p, dict):
                    raise TypeError("FG_SOLVE_WITH_BREAKPOINTS_BATCH payload item must be dict")
                results.append(self._run_fg_solve_with_breakpoints_payload(p))
        except Exception as e:
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error=f"FG_SOLVE_WITH_BREAKPOINTS_BATCH: {type(e).__name__}: {e}",
            )
        return GpuResponse(request_id=request.request_id, success=True, result=results)

    def _run_fg_solve_with_breakpoints_payload(
        self, payload: dict[str, Any], *, batch_pack_idx: int | None = None
    ) -> Any:
        import numpy as np

        try:
            n_sections = int(payload.get("n_sections", 0) or 0)
        except Exception:
            n_sections = 0
        if n_sections <= 0:
            return None

        # Optional: precompute the timeline grid in this same executor request to avoid
        # an extra PRECOMPUTE_TIMELINE boundary between GA/FG.
        #
        # This is safe: `precompute_timeline_gpu` is cached per (song_slot, song_key).
        ensure_timeline = bool(payload.get("ensure_timeline_precompute", False))
        if ensure_timeline:
            try:
                calc_song = payload.get("calc_song")
                solve_kwargs0 = payload.get("solve_kwargs") or {}
                ref_arrays0 = solve_kwargs0.get("ref_arrays")
                if isinstance(calc_song, dict) and isinstance(ref_arrays0, dict):
                    from .taichi_gem.api.timeline import precompute_timeline_gpu

                    precompute_timeline_gpu(calc_song, ref_arrays0, song_slot=int(payload.get("song_slot", 0) or 0))
            except Exception:
                # Keep fused FG robust; caps can still come from an explicit grid upload.
                pass

        ftff_pairs = payload.get("ftff_pairs")
        base_stats_pairs = payload.get("base_stats_pairs")
        non_fever_base_by_ff = payload.get("non_fever_base_by_ff")
        fp_cap_table = payload.get("fp_cap_table")
        song_slot = int(payload.get("song_slot", 0) or 0)
        gem_scale_fever = int(payload.get("gem_scale_fever", 3) or 3)

        if ftff_pairs is None or base_stats_pairs is None or non_fever_base_by_ff is None or fp_cap_table is None:
            raise ValueError("FG_SOLVE_WITH_BREAKPOINTS missing required breakpoint inputs")

        try:
            pairs_arr = np.asarray(ftff_pairs, dtype=np.int32)
            base_arr = np.asarray(base_stats_pairs, dtype=np.int32)
            if pairs_arr.ndim != 2 or int(pairs_arr.shape[1]) < 2:
                raise ValueError("ftff_pairs must be shape (n,2)")
            if base_arr.ndim != 2 or int(base_arr.shape[1]) < 2:
                raise ValueError("base_stats_pairs must be shape (n,2)")
        except Exception as e:
            raise ValueError(str(e)) from e

        if int(pairs_arr.shape[0]) <= 0:
            return None

        try:
            pairs_arr = np.ascontiguousarray(pairs_arr, dtype=np.int32)
            base_arr = np.ascontiguousarray(base_arr, dtype=np.int32)
            base_ft = np.ascontiguousarray(base_arr[:, 0], dtype=np.int32)
            base_ff = np.ascontiguousarray(base_arr[:, 1], dtype=np.int32)
        except Exception as e:
            raise RuntimeError(f"breakpoint inputs invalid: {type(e).__name__}: {e}") from e

        implicit_cfgs = str(os.environ.get("FG_IMPLICIT_CONFIGS", "1") or "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
            "",
        }

        fg_tasks: list[dict[str, Any]] = []
        cfg_windows: list[dict] | None = None
        use_gpu_max_fp_compute = str(os.environ.get("FG_MAX_FP_GPU_COMPUTE", "0") or "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if implicit_cfgs:
            if use_gpu_max_fp_compute:
                # Per-pair max-FP caps (no CPU grouping). The packed-task solver can consume
                # per-pair max-FP caps computed on GPU and decode per-ftff configs on-GPU.
                fg_tasks.append(
                    {
                        "counts_list": None,
                        "counts_max_fp": {
                            "mode": "gpu",
                            "base_stats_pairs": base_arr,
                            "non_fever_base_by_ff": non_fever_base_by_ff,
                            "fp_cap_table": fp_cap_table,
                            "n_sections": int(n_sections),
                            "song_slot": int(song_slot),
                            "gem_scale_fever": int(gem_scale_fever),
                        },
                        "ftff_pairs": pairs_arr,
                        "base_cfg_offset": 0,
                    }
                )
            else:
                # Per-pair max-FP caps with full matrix download (avoid CPU grouping).
                try:
                    pair_ft = np.ascontiguousarray(pairs_arr[:, 0], dtype=np.int32)
                    pair_ff = np.ascontiguousarray(pairs_arr[:, 1], dtype=np.int32)
                    max_fp_matrix = self._compute_fg_breakpoints_max_fp_matrix(
                        pair_ft=pair_ft,
                        pair_ff=pair_ff,
                        base_ft=base_ft,
                        base_ff=base_ff,
                        n_sections=int(n_sections),
                        song_slot=int(song_slot),
                        gem_scale_fever=int(gem_scale_fever),
                        non_fever_base_by_ff=non_fever_base_by_ff,
                        fp_cap_table=fp_cap_table,
                    )
                except Exception as e:
                    raise RuntimeError(f"per-pair max-FP compute failed: {type(e).__name__}: {e}") from e
                fg_tasks.append(
                    {
                        "counts_list": None,
                        "counts_max_fp": max_fp_matrix,
                        "ftff_pairs": pairs_arr,
                        "base_cfg_offset": 0,
                    }
                )
        else:
            # Fallback: group identical max-FP rows on CPU (legacy explicit grouping path).
            try:
                pair_ft = np.ascontiguousarray(pairs_arr[:, 0], dtype=np.int32)
                pair_ff = np.ascontiguousarray(pairs_arr[:, 1], dtype=np.int32)
                max_fp_matrix = self._compute_fg_breakpoints_max_fp_matrix(
                    pair_ft=pair_ft,
                    pair_ff=pair_ff,
                    base_ft=base_ft,
                    base_ff=base_ff,
                    n_sections=int(n_sections),
                    song_slot=int(song_slot),
                    gem_scale_fever=int(gem_scale_fever),
                    non_fever_base_by_ff=non_fever_base_by_ff,
                    fp_cap_table=fp_cap_table,
                )
                rows = np.ascontiguousarray(max_fp_matrix[:, : int(n_sections)], dtype=np.int16)
                uniq, inv = np.unique(rows, axis=0, return_inverse=True)
            except Exception as e:
                raise RuntimeError(f"grouping failed: {type(e).__name__}: {e}") from e

            cfg_windows = []
            cfg_next_base = 0

            try:
                from .taichi_gem.force_greats import fg_fields

                chunk_size = int(getattr(fg_fields, "FG_MAX_FTFF", 0) or 0)
            except Exception:
                chunk_size = 0
            if chunk_size <= 0:
                chunk_size = 1024

            for i_group in range(int(uniq.shape[0])):
                mask = inv == int(i_group)
                if not np.any(mask):
                    continue
                group_pairs = pairs_arr[mask]
                try:
                    max_fp_norm = [max(0, int(v)) for v in uniq[int(i_group)].tolist()[: int(n_sections)]]
                except Exception:
                    max_fp_norm = [0] * int(n_sections)
                if not max_fp_norm:
                    max_fp_norm = [0] * int(n_sections)

                cfg_len = 1
                for v in max_fp_norm[: int(n_sections)]:
                    cfg_len *= int(v) + 1
                cfg_len = max(1, int(cfg_len))

                group_cfg_offset = int(cfg_next_base)
                cfg_windows.append(
                    {
                        "base": int(group_cfg_offset),
                        "len": int(cfg_len),
                        "kind": "max_fp",
                        "max_fp": list(max_fp_norm),
                        "n_sections": int(n_sections),
                    }
                )
                cfg_next_base = int(group_cfg_offset) + int(cfg_len)

                for j in range(0, int(group_pairs.shape[0]), int(chunk_size)):
                    chunk = group_pairs[j : j + int(chunk_size)]
                    if int(chunk.shape[0]) <= 0:
                        continue
                    fg_tasks.append(
                        {
                            "counts_list": None,
                            "counts_max_fp": list(max_fp_norm),
                            "ftff_pairs": np.asarray(chunk, dtype=np.int32),
                            "base_cfg_offset": int(group_cfg_offset),
                        }
                    )

        if not fg_tasks:
            return None

        # Solve + accumulate + download best.
        try:
            from .taichi_gem.force_greats.api import fg_download_global_best, fg_reset_global_best
            from .taichi_gem.force_greats.api import solve_force_greats_finder_gpu_tasks
        except Exception as e:
            raise RuntimeError(f"missing FG APIs: {type(e).__name__}: {e}") from e

        genome_stats_list = payload.get("genome_stats_list")
        timestamps_np = payload.get("timestamps_np")
        great_candidate_timestamps_np = payload.get("great_candidate_timestamps_np")
        long_notes = int(payload.get("long_notes", 0) or 0)
        last_note_time = float(payload.get("last_note_time", 0.0) or 0.0)

        kwargs_local = dict(payload.get("solve_kwargs") or {})
        kwargs_local["accumulate_global"] = True
        kwargs_local["return_raw"] = True

        try:
            if genome_stats_list is None:
                n_genomes = int(kwargs_local.get("n_genomes_override", 0) or 0)
            else:
                n_genomes = int(len(genome_stats_list))
        except Exception:
            n_genomes = 0
        if n_genomes <= 0:
            raise ValueError("FG_SOLVE_WITH_BREAKPOINTS n_genomes <= 0")

        # Optional GA->FG staging (run on the owner thread to avoid a separate request boundary).
        ga_stage_coords = payload.get("ga_stage_coords")
        if ga_stage_coords is not None and bool(kwargs_local.get("genome_stats_preuploaded")):
            try:
                from .taichi_gem import api as _taichi_api

                table_slot = int(payload.get("ga_stage_table_slot", song_slot) or song_slot)
                _taichi_api.ga_stage_genome_base_stats_from_fg_candidates_table(
                    int(table_slot),
                    np.asarray(ga_stage_coords, dtype=np.int32),
                    n_slots=9,
                )
            except Exception:
                # Fallback to host upload path.
                kwargs_local["genome_stats_preuploaded"] = False
                kwargs_local["upload_genome_stats"] = True

        if bool(payload.get("fg_reset_before", True)):
            fg_reset_global_best(int(n_genomes), session_slot=int(song_slot))

        solve_force_greats_finder_gpu_tasks(
            genome_stats_list,
            np.asarray(timestamps_np, dtype=np.float32),
            None
            if great_candidate_timestamps_np is None
            else np.asarray(great_candidate_timestamps_np, dtype=np.float32),
            int(long_notes),
            float(last_note_time),
            fg_tasks=fg_tasks,
            **kwargs_local,
        )

        download_topk = payload.get("fg_download_topk", None)
        download_base_scores = payload.get("fg_download_base_scores", None)
        download_keep_mask = payload.get("fg_download_keep_mask", None)
        if batch_pack_idx is not None and download_topk is not None and download_base_scores is not None:
            from .taichi_gem.force_greats.api import fg_pack_global_best_topk_to_batch

            fg_pack_global_best_topk_to_batch(
                int(n_genomes),
                session_slot=int(song_slot),
                topk=int(download_topk),
                base_scores=download_base_scores,
                keep_mask=download_keep_mask,
                batch_idx=int(batch_pack_idx),
            )
            return {
                "_packed_batch": True,
                "implicit_cfgs": bool(implicit_cfgs),
                "cfg_windows": cfg_windows,
                "n_sections": int(n_sections),
                "song_slot": int(song_slot),
                "gem_scale_fever": int(gem_scale_fever),
                "base_ft": base_ft,
                "base_ff": base_ff,
                "non_fever_base_by_ff": non_fever_base_by_ff,
                "fp_cap_table": fp_cap_table,
            }

        if download_topk is not None and download_base_scores is not None:
            result = fg_download_global_best(
                int(n_genomes),
                session_slot=int(song_slot),
                topk=int(download_topk),
                base_scores=download_base_scores,
                keep_mask=download_keep_mask,
            )
        else:
            result = fg_download_global_best(int(n_genomes), session_slot=int(song_slot))

        if isinstance(result, dict):
            cfg_counts = result.get("cfg_counts")
            if cfg_counts is None:
                if implicit_cfgs:
                    try:
                        result_ft = np.asarray(result.get("FT"), dtype=np.int32)
                        result_ff = np.asarray(result.get("FF"), dtype=np.int32)
                        if (
                            result_ft.ndim == 1
                            and result_ff.ndim == 1
                            and int(result_ft.shape[0]) == int(result_ff.shape[0])
                        ):
                            # Compute max-FP only for the returned FT/FF rows (avoid full matrix download).
                            max_fp_rows = self._compute_fg_breakpoints_max_fp_matrix(
                                pair_ft=result_ft,
                                pair_ff=result_ff,
                                base_ft=base_ft,
                                base_ff=base_ff,
                                n_sections=int(n_sections),
                                song_slot=int(song_slot),
                                gem_scale_fever=int(gem_scale_fever),
                                non_fever_base_by_ff=non_fever_base_by_ff,
                                fp_cap_table=fp_cap_table,
                            )
                            result_pairs = np.stack([result_ft, result_ff], axis=1)
                            cfg_counts = self._decode_cfg_counts_from_max_fp_matrix(
                                result.get("cfg_idx"),
                                result_ft,
                                result_ff,
                                max_fp_rows,
                                result_pairs,
                                int(n_sections),
                            )
                    except Exception:
                        cfg_counts = None
                elif cfg_windows:
                    cfg_counts = self._decode_cfg_counts_from_windows(
                        result.get("cfg_idx"), cfg_windows, int(n_sections)
                    )
            if cfg_counts is not None and result.get("cfg_counts") is None:
                result = dict(result)
                result["cfg_counts"] = cfg_counts
        return result

    def _execute_optimize_gems_batch(self, request: GpuRequest) -> GpuResponse:
        """Execute optimize_gems_batch_gpu on GPU."""
        from .taichi_gem.api import optimize_gems_batch_gpu

        payload = request.payload
        results = optimize_gems_batch_gpu(
            payload["batch_input"],
            payload["cur_pp"],
            payload["cur_cm"],
            payload["cur_fm"],
            payload["base_p_val"],
            payload["base_s_val"],
            payload["is_p_ft"],
            payload["is_s_ft"],
            payload["is_p_ff"],
            payload["is_s_ff"],
            payload["is_p_pp"],
            payload["is_s_pp"],
            payload["is_p_cm"],
            payload["is_s_cm"],
            payload["is_p_fm"],
            payload["is_s_fm"],
            payload["is_p_ov"],
            payload["is_s_ov"],
            payload["ref_arrays"],
        )

        return GpuResponse(
            request_id=request.request_id,
            success=True,
            result=results,
        )

    def _execute_load_refs(self, request: GpuRequest) -> GpuResponse:
        """Load reference arrays."""
        from .taichi_gem.api import load_ref_arrays

        ref_arrays = request.payload["ref_arrays"]
        sig = self._ref_arrays_sig(ref_arrays)
        if sig is None or sig != self._last_ref_arrays_sig:
            load_ref_arrays(ref_arrays)
            self._last_ref_arrays_sig = sig

        return GpuResponse(
            request_id=request.request_id,
            success=True,
            result=None,
        )

    @staticmethod
    def _ref_arrays_sig(ref_arrays) -> bytes | None:
        """
        Stable content signature for `ref_arrays` dict to avoid redundant uploads.
        """
        try:
            from .taichi_gem.api.initialization import _ref_arrays_sig as _taichi_ref_arrays_sig
        except Exception:
            return None
        try:
            return _taichi_ref_arrays_sig(ref_arrays)
        except Exception:
            return None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def last_init_error(self) -> Optional[str]:
        return self._last_init_error

    def wait_until_ready(self, timeout: float | None = None) -> bool:
        if not self._running:
            return False
        self._ready_event.wait(timeout=timeout)
        return bool(self._taichi_ready)

    @property
    def stats(self) -> dict:
        out = {
            "requests_processed": self._requests_processed,
            "registered_workers": len(self._response_queues),
        }
        if self._profile_enabled:
            total = self._wait_sec + self._exec_sec
            out["profile"] = {
                "wait_sec": self._wait_sec,
                "exec_sec": self._exec_sec,
                "utilization_pct": (self._exec_sec / total * 100.0) if total > 0 else 0.0,
                "batches_observed": self._batches_observed,
                "avg_batch_size": (self._batch_size_sum / self._batches_observed) if self._batches_observed else 0.0,
            }
        return out


# Global executor instance
_executor: Optional[GpuExecutor] = None


def get_gpu_executor() -> GpuExecutor:
    """Get the global GPU executor instance."""
    global _executor
    if _executor is None:
        _executor = GpuExecutor()
    return _executor


def _auto_stop_gpu_executor_at_exit() -> None:
    if str(os.environ.get("GPU_EXECUTOR_AUTO_STOP", "") or "").strip().lower() not in {"1", "true", "yes", "on"}:
        return
    global _executor
    ex = _executor
    if ex is None:
        return
    try:
        if ex.is_running:
            ex.stop()
    except Exception:
        pass


atexit.register(_auto_stop_gpu_executor_at_exit)


def send_gpu_executor_shutdown(request_queue) -> None:
    """
    Best-effort helper to stop a GPU executor loop using its request queue.

    Intended for out-of-process GPU executor servers, where the owner process needs a simple
    "poke" to request shutdown without holding a `GpuExecutor` instance.
    """
    try:
        req = GpuRequest(
            request_type=GpuRequestType.SHUTDOWN,
            request_id=-1,
            worker_id=-1,
            payload={},
        )
        request_queue.put(req)
    except Exception:
        pass


def run_gpu_executor_server(
    request_queue,
    response_queues: dict[int, multiprocessing.Queue],
    *,
    ready_event=None,
    ready_queue=None,
    vulkan_visible_device: Optional[str] = None,
    label: str = "Server",
) -> None:
    """
    Run a dedicated GPU-owner loop in a separate process.

    This is used to own a second Vulkan device (e.g., iGPU) in parallel with the primary executor.
    Taichi's Vulkan backend is single-device per process, so multi-GPU requires multi-process.

    Args:
        request_queue: Shared request queue (multiprocessing.Queue).
        response_queues: worker_id -> response queue mapping (multiprocessing.Queue).
        ready_event: Optional multiprocessing.Event set after Taichi init completes (success or fail).
        vulkan_visible_device: If provided, sets `TAICHI_VULKAN_VISIBLE_DEVICE` for this process before init.
        label: Log label for this server instance.
    """
    if vulkan_visible_device is not None and str(vulkan_visible_device).strip() != "":
        os.environ["TAICHI_VULKAN_VISIBLE_DEVICE"] = str(vulkan_visible_device).strip()

    ex = get_gpu_executor()

    # Wire external queues before entering the loop.
    ex._request_queue = request_queue
    ex._response_queues = dict(response_queues or {})
    ex._in_process_queues = isinstance(request_queue, queue.Queue)
    ex._running = True
    ex._taichi_ready = False
    ex._last_init_error = None
    try:
        ex._ready_event.clear()
    except Exception:
        pass

    if ready_event is not None:
        # Bridge the executor's thread Event into a multiprocessing.Event for the parent.
        def _signal_ready() -> None:
            try:
                ex._ready_event.wait()
            finally:
                try:
                    ready_event.set()
                except Exception:
                    pass
                if ready_queue is not None:
                    try:
                        ready_queue.put(
                            {
                                "ok": bool(getattr(ex, "_taichi_ready", False)),
                                "error": getattr(ex, "_last_init_error", None),
                            }
                        )
                    except Exception:
                        pass

        threading.Thread(target=_signal_ready, name=f"GpuExecutorReady[{label}]", daemon=True).start()

    try:
        print(
            f"[GpuExecutor][{label}] Starting server loop "
            f"(TAICHI_VULKAN_VISIBLE_DEVICE={os.environ.get('TAICHI_VULKAN_VISIBLE_DEVICE', '') or 'default'})"
        )
    except Exception:
        pass

    ex._executor_loop()


def submit_gpu_solve_genomes(
    genome_stats_list: list,
    timeline_grid,
    is_p_ft: int,
    is_s_ft: int,
    is_p_ff: int,
    is_s_ff: int,
    is_p_pp: int,
    is_s_pp: int,
    is_p_cm: int,
    is_s_cm: int,
    is_p_fm: int,
    is_s_fm: int,
    is_p_ov: int,
    is_s_ov: int,
    ref_arrays: dict,
    total_budget: int = 90,
    gem_scale_fever: int = 3,
    song_slot: int = 0,
    timeout: float = 60.0,
) -> list:
    """
    Submit solve_genomes_parallel request via IPC (for worker processes).

    This is a blocking call that waits for the GPU executor to return results.

    Args:
        Same as solve_genomes_parallel. `timeline_grid` may be either:
        - a `SongTimelineGrid` instance (sequential mode), or
        - a lightweight `calc_song` dict with `metadata`/`song_data` (parallel/IPC mode),
          which will be used to precompute the full 161×161 grid on GPU.
        timeout: Max seconds to wait for response

    Returns:
        List of (score, ft, ff, pp, cm, fm, ov) tuples per genome

    Raises:
        RuntimeError: If not in worker mode or timeout
    """
    global _REQUEST_COUNTER

    if not _WORKER_MODE:
        raise RuntimeError("submit_gpu_solve_genomes called but not in worker mode")

    _REQUEST_COUNTER += 1
    request_id = _REQUEST_COUNTER

    request = GpuRequest(
        request_type=GpuRequestType.SOLVE_GENOMES_PARALLEL,
        request_id=request_id,
        worker_id=_WORKER_ID,
        payload={
            "genome_stats_list": genome_stats_list,
            "timeline_grid": timeline_grid,
            "is_p_ft": is_p_ft,
            "is_s_ft": is_s_ft,
            "is_p_ff": is_p_ff,
            "is_s_ff": is_s_ff,
            "is_p_pp": is_p_pp,
            "is_s_pp": is_s_pp,
            "is_p_cm": is_p_cm,
            "is_s_cm": is_s_cm,
            "is_p_fm": is_p_fm,
            "is_s_fm": is_s_fm,
            "is_p_ov": is_p_ov,
            "is_s_ov": is_s_ov,
            "ref_arrays": ref_arrays,
            "total_budget": total_budget,
            "gem_scale_fever": gem_scale_fever,
            "song_slot": int(song_slot),
        },
    )

    # Submit request
    _REQUEST_QUEUE.put(request)

    # Wait for response
    start = time.monotonic()
    while True:
        _prune_pending_responses()
        if request_id in _PENDING_RESPONSES:
            response, _ts = _PENDING_RESPONSES.pop(request_id)
            break

        remaining = timeout - (time.monotonic() - start)
        if remaining <= 0:
            raise RuntimeError(f"GPU executor timeout after {timeout}s")

        try:
            response: GpuResponse = _RESPONSE_QUEUE.get(timeout=remaining)
        except queue.Empty:
            raise RuntimeError(f"GPU executor timeout after {timeout}s")

        if response.request_id != request_id:
            # Can happen if an earlier request timed out and its response arrived late.
            _store_pending_response(response)
            continue
        break

    if not response.success:
        raise RuntimeError(f"GPU executor error: {response.error}")

    result = response.result
    if isinstance(result, list) and len(result) != len(genome_stats_list):
        raise RuntimeError(f"GPU executor returned {len(result)} results for {len(genome_stats_list)} genomes")
    return result


def submit_gpu_solve_genomes_from_registry(
    population_indices,
    item_stats,
    slot_start,
    slot_count,
    base_fixed_stats,
    timeline_grid,
    is_p_ft: int,
    is_s_ft: int,
    is_p_ff: int,
    is_s_ff: int,
    is_p_pp: int,
    is_s_pp: int,
    is_p_cm: int,
    is_s_cm: int,
    is_p_fm: int,
    is_s_fm: int,
    is_p_ov: int,
    is_s_ov: int,
    ref_arrays: dict,
    total_budget: int = 90,
    gem_scale_fever: int = 3,
    song_slot: int = 0,
    timeout: float = 60.0,
) -> list:
    """
    Submit solve_genomes_from_registry request via IPC (for worker processes).

    This uses the GPU-resident stat aggregation path and avoids uploading large
    work-item buffers for FT/FF permutations.
    """
    global _REQUEST_COUNTER

    if not _WORKER_MODE:
        raise RuntimeError("submit_gpu_solve_genomes_from_registry called but not in worker mode")

    _REQUEST_COUNTER += 1
    request_id = _REQUEST_COUNTER

    request = GpuRequest(
        request_type=GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
        request_id=request_id,
        worker_id=_WORKER_ID,
        payload={
            "population_indices": population_indices,
            "item_stats": item_stats,
            "slot_start": slot_start,
            "slot_count": slot_count,
            "base_fixed_stats": base_fixed_stats,
            "timeline_grid": timeline_grid,
            "is_p_ft": int(is_p_ft),
            "is_s_ft": int(is_s_ft),
            "is_p_ff": int(is_p_ff),
            "is_s_ff": int(is_s_ff),
            "is_p_pp": int(is_p_pp),
            "is_s_pp": int(is_s_pp),
            "is_p_cm": int(is_p_cm),
            "is_s_cm": int(is_s_cm),
            "is_p_fm": int(is_p_fm),
            "is_s_fm": int(is_s_fm),
            "is_p_ov": int(is_p_ov),
            "is_s_ov": int(is_s_ov),
            "ref_arrays": ref_arrays,
            "total_budget": int(total_budget),
            "gem_scale_fever": int(gem_scale_fever),
            "song_slot": int(song_slot),
        },
    )

    _REQUEST_QUEUE.put(request)

    start = time.monotonic()
    while True:
        _prune_pending_responses()
        if request_id in _PENDING_RESPONSES:
            response, _ts = _PENDING_RESPONSES.pop(request_id)
            break

        remaining = timeout - (time.monotonic() - start)
        if remaining <= 0:
            raise RuntimeError(f"GPU executor timeout after {timeout}s")

        try:
            response: GpuResponse = _RESPONSE_QUEUE.get(timeout=remaining)
        except queue.Empty:
            raise RuntimeError(f"GPU executor timeout after {timeout}s")

        if response.request_id != request_id:
            _store_pending_response(response)
            continue
        break

    if not response.success:
        raise RuntimeError(f"GPU executor error: {response.error}")

    result = response.result
    try:
        n_expected = int(getattr(population_indices, "shape", [len(population_indices)])[0])
    except Exception:
        n_expected = 0
    if isinstance(result, list) and n_expected and len(result) != n_expected:
        raise RuntimeError(f"GPU executor returned {len(result)} results for {n_expected} genomes")
    return result


def submit_gpu_optimize_gems_batch(
    batch_input: list,
    cur_pp: int,
    cur_cm: int,
    cur_fm: int,
    base_p_val: int,
    base_s_val: int,
    is_p_ft: int,
    is_s_ft: int,
    is_p_ff: int,
    is_s_ff: int,
    is_p_pp: int,
    is_s_pp: int,
    is_p_cm: int,
    is_s_cm: int,
    is_p_fm: int,
    is_s_fm: int,
    is_p_ov: int,
    is_s_ov: int,
    ref_arrays: dict,
    timeout: float = 60.0,
) -> list:
    """
    Submit optimize_gems_batch_gpu request via IPC (for worker processes).

    Mirrors `gear_optimizer.solver.taichi_gem.api.optimize_gems_batch_gpu`.
    """
    global _REQUEST_COUNTER

    if not _WORKER_MODE:
        raise RuntimeError("submit_gpu_optimize_gems_batch called but not in worker mode")

    _REQUEST_COUNTER += 1
    request_id = _REQUEST_COUNTER

    request = GpuRequest(
        request_type=GpuRequestType.OPTIMIZE_GEMS_BATCH,
        request_id=request_id,
        worker_id=_WORKER_ID,
        payload={
            "batch_input": batch_input,
            "cur_pp": int(cur_pp),
            "cur_cm": int(cur_cm),
            "cur_fm": int(cur_fm),
            "base_p_val": int(base_p_val),
            "base_s_val": int(base_s_val),
            "is_p_ft": int(is_p_ft),
            "is_s_ft": int(is_s_ft),
            "is_p_ff": int(is_p_ff),
            "is_s_ff": int(is_s_ff),
            "is_p_pp": int(is_p_pp),
            "is_s_pp": int(is_s_pp),
            "is_p_cm": int(is_p_cm),
            "is_s_cm": int(is_s_cm),
            "is_p_fm": int(is_p_fm),
            "is_s_fm": int(is_s_fm),
            "is_p_ov": int(is_p_ov),
            "is_s_ov": int(is_s_ov),
            "ref_arrays": ref_arrays,
        },
    )

    _REQUEST_QUEUE.put(request)

    start = time.monotonic()
    while True:
        _prune_pending_responses()
        if request_id in _PENDING_RESPONSES:
            response, _ts = _PENDING_RESPONSES.pop(request_id)
            break

        remaining = timeout - (time.monotonic() - start)
        if remaining <= 0:
            raise RuntimeError(f"GPU executor timeout after {timeout}s")

        try:
            response: GpuResponse = _RESPONSE_QUEUE.get(timeout=remaining)
        except queue.Empty:
            raise RuntimeError(f"GPU executor timeout after {timeout}s")

        if response.request_id != request_id:
            _store_pending_response(response)
            continue
        break

    if not response.success:
        raise RuntimeError(f"GPU executor error: {response.error}")

    result = response.result
    if isinstance(result, list) and len(result) != len(batch_input):
        raise RuntimeError(f"GPU executor returned {len(result)} results for {len(batch_input)} items")
    return result


def submit_gpu_load_ref_arrays(ref_arrays: dict, timeout: float = 30.0) -> None:
    """Submit load_ref_arrays request via IPC (for worker processes)."""
    global _REQUEST_COUNTER

    if not _WORKER_MODE:
        raise RuntimeError("submit_gpu_load_ref_arrays called but not in worker mode")

    _REQUEST_COUNTER += 1
    request_id = _REQUEST_COUNTER

    request = GpuRequest(
        request_type=GpuRequestType.LOAD_REF_ARRAYS,
        request_id=request_id,
        worker_id=_WORKER_ID,
        payload={"ref_arrays": ref_arrays},
    )

    _REQUEST_QUEUE.put(request)

    start = time.monotonic()
    while True:
        _prune_pending_responses()
        if request_id in _PENDING_RESPONSES:
            response, _ts = _PENDING_RESPONSES.pop(request_id)
            break

        remaining = timeout - (time.monotonic() - start)
        if remaining <= 0:
            raise RuntimeError(f"GPU executor timeout after {timeout}s")

        try:
            response: GpuResponse = _RESPONSE_QUEUE.get(timeout=remaining)
        except queue.Empty:
            raise RuntimeError(f"GPU executor timeout after {timeout}s")

        if response.request_id != request_id:
            _store_pending_response(response)
            continue
        break

    if not response.success:
        raise RuntimeError(f"GPU executor error: {response.error}")


def submit_gpu_solve_force_greats_finder(
    *args,
    timeout: float = 180.0,
    **kwargs,
):
    """
    Submit solve_force_greats_finder_gpu request via IPC (for worker processes).

    NOTE: This is only intended for in-process GPU worker mode by default, since
    timestamps/config grids can be large and expensive to pickle over IPC.
    """
    global _REQUEST_COUNTER

    if not _WORKER_MODE:
        raise RuntimeError("submit_gpu_solve_force_greats_finder called but not in worker mode")

    _REQUEST_COUNTER += 1
    request_id = _REQUEST_COUNTER

    request = GpuRequest(
        request_type=GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
        request_id=request_id,
        worker_id=_WORKER_ID,
        payload={
            "args": args,
            "kwargs": kwargs,
        },
    )

    _REQUEST_QUEUE.put(request)

    start = time.monotonic()
    while True:
        _prune_pending_responses()
        if request_id in _PENDING_RESPONSES:
            response, _ts = _PENDING_RESPONSES.pop(request_id)
            break

        remaining = timeout - (time.monotonic() - start)
        if remaining <= 0:
            raise RuntimeError(f"GPU executor timeout after {timeout}s")

        try:
            response: GpuResponse = _RESPONSE_QUEUE.get(timeout=remaining)
        except queue.Empty:
            raise RuntimeError(f"GPU executor timeout after {timeout}s")

        if response.request_id != request_id:
            _store_pending_response(response)
            continue
        break

    if not response.success:
        raise RuntimeError(f"GPU executor error: {response.error}")

    return response.result
