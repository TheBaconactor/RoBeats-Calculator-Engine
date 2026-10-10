"""Exact activation witnesses: the notes a full-combo play hits before a fever activation, lane by lane.

The FG trace reconstruction (response_builder) and the FG persist guard (reducer) ask one question of a concrete
Perfect/Great label stream: hit at ``activation_hit_timestamp``, can ``activation_index`` be the note whose own fill
takes the bar to full, with every note hit inside its label's window and full combo in chart order on every lane?
The witnesses are the answer (none: the activation is unreachable). The frontier producer and its caches never read
this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, NamedTuple, Sequence

import numpy as np

from gear_optimizer.core.time_quantize import quantize_to_int_ms
from gear_optimizer.solver.timing_envelope import HELD_TAIL_WINDOW_SCALE, judgment_bounds

# The combo ramp: these first notes keep chart order, because their combo position is score-bearing.
_HEAD_NOTES = 100


class LabelHitIntervals(NamedTuple):
    """One Perfect/Great label per note and the hit times it allows: the primary band (Perfect, or a Great's early
    band) and the secondary band (a Great's late band; empty, (inf, -inf), for a Perfect)."""

    is_great: np.ndarray
    primary_low: np.ndarray
    primary_high: np.ndarray
    secondary_low: np.ndarray
    secondary_high: np.ndarray


def exact_label_hit_intervals(
    *,
    is_great: Sequence[bool] | np.ndarray,
    timestamps: Sequence[float] | np.ndarray,
    perfect_floor_timestamps: Sequence[float] | np.ndarray,
    perfect_candidate_timestamps: Sequence[float] | np.ndarray,
    great_floor_timestamps: Sequence[float] | np.ndarray,
    great_candidate_timestamps: Sequence[float] | np.ndarray,
) -> LabelHitIntervals:
    """The exact hit intervals of a concrete Perfect/Great label stream.

    A Great's two bands are disjoint: the Perfect band between them is never a Great hit, although the outer envelope
    spans it. The candidate offset tells the normal (+40 ms) from the held-tail (+80 ms) window without note types in
    the stats-free response trace.

    ``perfect_floor_timestamps`` and ``great_floor_timestamps`` are the monotone prefix-max envelopes fever-end search
    owns, not per-note hit-window lows (as such they would lose a held tail's wider early reach): they are validated
    here, and the raw per-note intervals are rebuilt from the quantized chart time and the note's window width.
    """
    labels = np.asarray(is_great, dtype=np.bool_).reshape(-1)
    chart = np.asarray(timestamps, dtype=np.float32).reshape(-1)
    perfect_floor = np.asarray(perfect_floor_timestamps, dtype=np.float32).reshape(-1)
    perfect_high = np.asarray(perfect_candidate_timestamps, dtype=np.float32).reshape(-1)
    great_floor = np.asarray(great_floor_timestamps, dtype=np.float32).reshape(-1)
    great_high = np.asarray(great_candidate_timestamps, dtype=np.float32).reshape(-1)
    n = int(labels.shape[0])
    if any(int(values.shape[0]) != n for values in (chart, perfect_floor, perfect_high, great_floor, great_high)):
        raise ValueError("exact label hit-interval arrays must have one row per note")

    chart_ms = np.asarray(quantize_to_int_ms(chart), dtype=np.int64)
    if (
        np.array_equal(perfect_floor, chart)
        and np.array_equal(perfect_high, chart)
        and np.array_equal(great_floor, chart)
        and np.array_equal(great_high, chart)
    ):
        # Fixed timing (zero ms): every label is hit on its one fixed time. A Great still changes score and fill,
        # but cannot move its input.
        empty_low = np.full(n, np.float32(np.inf), dtype=np.float32)
        empty_high = np.full(n, np.float32(-np.inf), dtype=np.float32)
        return LabelHitIntervals(labels, chart.copy(), chart.copy(), empty_low, empty_high)

    perfect_upper_ms = np.rint(np.asarray(perfect_high, dtype=np.float64) * 1000.0).astype(np.int64) - chart_ms
    tap, tail = judgment_bounds(1), judgment_bounds(HELD_TAIL_WINDOW_SCALE)
    if not np.isin(perfect_upper_ms, (tap.perfect.latest, tail.perfect.latest)).all():
        raise ValueError("Perfect candidate envelope must use Precise's exact latest Perfect offsets")
    is_tail = perfect_upper_ms == tail.perfect.latest

    def offsets_ms(tap_ms: int, tail_ms: int) -> np.ndarray:
        return chart_ms + np.where(is_tail, tail_ms, tap_ms).astype(np.int64)

    perfect_low_ms = offsets_ms(tap.perfect.earliest, tail.perfect.earliest)
    great_early_low_ms = offsets_ms(tap.early_great.earliest, tail.early_great.earliest)
    great_early_high_ms = offsets_ms(tap.early_great.latest, tail.early_great.latest)
    great_late_low_ms = offsets_ms(tap.late_great.earliest, tail.late_great.earliest)
    expected_great_high_ms = offsets_ms(tap.late_great.latest, tail.late_great.latest)
    actual_great_high_ms = np.rint(np.asarray(great_high, dtype=np.float64) * 1000.0).astype(np.int64)
    if not bool(np.array_equal(actual_great_high_ms, expected_great_high_ms)):
        raise ValueError("Great candidate envelope must use the mode's exact latest late-Great offsets")

    raw_perfect_low = perfect_low_ms.astype(np.float32) * np.float32(0.001)
    raw_great_low = great_early_low_ms.astype(np.float32) * np.float32(0.001)
    if not bool(np.array_equal(perfect_floor, np.maximum.accumulate(raw_perfect_low.copy()))):
        raise ValueError("Perfect floor must be the exact prefix-max raw Perfect-lower envelope")
    if not bool(np.array_equal(great_floor, np.maximum.accumulate(raw_great_low.copy()))):
        raise ValueError("Great floor must be the exact prefix-max raw Great-lower envelope")

    great_early_high = great_early_high_ms.astype(np.float32) * np.float32(0.001)
    great_late_low = great_late_low_ms.astype(np.float32) * np.float32(0.001)
    return LabelHitIntervals(
        labels,
        np.where(labels, raw_great_low, raw_perfect_low).astype(np.float32),
        np.where(labels, great_early_high, perfect_high).astype(np.float32),
        np.where(labels, great_late_low, np.float32(np.inf)).astype(np.float32),
        np.where(labels, great_high, np.float32(-np.inf)).astype(np.float32),
    )


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
    """One activation's question over the section [start, n): each note's hit bands as Python floats (the loops read
    one note at a time), the activation hit, and the clocks the section's inputs start from."""

    __slots__ = (
        "start", "activation", "hit", "first_clock", "head_clock", "half_units", "primary_ok", "primary_low",
        "primary_high", "secondary_ok", "secondary_low", "secondary_high", "earliest", "latest",
    )

    def __init__(
        self,
        labels: LabelHitIntervals,
        *,
        start: int,
        activation: int,
        hit: float,
        first_clock: float,
    ) -> None:
        part = slice(start, None)
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
        # Producer state that cannot realize full combo in its own lane order is a bug, not an unreachable activation.
        if self.walk(notes, self.first_clock, np.inf) is None:
            raise ValueError("lane label windows cannot realize chart-order full combo")
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
    section = _Section(
        labels,
        start=start,
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

    by_lane: dict[int, list[int]] = {}
    for note, lane in enumerate(lane_values[start:].tolist(), start):
        notes = by_lane.get(lane)
        if notes is None:
            by_lane[lane] = notes = []
        notes.append(note)
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
