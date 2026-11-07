"""Exact activation witnesses: the notes a full-combo play hits before a fever activation, lane by lane.

The FG trace reconstruction (reconstruct) asks one question of a concrete Perfect/Great label stream: does a hit at the
activation time take the bar to full, with the notes before the activation played first, each inside its label's window
and in chart order on every lane? The witness is the answer. The frontier producer and its caches never read this module.
"""

from __future__ import annotations

from typing import NamedTuple, Sequence

import numpy as np

from gear_optimizer.core.jit_setup import jit
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


class ChartPrefixWitness(NamedTuple):
    """A section's notes before its activation, as a play hits them: `order`, their input order, and `lane_counts`, each
    lane of the section with how many of them it plays."""

    order: tuple[int, ...]
    lane_counts: tuple[tuple[int, int], ...]


@jit(nopython=True, cache=True)
def _earliest_hit(primary_low, primary_high, secondary_low, secondary_high, note, floor):
    """The note's earliest legal hit no earlier than `floor`; inf once its windows have closed."""
    best = np.inf
    if floor <= primary_high[note] and primary_low[note] <= primary_high[note]:
        best = max(floor, primary_low[note])
    if floor <= secondary_high[note] and secondary_low[note] <= secondary_high[note]:
        best = min(best, max(floor, secondary_low[note]))
    return best


@jit(nopython=True, cache=True)
def _prefix_order(bands, lane_ranks, activation, head_end, hit, first_clock):
    """The notes before `activation` in input order, all of a section's arrays from its first note; `head_end` of them are
    head notes, which keep chart order from `first_clock`. Each lane then walks its body notes from the head's last hit, each
    as early as it can be, and they merge by hit (a tie: the lane's rank, then chart order). (ok, order): not ok when a
    prefix note opens after `hit` or cannot be hit by it, or a later note closes before it."""
    primary_low, primary_high, secondary_low, secondary_high = bands
    order = np.empty(activation, dtype=np.int64)
    for note in range(primary_low.shape[0]):
        open_primary, open_secondary = primary_low[note] <= primary_high[note], secondary_low[note] <= secondary_high[note]
        if note < activation and not (
            (open_primary and primary_low[note] <= hit) or (open_secondary and secondary_low[note] <= hit)
        ):
            return False, order
        if note > activation and not (
            (open_primary and primary_high[note] >= hit) or (open_secondary and secondary_high[note] >= hit)
        ):
            return False, order
    clock = first_clock
    for note in range(head_end):
        clock = _earliest_hit(primary_low, primary_high, secondary_low, secondary_high, note, clock)
        if clock > hit:
            return False, order
        order[note] = note
    body = activation - head_end
    lane_clock = np.full(lane_ranks.max() + 1, clock)
    hits = np.empty(body, dtype=np.float64)
    for position in range(body):
        note = head_end + position
        rank = lane_ranks[note]
        lane_clock[rank] = _earliest_hit(primary_low, primary_high, secondary_low, secondary_high, note, lane_clock[rank])
        if lane_clock[rank] > hit:
            return False, order
        hits[position] = lane_clock[rank]
    by_lane = np.argsort(lane_ranks[head_end:activation], kind="mergesort")
    order[head_end:] = head_end + by_lane[np.argsort(hits[by_lane], kind="mergesort")]
    return True, order


def chart_prefix_witness(
    *,
    labels: LabelHitIntervals,
    lanes: np.ndarray,
    activation_index: int,
    activation_hit_timestamp: float,
    fever_fill_denom: float,
    preactivation_fill: int,
    section_start: int,
    predecessor_hit_timestamp: float | None,
) -> ChartPrefixWitness | None:
    """The witness of an activation hit that follows the notes before it in chart order; None: there is none.

    The hit is legal when the activation is the first note whose fill reaches the denominator (preactivation_fill: the
    half-units before it, a Perfect 2, a Great 1) with every note hit inside its label's windows and full combo in chart
    order on every lane. Each lane plays the notes before the activation, so they all open by the hit, the later ones close
    after it, and the walk of _prefix_order reaches the hit.
    """
    start, a = section_start, activation_index
    if not 0.5 * preactivation_fill < fever_fill_denom <= 0.5 * (preactivation_fill + (1 if labels.is_great[a] else 2)):
        return None
    hit = float(np.float32(activation_hit_timestamp))
    first_clock = -np.inf if predecessor_hit_timestamp is None else predecessor_hit_timestamp
    if first_clock > hit:
        return None
    # Notes that open after the hit, and every note after them, cannot close before it. The head stays whole.
    opens_after = np.minimum.accumulate(np.minimum(labels.primary_low, labels.secondary_low)[::-1])[::-1]
    end = max(a + 1, min(labels.is_great.shape[0], _HEAD_NOTES), int(np.searchsorted(opens_after, hit, side="right")))
    bands = tuple(band[start:end].astype(np.float64) for band in labels[1:])
    i = a - start
    if not (bands[0][i] <= hit <= bands[1][i] or bands[2][i] <= hit <= bands[3][i]):
        return None
    section_lanes, first_notes, lane_of_note = np.unique(lanes[start:], return_index=True, return_inverse=True)
    lanes_in_order = np.argsort(first_notes)
    rank_of_lane = np.empty(lanes_in_order.shape[0], dtype=np.int64)
    rank_of_lane[lanes_in_order] = np.arange(lanes_in_order.shape[0])
    ok, order = _prefix_order(
        bands, rank_of_lane[lane_of_note[: end - start]], i, max(0, min(a, _HEAD_NOTES) - start), hit, first_clock
    )
    if not ok:
        return None
    played = np.bincount(lane_of_note[:i], minlength=section_lanes.shape[0])[lanes_in_order].tolist()
    return ChartPrefixWitness(
        tuple((order + start).tolist()), tuple(zip(section_lanes[lanes_in_order].tolist(), played, strict=True))
    )
