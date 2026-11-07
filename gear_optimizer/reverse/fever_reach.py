"""Every fever timeline a play can reach, walked over event positions the way the game's server replays a play.

The saved score is the server's replay of the client's event stream (ServerPlayerNoteSequenceInfo push_note_sequence),
in time order, so a head note's combo is its position in that order. An event fills the bar, or charges its elapsed time
while fever runs; the event that fills the bar is the first fever event, and the first event at or past the fever time
is scored outside fever and adds no fill. Only the positions of those two events move a timeline, and a play's timing
moves them: the k-th event's time lies between the k-th smallest earliest time and the k-th smallest latest time of the
notes. From an activation at position a, fever ends at any position between the first that can lie a fever time after
the earliest activation and the last whose predecessor can lie under a fever time after the latest one.

Cost: O(E log n) per (Fever Time, Fever Fill) cell for E reachable ends, ~12 on average: ~30 ms for the 25,921 cells.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from gear_optimizer.chart import Chart
from gear_optimizer.core.jit_setup import jit
from gear_optimizer.core.time_quantize import quantize_to_int_ms
from gear_optimizer.frontier.fg_cache_patterns import surface_head_coeffs
from gear_optimizer.gamedata import StatCurves
from gear_optimizer.rules import MAX_STAT
from gear_optimizer.score import HEAD_NOTES
from gear_optimizer.solver.timing_envelope import HELD_TAIL_TYPE, HELD_TAIL_WINDOW_SCALE, fever_axes, judgment_bounds

CELLS = (MAX_STAT + 1) ** 2
# Head fever positions: a state's first mask word holds positions 0..61, its second 62..99.
_LOW_WORD_BITS = 62
# A body fever set is (lowest, highest, bits over the lowest); wider than this it keeps every count between them.
_SET_BITS = 62
_ALL_COUNTS = -1
_STATE_ROWS = 1 << 15
_GREAT_STATE_ROWS = 1 << 11


def event_times(chart: Chart, perfect_time: int, greats: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Per event position, the earliest and latest server event time (whole ms) of a play at this Perfect Time that
    judges every note Perfect but `greats` of them. An event's time is the floor of its frame's clock, so a hit just past
    the exclusive early edge floors one millisecond under the band's first whole millisecond. A Great moves its own
    note out of the Perfect order, so a position reaches at most `greats` positions further along that order, and at
    most the same position of the all-Great order."""
    hit = quantize_to_int_ms(chart.timestamps).astype(np.int64)
    tap, tail = judgment_bounds(1, perfect_time), judgment_bounds(HELD_TAIL_WINDOW_SCALE, perfect_time)
    is_tail = chart.note_types == HELD_TAIL_TYPE
    earliest = np.sort(hit + np.where(is_tail, tail.perfect.earliest, tap.perfect.earliest) - 1)
    latest = np.sort(hit + np.where(is_tail, tail.perfect.latest, tap.perfect.latest))
    if greats == 0:
        return earliest, latest
    positions = np.arange(hit.shape[0])
    great_early = np.sort(hit + np.where(is_tail, tail.early_great.earliest, tap.early_great.earliest) - 1)
    great_late = np.sort(hit + np.where(is_tail, tail.late_great.latest, tap.late_great.latest))
    return (
        np.maximum(great_early, earliest[np.maximum(positions - greats, 0)]),
        np.minimum(great_late, latest[np.minimum(positions + greats, hit.shape[0] - 1)]),
    )


def great_times(chart: Chart, perfect_time: int) -> tuple[np.ndarray, np.ndarray]:
    """Per event position, the earliest and latest server event time of a play at this Perfect Time, every note Great."""
    hit = quantize_to_int_ms(chart.timestamps).astype(np.int64)
    tap, tail = judgment_bounds(1, perfect_time), judgment_bounds(HELD_TAIL_WINDOW_SCALE, perfect_time)
    is_tail = chart.note_types == HELD_TAIL_TYPE
    return (
        np.sort(hit + np.where(is_tail, tail.early_great.earliest, tap.early_great.earliest) - 1),
        np.sort(hit + np.where(is_tail, tail.late_great.latest, tap.late_great.latest)),
    )


