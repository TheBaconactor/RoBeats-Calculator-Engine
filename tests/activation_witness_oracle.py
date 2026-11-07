"""The general activation-witness search, the tests' oracle: every lane-prefix partition an activation hit allows.

Production asks only for the chart-order prefix (activation_witness.chart_prefix_witness): no stored plan of the catalog
ever held another. The search stays here as an independent reading of what the frontier may price.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

from gear_optimizer.trace.activation_witness import LabelHitIntervals, exact_label_hit_intervals

_HEAD_NOTES = 100

__all__ = ["ActivationLanePrefix", "ActivationScheduleWitness", "LabelHitIntervals", "activation_schedule_witnesses",
           "exact_label_hit_intervals"]


@dataclass(frozen=True, slots=True)
class ActivationLanePrefix:
    """One lane's exact before-activation prefix in immutable chart ordinals."""

    lane: int
    note_indices: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class ActivationScheduleWitness:
    """The exact full-combo event partition chosen for one activation.

    ``lane_prefixes`` is sufficient for the input matcher: on every lane, exactly the listed chart-order prefix is
    consumed before the activation. ``preactivation_order`` is the concrete cross-lane merge replay uses (ties are
    intentional input order, not a downstream guess). The half-unit and count fields are the response-surface
    signature the producer prices.
    """

    lane_prefixes: tuple[ActivationLanePrefix, ...]
    preactivation_order: tuple[int, ...]
    preactivation_fill_half_units: int
    preactivation_event_count: int
    preactivation_great_count: int


