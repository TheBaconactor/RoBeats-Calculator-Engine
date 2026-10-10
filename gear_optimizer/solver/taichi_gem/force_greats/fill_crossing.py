"""The fever fill crossing in closed form: the note that activates fever for the producer's placements.

The game (PlayerScore.lua; the WebPort ScoreEngine matches it) fills the bar by 1/D per Perfect and 1/(2D) per Great,
D the fill denominator, and activates fever on the first note whose own fill takes the bar to full. The producer
places only Perfects and one contiguous forced-Great run per section, so the crossing has closed forms:

  * ``server_fill_crossing_run``: the crossing of such a placement in O(1), in one of three regions (a Perfect before
    the run, a Great inside it, a Perfect after it);
  * ``perfect_fill_crossing_offset`` / ``perfect_crossing_is_region3``: a section's Perfect activation offset with k
    forced Greats packed at its first accumulating note (``ceil(D + 0.5k)``; the first section has no wasted note),
    and whether that placement is the one the prefix family models;
  * ``late_great_prefix_is_legal`` / ``late_great_activation_prefix``: whether a late-Great activation is the
    crossing (the bar must fill ON that Great, not on an earlier Perfect) and its forced-Great prefix.

tests/parity/force_greats/fill_crossing_walk.py walks the notes one by one; tests/test_fg_fill_crossing.py proves
every closed form bit-exact against that walk. activation_witness.py answers the per-hit question for a concrete
label stream.
"""

from __future__ import annotations

from math import ceil


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
    its first accumulating note -- the ONE owner of ``response_build_gpu_batch.action_table``'s ``fill``.

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
