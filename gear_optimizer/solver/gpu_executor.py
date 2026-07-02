"""
GPU Executor - Cross-process GPU ownership for parallel song processing.
Architecture:
    Song Workers (CPU) --IPC Queue--> GpuExecutor (GPU owner) --> RX 7900 XTX
This ensures only ONE process initializes Taichi/Vulkan, preventing:
- Multiple GPU contexts fighting for resources
- Wasted GPU memory from duplicate Taichi inits
- Potential Vulkan driver conflicts
Usage:
    executor = get_gpu_executor()
    executor.start()
    if is_gpu_worker_mode():
        result = submit_gpu_work(...)
    executor.stop()
"""
import multiprocessing
import threading
import queue
import logging
import os
import atexit
import traceback
import time
from collections import deque
from contextlib import nullcontext
from time import perf_counter
from typing import Optional, Dict
from gear_optimizer.core.env_config import ENV
from gear_optimizer.core.parsing import env_flag
from gear_optimizer.solver.gpu_executor_batching import (
    COALESCABLE_REQUEST_TYPES,
    is_ga_recovery_request as _is_ga_recovery_request,
    ResponseDeliveryTracker,
    execute_request_from_dispatch as _execute_request_from_dispatch,
    plan_execution_units as _plan_execution_units,
)
from gear_optimizer.solver.gpu_executor_types import (
    GpuRequest,
    GpuRequestType,
    GpuResponse,
)
from gear_optimizer.solver.gpu_executor_batching import (
    extend_inprocess_after_first_deadline as _extend_inprocess_after_first_deadline,
    ga_recovery_lookahead_limit as _ga_recovery_lookahead_limit,
    ga_recovery_streak_cap as _ga_recovery_streak_cap,
    load_inprocess_coalesce_settings as _load_inprocess_coalesce_settings,
    load_loop_batch_settings as _load_loop_batch_settings,
    plan_loop_batch as _plan_loop_batch,
    select_inprocess_batch_timeout as _select_inprocess_batch_timeout,
)
from gear_optimizer.solver.gpu_executor_lifecycle import (
    ExecutorAbortState,
    ExecutorHeartbeatWriter,
    LiveReporter,
    pop_staged_request as _pop_staged_request,
    prefetch_ga_recovery_requests as _prefetch_ga_recovery_requests,
    stage_request as _stage_request,
    staged_ga_recovery_index as _staged_ga_recovery_index,
    stamp_request_dequeue as _stamp_request_dequeue,
    build_taichi_init_failure_report as _build_taichi_init_failure_report,
    build_warmup_sentinel_payload as _build_warmup_sentinel_payload,
    default_executor_heartbeat_path as _default_executor_heartbeat_path,
    executor_auto_stop_enabled as _executor_auto_stop_enabled,
    load_executor_start_settings as _load_executor_start_settings,
    load_executor_stop_profiler_settings as _load_executor_stop_profiler_settings,
    print_taichi_kernel_profiler as _print_taichi_kernel_profiler,
    send_shutdown_request as _send_shutdown_request,
    stop_executor_if_running as _stop_executor_if_running,
    warmup_sentinel_path as _warmup_sentinel_path,
    warmup_sentinel_is_fresh as _warmup_sentinel_is_fresh,
    write_warmup_sentinel_payload as _write_warmup_sentinel_payload,
)
from gear_optimizer.solver.windows_timer import (
    acquire_windows_timer_period_1ms as _acquire_windows_timer_period_1ms,
    release_windows_timer_period_1ms as _release_windows_timer_period_1ms,
    system_timer_override_allowed as _system_timer_override_allowed,
)
from gear_optimizer.solver.gpu_executor_lifecycle import (
    worker_response_router as _worker_response_router,
)
from gear_optimizer.solver.gpu_executor_lifecycle import (
    register_executor_worker as _register_executor_worker,
    unregister_executor_worker as _unregister_executor_worker,
    worker_mode_state as _worker_state,
)
from gear_optimizer.solver.gpu_executor_refs import (
    execute_load_refs as _execute_load_refs,
    ref_arrays_sig as _ref_arrays_sig,
)
from gear_optimizer.solver.gpu_executor_batching import (
    execute_gpu_native_ga_run_batch as _execute_gpu_native_ga_run_batch,
    execute_gpu_native_ga_run_chunk as _execute_gpu_native_ga_run_chunk,
)
from gear_optimizer.solver.gpu_executor_batching import (
    execute_gpu_native_ga_run as _execute_gpu_native_ga_run_request,
)
from gear_optimizer.solver.gpu_executor_lifecycle import (
    get_with_short_wait_spin as _get_with_short_wait_spin,
    load_short_wait_spin_settings as _load_short_wait_spin_settings,
    poll_inprocess_followup_nowait as _poll_inprocess_followup_nowait,
    safe_qsize as _safe_qsize,
)
from gear_optimizer.core.parsing import env_get
logger = logging.getLogger(__name__)


