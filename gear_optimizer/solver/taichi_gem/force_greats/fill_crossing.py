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


def late_great_activation_prefix(fill: int, k: int, first: bool, fever_fill_denom: float) -> int | None:
    """Canonical forced-Great PREFIX for a late-Great activation, or ``None`` if a late-Great is
    illegal there (a Perfect crosses first -> phantom over-report) -- the ONE owner of the late-Great
    placement math that BOTH the search compaction (``_compact_first_frontier_action_arrays``) and the
    reconstruct mirror (``_edge_surface_options``) consume, so the ``min(k-1, fill - wasted)`` +
    :func:`late_great_prefix_is_legal` pair is written once.

    ``prefix`` is the number of forced Greats before the activation Great; the section burns one wasted
    note on later sections (``wasted = 1``) and none on the first (``wasted = 0``).  Returns ``None``
    for ``k <= 0`` (no forced Great to activate on).
    """
    if int(k) <= 0:
        return None
    wasted = 0 if bool(first) else 1
    prefix = min(max(0, int(k) - 1), max(0, int(fill) - wasted))
    if late_great_prefix_is_legal(int(fill), int(prefix), float(fever_fill_denom), first=bool(first)):
        return int(prefix)
    return None


# The widest chart-time span (seconds) over which two notes' LATEST-legal hits can reorder relative
# to chart/array order: a held-tail Great late edge reaches ~+0.38s (note-removal-capped shorter),
# a normal Great ~+0.19s. 0.5s is a safe superset -- two notes farther apart than this in chart time
# keep chart order in hit-time, so outside this bounded window the hit-time crossing IS the index
# crossing and the O(1) count gate is already exact. The reachability correction below therefore
# scans only this bounded neighbourhood of the activation, never the whole section.
_MAX_HITTIME_REORDER_SPAN_S = 0.5


def late_great_activation_is_reachable(
    *,
    fill: int,
    prefix: int,
    fever_fill_denom: float,
    first: bool,
    activation_index: int,
    section_start: int,
    forced_start: int,
    timestamps: Sequence[float] | np.ndarray,
    perfect_candidate_timestamps: Sequence[float] | np.ndarray,
    great_candidate_timestamps: Sequence[float] | np.ndarray,
    n: int,
) -> bool:
    """HIT-TIME-ORDER reachability of a late-Great activation on ``activation_index``.

    :func:`late_great_prefix_is_legal` counts the pre-activation fill by ARRAY INDEX; that equals the
    physical (latest-legal-hit-order) fill ONLY where chart order == hit-time order. Inside an overlap
    window (a same-timestamp chord, or a wide held tail beside a narrow note) they diverge, and the
    index gate can bless an activation whose bar is actually completed FIRST by an earlier-hit sibling
    -- the chord phantom (e.g. All Right There: a +198ms held-tail Great "activation" whose two
    on-time normal siblings fill the bar at ~+40ms). Reachability is a scheduling condition: with each
    note hit anywhere in its own window and processed in hit-time order, the bar must first reach
    ``denom`` EXACTLY on the activation. The forced-before set uses each note's LATEST legal hit
    (``cand``); a note whose latest hit still precedes the activation's hit is unavoidably before it::

        must_precede = sum of unit_i over { i in [start,n), i != a, cand_i < h_a }   (unit: Perfect 1, forced-Great 1/2)
        reachable    = must_precede < denom <= must_precede + 0.5

    ``must_precede`` is the index-order ``bar_before`` plus a BOUNDED-LOCAL correction over only the
    notes within :data:`_MAX_HITTIME_REORDER_SPAN_S` of ``a`` whose latest hit can cross ``h_a``
    (chord siblings + near neighbours). Off overlap the correction is exactly 0, so this returns the
    index gate's verdict verbatim -- non-overlapping charts are bit-identical and pay no extra cost.
    A straddling note-ahead (earliest hit before ``h_a`` but latest hit after it) is delayable past
    the activation, so it is NOT counted -- a genuinely reachable late tail is never downgraded.
    """
    denom = float(fever_fill_denom)
    a = int(activation_index)
    wasted = 0 if bool(first) else 1
    perfects_before = int(fill) - wasted - int(prefix)
    if perfects_before < 0:
        return False
    bar_before = 0.5 * float(int(prefix)) + float(perfects_before)  # must_precede under index order
    ts = timestamps
    pc = perfect_candidate_timestamps
    gc = great_candidate_timestamps
    h_a = float(gc[a])  # the activation Great's own latest legal hit
    forced_lo = int(forced_start)
    forced_hi = int(forced_start) + int(prefix)  # forced-Great run [forced_lo, forced_hi)
    total = int(n)
    start = int(section_start)
    delta = 0.0
    # Notes AFTER a whose latest hit precedes h_a -> hit before a in physical order, so they belong in
    # must_precede but index order placed them after a. They are Perfects (the forced run is the
    # prefix, all < a). Bounded: once chart time reaches h_a, every later note's latest hit >= h_a.
    j = a + 1
    while j < total and float(ts[j]) < h_a:
        if float(pc[j]) < h_a:
            delta += 1.0
        j += 1
    # Notes BEFORE a whose latest hit is at/after h_a -> they can be delayed past a, so the index
    # count wrongly included them; remove their unit (1/2 inside the forced run, else a Perfect 1).
    j = a - 1
    while j >= start and (h_a - float(ts[j])) < _MAX_HITTIME_REORDER_SPAN_S:
        in_forced = forced_lo <= j < forced_hi
        cand_j = float(gc[j]) if in_forced else float(pc[j])
        if cand_j >= h_a:
            delta -= 0.5 if in_forced else 1.0
        j -= 1
    must_precede = bar_before + delta
    return (must_precede < denom) and (must_precede + 0.5 >= denom)


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
