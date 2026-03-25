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
import logging
import os
import atexit
import json
import traceback
import time
import random
import math
import hashlib
from contextlib import nullcontext
from pathlib import Path
from collections import defaultdict, OrderedDict, deque
from time import perf_counter
from dataclasses import dataclass
from typing import Any, Optional, Dict
from enum import Enum

from gear_optimizer.core.env_config import ENV, TRUTHY_ENV_VALUES, env_flag
from gear_optimizer.core.fallback_monitor import warn_fallback
from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.core.types import JsonDict
from gear_optimizer.solver.windows_timer import (
    acquire_windows_timer_period_1ms as _acquire_windows_timer_period_1ms_shared,
    release_windows_timer_period_1ms as _release_windows_timer_period_1ms_shared,
    system_timer_override_allowed as _system_timer_override_allowed_shared,
)

_ENV_GET = os.environ.get
logger = logging.getLogger(__name__)


def _system_timer_override_allowed() -> bool:
    # Wrapper kept for monkeypatch-based tests.
    return bool(_system_timer_override_allowed_shared())


def _acquire_windows_timer_period_1ms() -> bool:
    # Wrapper kept for monkeypatch-based tests.
    return bool(_acquire_windows_timer_period_1ms_shared())


def _release_windows_timer_period_1ms() -> None:
    # Wrapper kept for monkeypatch-based tests.
    _release_windows_timer_period_1ms_shared()


class GpuRequestType(Enum):
    """Types of GPU requests that can be submitted."""

    SOLVE_GENOMES_FROM_REGISTRY = "solve_genomes_from_registry"
    LOAD_REF_ARRAYS = "load_ref_arrays"
    PRECOMPUTE_TIMELINE = "precompute_timeline_gpu"
    SOLVE_FORCE_GREATS_FINDER = "solve_force_greats_finder_gpu"
    GPU_NATIVE_GA_RUN = "gpu_native_ga_run"
    GA_STAGE_FG_GENOME_BASE_STATS = "ga_stage_fg_genome_base_stats"
    FG_RESET_GLOBAL_BEST = "fg_reset_global_best"
    FG_DOWNLOAD_GLOBAL_BEST = "fg_download_global_best"
    FG_SELECT_SIGNATURE_FRONTIER_BATCH = "fg_select_signature_frontier_batch"
    FG_COMPUTE_BREAKPOINTS = "fg_compute_breakpoints"
    FG_SOLVE_WITH_BREAKPOINTS = "fg_solve_with_breakpoints"
    FG_SOLVE_WITH_BREAKPOINTS_BATCH = "fg_solve_with_breakpoints_batch"
    GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS = "ga_fg_fused_solve_with_breakpoints"
    SHUTDOWN = "shutdown"


@dataclass
class GpuRequest:
    """A request to execute on the GPU executor."""

    request_type: GpuRequestType
    request_id: int
    worker_id: int
    payload: JsonDict
    # Perf timestamps (best-effort, optional). `perf_counter_ns()` is monotonic and comparable across processes.
    submit_perf_ns: int = 0
    dequeue_perf_ns: int = 0


@dataclass
class GpuResponse:
    """Response from GPU executor."""

    request_id: int
    success: bool
    result: Any = None
    error: Optional[str] = None


@dataclass(frozen=True)
class _BatchPlan:
    """Batch gather decision metadata for one executor loop."""

    wait_ms: int
    max_batch: int
    mode: str
    queue_depth_hint: int
    pressure_hint: float


# Global state for worker processes
_WORKER_MODE = False
_WORKER_ID: Optional[int] = None
_REQUEST_QUEUE: Optional[multiprocessing.Queue] = None
_RESPONSE_QUEUE: Optional[multiprocessing.Queue] = None
_REQUEST_COUNTER = 0
_PENDING_RESPONSES: OrderedDict[int, tuple["GpuResponse", float]] = OrderedDict()
_PENDING_RESPONSES_COND = threading.Condition()
_PENDING_TTL_SEC = max(0.0, float(getattr(ENV, "gpu_executor_pending_ttl_sec", 300.0) or 0.0))
_PENDING_MAX = max(0, int(getattr(ENV, "gpu_executor_pending_max", 2048) or 0))
_REGISTRY_STATIC_HANDLE_COUNTER = 0
_REGISTRY_STATIC_HANDLE_CACHE_MAX = max(16, int(_ENV_GET("GPU_EXECUTOR_REGISTRY_HANDLE_CACHE_MAX", "256") or "256"))
_REGISTRY_STATIC_HANDLE_CACHE: OrderedDict[tuple[Any, ...], dict[str, Any]] = OrderedDict()

_WORKER_RESPONSE_ROUTER_THREAD: threading.Thread | None = None
_WORKER_RESPONSE_ROUTER_STOP = threading.Event()


def _default_executor_heartbeat_path() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "bin" / "gpu_executor_heartbeat.json"


def _prune_pending_responses(now: float | None = None) -> None:
    with _PENDING_RESPONSES_COND:
        _prune_pending_responses_locked(now)


def _prune_pending_responses_locked(now: float | None = None) -> None:
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
    with _PENDING_RESPONSES_COND:
        _store_pending_response_locked(response)
        _PENDING_RESPONSES_COND.notify_all()


def _store_pending_response_locked(response: "GpuResponse") -> None:
    now = time.monotonic()
    _PENDING_RESPONSES[response.request_id] = (response, now)
    _PENDING_RESPONSES.move_to_end(response.request_id)
    _prune_pending_responses_locked(now)


def _worker_response_router_loop() -> None:
    while True:
        if _WORKER_RESPONSE_ROUTER_STOP.is_set():
            return
        q = _RESPONSE_QUEUE
        if q is None:
            time.sleep(0.01)
            continue
        try:
            response = q.get(timeout=0.1)
        except queue.Empty:
            continue
        except Exception:
            time.sleep(0.05)
            continue
        if response is None:
            continue
        try:
            response_id = int(getattr(response, "request_id", 0) or 0)
        except Exception:
            response_id = 0
        with _PENDING_RESPONSES_COND:
            _store_pending_response_locked(response)
            # If this response collides on request_id, prefer the latest (should not happen).
            if response_id in _PENDING_RESPONSES:
                _PENDING_RESPONSES.move_to_end(response_id)
            _PENDING_RESPONSES_COND.notify_all()


def _ensure_worker_response_router_started() -> None:
    global _WORKER_RESPONSE_ROUTER_THREAD
    t = _WORKER_RESPONSE_ROUTER_THREAD
    if t is not None and t.is_alive():
        return
    _WORKER_RESPONSE_ROUTER_STOP.clear()
    label = str(_WORKER_ID) if _WORKER_ID is not None else "?"
    t = threading.Thread(
        target=_worker_response_router_loop,
        name=f"GpuWorkerResponseRouter[{label}]",
        daemon=True,
    )
    _WORKER_RESPONSE_ROUTER_THREAD = t
    t.start()


def _wait_for_worker_response(request_id: int, timeout: float) -> "GpuResponse":
    deadline = time.monotonic() + float(timeout)
    with _PENDING_RESPONSES_COND:
        while True:
            _prune_pending_responses_locked()
            if request_id in _PENDING_RESPONSES:
                response, _ts = _PENDING_RESPONSES.pop(request_id)
                return response
            remaining = float(deadline - time.monotonic())
            if remaining <= 0:
                raise RuntimeError(f"GPU executor timeout after {timeout}s")
            _PENDING_RESPONSES_COND.wait(timeout=remaining)


def _registry_base_fixed_stats_sig(arr: Any) -> tuple[Any, ...]:
    """
    Build a compact content signature for small base-fixed arrays.

    This keeps handle reuse robust even when callers rebuild small numpy arrays
    with identical values between requests.
    """
    try:
        import numpy as np

        a = np.asarray(arr, dtype=np.int32)
        if a.ndim == 0:
            return ("scalar", int(a))
        h = hashlib.blake2b(digest_size=8)
        h.update(memoryview(np.ascontiguousarray(a)).cast("B"))
        return ("arr", tuple(int(x) for x in a.shape), str(a.dtype), h.digest())
    except Exception:
        return ("obj", id(arr))


def _fg_selection_array_sig(
    arr: Any,
    *,
    n_active: int,
    sig_cache: dict[tuple[Any, ...], tuple[Any, ...]] | None = None,
) -> tuple[Any, ...]:
    """
    Stable signature for FG top-K selection inputs (base_scores / keep_mask).

    We hash only the active prefix `[0:n_active)` because FG top-K kernels only
    consume the first `n_genomes` rows.
    """
    try:
        import numpy as np

        a = np.asarray(arr, dtype=np.int32)
    except Exception:
        return ("obj", id(arr))

    if a.ndim == 0:
        try:
            return ("scalar", int(a))
        except Exception:
            return ("scalar", repr(a))

    if a.ndim != 1:
        try:
            a = np.ravel(a)
        except Exception:
            return ("obj", id(arr))

    try:
        n_total = int(a.shape[0])
    except Exception:
        return ("obj", id(arr))

    n = max(0, min(int(n_active), int(n_total)))
    if n <= 0:
        return ("empty", int(n_total))

    view = a[:n]
    try:
        ptr = int(view.__array_interface__["data"][0])
    except Exception:
        ptr = int(id(view))
    try:
        strides = tuple(int(x) for x in (view.strides or ()))
    except Exception:
        strides = ()
    cache_key = (int(id(a)), int(ptr), int(n), strides, str(view.dtype))

    if sig_cache is not None:
        cached = sig_cache.get(cache_key)
        if cached is not None:
            return cached

    if not view.flags["C_CONTIGUOUS"]:
        view = np.ascontiguousarray(view, dtype=np.int32)

    h = hashlib.blake2b(digest_size=12)
    h.update(memoryview(view).cast("B"))
    sig = ("arr", int(n), h.digest())

    if sig_cache is not None:
        sig_cache[cache_key] = sig
    return sig


def _fg_selection_upload_key(
    payload: dict[str, Any],
    *,
    n_active: int,
    sig_cache: dict[tuple[Any, ...], tuple[Any, ...]] | None = None,
) -> tuple[Any, ...]:
    """
    Content key for deciding whether top-K selection inputs must be re-uploaded.

    Using content signatures (instead of object identity only) allows reuse even
    when callers rebuild equivalent numpy arrays across adjacent payloads.
    """
    topk = int(payload.get("fg_download_topk", 0) or 0)
    base_scores = payload.get("fg_download_base_scores")
    keep_mask = payload.get("fg_download_keep_mask")
    keep_sig = (
        ("none", int(n_active))
        if keep_mask is None
        else _fg_selection_array_sig(keep_mask, n_active=int(n_active), sig_cache=sig_cache)
    )
    return (
        int(n_active),
        int(topk),
        _fg_selection_array_sig(base_scores, n_active=int(n_active), sig_cache=sig_cache),
        keep_sig,
    )


def _registry_static_handle_entry(
    *,
    item_stats: Any,
    slot_start: Any,
    slot_count: Any,
    base_fixed_stats: Any,
    timeline_grid: Any,
    ref_arrays: Any,
) -> dict[str, Any]:
    """
    Get or create a worker-local handle entry for registry static payload parts.

    The entry retains strong references for identity-based keys to prevent ID reuse
    collisions while the handle is alive.
    """
    global _REGISTRY_STATIC_HANDLE_COUNTER

    def _minimize_calc_song_for_gpu_timeline_grid(calc_song: Any) -> Any:
        """
        Reduce IPC payload size for `timeline_grid` when it is actually a `calc_song` dict.

        `taichi_gem.api.timeline.precompute_timeline_gpu` only needs:
          - calc_song["song_data"]["timestamps"]
          - calc_song["metadata"]["Long Notes"]
          - calc_song["metadata"]["Last Note Time"]
          - HumanHitSim cache-affecting metadata keys (for stable per-slot caching)
        """
        if not isinstance(calc_song, dict):
            return calc_song

        meta = calc_song.get("metadata", {}) or {}
        song_data = calc_song.get("song_data", {}) or {}
        if not isinstance(meta, dict) or not isinstance(song_data, dict):
            return calc_song

        timestamps = song_data.get("timestamps")
        if timestamps is None:
            return calc_song

        ts_out = timestamps
        try:
            import numpy as np

            ts_out = np.asarray(timestamps, dtype=np.float32)
            if not ts_out.flags["C_CONTIGUOUS"]:
                ts_out = np.ascontiguousarray(ts_out)
        except Exception:
            ts_out = timestamps

        meta_out = {
            "Song Name": meta.get("Song Name", ""),
            "Long Notes": int(meta.get("Long Notes", 0) or 0),
            "Last Note Time": float(meta.get("Last Note Time", 0) or 0.0),
            "HumanHitSimApplied": bool(meta.get("HumanHitSimApplied")),
            "HumanHitSimApplyTo": meta.get("HumanHitSimApplyTo", ""),
            "HumanHitSimDistribution": meta.get("HumanHitSimDistribution", ""),
            "HumanHitSimGreatMode": meta.get("HumanHitSimGreatMode", ""),
            "HumanHitSimSeed": meta.get("HumanHitSimSeed", 0),
        }
        return {"metadata": meta_out, "song_data": {"timestamps": ts_out}}

    key = (
        int(id(item_stats)),
        int(id(slot_start)),
        int(id(slot_count)),
        _registry_base_fixed_stats_sig(base_fixed_stats),
        int(id(timeline_grid)),
        int(id(ref_arrays)),
    )
    cached = _REGISTRY_STATIC_HANDLE_CACHE.get(key)
    if cached is not None:
        _REGISTRY_STATIC_HANDLE_CACHE.move_to_end(key)
        return cached

    _REGISTRY_STATIC_HANDLE_COUNTER += 1
    timeline_grid_send = _minimize_calc_song_for_gpu_timeline_grid(timeline_grid)
    entry = {
        "handle": int(_REGISTRY_STATIC_HANDLE_COUNTER),
        "registered": False,
        "item_stats_ref": item_stats,
        "slot_start_ref": slot_start,
        "slot_count_ref": slot_count,
        "timeline_grid_ref": timeline_grid,
        "timeline_grid_send": timeline_grid_send,
        "ref_arrays_ref": ref_arrays,
    }
    _REGISTRY_STATIC_HANDLE_CACHE[key] = entry
    _REGISTRY_STATIC_HANDLE_CACHE.move_to_end(key)
    while len(_REGISTRY_STATIC_HANDLE_CACHE) > _REGISTRY_STATIC_HANDLE_CACHE_MAX:
        _REGISTRY_STATIC_HANDLE_CACHE.popitem(last=False)
    return entry


