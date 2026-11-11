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
# The sets a body state's fevers keep apart: a window that may or may not fit before the song's end parts them by its notes.
_BODY_SETS = 8


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
    great_early, great_late = great_times(chart, perfect_time)
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
def _window_ends(ends, times, greats, a, duration, wide):
    """The ends of a fever window from position a into ends[a]: every note Perfect (first, last), and with `wide` where Greats
    move it (great first, great last, lowest, highest). Worked out once per position: the cells of a Fever Time share them,
    so a walk of the 161 cells pays each search once (~30% of a walk with Greats). -1 marks one not worked out yet."""
    n = times[0].shape[0]
    if ends[a, 0] < 0:
        ends[a, 0], ends[a, 1] = _ends_after(times, a, duration, n)
    if wide and ends[a, 2] < 0:
        ends[a, 2], ends[a, 3], ends[a, 4], ends[a, 5] = _great_ends_after(times, greats, a, duration, n)


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
def walk_scratch(notes, budget, rows):
    """walk_cell's scratch for a chart of this many notes at this Great budget: two state tables of `rows` rows, a row of sort
    keys, a table of moves for the head and one for the body, and the body's memo: per (activation, code) its sets, how many,
    the walk that wrote them, a stack and the walk counter."""
    codes = 2 * budget + 2
    moves = (notes + 2) * (budget + 2)
    return (
        np.empty((rows, 7), dtype=np.int64), np.empty((rows, 7), dtype=np.int64), np.empty(rows, dtype=np.int64),
        np.empty((moves, 3), dtype=np.int64), np.empty((moves, 3), dtype=np.int64),
        np.empty((notes, codes, _BODY_SETS, 3), dtype=np.int64), np.empty((notes, codes), dtype=np.int64),
        np.zeros((notes, codes), dtype=np.int64), np.empty((2 * notes * codes, 2), dtype=np.int64), np.zeros(1, dtype=np.int64),
    )


@jit(nopython=True, cache=True)
def _moves(times, greats, fill, duration, ends, state, out):
    """The moves of a state (activation, code: Greats spent x 2 + whether a fill Great reached the activation): per window end
    and fill delay its Greats allow, rows (end, next activation, its code) into out, the next activation n where no fever
    follows; returns how many. A Great is spent to delay a fill, to move the activation's time, or to move a note over the
    fever's end; an activation a fill Great has reached is that Great."""
    raw_fill, budget = fill
    a, code = state
    n = times[0].shape[0]
    notes = int(np.ceil(raw_fill))
    spent, activation_cost = code >> 1, 1 - (code & 1)
    wide = spent < budget or activation_cost == 0
    _window_ends(ends, times, greats, a, duration, wide)
    first, last = ends[a, 0], ends[a, 1]
    great_first, great_last, lowest, highest = first, last, first, last
    if wide:
        great_first, great_last, lowest, highest = ends[a, 2], ends[a, 3], ends[a, 4], ends[a, 5]
    count = 0
    for end in range(lowest, highest + 1):
        cost = min(max(0, first - end, end - last), activation_cost + max(0, great_first - end, end - great_last))
        delay = 0
        while spent + cost + _fill_delay_cost(raw_fill, delay) <= budget:
            activation = min(end + notes + delay, n)
            out[count, 0], out[count, 1], out[count, 2] = end, activation, 2 * (spent + cost + _fill_delay_cost(raw_fill, delay)) + (delay > 0)
            count += 1
            if activation == n:
                break
            delay += 1
    return count


@jit(nopython=True, cache=True)
def _add_set(sets, count, added):
    """sets[:count] with the body fever set `added` joined: into one it fits beside within _SET_BITS, else a set of its own; past
    _BODY_SETS of them into the nearest, as one set. Returns the count."""
    low, high, bits = added
    nearest, gap = 0, 1 << 62
    for k in range(count):
        if max(sets[k, 1], high) - min(sets[k, 0], low) <= _SET_BITS:
            sets[k, 0], sets[k, 1], sets[k, 2] = _merged((sets[k, 0], sets[k, 1], sets[k, 2]), added)
            return count
        if max(sets[k, 0] - high, low - sets[k, 1]) < gap:
            nearest, gap = k, max(sets[k, 0] - high, low - sets[k, 1])
    if count < sets.shape[0]:
        sets[count, 0], sets[count, 1], sets[count, 2] = low, high, bits
        return count + 1
    sets[nearest, 0], sets[nearest, 1], sets[nearest, 2] = _merged((sets[nearest, 0], sets[nearest, 1], sets[nearest, 2]), added)
    return count