def _request_work_units(request: GpuRequest) -> float:
    payload = request.payload if isinstance(request.payload, dict) else {}
    if request.request_type == GpuRequestType.GPU_NATIVE_GA_RUN:
        try:
            num_runs = int(payload.get("num_runs", 0) or 0)
            n_genomes = int(payload.get("n_genomes", 0) or 0)
            n_generations = int(payload.get("n_generations", 0) or 0)
        except (TypeError, ValueError):
            return 1.0
        if num_runs > 0 and n_genomes > 0:
            return float(max(1, num_runs) * max(1, n_genomes) * max(1, n_generations))
    for key in ("tasks", "payloads", "genomes", "population"):
        value = payload.get(key)
        if value is not None:
            try:
                return float(len(value))
            except TypeError:
                return 1.0
    return 1.0


def _warmup_fg_response_frontier_runtime() -> None:
    from .taichi_gem.force_greats import fields as fg_fields

    fg_fields.ensure_ready_with_warmup()


def is_gpu_worker_mode() -> bool:
    """Check if running in worker mode (should use IPC for GPU)."""
    return bool(_worker_state.enabled)
def clear_gpu_worker_mode():
    """Clear worker mode (for testing or process reuse)."""
    _worker_response_router.reset()
    _worker_state.clear()
