"""The fever fill-crossing walk: the oracle that proves the production closed forms in fill_crossing.py.

``server_fill_crossing`` walks the notes applying the ScoreEngine's fill (a Perfect adds ``1/feverFillDenom``, a
Great half of it) and activates on the first note whose own fill takes the bar to full; ``server_fill_crossing_fast``
is the same answer by prefix sum + searchsorted; ``server_fever_end`` is the canonical drain; and
``canonical_fever_sections`` steps a whole timeline with them. Production never calls these: its O(1) closed forms
(``server_fill_crossing_run``, ``late_great_prefix_is_legal``, ``_action_table``'s ``ceil(raw + 0.5k)``) are proven
bit-exact against them in tests/test_fg_fill_crossing.py. The module docstring of fill_crossing.py explains the
model.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

from gear_optimizer.solver.taichi_gem.force_greats.fill_crossing import _GREAT_UNIT, _PERFECT_UNIT

# The bar activates fever the instant a hit's own fill takes it to full (PlayerScore.lua; the
# WebPort ScoreEngine gate ``feverBar >= SCORING.FEVER_ACTIVATE_AT``).
FEVER_ACTIVATE_AT = 1.0


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