@jit(nopython=True, cache=True)
def _body_fevers(times, greats, fill, duration, ends, body, start):
    """How many sets hold the body fevers a state at activation start[0] >= HEAD_NOTES and code start[1] gains to the song's
    end, worked out into body: walk_cell's windows past the head, where no mask changes, so each (activation, code) is worked
    out once per walk, children first (an activation only moves on), as up to _BODY_SETS exact sets. body: (moves, sets, how
    many, the walk that wrote them, a stack, the walk's number); -1 when the stack is full."""
    moves, sets, counts, seen, stack, walk = body
    n = times[0].shape[0]
    stack[0, 0], stack[0, 1] = start
    top = 1
    while top > 0:
        a, code = stack[top - 1, 0], stack[top - 1, 1]
        if seen[a, code] == walk:
            top -= 1
            continue
        waiting = False
        held = 0
        for m in range(_moves(times, greats, fill, duration, ends, (a, code), moves)):
            end, activation, child = moves[m, 0], moves[m, 1], moves[m, 2]
            if activation == n:
                if not waiting:
                    held = _add_set(sets[a, code], held, (end - a, end - a, 1))
            elif seen[activation, child] != walk:
                if top == stack.shape[0]:
                    return -1
                stack[top, 0], stack[top, 1] = activation, child
                top += 1
                waiting = True
            elif not waiting:
                for k in range(counts[activation, child]):
                    known = sets[activation, child, k]
                    held = _add_set(sets[a, code], held, (known[0] + end - a, known[1] + end - a, known[2]))
        if not waiting:
            counts[a, code] = held
            seen[a, code] = walk
            top -= 1
    return counts[start[0], start[1]]


@jit(nopython=True, cache=True)
def _finished(out, written, mask, counts, sets, held):
    """A head state with mask (low, high) and body fever counts that reaches the body, where it gains the `held` sets of
    _body_fevers: its timelines into out's rows, each count with each set (_keep_timeline); -1 when a table is full or
    _body_fevers' stack was (held < 0). Counts that are every count between their lowest and highest stay so."""
    if held < 0:
        return -1
    for k in range(held):
        if counts[2] == _ALL_COUNTS:
            written = _keep_timeline(out, written, mask[0], mask[1], (counts[0] + sets[k, 0], counts[1] + sets[k, 1], _ALL_COUNTS))
        else:
            for shift in range(counts[1] - counts[0] + 1):
                if written >= 0 and (counts[2] >> shift) & 1:
                    added = counts[0] + shift
                    written = _keep_timeline(out, written, mask[0], mask[1], (sets[k, 0] + added, sets[k, 1] + added, sets[k, 2]))
        if written < 0:
            return -1
    return written


