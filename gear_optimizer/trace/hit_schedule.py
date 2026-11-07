"""A plan's hit times.

A plan has fixed each note's judgment and its fever. Its inputs merge the lanes' notes in chart order (input_order), and
what is left is a system of difference constraints over them, in input order:

  * each input stays at or after the one before it and inside its band, a frame margin below the band's top: the game
    judges a press up to a frame after it lands;
  * two inputs stay a frame margin apart where sharing a frame changes the play: two inputs of one lane merge, and two
    different judgments score in another order through the combo ramp or at an activation or a wasted note;
  * a window's last fever input stays a frame margin inside its activation + duration and its wasted note one outside.

A Great is late unless the inputs after it leave it no late hit and its early band is open. Every margin starts at
FRAME_MARGIN_MS, where the plan holds at every frame timing of any rate >= 60 fps. Where the constraints leave less, the
margins along that path share what there is, so one tight place costs only its own inputs. Each activation with an offset
then sits in the middle of its free range, and every other hit as near its chart time as the constraints allow. A plan
whose ordered inputs do not fit a frame apart at the fastest rate, as far as their judgments reach, has no hits.

n inputs and c constraints: one pass costs O(n + c), and passes run once per tight path and per activation.
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np
from numba import njit

from gear_optimizer.score import HEAD_NOTES
from gear_optimizer.solver.timing_envelope import FRAME_MARGIN_MS

# The fastest rate the site offers.
_FASTEST_FRAME_MS = 1000.0 / 360.0
# Notes further apart in chart time than this have hits more than a frame margin apart, whatever comes between them: a
# tail's earliest Great is 190 ms early and every hit is at most 200 ms late.
_PAIR_SPAN_MS = 390.0 + FRAME_MARGIN_MS
# A fever input lands strictly before its cutoff and a wasted note strictly after it, past the replay's rounding.
_STRICT_MS = 1e-6
_SLACK_MS = 1e-9


class Inputs(NamedTuple):
    """Per input, in input order. A Great that may go early has its early band too; every other input +inf, -inf there."""

    chart_ms: np.ndarray
    low_ms: np.ndarray  # its band's first and last hit
    high_ms: np.ndarray
    reach_ms: np.ndarray  # how far past its last planned hit its judgment still holds (a Perfect kept on time)
    early_low_ms: np.ndarray
    early_high_ms: np.ndarray
    lane: np.ndarray
    tail: np.ndarray
    great: np.ndarray
    fever: np.ndarray


class _Links(NamedTuple):
    """Constraints p[after] >= p[before] + fixed + a margin; `into`/`into_start` hold the ones that run forward by their
    `after`, `back` the ones that run back."""

    before: np.ndarray
    after: np.ndarray
    fixed: np.ndarray
    into: np.ndarray
    into_start: np.ndarray
    back: np.ndarray


@njit(cache=True, nogil=True)
def input_order(lane, rank, before, after):
    """The notes in input order, or no notes when the constraints contradict each other: each lane keeps its chart order,
    each `before` note goes ahead of its `after` note, and of the notes free to go the lowest `rank` goes first."""
    n, lanes = rank.shape[0], int(lane.max()) + 1 if rank.shape[0] else 1
    waits = np.zeros(n, np.int64)
    start = np.zeros(n + 1, np.int64)
    for index in range(before.shape[0]):
        start[before[index] + 1] += 1
        waits[after[index]] += 1
    start = np.cumsum(start)
    fill = start[:n].copy()
    released = np.empty(before.shape[0], np.int64)
    for index in range(before.shape[0]):
        released[fill[before[index]]] = after[index]
        fill[before[index]] += 1
    head, last = np.full(lanes, -1, np.int64), np.full(lanes, -1, np.int64)
    next_on_lane = np.full(n, -1, np.int64)
    for note in range(n):
        if last[lane[note]] < 0:
            head[lane[note]] = note
        else:
            next_on_lane[last[lane[note]]] = note
        last[lane[note]] = note
    ordered = np.empty(n, np.int64)
    for position in range(n):
        best = -1
        for line in range(lanes):
            note = head[line]
            if note >= 0 and waits[note] == 0 and (best < 0 or rank[note] < rank[best]):
                best = note
        if best < 0:
            return ordered[:0]
        ordered[position] = best
        head[lane[best]] = next_on_lane[best]
        for c in range(start[best], start[best + 1]):
            waits[released[c]] -= 1
    return ordered


@njit(cache=True, nogil=True)
def _scored_pairs(inputs, activation, wasted):
    """The inputs on two lanes whose order scores, as (m, 2) positions."""
    n = inputs.chart_ms.shape[0]
    pairs = np.empty((64, 2), np.int64)
    used = 0
    for x in range(n):
        for y in range(x + 1, n):
            if inputs.chart_ms[y] - inputs.chart_ms[x] > _PAIR_SPAN_MS:
                break
            if inputs.lane[x] == inputs.lane[y] or inputs.great[x] == inputs.great[y]:
                continue
            if min(inputs.low_ms[y], inputs.early_low_ms[y]) >= inputs.high_ms[x] + FRAME_MARGIN_MS:
                continue
            # A Great activation adds the least fill: past the ramp a follower read first fills the bar instead, and the
            # fevered set and the score stay the same.
            if activation[x] and inputs.great[x] and x >= HEAD_NOTES:
                continue
            if y < HEAD_NOTES or activation[x] or activation[y] or wasted[x] or wasted[y]:
                if used == pairs.shape[0]:
                    pairs = np.concatenate((pairs, pairs))
                pairs[used, 0], pairs[used, 1] = x, y
                used += 1
    return pairs[:used]


@njit(cache=True, nogil=True)
def _links_of(inputs, sections):
    """The constraints of `inputs` and the fever `sections`: per window its activation's position, the next one's, its
    duration."""
    n = inputs.chart_ms.shape[0]
    capacity = n + 2 * sections.shape[0]
    before, after = np.empty(capacity, np.int64), np.empty(capacity, np.int64)
    fixed = np.zeros(capacity, np.float64)
    used = 0
    activation, wasted = np.zeros(n, np.bool_), np.zeros(n, np.bool_)
    for row in range(sections.shape[0]):
        first, stop, duration = int(sections[row, 0]), int(sections[row, 1]), sections[row, 2]
        activation[first] = True
        last_in, out = -1, -1
        for k in range(first + 1, stop):
            if inputs.fever[k]:
                last_in = k
            elif out < 0:
                out = k
        if out >= 0:
            wasted[out] = True
            before[used], after[used], fixed[used] = first, out, duration + _STRICT_MS
            used += 1
        if last_in >= 0:
            before[used], after[used], fixed[used] = last_in, first, _STRICT_MS - duration
            used += 1
    last_on_lane = np.full(int(inputs.lane.max()) + 1 if n else 1, -1, np.int64)
    for k in range(n):
        lane = inputs.lane[k]
        # A hold's release may share its press's frame: the game reads the press first.
        if last_on_lane[lane] >= 0 and not inputs.tail[k]:
            before[used], after[used] = last_on_lane[lane], k
            used += 1
        last_on_lane[lane] = k
    pairs = _scored_pairs(inputs, activation, wasted)
    before = np.concatenate((before[:used], pairs[:, 0]))
    after = np.concatenate((after[:used], pairs[:, 1]))
    fixed = np.concatenate((fixed[:used], np.zeros(pairs.shape[0], np.float64)))
    forward = np.flatnonzero(before < after)
    into = forward[np.argsort(after[forward], kind="mergesort")]
    into_start = np.zeros(n + 1, np.int64)
    for link in into:
        into_start[after[link] + 1] += 1
    return _Links(before, after, fixed, into, np.cumsum(into_start), np.flatnonzero(before > after))


@njit(cache=True, nogil=True)
def _pick_bands(links, inputs, clearance_ms):
    """Each input's band's first and last hit: a Great goes early when the inputs after it, `clearance_ms` clear, leave it
    no late hit and the inputs before it, as early as they can be, leave it an early one."""
    n = inputs.chart_ms.shape[0]
    low_ms, high_ms = inputs.low_ms.copy(), inputs.high_ms.copy()
    earliest = np.minimum(low_ms, inputs.early_low_ms)
    for k in range(n):
        if k:
            earliest[k] = max(earliest[k], earliest[k - 1])
        for c in range(links.into_start[k], links.into_start[k + 1]):
            link = links.into[c]
            earliest[k] = max(earliest[k], earliest[links.before[link]] + links.fixed[link])
    latest = np.full(n, np.inf, np.float64)
    for k in range(n - 1, -1, -1):
        if latest[k] < low_ms[k] and earliest[k] <= inputs.early_high_ms[k]:
            low_ms[k], high_ms[k] = inputs.early_low_ms[k], inputs.early_high_ms[k]
        hit = min(latest[k], max(high_ms[k] - clearance_ms, low_ms[k]))
        if k:
            latest[k - 1] = min(latest[k - 1], hit)
        for c in range(links.into_start[k], links.into_start[k + 1]):
            link = links.into[c]
            latest[links.before[link]] = min(latest[links.before[link]], hit - links.fixed[link] - clearance_ms)
    return low_ms, high_ms


@njit(cache=True, nogil=True)
def _earliest(links, margin, low_ms, ceiling_ms, earliest, source):
    """Fills each input's earliest hit and what set it (-1 its band, -2 the input before it, else a link); returns the
    first input past its ceiling, or -1."""
    n = low_ms.shape[0]
    earliest[:] = low_ms
    source[:] = -1
    while True:
        for k in range(n):
            if k and earliest[k - 1] > earliest[k] + _SLACK_MS:
                earliest[k], source[k] = earliest[k - 1], -2
            for c in range(links.into_start[k], links.into_start[k + 1]):
                link = links.into[c]
                hit = earliest[links.before[link]] + links.fixed[link] + margin[link]
                if hit > earliest[k] + _SLACK_MS:
                    earliest[k], source[k] = hit, link
            if earliest[k] > ceiling_ms[k] + _SLACK_MS:
                return k
        settled = True
        for link in links.back:
            hit = earliest[links.before[link]] + links.fixed[link] + margin[link]
            if hit > earliest[links.after[link]] + _SLACK_MS:
                earliest[links.after[link]], source[links.after[link]] = hit, link
                settled = False
        if settled:
            return -1


@njit(cache=True, nogil=True)
def _latest(links, margin, ceiling_ms, latest):
    """Fills each input's latest hit."""
    n = ceiling_ms.shape[0]
    latest[:] = ceiling_ms
    while True:
        for k in range(n - 1, -1, -1):
            for c in range(links.into_start[k], links.into_start[k + 1]):
                link = links.into[c]
                latest[links.before[link]] = min(latest[links.before[link]], latest[k] - links.fixed[link] - margin[link])
            if k:
                latest[k - 1] = min(latest[k - 1], latest[k])
        settled = True
        for link in links.back:
            hit = latest[links.after[link]] - links.fixed[link] - margin[link]
            if hit < latest[links.before[link]] - _SLACK_MS:
                latest[links.before[link]] = hit
                settled = False
        if settled:
            return


