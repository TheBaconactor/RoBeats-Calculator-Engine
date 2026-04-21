from __future__ import annotations

import os
from typing import Any

from gear_optimizer.core.utils import safe_float, safe_int
from gear_optimizer.solver.inflight_utils import _truthy


def _default_prime_target(*, inflight_limit: int, prep_limit: int, pending_count: int) -> int:
    """
    Pick a startup prep backlog large enough to avoid the first GA/FG feed bubble.

    For smaller in-flight runs, priming only `inflight_limit` songs tends to leave the
    GPU queue shallow while prep/decode workers are still spinning up. We bias toward
    a modest 4-8 song startup backlog, but always cap by the prep buffer and pending queue.
    """
    try:
        inflight_limit = int(inflight_limit)
    except Exception:
        inflight_limit = 1
    try:
        prep_limit = int(prep_limit)
    except Exception:
        prep_limit = 1
    try:
        pending_count = int(pending_count)
    except Exception:
        pending_count = 0

    inflight_limit = max(1, inflight_limit)
    prep_limit = max(1, prep_limit)
    pending_count = max(0, pending_count)
    if pending_count <= 0:
        return 0

    target = max(inflight_limit, min(8, max(4, inflight_limit * 2)))
    return max(1, min(target, prep_limit, pending_count))


def _read_fg_scheduler_mode() -> str:
    """
    In-flight scheduler is intentionally fixed to continuous mode.

    We removed backlog/drain scheduler options to keep runtime behavior
    deterministic and easier to reason about.
    """
    return "continuous"


def _read_fg_ga_credit_budget(cfg0: Any, *, default_budget: int) -> tuple[int, bool]:
    """
    GA-credit budget used by continuous FG scheduler.

    Returns: (budget, explicit)
    - budget: effective positive integer
    - explicit: True when user explicitly set the budget (config/env), False when defaulted
    """
    budget = max(1, int(default_budget))
    explicit = False

    try:
        if cfg0 is not None:
            if cfg0.has_option("IterationEngine", "InFlight_FGGACreditBudget"):
                budget = safe_int(
                    cfg0.get("IterationEngine", "InFlight_FGGACreditBudget", fallback=str(budget)),
                    budget,
                )
                explicit = True
    except Exception:
        pass

    raw = os.environ.get("INFLIGHT_FG_GA_CREDIT_BUDGET")
    if raw is not None and str(raw).strip() != "":
        try:
            budget = int(raw)
            explicit = True
        except Exception:
            pass

    return max(1, int(budget)), bool(explicit)


def _read_continuous_ga_dispatch_burst(cfg0: Any, *, default_burst: int = 2) -> int:
    """
    Max GA submissions per scheduler cycle when continuous GA/FG interleaving is active.

    Lower values reduce GA burstiness and give FG more frequent chances to submit,
    which smooths GPU utilization without changing GA/FG scoring behavior.
    """
    burst = max(1, int(default_burst))
    try:
        if cfg0 is not None and cfg0.has_option("IterationEngine", "InFlight_ContinuousGABurst"):
            burst = safe_int(
                cfg0.get("IterationEngine", "InFlight_ContinuousGABurst", fallback=str(burst)),
                burst,
            )
    except Exception:
        pass

    raw = os.environ.get("INFLIGHT_CONTINUOUS_GA_BURST")
    if raw is not None and str(raw).strip() != "":
        try:
            burst = int(raw)
        except Exception:
            pass

    return max(1, min(int(burst), 32))


def _read_continuous_fg_adaptive_submit(cfg0: Any) -> tuple[bool, int]:
    """
    Adaptive FG submit policy for continuous mode.

    Returns:
    - enabled: whether adaptive FG submit burst sizing is enabled
    - max_burst: upper bound for adaptive FG submit burst size
    """
    enabled = True
    max_burst = 3

    try:
        if cfg0 is not None:
            if cfg0.has_option("IterationEngine", "InFlight_FGAdaptiveSubmit"):
                enabled = cfg0.getboolean("IterationEngine", "InFlight_FGAdaptiveSubmit", fallback=True)
            if cfg0.has_option("IterationEngine", "InFlight_FGAdaptiveMaxBurst"):
                max_burst = safe_int(
                    cfg0.get("IterationEngine", "InFlight_FGAdaptiveMaxBurst", fallback=str(max_burst)),
                    max_burst,
                )
    except Exception:
        pass

    raw = os.environ.get("INFLIGHT_FG_ADAPTIVE_SUBMIT")
    if raw is not None and str(raw).strip() != "":
        enabled = _truthy(raw)

    raw = os.environ.get("INFLIGHT_FG_ADAPTIVE_MAX_BURST")
    if raw is not None and str(raw).strip() != "":
        try:
            max_burst = int(raw)
        except Exception:
            pass

    return bool(enabled), max(1, min(int(max_burst), 16))


