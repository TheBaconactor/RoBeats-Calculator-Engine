"""Canonical server-matching fever fill crossing -- the authoritative activation index.

WHY THIS EXISTS
---------------
The FG frontier historically used ``_action_table``'s compressed estimate

    fill(k) = ceil(raw_fever_fill + 0.5 * k)      # notes-to-fill under a simplified count
    activation_index = state_i + fill(k)

as if it answered "which note does the server actually activate fever on, given this exact
placement of Greats?".  It does not.  It collapses first/later-section offset, the wasted note,
placed-Great locations, activation-hit inclusion, Great half-fill, and the float/ceil boundary into
one integer count.  For Perfect-only (BASE) sections the calibrated integer stepping happens to line
up; once Greats are placed non-uniformly it can land ONE NOTE too far right.  The late-Great branch
then starts the fever window from that (wrong) note's late-Great timestamp, extending fever past the
true drain -- an unreachable window (the FG late-Great over-report).

THE CANONICAL ANSWER
--------------------
Walk the actual notes in order and apply the SAME fill amounts the authoritative WebPort
``ScoreEngine`` (1:1 with the server) applies while charging -- a Perfect adds ``1/feverFillDenom``,
a Great adds ``1/(2*feverFillDenom)`` (a Great fills half) -- and activate on the FIRST note whose
own fill takes the bar to full (``>= FEVER_ACTIVATE_AT`` == 1.0).  ``raw_fever_fill`` equals the
ScoreEngine's ``feverFillDenom`` exactly (verified: diff < 1e-6), so this walk reproduces the
ScoreEngine crossing bit-for-bit.  It needs NONE of the ``-1`` / wasted-note / ceil corrections --
those were artifacts of the compressed formula; the walk gets them for free.

This is the SOURCE OF TRUTH for activation legality -- the ORACLE the production closed forms are
measured against, not a replacement for them.  For the Perfect crossing ``_action_table``'s ``fill``
equals this walk exactly on the production band (see below), so it does decide activation correctly;
for the non-uniform late-Great placement the walk exposed the pre-gate over-report, which the O(1)
``late_great_prefix_is_legal`` gate now forecloses (it reproduces this walk bit-for-bit).

BASE AND FG SHARE ONE CANONICAL MODEL (reference)
-------------------------------------------------
This crossing is not FG-specific.  The BASE (all-Perfect) timeline is the same walk with
``is_great`` all-False, and the historical ``calculate_fever_timeline_indices``
(``ceil((total-long)*0.333*ff)`` integer note-count) is its Perfect-only special case.  Conceptually
both surfaces reduce to the SAME two calls -- ``server_fill_crossing_fast`` (activation) and
``server_fever_end`` (drain) -- differing ONLY in ``is_great`` and the per-note hit-timing arrays.

PRODUCTION ALREADY COMPUTES THE CANONICAL CROSSING (in closed form)
-------------------------------------------------------------------
Production does not literally CALL ``server_fill_crossing_fast`` / ``server_fill_crossing_run`` in the
hot path -- and it does not need to.  The two O(1) closed forms it uses ARE that crossing, each proven
bit-exact against the walk oracle, so there is no "wrong compressed formula" left to route away:

  * Perfect activation: ``_action_table``'s ``fill = ceil(raw_fever_fill + 0.5*k)`` equals
    ``server_fill_crossing_run`` for EVERY production ``(raw_fever_fill, k)`` -- measured 0 differences
    over the full ``raw in [1, 300]``, ``k in [0, ceil(raw)]`` band.  Region 2 (the crossing lands ON a
    Great) needs a contiguous run of ``k >= ~2*raw`` Greats, which ``non_fever_base = ceil(raw)`` never
    reaches, so the Perfect crossing is always the region-3 form and ``ceil(...)`` is the exact index.
  * late-Great activation: ``late_great_prefix_is_legal`` equals the placement walk
    ``late_great_activation_is_legal`` (``test_fg_fill_crossing``, 200k cases).  The late-Great
    placement is ``[prefix Greats][Perfects][activation Great]`` -- non-contiguous -- which a single
    contiguous ``server_fill_crossing_run`` deliberately does NOT model; the GATE is that placement's
    canonical closed form.  So the gate is not a stopgap over a wrong formula: it IS the canonical
    late-Great crossing (it drops only the float-boundary phantom, e.g. the MoltenVK over-report).

The walk / searchsorted forms (``server_fill_crossing``, ``server_fill_crossing_fast``) are therefore
the ORACLE that PROVES the production closed forms, not a pending replacement for them.  Real loadouts
are re-validated walk-legal on every deploy by ``tools/dev/audit_loadout_legality.py``.  BASE was fixed
separately by invalidating the stale timeline-frontier disk cache (``exact-frontier`` version bump),
the DP/scorer already being floor-aware.
The MAXIMUM REACHABLE surface falls straight out of the server rules: activation is the AUTO crossing
(cannot fire earlier -- the bar is not full; cannot fire later -- the server auto-fires the instant it
is), and the drain starts at the crossing note's LATEST legal hit (a Great's late window reaches
further than a Perfect's, so activating on a late Great legally extends fever -- but only because the
crossing note IS that Great; when a Perfect crosses first you get its shorter window, never a
phantom).  The base under-report is the drain half of the same story: the historical base end searched
the NOMINAL timestamps, under-counting boundary notes the player can hit EARLY into the window; the
canonical drain searches the floor envelope (as FG already does).  See ``server_fever_end`` /
``canonical_fever_sections``.

COMPLEXITY (as low as it goes)
------------------------------
Per fever section, the whole formula is:

    activation = server_fill_crossing_run(start, great_run_start, k, denom, n)   # O(1)
    fever_end  = server_fever_end(floor_ts, activation_late_hit, feverTimeSec, activation)  # O(log n)

The activation is **O(1)** — the production placement is always Perfects + one contiguous forced-Great
run, so the crossing is a three-case closed form (``server_fill_crossing_run``), costing the same as
the old buggy ``state_i + ceil(raw + 0.5*k)`` while being correct. The drain is a single monotonic
threshold search — ``O(log n)`` via ``searchsorted``, or ``O(1)`` against the kernel's precomputed
end-index table. There is **no per-candidate ``O(n)``** (no prefix rebuild in the hot path). The
``O(n)`` walk (``server_fill_crossing``) and the ``O(log n)`` general searchsorted form
(``server_fill_crossing_fast`` over ``fill_prefix_perfect_units``) are the **oracle / reference** that
*prove* the O(1) form (walk == fast == run on 60k randomized placements) — test-only, not the hot path.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Sequence

import numpy as np

from gear_optimizer.solver.timing_envelope import floor_to_int_ms

# The bar activates fever the instant a hit's own fill takes it to full (PlayerScore.lua; the
# WebPort ScoreEngine gate ``feverBar >= SCORING.FEVER_ACTIVATE_AT``).
FEVER_ACTIVATE_AT = 1.0

# Fill in PERFECT-UNITS: a Perfect contributes 1.0, a Great half (0.5).  The bar is full at
# ``fever_fill_denom`` perfect-units (== normalized bar 1.0, since denom == feverFillDenom).  This is
# the same accumulation the walk does, expressed so a single cumulative-sum + searchsorted answers
# the crossing in O(log n) -- no re-derived closed form (a closed ``ceil(denom + 0.5g)`` is circular
# once the crossing note is itself a Great, e.g. AmongUs sec-1).
_PERFECT_UNIT = 1.0
_GREAT_UNIT = 0.5


@dataclass(frozen=True, slots=True)
class ActivationLanePrefix:
    """One lane's exact before-activation prefix in immutable chart ordinals."""

    lane: int
    note_indices: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class ActivationScheduleWitness:
    """Exact full-combo event partition chosen for one activation.

    ``lane_prefixes`` is sufficient for the input matcher: on every lane, exactly the listed
    chart-order prefix is consumed before the activation. ``preactivation_order`` is the concrete
    cross-lane merge used by replay (ties are intentional input order, not a downstream guess).
    The half-unit/count fields are the response-surface signature used by the producer.
    """

    activation_index: int
    activation_hit_timestamp: float
    section_start: int
    section_end: int
    lane_prefixes: tuple[ActivationLanePrefix, ...]
    preactivation_order: tuple[int, ...]
    preactivation_fill_half_units: int
    preactivation_event_count: int
    preactivation_great_count: int


