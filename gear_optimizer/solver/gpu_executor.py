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
from contextlib import nullcontext
from collections import defaultdict, deque
from time import perf_counter
from typing import Any, Optional, Dict
from gear_optimizer.core.env_config import ENV
from gear_optimizer.core.parsing import env_flag
from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.solver.gpu_executor_batching import (
    COALESCABLE_REQUEST_TYPES,
    is_ga_recovery_request as _is_ga_recovery_request,
    is_no_batch_request_type as _is_no_batch_request_type,
    ResponseDeliveryTracker,
    execute_request_from_dispatch as _execute_request_from_dispatch,
    plan_execution_units as _plan_execution_units,
)
from gear_optimizer.solver.gpu_executor_types import (
    GpuRequest,
    GpuRequestType,
    GpuResponse,
)
from gear_optimizer.solver.gpu_executor_profile import (
    batch_trace_context as _batch_trace_context,
    estimate_request_work_units,
    load_workload_profile_settings as _load_workload_profile_settings,
    record_workload_batch_state as _record_workload_batch_state,
    emit_workload_batch_profile as _emit_workload_batch_profile,
    emit_workload_stop_summary as _emit_workload_stop_summary,
    maybe_emit_workload_window_profile as _maybe_emit_workload_window_profile,
    summarize_batch,
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
    prefetch_fg_continuation_requests as _prefetch_fg_continuation_requests,
    prefetch_ga_recovery_requests as _prefetch_ga_recovery_requests,
    stage_request as _stage_request,
    staged_fg_continuation_index as _staged_fg_continuation_index,
    staged_ga_recovery_index as _staged_ga_recovery_index,
    stamp_request_dequeue as _stamp_request_dequeue,
    build_taichi_init_failure_report as _build_taichi_init_failure_report,
    build_warmup_sentinel_payload as _build_warmup_sentinel_payload,
    default_executor_heartbeat_path as _default_executor_heartbeat_path,
    executor_auto_stop_enabled as _executor_auto_stop_enabled,
    ga_light_warmup_enabled as _ga_light_warmup_enabled,
    load_executor_start_settings as _load_executor_start_settings,
    load_executor_stop_profiler_settings as _load_executor_stop_profiler_settings,
    print_taichi_kernel_profiler as _print_taichi_kernel_profiler,
    report_gpu_profiler as _report_gpu_profiler,
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
from gear_optimizer.solver.gpu_executor_profile import ExecutorTraceWriter
from gear_optimizer.solver.gpu_executor_batching import (
    execute_gpu_native_ga_run_batch as _execute_gpu_native_ga_run_batch,
    execute_gpu_native_ga_run_chunk as _execute_gpu_native_ga_run_chunk,
)
from gear_optimizer.solver.gpu_executor_batching import (
    execute_force_greats_response_frontier_score_batch as _execute_force_greats_response_frontier_score_batch_request,
    execute_gpu_native_ga_run as _execute_gpu_native_ga_run_request,
)
from gear_optimizer.solver.gpu_executor_lifecycle import (
    get_with_short_wait_spin as _get_with_short_wait_spin,
    load_short_wait_spin_settings as _load_short_wait_spin_settings,
    poll_inprocess_followup_nowait as _poll_inprocess_followup_nowait,
    safe_qsize as _safe_qsize,
)
from gear_optimizer.solver.gpu_executor_profile import (
    build_exec_breakdown_summary as _build_exec_breakdown_summary,
    build_executor_idle_summary as _build_executor_idle_summary,
    build_executor_profile_stats as _build_executor_profile_stats,
    build_executor_stats as _build_executor_stats,
    build_idle_transition_summary as _build_idle_transition_summary,
    build_request_latency_summary as _build_request_latency_summary,
    compute_exec_breakdown as _compute_exec_breakdown,
    compute_request_latency_window as _compute_request_latency_window,
    exec_breakdown_enabled as _exec_breakdown_enabled,
    executor_profile_log_message as _executor_profile_log_message,
    exec_breakdown_summary_log_message as _exec_breakdown_summary_log_message,
    gpu_profiler_snapshot as _gpu_profiler_snapshot,
    idle_transition_summary_log_message as _idle_transition_summary_log_message,
    profile_events_output_enabled as _profile_events_output_enabled,
    record_exec_breakdown_stats as _record_exec_breakdown_stats,
    record_pack_stats as _record_pack_stats,
    record_request_latency_stats as _record_request_latency_stats,
    request_latency_summary_log_message as _request_latency_summary_log_message,
)
from gear_optimizer.core.parsing import env_get
_ENV_GET = os.environ.get
logger = logging.getLogger(__name__)


def _warmup_fg_response_frontier_runtime() -> None:
    from .taichi_gem.force_greats import fields as fg_fields
    from gear_optimizer.helpers.song_helpers.force_greats.response_frontier_warmup import (
        warmup_force_greats_response_frontier_runtime_imports,
    )

    fg_fields.ensure_ready_with_warmup()
    warmup_force_greats_response_frontier_runtime_imports()


def _precompute_timeline_gpu(calc_song, ref_arrays, *, song_slot: int = 0):
    from .taichi_gem.api.timeline import precompute_timeline_gpu as _precompute_timeline_gpu_fn
    return _precompute_timeline_gpu_fn(calc_song, ref_arrays, song_slot=song_slot)
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
        from gear_optimizer.core.env_config import ENV
        self._profile_enabled = ENV.gpu_executor_profile
        self._wait_sec = 0.0
        self._exec_sec = 0.0
        self._req_type_counts = defaultdict(int)
        self._req_type_exec_sec = defaultdict(float)
        self._req_type_pack_sec = defaultdict(float)
        self._req_type_host_sec = defaultdict(float)
        self._req_type_gpu_kernel_sec = defaultdict(float)
        self._req_type_gpu_upload_sec = defaultdict(float)
        self._req_type_gpu_download_sec = defaultdict(float)
        self._exec_breakdown_enabled = _exec_breakdown_enabled(
            profile_enabled=bool(self._profile_enabled),
            gpu_profiler_enabled=bool(ENV.gpu_profiler),
            env_flag_fn=env_flag,
        )
        self._pack_sec = 0.0
        self._batch_size_counts = defaultdict(int)
        self._batches_observed = 0
        self._batch_size_sum = 0
        self._idle_gaps: list[float] = []
        self._idle_sample_threshold_sec = 0.001
        self._profile_loop_start_ts: Optional[float] = None
        self._profile_first_work_ts: Optional[float] = None
        self._profile_last_work_end_ts: Optional[float] = None
        self._last_work_end_ts: Optional[float] = None
        self._profile_shutdown_ts: Optional[float] = None
        self._idle_transitions_sec = defaultdict(float)
        self._idle_transitions_count = defaultdict(int)
        self._last_work_req_type: Optional[GpuRequestType] = None
        self._lat_sample_cap = 5000
        self._lat_counts = defaultdict(int)
        self._lat_total_sec = defaultdict(float)
        self._lat_max_sec = defaultdict(float)
        self._lat_samples = defaultdict(list)
        self._lat_queue_total_sec = defaultdict(float)
        self._lat_queue_max_sec = defaultdict(float)
        self._lat_queue_samples = defaultdict(list)
        self._lat_in_exec_total_sec = defaultdict(float)
        self._lat_in_exec_max_sec = defaultdict(float)
        self._lat_in_exec_samples = defaultdict(list)
        self._trace = ExecutorTraceWriter()
        self._live = LiveReporter()
        self._last_batch_plan_mode = "balanced"
        workload_profile_settings = _load_workload_profile_settings(
            profile_enabled=bool(self._profile_enabled),
            env_flag_fn=env_flag,
            env_get_fn=_ENV_GET,
        )
        self._workload_profile_enabled = workload_profile_settings.enabled
        self._workload_profile_interval_sec = workload_profile_settings.interval_sec
        self._workload_profile_last_emit_ts: Optional[float] = None
        self._workload_events_emitted = 0
        self._workload_batch_seq = 0
        self._workload_recent_batches: deque[dict[str, Any]] = deque(maxlen=256)
        self._workload_mode_counts = defaultdict(int)
        self._workload_mode_wait_sec = defaultdict(float)
        self._workload_mode_exec_sec = defaultdict(float)
        self._workload_queue_depth_samples: deque[float] = deque(maxlen=4096)
        self._workload_age_ms_samples: deque[float] = deque(maxlen=4096)
        self._workload_units_samples: deque[float] = deque(maxlen=4096)
        self._workload_diversity_samples: deque[float] = deque(maxlen=4096)
        self._workload_pressure_samples: deque[float] = deque(maxlen=4096)
        self._high_res_timer_enabled = False
        short_wait_settings = _load_short_wait_spin_settings(env_get_fn=_ENV_GET)
        self._short_wait_spin_sec = short_wait_settings.short_wait_spin_sec
        self._short_wait_spin_yield_rounds = short_wait_settings.short_wait_spin_yield_rounds
        self._dispatch = {
            GpuRequestType.LOAD_REF_ARRAYS: self._execute_load_refs,
            GpuRequestType.GPU_NATIVE_GA_RUN: self._execute_gpu_native_ga_run,
            GpuRequestType.FORCE_GREATS_RESPONSE_FRONTIER_SCORE_BATCH: (
                self._execute_force_greats_response_frontier_score_batch
            ),
        }
    def _record_pack(self, request_type: GpuRequestType, dt_sec: float) -> None:
        self._pack_sec = _record_pack_stats(
            request_type,
            dt_sec,
            pack_sec=self._pack_sec,
            req_type_pack_sec=self._req_type_pack_sec,
        )
    def _gpu_prof_snapshot(self) -> tuple[float, float, float]:
        """
        Best-effort snapshot of cumulative in-process GPU profiler totals.
        Returns:
            (kernel_sec, upload_sec, download_sec)
        """
        return _gpu_profiler_snapshot(enabled=bool(self._exec_breakdown_enabled))
    def _record_exec_breakdown(
        self,
        request_type: GpuRequestType,
        *,
        exec_wall_sec: float,
        prof_before: tuple[float, float, float] | None,
    ) -> None:
        """
        Attribute one executor exec window to host-vs-GPU buckets.
        `exec_wall_sec` is the full owner-thread wall time for the request/coalesced batch.
        GPU deltas are read from `gpu_profiler`; the residual is attributed to host work.
        """
        prof_after = self._gpu_prof_snapshot() if prof_before is not None else None
        breakdown = _compute_exec_breakdown(
            exec_wall_sec=float(exec_wall_sec),
            prof_before=prof_before,
            prof_after=prof_after,
        )
        if breakdown is None:
            return
        _record_exec_breakdown_stats(
            request_type,
            breakdown,
            req_type_host_sec=self._req_type_host_sec,
            req_type_gpu_kernel_sec=self._req_type_gpu_kernel_sec,
            req_type_gpu_upload_sec=self._req_type_gpu_upload_sec,
            req_type_gpu_download_sec=self._req_type_gpu_download_sec,
        )
    def _record_latency(
        self,
        request: "GpuRequest",
        *,
        exec_start_ns: int,
        exec_end_ns: int,
    ) -> None:
        if not self._profile_enabled:
            return
        latency = _compute_request_latency_window(
            request,
            exec_start_ns=exec_start_ns,
            exec_end_ns=exec_end_ns,
        )
        if latency is None:
            return
        _record_request_latency_stats(
            latency,
            lat_counts=self._lat_counts,
            lat_total_sec=self._lat_total_sec,
            lat_max_sec=self._lat_max_sec,
            lat_samples=self._lat_samples,
            lat_queue_total_sec=self._lat_queue_total_sec,
            lat_queue_max_sec=self._lat_queue_max_sec,
            lat_queue_samples=self._lat_queue_samples,
            lat_in_exec_total_sec=self._lat_in_exec_total_sec,
            lat_in_exec_max_sec=self._lat_in_exec_max_sec,
            lat_in_exec_samples=self._lat_in_exec_samples,
            sample_cap=int(self._lat_sample_cap),
        )
    def _record_workload_batch(self, metrics: dict[str, Any]) -> None:
        if not metrics:
            return
        self._last_batch_plan_mode = _record_workload_batch_state(
            metrics,
            recent_batches=self._workload_recent_batches,
            mode_counts=self._workload_mode_counts,
            mode_wait_sec=self._workload_mode_wait_sec,
            mode_exec_sec=self._workload_mode_exec_sec,
            queue_depth_samples=self._workload_queue_depth_samples,
            age_ms_samples=self._workload_age_ms_samples,
            units_samples=self._workload_units_samples,
            diversity_samples=self._workload_diversity_samples,
            pressure_samples=self._workload_pressure_samples,
            last_batch_plan_mode=self._last_batch_plan_mode,
        )
        if self._workload_profile_enabled:
            if _emit_workload_batch_profile(metrics, emit_profile_event_fn=emit_profile_event):
                self._workload_events_emitted += 1
            self._maybe_emit_workload_profile()
    def _maybe_emit_workload_profile(self, *, force: bool = False) -> None:
        result = _maybe_emit_workload_window_profile(
            enabled=bool(self._workload_profile_enabled),
            force=bool(force),
            now=perf_counter(),
            last_emit_ts=self._workload_profile_last_emit_ts,
            interval_sec=float(self._workload_profile_interval_sec),
            recent_batches=self._workload_recent_batches,
            events_emitted=int(self._workload_events_emitted),
            log_enabled=bool(self._profile_enabled),
            log_debug=logger.debug,
            emit_profile_event_fn=emit_profile_event,
        )
        self._workload_profile_last_emit_ts = result.last_emit_ts
        self._workload_events_emitted = int(result.events_emitted)
    def _execute_request(self, request: GpuRequest) -> GpuResponse:
        """Dispatch a single request to the appropriate executor handler."""
        return _execute_request_from_dispatch(request, dispatch=self._dispatch)
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
        self._wait_sec = 0.0
        self._exec_sec = 0.0
        try:
            self._req_type_counts.clear()
            self._req_type_exec_sec.clear()
            self._req_type_host_sec.clear()
            self._req_type_gpu_kernel_sec.clear()
            self._req_type_gpu_upload_sec.clear()
            self._req_type_gpu_download_sec.clear()
            self._batch_size_counts.clear()
        except Exception as e:
            logger.debug(f"gpu_executor:start: {e}")
        self._batches_observed = 0
        self._batch_size_sum = 0
        self._idle_gaps = []
        start_settings = _load_executor_start_settings(
            in_process=bool(in_process),
            env_get_fn=env_get,
            env_flag_fn=env_flag,
            os_name=os.name,
            env_config=ENV,
            system_timer_override_allowed_fn=_system_timer_override_allowed,
            default_heartbeat_path_fn=_default_executor_heartbeat_path,
        )
        self._idle_sample_threshold_sec = float(start_settings.idle_sample_threshold_sec)
        self._profile_loop_start_ts = None
        self._profile_first_work_ts = None
        self._profile_last_work_end_ts = None
        self._last_work_end_ts = None
        self._profile_shutdown_ts = None
        self._idle_transitions_sec = defaultdict(float)
        self._idle_transitions_count = defaultdict(int)
        self._last_work_req_type = None
        try:
            self._lat_counts.clear()
            self._lat_total_sec.clear()
            self._lat_max_sec.clear()
            self._lat_samples.clear()
            self._lat_queue_total_sec.clear()
            self._lat_queue_max_sec.clear()
            self._lat_queue_samples.clear()
            self._lat_in_exec_total_sec.clear()
            self._lat_in_exec_max_sec.clear()
            self._lat_in_exec_samples.clear()
        except Exception as e:
            logger.debug(f"gpu_executor:start: {e}")
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
        self._trace.open(str(start_settings.trace_path or "").strip())
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
        self._trace.close()
        if self._profile_enabled:
            idle_summary = _build_executor_idle_summary(
                idle_gaps=self._idle_gaps,
                loop_start_ts=self._profile_loop_start_ts,
                first_work_ts=self._profile_first_work_ts,
                shutdown_ts=self._profile_shutdown_ts,
                last_work_end_ts=self._profile_last_work_end_ts,
            )
            logger.debug(
                _executor_profile_log_message(
                    wait_sec=self._wait_sec,
                    exec_sec=self._exec_sec,
                    requests_processed=int(self._requests_processed),
                    batch_size_sum=int(self._batch_size_sum),
                    batches_observed=int(self._batches_observed),
                    pack_sec=self._pack_sec,
                    req_type_exec_sec=self._req_type_exec_sec,
                    req_type_counts=self._req_type_counts,
                    req_type_pack_sec=self._req_type_pack_sec,
                    batch_size_counts=self._batch_size_counts,
                    idle_gaps_count=len(self._idle_gaps),
                    idle_summary=idle_summary,
                )
            )
            try:
                if self._lat_counts:
                    rows = _build_request_latency_summary(
                        lat_counts=self._lat_counts,
                        lat_total_sec=self._lat_total_sec,
                        lat_samples=self._lat_samples,
                        lat_queue_total_sec=self._lat_queue_total_sec,
                        lat_queue_samples=self._lat_queue_samples,
                        lat_in_exec_total_sec=self._lat_in_exec_total_sec,
                        lat_in_exec_samples=self._lat_in_exec_samples,
                    )
                    msg = _request_latency_summary_log_message(rows)
                    if msg:
                        logger.debug(msg)
            except Exception as e:
                logger.debug(f"gpu_executor:_p95: {e}")
            try:
                if self._req_type_exec_sec:
                    breakdown_rows = _build_exec_breakdown_summary(
                        req_type_exec_sec=self._req_type_exec_sec,
                        req_type_host_sec=self._req_type_host_sec,
                        req_type_gpu_kernel_sec=self._req_type_gpu_kernel_sec,
                        req_type_gpu_upload_sec=self._req_type_gpu_upload_sec,
                        req_type_gpu_download_sec=self._req_type_gpu_download_sec,
                    )
                    msg = _exec_breakdown_summary_log_message(breakdown_rows)
                    if msg:
                        logger.debug(msg)
            except Exception as e:
                logger.debug(f"gpu_executor:_p95: {e}")
            try:
                transition_rows = _build_idle_transition_summary(
                    idle_transitions_sec=self._idle_transitions_sec,
                    idle_transitions_count=self._idle_transitions_count,
                )
                msg = _idle_transition_summary_log_message(transition_rows)
                if msg:
                    logger.debug(msg)
            except (ValueError, TypeError, KeyError):
                pass
            try:
                self._maybe_emit_workload_profile(force=True)
            except Exception as e:
                logger.debug(f"gpu_executor:_p95: {e}")
            try:
                if self._workload_recent_batches:
                    window = list(self._workload_recent_batches)
                    _emit_workload_stop_summary(
                        window,
                        age_ms_samples=self._workload_age_ms_samples,
                        units_samples=self._workload_units_samples,
                        diversity_samples=self._workload_diversity_samples,
                        queue_depth_samples=self._workload_queue_depth_samples,
                        mode_counts=self._workload_mode_counts,
                        events_emitted=int(self._workload_events_emitted),
                        last_mode=str(self._last_batch_plan_mode),
                        log_debug=logger.debug,
                        emit_profile_event_fn=emit_profile_event,
                    )
            except (ValueError, TypeError, KeyError, AttributeError):
                pass
        if self._workload_profile_enabled and (not self._profile_enabled):
            try:
                self._maybe_emit_workload_profile(force=True)
            except Exception as e:
                logger.debug(f"gpu_executor:_p95: {e}")
        stop_profiler_settings = _load_executor_stop_profiler_settings(env_flag_fn=env_flag, env_config=ENV)
        _print_taichi_kernel_profiler(enabled=bool(stop_profiler_settings.print_taichi_kernel_profiler))
        _report_gpu_profiler(enabled=bool(stop_profiler_settings.report_gpu_profiler))
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
    def _trace_event(
        self,
        *,
        event: str,
        wait_sec: float = 0.0,
        exec_sec: float = 0.0,
        batch_size: int = 0,
        types: str = "",
        planner_mode: str = "",
        queue_depth_hint: int = -1,
        pressure_hint: float = 0.0,
        work_units: float = 0.0,
        dominant_type: str = "",
        dominant_share_pct: float = 0.0,
        diversity_pct: float = 0.0,
        avg_submit_age_ms: float = 0.0,
    ) -> None:
        self._trace.write_event(
            event=event,
            in_process=bool(self._in_process_queues),
            wait_sec=wait_sec,
            exec_sec=exec_sec,
            batch_size=batch_size,
            types=types,
            planner_mode=planner_mode,
            queue_depth_hint=queue_depth_hint,
            pressure_hint=pressure_hint,
            work_units=work_units,
            dominant_type=dominant_type,
            dominant_share_pct=dominant_share_pct,
            diversity_pct=diversity_pct,
            avg_submit_age_ms=avg_submit_age_ms,
        )
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
        warmup_fg = bool(getattr(ENV, "gpu_executor_warmup_fg", False))
        warmup_ga = bool(getattr(ENV, "gpu_executor_warmup_ga", False))
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
                                self._write_heartbeat(phase="warmup_ga_live_cached", force=True)
                                from .taichi_gem.api import ga_operations as ga_ops
                                ga_ops.warmup_ga_live_request_kernels()
                        except Exception as e:
                            try:
                                logger.debug("[GpuExecutor] Cached warmup refresh failed: %s: %s", type(e).__name__, e)
                            except Exception as e:
                                logger.debug(f"gpu_executor:_executor_loop: {e}")
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
                                ga_ops.warmup_ga_kernels()
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
            except Exception as e:
                logger.debug(f"gpu_executor:_executor_loop: {e}")
                try:
                    if warmup_fg:
                        _warmup_fg_response_frontier_runtime()
                    if warmup_ga:
                        from .taichi_gem.api import ga_operations as ga_ops
                        ga_ops.warmup_ga_kernels()
                except Exception as e:
                    logger.debug(f"gpu_executor:_executor_loop: {e}")
        warmup_ga_light = _ga_light_warmup_enabled(warmup_ga=bool(warmup_ga), env_flag_fn=env_flag)
        if warmup_ga_light:
            try:
                from .taichi_gem.api import ga_operations as ga_ops
                ga_ops.warmup_ga_kernels_light()
            except Exception as e:
                logger.debug(f"gpu_executor:_executor_loop: {e}")
        self._taichi_ready = True
        self._ready_event.set()
        self._write_heartbeat(phase="ready", force=True)
        def _try_put_response(req: GpuRequest, resp: GpuResponse) -> bool:
            return self._response_delivery.try_put(self._response_queues, req, resp)
        env_refresh_counter = 0
        cached_batch_settings = _load_loop_batch_settings(env_config=ENV, env_get=_ENV_GET)
        profile_events_enabled = _profile_events_output_enabled(env_get_fn=env_get)
        trace_enabled = bool(self._trace.has_file or profile_events_enabled)
        need_batch_summary = bool(self._workload_profile_enabled or trace_enabled)
        live_enabled = bool(self._live.enabled)
        while self._running:
            batch: list[GpuRequest] = []
            responded_ids: set[int] = set()
            batch_metrics: dict[str, Any] = {}
            trace_shared_kwargs: dict[str, Any] = {}
            try:
                if env_refresh_counter == 0:
                    cached_batch_settings = _load_loop_batch_settings(env_config=ENV, env_get=_ENV_GET)
                env_refresh_counter = (env_refresh_counter + 1) % 64
                queue_depth_hint = _safe_qsize(self._request_queue)
                batch_plan = _plan_loop_batch(
                    cached_batch_settings,
                    in_process_queues=bool(self._in_process_queues),
                    queue_depth_hint=int(queue_depth_hint),
                )
                batch_wait_ms = int(batch_plan.wait_ms)
                batch_max = int(batch_plan.max_batch)
                if self._profile_enabled and self._profile_loop_start_ts is None:
                    self._profile_loop_start_ts = perf_counter()
                t_wait0 = perf_counter()
                batch = self._gather_batch(max_wait_ms=batch_wait_ms, max_batch_size=batch_max)
                dt_wait = perf_counter() - t_wait0
                self._wait_sec += dt_wait
                if live_enabled:
                    self._live.record_wait(float(dt_wait))
                if need_batch_summary:
                    self._workload_batch_seq += 1
                    batch_metrics = summarize_batch(
                        batch,
                        plan=batch_plan,
                        wait_sec=float(dt_wait),
                        batch_id=int(self._workload_batch_seq),
                        estimate_work_units_fn=estimate_request_work_units,
                        coalescable_request_types=COALESCABLE_REQUEST_TYPES,
                    )
                    if trace_enabled:
                        trace_shared_kwargs = _batch_trace_context(batch_metrics)
                if trace_enabled:
                    self._trace_event(
                        event="wait",
                        wait_sec=float(dt_wait),
                        batch_size=len(batch or []),
                        types=str(batch_metrics.get("types", "")),
                        **trace_shared_kwargs,
                    )
                if live_enabled:
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
                    self._write_heartbeat(phase="idle")
                    batch_metrics["exec_sec"] = 0.0
                    if self._workload_profile_enabled:
                        self._record_workload_batch(batch_metrics)
                    continue
                if any(r.request_type == GpuRequestType.SHUTDOWN for r in batch):
                    if self._profile_enabled:
                        self._profile_shutdown_ts = perf_counter()
                    self._write_heartbeat(phase="stopping", batch=batch, force=True)
                    batch_metrics["exec_sec"] = 0.0
                    if self._workload_profile_enabled:
                        self._record_workload_batch(batch_metrics)
                    self._running = False
                    break
                batch_exec_t0 = perf_counter()
                self._write_heartbeat(phase="running", batch=batch)
                grouped_handlers = {
                    GpuRequestType.GPU_NATIVE_GA_RUN: self._execute_gpu_native_ga_run_batch,
                }
                def _execute_grouped_requests(
                    request_type: GpuRequestType, requests: list[GpuRequest], handler
                ) -> None:
                    if not requests:
                        return
                    prof_before = self._gpu_prof_snapshot() if self._exec_breakdown_enabled else None
                    exec_start_ns = time.perf_counter_ns()
                    responses = list(handler(requests) or [])
                    exec_end_ns = time.perf_counter_ns()
                    dt_exec = float(exec_end_ns - exec_start_ns) / 1e9
                    self._record_exec_breakdown(
                        request_type,
                        exec_wall_sec=float(dt_exec),
                        prof_before=prof_before,
                    )
                    self._exec_sec += dt_exec
                    per_req = dt_exec / max(1, len(requests))
                    for _ in requests:
                        self._req_type_counts[request_type] += 1
                        self._req_type_exec_sec[request_type] += per_req
                        self._last_work_req_type = request_type
                    response_count = int(len(responses))
                    for idx, req in enumerate(requests):
                        resp = responses[idx] if idx < response_count else None
                        if resp is None:
                            resp = GpuResponse(
                                request_id=req.request_id,
                                success=False,
                                error=f"GpuExecutor {request_type.value} batch returned no response (internal error)",
                            )
                        self._record_latency(req, exec_start_ns=exec_start_ns, exec_end_ns=exec_end_ns)
                        if _try_put_response(req, resp):
                            responded_ids.add(int(req.request_id))
                        self._requests_processed += 1
                    if trace_enabled:
                        self._trace_event(
                            event="exec",
                            exec_sec=float(dt_exec),
                            batch_size=len(requests),
                            types=f"{request_type.value}:{len(requests)}",
                            **trace_shared_kwargs,
                        )
                    if live_enabled:
                        self._live.record_exec(request_type, exec_sec=float(dt_exec), count=len(requests))
                        self._maybe_live_report()
                    if request_type == GpuRequestType.GPU_NATIVE_GA_RUN:
                        self._ga_owner_turn_streak = min(1024, int(self._ga_owner_turn_streak) + 1)
                    else:
                        self._ga_owner_turn_streak = 0
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
                    prof_before = self._gpu_prof_snapshot() if self._exec_breakdown_enabled else None
                    exec_start_ns = time.perf_counter_ns()
                    response = self._execute_request(req)
                    exec_end_ns = time.perf_counter_ns()
                    dt_exec = float(exec_end_ns - exec_start_ns) / 1e9
                    self._record_exec_breakdown(
                        req.request_type,
                        exec_wall_sec=float(dt_exec),
                        prof_before=prof_before,
                    )
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
                    self._record_latency(req, exec_start_ns=exec_start_ns, exec_end_ns=exec_end_ns)
                    if _try_put_response(req, response):
                        responded_ids.add(int(req.request_id))
                    self._requests_processed += 1
                    if trace_enabled:
                        self._trace_event(
                            event="exec",
                            exec_sec=float(dt_exec),
                            batch_size=1,
                            types=f"{req.request_type.value}:1",
                            **trace_shared_kwargs,
                        )
                    if live_enabled:
                        self._live.record_exec(req.request_type, exec_sec=float(dt_exec), count=1)
                        self._maybe_live_report()
                    self._ga_owner_turn_streak = 0
                work_end_ts = perf_counter()
                self._last_work_end_ts = float(work_end_ts)
                if self._profile_enabled:
                    self._profile_last_work_end_ts = float(work_end_ts)
                batch_metrics["exec_sec"] = max(0.0, float(perf_counter() - batch_exec_t0))
                if self._workload_profile_enabled:
                    self._record_workload_batch(batch_metrics)
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
                try:
                    if (
                        self._workload_profile_enabled
                        and batch_metrics
                        and float(batch_metrics.get("exec_sec", 0.0) or 0.0) <= 0.0
                    ):
                        batch_metrics["exec_sec"] = 0.0
                        batch_metrics["error"] = str(err)
                        self._record_workload_batch(batch_metrics)
                except (ValueError, TypeError, KeyError, AttributeError):
                    pass
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
            streak_cap=int(_ga_recovery_streak_cap(env_get=_ENV_GET)),
            lookahead_limit=int(_ga_recovery_lookahead_limit(batch_max_size=int(batch_max_size), env_get=_ENV_GET)),
            pop_queue_request=self._pop_queue_request,
            perf_counter_fn=perf_counter,
            is_ga_recovery_request=_is_ga_recovery_request,
            empty_exception=queue.Empty,
        )
    def _prefetch_fg_continuation_requests(self, *, deadline: float, batch_max_size: int) -> None:
        _prefetch_fg_continuation_requests(
            in_process_queues=bool(self._in_process_queues),
            staged_requests=self._staged_requests,
            deadline=float(deadline),
            batch_max_size=int(batch_max_size),
            pop_queue_request=self._pop_queue_request,
            perf_counter_fn=perf_counter,
            empty_exception=queue.Empty,
        )
    def _pop_seed_request(self, *, timeout: float, deadline: float, batch_max_size: int) -> "GpuRequest":
        if not self._staged_requests:
            _stage_request(self._staged_requests, self._pop_queue_request(timeout))
        self._prefetch_fg_continuation_requests(deadline=deadline, batch_max_size=int(batch_max_size))
        self._prefetch_ga_recovery_requests(deadline=deadline, batch_max_size=int(batch_max_size))
        if (
            self._in_process_queues
            and int(self._ga_owner_turn_streak) >= int(_ga_recovery_streak_cap(env_get=_ENV_GET))
            and self._staged_requests
            and self._staged_requests[0].request_type == GpuRequestType.GPU_NATIVE_GA_RUN
        ):
            recovery_idx = _staged_ga_recovery_index(
                list(self._staged_requests),
                is_ga_recovery_request=_is_ga_recovery_request,
            )
            if recovery_idx is not None:
                return _pop_staged_request(self._staged_requests, index=int(recovery_idx))
        if self._in_process_queues and self._staged_requests:
            fg_idx = _staged_fg_continuation_index(list(self._staged_requests))
            if fg_idx is not None:
                return _pop_staged_request(self._staged_requests, index=int(fg_idx))
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
            env_get=_ENV_GET,
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
                if batch and _is_no_batch_request_type(request.request_type):
                    _stage_request(self._staged_requests, request, front=True)
                    break
                batch.append(request)
                if _is_no_batch_request_type(request.request_type):
                    break
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
            estimate_work_units_fn=estimate_request_work_units,
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

    def _execute_force_greats_response_frontier_score_batch(self, request: GpuRequest) -> GpuResponse:
        """Execute exact response-frontier FG scoring on the GPU-owner thread."""
        return _execute_force_greats_response_frontier_score_batch_request(
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
        profile_stats = None
        if self._profile_enabled:
            profile_stats = _build_executor_profile_stats(
                wait_sec=self._wait_sec,
                exec_sec=self._exec_sec,
                batches_observed=self._batches_observed,
                batch_size_sum=self._batch_size_sum,
                workload_events_emitted=self._workload_events_emitted,
                last_batch_plan_mode=self._last_batch_plan_mode,
                workload_units_samples=self._workload_units_samples,
                workload_age_ms_samples=self._workload_age_ms_samples,
                req_type_counts=self._req_type_counts,
                req_type_host_sec=self._req_type_host_sec,
                req_type_gpu_kernel_sec=self._req_type_gpu_kernel_sec,
                req_type_gpu_upload_sec=self._req_type_gpu_upload_sec,
                req_type_gpu_download_sec=self._req_type_gpu_download_sec,
            )
        return _build_executor_stats(
            requests_processed=self._requests_processed,
            registered_workers=len(self._response_queues),
            profile=profile_stats,
        )
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