@jit(nopython=True, cache=True)
def walk_cell(times, greats, fill, duration, scratch, out, ends):
    """Into out the timelines of one cell of a play with at most fill[1] Greats, as rows (mask low, mask high, lowest,
    highest, bits): one fever window per round (_moves), states of a round merged by activation, mask and Greats spent. Past
    the head no mask changes: a state that reaches it takes what its activation and Greats spent reach in the body, worked out
    once (_body_fevers). times: earliest and latest per position with every note Perfect; greats: the same with every note
    Great; fill: the Perfects that fill the bar, and the Great budget; scratch: walk_scratch's; ends: _window_ends' table at
    this duration, shared by the cells of a Fever Time. Returns the rows written, -1 when a table is full. A superset of what
    such a play reaches: it holds every real one."""
    raw_fill, budget = fill
    current, following, order_keys, moves = scratch[0], scratch[1], scratch[2], scratch[3]
    body = scratch[4], scratch[5], scratch[6], scratch[7], scratch[8], scratch[9][0] + 1
    scratch[9][0] += 1
    n = times[0].shape[0]
    notes = int(np.ceil(raw_fill))
    if notes > n:
        out[0, 0], out[0, 1], out[0, 2], out[0, 3], out[0, 4] = 0, 0, 0, 0, 1
        return 1
    written = states = 0
    delay = 0
    while notes - 1 + delay < n and _fill_delay_cost(raw_fill, delay) <= budget:
        code = 2 * _fill_delay_cost(raw_fill, delay) + (delay > 0)
        if notes - 1 + delay >= HEAD_NOTES:
            held = _body_fevers(times, greats, fill, duration, ends, body, (notes - 1 + delay, code))
            written = _finished(out, written, (0, 0), (0, 0, 1), body[1][notes - 1 + delay, code], held)
            if written < 0:
                return -1
        else:
            row = current[states]
            row[0], row[1], row[2], row[3], row[4], row[5], row[6] = notes - 1 + delay, 0, 0, 0, 0, 1, code
            states += 1
        delay += 1
    while states > 0:
        # By activation and Greats spent (code 2 x spent + fill flag < 64): the states a merge compares lie together.
        keys = order_keys[:states]
        for k in range(states):
            keys[k] = (current[k, 0] << 6) | current[k, 6]
        rows = np.argsort(keys)
        pushed = 0
        at = 0
        while at < states:
            group = at
            while group < states and keys[rows[group]] == keys[rows[at]]:
                group += 1
            for i in range(at, group):
                state = current[rows[i]]
                if state[3] < 0:
                    continue
                a, low, high = state[0], state[1], state[2]
                counts = (state[3], state[4], state[5])
                for j in range(i + 1, group):
                    other = current[rows[j]]
                    if other[3] >= 0 and other[1] == low and other[2] == high:
                        counts = _merged(counts, (other[3], other[4], other[5]))
                        other[3] = -1
                for m in range(_moves(times, greats, fill, duration, ends, (a, state[6]), moves)):
                    end, activation, code = moves[m, 0], moves[m, 1], moves[m, 2]
                    next_low, next_high = low, high
                    for position in range(a, min(end, HEAD_NOTES)):
                        if position < _LOW_WORD_BITS:
                            next_low |= 1 << position
                        else:
                            next_high |= 1 << (position - _LOW_WORD_BITS)
                    gain = max(0, end - max(a, HEAD_NOTES))
                    gained = (counts[0] + gain, counts[1] + gain, counts[2])
                    if activation == n:
                        written = _keep_timeline(out, written, next_low, next_high, gained)
                    elif activation >= HEAD_NOTES:
                        held = _body_fevers(times, greats, fill, duration, ends, body, (activation, code))
                        written = _finished(out, written, (next_low, next_high), gained, body[1][activation, code], held)
                    elif pushed >= following.shape[0]:
                        return -1
                    else:
                        row = following[pushed]
                        row[0], row[1], row[2], row[3], row[4], row[5], row[6] = activation, next_low, next_high, gained[0], gained[1], gained[2], code
                        pushed += 1
                    if written < 0:
                        return -1
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
    whose head states overflow their table is left out (none on the dev charts at 8 Greats)."""
    out = np.empty((1 << 12, 5), dtype=np.int64)
    scratch = walk_scratch(times[0].shape[0], budget, _STATE_ROWS if budget == 0 else _GREAT_STATE_ROWS)
    expanded = np.empty((1 << 18, 4), dtype=np.int64)
    ends = np.empty((times[0].shape[0], 6), dtype=np.int64)
    used = 0
    for ft in range(durations.shape[0]):
        ends[:] = -1
        for ff in range(fills.shape[0]):
            cell = ft * fills.shape[0] + ff
            rows = walk_cell(times, greats, (fills[ff], budget), durations[ft], scratch, out, ends)
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


def _distinct(columns: tuple[np.ndarray, ...]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The first row of each distinct row of `columns`, each row's distinct id, and the rows by id, a stable sort."""
    order = np.lexsort(columns[::-1])
    new = np.zeros(order.shape[0], dtype=bool)
    new[:1] = True
    for column in columns:
        new[1:] |= column[order[1:]] != column[order[:-1]]
    ids = np.empty(order.shape[0], dtype=np.int32)
    ids[order] = np.cumsum(new) - 1
    return order[new], ids, order


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
    first, ids, order = _distinct((rows[:, 0], rows[:, 1], rows[:, 2]))
    patterns, pattern_ids, _order = _distinct((rows[first, 0], rows[first, 1]))
    words = pattern_words(rows[first[patterns], 0], rows[first[patterns], 1])
    # _walk_grid writes rows by cell and the sort is stable, so (surface, cell) pairs come sorted: only repeats to drop.
    pairs = ids[order].astype(np.int64) * CELLS + rows[order, 3]
    pairs = pairs[np.concatenate(([True], pairs[1:] != pairs[:-1]))]
    return FeverSurfaces(
        words=words,
        coeffs=surface_head_coeffs(words, head_len=min(chart.total_notes, HEAD_NOTES)),
        pattern=pattern_ids,
        body_fever=rows[first, 2].astype(np.int32),
        cell_start=np.searchsorted(pairs // CELLS, np.arange(first.shape[0] + 1)),
        cells=(pairs % CELLS).astype(np.int32),
    )
