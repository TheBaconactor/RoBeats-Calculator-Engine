"""Continuous GA/FG scheduler policy and config readers for native in-flight."""
from __future__ import annotations

import logging
from typing import Any

from gear_optimizer.core.parsing import env_get
from gear_optimizer.core.utils import safe_float, safe_int
from gear_optimizer.solver.native_inflight_config import native_song_label

logger = logging.getLogger(__name__)

def _song_lane_key(song: Any) -> str:
    try:
        return native_song_label(song)
    except Exception as e:
        logger.debug(f"native_inflight_scheduler_policy:_song_lane_key: {e}")
        return ""
def count_active_song_lanes(
    *,
    ga_inflight,
    decode_inflight,
    fg_active_keys,
) -> int:
    keys: set[str] = set()
    for song in ga_inflight:
        key = _song_lane_key(song)
        if key:
            keys.add(key)
    for song in decode_inflight:
        key = _song_lane_key(song)
        if key:
            keys.add(key)
    keys.update(str(key).strip() for key in fg_active_keys if str(key).strip())
    return int(len(keys))
def default_prime_target(*, inflight_limit: int, prep_limit: int, pending_count: int) -> int:
    """
    Pick a startup prep backlog large enough to avoid the first GA/FG feed bubble.
    For smaller in-flight runs, priming only `inflight_limit` songs tends to leave the
    GPU queue shallow while prep/decode workers are still spinning up. We bias toward
    a modest 4-8 song startup backlog, but always cap by the prep buffer and pending queue.
    """
    inflight_limit = int(inflight_limit)
    prep_limit = int(prep_limit)
    pending_count = int(pending_count)
    inflight_limit = max(1, inflight_limit)
    prep_limit = max(1, prep_limit)
    pending_count = max(0, pending_count)
    if pending_count <= 0:
        return 0
    target = max(inflight_limit, min(8, max(4, inflight_limit * 2)))
    return max(1, min(target, prep_limit, pending_count))
def read_prime_target(
    cfg0: Any,
    *,
    inflight_limit: int,
    prep_limit: int,
    pending_count: int,
) -> int:
    target = 0
    try:
        if cfg0 is not None:
            target = safe_int(cfg0.get("IterationEngine", "InFlight_PrimeTarget", fallback="0"), 0)
    except Exception as e:
        logger.debug(f"native_inflight_scheduler_policy:read_prime_target: {e}")
        target = 0
    raw = env_get("INFLIGHT_PRIME_TARGET")
    if raw is not None and str(raw).strip() != "":
        try:
            target = int(raw)
        except Exception as e:
            logger.debug(f"native_inflight_scheduler_policy:read_prime_target: {e}")
    if int(target) <= 0:
        return default_prime_target(
            inflight_limit=int(inflight_limit),
            prep_limit=int(prep_limit),
            pending_count=int(pending_count),
        )
    return max(0, min(int(target), int(prep_limit), int(pending_count)))
def read_fg_scheduler_mode() -> str:
    """
    In-flight scheduler is intentionally fixed to continuous mode.
    We removed backlog/drain scheduler options to keep runtime behavior
    deterministic and easier to reason about.
    """
    return "continuous"
def read_fg_ga_credit_budget(cfg0: Any, *, default_budget: int) -> tuple[int, bool]:
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
    except Exception as e:
        logger.debug(f"native_inflight_scheduler_policy:read_fg_ga_credit_budget: {e}")
    raw = env_get("INFLIGHT_FG_GA_CREDIT_BUDGET")
    if raw is not None and str(raw).strip() != "":
        try:
            budget = int(raw)
            explicit = True
        except Exception as e:
            logger.debug(f"native_inflight_scheduler_policy:read_fg_ga_credit_budget: {e}")
    return max(1, int(budget)), bool(explicit)
