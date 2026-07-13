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
    half = np.empty(int(end) - int(start), dtype=np.int8)
    for offset, value in enumerate(fill_units[int(start) : int(end)]):
        numeric = float(value)
        if numeric == _GREAT_UNIT:
            half[int(offset)] = np.int8(1)
        elif numeric == _PERFECT_UNIT:
            half[int(offset)] = np.int8(2)
        else:
            raise ValueError("fill_units must contain only exact Perfect (1.0) or Great (0.5) units")
    return half


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
    lane_values = np.asarray(lanes, dtype=np.int32).reshape(-1)
    units = np.asarray(fill_units, dtype=np.float32).reshape(-1)
    total = int(lo.shape[0])
    if any(int(values.shape[0]) != total for values in (hi, lane_values, units)):
        raise ValueError("hit timestamps, lanes, and fill_units must have the same length")
    if not (start <= a < end <= total):
        raise ValueError("activation_index must be inside [section_start, section_end)")
    if np.any(~np.isfinite(lo[start:end])) or np.any(~np.isfinite(hi[start:end])):
        raise ValueError("activation hit intervals must be finite")
    if np.any(lo[start:end] > hi[start:end]):
        raise ValueError("activation hit intervals must be non-empty")
    half_units = _exact_fill_half_units(units, start=start, end=end)

    h_a = np.float32(activation_hit_timestamp)
    if not np.isfinite(h_a) or h_a < lo[a] or h_a > hi[a]:
        return ()

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
        lane_clock = -np.inf
        for note_idx in notes:
            lane_clock = max(float(lane_clock), float(lo[int(note_idx)]))
            if lane_clock > float(hi[int(note_idx)]):
                raise ValueError("lane label windows cannot realize chart-order full combo")

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
            if any(lo[int(note_idx)] > h_a for note_idx in notes[:prefix_count]):
                return ()
            if any(hi[int(note_idx)] < h_a for note_idx in notes[prefix_count + 1 :]):
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
            if not options:
                return ()
            lane_options.append((int(lane_id), options))
            continue

        minimum_count = 0
        maximum_count = len(notes)
        for pos, note_idx in enumerate(notes):
            if hi[int(note_idx)] < h_a:
                minimum_count = int(pos) + 1
            if lo[int(note_idx)] > h_a and int(maximum_count) == len(notes):
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
        if not options:
            return ()
        lane_options.append((int(lane_id), options))

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
                key = (int(new_fill), int(new_count))
                prefixes = (*prior_prefixes, int(lane_count))
                previous = merged.get(key)
                if previous is None or prefixes < previous:
                    merged[key] = prefixes
        states = merged
        if not states:
            return ()

    activation_half = int(half_units[a - start])
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
            preferred = tuple(int(count) for count in chart_prefix_counts)
            preferred_fill = 0
            preferred_is_legal = True
            for (_lane_id, options), prefix_count in zip(
                lane_options,
                preferred,
                strict=True,
            ):
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
                and sum(preferred) == int(required_preactivation_event_count)
                and int(preferred_fill) == int(required_preactivation_fill_half_units)
            ):
                selected_rows = ((int(required_preactivation_event_count), preferred),)
        else:
            selected_rows = (rows[0], rows[-1])
        for event_count, prefixes in selected_rows:
            signature = (int(fill_half), int(event_count))
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)
            prefix_rows: list[ActivationLanePrefix] = []
            ordered_events: list[tuple[float, int, int, int]] = []
            for lane_rank, ((lane_id, _options), prefix_count) in enumerate(
                zip(lane_options, prefixes, strict=True)
            ):
                notes = lane_notes[int(lane_id)]
                selected = tuple(int(note_idx) for note_idx in notes[: int(prefix_count)])
                prefix_rows.append(ActivationLanePrefix(lane=int(lane_id), note_indices=selected))
                lane_clock = -np.inf
                for lane_pos, note_idx in enumerate(selected):
                    lane_clock = max(float(lane_clock), float(lo[int(note_idx)]))
                    if lane_clock > min(float(hi[int(note_idx)]), float(h_a)):
                        raise ValueError("selected lane prefix cannot be scheduled before activation")
                    ordered_events.append(
                        (float(lane_clock), int(lane_rank), int(lane_pos), int(note_idx))
                    )
            if prefixes == tuple(chart_prefix_counts):
                preactivation_order = tuple(range(int(start), int(a)))
            else:
                ordered_events.sort(key=lambda row: (float(row[0]), int(row[1]), int(row[2])))
                preactivation_order = tuple(int(row[3]) for row in ordered_events)
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
                    continue
            great_count = 2 * int(event_count) - int(fill_half)
            if great_count < 0 or great_count > int(event_count):
                raise ValueError("activation witness Great count escaped its exact fill identity")
            witnesses.append(
                ActivationScheduleWitness(
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
            )
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
