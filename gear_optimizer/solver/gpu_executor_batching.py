from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from gear_optimizer.solver.gpu_executor_types import GpuRequestType


FG_BURST_REQUEST_TYPES = frozenset(
    {
        GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
        GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS,
        GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH,
        GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS,
    }
)


def effective_owner_batch_max(
    base_batch_max: int,
    *,
    in_process_queues: bool,
    batch_max_overridden: bool,
) -> int:
    batch_max_i = max(1, int(base_batch_max))
    if in_process_queues and not batch_max_overridden:
        # Keep owner turns broad enough to drain local producer bursts without
        # widening the turn so far that same-song downstream readiness gets
        # buried behind unrelated in-process work.
        batch_max_i = max(batch_max_i, 24)
    return int(batch_max_i)


@dataclass(frozen=True)
class BatchPlan:
    """Batch gather decision metadata for one executor loop."""

    wait_ms: int
    max_batch: int
    mode: str
    queue_depth_hint: int
    pressure_hint: float


@dataclass(frozen=True)
class LoopBatchSettings:
    wait_ms: int
    max_batch: int
    wait_overridden: bool
    max_overridden: bool
    fg_burst_window_ms: int
    fg_burst_wait_ms: int


@dataclass(frozen=True)
class InProcessCoalesceSettings:
    enabled: bool
    idle_wait_s: float
    recent_idle_wait_s: float
    recent_idle_grace_s: float
    yields_left: int
    after_first_ms: int


def _int_value(value: Any, *, fallback: int) -> int:
    try:
        return int(str(value).strip())
    except (ValueError, TypeError, AttributeError):
        return int(fallback)


def _env_override_int(env_get: Callable[..., Any], name: str) -> tuple[int | None, bool]:
    try:
        raw = env_get(name)
    except (ValueError, TypeError):
        return None, False
    if raw is None or str(raw).strip() == "":
        return None, False
    try:
        return int(str(raw).strip()), True
    except (ValueError, TypeError):
        return None, False


def load_loop_batch_settings(
    *,
    env_config: Any,
    env_get: Callable[..., Any],
) -> LoopBatchSettings:
    wait_ms = _int_value(getattr(env_config, "gpu_executor_batch_wait_ms", 10) or 10, fallback=10)
    max_batch = _int_value(getattr(env_config, "gpu_executor_max_batch", 8) or 8, fallback=8)
    wait_overridden = False
    max_overridden = False

    override, ok = _env_override_int(env_get, "GPU_EXECUTOR_BATCH_WAIT_MS")
    if ok and override is not None:
        wait_ms = int(override)
        wait_overridden = True

    override, ok = _env_override_int(env_get, "GPU_EXECUTOR_MAX_BATCH")
    if ok and override is not None:
        max_batch = int(override)
        max_overridden = True

    burst_window, ok = _env_override_int(env_get, "GPU_EXECUTOR_FG_BURST_WINDOW_MS")
    fg_burst_window_ms = int(burst_window) if ok and burst_window is not None else 6
    fg_burst_window_ms = max(0, int(fg_burst_window_ms))

    burst_wait, ok = _env_override_int(env_get, "GPU_EXECUTOR_FG_BURST_BATCH_WAIT_MS")
    fg_burst_wait_ms = int(burst_wait) if ok and burst_wait is not None else 2
    fg_burst_wait_ms = max(0, min(int(fg_burst_wait_ms), 10))

    return LoopBatchSettings(
        wait_ms=int(wait_ms),
        max_batch=int(max_batch),
        wait_overridden=bool(wait_overridden),
        max_overridden=bool(max_overridden),
        fg_burst_window_ms=int(fg_burst_window_ms),
        fg_burst_wait_ms=int(fg_burst_wait_ms),
    )