def read_continuous_ga_dispatch_burst(cfg0: Any, *, default_burst: int = 2) -> int:
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
    except Exception as e:
        logger.debug(f"native_inflight_scheduler_policy:read_continuous_ga_dispatch_burst: {e}")
    raw = env_get("INFLIGHT_CONTINUOUS_GA_BURST")
    if raw is not None and str(raw).strip() != "":
        try:
            burst = int(raw)
        except Exception as e:
            logger.debug(f"native_inflight_scheduler_policy:read_continuous_ga_dispatch_burst: {e}")
    return max(1, min(int(burst), 32))
def read_continuous_fg_adaptive_max_burst(cfg0: Any) -> int:
    """
    Upper bound for adaptive FG submit burst size in continuous mode.
    """
    max_burst = 3
    try:
        if cfg0 is not None:
            if cfg0.has_option("IterationEngine", "InFlight_FGAdaptiveMaxBurst"):
                max_burst = safe_int(
                    cfg0.get("IterationEngine", "InFlight_FGAdaptiveMaxBurst", fallback=str(max_burst)),
                    max_burst,
                )
    except Exception as e:
        logger.debug(f"native_inflight_scheduler_policy:read_continuous_fg_adaptive_max_burst: {e}")
    raw = env_get("INFLIGHT_FG_ADAPTIVE_MAX_BURST")
    if raw is not None and str(raw).strip() != "":
        try:
            max_burst = int(raw)
        except Exception as e:
            logger.debug(f"native_inflight_scheduler_policy:read_continuous_fg_adaptive_max_burst: {e}")
    return max(1, min(int(max_burst), 16))
def read_fg_slot_reserve(
    cfg0: Any,
    *,
    inflight_limit: int,
    song_slot_limit: int,
) -> int:
    """
    Reserve a dedicated song-slot partition for FG work.
    This prevents GA from consuming all song slots and creating slot-pressure oscillation
    when FG submissions need to acquire slots.
    """
    if int(inflight_limit) <= 1 or int(song_slot_limit) <= 1:
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
    except Exception as e:
        logger.debug(f"native_inflight_scheduler_policy:read_fg_slot_reserve: {e}")
    raw = env_get("INFLIGHT_FG_SLOT_RESERVE")
    if raw is not None and str(raw).strip() != "":
        try:
            reserve = int(raw)
            absolute_explicit = True
        except Exception as e:
            logger.debug(f"native_inflight_scheduler_policy:read_fg_slot_reserve: {e}")
    raw = env_get("INFLIGHT_FG_SLOT_RESERVE_RATIO")
    if raw is not None and str(raw).strip() != "":
        try:
            reserve_ratio = float(raw)
        except Exception as e:
            logger.debug(f"native_inflight_scheduler_policy:read_fg_slot_reserve: {e}")
    reserve_cap = max(1, min(max(1, int(song_slot_limit) - 1), max(1, int(inflight_limit))))
    if absolute_explicit:
        if int(reserve) <= 0:
            return 0
        return max(1, min(int(reserve), int(reserve_cap)))
    reserve_ratio = max(0.0, min(float(reserve_ratio), 0.90))
    ratio_slots = int(round(float(song_slot_limit) * float(reserve_ratio)))
    reserve = max(int(reserve), int(ratio_slots))
    return max(1, min(int(reserve), int(reserve_cap)))
def read_inflight_target_song_lanes(cfg0: Any, *, inflight_limit: int) -> int:
    """
    Target number of concurrently active song lanes for the single-owner pipeline.
    Default to two lanes whenever overlap is enabled so GA/FG can interleave across
    songs instead of collapsing back into a single-song phase train.
    """
    inflight_limit_i = max(1, int(inflight_limit))
    target = 2 if int(inflight_limit_i) > 1 else 1
    try:
        if cfg0 is not None and cfg0.has_option("IterationEngine", "InFlight_TargetSongLanes"):
            target = safe_int(
                cfg0.get("IterationEngine", "InFlight_TargetSongLanes", fallback=str(target)),
                target,
            )
    except Exception as e:
        logger.debug(f"native_inflight_scheduler_policy:read_inflight_target_song_lanes: {e}")
    raw = env_get("INFLIGHT_TARGET_SONG_LANES")
    if raw is not None and str(raw).strip() != "":
        try:
            target = int(raw)
        except Exception as e:
            logger.debug(f"native_inflight_scheduler_policy:read_inflight_target_song_lanes: {e}")
    return max(1, min(int(target), int(inflight_limit_i)))