class _Section:
    """One activation's question over the notes [start, end): each note's hit bands as Python floats (the loops read one
    note at a time), the activation hit, and the clocks the section's inputs start from."""

    __slots__ = (
        "start", "activation", "hit", "first_clock", "head_clock", "half_units", "primary_ok", "primary_low",
        "primary_high", "secondary_ok", "secondary_low", "secondary_high", "earliest", "latest",
    )

    def __init__(
        self,
        labels: LabelHitIntervals,
        *,
        start: int,
        end: int,
        activation: int,
        hit: float,
        first_clock: float,
    ) -> None:
        part = slice(start, end)
        primary_low = labels.primary_low[part].astype(np.float64)
        primary_high = labels.primary_high[part].astype(np.float64)
        secondary_low = labels.secondary_low[part].astype(np.float64)
        secondary_high = labels.secondary_high[part].astype(np.float64)
        primary_ok = primary_low <= primary_high
        secondary_ok = secondary_low <= secondary_high
        finite_primary = np.isfinite(primary_low) & np.isfinite(primary_high) & primary_ok
        finite_secondary = np.isfinite(secondary_low) & np.isfinite(secondary_high) & secondary_ok
        if not bool(np.all(finite_primary | finite_secondary)):
            raise ValueError("activation label must have at least one finite non-empty hit interval")
        self.start = start
        self.activation = activation
        self.hit = hit
        self.first_clock = first_clock
        # The clock after the head notes before the activation, when an exact surface signature is required.
        self.head_clock: float | None = None
        self.half_units = np.where(labels.is_great[part], 1, 2).tolist()
        self.primary_ok, self.primary_low, self.primary_high = (
            primary_ok.tolist(), primary_low.tolist(), primary_high.tolist()
        )
        self.secondary_ok, self.secondary_low, self.secondary_high = (
            secondary_ok.tolist(), secondary_low.tolist(), secondary_high.tolist()
        )
        self.earliest = np.minimum(
            np.where(primary_ok, primary_low, np.inf), np.where(secondary_ok, secondary_low, np.inf)
        ).tolist()
        self.latest = np.maximum(
            np.where(primary_ok, primary_high, -np.inf), np.where(secondary_ok, secondary_high, -np.inf)
        ).tolist()

    def contains(self, note: int, hit: float) -> bool:
        i = note - self.start
        return (
            self.primary_low[i] <= hit <= self.primary_high[i]
            or self.secondary_low[i] <= hit <= self.secondary_high[i]
        )

    def at_or_after(self, note: int, floor: float) -> float | None:
        """Chart note ``note``'s earliest legal hit no earlier than ``floor``; None once its windows have closed."""
        i = note - self.start
        best = None
        if self.primary_ok[i] and floor <= self.primary_high[i]:
            low = self.primary_low[i]
            best = floor if floor > low else low
        if self.secondary_ok[i] and floor <= self.secondary_high[i]:
            low = self.secondary_low[i]
            candidate = floor if floor > low else low
            if best is None or candidate < best:
                best = candidate
        return best

    def walk(self, notes: Iterable[int], clock: float, deadline: float) -> float | None:
        """Hit ``notes`` in order from ``clock``, each as early as it can be: the last hit, or None when a note cannot
        be hit by ``deadline``."""
        for note in notes:
            hit = self.at_or_after(note, clock)
            if hit is None or hit > deadline:
                return None
            clock = hit
        return clock

    def lane_options(self, notes: list[int], activation_lane: bool) -> tuple[tuple[int, int], ...]:
        """The lane's legal before-activation prefixes as (fill half-units, note count); none: unreachable.

        The activation lane has one prefix, the notes before the activation. Another lane must consume every note whose
        windows close before the activation hit and none whose windows open after it.
        """
        prefix_half = [0]
        for note in notes:
            prefix_half.append(prefix_half[-1] + self.half_units[note - self.start])
        if activation_lane:
            count = notes.index(self.activation)
            if any(self.earliest[note - self.start] > self.hit for note in notes[:count]):
                return ()
            if any(self.latest[note - self.start] < self.hit for note in notes[count + 1 :]):
                return ()
            counts: Iterable[int] = (count,)
        else:
            minimum, maximum = 0, len(notes)
            for position, note in enumerate(notes):
                if self.latest[note - self.start] < self.hit:
                    minimum = position + 1
                if self.earliest[note - self.start] > self.hit and maximum == len(notes):
                    maximum = position
            if minimum > maximum:
                return ()
            counts = range(minimum, maximum + 1)
        if self.head_clock is not None:
            # The required signature keeps every head note before the activation, and no head note after it.
            head_notes = sum(1 for note in notes if note < _HEAD_NOTES)
            target = sum(1 for note in notes if note < _HEAD_NOTES and note < self.activation)
            counts = [count for count in counts if (count == target if target < head_notes else count >= target)]
            counts = [
                count
                for count in counts
                if self.walk((note for note in notes[:count] if note >= _HEAD_NOTES), self.head_clock, self.hit)
                is not None
            ]
        return tuple((prefix_half[count], count) for count in counts)

    def preactivation_order(self, prefixes: Sequence[tuple[int, ...]]) -> tuple[int, ...] | None:
        """One exact score-preserving cross-lane merge of the lanes' prefixes.

        Head notes keep chart order. After the combo ramp, independent lanes merge by their earliest exact hit, every
        event after the preceding fever's wasted boundary note. A Great's gap between its two bands is never a hit.
        """
        head = sorted(note for notes in prefixes for note in notes if note < _HEAD_NOTES)
        head_clock = self.walk(head, self.first_clock, self.hit)
        if head_clock is None:
            return None
        body: list[tuple[float, int, int, int]] = []
        for rank, notes in enumerate(prefixes):
            clock = head_clock
            position = 0
            for note in notes:
                if note < _HEAD_NOTES:
                    continue
                hit = self.at_or_after(note, clock)
                if hit is None or hit > self.hit:
                    return None
                clock = hit
                body.append((hit, rank, position, note))
                position += 1
        body.sort()
        return (*head, *(row[3] for row in body))

    def witness(
        self, lanes: Sequence[tuple[int, list[int]]], counts: Sequence[int], fill_half: int
    ) -> ActivationScheduleWitness | None:
        prefixes = [tuple(notes[:count]) for (_lane, notes), count in zip(lanes, counts, strict=True)]
        order = self.preactivation_order(prefixes)
        if order is None:
            return None
        if self.head_clock is not None and {note for note in order if note < _HEAD_NOTES} != set(
            range(self.start, min(self.activation, _HEAD_NOTES))
        ):
            return None
        return ActivationScheduleWitness(
            lane_prefixes=tuple(
                ActivationLanePrefix(lane=lane, note_indices=prefix)
                for (lane, _notes), prefix in zip(lanes, prefixes, strict=True)
            ),
            preactivation_order=order,
            preactivation_fill_half_units=fill_half,
            preactivation_event_count=len(order),
            preactivation_great_count=2 * len(order) - fill_half,
        )