@njit(cache=True, nogil=True)
def _settle_margins(links, low_ms, high_ms, margin, ceiling_ms):
    """Lowers the margins along each path that overruns a band until none does; returns -1, or an input no margin frees."""
    n = low_ms.shape[0]
    earliest, source = np.empty(n, np.float64), np.empty(n, np.int64)
    path = np.empty(n, np.int64)
    # Each round settles one path for good, and a plan has few of them.
    for _ in range(n + links.before.shape[0] + 1):
        k = _earliest(links, margin, low_ms, ceiling_ms, earliest, source)
        if k < 0:
            return -1
        left, size, gaps, v = high_ms[k], 0, 0, k
        while source[v] != -1:
            if source[v] == -2:
                v -= 1
                continue
            if size == n:
                raise ValueError("hit_schedule: a fever window closes on itself")
            link = source[v]
            path[size] = link
            left -= links.fixed[link]
            gaps += links.fixed[link] == 0.0
            v = links.before[link]
            size += 1
        # Past the frames its gaps need at the fastest rate, a path's margins share what it leaves alike; the gaps and the
        # band top split those frames, as a pair needs its gap and top to add up to a frame.
        room = max(left - low_ms[v], 0.0)
        reserved = min(room, gaps * _FASTEST_FRAME_MS)
        each = (room - reserved) / (size + 1)
        frames = each + reserved / (gaps + 1)
        freed = high_ms[k] - frames > ceiling_ms[k]
        ceiling_ms[k] = max(ceiling_ms[k], high_ms[k] - frames)
        for index in range(size):
            share = frames if links.fixed[path[index]] == 0.0 else each
            if margin[path[index]] > share:
                margin[path[index]] = share
                freed = True
        if not freed:
            return k
    raise ValueError("hit_schedule: the margins did not settle")