def _read_fg_slot_reserve(
    cfg0: Any,
    *,
    fg_enabled: bool,
    inflight_limit: int,
    song_slot_limit: int,
) -> int:
    """
    Reserve a dedicated song-slot partition for FG work.

    This prevents GA from consuming all song slots and creating slot-pressure oscillation
    when FG submissions need to acquire slots.
    """
    if (not fg_enabled) or int(inflight_limit) <= 1 or int(song_slot_limit) <= 1:
        return 0

    reserve = 1
    reserve_ratio = 0.20
    absolute_explicit = False

    try:
        if cfg0 is not None:
            if cfg0.has_option("IterationEngine", "InFlight_FGSlotReserve"):
                reserve = safe_int(cfg0.get("IterationEngine", "InFlight_FGSlotReserve", fallback="1"), 1)
                absolute_explicit = True
            elif cfg0.has_option("IterationEngine", "InFlight_FGSlotReserveRatio"):
                reserve_ratio = safe_float(
                    cfg0.get("IterationEngine", "InFlight_FGSlotReserveRatio", fallback=str(reserve_ratio)),
                    reserve_ratio,
                )
    except Exception:
        pass

    raw = os.environ.get("INFLIGHT_FG_SLOT_RESERVE")
    if raw is not None and str(raw).strip() != "":
        try:
            reserve = int(raw)
            absolute_explicit = True
        except Exception:
            pass

    raw = os.environ.get("INFLIGHT_FG_SLOT_RESERVE_RATIO")
    if raw is not None and str(raw).strip() != "":
        try:
            reserve_ratio = float(raw)
        except Exception:
            pass

    reserve_cap = max(1, min(max(1, int(song_slot_limit) - 1), max(1, int(inflight_limit))))
    if absolute_explicit:
        if int(reserve) <= 0:
            return 0
        return max(1, min(int(reserve), int(reserve_cap)))

    reserve_ratio = max(0.0, min(float(reserve_ratio), 0.90))
    ratio_slots = int(round(float(song_slot_limit) * float(reserve_ratio)))
    reserve = max(int(reserve), int(ratio_slots))
    return max(1, min(int(reserve), int(reserve_cap)))


def _continuous_ga_warm_queue_limit(
    *,
    ga_queue_limit: int,
    inflight_limit: int,
    fg_enabled: bool,
    prepared_count: int,
    prep_inflight_count: int,
    decode_inflight_count: int,
    pending_fg_count: int,
    fg_prep_inflight_count: int,
    fg_inflight_count: int,
) -> int:
    """
    Limit the initial GA backlog while the FG pipeline has not started yet.

    During startup, CPU prep can outrun the GPU and bury the first decoded/FG-ready songs behind
    a large queued GA tail. Cap the warm-start GA backlog to roughly one in-flight window only
    while:
    - FG is enabled,
    - no downstream decode/FG work exists yet, and
    - the CPU staging side is already healthy enough to refill that window.

    Once decode/FG work exists, or prep staging is shallow, restore the full GA queue limit.
    """
    limit = max(1, int(ga_queue_limit))
    inflight_limit = max(1, int(inflight_limit))
    if (not fg_enabled) or inflight_limit <= 1:
        return limit

    downstream_fg_work = (
        max(0, int(decode_inflight_count))
        + max(0, int(pending_fg_count))
        + max(0, int(fg_prep_inflight_count))
        + max(0, int(fg_inflight_count))
    )
    if downstream_fg_work > 0:
        return limit

    warm_limit = max(2, min(limit, min(inflight_limit, 4)))
    staging_depth = max(0, int(prepared_count)) + max(0, int(prep_inflight_count))
    if staging_depth < warm_limit:
        return limit

    return max(1, min(limit, warm_limit))


