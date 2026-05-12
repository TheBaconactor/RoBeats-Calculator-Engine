from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from gear_optimizer.solver.gpu_executor_types import GpuRequestType


FG_BURST_REQUEST_TYPES = frozenset(
    {
        GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
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
