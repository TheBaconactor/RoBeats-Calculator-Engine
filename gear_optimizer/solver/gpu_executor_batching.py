from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from gear_optimizer.core.profile_events import emit_profile_event, profile_events_active
from gear_optimizer.solver.gpu_executor_types import GpuRequestType


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


def load_loop_batch_settings(
    *,
    env_config: Any,
    env_get: Callable[..., Any],
) -> LoopBatchSettings:
    # GPU-owner loop batch base is hardwired (was GPU_EXECUTOR_BATCH_WAIT_MS /
    # GPU_EXECUTOR_MAX_BATCH overrides). *_overridden stay False so the downstream
    # effective-owner-batch widening always applies, as in production-no-override.
    wait_ms = _int_value(getattr(env_config, "gpu_executor_batch_wait_ms", 10) or 10, fallback=10)
    max_batch = _int_value(getattr(env_config, "gpu_executor_max_batch", 8) or 8, fallback=8)

    return LoopBatchSettings(
        wait_ms=int(wait_ms),
        max_batch=int(max_batch),
        wait_overridden=False,
        max_overridden=False,
    )


def plan_loop_batch(
    settings: LoopBatchSettings,
    *,
    in_process_queues: bool,
    queue_depth_hint: int,
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

    planner_mode = "inproc" if bool(in_process_queues) else "static"

    return BatchPlan(
        wait_ms=int(batch_wait_ms),
        max_batch=int(batch_max),
        mode=str(planner_mode),
        queue_depth_hint=int(queue_depth_hint),
        pressure_hint=float(max(0.0, pressure_hint)),
    )


def ga_recovery_streak_cap(*, env_get: Callable[..., Any]) -> int:
    # Hardwired to the most FG-protective value (was GPU_EXECUTOR_GA_RECOVERY_STREAK_MAX=1).
    return 1


def ga_recovery_lookahead_limit(*, batch_max_size: int, env_get: Callable[..., Any]) -> int:
    # Hardwired to the batch-size-derived default (was GPU_EXECUTOR_GA_RECOVERY_LOOKAHEAD_MAX_REQS).
    return max(8, min(max(1, int(batch_max_size)) * 4, 64))


def load_inprocess_coalesce_settings(
    *,
    max_wait_ms: int,
    in_process_queues: bool,
    env_get: Callable[..., Any],
    env_flag_fn: Callable[[str, str], bool],
) -> InProcessCoalesceSettings:
    # Hardwired in-proc coalesce tuning (was GPU_EXECUTOR_INPROC_COALESCE +
    # _IDLE_WAIT_MS=100 / _IDLE_RECENT_WAIT_MS=10 / _IDLE_RECENT_GRACE_MS=250 /
    # _COALESCE_YIELD_ROUNDS / _COALESCE_AFTER_FIRST_MS=2). Yield rounds stay
    # derived from max_wait_ms; after_first_ms drops to 0 when batching is off.
    max_wait_ms_i = int(max_wait_ms)
    enabled = True
    idle_wait_s = 0.1
    recent_idle_wait_s = 0.0
    recent_idle_grace_s = 0.0
    yields_left = 0

    if in_process_queues:
        idle_wait_s = 0.1
        recent_idle_wait_s = 0.01
        recent_idle_grace_s = 0.25
        yields_left = max(0, min(64, max_wait_ms_i))

    after_first_ms = 2
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

from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuResponse

logger = logging.getLogger(__name__)


GA_RECOVERY_REQUEST_TYPES = frozenset()

COALESCABLE_REQUEST_TYPES = frozenset({GpuRequestType.GPU_NATIVE_GA_RUN})

GA_RECOVERY_REQUEST_TYPE_VALUES = frozenset({str(rt.value) for rt in GA_RECOVERY_REQUEST_TYPES})


def request_type_in(request_type: Any, request_types: frozenset[GpuRequestType], request_type_values: frozenset[str]) -> bool:
    if request_type in request_types:
        return True
    try:
        value = str(getattr(request_type, "value", request_type))
    except (AttributeError, TypeError):
        value = ""
    return value in request_type_values


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
    fused_fg_fn: Callable[..., Any] | None = None,
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
    fg_gear_name_rank = payload.get("fg_gear_name_rank")
    fg_mini_sig_id = payload.get("fg_mini_sig_id")
    fg_scoring_bundle = payload.get("fg_scoring_bundle")
    fg_calc_song = payload.get("fg_calc_song")

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
            fg_gear_name_rank=fg_gear_name_rank,
            fg_mini_sig_id=fg_mini_sig_id,
            abort_requested=abort_requested,
        )
        if n_genomes is not None:
            kwargs["n_genomes"] = int(n_genomes)

        # Gated owner-thread phase profiling for the fused GA->FG continuation
        # (docs/research/GPU_FUSED_FG_OWNER_GAP_REVIEW_REQUEST_20260613.md). OFF
        # unless METAFINDER_PROFILE_EVENTS_PATH is set; pure measurement, no behavior change.
        _prof = profile_events_active()
        _prof_song_key = ""
        if _prof and isinstance(calc_song, dict):
            _prof_song_key = f"{calc_song.get('Song_Name', '')}|{calc_song.get('Difficulty', '')}"

        _t_ga = time.perf_counter() if _prof else 0.0
        runs_payload = run_payload_fn(**kwargs)
        if _prof:
            emit_profile_event(
                component="fg_fused",
                event="fg_owner_phase",
                song_key=_prof_song_key,
                metrics={"phase": "ga_run_total", "total_ms": (time.perf_counter() - _t_ga) * 1000.0},
            )

        # FUSED GA->FG owner continuation (Slice 3): immediately after the GA
        # pack/select, on the SAME owner thread, score FG straight from the selected
        # payload's device base_stats7 and hand a compact per-base_components result
        # map back with the payload. The driver materializes it off the owner's
        # critical path. This replaces the per-song decode->FG-prep->BUILD->SCORE
        # driver round-trip (the fg_owner_queue) with one fused owner turn.
        if fused_fg_fn is None:
            from gear_optimizer.solver.genetic_pipeline import (
                score_fused_fg_from_selected_payload as fused_fg_fn,
            )

        _t_fg = time.perf_counter() if _prof else 0.0
        fg_owner_score = fused_fg_fn(
            runs_payload=runs_payload,
            fg_scoring_bundle=fg_scoring_bundle,
            fg_calc_song=fg_calc_song,
            ref_arrays=ref_arrays,
            cfg_data=dict(cfg_data),
        )
        if _prof:
            emit_profile_event(
                component="fg_fused",
                event="fg_owner_phase",
                song_key=_prof_song_key,
                metrics={"phase": "fg_block_total", "total_ms": (time.perf_counter() - _t_fg) * 1000.0},
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
        result={"runs_payload": runs_payload, "fg_owner_score": fg_owner_score},
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
    # Hardwired (was GPU_NATIVE_GA_BATCH_COALESCE_MAX_REQS=2 / _MAX_WORK_UNITS=240000).
    # The per-dispatch work-unit cap is a GPU TDR / oversized-submit safety bound -- baked
    # and always active (the former 0=unbounded override is removed).
    return NativeGaBatchLimits(max_reqs=2, max_work_units=240000.0)


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
