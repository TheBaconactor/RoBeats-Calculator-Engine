from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable
import logging

from gear_optimizer.core.utils import safe_float, safe_int
from gear_optimizer.solver.native_inflight_types import native_song_label


from gear_optimizer.core.parsing import env_get

logger = logging.getLogger(__name__)


@dataclass
class GAQueueLimitController:
    base_limit: int
    pressure_window_s: float
    extra_free_on_slot_pressure: int
    fg_slot_reserve: int
    song_slot_limit: int
    monotonic: Callable[[], float] = field(default=time.monotonic, repr=False)
    _cache_key: tuple[bool, int, int, int, int] | None = field(default=None, init=False, repr=False)
    _cache_value: int = field(default=1, init=False, repr=False)

    def __post_init__(self) -> None:
        self.base_limit = max(1, int(self.base_limit))
        self.pressure_window_s = max(0.0, float(self.pressure_window_s))
        self.extra_free_on_slot_pressure = max(0, int(self.extra_free_on_slot_pressure))
        self.fg_slot_reserve = max(0, int(self.fg_slot_reserve))
        self.song_slot_limit = max(1, int(self.song_slot_limit))
        self._cache_value = int(self.base_limit)

    def effective_limit(self, *, last_slot_block_t: float | None) -> int:
        extra_free = 0
        slot_pressure_active = False

        if last_slot_block_t is not None and float(self.pressure_window_s) > 0.0:
            try:
                if (float(self.monotonic()) - float(last_slot_block_t)) <= float(self.pressure_window_s):
                    slot_pressure_active = True
                    extra_free = max(int(extra_free), int(self.extra_free_on_slot_pressure))
            except Exception as e:
                logger.debug(f"native_inflight_scheduler:GAQueueLimitController.effective_limit: {e}")

        cache_key = (
            bool(slot_pressure_active),
            int(extra_free),
            int(self.fg_slot_reserve),
            int(self.song_slot_limit),
            int(self.base_limit),
        )
        if cache_key == self._cache_key:
            return int(self._cache_value)

        min_free = int(self.fg_slot_reserve) + int(extra_free)
        min_free = max(0, min(int(min_free), max(0, int(self.song_slot_limit) - 1)))
        limit_from_free = max(1, int(self.song_slot_limit) - int(min_free))
        self._cache_value = max(1, min(int(self.base_limit), int(limit_from_free)))
        self._cache_key = cache_key
        return int(self._cache_value)


def _song_lane_key(song: Any) -> str:
    try:
        return native_song_label(song)
    except Exception as e:
        logger.debug(f"native_inflight_scheduler:_song_lane_key: {e}")
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
    try:
        keys.update(str(key).strip() for key in fg_active_keys if str(key).strip())
    except Exception as e:
        logger.debug(f"native_inflight_scheduler:count_active_song_lanes: {e}")
    return int(len(keys))