def set_gpu_worker_mode(worker_id: int, request_queue, response_queue):
    """Configure this process as a GPU worker (called after fork/spawn)."""
    global _WORKER_MODE, _WORKER_ID, _REQUEST_QUEUE, _RESPONSE_QUEUE
    global _PENDING_RESPONSES, _REGISTRY_STATIC_HANDLE_CACHE, _WORKER_RESPONSE_ROUTER_THREAD

    _WORKER_RESPONSE_ROUTER_STOP.set()
    t = _WORKER_RESPONSE_ROUTER_THREAD
    if t is not None:
        try:
            t.join(timeout=0.25)
        except Exception:
            pass
    _WORKER_RESPONSE_ROUTER_THREAD = None
    _WORKER_RESPONSE_ROUTER_STOP.clear()

    with _PENDING_RESPONSES_COND:
        _PENDING_RESPONSES = OrderedDict()
        _PENDING_RESPONSES_COND.notify_all()
    _WORKER_MODE = True
    _WORKER_ID = worker_id
    _REQUEST_QUEUE = request_queue
    _RESPONSE_QUEUE = response_queue
    _REGISTRY_STATIC_HANDLE_CACHE = OrderedDict()


def is_gpu_worker_mode() -> bool:
    """Check if running in worker mode (should use IPC for GPU)."""
    return _WORKER_MODE


def clear_gpu_worker_mode():
    """Clear worker mode (for testing or process reuse)."""
    global _WORKER_MODE, _WORKER_ID, _REQUEST_QUEUE, _RESPONSE_QUEUE, _PENDING_RESPONSES
    global _REGISTRY_STATIC_HANDLE_CACHE, _WORKER_RESPONSE_ROUTER_THREAD
    global _SOLVE_STATIC_HANDLE_CACHE
    _WORKER_RESPONSE_ROUTER_STOP.set()
    with _PENDING_RESPONSES_COND:
        _PENDING_RESPONSES_COND.notify_all()
    t = _WORKER_RESPONSE_ROUTER_THREAD
    if t is not None:
        try:
            t.join(timeout=0.25)
        except Exception:
            pass
    _WORKER_RESPONSE_ROUTER_THREAD = None
    _WORKER_MODE = False
    _WORKER_ID = None
    _REQUEST_QUEUE = None
    _RESPONSE_QUEUE = None
    with _PENDING_RESPONSES_COND:
        _PENDING_RESPONSES = OrderedDict()
    _REGISTRY_STATIC_HANDLE_CACHE = OrderedDict()