@jit(nopython=True, cache=True)
def _merged(left, right):
    """The union of two body fever sets (lowest, highest, bits)."""
    lowest, highest = min(left[0], right[0]), max(left[1], right[1])
    if highest - lowest > _SET_BITS or left[2] == _ALL_COUNTS or right[2] == _ALL_COUNTS:
        return lowest, highest, _ALL_COUNTS
    return lowest, highest, (left[2] << (left[0] - lowest)) | (right[2] << (right[0] - lowest))


@jit(nopython=True, cache=True)
def _fill_delay_cost(raw_fill, delay):
    """The fewest Greats that move a bar's crossing `delay` notes on: a Great fills half a Perfect (fill_crossing)."""
    return 0 if delay == 0 else int(np.floor(2.0 * (delay - 1 + np.ceil(raw_fill) - raw_fill))) + 1


@jit(nopython=True, cache=True)
def _ends_after(times, a, duration, n):
    """The events a fever window from position a can end on, every note Perfect: the lowest and the highest."""
    earliest, latest = times
    first = min(max(int(np.searchsorted(latest, earliest[a] + duration, side="left")), a + 1), n)
    return first, max(min(int(np.searchsorted(earliest, latest[a] + duration, side="left")), n), first)


@jit(nopython=True, cache=True)
def _great_ends_after(times, greats, a, duration, n):
    """The same with the activation a Great, and the most one window can move with every note a Great. A note moved past
    its Perfect band costs one Great, whichever way."""
    earliest, latest = times
    great_early, great_late = greats
    first = min(max(int(np.searchsorted(latest, great_early[a] + duration, side="left")), a + 1), n)
    last = max(min(int(np.searchsorted(earliest, great_late[a] + duration, side="left")), n), first)
    lowest = min(max(int(np.searchsorted(great_late, great_early[a] + duration, side="left")), a + 1), n)
    return first, last, lowest, max(min(int(np.searchsorted(great_early, great_late[a] + duration, side="left")), n), last)


@jit(nopython=True, cache=True)
def _keep_timeline(out, written, low, high, counts):
    """A finished timeline into out's rows, merged with a row of its head mask while their counts fit one set; returns the
    rows, -1 when they stop fitting."""
    for row in range(written):
        if out[row, 0] == low and out[row, 1] == high and max(out[row, 3], counts[1]) - min(out[row, 2], counts[0]) <= _SET_BITS:
            out[row, 2], out[row, 3], out[row, 4] = _merged((out[row, 2], out[row, 3], out[row, 4]), counts)
            return written
    if written == out.shape[0]:
        return -1
    row = out[written]
    row[0], row[1], row[2], row[3], row[4] = low, high, counts[0], counts[1], counts[2]
    return written + 1