@njit(cache=True, nogil=True)
def _hits(links, inputs, low_ms, margin, ceiling_ms, sections, middle):
    """The hits under settled margins: the activations first, as their pick moves everything fever ties to them."""
    n = low_ms.shape[0]
    low_ms, ceiling_ms = low_ms.copy(), ceiling_ms.copy()
    earliest, latest = np.empty(n, np.float64), np.empty(n, np.float64)
    source = np.empty(n, np.int64)
    for row in range(sections.shape[0]):
        k = int(sections[row, 0])
        _earliest(links, margin, low_ms, ceiling_ms, earliest, source)
        _latest(links, margin, ceiling_ms, latest)
        at = 0.5 * (earliest[k] + latest[k]) if middle[row] else min(max(inputs.chart_ms[k], earliest[k]), latest[k])
        low_ms[k], ceiling_ms[k] = at, at
    _latest(links, margin, ceiling_ms, latest)
    hits = np.empty(n, np.float64)
    for k in range(n):
        floor = low_ms[k]
        if k:
            floor = max(floor, hits[k - 1])
        for c in range(links.into_start[k], links.into_start[k + 1]):
            link = links.into[c]
            floor = max(floor, hits[links.before[link]] + links.fixed[link] + margin[link])
        hits[k] = min(max(inputs.chart_ms[k], floor), latest[k])
    return hits