class GpuExecutor:
    """
    Single GPU owner process that handles all Taichi kernel execution.

    Song worker processes submit requests via IPC queue, which are executed
    serially on the GPU thread for maximum throughput.
    """

    _instance = None
    _lock = threading.Lock()
    _FG_REQUEST_TYPES = frozenset(
        {
            GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
            GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS,
            GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH,
            GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS,
            GpuRequestType.FG_RESET_GLOBAL_BEST,
            GpuRequestType.FG_DOWNLOAD_GLOBAL_BEST,
            GpuRequestType.FG_COMPUTE_BREAKPOINTS,
        }
    )
    _COALESCABLE_REQUEST_TYPES = frozenset(
        {
            GpuRequestType.GPU_NATIVE_GA_RUN,
            GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
            GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
            GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS,
            GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH,
            GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS,
        }
    )
    # These request types should never be batched in the executor loop. In practice, batching these can create
    # multi-second continuous GPU work that risks Windows UI freezes / TDR.
    _NO_BATCH_REQUEST_TYPES = frozenset(
        {
            GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS,
            GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH,
            GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS,
            GpuRequestType.GPU_NATIVE_GA_RUN,
        }
    )
    _NO_BATCH_REQUEST_TYPE_VALUES = frozenset({str(rt.value) for rt in _NO_BATCH_REQUEST_TYPES})

    @classmethod
    def _is_no_batch_request_type(cls, request_type: Any) -> bool:
        if request_type in cls._NO_BATCH_REQUEST_TYPES:
            return True
        try:
            value = str(getattr(request_type, "value", request_type))
        except Exception:
            value = ""
        return value in cls._NO_BATCH_REQUEST_TYPE_VALUES

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
            # Tests may monkeypatch singleton instance methods directly; clear those
            # overrides on re-access so they do not leak between test cases.
            for patched_name in (
                "_coalesce_fg_solve_with_breakpoints_batch_requests",
                "_execute_request",
                "_execute_fg_solve_with_breakpoints_batch",
            ):
                try:
                    self.__dict__.pop(patched_name, None)
                except Exception:
                    pass
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
        # Single-item defer buffer used by `_gather_batch()` to prevent batching "no-batch"
        # request types behind unrelated work (stability/TDR guard on Windows).
        self._deferred_request: Optional[GpuRequest] = None
        # Ref-array upload caching: avoid redundant `load_ref_arrays()` calls when inputs are identical.
        # This saves host work and can avoid implicit syncs inside Taichi APIs.
        self._last_ref_arrays_sig: bytes | None = None
        # Per-worker registry static-payload cache. Worker requests can send a compact
        # handle after first registration to avoid repeatedly pickling large immutable
        # arrays/dicts (item stats, timeline grid, ref arrays, base fixed stats).
        self._registry_payload_cache: OrderedDict[tuple[int, int], dict[str, Any]] = OrderedDict()
        self._registry_payload_cache_max = max(
            64, int(_ENV_GET("GPU_EXECUTOR_REGISTRY_PAYLOAD_CACHE_MAX", "1024") or "1024")
        )
        self._registry_coalesce_staging: Any | None = None

        # Stats
        self._requests_processed = 0
        from gear_optimizer.core.env_config import ENV

        self._profile_enabled = ENV.gpu_executor_profile
        self._wait_sec = 0.0
        self._exec_sec = 0.0
        self._req_type_counts = defaultdict(int)
        self._req_type_exec_sec = defaultdict(float)
        self._req_type_pack_sec = defaultdict(float)
        # Exec-wall decomposition:
        # - host: Python-side batching/coalescing/packing on GPU-owner thread
        # - gpu_*: in-process GPU profiler deltas (kernel/upload/download) measured during that exec window
        self._req_type_host_sec = defaultdict(float)
        self._req_type_gpu_kernel_sec = defaultdict(float)
        self._req_type_gpu_upload_sec = defaultdict(float)
        self._req_type_gpu_download_sec = defaultdict(float)
        self._exec_breakdown_enabled = bool(
            self._profile_enabled or ENV.gpu_profiler or env_flag("GPU_EXECUTOR_EXEC_BREAKDOWN", "0")
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
        self._profile_shutdown_ts: Optional[float] = None
        self._idle_transitions_sec = defaultdict(float)
        self._idle_transitions_count = defaultdict(int)
        self._last_work_req_type: Optional[GpuRequestType] = None
        self._fg_tasks_batches = 0
        self._fg_tasks_total = 0
        self._fg_tasks_max = 0
        self._fg_tasks_batch_hist = defaultdict(int)

        # Request latency profiling (submit -> dequeue -> exec_start -> exec_end).
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
        self._last_batch_plan_mode = "balanced"

        # Workload-level observability (profiling-only in this phase).
        self._workload_profile_enabled = bool(self._profile_enabled or env_flag("GPU_EXECUTOR_WORKLOAD_PROFILE", "0"))
        try:
            interval_raw = float(str(_ENV_GET("GPU_EXECUTOR_WORKLOAD_PROFILE_INTERVAL_SEC", "2.0") or "2.0").strip())
        except Exception:
            interval_raw = 2.0
        self._workload_profile_interval_sec = max(0.2, float(interval_raw))
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
        try:
            short_wait_spin_ms = float(str(_ENV_GET("GPU_EXECUTOR_SHORT_WAIT_SPIN_MS", "3.0") or "3.0").strip())
        except Exception:
            short_wait_spin_ms = 3.0
        self._short_wait_spin_sec = max(0.0, float(short_wait_spin_ms) / 1000.0)
        try:
            short_wait_spin_yields = int(str(_ENV_GET("GPU_EXECUTOR_SHORT_WAIT_SPIN_YIELD_ROUNDS", "8") or "8").strip())
        except Exception:
            short_wait_spin_yields = 8
        self._short_wait_spin_yield_rounds = max(0, min(int(short_wait_spin_yields), 100_000))

        # Dispatch table (reduces branching in the hot loop and centralizes request routing).
        self._dispatch = {
            GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY: self._handle_solve_genomes_from_registry,
            GpuRequestType.LOAD_REF_ARRAYS: self._execute_load_refs,
            GpuRequestType.PRECOMPUTE_TIMELINE: self._execute_precompute_timeline,
            GpuRequestType.SOLVE_FORCE_GREATS_FINDER: self._execute_solve_force_greats_finder,
            GpuRequestType.GPU_NATIVE_GA_RUN: self._execute_gpu_native_ga_run,
            GpuRequestType.GA_STAGE_FG_GENOME_BASE_STATS: self._execute_ga_stage_fg_genome_base_stats,
            GpuRequestType.FG_RESET_GLOBAL_BEST: self._execute_fg_reset_global_best,
            GpuRequestType.FG_DOWNLOAD_GLOBAL_BEST: self._execute_fg_download_global_best,
            GpuRequestType.FG_SELECT_SIGNATURE_FRONTIER_BATCH: self._execute_fg_select_signature_frontier_batch,
            GpuRequestType.FG_COMPUTE_BREAKPOINTS: self._execute_fg_compute_breakpoints,
            GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS: self._execute_fg_solve_with_breakpoints,
            GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH: self._execute_fg_solve_with_breakpoints_batch,
            GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS: self._execute_ga_fg_fused_solve_with_breakpoints,
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

    def _gpu_prof_snapshot(self) -> tuple[float, float, float]:
        """
        Best-effort snapshot of cumulative in-process GPU profiler totals.

        Returns:
            (kernel_sec, upload_sec, download_sec)
        """
        if not self._exec_breakdown_enabled:
            return (0.0, 0.0, 0.0)
        try:
            from gear_optimizer.solver.gpu_profiler import get_gpu_profiler

            prof = get_gpu_profiler()
            summary = prof.summary()
            return (
                float(summary.get("total_kernel_sec", 0.0) or 0.0),
                float(summary.get("total_upload_sec", 0.0) or 0.0),
                float(summary.get("total_download_sec", 0.0) or 0.0),
            )
        except Exception:
            return (0.0, 0.0, 0.0)

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
        try:
            wall = max(0.0, float(exec_wall_sec))
        except Exception:
            return
        if wall <= 0.0:
            return

        kernel = 0.0
        upload = 0.0
        download = 0.0
        if prof_before is not None:
            try:
                prof_after = self._gpu_prof_snapshot()
                kernel = max(0.0, float(prof_after[0]) - float(prof_before[0]))
                upload = max(0.0, float(prof_after[1]) - float(prof_before[1]))
                download = max(0.0, float(prof_after[2]) - float(prof_before[2]))
            except Exception:
                kernel = 0.0
                upload = 0.0
                download = 0.0

        gpu_total = max(0.0, kernel + upload + download)
        host = max(0.0, wall - gpu_total)

        try:
            self._req_type_host_sec[request_type] += float(host)
            self._req_type_gpu_kernel_sec[request_type] += float(kernel)
            self._req_type_gpu_upload_sec[request_type] += float(upload)
            self._req_type_gpu_download_sec[request_type] += float(download)
        except Exception:
            return

    def _record_latency(
        self,
        request: "GpuRequest",
        *,
        exec_start_ns: int,
        exec_end_ns: int,
    ) -> None:
        if not self._profile_enabled:
            return
        try:
            req_type = request.request_type
        except Exception:
            return
        try:
            submit_ns = int(getattr(request, "submit_perf_ns", 0) or 0)
            dequeue_ns = int(getattr(request, "dequeue_perf_ns", 0) or 0)
            exec_start_ns = int(exec_start_ns or 0)
            exec_end_ns = int(exec_end_ns or 0)
        except Exception:
            return
        if submit_ns <= 0 or exec_end_ns <= 0:
            return
        if dequeue_ns <= 0:
            dequeue_ns = exec_start_ns
        if exec_start_ns < dequeue_ns:
            exec_start_ns = dequeue_ns
        if exec_end_ns < exec_start_ns:
            exec_end_ns = exec_start_ns

        queue_sec = max(0.0, float(dequeue_ns - submit_ns) / 1e9)
        in_exec_sec = max(0.0, float(exec_start_ns - dequeue_ns) / 1e9)
        total_sec = max(0.0, float(exec_end_ns - submit_ns) / 1e9)

        try:
            self._lat_counts[req_type] += 1
            n = int(self._lat_counts[req_type])
            self._lat_total_sec[req_type] += float(total_sec)
            if total_sec > float(self._lat_max_sec[req_type]):
                self._lat_max_sec[req_type] = float(total_sec)
            self._lat_queue_total_sec[req_type] += float(queue_sec)
            if queue_sec > float(self._lat_queue_max_sec[req_type]):
                self._lat_queue_max_sec[req_type] = float(queue_sec)
            self._lat_in_exec_total_sec[req_type] += float(in_exec_sec)
            if in_exec_sec > float(self._lat_in_exec_max_sec[req_type]):
                self._lat_in_exec_max_sec[req_type] = float(in_exec_sec)
        except Exception:
            return

        try:
            cap = int(self._lat_sample_cap)
        except Exception:
            cap = 0
        if cap <= 0:
            return

        try:
            total_samples = self._lat_samples[req_type]
            queue_samples = self._lat_queue_samples[req_type]
            in_exec_samples = self._lat_in_exec_samples[req_type]
            if len(total_samples) < cap:
                total_samples.append(float(total_sec))
                queue_samples.append(float(queue_sec))
                in_exec_samples.append(float(in_exec_sec))
            else:
                if n > 0:
                    j = random.randint(0, n - 1)
                    if j < cap:
                        total_samples[j] = float(total_sec)
                        queue_samples[j] = float(queue_sec)
                        in_exec_samples[j] = float(in_exec_sec)
        except Exception:
            return

    @staticmethod
    def _size_hint(value: Any) -> int:
        if value is None:
            return 0
        try:
            shape = getattr(value, "shape", None)
            if shape is not None and len(shape) > 0:
                return max(0, int(shape[0]))
        except Exception:
            pass
        try:
            return max(0, int(len(value)))
        except Exception:
            return 0

    def _safe_qsize(self) -> int:
        q = self._request_queue
        if q is None:
            return -1
        try:
            size = q.qsize()
        except (NotImplementedError, AttributeError):
            return -1
        except Exception:
            return -1
        try:
            return max(0, int(size))
        except Exception:
            return -1

    def _estimate_request_work_units(self, request: "GpuRequest") -> float:
        req_type = getattr(request, "request_type", None)
        payload = self._payload_dict(request)

        if req_type == GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY:
            n = self._size_hint(payload.get("population_indices"))
            return float(max(1, n))

        if req_type == GpuRequestType.GPU_NATIVE_GA_RUN:
            n_genomes = int(payload.get("n_genomes", 0) or 0)
            if n_genomes <= 0:
                n_genomes = self._size_hint(payload.get("initial_populations"))
            n_generations = max(1, int(payload.get("n_generations", 1) or 1))
            runs = max(1, int(payload.get("num_runs", 1) or 1))
            return float(max(1, n_genomes) * n_generations * runs)

        if req_type == GpuRequestType.SOLVE_FORCE_GREATS_FINDER:
            kwargs = payload.get("kwargs")
            if not isinstance(kwargs, dict):
                return 1.0
            fg_tasks = kwargs.get("fg_tasks")
            if isinstance(fg_tasks, (list, tuple)) and fg_tasks:
                pair_total = 0
                for task in fg_tasks:
                    if isinstance(task, dict):
                        pair_total += max(1, self._size_hint(task.get("ftff_pairs")))
                n_genomes = int(kwargs.get("n_genomes_override", 0) or 0)
                if n_genomes <= 0:
                    args = payload.get("args")
                    if isinstance(args, (list, tuple)) and args:
                        n_genomes = self._size_hint(args[0])
                n_genomes = max(1, n_genomes)
                return float(max(1, pair_total) * n_genomes)
            ftff_chunks = kwargs.get("ftff_chunks")
            if isinstance(ftff_chunks, (list, tuple)) and ftff_chunks:
                return float(max(1, len(ftff_chunks)))
            return 1.0

        if req_type == GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH:
            payloads = payload.get("payloads")
            if not isinstance(payloads, (list, tuple)):
                return 1.0
            pair_total = 0
            for item in payloads:
                if isinstance(item, dict):
                    pair_total += max(1, self._size_hint(item.get("ftff_pairs")))
                else:
                    pair_total += 1
            return float(max(1, pair_total))

        if req_type in (GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS, GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS):
            return float(max(1, self._size_hint(payload.get("ftff_pairs"))))

        if req_type in (GpuRequestType.LOAD_REF_ARRAYS, GpuRequestType.PRECOMPUTE_TIMELINE):
            return 0.25

        if req_type == GpuRequestType.SHUTDOWN:
            return 0.0

        return 1.0

    def _summarize_batch(self, batch: list["GpuRequest"], *, plan: _BatchPlan, wait_sec: float) -> dict[str, Any]:
        non_shutdown = [req for req in (batch or []) if req.request_type != GpuRequestType.SHUTDOWN]
        by_type = defaultdict(int)
        coalescable_count = 0
        fg_count = 0
        units_total = 0.0
        age_ms: list[float] = []

        for req in non_shutdown:
            rt = req.request_type
            by_type[rt] += 1
            if rt in self._COALESCABLE_REQUEST_TYPES:
                coalescable_count += 1
            if rt in self._FG_REQUEST_TYPES:
                fg_count += 1
            units_total += float(self._estimate_request_work_units(req))

            try:
                submit_ns = int(getattr(req, "submit_perf_ns", 0) or 0)
                dequeue_ns = int(getattr(req, "dequeue_perf_ns", 0) or 0)
                if submit_ns > 0 and dequeue_ns > submit_ns:
                    age_ms.append(max(0.0, float(dequeue_ns - submit_ns) / 1e6))
            except Exception:
                continue

        total = int(len(non_shutdown))
        distinct = int(len(by_type))
        dominant_type = ""
        dominant_count = 0
        if by_type:
            dominant_rt, dominant_count = max(by_type.items(), key=lambda kv: kv[1])
            dominant_type = str(dominant_rt.value)

        dominant_share_pct = (float(dominant_count) / float(total) * 100.0) if total > 0 else 0.0
        diversity_pct = 0.0
        if total > 0 and distinct > 1:
            entropy = 0.0
            for count in by_type.values():
                p = float(count) / float(total)
                if p > 0.0:
                    entropy -= p * math.log(p, 2)
            max_entropy = math.log(float(distinct), 2)
            if max_entropy > 0.0:
                diversity_pct = float(entropy / max_entropy * 100.0)

        oldest_age_ms = float(max(age_ms)) if age_ms else 0.0
        avg_age_ms = (float(sum(age_ms)) / float(len(age_ms))) if age_ms else 0.0

        type_compact = ";".join(f"{rt.value}:{int(n)}" for rt, n in sorted(by_type.items(), key=lambda kv: kv[0].value))
        return {
            "batch_id": int(self._workload_batch_seq),
            "mode": str(plan.mode),
            "wait_ms": float(max(0.0, float(wait_sec) * 1000.0)),
            "batch_wait_ms_target": int(plan.wait_ms),
            "batch_max_target": int(plan.max_batch),
            "queue_depth_hint": int(plan.queue_depth_hint),
            "pressure_hint": float(plan.pressure_hint),
            "size": int(total),
            "distinct_types": int(distinct),
            "coalescable_count": int(coalescable_count),
            "fg_count": int(fg_count),
            "dominant_type": str(dominant_type),
            "dominant_share_pct": float(dominant_share_pct),
            "diversity_pct": float(diversity_pct),
            "work_units": float(max(0.0, units_total)),
            "avg_work_units_per_req": (float(units_total) / float(total)) if total > 0 else 0.0,
            "oldest_submit_age_ms": float(oldest_age_ms),
            "avg_submit_age_ms": float(avg_age_ms),
            "types": str(type_compact),
        }

    def _record_workload_batch(self, metrics: dict[str, Any]) -> None:
        if not metrics:
            return
        self._workload_recent_batches.append(dict(metrics))
        self._workload_mode_counts[str(metrics.get("mode") or "unknown")] += 1
        self._workload_mode_wait_sec[str(metrics.get("mode") or "unknown")] += (
            float(metrics.get("wait_ms", 0.0) or 0.0) / 1000.0
        )
        self._workload_mode_exec_sec[str(metrics.get("mode") or "unknown")] += float(
            metrics.get("exec_sec", 0.0) or 0.0
        )
        self._workload_queue_depth_samples.append(float(metrics.get("queue_depth_hint", 0.0) or 0.0))
        self._workload_age_ms_samples.append(float(metrics.get("avg_submit_age_ms", 0.0) or 0.0))
        self._workload_units_samples.append(float(metrics.get("work_units", 0.0) or 0.0))
        self._workload_diversity_samples.append(float(metrics.get("diversity_pct", 0.0) or 0.0))
        self._workload_pressure_samples.append(float(metrics.get("pressure_hint", 0.0) or 0.0))
        self._last_batch_plan_mode = str(metrics.get("mode") or self._last_batch_plan_mode)

        if self._workload_profile_enabled:
            batch_id = int(metrics.get("batch_id", 0) or 0)
            pressure = float(metrics.get("pressure_hint", 0.0) or 0.0)
            mode = str(metrics.get("mode") or "")
            should_emit = (
                batch_id <= 12
                or (batch_id % 64 == 0)
                or pressure >= 1.0
                or mode
                in {
                    "fg_recovery",
                    "throughput",
                }
            )
            if should_emit:
                emit_profile_event(
                    component="gpu_executor",
                    event="workload::batch",
                    metrics={
                        "batch_id": int(batch_id),
                        "mode": str(mode),
                        "size": int(metrics.get("size", 0) or 0),
                        "types": str(metrics.get("types", "")),
                        "dominant_type": str(metrics.get("dominant_type", "")),
                        "dominant_share_pct": float(metrics.get("dominant_share_pct", 0.0) or 0.0),
                        "diversity_pct": float(metrics.get("diversity_pct", 0.0) or 0.0),
                        "work_units": float(metrics.get("work_units", 0.0) or 0.0),
                        "queue_depth_hint": int(metrics.get("queue_depth_hint", -1) or -1),
                        "avg_submit_age_ms": float(metrics.get("avg_submit_age_ms", 0.0) or 0.0),
                        "wait_ms": float(metrics.get("wait_ms", 0.0) or 0.0),
                        "exec_ms": float(metrics.get("exec_sec", 0.0) or 0.0) * 1000.0,
                    },
                )
                self._workload_events_emitted += 1
            self._maybe_emit_workload_profile()

    @staticmethod
    def _p95(values: list[float] | deque[float]) -> float:
        if not values:
            return 0.0
        data = sorted(float(v) for v in values)
        idx = int(round(0.95 * (len(data) - 1)))
        idx = max(0, min(idx, len(data) - 1))
        return float(data[idx])

    def _maybe_emit_workload_profile(self, *, force: bool = False) -> None:
        if not self._workload_profile_enabled:
            return
        now = perf_counter()
        if not force:
            if self._workload_profile_last_emit_ts is None:
                self._workload_profile_last_emit_ts = now
                return
            if (now - float(self._workload_profile_last_emit_ts)) < float(self._workload_profile_interval_sec):
                return

        window = list(self._workload_recent_batches)
        if not window:
            self._workload_profile_last_emit_ts = now
            return

        n = float(len(window))
        total_wait = float(sum(float(item.get("wait_ms", 0.0) or 0.0) for item in window))
        total_exec_ms = float(sum(float(item.get("exec_sec", 0.0) or 0.0) for item in window) * 1000.0)
        total = total_wait + total_exec_ms
        busy_pct = (total_exec_ms / total * 100.0) if total > 0 else 0.0
        avg_batch = float(sum(float(item.get("size", 0.0) or 0.0) for item in window) / n)
        avg_units = float(sum(float(item.get("work_units", 0.0) or 0.0) for item in window) / n)
        avg_diversity = float(sum(float(item.get("diversity_pct", 0.0) or 0.0) for item in window) / n)
        avg_qdepth = float(sum(float(item.get("queue_depth_hint", 0.0) or 0.0) for item in window) / n)
        fg_share = float(
            sum(float(item.get("fg_count", 0.0) or 0.0) for item in window)
            / max(1.0, sum(float(item.get("size", 0.0) or 0.0) for item in window))
            * 100.0
        )
        mode_counts = defaultdict(int)
        for item in window:
            mode_counts[str(item.get("mode") or "unknown")] += 1
        top_modes = sorted(mode_counts.items(), key=lambda kv: kv[1], reverse=True)[:3]
        mode_str = ",".join(f"{k}:{int(v)}" for k, v in top_modes)

        emit_profile_event(
            component="gpu_executor",
            event="workload::window",
            metrics={
                "batches": int(len(window)),
                "busy_pct": float(busy_pct),
                "avg_batch": float(avg_batch),
                "avg_work_units": float(avg_units),
                "avg_diversity_pct": float(avg_diversity),
                "avg_queue_depth_hint": float(avg_qdepth),
                "fg_share_pct": float(fg_share),
                "mode_top": str(mode_str),
            },
        )
        self._workload_events_emitted += 1
        self._workload_profile_last_emit_ts = now

        if self._profile_enabled:
            logger.debug(
                "[GpuExecutor][WORKLOAD] "
                f"window_batches={len(window)} busy={busy_pct:.1f}% avg_batch={avg_batch:.2f} "
                f"avg_units={avg_units:.1f} fg_share={fg_share:.1f}% qdepth~={avg_qdepth:.1f} "
                f"diversity={avg_diversity:.1f}% modes=[{mode_str}]"
            )

    def _handle_solve_genomes_from_registry(self, request: GpuRequest) -> GpuResponse:
        payload = request.payload or {}
        try:
            song_slot = int(payload.get("song_slot", 0) or 0)
        except Exception:
            song_slot = 0
        return self._execute_solve_genomes_from_registry(request, song_slot=song_slot)

    @staticmethod
    def _default_song_slot_for_worker(worker_id: int) -> int:
        """Map a worker id to a stable non-zero song slot for timeline reuse."""
        try:
            from .taichi_gem import fields as gem_fields

            max_slots = int(getattr(gem_fields, "MAX_SONG_SLOTS", 1) or 1)
        except Exception:
            try:
                max_slots = int(os.environ.get("GPU_SONG_SLOTS", "24") or "24")
            except Exception:
                max_slots = 24
        max_slots = max(1, int(max_slots))
        if max_slots <= 1:
            return 0
        return 1 + (abs(int(worker_id)) % max(1, int(max_slots) - 1))

    def _execute_request(self, request: GpuRequest) -> GpuResponse:
        """Dispatch a single request to the appropriate executor handler."""
        req_type = getattr(request, "request_type", None)
        if req_type == GpuRequestType.SHUTDOWN:
            return GpuResponse(request_id=int(getattr(request, "request_id", 0) or 0), success=True, result=None)
        handler = self._dispatch.get(req_type)
        if handler is None:
            return GpuResponse(
                request_id=int(getattr(request, "request_id", 0) or 0),
                success=False,
                error=f"Unsupported GPU request type: {req_type!r}",
            )
        try:
            return handler(request)
        except Exception as exc:
            return GpuResponse(
                request_id=int(getattr(request, "request_id", 0) or 0),
                success=False,
                error=f"GpuExecutor error: {type(exc).__name__}: {exc}",
            )

    def start(self, *, in_process: bool = False):
        """Start the GPU executor thread in the main process."""
        if self._running:
            # Cross-process (multiprocessing.Queue) mode can service in-process callers,
            # but the reverse is not true. If we started in-process and later need
            # IPC queues (parallel worker mode), restart with `in_process=False`.
            if (not bool(in_process)) and bool(getattr(self, "_in_process_queues", False)):
                try:
                    self.stop()
                except Exception:
                    return
            else:
                return

        # Reset per-run state (GpuExecutor is a singleton and may be started/stopped
        # multiple times within one Python process during profiling/benchmarks).
        self._requests_processed = 0
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
        except Exception:
            pass
        self._response_queues = {}
        self._next_worker_id = 0
        self._taichi_ready = False
        self._last_init_error = None
        self._deferred_request = None
        self._ready_event.clear()
        self._last_ref_arrays_sig = None
        # Scratch buffer for registry request coalescing (avoid per-chunk np.empty allocations).
        self._registry_coalesce_staging: Any | None = None
        self._registry_payload_cache.clear()

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
                    self._trace_fp.write(
                        "wall_ts,rel_ts,event,wait_sec,exec_sec,batch_size,types,in_process,"
                        "planner_mode,queue_depth_hint,pressure_hint,work_units,dominant_type,"
                        "dominant_share_pct,diversity_pct,avg_submit_age_ms\n"
                    )
            except Exception:
                self._trace_fp = None

        self._in_process_queues = bool(in_process)
        self._high_res_timer_enabled = False
        heartbeat_raw = str(os.environ.get("GPU_EXECUTOR_HEARTBEAT_PATH", "") or "").strip()
        self._heartbeat_path = Path(heartbeat_raw) if heartbeat_raw else _default_executor_heartbeat_path()
        try:
            self._heartbeat_interval_sec = max(
                0.1,
                float(os.environ.get("GPU_EXECUTOR_HEARTBEAT_INTERVAL_SEC", "2.0") or "2.0"),
            )
        except Exception:
            self._heartbeat_interval_sec = 2.0
        self._heartbeat_last_write_monotonic = 0.0
        self._heartbeat_last_phase = ""
        if self._in_process_queues and os.name == "nt" and _system_timer_override_allowed():
            # The executor's gather loop uses small timeout waits (<=6ms by default in inproc mode).
            # On Windows, keep 1ms timer resolution so these waits aren't quantized to ~15ms.
            try:
                raw_wait = os.environ.get("GPU_EXECUTOR_BATCH_WAIT_MS")
                if raw_wait is None or str(raw_wait).strip() == "":
                    base_wait_ms = int(getattr(ENV, "gpu_executor_batch_wait_ms", 10) or 10)
                    batch_wait_ms = min(int(base_wait_ms), 6)
                else:
                    batch_wait_ms = int(str(raw_wait).strip())
            except Exception:
                batch_wait_ms = 6
            try:
                after_first_ms = int(os.environ.get("GPU_EXECUTOR_INPROC_COALESCE_AFTER_FIRST_MS", "2") or "2")
            except Exception:
                after_first_ms = 2
            if (0 < int(batch_wait_ms) <= 4) or (0 < int(after_first_ms) <= 4):
                self._high_res_timer_enabled = bool(_acquire_windows_timer_period_1ms())
        self._request_queue = queue.Queue() if self._in_process_queues else multiprocessing.Queue()
        self._running = True

        # Run in thread (not process) so we stay in main process
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
        if self._high_res_timer_enabled:
            _release_windows_timer_period_1ms()
            self._high_res_timer_enabled = False
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
            logger.debug(
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
                fg_exec = float(self._req_type_exec_sec.get(GpuRequestType.SOLVE_FORCE_GREATS_FINDER, 0.0) or 0.0)
                if fg_exec > 0 and self._fg_tasks_total > 0:
                    fg_tasks_per_s = float(self._fg_tasks_total) / fg_exec
                    logger.debug(
                        "[GpuExecutor][FG] tasks_per_sec~=%.1f (executor-wall) fg_exec=%.2fs",
                        fg_tasks_per_s,
                        fg_exec,
                    )
            except Exception:
                pass
            try:
                if self._lat_counts:
                    items = []

                    def _p95(d: dict, k: Any) -> float:
                        try:
                            samples = list(d.get(k) or [])
                        except Exception:
                            samples = []
                        if not samples:
                            return 0.0
                        samples_sorted = sorted(samples)
                        idx = int(round(0.95 * (len(samples_sorted) - 1)))
                        idx = max(0, min(idx, len(samples_sorted) - 1))
                        return float(samples_sorted[idx])

                    for req_type, count in self._lat_counts.items():
                        n = int(count or 0)
                        if n <= 0:
                            continue
                        total_avg = float(self._lat_total_sec.get(req_type, 0.0) or 0.0) / n
                        queue_avg = float(self._lat_queue_total_sec.get(req_type, 0.0) or 0.0) / n
                        in_exec_avg = float(self._lat_in_exec_total_sec.get(req_type, 0.0) or 0.0) / n

                        total_p95 = _p95(self._lat_samples, req_type)
                        queue_p95 = _p95(self._lat_queue_samples, req_type)
                        in_exec_p95 = _p95(self._lat_in_exec_samples, req_type)
                        items.append(
                            (total_avg, req_type, n, total_p95, queue_p95, in_exec_p95, queue_avg, in_exec_avg)
                        )
                    items.sort(key=lambda t: t[0], reverse=True)
                    items = items[:6]
                    if items:
                        parts = []
                        for total_avg, req_type, n, total_p95, queue_p95, in_exec_p95, queue_avg, in_exec_avg in items:
                            parts.append(
                                f"{req_type.value}:n={n} "
                                f"total_avg={total_avg * 1000:.1f}ms p95={total_p95 * 1000:.1f}ms "
                                f"queue_avg={queue_avg * 1000:.1f}ms p95={queue_p95 * 1000:.1f}ms "
                                f"in_exec_avg={in_exec_avg * 1000:.1f}ms p95={in_exec_p95 * 1000:.1f}ms"
                            )
                        logger.debug("[GpuExecutor][LATENCY] %s", "; ".join(parts))
            except Exception:
                pass
            try:
                if self._req_type_exec_sec:
                    breakdown_parts = []
                    top_exec = sorted(self._req_type_exec_sec.items(), key=lambda kv: kv[1], reverse=True)[:6]
                    for req_type, total_exec in top_exec:
                        host_s = float(self._req_type_host_sec.get(req_type, 0.0) or 0.0)
                        kernel_s = float(self._req_type_gpu_kernel_sec.get(req_type, 0.0) or 0.0)
                        upload_s = float(self._req_type_gpu_upload_sec.get(req_type, 0.0) or 0.0)
                        download_s = float(self._req_type_gpu_download_sec.get(req_type, 0.0) or 0.0)
                        breakdown_parts.append(
                            f"{req_type.value}:exec={float(total_exec):.2f}s host~={host_s:.2f}s "
                            f"gpu_kernel~={kernel_s:.2f}s up~={upload_s:.2f}s down~={download_s:.2f}s"
                        )
                    if breakdown_parts:
                        logger.debug("[GpuExecutor][BREAKDOWN] %s", "; ".join(breakdown_parts))
            except Exception:
                pass
            try:
                top_transitions = sorted(self._idle_transitions_sec.items(), key=lambda kv: kv[1], reverse=True)[:6]
                if top_transitions:
                    parts = []
                    for (prev_t, next_t), sec in top_transitions:
                        prev_s = prev_t.value if prev_t is not None else "<start>"
                        next_s = next_t.value if next_t is not None else "<none>"
                        cnt = int(self._idle_transitions_count.get((prev_t, next_t), 0))
                        parts.append(f"{prev_s}->{next_s}:{sec:.2f}s({cnt})")
                    logger.debug("[GpuExecutor][IDLE] transitions=[%s]", ", ".join(parts))
            except Exception:
                pass
            try:
                self._maybe_emit_workload_profile(force=True)
            except Exception:
                pass
            try:
                if self._workload_recent_batches:
                    window = list(self._workload_recent_batches)
                    n = float(len(window))
                    avg_units = float(sum(float(b.get("work_units", 0.0) or 0.0) for b in window) / n)
                    avg_div = float(sum(float(b.get("diversity_pct", 0.0) or 0.0) for b in window) / n)
                    avg_q = float(sum(float(b.get("queue_depth_hint", 0.0) or 0.0) for b in window) / n)
                    avg_age_ms = float(sum(float(b.get("avg_submit_age_ms", 0.0) or 0.0) for b in window) / n)
                    p95_age_ms = self._p95(self._workload_age_ms_samples)
                    p95_units = self._p95(self._workload_units_samples)
                    p95_div = self._p95(self._workload_diversity_samples)
                    p95_q = self._p95(self._workload_queue_depth_samples)
                    mode_top = sorted(self._workload_mode_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
                    mode_str = ", ".join(f"{name}:{int(count)}" for name, count in mode_top)
                    logger.debug(
                        "[GpuExecutor][WORKLOAD][SUMMARY] "
                        f"batches={len(window)} avg_units={avg_units:.1f} p95_units={p95_units:.1f} "
                        f"avg_diversity={avg_div:.1f}% p95_diversity={p95_div:.1f}% "
                        f"avg_qdepth={avg_q:.1f} p95_qdepth={p95_q:.1f} "
                        f"avg_submit_age={avg_age_ms:.2f}ms p95_submit_age={p95_age_ms:.2f}ms "
                        f"events={self._workload_events_emitted} modes=[{mode_str}]"
                    )
                    emit_profile_event(
                        component="gpu_executor",
                        event="workload::summary",
                        metrics={
                            "batches": int(len(window)),
                            "avg_work_units": float(avg_units),
                            "p95_work_units": float(p95_units),
                            "avg_diversity_pct": float(avg_div),
                            "p95_diversity_pct": float(p95_div),
                            "avg_queue_depth_hint": float(avg_q),
                            "p95_queue_depth_hint": float(p95_q),
                            "avg_submit_age_ms": float(avg_age_ms),
                            "p95_submit_age_ms": float(p95_age_ms),
                            "events_emitted": int(self._workload_events_emitted),
                            "last_mode": str(self._last_batch_plan_mode),
                        },
                    )
            except Exception:
                pass

        if self._workload_profile_enabled and (not self._profile_enabled):
            try:
                self._maybe_emit_workload_profile(force=True)
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
        logger.debug("[GpuExecutor] Stopped. Processed %s requests.", self._requests_processed)

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
        planner_mode: str = "",
        queue_depth_hint: int = -1,
        pressure_hint: float = 0.0,
        work_units: float = 0.0,
        dominant_type: str = "",
        dominant_share_pct: float = 0.0,
        diversity_pct: float = 0.0,
        avg_submit_age_ms: float = 0.0,
    ) -> None:
        if self._trace_start_perf is None:
            self._trace_start_perf = perf_counter()
        if self._trace_start_wall is None:
            self._trace_start_wall = time.time()
        rel_ts = perf_counter() - float(self._trace_start_perf)
        wall_ts = time.time()
        fp = self._trace_fp
        try:
            if fp is not None:
                fp.write(
                    f"{wall_ts:.6f},{rel_ts:.6f},{event},{float(wait_sec):.6f},{float(exec_sec):.6f},{int(batch_size)},"
                    f"{types},{int(bool(self._in_process_queues))},{str(planner_mode)},{int(queue_depth_hint)},"
                    f"{float(pressure_hint):.3f},{float(work_units):.3f},{str(dominant_type)},"
                    f"{float(dominant_share_pct):.2f},{float(diversity_pct):.2f},{float(avg_submit_age_ms):.3f}\n"
                )
        except Exception:
            pass
        emit_profile_event(
            component="gpu_executor",
            event=f"trace::{str(event or '').strip().lower()}",
            metrics={
                "rel_ts": float(rel_ts),
                "wait_sec": float(wait_sec),
                "exec_sec": float(exec_sec),
                "batch_size": int(batch_size),
                "types": str(types or ""),
                "in_process": int(bool(self._in_process_queues)),
                "planner_mode": str(planner_mode or ""),
                "queue_depth_hint": int(queue_depth_hint),
                "pressure_hint": float(pressure_hint),
                "work_units": float(work_units),
                "dominant_type": str(dominant_type or ""),
                "dominant_share_pct": float(dominant_share_pct),
                "diversity_pct": float(diversity_pct),
                "avg_submit_age_ms": float(avg_submit_age_ms),
            },
            ts_wall=float(wall_ts),
        )

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
        logger.debug(
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

    def _write_heartbeat(
        self,
        *,
        phase: str,
        batch: list[GpuRequest] | None = None,
        note: str = "",
        force: bool = False,
    ) -> None:
        now_monotonic = time.monotonic()
        if (
            not force
            and str(phase) == str(self._heartbeat_last_phase)
            and (now_monotonic - float(self._heartbeat_last_write_monotonic or 0.0))
            < float(self._heartbeat_interval_sec)
        ):
            return

        path = self._heartbeat_path
        type_counts: dict[str, int] = {}
        request_count = 0
        for req in batch or []:
            if getattr(req, "request_type", None) == GpuRequestType.SHUTDOWN:
                continue
            req_name = str(getattr(getattr(req, "request_type", None), "value", "unknown") or "unknown")
            type_counts[req_name] = int(type_counts.get(req_name, 0)) + 1
            request_count += 1

        payload = {
            "pid": int(os.getpid()),
            "updated_at": int(time.time() * 1000.0),
            "phase": str(phase or "unknown"),
            "ready": bool(self._taichi_ready),
            "running": bool(self._running),
            "requests_processed": int(self._requests_processed),
            "request_count": int(request_count),
            "request_types": type_counts,
            "note": str(note or ""),
        }

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = path.with_suffix(path.suffix + ".tmp")
            tmp_path.write_text(
                json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")),
                encoding="utf-8",
            )
            os.replace(tmp_path, path)
            self._heartbeat_last_write_monotonic = now_monotonic
            self._heartbeat_last_phase = str(phase or "")
        except Exception:
            return

    def _executor_loop(self):
        """Main GPU execution loop with batch coalescing."""
        # Initialize Taichi ONCE
        try:
            from .taichi_gem.runtime import init_taichi

            init_taichi()
            self._taichi_ready = True
            self._ready_event.set()
            logger.debug("[GpuExecutor] Taichi initialized")
        except Exception as e:
            self._taichi_ready = False
            err = f"{type(e).__name__}: {e}"
            # Capture the full init traceback to disk so startup failures in dual-process mode
            # are diagnosable from user logs without enabling verbose tracing.
            try:
                tb = traceback.format_exc()
            except Exception:
                tb = ""
            trace_path = None
            try:
                trace_path = self._heartbeat_path.with_name(self._heartbeat_path.stem + "_taichi_init_error.log")
                trace_path.parent.mkdir(parents=True, exist_ok=True)
                trace_path.write_text(tb, encoding="utf-8", errors="replace")
            except Exception:
                trace_path = None
            if trace_path is not None:
                err = f"{err} (trace: {trace_path})"
            self._last_init_error = err
            self._running = False
            self._ready_event.set()
            self._write_heartbeat(phase="init_failed", note=self._last_init_error, force=True)
            logger.debug("[GpuExecutor] Taichi init failed: %s", e)
            return
        # Taichi init completed (warmup may still be running below).
        self._write_heartbeat(phase="init_ok", force=True)
        # Warm up FG kernels up-front to avoid the first ForceGreatsFinder call
        # incurring multi-second Taichi JIT latency (which shows up as a GA->FG GPU idle gap).
        warmup_fg = bool(getattr(ENV, "gpu_executor_warmup_fg", False))
        warmup_ga = bool(getattr(ENV, "gpu_executor_warmup_ga", False))
        if warmup_fg or warmup_ga:
            # Cross-process warmup coordination:
            # - On cold caches, Taichi warmups can take ~minute-scale wall time on Windows/Vulkan.
            # - In dual-process mode, workers can race compiling the same kernels into the shared
            #   offline-cache directory, increasing wall time and sometimes failing.
            # - Serialize the cold-cache warmup once per offline-cache dir using a file lock +
            #   a sentinel file. Other workers skip the expensive warmup work.
            try:
                from .taichi_gem import runtime as ti_runtime

                lock_cm = ti_runtime.offline_cache_lock(timeout_sec=None)
            except Exception:
                lock_cm = nullcontext("")

            self._write_heartbeat(phase="warmup_wait", force=True)
            try:
                with lock_cm as cache_dir:
                    cache_dir = str(cache_dir or "").strip()
                    sentinel_path = Path(cache_dir) / "metafinder_warmup_done.json" if cache_dir else None
                    if sentinel_path is not None and sentinel_path.exists():
                        self._write_heartbeat(phase="warmup_cached", force=True)
                    else:
                        sentinel_error = ""
                        try:
                            # Warm up FG kernels up-front to avoid the first ForceGreatsFinder call
                            # paying compilation latency (which shows up as a GA->FG GPU idle gap).
                            if warmup_fg:
                                try:
                                    self._write_heartbeat(phase="warmup_fg", force=True)
                                except Exception:
                                    pass
                                t0 = perf_counter()
                                from .taichi_gem.force_greats import fields as fg_fields

                                fg_fields.ensure_ready_with_warmup()
                                dt_ms = (perf_counter() - t0) * 1000.0
                                if ENV.perf_timing:
                                    logger.debug("[GpuExecutor] Warmed FG kernels in %.1fms", dt_ms)

                            # Warm up GPU-native GA kernels up-front to avoid the first GA request paying
                            # multi-second compilation latency. This also helps stabilize external GPU
                            # utilization graphs that otherwise show an early low-util \"hiccup\".
                            if warmup_ga:
                                try:
                                    self._write_heartbeat(phase="warmup_ga", force=True)
                                except Exception:
                                    pass
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
                            except Exception:
                                pass
                        finally:
                            if sentinel_path is not None:
                                try:
                                    payload = {
                                        "schema": 1,
                                        "ok": not bool(sentinel_error),
                                        "error": str(sentinel_error or ""),
                                        "pid": int(os.getpid()),
                                        "warmed_at": int(time.time() * 1000.0),
                                        "warmup_fg": bool(warmup_fg),
                                        "warmup_ga": bool(warmup_ga),
                                    }
                                    sentinel_path.parent.mkdir(parents=True, exist_ok=True)
                                    tmp_path = sentinel_path.with_suffix(".tmp")
                                    tmp_path.write_text(
                                        json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")),
                                        encoding="utf-8",
                                    )
                                    os.replace(tmp_path, sentinel_path)
                                except Exception:
                                    pass
            except Exception:
                # If anything about cross-process coordination fails, fall back to best-effort warmup.
                try:
                    if warmup_fg:
                        from .taichi_gem.force_greats import fields as fg_fields

                        fg_fields.ensure_ready_with_warmup()
                    if warmup_ga:
                        from .taichi_gem.api import ga_operations as ga_ops

                        ga_ops.warmup_ga_kernels()
                except Exception:
                    pass

        self._write_heartbeat(phase="ready", force=True)

        def _try_put_response(req: GpuRequest, resp: GpuResponse) -> bool:
            try:
                q = self._response_queues.get(req.worker_id)
                if q is None:
                    return False
                q.put(resp)
                return True
            except Exception:
                return False

        # After observing bursty workload, briefly switch to zero-wait dequeue so local
        # producers don't pay repeated batch-wait latency. This is especially important
        # in in-process mode where tiny timed waits can quantize into multi-ms bubbles
        # under Windows scheduler jitter.
        fg_burst_until = 0.0
        fg_burst_request_types = {
            GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
            GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
            GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS,
            GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH,
            GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS,
        }
        env_refresh_counter = 0
        cached_batch_wait_ms = int(getattr(ENV, "gpu_executor_batch_wait_ms", 10) or 10)
        cached_batch_max = int(getattr(ENV, "gpu_executor_max_batch", 8) or 8)
        cached_batch_wait_overridden = False
        cached_batch_max_overridden = False
        cached_fg_burst_window_ms = 6
        profile_events_enabled = bool(
            str(os.environ.get("METAFINDER_PROFILE_EVENTS_PATH") or os.environ.get("PROFILE_EVENTS_PATH") or "").strip()
        )
        trace_enabled = bool(self._trace_fp is not None or profile_events_enabled)
        need_batch_summary = bool(self._workload_profile_enabled or trace_enabled)
        live_enabled = bool(self._live_enabled)

        while self._running:
            batch: list[GpuRequest] = []
            responded_ids: set[int] = set()
            batch_metrics: dict[str, Any] = {}
            trace_shared_kwargs: dict[str, Any] = {}
            try:
                # Gather batch of pending requests.
                # Prefer runtime env overrides so batch sizing can be tuned without a restart.
                # (ENV is a cached snapshot read at import time.)
                if env_refresh_counter == 0:
                    cached_batch_wait_ms = int(getattr(ENV, "gpu_executor_batch_wait_ms", 10) or 10)
                    cached_batch_max = int(getattr(ENV, "gpu_executor_max_batch", 8) or 8)
                    cached_batch_wait_overridden = False
                    cached_batch_max_overridden = False
                    try:
                        raw = _ENV_GET("GPU_EXECUTOR_BATCH_WAIT_MS")
                        if raw is not None and str(raw).strip() != "":
                            cached_batch_wait_ms = int(str(raw).strip())
                            cached_batch_wait_overridden = True
                    except Exception:
                        pass
                    try:
                        raw = _ENV_GET("GPU_EXECUTOR_MAX_BATCH")
                        if raw is not None and str(raw).strip() != "":
                            cached_batch_max = int(str(raw).strip())
                            cached_batch_max_overridden = True
                    except Exception:
                        pass
                    try:
                        raw = _ENV_GET("GPU_EXECUTOR_FG_BURST_WINDOW_MS")
                        if raw is not None and str(raw).strip() != "":
                            cached_fg_burst_window_ms = int(str(raw).strip())
                        else:
                            cached_fg_burst_window_ms = 6
                    except Exception:
                        cached_fg_burst_window_ms = 6
                    cached_fg_burst_window_ms = max(0, int(cached_fg_burst_window_ms))
                env_refresh_counter = (env_refresh_counter + 1) % 64

                batch_wait_ms = int(cached_batch_wait_ms)
                batch_max = int(cached_batch_max)
                fg_burst_window_ms = int(cached_fg_burst_window_ms)
                # In-process mode benefits from larger batches but shorter waits because
                # producers are local and can enqueue follow-up work immediately.
                if self._in_process_queues:
                    if not cached_batch_max_overridden:
                        batch_max = max(int(batch_max), 8)
                    if not cached_batch_wait_overridden:
                        # Keep a modest default coalescing window so we can batch/coalesce without
                        # forcing the owner loop into sub-ms yield-spin behavior.
                        batch_wait_ms = min(int(batch_wait_ms), 6)
                        if int(fg_burst_window_ms) > 0 and perf_counter() < float(fg_burst_until):
                            batch_wait_ms = 0
                if batch_wait_ms < 0:
                    batch_wait_ms = 0
                if batch_max <= 0:
                    batch_max = 1
                queue_depth_hint = self._safe_qsize()
                pressure_hint = (
                    (float(queue_depth_hint) / float(batch_max))
                    if queue_depth_hint >= 0 and int(batch_max) > 0
                    else 0.0
                )
                planner_mode = (
                    "fg_burst"
                    if (int(fg_burst_window_ms) > 0 and perf_counter() < float(fg_burst_until))
                    else ("inproc" if self._in_process_queues else "static")
                )
                batch_plan = _BatchPlan(
                    wait_ms=int(batch_wait_ms),
                    max_batch=int(batch_max),
                    mode=str(planner_mode),
                    queue_depth_hint=int(queue_depth_hint),
                    pressure_hint=float(max(0.0, pressure_hint)),
                )

                if self._profile_enabled and self._profile_loop_start_ts is None:
                    self._profile_loop_start_ts = perf_counter()

                t_wait0 = perf_counter()
                batch = self._gather_batch(max_wait_ms=batch_wait_ms, max_batch_size=batch_max)
                dt_wait = perf_counter() - t_wait0
                self._wait_sec += dt_wait
                if live_enabled:
                    self._live_wait_sec += float(dt_wait)

                if need_batch_summary:
                    self._workload_batch_seq += 1
                    batch_metrics = self._summarize_batch(batch, plan=batch_plan, wait_sec=float(dt_wait))
                    if trace_enabled:
                        trace_shared_kwargs = {
                            "planner_mode": str(batch_metrics.get("mode", "")),
                            "queue_depth_hint": int(batch_metrics.get("queue_depth_hint", -1)),
                            "pressure_hint": float(batch_metrics.get("pressure_hint", 0.0)),
                            "work_units": float(batch_metrics.get("work_units", 0.0)),
                            "dominant_type": str(batch_metrics.get("dominant_type", "")),
                            "dominant_share_pct": float(batch_metrics.get("dominant_share_pct", 0.0)),
                            "diversity_pct": float(batch_metrics.get("diversity_pct", 0.0)),
                            "avg_submit_age_ms": float(batch_metrics.get("avg_submit_age_ms", 0.0)),
                        }

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

                saw_fg_work = False
                if self._in_process_queues and int(fg_burst_window_ms) > 0 and batch:
                    for req in batch:
                        if req.request_type == GpuRequestType.SHUTDOWN:
                            continue
                        if req.request_type in fg_burst_request_types:
                            saw_fg_work = True
                            break

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

                # Check for shutdown
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

                # Single-pass partitioning keeps request order without rescanning `batch`.
                ga_native_requests: list[GpuRequest] = []
                fg_requests: list[GpuRequest] = []
                fg_bundle_requests: list[GpuRequest] = []
                fg_ga_fused_requests: list[GpuRequest] = []
                reg_requests: list[GpuRequest] = []
                remaining: list[GpuRequest] = []
                for req in batch:
                    rt = req.request_type
                    if rt == GpuRequestType.GPU_NATIVE_GA_RUN:
                        ga_native_requests.append(req)
                    elif rt == GpuRequestType.SOLVE_FORCE_GREATS_FINDER:
                        fg_requests.append(req)
                    elif rt == GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH:
                        fg_bundle_requests.append(req)
                    elif rt == GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS:
                        fg_ga_fused_requests.append(req)
                    elif rt == GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY:
                        reg_requests.append(req)
                    else:
                        remaining.append(req)

                if ga_native_requests:
                    prof_before = self._gpu_prof_snapshot() if self._exec_breakdown_enabled else None
                    exec_start_ns = time.perf_counter_ns()
                    responses = self._execute_gpu_native_ga_run_batch(ga_native_requests)
                    exec_end_ns = time.perf_counter_ns()
                    dt_exec = float(exec_end_ns - exec_start_ns) / 1e9
                    self._record_exec_breakdown(
                        GpuRequestType.GPU_NATIVE_GA_RUN,
                        exec_wall_sec=float(dt_exec),
                        prof_before=prof_before,
                    )
                    self._exec_sec += dt_exec
                    per_req = dt_exec / max(1, len(ga_native_requests))
                    for _ in ga_native_requests:
                        self._req_type_counts[GpuRequestType.GPU_NATIVE_GA_RUN] += 1
                        self._req_type_exec_sec[GpuRequestType.GPU_NATIVE_GA_RUN] += per_req
                        self._last_work_req_type = GpuRequestType.GPU_NATIVE_GA_RUN

                    for req, resp in zip(ga_native_requests, responses):
                        if resp is None:
                            resp = GpuResponse(
                                request_id=req.request_id,
                                success=False,
                                error="GpuExecutor GA-native batch returned no response (internal error)",
                            )
                        self._record_latency(req, exec_start_ns=exec_start_ns, exec_end_ns=exec_end_ns)
                        if _try_put_response(req, resp):
                            responded_ids.add(int(req.request_id))
                        self._requests_processed += 1
                    if trace_enabled:
                        self._trace_event(
                            event="exec",
                            exec_sec=float(dt_exec),
                            batch_size=len(ga_native_requests),
                            types=f"{GpuRequestType.GPU_NATIVE_GA_RUN.value}:{len(ga_native_requests)}",
                            **trace_shared_kwargs,
                        )
                    if live_enabled:
                        self._live_exec_sec += float(dt_exec)
                        self._live_type_counts[GpuRequestType.GPU_NATIVE_GA_RUN] += len(ga_native_requests)
                        self._maybe_live_report()

                if fg_requests:
                    prof_before = self._gpu_prof_snapshot() if self._exec_breakdown_enabled else None
                    exec_start_ns = time.perf_counter_ns()
                    responses = self._coalesce_fg_task_requests(fg_requests)
                    exec_end_ns = time.perf_counter_ns()
                    dt_exec = float(exec_end_ns - exec_start_ns) / 1e9
                    self._record_exec_breakdown(
                        GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
                        exec_wall_sec=float(dt_exec),
                        prof_before=prof_before,
                    )
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
                        self._record_latency(req, exec_start_ns=exec_start_ns, exec_end_ns=exec_end_ns)
                        if _try_put_response(req, resp):
                            responded_ids.add(int(req.request_id))
                        self._requests_processed += 1
                    if trace_enabled:
                        self._trace_event(
                            event="exec",
                            exec_sec=float(dt_exec),
                            batch_size=len(fg_requests),
                            types=f"{GpuRequestType.SOLVE_FORCE_GREATS_FINDER.value}:{len(fg_requests)}",
                            **trace_shared_kwargs,
                        )
                    if live_enabled:
                        self._live_exec_sec += float(dt_exec)
                        self._live_type_counts[GpuRequestType.SOLVE_FORCE_GREATS_FINDER] += len(fg_requests)
                        self._maybe_live_report()

                if fg_bundle_requests:
                    prof_before = self._gpu_prof_snapshot() if self._exec_breakdown_enabled else None
                    exec_start_ns = time.perf_counter_ns()
                    responses = self._coalesce_fg_solve_with_breakpoints_batch_requests(fg_bundle_requests)
                    exec_end_ns = time.perf_counter_ns()
                    dt_exec = float(exec_end_ns - exec_start_ns) / 1e9
                    self._record_exec_breakdown(
                        GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH,
                        exec_wall_sec=float(dt_exec),
                        prof_before=prof_before,
                    )
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
                        self._record_latency(req, exec_start_ns=exec_start_ns, exec_end_ns=exec_end_ns)
                        if _try_put_response(req, resp):
                            responded_ids.add(int(req.request_id))
                        self._requests_processed += 1
                    if trace_enabled:
                        self._trace_event(
                            event="exec",
                            exec_sec=float(dt_exec),
                            batch_size=len(fg_bundle_requests),
                            types=f"{GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH.value}:{len(fg_bundle_requests)}",
                            **trace_shared_kwargs,
                        )
                    if live_enabled:
                        self._live_exec_sec += float(dt_exec)
                        self._live_type_counts[GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH] += len(
                            fg_bundle_requests
                        )
                        self._maybe_live_report()

                if fg_ga_fused_requests:
                    prof_before = self._gpu_prof_snapshot() if self._exec_breakdown_enabled else None
                    exec_start_ns = time.perf_counter_ns()
                    responses = self._coalesce_ga_fg_fused_requests(fg_ga_fused_requests)
                    exec_end_ns = time.perf_counter_ns()
                    dt_exec = float(exec_end_ns - exec_start_ns) / 1e9
                    self._record_exec_breakdown(
                        GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS,
                        exec_wall_sec=float(dt_exec),
                        prof_before=prof_before,
                    )
                    self._exec_sec += dt_exec
                    per_req = dt_exec / max(1, len(fg_ga_fused_requests))
                    for _ in fg_ga_fused_requests:
                        self._req_type_counts[GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS] += 1
                        self._req_type_exec_sec[GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS] += per_req
                        self._last_work_req_type = GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS

                    for req, resp in zip(fg_ga_fused_requests, responses):
                        if resp is None:
                            resp = GpuResponse(
                                request_id=req.request_id,
                                success=False,
                                error="GpuExecutor fused GA->FG batch returned no response (internal error)",
                            )
                        self._record_latency(req, exec_start_ns=exec_start_ns, exec_end_ns=exec_end_ns)
                        if _try_put_response(req, resp):
                            responded_ids.add(int(req.request_id))
                        self._requests_processed += 1
                    if trace_enabled:
                        self._trace_event(
                            event="exec",
                            exec_sec=float(dt_exec),
                            batch_size=len(fg_ga_fused_requests),
                            types=(
                                f"{GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS.value}:{len(fg_ga_fused_requests)}"
                            ),
                            **trace_shared_kwargs,
                        )
                    if live_enabled:
                        self._live_exec_sec += float(dt_exec)
                        self._live_type_counts[GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS] += len(
                            fg_ga_fused_requests
                        )
                        self._maybe_live_report()

                if reg_requests:
                    prof_before = self._gpu_prof_snapshot() if self._exec_breakdown_enabled else None
                    exec_start_ns = time.perf_counter_ns()
                    responses = self._coalesce_solve_genomes_from_registry(reg_requests)
                    exec_end_ns = time.perf_counter_ns()
                    dt_exec = float(exec_end_ns - exec_start_ns) / 1e9
                    self._record_exec_breakdown(
                        GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
                        exec_wall_sec=float(dt_exec),
                        prof_before=prof_before,
                    )
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
                        self._record_latency(req, exec_start_ns=exec_start_ns, exec_end_ns=exec_end_ns)
                        if _try_put_response(req, resp):
                            responded_ids.add(int(req.request_id))
                        self._requests_processed += 1
                    if trace_enabled:
                        self._trace_event(
                            event="exec",
                            exec_sec=float(dt_exec),
                            batch_size=len(reg_requests),
                            types=f"{GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY.value}:{len(reg_requests)}",
                            **trace_shared_kwargs,
                        )
                    if live_enabled:
                        self._live_exec_sec += float(dt_exec)
                        self._live_type_counts[GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY] += len(reg_requests)
                        self._maybe_live_report()

                # Process remaining request types individually
                for req in remaining:
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
                        self._live_exec_sec += float(dt_exec)
                        self._live_type_counts[req.request_type] += 1
                        self._maybe_live_report()

                if self._profile_enabled:
                    self._profile_last_work_end_ts = perf_counter()
                if saw_fg_work and self._in_process_queues and int(fg_burst_window_ms) > 0:
                    # Start the burst window *after* finishing the batch. The previous behavior anchored
                    # the window at gather time, which can expire during long GPU kernels and fail to
                    # suppress the very next coalesce-wait (the bubble we care about).
                    fg_burst_until = max(
                        float(fg_burst_until),
                        perf_counter() + (float(fg_burst_window_ms) / 1000.0),
                    )
                batch_metrics["exec_sec"] = max(0.0, float(perf_counter() - batch_exec_t0))
                if self._workload_profile_enabled:
                    self._record_workload_batch(batch_metrics)

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
                    logger.debug("[GpuExecutor] Error: %s", e)
                except Exception:
                    pass
                try:
                    traceback.print_exc()
                except Exception:
                    pass
                try:
                    if (
                        self._workload_profile_enabled
                        and batch_metrics
                        and float(batch_metrics.get("exec_sec", 0.0) or 0.0) <= 0.0
                    ):
                        batch_metrics["exec_sec"] = 0.0
                        batch_metrics["error"] = str(err)
                        self._record_workload_batch(batch_metrics)
                except Exception:
                    pass
                self._write_heartbeat(phase="error", batch=batch, note=str(err), force=True)

        self._write_heartbeat(phase="stopped", note=self._last_init_error or "", force=True)

    def _queue_get(self, timeout: float):
        wait_timeout = max(0.0, float(timeout))
        if wait_timeout <= 0.0:
            return self._request_queue.get(timeout=0.0)

        if not self._in_process_queues or wait_timeout > float(self._short_wait_spin_sec):
            return self._request_queue.get(timeout=wait_timeout)

        get_nowait = getattr(self._request_queue, "get_nowait", None)
        if not callable(get_nowait):
            return self._request_queue.get(timeout=wait_timeout)

        deadline = perf_counter() + wait_timeout
        yields = 0
        max_yields = int(getattr(self, "_short_wait_spin_yield_rounds", 0) or 0)
        while True:
            try:
                return get_nowait()
            except queue.Empty:
                now = perf_counter()
                if now >= deadline:
                    raise
                remaining = float(deadline - now)
                if yields < max_yields:
                    yields += 1
                    time.sleep(0)
                    continue

                # After a few yields, block in tiny chunks to avoid burning CPU.
                block_s = min(remaining, 0.001)  # 1ms cap
                if block_s <= 0.0:
                    raise
                try:
                    return self._request_queue.get(timeout=block_s)
                except queue.Empty:
                    continue

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
        coalescable_types = self._COALESCABLE_REQUEST_TYPES
        # Default to enabled for in-process queues; callers can opt out via env var.
        inproc_coalesce_enabled = env_flag("GPU_EXECUTOR_INPROC_COALESCE", "1")
        inproc_idle_wait_s = 0.1
        inproc_yields_left = 0
        if self._in_process_queues:
            # In-process queues can be extremely latency sensitive when there is already work in-flight, but when
            # completely idle we should avoid a tight (ms-scale) poll loop that burns CPU on Windows.
            try:
                raw_idle_ms = _ENV_GET("GPU_EXECUTOR_INPROC_IDLE_WAIT_MS", "100")
                inproc_idle_wait_s = float(str(raw_idle_ms).strip()) / 1000.0
            except Exception:
                inproc_idle_wait_s = 0.1
            inproc_idle_wait_s = max(0.0, min(float(inproc_idle_wait_s), 1.0))
            try:
                raw_yields = _ENV_GET("GPU_EXECUTOR_INPROC_COALESCE_YIELD_ROUNDS")
                if raw_yields is None or str(raw_yields).strip() == "":
                    inproc_yields_left = max(0, min(64, int(max_wait_ms)))
                else:
                    inproc_yields_left = int(str(raw_yields).strip())
            except Exception:
                inproc_yields_left = max(0, min(64, int(max_wait_ms)))
            inproc_yields_left = max(0, min(int(inproc_yields_left), 256))
        try:
            inproc_after_first_ms = int(_ENV_GET("GPU_EXECUTOR_INPROC_COALESCE_AFTER_FIRST_MS", "2"))
        except Exception:
            inproc_after_first_ms = 0
        inproc_after_first_ms = max(0, int(inproc_after_first_ms))
        if int(max_wait_ms) <= 0:
            inproc_after_first_ms = 0

        deferred = self._deferred_request
        if deferred is not None:
            self._deferred_request = None
            try:
                deferred.dequeue_perf_ns = time.perf_counter_ns()
            except Exception:
                pass
            batch.append(deferred)
            if deferred.request_type == GpuRequestType.SHUTDOWN:
                return batch
            if self._is_no_batch_request_type(deferred.request_type):
                return batch

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
                        if float(inproc_idle_wait_s) > 0.0:
                            timeout = float(inproc_idle_wait_s)
                        else:
                            timeout = 0.0 if int(max_wait_ms) <= 0 else max(0.0, float(remaining))
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
                            if int(max_wait_ms) <= 0:
                                timeout = 0.0
                            else:
                                # Avoid a hard 1ms floor in in-process mode. The floor can inject
                                # avoidable sub-ms → 1ms bubbles between back-to-back GPU batches.
                                timeout = max(0.0, float(remaining)) if allow_coalesce else 0.0
                else:
                    timeout = max(0.001, remaining) if len(batch) > 0 else 0.1
                if self._in_process_queues and inproc_coalesce_enabled and len(batch) > 0 and float(timeout) > 0.0:
                    get_nowait = getattr(self._request_queue, "get_nowait", None)
                    if callable(get_nowait):
                        try:
                            request = get_nowait()
                        except queue.Empty:
                            if perf_counter() >= deadline or int(inproc_yields_left) <= 0:
                                break
                            inproc_yields_left = int(inproc_yields_left) - 1
                            time.sleep(0)
                            continue
                    else:
                        request = self._queue_get(timeout)
                else:
                    request = self._queue_get(timeout)
                try:
                    request.dequeue_perf_ns = time.perf_counter_ns()
                except Exception:
                    pass
                if request.request_type == GpuRequestType.SHUTDOWN:
                    batch.append(request)
                    return batch

                # If a heavy/no-batch request arrives after we already have work, defer it to
                # become the first item of the next batch.
                if batch and self._is_no_batch_request_type(request.request_type):
                    if self._deferred_request is None:
                        self._deferred_request = request
                    else:
                        # Should be unreachable; avoid dropping work.
                        batch.append(request)
                    break

                batch.append(request)
                if self._is_no_batch_request_type(request.request_type):
                    break

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

    def _cache_registry_payload_static(self, worker_id: int, handle: int, static_payload: dict[str, Any]) -> None:
        key = (int(worker_id), int(handle))
        self._registry_payload_cache[key] = dict(static_payload)
        self._registry_payload_cache.move_to_end(key)
        while len(self._registry_payload_cache) > int(self._registry_payload_cache_max):
            self._registry_payload_cache.popitem(last=False)

    def _resolve_registry_payload(self, request: "GpuRequest") -> tuple[dict[str, Any], str | None]:
        """
        Resolve registry-solve payloads that optionally use worker-side static handles.

        Workers may send only dynamic fields (population indices + flags) plus
        `registry_payload_handle` after first registration to avoid repeated IPC
        transfer of immutable arrays/dicts.
        """
        payload = self._payload_dict(request)
        handle_raw = payload.get("registry_payload_handle")
        if handle_raw is None:
            return payload, None

        try:
            handle = int(handle_raw)
        except Exception:
            return payload, f"Invalid registry payload handle: {handle_raw!r}"

        worker_id = int(getattr(request, "worker_id", 0) or 0)
        cache_key = (worker_id, handle)
        inline = bool(payload.get("registry_payload_inline", False))
        static_keys = (
            "item_stats",
            "slot_start",
            "slot_count",
            "base_fixed_stats",
            "timeline_grid",
            "ref_arrays",
        )

        static_payload: dict[str, Any] | None = None
        if inline:
            missing = [k for k in static_keys if k not in payload]
            if missing:
                return payload, f"Invalid inline registry payload (missing {','.join(missing)})"
            static_payload = {k: payload[k] for k in static_keys}
            self._cache_registry_payload_static(worker_id, handle, static_payload)
        else:
            static_payload = self._registry_payload_cache.get(cache_key)
            if static_payload is None:
                return payload, f"Unknown registry payload handle={handle} for worker_id={worker_id}"
            self._registry_payload_cache.move_to_end(cache_key)

        resolved = dict(payload)
        for key in static_keys:
            if key not in resolved and static_payload is not None:
                resolved[key] = static_payload[key]
        return resolved, None

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

        task_budget = None
        try:
            raw_budget = os.environ.get("FG_TASK_BUDGET")
            if raw_budget is not None and str(raw_budget).strip() != "":
                task_budget = int(str(raw_budget).strip())
        except Exception:
            task_budget = None
        if task_budget is None:
            inflight_v3 = str(os.environ.get("INFLIGHT_V3", "") or "").strip().lower() in {"1", "true", "yes", "on"}
            inflight_v4 = str(os.environ.get("INFLIGHT_V4", "") or "").strip().lower() in {"1", "true", "yes", "on"}
            # Safety default: chunk FG task uploads in in-process mode to avoid multi-second continuous GPU work.
            task_budget = 256 if (inflight_v3 or inflight_v4 or self._in_process_queues) else 0
        task_budget = max(0, int(task_budget))

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
                    if self._profile_enabled:
                        try:
                            task_count = int(len(_fg_tasks))
                        except Exception:
                            task_count = 0
                        self._fg_tasks_batches += 1
                        self._fg_tasks_total += task_count
                        if task_count > self._fg_tasks_max:
                            self._fg_tasks_max = task_count
                        self._fg_tasks_batch_hist[task_count] += 1

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
                    if int(task_budget) > 0 and int(len(merged_tasks)) > int(task_budget):
                        upload_this = bool(kwargs_local.get("upload_genome_stats", True))
                        for j in range(0, int(len(merged_tasks)), int(task_budget)):
                            kwargs_local["upload_genome_stats"] = bool(upload_this)
                            solve_force_greats_finder_gpu_tasks(
                                genome_stats_list,
                                timestamps_np,
                                great_candidate_timestamps_np,
                                int(long_notes),
                                float(last_note_time),
                                fg_tasks=merged_tasks[j : j + int(task_budget)],
                                **kwargs_local,
                            )
                            upload_this = False
                    else:
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
            warn_fallback(
                "gpu_executor.fg_breakpoints_coalesce",
                "coalescing unavailable (not in-process); falling back to per-request execution",
                context={"request_count": len(requests)},
            )
            return [self._execute_request(req) for req in requests]

        try:
            max_payloads = int(os.environ.get("FG_BREAKPOINTS_BATCH_COALESCE_MAX_PAYLOADS", "16") or "16")
        except Exception:
            max_payloads = 16
        max_payloads = max(1, min(int(max_payloads), 512))
        try:
            max_pairs = int(os.environ.get("FG_BREAKPOINTS_BATCH_COALESCE_MAX_PAIRS", "32768") or "32768")
        except Exception:
            max_pairs = 32768
        max_pairs = max(0, int(max_pairs))
        if max_pairs > 0:
            import numpy as np

        def _payload_pairs(payloads: list[dict[str, Any]]) -> int:
            if max_pairs <= 0:
                return 0
            total = 0
            for p in payloads:
                ftff_pairs = p.get("ftff_pairs")
                if ftff_pairs is None:
                    continue
                try:
                    if isinstance(ftff_pairs, np.ndarray):
                        total += int(ftff_pairs.shape[0])
                    else:
                        total += int(len(ftff_pairs))
                except Exception:
                    continue
            return total

        def _split_payload_list(payload_list: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
            chunks: list[list[dict[str, Any]]] = []
            cur_chunk: list[dict[str, Any]] = []
            cur_pairs = 0

            for payload_item in payload_list:
                item_pairs = _payload_pairs([payload_item]) if max_pairs > 0 else 0
                if not cur_chunk:
                    cur_chunk = [payload_item]
                    cur_pairs = int(item_pairs)
                    continue

                exceed_payload_cap = (len(cur_chunk) + 1) > int(max_payloads)
                exceed_pairs_cap = bool(max_pairs > 0 and (cur_pairs + int(item_pairs)) > int(max_pairs))
                if exceed_payload_cap or exceed_pairs_cap:
                    chunks.append(cur_chunk)
                    cur_chunk = [payload_item]
                    cur_pairs = int(item_pairs)
                else:
                    cur_chunk.append(payload_item)
                    cur_pairs += int(item_pairs)

            if cur_chunk:
                chunks.append(cur_chunk)
            return chunks

        fallback: list[GpuResponse] = []
        direct: list[GpuResponse] = []
        groups: list[list[tuple["GpuRequest", list[dict[str, Any]], int, int]]] = []
        cur: list[tuple["GpuRequest", list[dict[str, Any]], int, int]] = []
        cur_payloads = 0
        cur_pairs = 0

        def _append_fallback(req: "GpuRequest", reason: str, *, extra: dict[str, Any] | None = None) -> None:
            context = {"request_id": int(getattr(req, "request_id", -1))}
            if extra:
                context.update(extra)
            warn_fallback("gpu_executor.fg_breakpoints_request", reason, context=context)
            fallback.append(self._execute_request(req))

        for req in requests:
            payload = self._payload_dict(req)
            payloads = payload.get("payloads")
            if not isinstance(payloads, (list, tuple)) or not payloads:
                _append_fallback(req, "missing/empty payloads list")
                continue
            ok = True
            for p in payloads:
                if not isinstance(p, dict):
                    ok = False
                    break
            if not ok:
                _append_fallback(req, "payload list contains non-dict item")
                continue

            payload_list = list(payloads)
            n_payloads = int(len(payload_list))
            if n_payloads <= 0:
                _append_fallback(req, "payload list length resolved to zero")
                continue
            n_pairs = _payload_pairs(payload_list)
            if n_payloads > int(max_payloads) or (max_pairs > 0 and n_pairs > int(max_pairs)):
                try:
                    merged_results: list[Any] = []
                    for payload_chunk in _split_payload_list(payload_list):
                        split_req = GpuRequest(
                            request_type=GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH,
                            request_id=int(req.request_id),
                            worker_id=int(req.worker_id),
                            payload={"payloads": payload_chunk},
                        )
                        split_resp = self._execute_fg_solve_with_breakpoints_batch(split_req)
                        if not getattr(split_resp, "success", False):
                            raise RuntimeError(f"split FG request failed: {getattr(split_resp, 'error', None)}")
                        split_result = getattr(split_resp, "result", None)
                        if not isinstance(split_result, list):
                            raise TypeError("split FG request returned non-list result")
                        if int(len(split_result)) != int(len(payload_chunk)):
                            raise RuntimeError("split FG request length mismatch")
                        merged_results.extend(split_result)
                    direct.append(
                        GpuResponse(
                            request_id=int(req.request_id),
                            success=True,
                            result=merged_results,
                        )
                    )
                except Exception as exc:
                    warn_fallback(
                        "gpu_executor.fg_breakpoints_request_split",
                        "failed to split oversized payload list; falling back to per-request execution",
                        context={
                            "request_id": int(req.request_id),
                            "payloads": n_payloads,
                            "max_payloads": max_payloads,
                            "pairs": int(n_pairs),
                            "max_pairs": int(max_pairs),
                        },
                        exc=exc,
                    )
                    fallback.append(self._execute_request(req))
                continue

            if cur and (
                cur_payloads + n_payloads > int(max_payloads)
                or (max_pairs > 0 and cur_pairs + n_pairs > int(max_pairs))
            ):
                groups.append(cur)
                cur = []
                cur_payloads = 0
                cur_pairs = 0

            cur.append((req, payload_list, n_payloads, n_pairs))
            cur_payloads += n_payloads
            cur_pairs += n_pairs

        if cur:
            groups.append(cur)

        out: list[GpuResponse] = []
        out.extend(direct)
        out.extend(fallback)

        if not groups:
            by_id = {r.request_id: r for r in out if r is not None}
            return [by_id.get(req.request_id) for req in requests]

        for group in groups:
            if len(group) == 1:
                out.append(self._execute_request(group[0][0]))
                continue
            try:
                merged_payloads: list[dict[str, Any]] = []
                slices: list[tuple["GpuRequest", int, int]] = []
                for req, payload_list, n_payloads, _ in group:
                    start = len(merged_payloads)
                    merged_payloads.extend(payload_list)
                    slices.append((req, start, int(n_payloads)))

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
            except Exception as exc:
                warn_fallback(
                    "gpu_executor.fg_breakpoints_group",
                    "merged coalesced group failed; falling back to per-request execution",
                    context={"group_size": len(group)},
                    exc=exc,
                )
                for req, _, _, _ in group:
                    out.append(self._execute_request(req))

        by_id = {r.request_id: r for r in out if r is not None}
        return [by_id.get(req.request_id) for req in requests]

    def _coalesce_ga_fg_fused_requests(self, requests: list["GpuRequest"]) -> list["GpuResponse"]:
        """
        Coalesce GA->FG fused requests by routing through the FG breakpoint batch handler.

        Each request payload matches `FG_SOLVE_WITH_BREAKPOINTS` input. We pack request payloads
        into one synthetic `FG_SOLVE_WITH_BREAKPOINTS_BATCH` call and then split outputs.
        """
        if not requests:
            return []
        if not self._in_process_queues or len(requests) <= 1:
            return [self._execute_request(req) for req in requests]

        synthetic_batch_requests: list[GpuRequest] = []
        fallback_ids: set[int] = set()
        fallback_reason_by_id: dict[int, str] = {}

        def _mark_fallback(req_id: int, reason: str) -> None:
            rid = int(req_id)
            fallback_ids.add(rid)
            if rid not in fallback_reason_by_id:
                fallback_reason_by_id[rid] = str(reason)

        for req in requests:
            payload = req.payload
            if not isinstance(payload, dict):
                _mark_fallback(int(req.request_id), "invalid request payload type")
                continue
            synthetic_batch_requests.append(
                GpuRequest(
                    request_type=GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH,
                    request_id=int(req.request_id),
                    worker_id=int(req.worker_id),
                    payload={"payloads": [payload]},
                )
            )

        out: list[GpuResponse] = []
        if synthetic_batch_requests:
            batch_responses = self._coalesce_fg_solve_with_breakpoints_batch_requests(synthetic_batch_requests)
            for req, resp in zip(synthetic_batch_requests, batch_responses):
                if resp is None:
                    _mark_fallback(int(req.request_id), "missing coalesced response")
                    continue
                if not bool(getattr(resp, "success", False)):
                    _mark_fallback(int(req.request_id), "coalesced response unsuccessful")
                    continue
                result = getattr(resp, "result", None)
                if not isinstance(result, list) or len(result) != 1:
                    _mark_fallback(int(req.request_id), "unexpected coalesced result shape")
                    continue
                out.append(
                    GpuResponse(
                        request_id=int(req.request_id),
                        success=True,
                        result=result[0],
                    )
                )

        if fallback_ids:
            for req in requests:
                if int(req.request_id) in fallback_ids:
                    warn_fallback(
                        "gpu_executor.ga_fg_fused_coalesce.request",
                        "coalesced fused request fallback to per-request execution",
                        context={
                            "request_id": int(req.request_id),
                            "reason": fallback_reason_by_id.get(int(req.request_id), "unknown"),
                        },
                    )
                    out.append(self._execute_request(req))

        by_id = {r.request_id: r for r in out if r is not None}
        return [by_id.get(req.request_id) for req in requests]

    def _coalesce_solve_genomes_from_registry(self, requests: list["GpuRequest"]) -> list["GpuResponse"]:
        """
        Coalesce multiple SOLVE_GENOMES_FROM_REGISTRY requests by concatenating small population batches.

        This is conservative and only merges requests with semantically identical per-song inputs.
        Object identity checks are not reliable across IPC boundaries, so request equivalence must be
        decided by value equality for arrays/dicts plus exact scalar flag equality.
        """
        import numpy as np

        from .taichi_gem.api import (
            ga_upload_base_fixed_stats,
            ga_upload_item_stats,
            load_ref_arrays,
            solve_genomes_from_registry,
        )
        from .taichi_gem import fields as gem_fields

        scalar_fields = (
            "song_slot",
            "total_budget",
            "gem_scale_fever",
            "is_p_ft",
            "is_s_ft",
            "is_p_ff",
            "is_s_ff",
            "is_p_pp",
            "is_s_pp",
            "is_p_cm",
            "is_s_cm",
            "is_p_fm",
            "is_s_fm",
            "is_p_ov",
            "is_s_ov",
        )

        array_sig_cache: dict[tuple[int, int, tuple[int, ...], tuple[int, ...], str], bytes] = {}
        object_sig_cache: dict[int, Any] = {}

        def _array_sig(v: Any) -> tuple[Any, ...]:
            if v is None:
                return ("none",)
            try:
                arr = np.asarray(v)
            except Exception:
                return ("repr", type(v).__name__, repr(v))
            if arr.ndim == 0:
                try:
                    return ("scalar", str(arr.dtype), repr(arr.item()))
                except Exception:
                    return ("scalar", str(arr.dtype), repr(arr))
            try:
                arr_ptr = int(arr.__array_interface__["data"][0])
            except Exception:
                arr_ptr = int(id(arr))
            # Include strides so distinct views sharing the same pointer/shape/dtype
            # (e.g. square transpose) cannot collide.
            try:
                strides = tuple(int(x) for x in (arr.strides or ()))
            except Exception:
                strides = ()
            key = (int(id(arr)), int(arr_ptr), tuple(int(x) for x in arr.shape), strides, str(arr.dtype))
            digest = array_sig_cache.get(key)
            if digest is None:
                try:
                    arr_c = arr if arr.flags["C_CONTIGUOUS"] else np.ascontiguousarray(arr)
                    h = hashlib.blake2b(digest_size=16)
                    h.update(memoryview(arr_c).cast("B"))
                    digest = h.digest()
                except Exception:
                    digest = bytes(str(id(arr)), "utf-8")
                array_sig_cache[key] = digest
            return ("arr", key[2], key[3], key[4], digest)

        def _object_sig(v: Any) -> Any:
            if v is None or isinstance(v, (int, float, bool, str, bytes)):
                return v
            if isinstance(v, np.ndarray):
                return _array_sig(v)
            oid = int(id(v))
            cached = object_sig_cache.get(oid)
            if cached is not None:
                return cached
            if isinstance(v, dict):
                sig = (
                    "dict",
                    tuple((str(k), _object_sig(v.get(k))) for k in sorted(v.keys(), key=lambda x: str(x))),
                )
                object_sig_cache[oid] = sig
                return sig
            if isinstance(v, (list, tuple)):
                sig = (type(v).__name__, tuple(_object_sig(x) for x in v))
                object_sig_cache[oid] = sig
                return sig
            sig = ("obj", type(v).__name__, repr(v))
            object_sig_cache[oid] = sig
            return sig

        def _scalar_key(p: dict[str, Any]) -> tuple[int, ...]:
            vals: list[int] = []
            for field in scalar_fields:
                default = 90 if field == "total_budget" else 3 if field == "gem_scale_fever" else 0
                vals.append(int(p.get(field, default) or default))
            return tuple(vals)

        def _timeline_sig(v: Any) -> Any:
            if not isinstance(v, dict):
                return _object_sig(v)
            song_data = v.get("song_data")
            if not isinstance(song_data, dict):
                return _object_sig(v)
            try:
                from gear_optimizer.core.array_signature import array_sig16 as _array_sig16_fast
            except Exception:
                _array_sig16_fast = None  # type: ignore[assignment]

            def _sig16(key_name: str, arr: Any) -> Any:
                sig = song_data.get(key_name)
                if isinstance(sig, (bytes, bytearray, memoryview)) and len(sig) == 16:
                    return ("sig16", bytes(sig))
                if _array_sig16_fast is not None:
                    try:
                        return ("sig16", _array_sig16_fast(arr))
                    except Exception:
                        pass
                return _array_sig(arr)

            return (
                "timeline",
                _object_sig(v.get("metadata")),
                _sig16("_timestamps_sig", song_data.get("timestamps")),
                _sig16("_chart_timestamps_sig", song_data.get("chart_timestamps")),
                _sig16("_note_types_sig", song_data.get("note_types")),
            )

        def _ref_sig(v: Any) -> Any:
            if isinstance(v, dict):
                sig = self._ref_arrays_sig(v)
                if sig is not None:
                    return ("ref", bytes(sig))
            return _object_sig(v)

        def _registry_payload_sig(p: dict[str, Any]) -> tuple[Any, ...]:
            return (
                _scalar_key(p),
                _timeline_sig(p.get("timeline_grid")),
                _ref_sig(p.get("ref_arrays")),
                _array_sig(p.get("item_stats")),
                _array_sig(p.get("slot_start")),
                _array_sig(p.get("slot_count")),
                _array_sig(p.get("base_fixed_stats")),
            )

        groups_by_sig: "OrderedDict[tuple[Any, ...], list[GpuRequest]]" = OrderedDict()
        groups: list[list[GpuRequest]] = []
        for req in requests:
            p = self._payload_dict(req)
            pop = p.get("population_indices")
            if pop is None:
                groups.append([req])
                continue
            try:
                handle_raw = p.get("registry_payload_handle")
                if handle_raw is not None:
                    sig = (
                        _scalar_key(p),
                        ("handle", int(getattr(req, "worker_id", 0) or 0), int(handle_raw)),
                    )
                else:
                    sig = _registry_payload_sig(p)
            except Exception:
                groups.append([req])
                continue
            groups_by_sig.setdefault(sig, []).append(req)
        groups.extend(list(groups_by_sig.values()))

        out: list[GpuResponse] = []
        max_genomes = int(getattr(gem_fields, "MAX_GENOMES", 4096) or 4096)
        resolved_payload_cache: dict[int, dict[str, Any]] = {}

        def _resolved_payload(req: GpuRequest) -> tuple[dict[str, Any], str | None]:
            rid = int(getattr(req, "request_id", 0) or 0)
            cached = resolved_payload_cache.get(rid)
            if cached is not None:
                return cached, None
            resolved, err = self._resolve_registry_payload(req)
            if err is None:
                resolved_payload_cache[rid] = resolved
            return resolved, err

        for group in groups:
            if not group:
                continue
            if len(group) == 1:
                out.append(self._execute_request(group[0]))
                continue

            p0, err0 = _resolved_payload(group[0])
            if err0:
                for req in group:
                    out.append(
                        GpuResponse(
                            request_id=req.request_id,
                            success=False,
                            error=err0,
                        )
                    )
                continue
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
                    p, perr = _resolved_payload(group[i])
                    if perr:
                        out.append(
                            GpuResponse(
                                request_id=group[i].request_id,
                                success=False,
                                error=perr,
                            )
                        )
                        i += 1
                        continue
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

                # Reuse a persistent scratch buffer to reduce allocator churn in hot coalescing loops.
                staging_buf = self._registry_coalesce_staging
                if staging_buf is None or int(staging_buf.shape[0]) < int(n_total) or int(staging_buf.shape[1]) != 9:
                    # Keep it at least `max_genomes` rows so typical batches don't reallocate.
                    staging_rows = max(int(n_total), int(max_genomes))
                    staging_buf = np.empty((int(staging_rows), 9), dtype=np.int32)
                    self._registry_coalesce_staging = staging_buf
                staging = staging_buf[: int(n_total), :]
                spans: list[tuple[int, int]] = []
                cur = 0
                ok = True
                t_pack0 = perf_counter()
                for req in chunk:
                    p, perr = _resolved_payload(req)
                    if perr:
                        ok = False
                        break
                    pop_arr = np.asarray(p.get("population_indices"), dtype=np.int32)
                    n = int(pop_arr.shape[0])
                    if pop_arr.ndim != 2 or int(pop_arr.shape[1]) != 9 or n <= 0:
                        ok = False
                        break
                    staging[cur : cur + n, :] = pop_arr[:n, :]
                    spans.append((cur, cur + n))
                    cur += n

                if not ok or cur <= 0:
                    warn_fallback(
                        "gpu_executor.registry_coalesce.chunk",
                        "registry coalescing chunk pack failed; falling back to per-request execution",
                        context={"chunk_size": int(len(chunk)), "cur": int(cur)},
                    )
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

    def _execute_solve_genomes_from_registry(self, request: GpuRequest, song_slot: int = 0) -> GpuResponse:
        """Execute solve_genomes_from_registry on GPU (GPU-resident stat aggregation path)."""
        from .taichi_gem.api import (
            ga_upload_base_fixed_stats,
            ga_upload_item_stats,
            load_ref_arrays,
            solve_genomes_from_registry,
        )

        payload, resolve_err = self._resolve_registry_payload(request)
        if resolve_err:
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error=resolve_err,
            )

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

        # ------------------------------------------------------------------
        # Executor-managed dependencies (avoid multi-request submit sequences).
        #
        # These keys are consumed here and MUST NOT be forwarded into the Taichi API.
        # ------------------------------------------------------------------
        ensure_timeline_precompute = bool(kwargs.pop("ensure_timeline_precompute", False))
        calc_song = kwargs.pop("calc_song", None)
        ga_stage_coords = kwargs.pop("ga_stage_coords", None)
        ga_stage_table_slot = kwargs.pop("ga_stage_table_slot", None)
        ga_stage_n_slots = kwargs.pop("ga_stage_n_slots", 9)

        # Optional: precompute the timeline grid as part of this same request so callers
        # don't need a separate PRECOMPUTE_TIMELINE request that can interleave across songs.
        if ensure_timeline_precompute:
            ref_arrays0 = kwargs.get("ref_arrays")
            try:
                song_slot0 = int(kwargs.get("song_slot", 0) or 0)
            except Exception:
                song_slot0 = 0
            if not isinstance(calc_song, dict) or not isinstance(ref_arrays0, dict):
                return GpuResponse(
                    request_id=request.request_id,
                    success=False,
                    error="SOLVE_FORCE_GREATS_FINDER ensure_timeline_precompute requires calc_song/ref_arrays dicts",
                )
            try:
                from .taichi_gem.api.timeline import precompute_timeline_gpu

                precompute_timeline_gpu(calc_song, ref_arrays0, song_slot=int(song_slot0))
            except Exception as e:
                return GpuResponse(
                    request_id=request.request_id,
                    success=False,
                    error=f"SOLVE_FORCE_GREATS_FINDER timeline precompute failed: {type(e).__name__}: {e}",
                )

        # Optional: stage genome_base_stats from GPU-native GA -> FG candidate table within
        # the same request to avoid a GA_STAGE_FG_GENOME_BASE_STATS boundary.
        if ga_stage_coords is not None:
            if not self._in_process_queues:
                return GpuResponse(
                    request_id=request.request_id,
                    success=False,
                    error="SOLVE_FORCE_GREATS_FINDER GA staging requires in-process queues",
                )
            try:
                from .taichi_gem.api import ga_stage_genome_base_stats_from_fg_candidates_table

                try:
                    table_slot = (
                        int(ga_stage_table_slot)
                        if ga_stage_table_slot is not None
                        else int(kwargs.get("song_slot", 0) or 0)
                    )
                except Exception:
                    table_slot = int(kwargs.get("song_slot", 0) or 0)
                n_staged = ga_stage_genome_base_stats_from_fg_candidates_table(
                    table_slot=int(table_slot),
                    coords=ga_stage_coords,
                    n_slots=int(ga_stage_n_slots or 9),
                )
                if int(n_staged) <= 0:
                    return GpuResponse(
                        request_id=request.request_id,
                        success=False,
                        error="SOLVE_FORCE_GREATS_FINDER GA staging produced n_staged<=0",
                    )
            except Exception as e:
                return GpuResponse(
                    request_id=request.request_id,
                    success=False,
                    error=f"SOLVE_FORCE_GREATS_FINDER GA staging failed: {type(e).__name__}: {e}",
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

    def _execute_gpu_native_ga_run_batch(self, requests: list[GpuRequest]) -> list[GpuResponse]:
        """
        Execute multiple GPU_NATIVE_GA_RUN requests on the owner thread.

        This keeps request dispatch in one executor pass and reduces per-request routing overhead.
        """
        if not requests:
            return []
        if len(requests) == 1:
            return [self._execute_gpu_native_ga_run(requests[0])]

        try:
            max_reqs = int(os.environ.get("GPU_NATIVE_GA_BATCH_COALESCE_MAX_REQS", "3") or "3")
        except Exception:
            max_reqs = 3
        max_reqs = max(1, min(int(max_reqs), 64))

        try:
            max_work_units = float(os.environ.get("GPU_NATIVE_GA_BATCH_COALESCE_MAX_WORK_UNITS", "60000") or "60000")
        except Exception:
            max_work_units = 60000.0
        if max_work_units <= 0.0:
            max_work_units = float("inf")

        out: list[GpuResponse] = []
        chunk: list[GpuRequest] = []
        chunk_units = 0.0

        for req in requests:
            req_units = max(1.0, float(self._estimate_request_work_units(req)))
            if chunk and (len(chunk) >= int(max_reqs) or (chunk_units + req_units) > float(max_work_units)):
                out.extend(self._execute_gpu_native_ga_run_chunk(chunk))
                chunk = []
                chunk_units = 0.0
            chunk.append(req)
            chunk_units += req_units

        if chunk:
            out.extend(self._execute_gpu_native_ga_run_chunk(chunk))

        return out

    def _execute_gpu_native_ga_run_chunk(self, requests: list[GpuRequest]) -> list[GpuResponse]:
        if not requests:
            return []
        return [self._execute_gpu_native_ga_run(req) for req in requests]

    def _execute_ga_fg_fused_solve_with_breakpoints(self, request: GpuRequest) -> GpuResponse:
        """
        Fused GA->FG request.

        Payload contract matches `FG_SOLVE_WITH_BREAKPOINTS`; this type exists so callers can
        explicitly mark the GA->FG fast path and the executor can batch/coalesce it separately.
        """
        return self._execute_fg_solve_with_breakpoints(request)

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

    def _execute_fg_select_signature_frontier_batch(self, request: GpuRequest) -> GpuResponse:
        """
        Select multiple FG signature frontiers on the GPU-owner thread.

        This is the in-process/owned equivalent of calling
        `taichi_gem.force_greats.api.fg_select_signature_frontier_batch()` directly.
        """
        if not self._in_process_queues:
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="FG_SELECT_SIGNATURE_FRONTIER_BATCH requires in-process queues (avoid IPC pickling)",
            )

        payload = request.payload or {}
        payloads = payload.get("payloads")
        if not isinstance(payloads, list):
            return GpuResponse(
                request_id=request.request_id,
                success=False,
                error="FG_SELECT_SIGNATURE_FRONTIER_BATCH requires payload['payloads'] list",
            )

        from .taichi_gem.force_greats.api import fg_select_signature_frontier_batch

        result = fg_select_signature_frontier_batch(payloads)
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

        ensure_timeline_precompute = bool(payload.get("ensure_timeline_precompute", False))
        if ensure_timeline_precompute:
            calc_song = payload.get("calc_song")
            ref_arrays = payload.get("ref_arrays")
            song_slot0 = int(payload.get("song_slot", 0) or 0)
            if not isinstance(calc_song, dict) or not isinstance(ref_arrays, dict):
                return GpuResponse(
                    request_id=request.request_id,
                    success=False,
                    error="FG_COMPUTE_BREAKPOINTS ensure_timeline_precompute requires calc_song/ref_arrays dicts",
                )
            try:
                from .taichi_gem.api.timeline import precompute_timeline_gpu

                precompute_timeline_gpu(calc_song, ref_arrays, song_slot=int(song_slot0))
            except Exception as e:
                return GpuResponse(
                    request_id=request.request_id,
                    success=False,
                    error=f"FG_COMPUTE_BREAKPOINTS timeline precompute failed: {type(e).__name__}: {e}",
                )

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

        debug_batch_pack = env_flag("FG_BREAKPOINTS_BATCH_PACK_DEBUG", "0")
        try:
            min_pack_payloads = int(os.environ.get("FG_BREAKPOINTS_BATCH_PACK_MIN_PAYLOADS", "2") or "2")
        except Exception:
            min_pack_payloads = 2
        min_pack_payloads = max(1, min(int(min_pack_payloads), 128))
        if debug_batch_pack:
            try:
                logger.debug("[FG][BatchPack] request payloads=%s", len(payloads))
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
                # Hidden host-side bottleneck: when payloads share the same top-K selection
                # inputs (base_scores/keep_mask), repeatedly uploading them for every payload
                # adds avoidable transfer overhead and GPU idle gaps. Reuse uploads across
                # consecutive payloads in this batch when identity + shape context matches.
                last_selection_upload_key: tuple[Any, ...] | None = None
                selection_sig_cache: dict[tuple[Any, ...], tuple[Any, ...]] = {}
                for chunk_start in range(0, int(len(payloads)), int(max_batch)):
                    chunk = list(payloads[chunk_start : chunk_start + int(max_batch)])
                    if not chunk:
                        continue

                    decode_ctx: list[dict[str, Any]] = []
                    for i, p in enumerate(chunk):
                        payload_for_run = p
                        try:
                            n_sel = 0
                            gs = p.get("genome_stats_list")
                            if gs is not None:
                                n_sel = int(len(gs))
                            else:
                                solve_kwargs_i = p.get("solve_kwargs") or {}
                                if isinstance(solve_kwargs_i, dict):
                                    n_sel = int(solve_kwargs_i.get("n_genomes_override", 0) or 0)
                            selection_upload_key = _fg_selection_upload_key(
                                p,
                                n_active=int(n_sel),
                                sig_cache=selection_sig_cache,
                            )
                            if (
                                last_selection_upload_key is not None
                                and selection_upload_key == last_selection_upload_key
                            ):
                                payload_for_run = dict(p)
                                payload_for_run["fg_selection_inputs_preuploaded"] = True
                            else:
                                last_selection_upload_key = selection_upload_key
                        except Exception:
                            payload_for_run = p

                        ctx = self._run_fg_solve_with_breakpoints_payload(payload_for_run, batch_pack_idx=int(i))
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
                            # Match single-payload behavior for callers without cfg_counts.
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
                    logger.debug("[FG][BatchPack] skipped: %s (payloads=%s)", reason, len(payloads))
                except Exception:
                    pass
        except Exception as exc:
            if debug_batch_pack:
                try:
                    import traceback

                    logger.debug("[FG][BatchPack] disabled: %s: %s", type(exc).__name__, exc)
                    logger.debug("%s", traceback.format_exc())
                except Exception:
                    pass
            # Fall through to per-payload download path.
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

        implicit_cfgs = str(_ENV_GET("FG_IMPLICIT_CONFIGS", "1") or "").strip().lower() in (TRUTHY_ENV_VALUES | {""})

        fg_tasks: list[dict[str, Any]] = []
        cfg_windows: list[dict] | None = None
        # Default ON: keeping per-pair max-FP computation on-GPU avoids an expensive
        # host download+re-upload cycle that often appears as unexplained idle time.
        use_gpu_max_fp_compute = env_flag("FG_MAX_FP_GPU_COMPUTE", "1")
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
                            # Reuse pre-split base stat vectors; avoids repeated host slicing
                            # in downstream task preparation.
                            "base_ft": base_ft,
                            "base_ff": base_ff,
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
            # Fallback: group identical max-FP rows on CPU (explicit grouping path).
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
            timestamps_np,
            great_candidate_timestamps_np,
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

            skip_selection_upload = bool(payload.get("fg_selection_inputs_preuploaded", False))
            fg_pack_global_best_topk_to_batch(
                int(n_genomes),
                session_slot=int(song_slot),
                topk=int(download_topk),
                base_scores=download_base_scores,
                keep_mask=download_keep_mask,
                batch_idx=int(batch_pack_idx),
                upload_selection_inputs=not bool(skip_selection_upload),
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
                "workload_events_emitted": int(self._workload_events_emitted),
                "last_batch_mode": str(self._last_batch_plan_mode),
                "avg_work_units": (
                    float(sum(self._workload_units_samples)) / float(len(self._workload_units_samples))
                    if self._workload_units_samples
                    else 0.0
                ),
                "avg_submit_age_ms": (
                    float(sum(self._workload_age_ms_samples)) / float(len(self._workload_age_ms_samples))
                    if self._workload_age_ms_samples
                    else 0.0
                ),
                "exec_breakdown_sec_by_type": {
                    str(req_type.value): {
                        "host_sec": float(self._req_type_host_sec.get(req_type, 0.0) or 0.0),
                        "gpu_kernel_sec": float(self._req_type_gpu_kernel_sec.get(req_type, 0.0) or 0.0),
                        "gpu_upload_sec": float(self._req_type_gpu_upload_sec.get(req_type, 0.0) or 0.0),
                        "gpu_download_sec": float(self._req_type_gpu_download_sec.get(req_type, 0.0) or 0.0),
                    }
                    for req_type in self._req_type_counts.keys()
                },
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
        visible_device = str(vulkan_visible_device).strip()
        os.environ["TAICHI_VULKAN_VISIBLE_DEVICE"] = visible_device
        os.environ["TI_VISIBLE_DEVICE"] = visible_device

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
        logger.debug(
            f"[GpuExecutor][{label}] Starting server loop "
            f"(TAICHI_VULKAN_VISIBLE_DEVICE={os.environ.get('TAICHI_VULKAN_VISIBLE_DEVICE', '') or 'default'})"
        )
    except Exception:
        pass

    ex._executor_loop()


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
    entry = _registry_static_handle_entry(
        item_stats=item_stats,
        slot_start=slot_start,
        slot_count=slot_count,
        base_fixed_stats=base_fixed_stats,
        timeline_grid=timeline_grid,
        ref_arrays=ref_arrays,
    )
    handle = int(entry.get("handle", 0) or 0)
    if handle <= 0:
        raise RuntimeError("Failed to allocate registry payload handle")

    def _build_payload(*, inline_static: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "population_indices": population_indices,
            "registry_payload_handle": int(handle),
            "registry_payload_inline": bool(inline_static),
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
            "total_budget": int(total_budget),
            "gem_scale_fever": int(gem_scale_fever),
            "song_slot": int(song_slot),
        }
        if inline_static:
            payload.update(
                {
                    "item_stats": item_stats,
                    "slot_start": slot_start,
                    "slot_count": slot_count,
                    "base_fixed_stats": base_fixed_stats,
                    "timeline_grid": entry.get("timeline_grid_send", timeline_grid),
                    "ref_arrays": ref_arrays,
                }
            )
        return payload

    def _submit_once(payload: dict[str, Any]) -> GpuResponse:
        nonlocal timeout
        global _REQUEST_COUNTER
        _REQUEST_COUNTER += 1
        request_id = _REQUEST_COUNTER
        request = GpuRequest(
            request_type=GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
            request_id=request_id,
            worker_id=_WORKER_ID,
            payload=payload,
            submit_perf_ns=time.perf_counter_ns(),
        )
        _ensure_worker_response_router_started()
        _REQUEST_QUEUE.put(request)
        return _wait_for_worker_response(request_id, timeout)

    inline_static = not bool(entry.get("registered", False))
    response = _submit_once(_build_payload(inline_static=inline_static))

    # Executor can restart and lose handle cache; re-register inline once.
    if (not response.success) and (not inline_static):
        err_text = str(getattr(response, "error", "") or "")
        if "Unknown registry payload handle" in err_text:
            entry["registered"] = False
            response = _submit_once(_build_payload(inline_static=True))

    if not response.success:
        raise RuntimeError(f"GPU executor error: {response.error}")

    entry["registered"] = True
    result = response.result
    try:
        n_expected = int(getattr(population_indices, "shape", [len(population_indices)])[0])
    except Exception:
        n_expected = 0
    if isinstance(result, list) and n_expected and len(result) != n_expected:
        raise RuntimeError(f"GPU executor returned {len(result)} results for {n_expected} genomes")
    return result
