"""Continuous GA/FG scheduler policy and config readers for native in-flight."""
from __future__ import annotations

import logging
from typing import Any

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
    *,
    inflight_limit: int,
    prep_limit: int,
    pending_count: int,
) -> int:
    return default_prime_target(
        inflight_limit=int(inflight_limit),
        prep_limit=int(prep_limit),
        pending_count=int(pending_count),
    )
def read_fg_scheduler_mode() -> str:
    """
    In-flight scheduler is intentionally fixed to continuous mode.
    We removed backlog/drain scheduler options to keep runtime behavior
    deterministic and easier to reason about.
    """
    return "continuous"
def ga_admission_fg_backlog_limit(*, fg_workers: int, fg_prep_workers: int) -> int:
    """
    Canonical bound on host-side FG debt before GA admission pauses.

    FG never visits the GPU owner anymore (the fused GA turn already scored it),
    so the only GA<->FG coupling left is a resource bound: each FG song past the
    workers holds its decoded payload, prepared plan, and owner score map in host
    memory. Size the allowance to steady state (every FG worker busy, the prep
    runway full, plus a small completion-batch margin) so it only binds when FG
    genuinely falls behind GA.
    """
    workers = max(1, int(fg_workers))
    prep_workers = max(1, int(fg_prep_workers))
    return max(4, 2 * int(workers)) + int(prep_workers)
def ga_should_pause_for_fg_backlog(
    *,
    pending_fg_count: int,
    fg_inflight_count: int,
    backlog_limit: int,
) -> bool:
    """
    Pause GA admission while the FG stage owes more work than its bound.

    This replaces the round-trip-era credit/lane-fill/yield policies with the one
    invariant they actually protected: GA throughput must not mint unbounded FG
    debt ("GA and FG are one product surface"). GA resumes as soon as FG workers
    drain back under the bound.
    """
    backlog = max(0, int(pending_fg_count)) + max(0, int(fg_inflight_count))
    return int(backlog) > max(1, int(backlog_limit))

def continuous_fg_prep_start_budget(
    *,
    pending_fg_count: int,
    fg_prep_inflight_count: int,
    fg_prep_worker_count: int,
) -> int:
    """
    Keep enough pending FG plans moving toward worker-ready status.

    Dynamic FG prep covers candidate selection plus exact-plan construction before
    a song can be handed to an FG worker. Keep the prep runway sized to its own
    worker pool so prep never becomes the FG stage's critical path.
    """
    pending = max(0, int(pending_fg_count))
    if pending <= 0:
        return 0
    runway = max(1, int(fg_prep_worker_count))
    active_prep = max(0, int(fg_prep_inflight_count))
    return max(0, min(int(pending), int(runway) - int(active_prep)))

def continuous_fg_allow_not_ready(
    *,
    no_ga_remaining: bool,
) -> bool:
    """
    Decide whether a pending FG song may be handed to a worker before prep is done.
    During the final FG drain there is no GA work left to feed; handing the worker a
    not-yet-ready song lets it wait on the prep future instead of serializing the
    last prep/submit window behind the scheduler loop.
    """
    return bool(no_ga_remaining)
def continuous_fg_submit_budget(
    *,
    pending_fg_count: int,
    ready_fg_count: int,
    fg_inflight_count: int,
    fg_workers: int,
    fg_batch_max: int,
    no_ga_remaining: bool,
) -> int:
    """
    FG submissions are bounded by worker availability alone.

    FG jobs are host-only materialization (fused handoff): a free worker is the
    only resource they consume, so hand every free worker a prep-ready song. Songs
    still in prep are not eligible until the final drain (a worker blocked on a
    prep future serves nobody while GA still feeds the owner).
    """
    available_pending = max(0, int(pending_fg_count))
    if not bool(no_ga_remaining):
        available_pending = min(int(available_pending), max(0, int(ready_fg_count)))
    return max(0, min(int(fg_workers) - int(fg_inflight_count), int(fg_batch_max), int(available_pending)))
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