def plan_loop_batch(
    settings: LoopBatchSettings,
    *,
    in_process_queues: bool,
    queue_depth_hint: int,
    fg_burst_active: bool,
) -> BatchPlan:
    batch_wait_ms = int(settings.wait_ms)
    batch_max = int(settings.max_batch)

    if bool(in_process_queues):
        batch_max = effective_owner_batch_max(
            int(batch_max),
            in_process_queues=True,
            batch_max_overridden=bool(settings.max_overridden),
        )
        if not bool(settings.wait_overridden):
            batch_wait_ms = min(int(batch_wait_ms), 6)
            if bool(fg_burst_active):
                batch_wait_ms = min(int(batch_wait_ms), int(settings.fg_burst_wait_ms))

    if batch_wait_ms < 0:
        batch_wait_ms = 0
    if batch_max <= 0:
        batch_max = 1

    pressure_hint = (
        (float(queue_depth_hint) / float(batch_max))
        if int(queue_depth_hint) >= 0 and int(batch_max) > 0
        else 0.0
    )
    if pressure_hint >= 1.0:
        batch_wait_ms = 0

    planner_mode = "fg_burst" if bool(fg_burst_active) else ("inproc" if bool(in_process_queues) else "static")

    return BatchPlan(
        wait_ms=int(batch_wait_ms),
        max_batch=int(batch_max),
        mode=str(planner_mode),
        queue_depth_hint=int(queue_depth_hint),
        pressure_hint=float(max(0.0, pressure_hint)),
    )


def batch_contains_fg_burst_work(
    batch: list[Any],
    *,
    request_types: frozenset[GpuRequestType] = FG_BURST_REQUEST_TYPES,
) -> bool:
    for request in batch or []:
        request_type = getattr(request, "request_type", None)
        if request_type == GpuRequestType.SHUTDOWN:
            continue
        if request_type in request_types:
            return True
    return False


def next_fg_burst_until(
    current_until_s: float,
    *,
    saw_fg_work: bool,
    in_process_queues: bool,
    window_ms: int,
    now_s: float,
) -> float:
    if not bool(saw_fg_work):
        return float(current_until_s)
    if not bool(in_process_queues):
        return float(current_until_s)
    if int(window_ms) <= 0:
        return float(current_until_s)
    next_until = float(now_s) + (float(window_ms) / 1000.0)
    return max(float(current_until_s), float(next_until))


def _env_ms_as_seconds(
    env_get: Callable[..., Any],
    name: str,
    default_ms: str,
    *,
    fallback_s: float,
    min_s: float,
    max_s: float,
) -> float:
    try:
        raw_ms = env_get(name, default_ms)
        value_s = float(str(raw_ms).strip()) / 1000.0
    except (ValueError, TypeError):
        value_s = float(fallback_s)
    return max(float(min_s), min(float(value_s), float(max_s)))


def _env_int(env_get: Callable[..., Any], name: str, default: str | None, *, fallback: int) -> int:
    try:
        raw = env_get(name, default) if default is not None else env_get(name)
        return int(str(raw).strip())
    except (ValueError, TypeError):
        return int(fallback)


def ga_recovery_streak_cap(*, env_get: Callable[..., Any]) -> int:
    raw = _env_int(
        env_get,
        "GPU_EXECUTOR_GA_RECOVERY_STREAK_MAX",
        "1",
        fallback=1,
    )
    return max(1, min(int(raw), 128))


def ga_recovery_lookahead_limit(*, batch_max_size: int, env_get: Callable[..., Any]) -> int:
    default_limit = max(8, min(max(1, int(batch_max_size)) * 4, 64))
    raw = _env_int(
        env_get,
        "GPU_EXECUTOR_GA_RECOVERY_LOOKAHEAD_MAX_REQS",
        str(default_limit),
        fallback=default_limit,
    )
    return max(1, min(int(raw), 256))