def default_prime_target(*, inflight_limit: int, prep_limit: int, pending_count: int) -> int:
    """
    Pick a startup prep backlog large enough to avoid the first GA/FG feed bubble.

    For smaller in-flight runs, priming only `inflight_limit` songs tends to leave the
    GPU queue shallow while prep/decode workers are still spinning up. We bias toward
    a modest 4-8 song startup backlog, but always cap by the prep buffer and pending queue.
    """
    try:
        inflight_limit = int(inflight_limit)
    except Exception as e:
        logger.debug(f"native_inflight_scheduler:default_prime_target: {e}")
        inflight_limit = 1
    try:
        prep_limit = int(prep_limit)
    except Exception as e:
        logger.debug(f"native_inflight_scheduler:default_prime_target: {e}")
        prep_limit = 1
    try:
        pending_count = int(pending_count)
    except Exception as e:
        logger.debug(f"native_inflight_scheduler:default_prime_target: {e}")
        pending_count = 0

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
        logger.debug(f"native_inflight_scheduler:read_prime_target: {e}")
        target = 0

    raw = env_get("INFLIGHT_PRIME_TARGET")
    if raw is not None and str(raw).strip() != "":
        try:
            target = int(raw)
        except Exception as e:
            logger.debug(f"native_inflight_scheduler:read_prime_target: {e}")

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
        logger.debug(f"native_inflight_scheduler:read_fg_ga_credit_budget: {e}")

    raw = env_get("INFLIGHT_FG_GA_CREDIT_BUDGET")
    if raw is not None and str(raw).strip() != "":
        try:
            budget = int(raw)
            explicit = True
        except Exception as e:
            logger.debug(f"native_inflight_scheduler:read_fg_ga_credit_budget: {e}")

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
        logger.debug(f"native_inflight_scheduler:read_continuous_ga_dispatch_burst: {e}")

    raw = env_get("INFLIGHT_CONTINUOUS_GA_BURST")
    if raw is not None and str(raw).strip() != "":
        try:
            burst = int(raw)
        except Exception as e:
            logger.debug(f"native_inflight_scheduler:read_continuous_ga_dispatch_burst: {e}")

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
        logger.debug(f"native_inflight_scheduler:read_continuous_fg_adaptive_max_burst: {e}")

    raw = env_get("INFLIGHT_FG_ADAPTIVE_MAX_BURST")
    if raw is not None and str(raw).strip() != "":
        try:
            max_burst = int(raw)
        except Exception as e:
            logger.debug(f"native_inflight_scheduler:read_continuous_fg_adaptive_max_burst: {e}")

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
        logger.debug(f"native_inflight_scheduler:read_fg_slot_reserve: {e}")

    raw = env_get("INFLIGHT_FG_SLOT_RESERVE")
    if raw is not None and str(raw).strip() != "":
        try:
            reserve = int(raw)
            absolute_explicit = True
        except Exception as e:
            logger.debug(f"native_inflight_scheduler:read_fg_slot_reserve: {e}")

    raw = env_get("INFLIGHT_FG_SLOT_RESERVE_RATIO")
    if raw is not None and str(raw).strip() != "":
        try:
            reserve_ratio = float(raw)
        except Exception as e:
            logger.debug(f"native_inflight_scheduler:read_fg_slot_reserve: {e}")

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
    try:
        inflight_limit_i = int(inflight_limit)
    except Exception as e:
        logger.debug(f"native_inflight_scheduler:read_inflight_target_song_lanes: {e}")
        inflight_limit_i = 1
    inflight_limit_i = max(1, int(inflight_limit_i))

    target = 2 if int(inflight_limit_i) > 1 else 1
    try:
        if cfg0 is not None and cfg0.has_option("IterationEngine", "InFlight_TargetSongLanes"):
            target = safe_int(
                cfg0.get("IterationEngine", "InFlight_TargetSongLanes", fallback=str(target)),
                target,
            )
    except Exception as e:
        logger.debug(f"native_inflight_scheduler:read_inflight_target_song_lanes: {e}")

    raw = env_get("INFLIGHT_TARGET_SONG_LANES")
    if raw is not None and str(raw).strip() != "":
        try:
            target = int(raw)
        except Exception as e:
            logger.debug(f"native_inflight_scheduler:read_inflight_target_song_lanes: {e}")

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
    Keep startup GA warmup bounded without starving the continuous conveyor.

    The original continuous architecture worked best when GA could keep a healthy
    runway of future songs behind the currently visible FG lanes. The important
    protection is only at startup: before any decode/FG work exists, avoid
    front-loading an arbitrarily deep GA tail that hides the first ready FG.

    Once decode/FG work exists, return the full GA queue limit and rely on owner
    turn discipline to surface ready FG promptly. Clamping GA to the visible lane
    count once the conveyor is full underfeeds fast GPUs because downstream decode/FG prep
    latency can exceed a two-lane runway.
    """
    limit = max(1, int(ga_queue_limit))
    inflight_limit = max(1, int(inflight_limit))
    if inflight_limit <= 1:
        return limit

    target_lanes = max(1, min(int(target_song_lanes), int(inflight_limit)))
    burst = max(1, int(dispatch_burst))
    warm_limit = max(1, min(int(limit), max(int(target_lanes), min(int(inflight_limit), int(burst)))))
    handoff_limit = max(
        int(warm_limit),
        min(int(limit), max(int(target_lanes) * 2, int(target_lanes) + int(burst))),
    )

    if max(0, int(fg_inflight_count)) > 0:
        return int(limit)

    handoff_fg_work = (
        max(0, int(decode_inflight_count)) + max(0, int(pending_fg_count)) + max(0, int(fg_prep_inflight_count))
    )
    if handoff_fg_work > 0:
        # Decode/pending FG means the first FG handoff is approaching, but if we
        # immediately reopen GA to the full queue depth we can bury that first FG
        # owner turn behind a long GA tail. Keep a modest GA runway until FG has
        # actually surfaced onto the owner, then restore the full continuous
        # limit.
        return int(handoff_limit)

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
    target_song_lanes: int,
    oldest_wait_s: float,
    aging_trigger_s: float,
    blocked_on_slot: bool,
) -> bool:
    """
    Stop GA admission when FG has become the limiting queue.

    This is deliberately an admission rule, not a scoring shortcut. Existing GA
    work may finish, but the submit loop yields to the FG scheduler before it
    adds more GA jobs once FG is ready. Active-but-unready FG prep is not a
    runnable GPU lane, so it must not stop GA admission by itself.
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
    if fg_inflight >= fg_workers:
        return False
    if ready > 0:
        return True
    return False


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
    # Treat `ready_fg_count` as a hint, not a hard gate. The conveyor's real
    # readiness check lives in `_pop_next_fg(...)`; gating here on an exact
    # count can defer runnable FG work behind a full GA drain if bookkeeping
    # lags the actual collect/prep state.
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
            # Probe one pending FG lane even when the ready hint is stale. The
            # submit loop still routes through `_pop_next_fg(...)`, so at worst
            # this is a cheap no-op; at best it lets a genuinely ready FG lane
            # surface immediately instead of waiting for GA to fully drain.
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