@jit(nopython=True, cache=True)
def walk_cell(times, greats, fill, duration, scratch, out):
    """Into out the timelines of one cell of a play with at most fill[1] Greats, as rows (mask low, mask high, lowest,
    highest, bits): one fever window per round, states of a round merged by activation, mask and Greats spent. A Great
    is spent to delay a fill, to move the activation's time, or to move a note over the fever's end; an activation a fill
    Great has reached is that Great. times: earliest and latest per position with every note Perfect; greats: the same
    with every note Great; fill: the Perfects that fill the bar, and the Great budget; scratch: two state tables. Returns
    the rows written, -1 when a table is full. A superset of what such a play reaches: it holds every real one."""
    raw_fill, budget = fill
    current, following = scratch
    n = times[0].shape[0]
    notes = int(np.ceil(raw_fill))
    if notes > n:
        out[0, 0], out[0, 1], out[0, 2], out[0, 3], out[0, 4] = 0, 0, 0, 0, 1
        return 1
    written = states = 0
    delay = 0
    while notes - 1 + delay < n and _fill_delay_cost(raw_fill, delay) <= budget:
        row = current[states]
        row[0], row[1], row[2], row[3], row[4], row[5] = notes - 1 + delay, 0, 0, 0, 0, 1
        row[6] = 2 * _fill_delay_cost(raw_fill, delay) + (delay > 0)
        states += 1
        delay += 1
    while states > 0:
        rows = np.argsort(current[:states, 0])
        pushed = 0
        at = 0
        while at < states:
            group = at
            while group < states and current[rows[group], 0] == current[rows[at], 0]:
                group += 1
            for i in range(at, group):
                state = current[rows[i]]
                if state[3] < 0:
                    continue
                a, low, high = state[0], state[1], state[2]
                spent, activation_cost = state[6] >> 1, 1 - (state[6] & 1)
                counts = (state[3], state[4], state[5])
                for j in range(i + 1, group):
                    other = current[rows[j]]
                    if other[3] >= 0 and other[1] == low and other[2] == high and other[6] == state[6]:
                        counts = _merged(counts, (other[3], other[4], other[5]))
                        other[3] = -1
                first, last = _ends_after(times, a, duration, n)
                great_first, great_last, lowest, highest = first, last, first, last
                if spent < budget or activation_cost == 0:
                    great_first, great_last, lowest, highest = _great_ends_after(times, greats, a, duration, n)
                for end in range(lowest, highest + 1):
                    cost = min(
                        max(0, first - end, end - last),
                        activation_cost + max(0, great_first - end, end - great_last),
                    )
                    if spent + cost > budget:
                        continue
                    next_low, next_high = low, high
                    for position in range(a, min(end, HEAD_NOTES)):
                        if position < _LOW_WORD_BITS:
                            next_low |= 1 << position
                        else:
                            next_high |= 1 << (position - _LOW_WORD_BITS)
                    gain = max(0, end - max(a, HEAD_NOTES))
                    delay = 0
                    while spent + cost + _fill_delay_cost(raw_fill, delay) <= budget:
                        if end + notes + delay >= n:
                            written = _keep_timeline(out, written, next_low, next_high, (counts[0] + gain, counts[1] + gain, counts[2]))
                            if written < 0:
                                return -1
                            break
                        if pushed >= following.shape[0]:
                            return -1
                        row = following[pushed]
                        row[0], row[1], row[2] = end + notes + delay, next_low, next_high
                        row[3], row[4], row[5] = counts[0] + gain, counts[1] + gain, counts[2]
                        row[6] = 2 * (spent + cost + _fill_delay_cost(raw_fill, delay)) + (delay > 0)
                        pushed += 1
                        delay += 1
            at = group
        current, following = following, current
        states = pushed
    return written


@jit(nopython=True, cache=True)
def fever_span(times, fills, duration):
    """The fewest and the most events one cell's play keeps in fever when the notes that fill its bar lie between fills:
    walk_cell's windows without their masks."""
    earliest, latest = times
    fill_lo, fill_hi = fills
    n = earliest.shape[0]
    most = np.full(n, -1, dtype=np.int64)
    least = np.full(n, n + 1, dtype=np.int64)
    fewest, highest = n, -1
    if fill_hi > n:
        fewest, highest = 0, 0
    for a in range(fill_lo - 1, min(fill_hi, n)):
        most[a], least[a] = 0, 0
    for a in range(n):
        if most[a] < 0:
            continue
        first = min(max(int(np.searchsorted(latest, earliest[a] + duration, side="left")), a + 1), n)
        last = max(min(int(np.searchsorted(earliest, latest[a] + duration, side="left")), n), first)
        for end in range(first, last + 1):
            if end + fill_hi >= n:
                fewest, highest = min(fewest, least[a] + end - a), max(highest, most[a] + end - a)
            for activation in range(end + fill_lo, min(end + fill_hi + 1, n)):
                most[activation] = max(most[activation], most[a] + end - a)
                least[activation] = min(least[activation], least[a] + end - a)
    return fewest, highest