def load_inprocess_coalesce_settings(
    *,
    max_wait_ms: int,
    in_process_queues: bool,
    env_get: Callable[..., Any],
    env_flag_fn: Callable[[str, str], bool],
) -> InProcessCoalesceSettings:
    max_wait_ms_i = int(max_wait_ms)
    enabled = bool(env_flag_fn("GPU_EXECUTOR_INPROC_COALESCE", "1"))
    idle_wait_s = 0.1
    recent_idle_wait_s = 0.0
    recent_idle_grace_s = 0.0
    yields_left = 0

    if in_process_queues:
        idle_wait_s = _env_ms_as_seconds(
            env_get,
            "GPU_EXECUTOR_INPROC_IDLE_WAIT_MS",
            "100",
            fallback_s=0.1,
            min_s=0.0,
            max_s=1.0,
        )
        recent_idle_wait_s = _env_ms_as_seconds(
            env_get,
            "GPU_EXECUTOR_INPROC_IDLE_RECENT_WAIT_MS",
            "10",
            fallback_s=0.01,
            min_s=0.0,
            max_s=idle_wait_s,
        )
        recent_idle_grace_s = _env_ms_as_seconds(
            env_get,
            "GPU_EXECUTOR_INPROC_IDLE_RECENT_GRACE_MS",
            "250",
            fallback_s=0.25,
            min_s=0.0,
            max_s=5.0,
        )
        default_yields = max(0, min(64, max_wait_ms_i))
        raw_yields = env_get("GPU_EXECUTOR_INPROC_COALESCE_YIELD_ROUNDS")
        if raw_yields is None or str(raw_yields).strip() == "":
            yields_left = default_yields
        else:
            yields_left = _env_int(
                env_get,
                "GPU_EXECUTOR_INPROC_COALESCE_YIELD_ROUNDS",
                None,
                fallback=default_yields,
            )
        yields_left = max(0, min(int(yields_left), 256))

    after_first_ms = _env_int(
        env_get,
        "GPU_EXECUTOR_INPROC_COALESCE_AFTER_FIRST_MS",
        "2",
        fallback=0,
    )
    after_first_ms = max(0, int(after_first_ms))
    if max_wait_ms_i <= 0:
        after_first_ms = 0

    return InProcessCoalesceSettings(
        enabled=enabled,
        idle_wait_s=float(idle_wait_s),
        recent_idle_wait_s=float(recent_idle_wait_s),
        recent_idle_grace_s=float(recent_idle_grace_s),
        yields_left=int(yields_left),
        after_first_ms=int(after_first_ms),
    )


def batch_allows_coalesce(batch: list[Any], *, coalescable_request_types: frozenset[GpuRequestType]) -> bool:
    for request in batch or []:
        request_type = getattr(request, "request_type", None)
        if request_type == GpuRequestType.SHUTDOWN:
            continue
        if request_type not in coalescable_request_types:
            return False
    return True


def select_inprocess_batch_timeout(
    batch: list[Any],
    *,
    max_wait_ms: int,
    remaining_s: float,
    settings: InProcessCoalesceSettings,
    last_work_end_ts: float | None,
    now_s: float | None,
    coalescable_request_types: frozenset[GpuRequestType],
) -> float:
    if not batch:
        if float(settings.idle_wait_s) > 0.0:
            timeout = float(settings.idle_wait_s)
            if (
                last_work_end_ts is not None
                and now_s is not None
                and float(settings.recent_idle_wait_s) > 0.0
                and float(settings.recent_idle_grace_s) > 0.0
                and (float(now_s) - float(last_work_end_ts)) <= float(settings.recent_idle_grace_s)
            ):
                timeout = min(float(timeout), float(settings.recent_idle_wait_s))
            return float(timeout)
        return 0.0 if int(max_wait_ms) <= 0 else max(0.0, float(remaining_s))

    if not bool(settings.enabled):
        return 0.0
    if int(max_wait_ms) <= 0:
        return 0.0
    if not batch_allows_coalesce(batch, coalescable_request_types=coalescable_request_types):
        return 0.0
    return max(0.0, float(remaining_s))