def _prefix_states(
    options: Sequence[tuple[tuple[int, int], ...]], fill_limit: float, required: tuple[int, int] | None
) -> dict[tuple[int, int], tuple[int, ...]]:
    """(fill half-units, event count) -> the smallest per-lane prefix-count tuple reaching it below ``fill_limit``."""
    states: dict[tuple[int, int], tuple[int, ...]] = {(0, 0): ()}
    for lane_options in options:
        merged: dict[tuple[int, int], tuple[int, ...]] = {}
        for (prior_fill, prior_count), prior_prefixes in states.items():
            for lane_fill, lane_count in lane_options:
                fill = prior_fill + lane_fill
                if fill >= fill_limit:
                    continue
                count = prior_count + lane_count
                if required is not None and (fill > required[0] or count > required[1]):
                    continue
                prefixes = (*prior_prefixes, lane_count)
                previous = merged.get((fill, count))
                if previous is None or prefixes < previous:
                    merged[(fill, count)] = prefixes
        states = merged
        if not states:
            break
    return states


def activation_schedule_witnesses(
    *,
    labels: LabelHitIntervals,
    lanes: Sequence[int] | np.ndarray,
    activation_index: int,
    activation_hit_timestamp: float,
    fever_fill_denom: float,
    section_start: int,
    predecessor_hit_timestamp: float | None,
    required_signature: tuple[int, int] | None = None,
) -> tuple[ActivationScheduleWitness, ...]:
    """The score-relevant extreme exact lane-prefix witnesses of one activation hit; none: it is unreachable.

    The activation is legal only when the weighted, lane-aware hit-time walk the surface prices can make
    ``activation_index`` the first note whose fill (Perfect 2 half-units, Great 1) reaches the fever denominator.
    On every lane the events before the hit ``h_a`` are a chart-order prefix: it holds every note whose label windows
    close before ``h_a`` and none whose windows open after it; the activation lane's prefix ends right before the
    activation. Later same-lane notes cannot fill the bar while the activation is unhit (earliest-hittable-first
    would consume the activation first). The cross-lane product folds on the exact half-unit lattice.

    For a fixed pre-activation fill the body response score is affine in the event count (Great count = 2 x events
    - fill), so only the minimum and maximum reachable counts can win for any loadout: both are returned, each with a
    deterministic witness. ``required_signature`` = (fill half-units, event count) asks instead for the one witness of
    that cached-surface signature; the scored chart-order prefixes win when they realize it.
    """
    a = int(activation_index)
    start = int(section_start)
    denom = float(fever_fill_denom)
    if not np.isfinite(denom) or denom <= 0.0:
        raise ValueError("fever_fill_denom must be finite and > 0")
    labels = LabelHitIntervals(
        np.asarray(labels.is_great, dtype=np.bool_).reshape(-1),
        *(np.asarray(values, dtype=np.float32).reshape(-1) for values in labels[1:]),
    )
    lane_values = np.asarray(lanes, dtype=np.int32).reshape(-1)
    n = int(labels.is_great.shape[0])
    if start < 0 or n < start:
        raise ValueError("invalid section bounds")
    if any(int(values.shape[0]) != n for values in (*labels, lane_values)):
        raise ValueError("labels, hit intervals and lanes must have one row per note")
    if not start <= a < n:
        raise ValueError("activation_index must be inside [section_start, note count)")
    h_a = np.float32(activation_hit_timestamp)
    # The notes that open after the hit, and every note after them, are out of the question: no prefix reaches them, and
    # their windows cannot close before the hit. The head stays whole, its notes are counted against the signature.
    opens_after = np.minimum.accumulate(np.minimum(labels.primary_low, labels.secondary_low)[::-1])[::-1]
    end = max(a + 1, min(n, _HEAD_NOTES), int(np.searchsorted(opens_after, h_a, side="right")))
    section = _Section(
        labels,
        start=start,
        end=end,
        activation=a,
        hit=float(h_a),
        first_clock=-np.inf if predecessor_hit_timestamp is None else float(predecessor_hit_timestamp),
    )
    if not np.isfinite(h_a) or not section.contains(a, section.hit):
        return ()
    if predecessor_hit_timestamp is not None and (
        not np.isfinite(float(predecessor_hit_timestamp)) or float(predecessor_hit_timestamp) > section.hit
    ):
        return ()
    if required_signature is not None:
        section.head_clock = section.walk(range(start, min(a, _HEAD_NOTES)), section.first_clock, section.hit)
        if section.head_clock is None:
            return ()

    # Every lane of the section, in order of its first note: a lane that plays nothing before the hit has an empty prefix.
    section_lanes, first_notes = np.unique(lane_values[start:], return_index=True)
    by_lane: dict[int, list[int]] = {int(section_lanes[i]): [] for i in np.argsort(first_notes)}
    for note, lane in enumerate(lane_values[start:end].tolist(), start):
        by_lane[lane].append(note)
    lanes_in_order = list(by_lane.items())
    activation_lane = int(lane_values[a])
    options = []
    for lane, notes in lanes_in_order:
        lane_options = section.lane_options(notes, lane == activation_lane)
        if not lane_options:
            return ()
        options.append(lane_options)

    activation_half = section.half_units[a - start]
    if required_signature is not None:
        # Prefer the scored chart-order prefixes when they realize the signature: the same first row the search below
        # would select, without its state expansion.
        fill, count = required_signature
        chart_counts = [sum(1 for note in notes if note < a) for _lane, notes in lanes_in_order]
        fills = [
            next((lane_fill for lane_fill, lane_count in lane_options if lane_count == chart_count), None)
            for lane_options, chart_count in zip(options, chart_counts, strict=True)
        ]
        if (
            None not in fills
            and sum(chart_counts) == count
            and sum(fills) == fill
            and 0.5 * sum(fills) < denom <= 0.5 * (sum(fills) + activation_half)
        ):
            witness = section.witness(lanes_in_order, chart_counts, fill)
            if witness is not None:
                return (witness,)

    feasible: dict[int, list[tuple[int, tuple[int, ...]]]] = {}
    for (fill_half, event_count), prefixes in _prefix_states(options, 2.0 * denom, required_signature).items():
        if 0.5 * fill_half < denom <= 0.5 * (fill_half + activation_half):
            feasible.setdefault(fill_half, []).append((event_count, prefixes))
    witnesses: list[ActivationScheduleWitness] = []
    seen: set[tuple[int, int]] = set()
    for fill_half in sorted(feasible):
        rows = sorted(feasible[fill_half])
        if required_signature is None:
            selected = (rows[0], rows[-1])
        elif fill_half == required_signature[0]:
            selected = tuple(row for row in rows if row[0] == required_signature[1])
        else:
            continue
        for event_count, prefixes in selected:
            if (fill_half, event_count) in seen:
                continue
            witness = section.witness(lanes_in_order, prefixes, fill_half)
            if witness is not None:
                seen.add((fill_half, event_count))
                witnesses.append(witness)
    return tuple(witnesses)