@jit(nopython=True, cache=True)
def _walk_grid(times, greats, fills, durations, budget):
    """walk_cell over every (Fever Time, Fever Fill) cell: rows (mask low, mask high, body fever, cell). With Greats a cell
    whose head holds so many short windows that its tables overflow is left out: such a cell is far from any song's top."""
    out = np.empty((1 << 12, 5), dtype=np.int64)
    states = _STATE_ROWS if budget == 0 else _GREAT_STATE_ROWS
    scratch = (np.empty((states, 7), dtype=np.int64), np.empty((states, 7), dtype=np.int64))
    expanded = np.empty((1 << 18, 4), dtype=np.int64)
    used = 0
    for ft in range(durations.shape[0]):
        for ff in range(fills.shape[0]):
            cell = ft * fills.shape[0] + ff
            rows = walk_cell(times, greats, (fills[ff], budget), durations[ft], scratch, out)
            if rows < 0:
                if budget == 0:
                    raise ValueError("fever walk: a cell outgrew its tables")
                continue
            for row in range(rows):
                lowest, highest, bits = out[row, 2], out[row, 3], out[row, 4]
                for count in range(lowest, highest + 1):
                    if bits == _ALL_COUNTS or (bits >> (count - lowest)) & 1:
                        if used >= expanded.shape[0]:
                            grown = np.empty((expanded.shape[0] * 2, 4), dtype=np.int64)
                            grown[:used] = expanded[:used]
                            expanded = grown
                        written = expanded[used]
                        written[0], written[1], written[2], written[3] = out[row, 0], out[row, 1], count, cell
                        used += 1
    return expanded[:used]


@dataclass(frozen=True, slots=True, eq=False)
class FeverSurfaces:
    """The distinct timelines of a chart's cells. Surface u is head pattern pattern[u] (words: its 8 pattern words as the
    gem search reads them, coeffs: surface_head_coeffs) with body_fever[u] fever notes after the head; its cells (Fever
    Time x 161 + Fever Fill) are cells[cell_start[u] : cell_start[u + 1]]."""

    words: np.ndarray
    coeffs: np.ndarray
    pattern: np.ndarray
    body_fever: np.ndarray
    cell_start: np.ndarray
    cells: np.ndarray


def _distinct(columns: tuple[np.ndarray, ...]) -> tuple[np.ndarray, np.ndarray]:
    """The first row of each distinct row of `columns`, and each row's distinct id."""
    order = np.lexsort(columns[::-1])
    new = np.zeros(order.shape[0], dtype=bool)
    new[:1] = True
    for column in columns:
        new[1:] |= column[order[1:]] != column[order[:-1]]
    ids = np.empty(order.shape[0], dtype=np.int32)
    ids[order] = np.cumsum(new) - 1
    return order[new], ids


def pattern_words(low: np.ndarray, high: np.ndarray) -> np.ndarray:
    """(n, 8) uint32 pattern words of masks over positions 0..61 (low) and 62..99 (high): no Great notes."""
    low, high = low.astype(np.uint64), high.astype(np.uint64)
    mask = np.uint64(0xFFFFFFFF)
    words = np.zeros((low.shape[0], 8), dtype=np.uint32)
    words[:, 0] = low & mask
    words[:, 1] = ((low >> np.uint64(32)) | (high << np.uint64(30))) & mask
    words[:, 2] = (high >> np.uint64(2)) & mask
    words[:, 3] = high >> np.uint64(34)
    return words


def fever_surfaces(chart: Chart, curves: StatCurves, perfect_time: int, greats: int = 0) -> FeverSurfaces:
    """The timelines of every cell of `chart` of a play at this Perfect Time with at most `greats` Greats."""
    durations, thresholds = fever_axes(chart.total_notes, chart.long_notes, chart.last_note_time, curves)
    times = event_times(chart, perfect_time), great_times(chart, perfect_time)
    rows = _walk_grid(*times, thresholds.astype(np.float64), durations * 1000.0, greats)
    first, ids = _distinct((rows[:, 0], rows[:, 1], rows[:, 2]))
    patterns, pattern_ids = _distinct((rows[first, 0], rows[first, 1]))
    words = pattern_words(rows[first[patterns], 0], rows[first[patterns], 1])
    pairs = np.unique(ids.astype(np.int64) * CELLS + rows[:, 3])
    return FeverSurfaces(
        words=words,
        coeffs=surface_head_coeffs(words, head_len=min(chart.total_notes, HEAD_NOTES)),
        pattern=pattern_ids,
        body_fever=rows[first, 2].astype(np.int32),
        cell_start=np.searchsorted(pairs // CELLS, np.arange(first.shape[0] + 1)),
        cells=(pairs % CELLS).astype(np.int32),
    )