@njit(cache=True, nogil=True)
def schedule_hits(inputs, sections, middle):
    """Returns (the first input with no frame of its own at the fastest rate or -1, the hits). `middle`: per fever section,
    whether its activation sits in the middle of its free range."""
    n = inputs.chart_ms.shape[0]
    links = _links_of(inputs, sections)
    # The game counts a window in whole ms between floored frame times, so a wasted note needs a whole ms past it.
    whole_ms = np.ceil(links.fixed) - links.fixed + _STRICT_MS
    margin = np.where(links.fixed == 0.0, _FASTEST_FRAME_MS, np.where(links.fixed > 0.0, whole_ms, 0.0))
    earliest, source = np.empty(n, np.float64), np.empty(n, np.int64)
    # Greats go early for a frame margin; a run of them that cannot all make it settles for a frame of the fastest rate.
    low_ms, high_ms = _pick_bands(links, inputs, FRAME_MARGIN_MS)
    stopped = _earliest(links, margin, low_ms, high_ms + inputs.reach_ms, earliest, source)
    if stopped >= 0:
        low_ms, high_ms = _pick_bands(links, inputs, _FASTEST_FRAME_MS)
        stopped = _earliest(links, margin, low_ms, high_ms + inputs.reach_ms, earliest, source)
        if stopped >= 0:
            return stopped, earliest
    margin[:] = FRAME_MARGIN_MS
    ceiling_ms = np.maximum(high_ms - FRAME_MARGIN_MS, low_ms)
    stopped = _settle_margins(links, low_ms, high_ms, margin, ceiling_ms)
    if stopped >= 0:
        return stopped, earliest
    hits = _hits(links, inputs, low_ms, margin, ceiling_ms, sections, middle)
    for link in range(links.before.shape[0]):
        if links.fixed[link] == 0.0 and hits[links.after[link]] <= hits[links.before[link]]:
            return links.after[link], hits
    return -1, hits


def warm() -> None:
    """Load the kernels (a first run compiles them, about 7 s), so that no request of a server pays for it."""
    one_ms, lane, flag = np.zeros(1, np.float64), np.zeros(1, np.int64), np.zeros(1, np.bool_)
    no_links = np.empty(0, np.int64)
    input_order(lane, lane, no_links, no_links)
    schedule_hits(
        Inputs(one_ms, one_ms, one_ms, one_ms, np.full(1, np.inf), np.full(1, -np.inf), lane, flag, flag, flag),
        np.empty((0, 3), np.float64),
        np.empty(0, np.bool_),
    )