def extend_inprocess_after_first_deadline(
    deadline_s: float,
    *,
    in_process_queues: bool,
    settings: InProcessCoalesceSettings,
    batch_size: int,
    request_type: GpuRequestType,
    coalescable_request_types: frozenset[GpuRequestType],
    now_fn: Callable[[], float],
) -> float:
    if not in_process_queues:
        return float(deadline_s)
    if not bool(settings.enabled):
        return float(deadline_s)
    if int(batch_size) != 1:
        return float(deadline_s)
    if int(settings.after_first_ms) <= 0:
        return float(deadline_s)
    if request_type not in coalescable_request_types:
        return float(deadline_s)
    return max(float(deadline_s), float(now_fn()) + (float(settings.after_first_ms) / 1000.0))

# ---- merged from gpu_executor_dispatch.py ----
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
import logging
import queue
import time

from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType, GpuResponse

logger = logging.getLogger(__name__)


FG_REQUEST_TYPES = frozenset(
    {
        GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
        GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS,
        GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH,
        GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS,
        GpuRequestType.FG_RESET_GLOBAL_BEST,
        GpuRequestType.FG_DOWNLOAD_GLOBAL_BEST,
        GpuRequestType.FG_SELECT_SIGNATURE_FRONTIER_BATCH,
        GpuRequestType.FG_COMPUTE_BREAKPOINTS,
    }
)

GA_RECOVERY_REQUEST_TYPES = frozenset(FG_REQUEST_TYPES)

COALESCABLE_REQUEST_TYPES = frozenset(
    {
        GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
        GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS,
        GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH,
        GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS,
    }
)

NO_BATCH_REQUEST_TYPES = frozenset({GpuRequestType.GPU_NATIVE_GA_RUN})
NO_BATCH_REQUEST_TYPE_VALUES = frozenset({str(rt.value) for rt in NO_BATCH_REQUEST_TYPES})
GA_RECOVERY_REQUEST_TYPE_VALUES = frozenset({str(rt.value) for rt in GA_RECOVERY_REQUEST_TYPES})


def request_type_in(request_type: Any, request_types: frozenset[GpuRequestType], request_type_values: frozenset[str]) -> bool:
    if request_type in request_types:
        return True
    try:
        value = str(getattr(request_type, "value", request_type))
    except (AttributeError, TypeError):
        value = ""
    return value in request_type_values


def is_no_batch_request_type(request_type: Any) -> bool:
    return request_type_in(request_type, NO_BATCH_REQUEST_TYPES, NO_BATCH_REQUEST_TYPE_VALUES)


def is_ga_recovery_request_type(request_type: Any) -> bool:
    return request_type_in(request_type, GA_RECOVERY_REQUEST_TYPES, GA_RECOVERY_REQUEST_TYPE_VALUES)


def is_ga_recovery_request(request: Any) -> bool:
    return is_ga_recovery_request_type(getattr(request, "request_type", None))


@dataclass(frozen=True)
class GpuExecutionUnit:
    request_type: GpuRequestType
    requests: tuple[GpuRequest, ...]
    grouped: bool


def execute_request_from_dispatch(
    request: GpuRequest,
    *,
    dispatch: Mapping[Any, Callable[[GpuRequest], GpuResponse]],
) -> GpuResponse:
    req_type = getattr(request, "request_type", None)
    request_id = int(getattr(request, "request_id", 0) or 0)
    if req_type == GpuRequestType.SHUTDOWN:
        return GpuResponse(request_id=request_id, success=True, result=None)

    handler = dispatch.get(req_type)
    if handler is None:
        return GpuResponse(
            request_id=request_id,
            success=False,
            error=f"Unsupported GPU request type: {req_type!r}",
        )

    try:
        return handler(request)
    except Exception as exc:
        return GpuResponse(
            request_id=request_id,
            success=False,
            error=f"GpuExecutor error: {type(exc).__name__}: {exc}",
        )