def _continuous_fg_should_start(
    *,
    pending_fg_count: int,
    ready_fg_count: int,
    ga_credit: int,
    oldest_wait_s: float,
    blocked_on_slot: bool,
    no_ga_remaining: bool,
    fg_drain_at_end: bool,
    aging_trigger_s: float,
    aging_hard_s: float,
    ga_inflight_count: int,
    ga_queue_limit: int,
    fg_slot_reserve: int,
) -> bool:
    if int(pending_fg_count) <= 0:
        return False
    if bool(no_ga_remaining):
        return bool(fg_drain_at_end)
    if bool(blocked_on_slot):
        return True
    if (
        int(fg_slot_reserve) > 0
        and int(ready_fg_count) > 0
        and int(ga_inflight_count) >= max(1, int(ga_queue_limit))
    ):
        return True
    if float(aging_hard_s) > 0.0 and float(oldest_wait_s) >= float(aging_hard_s):
        return True
    if float(aging_trigger_s) > 0.0 and float(oldest_wait_s) >= float(aging_trigger_s):
        return True
    return int(ga_credit) <= 0


def _continuous_fg_submit_budget(
    *,
    pending_fg_count: int,
    ready_fg_count: int,
    fg_inflight_count: int,
    fg_workers: int,
    fg_batch_max: int,
    no_ga_remaining: bool,
    fg_drain_at_end: bool,
    blocked_on_slot: bool,
    oldest_wait_s: float,
    aging_trigger_s: float,
    aging_hard_s: float,
    ga_inflight_count: int,
    ga_queue_limit: int,
    adaptive_submit: bool,
    adaptive_max_burst: int,
    fg_slot_reserve: int,
) -> int:
    capacity = max(0, min(int(fg_workers) - int(fg_inflight_count), int(fg_batch_max), int(pending_fg_count)))
    if capacity <= 0:
        return 0

    if bool(no_ga_remaining):
        return capacity if bool(fg_drain_at_end) else 0

    budget = 1
    max_burst = max(1, int(adaptive_max_burst))

    if (
        int(fg_slot_reserve) > 0
        and int(ready_fg_count) > 0
        and int(ga_inflight_count) >= max(1, int(ga_queue_limit))
    ):
        budget = max(int(budget), 1)

    if bool(blocked_on_slot):
        budget = max(int(budget), min(int(capacity), int(max_burst)))

    if float(aging_hard_s) > 0.0 and float(oldest_wait_s) >= float(aging_hard_s):
        budget = max(int(budget), min(int(capacity), int(max_burst)))
    elif float(aging_trigger_s) > 0.0 and float(oldest_wait_s) >= float(aging_trigger_s):
        trigger_burst = 2 if bool(adaptive_submit) else 1
        budget = max(int(budget), min(int(capacity), int(trigger_burst)))

    if bool(adaptive_submit):
        ga_util = 0.0
        if int(ga_queue_limit) > 0:
            try:
                ga_util = float(ga_inflight_count) / float(ga_queue_limit)
            except Exception:
                ga_util = 0.0
        ga_util = max(0.0, min(1.0, float(ga_util)))

        backlog_total = max(0, int(pending_fg_count) + int(fg_inflight_count))
        half_burst = max(2, int((int(max_burst) + 1) // 2))

        if ga_util <= 0.50 and backlog_total >= int(half_burst):
            budget = max(int(budget), min(int(capacity), int(half_burst)))
        if ga_util <= 0.25 and backlog_total >= int(max(4, int(max_burst) * 2)):
            budget = max(int(budget), min(int(capacity), int(max_burst)))

    return max(0, min(int(capacity), int(budget)))


def _closed_loop_bubble_kpi(
    *,
    idle_sec: float,
    ready_ga_count: int,
    ready_fg_count: int,
    backlog_count: int,
    oldest_fg_wait_s: float,
) -> float:
    idle = max(0.0, float(idle_sec))
    if idle <= 0.0:
        return 0.0

    ready_depth = max(0, int(ready_ga_count)) + max(0, int(ready_fg_count))
    backlog_depth = max(0, int(backlog_count))
    fg_wait = max(0.0, float(oldest_fg_wait_s))

    if ready_depth <= 0 and backlog_depth <= 0 and fg_wait <= 0.0:
        return 0.0

    backlog_term = min(4.0, float(backlog_depth) / 4.0)
    fg_wait_term = min(5.0, float(fg_wait))
    pressure = 1.0 + float(ready_depth) + float(backlog_term) + float(fg_wait_term)
    return float(idle) * float(pressure)
