from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

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


COALESCABLE_REQUEST_TYPES = frozenset({GpuRequestType.EXACT_BASE_SEARCH})


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

# ---- exact Base + native FG owner turn ----
def execute_exact_base_search(
    request: GpuRequest,
    *,
    in_process_queues: bool,
    abort_requested: Callable[[], bool],
    raise_if_abort_requested: Callable[[], None],
    run_pipeline_fn: Callable[..., Any] | None = None,
    score_fg_fn: Callable[..., Any] | None = None,
) -> GpuResponse:
    if not bool(in_process_queues):
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error="EXACT_BASE_SEARCH requires in-process queues (typed payload is not IPC-safe)",
        )

    try:
        raise_if_abort_requested()
    except Exception as e:
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error=str(e),
        )

    payload = request.payload if isinstance(request.payload, dict) else {}
    context = payload.get("context")
    domains = payload.get("domains")
    song_context = payload.get("song_context")
    timeline_frontier = payload.get("timeline_frontier")
    candidate_limit = payload.get("candidate_limit")
    fg_scoring_bundle = payload.get("fg_scoring_bundle")
    fg_calc_song = payload.get("fg_calc_song")

    from gear_optimizer.solver.exact_base_domains import ExactBaseDomains
    from gear_optimizer.solver.exact_base_song_context import ExactBaseSongContext
    from gear_optimizer.solver.solver_common import SolverContext
    from gear_optimizer.solver.taichi_gem.api.timeline import TimelineFrontierPrewarmResult

    invalid = []
    if not isinstance(context, SolverContext):
        invalid.append("context")
    if not isinstance(domains, ExactBaseDomains):
        invalid.append("domains")
    if not isinstance(song_context, ExactBaseSongContext):
        invalid.append("song_context")
    if not isinstance(timeline_frontier, TimelineFrontierPrewarmResult):
        invalid.append("timeline_frontier")
    if fg_scoring_bundle is None:
        invalid.append("fg_scoring_bundle")
    if not isinstance(fg_calc_song, dict):
        invalid.append("fg_calc_song")
    try:
        candidate_limit_i = int(candidate_limit)
    except (TypeError, ValueError):
        candidate_limit_i = 0
    if candidate_limit_i <= 0:
        invalid.append("candidate_limit")
    if invalid:
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error=f"Invalid payload for EXACT_BASE_SEARCH: {', '.join(invalid)}",
        )

    try:
        if run_pipeline_fn is None:
            from gear_optimizer.solver.exact_base_search import (
                run_exact_base_pipeline as run_pipeline_fn,
            )
        if score_fg_fn is None:
            from gear_optimizer.solver.native_fg_owner import (
                score_native_fg_candidate_surface as score_fg_fn,
            )

        base = run_pipeline_fn(
            context,
            domains=domains,
            song_context=song_context,
            timeline_frontier=timeline_frontier,
            candidate_limit=candidate_limit_i,
            abort_requested=abort_requested,
        )
        raise_if_abort_requested()
        fg_owner_score = score_fg_fn(
            base_stats7=base.candidate_surface.base_stats7,
            context=context,
            scoring_bundle=fg_scoring_bundle,
            calc_song=fg_calc_song,
        )
        from gear_optimizer.solver.native_fg_owner import ExactBaseOwnerResult

        result = ExactBaseOwnerResult(base_result=base, fg_owner_score=fg_owner_score)
    except Exception as e:
        return GpuResponse(
            request_id=request.request_id,
            success=False,
            error=f"{type(e).__name__}: {e}",
        )

    return GpuResponse(
        request_id=request.request_id,
        success=True,
        result=result,
    )