def plan_execution_units(
    batch: list[GpuRequest],
    *,
    grouped_request_types: set[GpuRequestType],
) -> list[GpuExecutionUnit]:
    execution_units: list[GpuExecutionUnit] = []
    for req in batch:
        request_type = req.request_type
        if request_type in grouped_request_types:
            if (
                execution_units
                and execution_units[-1].grouped
                and execution_units[-1].request_type == request_type
            ):
                prev = execution_units[-1]
                execution_units[-1] = GpuExecutionUnit(
                    request_type=prev.request_type,
                    requests=(*prev.requests, req),
                    grouped=True,
                )
            else:
                execution_units.append(
                    GpuExecutionUnit(
                        request_type=request_type,
                        requests=(req,),
                        grouped=True,
                    )
                )
        else:
            execution_units.append(
                GpuExecutionUnit(
                    request_type=request_type,
                    requests=(req,),
                    grouped=False,
                )
            )
    return execution_units


def order_responses_for_requests(
    requests: list[GpuRequest],
    responses: Any,
) -> list[GpuResponse | None]:
    by_id: dict[int, GpuResponse] = {}
    for response in responses or []:
        if response is None:
            continue
        try:
            by_id[int(response.request_id)] = response
        except (ValueError, TypeError, AttributeError):
            continue
    return [by_id.get(int(req.request_id)) for req in requests]


class ResponseDeliveryTracker:
    def __init__(self) -> None:
        self.failures_total = 0
        self.failures_by_worker = defaultdict(int)
        self.last_warn_monotonic = 0.0

    def reset(self) -> None:
        self.failures_total = 0
        self.failures_by_worker.clear()
        self.last_warn_monotonic = 0.0

    def try_put(
        self,
        response_queues: dict[int, Any],
        request: GpuRequest,
        response: GpuResponse,
    ) -> bool:
        try:
            q = response_queues.get(request.worker_id)
            if q is None:
                return False
            put_nowait = getattr(q, "put_nowait", None)
            if callable(put_nowait):
                put_nowait(response)
            else:
                q.put(response, block=False)
            return True
        except queue.Full:
            self._record_failure(request, "Response queue full; dropping response")
            return False
        except Exception as e:
            logger.debug(f"gpu_executor_dispatch:try_put: {e}")
            self._record_failure(request, "Failed to deliver response")
            return False

    def _record_failure(self, request: GpuRequest, message: str) -> None:
        try:
            self.failures_total += 1
            self.failures_by_worker[int(request.worker_id)] += 1
            now = time.monotonic()
            if (now - float(self.last_warn_monotonic or 0.0)) < 5.0:
                return
            self.last_warn_monotonic = now
            logger.warning(
                "[GpuExecutor] %s (worker_id=%s request_id=%s type=%s total_failures=%s)",
                str(message),
                int(request.worker_id),
                int(getattr(request, "request_id", 0) or 0),
                str(getattr(getattr(request, "request_type", None), "value", "") or ""),
                int(self.failures_total),
            )
        except Exception as e:
            logger.debug(f"gpu_executor_dispatch:_record_failure: {e}")

# ---- merged from gpu_executor_native_ga.py ----
"""GPU executor handler for native GA requests."""


def execute_gpu_native_ga_run(
    request: GpuRequest,
    *,
    in_process_queues: bool,
    abort_requested: Callable[[], bool],
    raise_if_abort_requested: Callable[[], None],
    run_payload_fn: Callable[..., Any] | None = None,
) -> GpuResponse:
    if not bool(in_process_queues):
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error="GPU_NATIVE_GA_RUN requires in-process queues (avoid IPC pickling)",
        )

    try:
        raise_if_abort_requested()
    except Exception as e:
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error=str(e),
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
        if run_payload_fn is None:
            from gear_optimizer.solver.genetic_pipeline import run_gpu_native_ga_runs_payload_prebuilt as run_payload_fn

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
            elite_count=elite_count,
            mutation_rate=mutation_rate,
            immigrant_rate=immigrant_rate,
            tournament_k=tournament_k,
            color_flags=dict(color_flags),
            cfg_data=dict(cfg_data),
            ga_seed=int(ga_seed) if ga_seed is not None else None,
            abort_requested=abort_requested,
        )
        if n_genomes is not None:
            kwargs["n_genomes"] = int(n_genomes)
        runs_payload = run_payload_fn(**kwargs)
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