def _exact_fill_half_units(fill_units: np.ndarray, *, start: int, end: int) -> np.ndarray:
    section = np.asarray(fill_units[int(start) : int(end)], dtype=np.float32)
    is_great = section == np.float32(_GREAT_UNIT)
    is_perfect = section == np.float32(_PERFECT_UNIT)
    if not bool(np.all(is_great | is_perfect)):
        raise ValueError("fill_units must contain only exact Perfect (1.0) or Great (0.5) units")
    return np.where(is_great, np.int8(1), np.int8(2)).astype(np.int8, copy=False)


def exact_label_hit_intervals(
    *,
    is_great: Sequence[bool] | np.ndarray,
    timestamps: Sequence[float] | np.ndarray,
    perfect_floor_timestamps: Sequence[float] | np.ndarray,
    perfect_candidate_timestamps: Sequence[float] | np.ndarray,
    great_floor_timestamps: Sequence[float] | np.ndarray,
    great_candidate_timestamps: Sequence[float] | np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return exact primary/secondary intervals for a concrete Perfect/Great label stream.

    Perfect has one interval. Great is the disjoint union of its early and late bands; the Perfect
    band between them must never be treated as Great merely because the outer envelope spans it.
    The candidate offset identifies the engine's normal (+40ms) versus held-tail (+80ms) window
    without adding note-type state to the stats-free response trace.

    ``perfect_floor_timestamps`` and ``great_floor_timestamps`` are monotone prefix-max envelopes
    owned by fever-end search. They are deliberately *not* per-note hit-window lows: using them as
    such loses a held tail's wider raw early reach. We validate those producer envelopes here, then
    reconstruct the raw per-note judgment intervals from the quantized chart time and note width.
    """
    labels = np.asarray(is_great, dtype=np.bool_).reshape(-1)
    chart = np.asarray(timestamps, dtype=np.float32).reshape(-1)
    perfect_floor = np.asarray(perfect_floor_timestamps, dtype=np.float32).reshape(-1)
    perfect_high = np.asarray(perfect_candidate_timestamps, dtype=np.float32).reshape(-1)
    great_floor = np.asarray(great_floor_timestamps, dtype=np.float32).reshape(-1)
    great_high = np.asarray(great_candidate_timestamps, dtype=np.float32).reshape(-1)
    n = int(labels.shape[0])
    if any(
        int(values.shape[0]) != n
        for values in (chart, perfect_floor, perfect_high, great_floor, great_high)
    ):
        raise ValueError("exact label hit-interval arrays must have one row per note")

    chart_ms = np.asarray(floor_to_int_ms(chart), dtype=np.int64)
    fixed_timing = bool(
        np.array_equal(perfect_floor, chart)
        and np.array_equal(perfect_high, chart)
        and np.array_equal(great_floor, chart)
        and np.array_equal(great_high, chart)
    )
    if fixed_timing:
        # The explicit zero-ms/baseline mode disables judgment-window carry: every selected label is
        # materialized on its one fixed hit timeline. Great still changes score/fill, but cannot move
        # the event earlier or later in this semantic mode.
        invalid_low = np.full(n, np.float32(np.inf), dtype=np.float32)
        invalid_high = np.full(n, np.float32(-np.inf), dtype=np.float32)
        return chart.copy(), chart.copy(), invalid_low, invalid_high

    perfect_high_ms = np.rint(np.asarray(perfect_high, dtype=np.float64) * 1000.0).astype(np.int64)
    perfect_upper_ms = perfect_high_ms - chart_ms
    if bool(np.any((perfect_upper_ms != 40) & (perfect_upper_ms != 80))):
        raise ValueError("Perfect candidate envelope must use the exact +40ms/+80ms engine windows")
    width = perfect_upper_ms // 40
    perfect_low_ms = chart_ms + (-20 * width + 1)
    great_early_low_ms = chart_ms + (-95 * width + 1)
    great_early_high_ms = chart_ms - 20 * width
    great_late_low_ms = chart_ms + 40 * width + 1
    expected_great_high_ms = chart_ms + np.minimum(190 * width, 200)
    actual_great_high_ms = np.rint(np.asarray(great_high, dtype=np.float64) * 1000.0).astype(np.int64)
    if not bool(np.array_equal(actual_great_high_ms, expected_great_high_ms)):
        raise ValueError("Great candidate envelope must use the exact +190ms/+200ms engine cap")

    raw_perfect_low = perfect_low_ms.astype(np.float32) * np.float32(0.001)
    raw_great_low = great_early_low_ms.astype(np.float32) * np.float32(0.001)
    expected_perfect_floor = np.maximum.accumulate(raw_perfect_low.copy())
    expected_great_floor = np.maximum.accumulate(raw_great_low.copy())
    if not bool(np.array_equal(perfect_floor, expected_perfect_floor)):
        raise ValueError("Perfect floor must be the exact prefix-max raw Perfect-lower envelope")
    if not bool(np.array_equal(great_floor, expected_great_floor)):
        raise ValueError("Great floor must be the exact prefix-max raw Great-lower envelope")

    great_early_high = great_early_high_ms.astype(np.float32) * np.float32(0.001)
    great_late_low = great_late_low_ms.astype(np.float32) * np.float32(0.001)

    primary_low = np.where(labels, raw_great_low, raw_perfect_low).astype(np.float32)
    primary_high = np.where(labels, great_early_high, perfect_high).astype(np.float32)
    secondary_low = np.where(labels, great_late_low, np.float32(np.inf)).astype(np.float32)
    secondary_high = np.where(labels, great_high, np.float32(-np.inf)).astype(np.float32)
    return primary_low, primary_high, secondary_low, secondary_high


def _interval_contains(
    index: int,
    value: float,
    primary_low: np.ndarray,
    primary_high: np.ndarray,
    secondary_low: np.ndarray | None,
    secondary_high: np.ndarray | None,
) -> bool:
    i = int(index)
    hit = float(value)
    if float(primary_low[i]) <= hit <= float(primary_high[i]):
        return True
    return bool(
        secondary_low is not None
        and secondary_high is not None
        and float(secondary_low[i]) <= hit <= float(secondary_high[i])
    )


def _canonical_preactivation_order(
    *,
    selected_by_lane: Sequence[tuple[int, Sequence[int]]],
    activation_hit_timestamp: float,
    predecessor_hit_timestamp: float | None,
    hit_at_or_after,
    note_offset: int,
) -> tuple[int, ...] | None:
    """Materialize one exact score-preserving cross-lane merge.

    Head notes retain chart order because their combo position is score-bearing. Once the 100-note
    ramp is complete, independent lanes are merged by their earliest exact physical hit. Every event
    remains after the preceding fever's wasted boundary note, when one exists. Great labels may have
    two disjoint legal bands; the gap is never treated as a hittable Great timestamp.
    """
    floor = -np.inf if predecessor_hit_timestamp is None else float(predecessor_hit_timestamp)
    h_a = float(activation_hit_timestamp)
    if floor > h_a:
        return None

    selected = tuple(
        int(note_idx)
        for _lane_id, note_indices in selected_by_lane
        for note_idx in note_indices
    )
    off = int(note_offset)
    head = tuple(sorted(note_idx for note_idx in selected if int(note_idx) < 100))
    head_clock = float(floor)
    for note_idx in head:
        hit = hit_at_or_after(int(note_idx) - off, float(head_clock))
        if hit is None or float(hit) > h_a:
            return None
        head_clock = float(hit)

    body_events: list[tuple[float, int, int, int]] = []
    for lane_rank, (_lane_id, note_indices) in enumerate(selected_by_lane):
        lane_clock = float(head_clock)
        lane_pos = 0
        for note_idx_raw in note_indices:
            note_idx = int(note_idx_raw)
            if note_idx < 100:
                continue
            hit = hit_at_or_after(int(note_idx) - off, float(lane_clock))
            if hit is None or float(hit) > h_a:
                return None
            lane_clock = float(hit)
            body_events.append((float(hit), int(lane_rank), int(lane_pos), int(note_idx)))
            lane_pos += 1
    body_events.sort(key=lambda row: (float(row[0]), int(row[1]), int(row[2]), int(row[3])))
    return (*head, *(int(row[3]) for row in body_events))


def activation_schedule_witnesses_weighted_lane_aware(
    *,
    activation_index: int,
    activation_hit_timestamp: float,
    low_hit_timestamps: Sequence[float] | np.ndarray,
    high_hit_timestamps: Sequence[float] | np.ndarray,
    lanes: Sequence[int] | np.ndarray,
    fill_units: Sequence[float] | np.ndarray,
    fever_fill_denom: float,
    section_start: int,
    section_end: int,
    required_preactivation_fill_half_units: int | None = None,
    required_preactivation_event_count: int | None = None,
    secondary_low_hit_timestamps: Sequence[float] | np.ndarray | None = None,
    secondary_high_hit_timestamps: Sequence[float] | np.ndarray | None = None,
    predecessor_hit_timestamp: float | None = None,
) -> tuple[ActivationScheduleWitness, ...]:
    """Return the score-relevant extreme exact lane-prefix witnesses.

    On every non-activation lane, events before ``h_a`` must be a chart-order prefix. A legal
    prefix contains every note whose label window closes before ``h_a`` and contains no note whose
    window opens after it. The activation lane has the one fixed prefix ending immediately before
    ``activation_index``. The cross-lane product is folded on the exact Perfect/Great half-unit
    lattice.

    For a fixed pre-activation fill, body response scoring is affine in the number of events before
    activation (the Great count is ``2*event_count - fill_half_units``). Therefore only the minimum
    and maximum reachable event counts can win for any loadout; intermediate counts lie on the
    segment between them. Both extremes are returned, with deterministic full-equality witnesses.
    Head-order variants are owned separately by the response-surface producer.  When both
    ``required_preactivation_*`` fields are supplied, return the deterministic witness for that
    exact cached-surface signature instead of the unconstrained score-relevant extrema.
    """
    a = int(activation_index)
    start = int(section_start)
    end = int(section_end)
    denom = float(fever_fill_denom)
    if not np.isfinite(denom) or denom <= 0.0:
        raise ValueError("fever_fill_denom must be finite and > 0")
    if start < 0 or end < start:
        raise ValueError("invalid section bounds")
    if (required_preactivation_fill_half_units is None) != (
        required_preactivation_event_count is None
    ):
        raise ValueError("the exact preactivation fill and event-count signature must be supplied together")

    lo = np.asarray(low_hit_timestamps, dtype=np.float32).reshape(-1)
    hi = np.asarray(high_hit_timestamps, dtype=np.float32).reshape(-1)
    if (secondary_low_hit_timestamps is None) != (secondary_high_hit_timestamps is None):
        raise ValueError("secondary hit-interval bounds must be supplied together")
    secondary_lo = (
        None
        if secondary_low_hit_timestamps is None
        else np.asarray(secondary_low_hit_timestamps, dtype=np.float32).reshape(-1)
    )
    secondary_hi = (
        None
        if secondary_high_hit_timestamps is None
        else np.asarray(secondary_high_hit_timestamps, dtype=np.float32).reshape(-1)
    )
    lane_values = np.asarray(lanes, dtype=np.int32).reshape(-1)
    units = np.asarray(fill_units, dtype=np.float32).reshape(-1)
    total = int(lo.shape[0])
    if any(int(values.shape[0]) != total for values in (hi, lane_values, units)):
        raise ValueError("hit timestamps, lanes, and fill_units must have the same length")
    if secondary_lo is not None and secondary_hi is not None and (
        int(secondary_lo.shape[0]) != total or int(secondary_hi.shape[0]) != total
    ):
        raise ValueError("secondary hit timestamps must match the primary interval length")
    if not (start <= a < end <= total):
        raise ValueError("activation_index must be inside [section_start, section_end)")
    # Batched per-note interval precompute over [start, end): the exact same per-note
    # scalar reads the loops below previously issued one numpy scalar at a time, hoisted
    # into vector ops once per call. float32 values embed exactly in float64, and every
    # comparison below keeps the original predicate (lo <= hi validity, not isfinite), so
    # this is a pure batching -- no semantic change.
    off = int(start)
    sl = slice(int(start), int(end))
    p_lo64 = lo[sl].astype(np.float64)
    p_hi64 = hi[sl].astype(np.float64)
    p_finite_valid = np.isfinite(p_lo64) & np.isfinite(p_hi64) & (p_lo64 <= p_hi64)
    if secondary_lo is not None and secondary_hi is not None:
        s_lo64 = secondary_lo[sl].astype(np.float64)
        s_hi64 = secondary_hi[sl].astype(np.float64)
        s_finite_valid = np.isfinite(s_lo64) & np.isfinite(s_hi64) & (s_lo64 <= s_hi64)
        s_ok_arr = s_lo64 <= s_hi64
    else:
        s_lo64 = s_hi64 = None
        s_finite_valid = np.zeros(p_finite_valid.shape, dtype=np.bool_)
        s_ok_arr = s_finite_valid
    if not bool(np.all(p_finite_valid | s_finite_valid)):
        raise ValueError("activation label must have at least one finite non-empty hit interval")
    p_ok_arr = p_lo64 <= p_hi64
    earliest_arr = np.where(p_ok_arr, p_lo64, np.inf)
    latest_arr = np.where(p_ok_arr, p_hi64, -np.inf)
    if s_lo64 is not None:
        earliest_arr = np.minimum(earliest_arr, np.where(s_ok_arr, s_lo64, np.inf))
        latest_arr = np.maximum(latest_arr, np.where(s_ok_arr, s_hi64, -np.inf))
    earliest_l = earliest_arr.tolist()
    latest_l = latest_arr.tolist()
    plo_l = p_lo64.tolist()
    phi_l = p_hi64.tolist()
    p_ok_l = p_ok_arr.tolist()
    slo_l = None if s_lo64 is None else s_lo64.tolist()
    shi_l = None if s_hi64 is None else s_hi64.tolist()
    s_ok_l = None if s_lo64 is None else s_ok_arr.tolist()

    def _hit_at_or_after(rel_idx: int, floor: float) -> float | None:
        # _earliest_interval_hit_at_or_after on the precomputed section lists: identical
        # candidate math (max(floor, lo) per valid band with floor <= hi, then min).
        best: float | None = None
        if p_ok_l[rel_idx]:
            hi_v = phi_l[rel_idx]
            if floor <= hi_v:
                lo_v = plo_l[rel_idx]
                best = floor if floor > lo_v else lo_v
        if slo_l is not None and s_ok_l[rel_idx]:
            hi_v = shi_l[rel_idx]
            if floor <= hi_v:
                lo_v = slo_l[rel_idx]
                candidate = floor if floor > lo_v else lo_v
                if best is None or candidate < best:
                    best = candidate
        return best

    half_units = _exact_fill_half_units(units, start=start, end=end)

    h_a = np.float32(activation_hit_timestamp)
    if not np.isfinite(h_a) or not _interval_contains(
        int(a), float(h_a), lo, hi, secondary_lo, secondary_hi
    ):
        return ()
    h_a_f = float(h_a)
    if predecessor_hit_timestamp is not None and (
        not np.isfinite(float(predecessor_hit_timestamp))
        or float(predecessor_hit_timestamp) > float(h_a)
    ):
        return ()

    required_head_clock: float | None = None
    if required_preactivation_event_count is not None:
        required_head_clock = (
            -np.inf if predecessor_hit_timestamp is None else float(predecessor_hit_timestamp)
        )
        for note_idx in range(int(start), min(int(a), 100)):
            hit = _hit_at_or_after(int(note_idx) - off, float(required_head_clock))
            if hit is None or float(hit) > h_a_f:
                return ()
            required_head_clock = float(hit)

    def _exact_prefix_is_schedulable(notes: Sequence[int], prefix_count: int) -> bool:
        if required_head_clock is None:
            return True
        lane_clock = float(required_head_clock)
        for note_idx_raw in notes[: int(prefix_count)]:
            note_idx = int(note_idx_raw)
            if note_idx < 100:
                continue
            hit = _hit_at_or_after(int(note_idx) - off, float(lane_clock))
            if hit is None or float(hit) > h_a_f:
                return False
            lane_clock = float(hit)
        return True

    lane_order: list[int] = []
    lane_notes: dict[int, list[int]] = {}
    for note_idx in range(start, end):
        lane_id = int(lane_values[int(note_idx)])
        notes = lane_notes.get(lane_id)
        if notes is None:
            lane_order.append(int(lane_id))
            notes = []
            lane_notes[int(lane_id)] = notes
        notes.append(int(note_idx))

    activation_lane = int(lane_values[a])
    lane_options: list[tuple[int, tuple[tuple[int, int], ...]]] = []
    chart_prefix_counts: list[int] = []
    for lane_id in lane_order:
        notes = lane_notes[int(lane_id)]
        chart_prefix_counts.append(sum(1 for note_idx in notes if int(note_idx) < int(a)))
        head_note_count = sum(1 for note_idx in notes if int(note_idx) < 100)
        target_head_count = sum(
            1 for note_idx in notes if int(note_idx) < 100 and int(note_idx) < int(a)
        )
        # Fail loudly if an internally supplied label envelope cannot realize full combo even in
        # its own lane order. This is producer state, not an optional external-boundary recovery.
        lane_clock = (
            -np.inf if predecessor_hit_timestamp is None else float(predecessor_hit_timestamp)
        )
        for note_idx in notes:
            hit = _hit_at_or_after(int(note_idx) - off, float(lane_clock))
            if hit is None:
                raise ValueError("lane label windows cannot realize chart-order full combo")
            lane_clock = float(hit)

        prefix_half = [0]
        for note_idx in notes:
            prefix_half.append(
                int(prefix_half[-1]) + int(half_units[int(note_idx) - int(start)])
            )

        if int(lane_id) == int(activation_lane):
            activation_positions = [pos for pos, note_idx in enumerate(notes) if int(note_idx) == a]
            if len(activation_positions) != 1:
                raise ValueError("activation note must occur exactly once in its lane")
            prefix_count = int(activation_positions[0])
            if any(
                earliest_l[int(note_idx) - off] > h_a_f for note_idx in notes[:prefix_count]
            ):
                return ()
            if any(
                latest_l[int(note_idx) - off] < h_a_f
                for note_idx in notes[prefix_count + 1 :]
            ):
                return ()
            options = ((int(prefix_half[prefix_count]), int(prefix_count)),)
            if required_preactivation_event_count is not None:
                options = tuple(
                    option
                    for option in options
                    if (
                        int(option[1]) == int(target_head_count)
                        if int(target_head_count) < int(head_note_count)
                        else int(option[1]) >= int(target_head_count)
                    )
                )
            options = tuple(
                option
                for option in options
                if _exact_prefix_is_schedulable(notes, int(option[1]))
            )
            if not options:
                return ()
            lane_options.append((int(lane_id), options))
            continue

        minimum_count = 0
        maximum_count = len(notes)
        for pos, note_idx in enumerate(notes):
            if latest_l[int(note_idx) - off] < h_a_f:
                minimum_count = int(pos) + 1
            if (
                earliest_l[int(note_idx) - off] > h_a_f
                and int(maximum_count) == len(notes)
            ):
                maximum_count = int(pos)
        if int(minimum_count) > int(maximum_count):
            return ()
        options = tuple(
            (int(prefix_half[count]), int(count))
            for count in range(int(minimum_count), int(maximum_count) + 1)
        )
        if required_preactivation_event_count is not None:
            options = tuple(
                option
                for option in options
                if (
                    int(option[1]) == int(target_head_count)
                    if int(target_head_count) < int(head_note_count)
                    else int(option[1]) >= int(target_head_count)
                )
            )
        options = tuple(
            option
            for option in options
            if _exact_prefix_is_schedulable(notes, int(option[1]))
        )
        if not options:
            return ()
        lane_options.append((int(lane_id), options))

    def _witness_for_prefixes(
        fill_half: int,
        event_count: int,
        prefixes: tuple[int, ...],
    ) -> ActivationScheduleWitness | None:
        prefix_rows: list[ActivationLanePrefix] = []
        selected_by_lane: list[tuple[int, tuple[int, ...]]] = []
        for (lane_id, _options), prefix_count in zip(lane_options, prefixes, strict=True):
            notes = lane_notes[int(lane_id)]
            selected = tuple(int(note_idx) for note_idx in notes[: int(prefix_count)])
            prefix_rows.append(ActivationLanePrefix(lane=int(lane_id), note_indices=selected))
            selected_by_lane.append((int(lane_id), selected))
        preactivation_order = _canonical_preactivation_order(
            selected_by_lane=selected_by_lane,
            activation_hit_timestamp=float(h_a),
            predecessor_hit_timestamp=predecessor_hit_timestamp,
            hit_at_or_after=_hit_at_or_after,
            note_offset=off,
        )
        if preactivation_order is None:
            return None
        if len(preactivation_order) != int(event_count):
            raise ValueError("activation witness event count does not match its lane prefixes")
        if required_preactivation_event_count is not None:
            expected_head = {
                int(note_idx)
                for note_idx in range(int(start), int(a))
                if int(note_idx) < 100
            }
            selected_head = {
                int(note_idx) for note_idx in preactivation_order if int(note_idx) < 100
            }
            if selected_head != expected_head:
                return None
        great_count = 2 * int(event_count) - int(fill_half)
        if great_count < 0 or great_count > int(event_count):
            raise ValueError("activation witness Great count escaped its exact fill identity")
        return ActivationScheduleWitness(
            activation_index=int(a),
            activation_hit_timestamp=float(h_a),
            section_start=int(start),
            section_end=int(end),
            lane_prefixes=tuple(prefix_rows),
            preactivation_order=preactivation_order,
            preactivation_fill_half_units=int(fill_half),
            preactivation_event_count=int(event_count),
            preactivation_great_count=int(great_count),
        )

    exact_fill = (
        None
        if required_preactivation_fill_half_units is None
        else int(required_preactivation_fill_half_units)
    )
    exact_count = (
        None
        if required_preactivation_event_count is None
        else int(required_preactivation_event_count)
    )
    activation_half = int(half_units[a - start])
    if exact_fill is not None and exact_count is not None:
        # The historical tie rule explicitly prefers chart-prefix counts when they realize the
        # requested surface signature. Prove that preference before building the cross-lane DP;
        # returning it here is the same first selected row, with no combinatorial state expansion.
        preferred = tuple(int(count) for count in chart_prefix_counts)
        preferred_fill = 0
        preferred_is_legal = True
        for (_lane_id, options), prefix_count in zip(lane_options, preferred, strict=True):
            matching = tuple(
                int(option_fill)
                for option_fill, option_count in options
                if int(option_count) == int(prefix_count)
            )
            if len(matching) != 1:
                preferred_is_legal = False
                break
            preferred_fill += int(matching[0])
        if (
            preferred_is_legal
            and sum(preferred) == int(exact_count)
            and int(preferred_fill) == int(exact_fill)
            and 0.5 * float(preferred_fill) < denom
            and denom <= 0.5 * float(preferred_fill + activation_half)
        ):
            preferred_witness = _witness_for_prefixes(
                int(exact_fill), int(exact_count), preferred
            )
            if preferred_witness is not None:
                return (preferred_witness,)

    # (fill half-units, event count) -> per-lane prefix counts. Full tuple equality decides ties.
    states: dict[tuple[int, int], tuple[int, ...]] = {(0, 0): ()}
    fill_limit = float(2.0 * denom)
    for _lane_id, options in lane_options:
        merged: dict[tuple[int, int], tuple[int, ...]] = {}
        for (prior_fill, prior_count), prior_prefixes in states.items():
            for lane_fill, lane_count in options:
                new_fill = int(prior_fill) + int(lane_fill)
                if float(new_fill) >= fill_limit:
                    continue
                new_count = int(prior_count) + int(lane_count)
                if exact_fill is not None and exact_count is not None and (
                    int(new_fill) > int(exact_fill) or int(new_count) > int(exact_count)
                ):
                    continue
                key = (int(new_fill), int(new_count))
                prefixes = (*prior_prefixes, int(lane_count))
                previous = merged.get(key)
                if previous is None or prefixes < previous:
                    merged[key] = prefixes
        states = merged
        if not states:
            return ()

    feasible: dict[int, list[tuple[int, tuple[int, ...]]]] = {}
    for (fill_half, event_count), prefixes in states.items():
        if 0.5 * float(fill_half) < denom <= 0.5 * float(fill_half + activation_half):
            feasible.setdefault(int(fill_half), []).append((int(event_count), prefixes))
    if not feasible:
        return ()

    witnesses: list[ActivationScheduleWitness] = []
    seen_signatures: set[tuple[int, int]] = set()
    for fill_half in sorted(feasible):
        rows = sorted(feasible[int(fill_half)], key=lambda row: (int(row[0]), row[1]))
        if required_preactivation_fill_half_units is not None:
            if int(fill_half) != int(required_preactivation_fill_half_units):
                continue
            selected_rows = tuple(
                row
                for row in rows
                if int(row[0]) == int(required_preactivation_event_count)
            )
        else:
            selected_rows = (rows[0], rows[-1])
        for event_count, prefixes in selected_rows:
            signature = (int(fill_half), int(event_count))
            if signature in seen_signatures:
                continue
            witness = _witness_for_prefixes(int(fill_half), int(event_count), prefixes)
            if witness is None:
                continue
            seen_signatures.add(signature)
            witnesses.append(witness)
    return tuple(witnesses)


def late_great_prefix_is_legal(fill: int, prefix: int, fever_fill_denom: float, first: bool) -> bool:
    """O(1) late-Great gate for the PRODUCTION placement — Perfects + a ``prefix``-Great run, then the
    forced-Great activation ``fill`` notes into the section.

    A late-Great activation right-shifts the fever window (it starts fever from the Great's late hit),
    which is legal ONLY if the server float bar reaches full **on that Great** — not on an earlier
    Perfect. With the section's ``prefix`` forced Greats at the run start and the activation Great at
    offset ``fill`` (``fill-1`` accumulating notes precede it on later sections; ``fill`` on the first
    section, which has no wasted note), the bar in perfect-units just before the activation is::

        bar_before = 0.5*prefix + (perfects before the activation Great)

    and the activation Great is the crossing iff ``bar_before < denom <= bar_before + 0.5`` (a Perfect
    crossed first ⇔ ``bar_before >= denom`` ⇒ phantom; the Great can't reach full ⇔ ``bar_before + 0.5
    < denom`` ⇒ not the crossing). Bit-exact with :func:`late_great_activation_is_legal` over the
    reconstructed placement (verified in ``test_fg_fill_crossing``); this is the form to gate the search
    (set the activation-forced sentinel to -1 when it returns False). Same off-knife-edge float caveat.
    """
    denom = float(fever_fill_denom)
    if denom <= 0.0:
        raise ValueError("fever_fill_denom must be > 0 (a real fill denominator)")
    wasted = 0 if bool(first) else 1  # later sections burn one wasted note where the prior fever ended
    perfects_before = int(fill) - wasted - int(prefix)
    if perfects_before < 0:
        return False  # the activation lands inside the forced-Great run; not a late-Great crossing
    bar_before = 0.5 * float(int(prefix)) + float(perfects_before)
    return bool(bar_before < denom and bar_before + 0.5 >= denom)


def perfect_fill_crossing_offset(fever_fill_denom: float, k: int, first: bool) -> int:
    """Canonical Perfect fill-crossing OFFSET for a fever section that forces ``k`` Greats packed at
    its first accumulating note -- the ONE owner of ``_action_table``'s ``fill``.

    The section's activation note is ``section_state + this`` (later section) or ``this`` (first
    section, which burns no wasted note).  This is ``server_fill_crossing_run``'s region-3 index (the
    crossing is a Perfect after the packed run for every production ``k <= ceil(denom)``; measured
    bit-exact across the whole band -- see the module docstring), whose closed form is
    ``ceil(denom + 0.5*k)`` minus the first-section wasted note.  Kept here next to the walk oracle so
    the Perfect-crossing formula lives in exactly one place.
    """
    fill = int(ceil(float(fever_fill_denom) + 0.5 * float(int(k))))
    return int(fill if not bool(first) else max(0, fill - 1))


def perfect_crossing_is_region3(fill: int, k: int, first: bool, fever_fill_denom: float) -> bool:
    """Whether the Perfect-activation (normal) edge for action ``k`` at offset ``fill`` is the
    region-3 crossing -- the placement the prefix family actually models: ``k`` forced Greats
    packed at the section's first accumulating slot, then Perfects, then the PERFECT activation
    at offset ``fill``.

    Two conditions, both required (record 16.28 follow-up: the fixture's phantom family is the
    normal edges of rows violating them):

    * the forced run must FIT before the activation: ``k <= slots`` where ``slots`` is the number
      of accumulating notes before the activation (``fill`` on a first section, ``fill - 1`` on a
      later one -- the wasted note does not accumulate);
    * the bar must still be short of full after every pre-activation note: ``slots - 0.5*k <
      denom`` (otherwise the crossing happened ON a Great inside the run -- region 2, which is the
      region-run family's placement, priced there with lane-aware reachability).

    The matching upper bound (``denom <= bar_before + 1``) holds by construction for any ``fill``
    produced by :func:`perfect_fill_crossing_offset` for the same ``k``.
    """
    denom = float(fever_fill_denom)
    if denom <= 0.0:
        raise ValueError("fever_fill_denom must be > 0 (a real fill denominator)")
    if int(k) <= 0:
        return True
    slots = int(fill) if bool(first) else int(fill) - 1
    if int(k) > int(slots):
        return False
    return float(slots) - 0.5 * float(int(k)) < denom


def late_great_activation_prefix(fill: int, k: int, first: bool, fever_fill_denom: float) -> int | None:
    """Canonical forced-Great PREFIX for a late-Great activation, or ``None`` if a late-Great is
    illegal there (a Perfect crosses first -> phantom over-report) -- the ONE owner of the late-Great
    placement math that BOTH the search compaction (``_compact_first_frontier_action_arrays``) and the
    reconstruct mirror (``_edge_surface_options``) consume, so the prefix cap +
    :func:`late_great_prefix_is_legal` pair is written once.

    ``prefix`` is the number of forced Greats before the activation Great; the section burns one wasted
    note on later sections (``wasted = 1``) and none on the first (``wasted = 0``).  Returns ``None``
    for ``k <= 0`` (no forced Great to activate on).

    The first-section ``prefix == fill`` placement (every pre-activation slot a Great, the
    activation Great crossing on the run's end) is LEGAL and required: the P/G brute-force oracle
    realizes it and the reconstruct mirror re-finds it (record 16.28's cap-to-``fill - 1``
    direction was refuted by that oracle -- the fixture phantoms were the region-2 NORMAL edges,
    fixed by :func:`perfect_crossing_is_region3`, not this chooser).
    """
    if int(k) <= 0:
        return None
    wasted = 0 if bool(first) else 1
    prefix = min(max(0, int(k) - 1), max(0, int(fill) - wasted))
    if late_great_prefix_is_legal(int(fill), int(prefix), float(fever_fill_denom), first=bool(first)):
        return int(prefix)
    return None


def activation_hit_is_reachable_weighted_lane_aware(
    *,
    activation_index: int,
    activation_hit_timestamp: float,
    low_hit_timestamps: Sequence[float] | np.ndarray,
    high_hit_timestamps: Sequence[float] | np.ndarray,
    lanes: Sequence[int] | np.ndarray,
    fill_units: Sequence[float] | np.ndarray,
    fever_fill_denom: float,
    section_start: int,
    section_end: int,
    secondary_low_hit_timestamps: Sequence[float] | np.ndarray | None = None,
    secondary_high_hit_timestamps: Sequence[float] | np.ndarray | None = None,
    predecessor_hit_timestamp: float | None = None,
) -> bool:
    """Canonical full-combo activation reachability for one concrete hit time.

    This is the ONE input-engine-aware reachability owner: the fragmented lane-blind legacy gates
    were collapsed into it (their deletion landed 2026-07-07, not merely shadowed). An activation is
    legal only when the same weighted, lane-aware hit-time walk that the surface prices can make
    ``activation_index`` the first note whose fill reaches the fever denominator.

    ``fill_units`` is in Perfect-fill units: Perfect = 1.0, Great = 0.5. ``low_hit_timestamps`` and
    ``high_hit_timestamps`` are the legal hit interval for each note under the surface's chosen label.
    A note is forced before ``activation_hit_timestamp`` if either its own latest legal hit is earlier
    on any lane, or it is an earlier same-lane note whose hittable interval still overlaps the
    activation hit. Other cross-lane notes hittable before ``h_a`` are optional capacity: they may be
    scheduled before the activation if needed to reach the crossing, or delayed after it if they would
    preempt. Later same-lane notes cannot supply pre-activation fill while ``a`` is still unhit,
    because earliest-hittable-first would consume ``a`` first.
    """
    return bool(
        activation_schedule_witnesses_weighted_lane_aware(
            activation_index=int(activation_index),
            activation_hit_timestamp=float(activation_hit_timestamp),
            low_hit_timestamps=low_hit_timestamps,
            high_hit_timestamps=high_hit_timestamps,
            lanes=lanes,
            fill_units=fill_units,
            fever_fill_denom=float(fever_fill_denom),
            section_start=int(section_start),
            section_end=int(section_end),
            secondary_low_hit_timestamps=secondary_low_hit_timestamps,
            secondary_high_hit_timestamps=secondary_high_hit_timestamps,
            predecessor_hit_timestamp=predecessor_hit_timestamp,
        )
    )


def server_fill_crossing(
    is_great: Sequence[bool],
    fever_fill_denom: float,
    start: int,
    n: int | None = None,
) -> tuple[int | None, bool]:
    """First note ``>= start`` whose cumulative fill takes the bar full -- placement-aware.

    ``is_great[i]``   : True if note ``i`` is a Great (half fill), False if Perfect (full fill).
    ``fever_fill_denom`` : ScoreEngine ``feverFillDenom`` == optimizer ``raw_fever_fill``
                           (the number of Perfect-fills needed to fill the bar).
    ``start``         : the section's fill-start note (the first ACCUMULATING note; the server
                        "wasted note" where the previous fever ended is already excluded, i.e.
                        ``start`` is the note after it).

    Returns ``(crossing_index, is_great_at_crossing)``, or ``(None, False)`` if the bar never fills
    before the chart ends (fever runs to the end).  Accumulation mirrors ``scoreEngine.ts`` exactly:
    ``bar += 1/denom`` (Perfect) or ``bar += 1/(2*denom)`` (Great), activate on ``bar >= 1``.
    """
    total = len(is_great) if n is None else int(n)
    denom = float(fever_fill_denom)
    if denom <= 0.0:
        raise ValueError("fever_fill_denom must be > 0 (a real fill denominator)")
    great_denom = denom * 2.0
    bar = 0.0
    for i in range(int(start), total):
        bar += (1.0 / great_denom) if is_great[i] else (1.0 / denom)
        if bar >= FEVER_ACTIVATE_AT:
            return i, bool(is_great[i])
    return None, False


def late_great_activation_is_legal(
    is_great: Sequence[bool],
    fever_fill_denom: float,
    start: int,
    activation_index: int,
    n: int | None = None,
) -> bool:
    """The gate: a late-Great activation at ``activation_index`` is legal ONLY if that note is the
    server fill-completion note AND it is itself a Great.

    A late-Great activation right-shifts the fever window (it starts fever from the Great's late
    hit).  That is legal ONLY when the Great is genuinely the note that fills the bar -- if a Perfect
    (or an earlier Great) crosses first, the server activates there, and pretending the later Great
    activates fever is an unreachable window.  When this returns False the caller must fall back to a
    Perfect activation at the true crossing note.
    """
    idx, is_great_at = server_fill_crossing(is_great, fever_fill_denom, start, n=n)
    return idx is not None and int(idx) == int(activation_index) and bool(is_great_at)


# --------------------------------------------------------------------------------------------------
# Fast path -- the same answer as ``server_fill_crossing``, in O(log n).
#
# ``server_fill_crossing`` is the reference oracle (a clear per-note walk).  This prefix-sum +
# ``searchsorted`` form is a MECHANICAL acceleration of it -- the cumulative perfect-units array IS the
# walk's running bar, and ``searchsorted(..., side="left")`` is the first note that reaches full -- so
# it returns the identical index (proven bit-equal to the walk on randomized + real placements in
# ``test_fg_fill_crossing``).  It exists as an ORACLE / kernel-portable reference; production does NOT
# call it -- the hot path uses ``_action_table``'s ``ceil(raw + 0.5k)``, which is itself bit-exact with
# this crossing on the whole production band (region-3 Perfect; measured 0 diffs), so the two agree and
# neither is a mere "hint".
# --------------------------------------------------------------------------------------------------


def fill_prefix_perfect_units(is_great: Sequence[bool]) -> np.ndarray:
    """Inclusive perfect-units fill prefix sum: ``prefix[i] = sum(fill(0..i))`` (Perfect 1, Great ½).

    Precompute once per candidate placement; feed to :func:`server_fill_crossing_fast` per section.
    """
    fills = np.where(np.asarray(is_great, dtype=bool), _GREAT_UNIT, _PERFECT_UNIT)
    return np.cumsum(fills)


def server_fill_crossing_fast(
    fill_prefix: np.ndarray,
    fever_fill_denom: float,
    start: int,
    n: int | None = None,
) -> int | None:
    """O(log n) crossing index -- identical to :func:`server_fill_crossing` (the reference walk).

    ``fill_prefix`` is :func:`fill_prefix_perfect_units` of the candidate placement.  The bar resets
    to 0 at ``start``, so the crossing is the first note whose *inclusive* prefix reaches
    ``prefix[start-1] + denom`` (a Perfect at ``start`` alone would already carry
    ``prefix[start-1] + 1``).  Uses ``side="left"`` -- the ``fever_timeline`` end-search style --
    so the FIRST note ``>= full`` wins.  Returns ``None`` if the bar never fills (fever to the end).
    """
    total = int(len(fill_prefix)) if n is None else int(n)
    denom = float(fever_fill_denom)
    if denom <= 0.0:
        raise ValueError("fever_fill_denom must be > 0 (a real fill denominator)")
    base = float(fill_prefix[int(start) - 1]) if int(start) > 0 else 0.0
    idx = int(np.searchsorted(fill_prefix[:total], base + denom, side="left"))
    if idx < int(start):
        idx = int(start)  # the bar resets at ``start``; the crossing cannot precede it
    if idx >= total:
        return None
    return idx


def server_fill_crossing_run(
    start: int,
    great_run_start: int,
    k: int,
    fever_fill_denom: float,
    n: int,
) -> tuple[int | None, bool]:
    """O(1) crossing for the PRODUCTION placement — Perfects + one contiguous forced-Great run.

    This is the search hot-path form. The FG search forces ``k`` Greats **contiguously** from
    ``great_run_start`` (body Greats beyond the crossing don't affect it); BASE is ``k == 0``. So the
    whole placement the crossing depends on is "all Perfect except a run ``[g0, g0+k)`` of Greats",
    and the crossing is **O(1)** — no per-candidate ``O(n)`` prefix, no ``O(log n)`` search. It costs
    the same as the old ``state_i + ceil(raw + 0.5*k)`` it replaces, but it is *correct*: the bar (in
    perfect-units from ``start``) reaches ``denom`` in exactly one of three places relative to the run,
    each a single ``ceil``:

        region 1  i = start + ceil(D) - 1                        if that i < g0   -> a Perfect
        region 2  i = g0 - 1 + ceil(2*(D - (g0 - start)))        if i < g0 + k    -> a GREAT
        region 3  i = (g0 + k) - 1 + ceil(D - (g0 - start) - 0.5*k)   otherwise   -> a Perfect

    Returns ``(crossing_index, is_great_at_crossing)`` or ``(None, False)`` if the bar never fills
    before note ``n``. **Proven bit-exact** against the ``server_fill_crossing`` walk (ground truth)
    AND ``server_fill_crossing_fast`` on 60k randomized runs across all three regions + base + the clip
    edges (run before ``start`` / past ``n``). Same off-knife-edge caveat as the searchsorted form
    (both compare perfect-units to ``denom``; the ScoreEngine's accumulated bar agrees except at
    measure-zero float boundaries). Pure ints + ``math.ceil`` — numba/Taichi-portable, so this is the
    form to wire into the kernel (NOT the searchsorted).
    """
    s = int(start)
    g0 = int(great_run_start)
    k = int(k)
    D = float(fever_fill_denom)
    N = int(n)
    if D <= 0.0:
        raise ValueError("fever_fill_denom must be > 0 (a real fill denominator)")
    # Clip the Great run to the accumulating region [s, N): Greats before the section start or past
    # the chart do not accumulate.
    run_lo = g0 if g0 > s else s
    run_hi = g0 + k if g0 + k < N else N
    if run_hi <= run_lo:  # no Greats accumulate (base, or the run lies outside [s, N))
        i = s + ceil(D) - 1
        return (i, False) if i < N else (None, False)
    g0 = run_lo
    k = run_hi - run_lo
    perfects_before = g0 - s  # notes [s, g0-1], all Perfect

    # region 1 -- crossing is a Perfect before the run
    i = s + ceil(D) - 1
    if i < g0:
        return (i, False) if i < N else (None, False)

    # region 2 -- crossing lands ON a Great inside the run
    i = g0 - 1 + ceil(2.0 * (D - perfects_before))
    if i < g0 + k:
        if i < g0:
            i = g0
        return (i, True) if i < N else (None, False)

    # region 3 -- crossing is a Perfect after the run
    i = (g0 + k) - 1 + ceil(D - perfects_before - 0.5 * k)
    return (i, False) if i < N else (None, False)


def server_fever_end(
    floor_ts: np.ndarray,
    activation_hit_time: float,
    fever_time_sec: float,
    activation: int,
    n: int | None = None,
) -> int:
    """Canonical drain end — the first note the fever window no longer covers (server-matching).

    Fever drains over a fixed wall-clock duration (``scoreEngine.ts`` ``feverTick``: the bar loses
    ``dt / feverTimeSec`` per frame, hitting 0 after exactly ``fever_time_sec`` seconds).  So the fever
    window in TIME is ``[activation_hit_time, activation_hit_time + fever_time_sec)`` and a note is
    fevered iff it can be hit before the window closes.  Returns the first NON-fever note index; fever
    covers ``[activation, fever_end)`` and note ``fever_end`` is the server 'wasted' note (no fill).

    MAXIMUM REACHABLE coverage comes from the two timing levers, both legal (a real play reaches them):

    * ``activation_hit_time`` is the crossing note's LATEST legal hit.  A Great's late window extends
      further than a Perfect's, so activating on a late Great pushes the window end later and covers
      more notes -- legal ONLY because :func:`server_fill_crossing` decided that Great IS the crossing
      (a Perfect crossing first yields the Perfect's shorter window; no phantom Great extension).
    * the end is searched over ``floor_ts`` (the earliest-legal-hit envelope), so a boundary note the
      player can hit EARLY enough to land inside the window is counted (issue #42, the claw-in).  The
      BASE historical path searched the NOMINAL timestamps instead, under-counting exactly these
      boundary notes -- the base under-report; searching ``floor_ts`` (as FG already does) fixes it.

    ``float32`` on the key matches the GPU precompute and the ScoreEngine's float32 window compare.
    """
    total = int(len(floor_ts)) if n is None else int(n)
    window_end = np.float32(float(activation_hit_time) + float(fever_time_sec))
    end = int(np.searchsorted(floor_ts[:total], window_end, side="left"))
    if end <= int(activation):
        end = int(activation) + 1  # fever always covers at least its own activation note
    if end > total:
        end = total
    return end


def canonical_fever_sections(
    fill_prefix: np.ndarray,
    fever_fill_denom: float,
    drain_end,
    *,
    n: int | None = None,
    first_start: int = 0,
) -> list[tuple[int, int]]:
    """Canonical fever-section stepping for BOTH base and FG — the whole timeline in one forward pass.

    This REPLACES both historical steppings with one loop:
      * BASE ``calculate_fever_timeline_indices`` (``non_fever_base = ceil(...)`` integer note-count),
      * FG ``_action_table`` + ``activation = state_i + fill`` (``fill = ceil(raw + 0.5*k)``),
    which both put activation on an integer note-count rather than the float bar crossing and so land
    one note off once Greats are placed non-uniformly (FG: past the true crossing -> late-Great
    over-report).  It carries no first/later/wasted-note offset arithmetic and no ``ceil`` corrections:

        activation = server_fill_crossing_fast(...)   # AUTO fill crossing (searchsorted, placement-aware)
        fever_end  = drain_end(activation)            # canonical drain -- pass server_fever_end(...)
        next section accumulates from fever_end + 1   # note AT fever_end is the server wasted note

    ``is_great`` (via ``fill_prefix``) all-False gives the BASE timeline; forced-Great positions give
    FG.  ``drain_end(activation:int) -> fever_end:int`` is the drain; production passes a closure over
    :func:`server_fever_end` with the crossing note's latest-legal hit time (the max-reachable lever).
    Because activation is the true crossing and the drain is the true reachable window, the search that
    consumes these sections optimises the real ``body_fever`` and selects the true reachable max -- no
    rescore/verification pass.  Returns the ``(activation, fever_end)`` windows (fever = ``[a, end)``).
    """
    total = int(len(fill_prefix)) if n is None else int(n)
    sections: list[tuple[int, int]] = []
    state = int(first_start)
    # Bounded: every section advances `state` past `fever_end >= activation + 1 > state`.
    for _ in range(total + 1):
        if state >= total:
            break
        activation = server_fill_crossing_fast(fill_prefix, fever_fill_denom, state, n=total)
        if activation is None:
            break  # bar never fills again -> the trailing run is non-fever; timeline complete
        fever_end = int(drain_end(int(activation)))
        if fever_end <= int(activation):
            fever_end = int(activation) + 1  # fever always covers at least its activation note
        sections.append((int(activation), int(fever_end)))
        state = int(fever_end) + 1  # skip the wasted note at fever_end; the bar resets after it
    return sections


# Historical name kept for the FG call sites + tests; base and FG now share this one stepping.
fg_canonical_fever_sections = canonical_fever_sections