def continuous_ga_warm_queue_limit(
    *,
    ga_queue_limit: int,
    inflight_limit: int,
    prepared_count: int,
    prep_inflight_count: int,
    decode_inflight_count: int,
    pending_fg_count: int,
    fg_prep_inflight_count: int,
    fg_inflight_count: int,
    target_song_lanes: int,
    active_song_lanes: int,
    dispatch_burst: int,
) -> int:
    """
    Keep the single GPU owner fed without allowing GA to create hidden FG debt.
    The owner needs a tiny runway, not a single-request cliff: one ready GA can
    leave the GPU empty while host decode/FG prep stages the next request. Keep
    the runway bounded by the song-lane/dispatch conveyor, and rely on the GPU
    owner to pull a ready FG continuation ahead of staged GA at the boundary.
    """
    limit = max(1, int(ga_queue_limit))
    inflight_limit = max(1, int(inflight_limit))
    if inflight_limit <= 1:
        return limit
    target_lanes = max(1, min(int(target_song_lanes), int(inflight_limit)))
    burst_lanes = max(1, int(dispatch_burst))
    warm_limit = max(1, min(int(limit), int(target_lanes), int(burst_lanes)))
    handoff_fg_work = (
        max(0, int(decode_inflight_count)) + max(0, int(pending_fg_count)) + max(0, int(fg_prep_inflight_count))
        + max(0, int(fg_inflight_count))
    )
    if handoff_fg_work > 0:
        return int(warm_limit)
    staging_depth = max(0, int(prepared_count)) + max(0, int(prep_inflight_count))
    if staging_depth >= int(warm_limit):
        return int(warm_limit)
    return int(limit)
def continuous_fg_should_fill_song_lanes(
    *,
    target_song_lanes: int,
    active_song_lanes: int,
    ready_ga_count: int,
    pending_fg_count: int = 0,
    ready_fg_count: int = 0,
    blocked_on_slot: bool,
    no_ga_remaining: bool,
    oldest_wait_s: float,
    aging_trigger_s: float = 0.0,
    aging_hard_s: float,
) -> bool:
    """
    Prefer filling the next GA song lane before starting FG when we have immediate GA work.
    This turns the in-flight queue into a real two-lane conveyor on one GPU owner:
    keep song B entering GA while song A is already headed toward FG, unless FG is
    already runnable or has aged enough that fairness must override the lane-fill
    preference.
    """
    if int(target_song_lanes) <= 1:
        return False
    if int(active_song_lanes) >= int(target_song_lanes):
        return False
    if int(ready_ga_count) <= 0:
        return False
    if bool(blocked_on_slot) or bool(no_ga_remaining):
        return False
    if int(pending_fg_count) > 0 and int(ready_fg_count) > 0:
        return False
    if int(pending_fg_count) > 0 and float(aging_trigger_s) > 0.0 and float(oldest_wait_s) >= float(aging_trigger_s):
        return False
    if float(aging_hard_s) > 0.0 and float(oldest_wait_s) >= float(aging_hard_s):
        return False
    return True
