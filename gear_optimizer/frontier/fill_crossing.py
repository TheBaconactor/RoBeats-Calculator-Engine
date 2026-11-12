"""The fever fill crossing in closed form: the note that activates fever for the producer's placements.

The game (PlayerScore.lua; the WebPort ScoreEngine matches it) fills the bar by 1/D per Perfect and 1/(2D) per Great,
D the fill denominator, and activates fever on the first note whose own fill takes the bar to full. The producer
places only Perfects and one contiguous forced-Great run per section, so the crossing has closed forms:

  * ``perfect_fill_crossing_offset`` / ``perfect_crossing_is_region3``: a section's Perfect activation offset with k
    forced Greats packed at its first accumulating note (``ceil(D + 0.5k)``; the first section has no wasted note),
    and whether that placement is the one the prefix family models;
  * ``late_great_prefix_is_legal`` / ``late_great_activation_prefix``: whether a late-Great activation is the
    crossing (the bar must fill ON that Great, not on an earlier Perfect) and its forced-Great prefix.

The crossing of a whole placement, in one of three regions (a Perfect before the run, a Great inside it, a Perfect
after it), is producer_kernels.fill_crossing_run. tests/parity/force_greats/fill_crossing_walk.py walks the notes
one by one; tests/test_fg_fill_crossing.py proves every closed form bit-exact against that walk. activation_witness.py
answers the per-hit question for a concrete label stream.
"""

from __future__ import annotations

from math import ceil


def late_great_prefix_is_legal(fill: int, prefix: int, fever_fill_denom: float, first: bool) -> bool:
    """Whether a late-Great activation `fill` notes into a section is the fill crossing, when `prefix` forced Greats
    start the section and Perfects follow up to the activation Great.

    A late-Great activation starts fever from the Great's late hit, which the game does only if the bar fills on that
    Great. `fill` accumulating notes precede it in the first section and `fill - 1` in a later one, whose first note
    (where the previous fever ended) is wasted. In Perfect units the bar before the activation is
    ``0.5 * prefix + the Perfects before it``, and the Great is the crossing iff that is less than the denominator by
    at most half a unit: at or past the denominator a Perfect filled the bar first, further below it the Great cannot
    fill it. Exact off the measure-zero float knife-edge where the game's accumulated bar and this sum disagree."""
    if fever_fill_denom <= 0.0:
        raise ValueError("fever_fill_denom must be > 0 (a real fill denominator)")
    perfects_before = fill - (0 if first else 1) - prefix
    if perfects_before < 0:
        return False  # the activation lies inside the forced-Great run
    bar_before = 0.5 * prefix + perfects_before
    return bar_before < fever_fill_denom <= bar_before + 0.5


def perfect_fill_crossing_offset(fever_fill_denom: float, k: int, first: bool) -> int:
    """The Perfect activation's offset in a section that forces `k` Greats packed at its first accumulating note: the
    one owner of ``producer_batch.action_table``'s fills.

    The activation note is the section's state plus this offset in a later section, and this offset itself in the
    first section, which has no wasted note. It is the region-3 crossing of producer_kernels.fill_crossing_run
    (a Perfect after the packed run): ``ceil(denom + 0.5 * k)``, less the wasted note in the first section."""
    fill = ceil(fever_fill_denom + 0.5 * k)
    return max(0, fill - 1) if first else fill


def perfect_crossing_is_region3(fill: int, k: int, first: bool, fever_fill_denom: float) -> bool:
    """Whether the Perfect activation of action `k` at offset `fill` is the region-3 crossing, the placement the prefix
    family models: `k` forced Greats packed at the section's first accumulating note, then Perfects, then the Perfect
    activation.

    The forced run must fit before the activation (``k <= slots``, the accumulating notes before it: `fill` in the
    first section, ``fill - 1`` in a later one), and the bar must still be short of full after them
    (``slots - 0.5 * k < denom``): otherwise the bar fills on a Great inside the run, the region-run family's
    placement. The matching upper bound holds for any `fill` perfect_fill_crossing_offset gives for the same `k`."""
    if fever_fill_denom <= 0.0:
        raise ValueError("fever_fill_denom must be > 0 (a real fill denominator)")
    if k <= 0:
        return True
    slots = fill if first else fill - 1
    return k <= slots and slots - 0.5 * k < fever_fill_denom


def late_great_activation_prefix(fill: int, k: int, first: bool, fever_fill_denom: float) -> int | None:
    """The forced Greats before a late-Great activation at offset `fill` for action `k`, or None where no late Great
    activates (`k` forces none, or a Perfect fills the bar first), for producer_batch.compact_action_table;
    trace/section_kernels.py computes the same prefix.

    The prefix is ``k - 1``, capped at the accumulating notes before the activation. In the first section that cap is
    `fill` itself: every note before the activation Great a Great, the bar filling on the run's last one."""
    if k <= 0:
        return None
    prefix = min(k - 1, max(0, fill - (0 if first else 1)))
    return prefix if late_great_prefix_is_legal(fill, prefix, fever_fill_denom, first) else None