# ---- merged from gpu_executor_native_ga_batch.py ----
from dataclasses import dataclass

from gear_optimizer.core.parsing import env_get


@dataclass(frozen=True)
class NativeGaBatchLimits:
    max_reqs: int
    max_work_units: float


def load_native_ga_batch_limits(
    *,
    env_get_fn: Callable[[str, Any], Any] = env_get,
) -> NativeGaBatchLimits:
    try:
        max_reqs = int(env_get_fn("GPU_NATIVE_GA_BATCH_COALESCE_MAX_REQS", "1") or "1")
    except (ValueError, TypeError):
        max_reqs = 1
    max_reqs = max(1, min(int(max_reqs), 128))

    try:
        max_work_units = float(env_get_fn("GPU_NATIVE_GA_BATCH_COALESCE_MAX_WORK_UNITS", "720000") or "720000")
    except (ValueError, TypeError):
        max_work_units = 720000.0
    if max_work_units <= 0.0:
        max_work_units = float("inf")

    return NativeGaBatchLimits(max_reqs=int(max_reqs), max_work_units=float(max_work_units))


def plan_native_ga_batch_chunks(
    requests: list[GpuRequest],
    *,
    limits: NativeGaBatchLimits,
    estimate_work_units_fn: Callable[[GpuRequest], float],
) -> list[list[GpuRequest]]:
    chunks: list[list[GpuRequest]] = []
    chunk: list[GpuRequest] = []
    chunk_units = 0.0

    for req in requests:
        req_units = max(1.0, float(estimate_work_units_fn(req)))
        if chunk and (
            len(chunk) >= int(limits.max_reqs)
            or (float(chunk_units) + float(req_units)) > float(limits.max_work_units)
        ):
            chunks.append(chunk)
            chunk = []
            chunk_units = 0.0
        chunk.append(req)
        chunk_units += float(req_units)

    if chunk:
        chunks.append(chunk)
    return chunks


def execute_gpu_native_ga_run_chunk(
    requests: list[GpuRequest],
    *,
    abort_requested: Callable[[], bool],
    aborted_response: Callable[[GpuRequest], GpuResponse],
    execute_single: Callable[[GpuRequest], GpuResponse],
) -> list[GpuResponse]:
    if not requests:
        return []
    out: list[GpuResponse] = []
    for idx, req in enumerate(requests):
        if abort_requested():
            out.extend(aborted_response(pending_req) for pending_req in requests[idx:])
            break
        out.append(execute_single(req))
    return out


def execute_gpu_native_ga_run_batch(
    requests: list[GpuRequest],
    *,
    abort_requested: Callable[[], bool],
    aborted_response: Callable[[GpuRequest], GpuResponse],
    execute_single: Callable[[GpuRequest], GpuResponse],
    execute_chunk: Callable[[list[GpuRequest]], list[GpuResponse]],
    env_get_fn: Callable[[str, Any], Any] = env_get,
    estimate_work_units_fn: Callable[[GpuRequest], float],
) -> list[GpuResponse]:
    if not requests:
        return []
    if len(requests) == 1:
        return [execute_single(requests[0])]

    out: list[GpuResponse] = []
    chunks = plan_native_ga_batch_chunks(
        requests,
        limits=load_native_ga_batch_limits(env_get_fn=env_get_fn),
        estimate_work_units_fn=estimate_work_units_fn,
    )
    for chunk_idx, chunk in enumerate(chunks):
        if abort_requested():
            pending = [pending_req for pending_chunk in chunks[chunk_idx:] for pending_req in pending_chunk]
            out.extend(aborted_response(pending_req) for pending_req in pending)
            return out
        out.extend(execute_chunk(chunk))
        if abort_requested():
            pending = [pending_req for pending_chunk in chunks[chunk_idx + 1 :] for pending_req in pending_chunk]
            out.extend(aborted_response(pending_req) for pending_req in pending)
            return out

    return out