def continuous_ga_should_yield_to_fg(
    *,
    pending_fg_count: int,
    ready_fg_count: int,
    fg_prep_inflight_count: int,
    fg_inflight_count: int,
    fg_worker_count: int,
    blocked_on_slot: bool,
) -> bool:
    """
    Stop GA admission when FG has become the limiting queue.
    This is deliberately an admission rule, not a scoring shortcut. Existing GA
    work may finish, but the submit loop yields to the FG scheduler only when
    FG has runnable GPU work. Active-but-unready FG prep is CPU work, not a GPU
    lane; letting it block ready GA creates visible owner starvation instead of
    protecting exactness.
    """
    pending = max(0, int(pending_fg_count))
    ready = max(0, int(ready_fg_count))
    prep = max(0, int(fg_prep_inflight_count))
    fg_inflight = max(0, int(fg_inflight_count))
    fg_workers = max(1, int(fg_worker_count))
    fg_pressure = int(pending) + int(prep) + int(fg_inflight)
    if fg_pressure <= 0:
        return False
    if bool(blocked_on_slot):
        return True
    if ready > 0:
        return True
    if fg_inflight >= fg_workers:
        return False
    return False

def continuous_fg_prep_start_budget(
    *,
    pending_fg_count: int,
    fg_prep_inflight_count: int,
    target_song_lanes: int,
) -> int:
    """
    Bound dynamic FG prep to the same song-lane runway that owns GA/FG overlap.

    FG prep is exact CPU work for a pending FG lane. Letting it top up to the
    raw worker count creates hidden active lanes during hard-chart clusters,
    even after GA admission yields correctly. The target song-lane budget is
    the owner invariant; worker count is only local execution capacity.
    """
    pending = max(0, int(pending_fg_count))
    if pending <= 0:
        return 0
    target = max(1, int(target_song_lanes))
    active_prep = max(0, int(fg_prep_inflight_count))
    return max(0, min(int(pending), int(target) - int(active_prep)))

def continuous_fg_should_start(
    *,
    pending_fg_count: int,
    ready_fg_count: int,
    ga_credit: int,
    oldest_wait_s: float,
    blocked_on_slot: bool,
    no_ga_remaining: bool,
    aging_trigger_s: float,
    aging_hard_s: float,
    ga_queue_limit: int,
    fg_slot_reserve: int,
) -> bool:
    if int(pending_fg_count) <= 0:
        return False
    if bool(no_ga_remaining):
        return True
    if bool(blocked_on_slot):
        return True
    return True
def continuous_fg_allow_not_ready(
    *,
    blocked_on_slot: bool,
    no_ga_remaining: bool,
) -> bool:
    """
    Decide whether a pending FG song may be handed to a worker before prep is done.
    During the final FG drain there is no GA work left to protect. Keeping those
    pending songs in the scheduler until their prep futures finish serializes the
    last CPU prep/first-submit window and can leave the GPU owner empty.
    """
    if bool(blocked_on_slot):
        return True
    return bool(no_ga_remaining)
def continuous_fg_submit_budget(
    *,
    pending_fg_count: int,
    ready_fg_count: int,
    fg_inflight_count: int,
    fg_workers: int,
    fg_batch_max: int,
    no_ga_remaining: bool,
    blocked_on_slot: bool,
    oldest_wait_s: float,
    aging_trigger_s: float,
    aging_hard_s: float,
    ga_queue_limit: int,
    adaptive_max_burst: int,
    fg_slot_reserve: int,
) -> int:
    available_pending = int(pending_fg_count)
    if (not bool(no_ga_remaining)) and (not bool(blocked_on_slot)):
        ready_hint = max(0, int(ready_fg_count))
        if ready_hint > 0:
            available_pending = min(int(available_pending), int(ready_hint))
        else:
            available_pending = min(int(available_pending), 1)
    capacity = max(0, min(int(fg_workers) - int(fg_inflight_count), int(fg_batch_max), int(available_pending)))
    if capacity <= 0:
        return 0
    if bool(no_ga_remaining):
        return int(capacity)
    if int(pending_fg_count) > int(ready_fg_count):
        burst_cap = max(1, min(int(adaptive_max_burst), int(fg_batch_max), int(fg_workers)))
        capacity = min(int(capacity), int(burst_cap))
    return int(capacity)
def closed_loop_bubble_kpi(
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