def set_gpu_worker_mode(worker_id: int, request_queue, response_queue):
    """Configure this process as a GPU worker (called after fork/spawn)."""
    _worker_response_router.restart()
    _worker_state.configure(worker_id, request_queue, response_queue)
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
        self._abort_state = ExecutorAbortState()
        self._in_process_queues = False
        self._staged_requests: deque[GpuRequest] = deque()
        self._ga_owner_turn_streak = 0
        self._last_ref_arrays_sig: bytes | None = None
        self._requests_processed = 0
        self._response_delivery = ResponseDeliveryTracker()
        self._last_work_end_ts: Optional[float] = None
        self._live = LiveReporter()
        self._high_res_timer_enabled = False
        short_wait_settings = _load_short_wait_spin_settings(env_get_fn=env_get)
        self._short_wait_spin_sec = short_wait_settings.short_wait_spin_sec
        self._short_wait_spin_yield_rounds = short_wait_settings.short_wait_spin_yield_rounds
        self._dispatch = {
            GpuRequestType.LOAD_REF_ARRAYS: self._execute_load_refs,
            GpuRequestType.GPU_NATIVE_GA_RUN: self._execute_gpu_native_ga_run,
        }
    def _execute_request(self, request: GpuRequest) -> GpuResponse:
        """Dispatch a single request to the appropriate executor handler."""
        return _execute_request_from_dispatch(request, dispatch=self._dispatch)
    def _maybe_dump_kernel_profiler_on_owner_thread(self) -> None:
        """Gated DEBUG instrumentation: write the kernel-profiler snapshot from the owner thread.

        OFF unless TAICHI_KERNEL_PROFILER_PATH is set (and TAICHI_KERNEL_PROFILER=1 enabled
        profiling at init). Must run on this (owner) thread because the Taichi/Vulkan runtime
        is thread-owned; cross-thread profiler reads during shutdown segfault.
        """
        try:
            settings = _load_executor_stop_profiler_settings(env_flag_fn=env_flag, env_config=ENV)
        except Exception as e:
            logger.debug(f"gpu_executor:_maybe_dump_kernel_profiler_on_owner_thread: {e}")
            return
        dump_path = str(getattr(settings, "kernel_profiler_dump_path", "") or "").strip()
        if not dump_path:
            return
        _print_taichi_kernel_profiler(enabled=False, dump_path=dump_path)
    def _finalize_taichi_on_owner_thread(self) -> None:
        """Finalize Taichi from the owner thread at shutdown (persists the offline cache).

        Must run on this (owner) thread for the same reason as the profiler dump:
        the Taichi/Vulkan runtime is thread-owned. hard_reset_taichi also clears
        taichi_gem module state, so a later in-process start() re-initializes cleanly.
        """
        if not self._taichi_ready:
            return
        try:
            from .taichi_gem.api.initialization import hard_reset_taichi
            hard_reset_taichi(reason="executor shutdown (persist offline kernel cache)")
        except Exception as e:
            logger.warning("[GpuExecutor] Taichi shutdown finalize failed (offline cache may be stale): %s", e)
    def start(self, *, in_process: bool = False):
        """Start the GPU executor thread in the main process."""
        if self._running:
            if (not bool(in_process)) and bool(getattr(self, "_in_process_queues", False)):
                try:
                    self.stop()
                except Exception as e:
                    logger.debug(f"gpu_executor:start: {e}")
                    return
            else:
                return
        self._requests_processed = 0
        self._response_delivery.reset()
        start_settings = _load_executor_start_settings(
            in_process=bool(in_process),
            env_get_fn=env_get,
            env_flag_fn=env_flag,
            os_name=os.name,
            env_config=ENV,
            system_timer_override_allowed_fn=_system_timer_override_allowed,
            default_heartbeat_path_fn=_default_executor_heartbeat_path,
        )
        self._last_work_end_ts = None
        self._response_queues = {}
        self._next_worker_id = 0
        self._taichi_ready = False
        self._last_init_error = None
        self._staged_requests.clear()
        self._ga_owner_turn_streak = 0
        self._ready_event.clear()
        self.clear_abort()
        self._last_ref_arrays_sig = None
        self._live.configure(
            enabled=bool(start_settings.live_enabled),
            interval_sec=float(start_settings.live_interval_sec),
        )
        self._in_process_queues = bool(in_process)
        self._high_res_timer_enabled = False
        self._heartbeat = ExecutorHeartbeatWriter(
            path=start_settings.heartbeat_path,
            interval_sec=float(start_settings.heartbeat_interval_sec),
        )
        if bool(start_settings.enable_high_res_timer):
            self._high_res_timer_enabled = bool(_acquire_windows_timer_period_1ms())
        self._request_queue = queue.Queue() if self._in_process_queues else multiprocessing.Queue()
        self._running = True
        self._executor_thread = threading.Thread(
            target=self._executor_loop,
            name="GpuExecutorThread",
            daemon=True,
        )
        self._executor_thread.start()
        logger.debug("[GpuExecutor] Started")
    def stop(self):
        """Stop the GPU executor."""
        if not self._running:
            return
        self.request_abort("shutdown")
        _send_shutdown_request(self._request_queue)
        if self._executor_thread:
            self._executor_thread.join(timeout=10.0)
            try:
                if self._executor_thread.is_alive():
                    logger.warning("[GpuExecutor] Stop timed out; executor thread is still alive.")
                    self._write_heartbeat(phase="error", note="stop_timeout_thread_alive", force=True)
            except Exception as e:
                logger.debug(f"gpu_executor:stop: {e}")
        self._running = False
        if self._high_res_timer_enabled:
            _release_windows_timer_period_1ms()
            self._high_res_timer_enabled = False
        stop_profiler_settings = _load_executor_stop_profiler_settings(env_flag_fn=env_flag, env_config=ENV)
        # NOTE: the structured FILE dump (kernel_profiler_dump_path) runs on the OWNER thread
        # at the SHUTDOWN break (_maybe_dump_kernel_profiler_on_owner_thread); doing Taichi
        # profiler reads here (a different thread) races Vulkan teardown. Only the optional
        # human stdout table is emitted from stop().
        _print_taichi_kernel_profiler(enabled=bool(stop_profiler_settings.print_taichi_kernel_profiler))
        logger.debug("[GpuExecutor] Stopped. Processed %s requests.", self._requests_processed)
    def register_worker(self) -> tuple:
        """
        Register a new worker and get its communication queues.
        Returns:
            (worker_id, request_queue, response_queue)
        """
        registered = _register_executor_worker(
            next_worker_id=self._next_worker_id,
            request_queue=self._request_queue,
            response_queues=self._response_queues,
            response_queue_factory=queue.Queue if self._in_process_queues else multiprocessing.Queue,
        )
        self._next_worker_id = int(registered.next_worker_id)
        return registered.as_tuple()
    def _maybe_live_report(self) -> None:
        self._live.maybe_report()
    def unregister_worker(self, worker_id: int):
        """Unregister a worker (cleanup)."""
        _unregister_executor_worker(worker_id=worker_id, response_queues=self._response_queues)
    def _write_heartbeat(
        self,
        *,
        phase: str,
        batch: list[GpuRequest] | None = None,
        note: str = "",
        force: bool = False,
    ) -> None:
        self._heartbeat.write(
            phase=phase,
            batch=batch,
            note=note,
            force=force,
            ready=bool(self._taichi_ready),
            running=bool(self._running),
            requests_processed=int(self._requests_processed),
            response_put_failures_total=int(self._response_delivery.failures_total),
        )
    def _executor_loop(self):
        """Main GPU execution loop with batch coalescing."""
        try:
            from .taichi_gem.runtime import init_taichi
            init_taichi()
            logger.debug("[GpuExecutor] Taichi initialized")
        except Exception as e:
            self._taichi_ready = False
            init_failure = _build_taichi_init_failure_report(e, heartbeat_path=self._heartbeat.path)
            self._last_init_error = init_failure.error
            self._running = False
            self._ready_event.set()
            self._write_heartbeat(phase="init_failed", note=self._last_init_error, force=True)
            logger.debug("[GpuExecutor] Taichi init failed: %s", e)
            return
        self._write_heartbeat(phase="init_ok", force=True)
        try:
            # FG fused-path runtime warmup: the group-row builder dispatches Taichi
            # kernels and its module warm-flag is not thread-safe. Warm ONCE here on
            # the owner thread so no prep/FG worker thread ever performs the first
            # dispatch (single-GPU-ownership rule; prep threads stay Taichi-free).
            from .taichi_gem.force_greats.response_frontier import warmup_response_frontier_group_builder
            from .taichi_gem.force_greats.response_ftff_prune import warmup_response_ftff_prune

            warmup_response_ftff_prune()
            warmup_response_frontier_group_builder()
        except Exception as e:
            self._taichi_ready = False
            self._last_init_error = f"GPU executor FG frontier warmup failed: {type(e).__name__}: {e}"
            self._running = False
            self._ready_event.set()
            self._write_heartbeat(phase="warmup_failed", note=self._last_init_error, force=True)
            return
        warmup_fg = bool(getattr(ENV, "gpu_executor_warmup_fg", False))
        warmup_ga = True
        if warmup_fg or warmup_ga:
            try:
                from .taichi_gem import runtime as ti_runtime
                lock_cm = ti_runtime.offline_cache_lock(timeout_sec=None)
            except Exception as e:
                logger.debug(f"gpu_executor:_executor_loop: {e}")
                lock_cm = nullcontext("")
            self._write_heartbeat(phase="warmup_wait", force=True)
            try:
                with lock_cm as cache_dir:
                    sentinel_path = _warmup_sentinel_path(cache_dir)
                    warmup_cached = bool(
                        sentinel_path is not None
                        and sentinel_path.exists()
                        and _warmup_sentinel_is_fresh(
                            sentinel_path=sentinel_path,
                            warmup_fg=bool(warmup_fg),
                            warmup_ga=bool(warmup_ga),
                        )
                    )
                    if warmup_cached:
                        self._write_heartbeat(phase="warmup_cached", force=True)
                        try:
                            if warmup_fg:
                                self._write_heartbeat(phase="warmup_fg_cached", force=True)
                                _warmup_fg_response_frontier_runtime()
                            if warmup_ga:
                                self._write_heartbeat(phase="warmup_ga_cached", force=True)
                                from .taichi_gem.api import ga_operations as ga_ops
                                ga_ops.warmup_ga_kernels_light()
                        except Exception as e:
                            self._taichi_ready = False
                            self._last_init_error = f"GPU executor warmup failed: {type(e).__name__}: {e}"
                            self._running = False
                            self._ready_event.set()
                            self._write_heartbeat(phase="warmup_failed", note=self._last_init_error, force=True)
                            return
                    else:
                        sentinel_error = ""
                        try:
                            if warmup_fg:
                                try:
                                    self._write_heartbeat(phase="warmup_fg", force=True)
                                except Exception as e:
                                    logger.debug(f"gpu_executor:_executor_loop: {e}")
                                t0 = perf_counter()
                                _warmup_fg_response_frontier_runtime()
                                dt_ms = (perf_counter() - t0) * 1000.0
                                if ENV.perf_timing:
                                    logger.debug("[GpuExecutor] Warmed FG kernels in %.1fms", dt_ms)
                            if warmup_ga:
                                try:
                                    self._write_heartbeat(phase="warmup_ga", force=True)
                                except Exception as e:
                                    logger.debug(f"gpu_executor:_executor_loop: {e}")
                                t0 = perf_counter()
                                from .taichi_gem.api import ga_operations as ga_ops
                                ga_ops.warmup_ga_kernels_light()
                                dt_ms = (perf_counter() - t0) * 1000.0
                                if ENV.perf_timing:
                                    logger.debug("[GpuExecutor] Warmed GA kernels in %.1fms", dt_ms)
                        except Exception as e:
                            sentinel_error = f"{type(e).__name__}: {e}"
                            try:
                                logger.debug("[GpuExecutor] Warmup failed: %s", sentinel_error)
                            except Exception as e:
                                logger.debug(f"gpu_executor:_executor_loop: {e}")
                        finally:
                            if sentinel_path is not None:
                                payload = _build_warmup_sentinel_payload(
                                    ok=not bool(sentinel_error),
                                    error=str(sentinel_error or ""),
                                    pid=int(os.getpid()),
                                    warmed_at_ms=int(time.time() * 1000.0),
                                    warmup_fg=bool(warmup_fg),
                                    warmup_ga=bool(warmup_ga),
                                )
                                _write_warmup_sentinel_payload(sentinel_path=sentinel_path, payload=payload)
                            if sentinel_error:
                                self._taichi_ready = False
                                self._last_init_error = f"GPU executor warmup failed: {sentinel_error}"
                                self._running = False
                                self._ready_event.set()
                                self._write_heartbeat(phase="warmup_failed", note=self._last_init_error, force=True)
                                return
            except Exception as e:
                warmup_error = f"{type(e).__name__}: {e}"
                logger.debug(f"gpu_executor:_executor_loop: {e}")
                try:
                    if warmup_fg:
                        _warmup_fg_response_frontier_runtime()
                    if warmup_ga:
                        from .taichi_gem.api import ga_operations as ga_ops
                        ga_ops.warmup_ga_kernels_light()
                except Exception as e:
                    warmup_error = f"{warmup_error}; fallback warmup failed: {type(e).__name__}: {e}"
                    logger.debug(f"gpu_executor:_executor_loop: {e}")
                    self._taichi_ready = False
                    self._last_init_error = f"GPU executor warmup failed: {warmup_error}"
                    self._running = False
                    self._ready_event.set()
                    self._write_heartbeat(phase="warmup_failed", note=self._last_init_error, force=True)
                    return
        self._taichi_ready = True
        self._ready_event.set()
        self._write_heartbeat(phase="ready", force=True)
        def _try_put_response(req: GpuRequest, resp: GpuResponse) -> bool:
            return self._response_delivery.try_put(self._response_queues, req, resp)
        env_refresh_counter = 0
        cached_batch_settings = _load_loop_batch_settings(env_config=ENV, env_get=env_get)
        live_enabled = bool(self._live.enabled)
        while self._running:
            batch: list[GpuRequest] = []
            responded_ids: set[int] = set()
            try:
                if env_refresh_counter == 0:
                    cached_batch_settings = _load_loop_batch_settings(env_config=ENV, env_get=env_get)
                env_refresh_counter = (env_refresh_counter + 1) % 64
                queue_depth_hint = _safe_qsize(self._request_queue)
                batch_plan = _plan_loop_batch(
                    cached_batch_settings,
                    in_process_queues=bool(self._in_process_queues),
                    queue_depth_hint=int(queue_depth_hint),
                )
                batch_wait_ms = int(batch_plan.wait_ms)
                batch_max = int(batch_plan.max_batch)
                t_wait0 = perf_counter()
                batch = self._gather_batch(max_wait_ms=batch_wait_ms, max_batch_size=batch_max)
                dt_wait = perf_counter() - t_wait0
                if live_enabled:
                    self._live.record_wait(float(dt_wait))
                if live_enabled:
                    self._maybe_live_report()
                if not batch:
                    self._write_heartbeat(phase="idle")
                    continue
                if any(r.request_type == GpuRequestType.SHUTDOWN for r in batch):
                    self._write_heartbeat(phase="stopping", batch=batch, force=True)
                    # Gated DEBUG instrumentation (OFF by default): snapshot the Taichi
                    # kernel profiler to TAICHI_KERNEL_PROFILER_PATH HERE, on the owner
                    # thread where the Taichi/Vulkan runtime lives and is still fully alive.
                    # Doing it from the external stop() (a different thread) races Vulkan
                    # teardown and segfaults. No-op unless the dump path is set.
                    self._maybe_dump_kernel_profiler_on_owner_thread()
                    # Finalize the Taichi runtime HERE, on the owner thread, so the
                    # offline kernel cache dumps synchronously while the Vulkan runtime
                    # is fully alive. Leaving finalization to interpreter atexit races
                    # daemon-thread teardown and truncates the dump (observed: 1-9 of
                    # ~40 .tic entries persisted per run), so the expensive fused GA/FG
                    # kernels never enter the cache and every process pays the full
                    # warmup recompile with the GPU idle.
                    self._finalize_taichi_on_owner_thread()
                    self._running = False
                    break
                self._write_heartbeat(phase="running", batch=batch)
                grouped_handlers = {
                    GpuRequestType.GPU_NATIVE_GA_RUN: self._execute_gpu_native_ga_run_batch,
                }
                def _deliver_group_responses(
                    request_type: GpuRequestType,
                    requests: list[GpuRequest],
                    responses: list[GpuResponse],
                    dt_exec: float,
                ) -> None:
                    response_count = int(len(responses))
                    for idx, req in enumerate(requests):
                        resp = responses[idx] if idx < response_count else None
                        if resp is None:
                            resp = GpuResponse(
                                request_id=req.request_id,
                                success=False,
                                error=f"GpuExecutor {request_type.value} batch returned no response (internal error)",
                            )
                        if _try_put_response(req, resp):
                            responded_ids.add(int(req.request_id))
                        self._requests_processed += 1
                    if live_enabled:
                        self._live.record_exec(request_type, exec_sec=float(dt_exec), count=len(requests))
                        self._maybe_live_report()
                    if request_type == GpuRequestType.GPU_NATIVE_GA_RUN:
                        self._ga_owner_turn_streak = min(1024, int(self._ga_owner_turn_streak) + 1)
                    else:
                        self._ga_owner_turn_streak = 0
                def _execute_single_request(req: GpuRequest) -> None:
                    exec_started = perf_counter()
                    response = self._execute_request(req)
                    dt_exec = perf_counter() - exec_started
                    if response is None:
                        response = GpuResponse(
                            request_id=req.request_id,
                            success=False,
                            error="GpuExecutor returned no response (internal error)",
                        )
                    if _try_put_response(req, response):
                        responded_ids.add(int(req.request_id))
                    self._requests_processed += 1
                    if live_enabled:
                        self._live.record_exec(req.request_type, exec_sec=float(dt_exec), count=1)
                        self._maybe_live_report()
                    self._ga_owner_turn_streak = 0
                def _execute_grouped_requests(
                    request_type: GpuRequestType, requests: list[GpuRequest], handler
                ) -> None:
                    if not requests:
                        return
                    if request_type == GpuRequestType.GPU_NATIVE_GA_RUN:
                        # Each GA run carries its own fused GA->FG owner continuation
                        # (Slice 3): the owner scores FG in the GA turn and returns it
                        # with the payload. There is no separate FG batch request to
                        # interleave between GA runs anymore.
                        for req in requests:
                            exec_started = perf_counter()
                            responses = list(handler([req]) or [])
                            _deliver_group_responses(request_type, [req], responses, perf_counter() - exec_started)
                        return
                    exec_started = perf_counter()
                    responses = list(handler(requests) or [])
                    _deliver_group_responses(request_type, requests, responses, perf_counter() - exec_started)
                execution_units = _plan_execution_units(
                    batch,
                    grouped_request_types=set(grouped_handlers),
                )
                for unit in execution_units:
                    request_type = unit.request_type
                    if unit.grouped:
                        _execute_grouped_requests(
                            request_type,
                            list(unit.requests),
                            handler=grouped_handlers[request_type],
                        )
                        continue
                    req = unit.requests[0]
                    _execute_single_request(req)
                work_end_ts = perf_counter()
                self._last_work_end_ts = float(work_end_ts)
            except Exception as e:
                err = f"{type(e).__name__}: {e}"
                for req in batch or []:
                    try:
                        if req.request_type == GpuRequestType.SHUTDOWN:
                            continue
                        if int(req.request_id) in responded_ids:
                            continue
                        resp = GpuResponse(request_id=req.request_id, success=False, error=f"GpuExecutor error: {err}")
                        _try_put_response(req, resp)
                    except (ValueError, TypeError, AttributeError):
                        continue
                try:
                    logger.debug("[GpuExecutor] Error: %s", e)
                except Exception as e:
                    logger.debug(f"gpu_executor:_execute_grouped_requests: {e}")
                try:
                    traceback.print_exc()
                except Exception as e:
                    logger.debug(f"gpu_executor:_execute_grouped_requests: {e}")
                self._write_heartbeat(phase="error", batch=batch, note=str(err), force=True)
        self._write_heartbeat(phase="stopped", note=self._last_init_error or "", force=True)
    def _queue_get(self, timeout: float):
        return _get_with_short_wait_spin(
            self._request_queue,
            timeout=float(timeout),
            in_process_queues=bool(self._in_process_queues),
            short_wait_spin_sec=float(getattr(self, "_short_wait_spin_sec", 0.0) or 0.0),
            short_wait_spin_yield_rounds=int(getattr(self, "_short_wait_spin_yield_rounds", 0) or 0),
        )
    def _pop_queue_request(self, timeout: float) -> "GpuRequest":
        request = self._queue_get(timeout)
        return _stamp_request_dequeue(request)
    def _prefetch_ga_recovery_requests(self, *, deadline: float, batch_max_size: int) -> None:
        _prefetch_ga_recovery_requests(
            in_process_queues=bool(self._in_process_queues),
            ga_owner_turn_streak=int(self._ga_owner_turn_streak),
            staged_requests=self._staged_requests,
            deadline=float(deadline),
            batch_max_size=int(batch_max_size),
            streak_cap=int(_ga_recovery_streak_cap(env_get=env_get)),
            lookahead_limit=int(_ga_recovery_lookahead_limit(batch_max_size=int(batch_max_size), env_get=env_get)),
            pop_queue_request=self._pop_queue_request,
            perf_counter_fn=perf_counter,
            is_ga_recovery_request=_is_ga_recovery_request,
            empty_exception=queue.Empty,
        )
    def _pop_seed_request(self, *, timeout: float, deadline: float, batch_max_size: int) -> "GpuRequest":
        if not self._staged_requests:
            _stage_request(self._staged_requests, self._pop_queue_request(timeout))
        self._prefetch_ga_recovery_requests(deadline=deadline, batch_max_size=int(batch_max_size))
        if (
            self._in_process_queues
            and int(self._ga_owner_turn_streak) >= int(_ga_recovery_streak_cap(env_get=env_get))
            and self._staged_requests
            and self._staged_requests[0].request_type == GpuRequestType.GPU_NATIVE_GA_RUN
        ):
            recovery_idx = _staged_ga_recovery_index(
                list(self._staged_requests),
                is_ga_recovery_request=_is_ga_recovery_request,
            )
            if recovery_idx is not None:
                return _pop_staged_request(self._staged_requests, index=int(recovery_idx))
        return _pop_staged_request(self._staged_requests, index=0)
    def _pop_followup_request(self, timeout: float) -> "GpuRequest":
        if self._staged_requests:
            return _pop_staged_request(self._staged_requests, index=0)
        return self._pop_queue_request(timeout)
    def _gather_batch(self, max_wait_ms: int = 10, max_batch_size: int = 8) -> list:
        """
        Gather pending requests into a batch for coalesced execution.
        Args:
            max_wait_ms: Max time to wait for additional requests (ms)
            max_batch_size: Max requests per batch
        Returns:
            List of GpuRequest objects
        """
        batch: list[GpuRequest] = []
        deadline = perf_counter() + (max_wait_ms / 1000.0)
        coalescable_types = COALESCABLE_REQUEST_TYPES
        inproc_settings = _load_inprocess_coalesce_settings(
            max_wait_ms=int(max_wait_ms),
            in_process_queues=bool(self._in_process_queues),
            env_get=env_get,
            env_flag_fn=env_flag,
        )
        inproc_coalesce_enabled = bool(inproc_settings.enabled)
        inproc_yields_left = int(inproc_settings.yields_left)
        while len(batch) < max_batch_size:
            remaining = deadline - perf_counter()
            if remaining <= 0 and len(batch) > 0:
                break  # Deadline passed, return what we have
            try:
                if self._in_process_queues:
                    last_end = self._last_work_end_ts
                    now_s = perf_counter() if len(batch) == 0 and last_end is not None else None
                    timeout = _select_inprocess_batch_timeout(
                        batch,
                        max_wait_ms=int(max_wait_ms),
                        remaining_s=float(remaining),
                        settings=inproc_settings,
                        last_work_end_ts=last_end,
                        now_s=now_s,
                        coalescable_request_types=coalescable_types,
                    )
                else:
                    timeout = max(0.001, remaining) if len(batch) > 0 else 0.1
                if len(batch) == 0:
                    request = self._pop_seed_request(
                        timeout=float(timeout),
                        deadline=float(deadline),
                        batch_max_size=int(max_batch_size),
                    )
                elif (
                    self._in_process_queues
                    and inproc_coalesce_enabled
                    and len(batch) > 0
                    and float(timeout) > 0.0
                    and not self._staged_requests
                ):
                    poll = _poll_inprocess_followup_nowait(
                        self._request_queue,
                        deadline_s=float(deadline),
                        yields_left=int(inproc_yields_left),
                        stamp_fn=_stamp_request_dequeue,
                        perf_counter_fn=perf_counter,
                        sleep_fn=time.sleep,
                    )
                    inproc_yields_left = int(poll.yields_left)
                    if poll.action == "request":
                        request = poll.request
                    elif poll.action == "continue":
                        continue
                    elif poll.action == "break":
                        break
                    else:
                        request = self._pop_followup_request(timeout)
                else:
                    request = self._pop_followup_request(timeout)
                if request.request_type == GpuRequestType.SHUTDOWN:
                    batch.append(request)
                    return batch
                batch.append(request)
                deadline = _extend_inprocess_after_first_deadline(
                    deadline,
                    in_process_queues=bool(self._in_process_queues),
                    settings=inproc_settings,
                    batch_size=len(batch),
                    request_type=request.request_type,
                    coalescable_request_types=coalescable_types,
                    now_fn=perf_counter,
                )
            except queue.Empty:
                break  # No more pending requests
        return batch

    def _execute_gpu_native_ga_run_batch(self, requests: list[GpuRequest]) -> list[GpuResponse]:
        """Execute multiple GPU_NATIVE_GA_RUN requests on the owner thread."""
        return _execute_gpu_native_ga_run_batch(
            requests,
            abort_requested=self.abort_requested,
            aborted_response=self._aborted_response,
            execute_single=self._execute_gpu_native_ga_run,
            execute_chunk=self._execute_gpu_native_ga_run_chunk,
            env_get_fn=env_get,
            estimate_work_units_fn=_request_work_units,
        )

    def _execute_gpu_native_ga_run_chunk(self, requests: list[GpuRequest]) -> list[GpuResponse]:
        return _execute_gpu_native_ga_run_chunk(
            requests,
            abort_requested=self.abort_requested,
            aborted_response=self._aborted_response,
            execute_single=self._execute_gpu_native_ga_run,
        )

    def _execute_gpu_native_ga_run(self, request: GpuRequest) -> GpuResponse:
        """Execute a full GPU-native GA run on the GPU-owner thread."""
        return _execute_gpu_native_ga_run_request(
            request,
            in_process_queues=bool(self._in_process_queues),
            abort_requested=self.abort_requested,
            raise_if_abort_requested=self._raise_if_abort_requested,
        )

    def _execute_load_refs(self, request: GpuRequest) -> GpuResponse:
        """Load reference arrays."""
        from .taichi_gem.api import load_ref_arrays
        outcome = _execute_load_refs(
            request,
            last_ref_arrays_sig=self._last_ref_arrays_sig,
            load_ref_arrays_fn=load_ref_arrays,
            ref_arrays_sig_fn=_ref_arrays_sig,
        )
        self._last_ref_arrays_sig = outcome.last_ref_arrays_sig
        return outcome.response
    @property
    def is_running(self) -> bool:
        return self._running
    @property
    def last_init_error(self) -> Optional[str]:
        return self._last_init_error
    def request_abort(self, reason: str = "abort requested") -> None:
        self._abort_state.request_abort(reason)
    def clear_abort(self) -> None:
        self._abort_state.clear()
    def abort_requested(self) -> bool:
        return self._abort_state.requested()
    def _raise_if_abort_requested(self) -> None:
        self._abort_state.raise_if_requested()
    def _aborted_response(self, request: GpuRequest) -> GpuResponse:
        return self._abort_state.response(request)
    def wait_until_ready(self, timeout: float | None = None) -> bool:
        if not self._running:
            return False
        self._ready_event.wait(timeout=timeout)
        return bool(self._taichi_ready)
    @property
    def stats(self) -> dict:
        return {
            "requests_processed": int(self._requests_processed),
            "registered_workers": int(len(self._response_queues)),
        }
_executor: Optional[GpuExecutor] = None
def get_gpu_executor() -> GpuExecutor:
    """Get the global GPU executor instance."""
    global _executor
    if _executor is None:
        _executor = GpuExecutor()
    return _executor
def _auto_stop_gpu_executor_at_exit() -> None:
    if not _executor_auto_stop_enabled(env_flag_fn=env_flag):
        return
    global _executor
    try:
        _stop_executor_if_running(_executor)
    except Exception as e:
        logger.debug(f"gpu_executor:_auto_stop_gpu_executor_at_exit: {e}")
atexit.register(_auto_stop_gpu_executor_at_exit)