# ---- merged from gpu_executor_fused_coalesce.py ----
from dataclasses import dataclass

from gear_optimizer.solver.gpu_executor_types import GpuRequestType


@dataclass(frozen=True)
class GaFgFusedCoalescePlan:
    synthetic_batch_requests: list[GpuRequest]
    fallback_reason_by_id: dict[int, str]


def build_ga_fg_fused_batch_requests(requests: list[GpuRequest]) -> GaFgFusedCoalescePlan:
    synthetic_batch_requests: list[GpuRequest] = []
    fallback_reason_by_id: dict[int, str] = {}

    for req in requests:
        payload = req.payload
        if not isinstance(payload, dict):
            fallback_reason_by_id.setdefault(int(req.request_id), "invalid request payload type")
            continue
        synthetic_batch_requests.append(
            GpuRequest(
                request_type=GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH,
                request_id=int(req.request_id),
                worker_id=int(req.worker_id),
                payload={"payloads": [payload]},
            )
        )

    return GaFgFusedCoalescePlan(
        synthetic_batch_requests=synthetic_batch_requests,
        fallback_reason_by_id=fallback_reason_by_id,
    )


def unwrap_ga_fg_fused_batch_response(req: GpuRequest, resp: GpuResponse | None) -> tuple[GpuResponse | None, str | None]:
    if resp is None:
        return None, "missing coalesced response"
    if not bool(getattr(resp, "success", False)):
        return None, "coalesced response unsuccessful"
    result = getattr(resp, "result", None)
    if not isinstance(result, list) or len(result) != 1:
        return None, "unexpected coalesced result shape"
    return (
        GpuResponse(
            request_id=int(req.request_id),
            success=True,
            result=result[0],
        ),
        None,
    )


def coalesce_ga_fg_fused_requests(
    requests: list[GpuRequest],
    *,
    in_process_queues: bool,
    execute_request: Callable[[GpuRequest], GpuResponse],
    coalesce_fg_breakpoint_batch: Callable[[list[GpuRequest]], list[GpuResponse]],
    warn_fallback_fn: Callable[..., None],
) -> list[GpuResponse]:
    if not requests:
        return []
    if not bool(in_process_queues) or len(requests) <= 1:
        return [execute_request(req) for req in requests]

    plan = build_ga_fg_fused_batch_requests(requests)
    synthetic_batch_requests = plan.synthetic_batch_requests
    fallback_ids: set[int] = set(plan.fallback_reason_by_id)
    fallback_reason_by_id: dict[int, str] = dict(plan.fallback_reason_by_id)

    def _mark_fallback(req_id: int, reason: str) -> None:
        rid = int(req_id)
        fallback_ids.add(rid)
        if rid not in fallback_reason_by_id:
            fallback_reason_by_id[rid] = str(reason)

    out: list[GpuResponse] = []
    if synthetic_batch_requests:
        batch_responses = coalesce_fg_breakpoint_batch(synthetic_batch_requests)
        for req, resp in zip(synthetic_batch_requests, batch_responses):
            unwrapped, fallback_reason = unwrap_ga_fg_fused_batch_response(req, resp)
            if fallback_reason is not None:
                _mark_fallback(int(req.request_id), fallback_reason)
                continue
            out.append(unwrapped)

    if fallback_ids:
        for req in requests:
            if int(req.request_id) in fallback_ids:
                warn_fallback_fn(
                    "gpu_executor.ga_fg_fused_coalesce.request",
                    "coalesced fused request fallback to per-request execution",
                    context={
                        "request_id": int(req.request_id),
                        "reason": fallback_reason_by_id.get(int(req.request_id), "unknown"),
                    },
                )
                out.append(execute_request(req))

    return order_responses_for_requests(requests, out)
