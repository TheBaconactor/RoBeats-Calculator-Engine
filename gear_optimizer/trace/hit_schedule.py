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

from gear_optimizer.core.jit_setup import jit
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


@jit(nopython=True, cache=True, nogil=True)
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


@jit(nopython=True, cache=True, nogil=True)
def early_greats_kernel(hit_ms, great, lanes, is_tail, bands_2, activations, fever_ends):
    """Non-Precise early Greats: Greats ahead of a chord's first Perfect or tighter late than early on their lane,
    clamped by activation/fever-end anchor floors."""
    n = hit_ms.shape[0]
    early = np.zeros(n, np.bool_)
    if n == 0:
        return early
    lane_min = lanes[0]
    lane_max = lanes[0]
    for i in range(1, n):
        v = lanes[i]
        if v < lane_min:
            lane_min = v
        if v > lane_max:
            lane_max = v
    prev_on_lane = np.full(lane_max - lane_min + 1, -1, np.int64)
    next_late_ms = np.full(n, np.inf, np.float64)
    from_last = np.full(n, np.inf, np.float64)
    for i in range(n):
        t = 1 if is_tail[i] else 0
        late_i = hit_ms[i] + (bands_2[t, 2, 0] if great[i] else 0.0)
        li = lanes[i] - lane_min
        prev = prev_on_lane[li]
        if prev >= 0:
            next_late_ms[prev] = late_i
            from_last[i] = hit_ms[i] - hit_ms[prev]
        prev_on_lane[li] = i
    # Chord runs share equal hit_ms: mark Greats before a chord's first Perfect.
    c0 = 0
    while c0 < n:
        c1 = c0 + 1
        t0 = hit_ms[c0]
        while c1 < n and hit_ms[c1] == t0:
            c1 += 1
        fp = n
        for i in range(c0, c1):
            if not great[i]:
                fp = i
                break
        if fp < n:
            for i in range(c0, fp):
                if great[i]:
                    early[i] = True
        c0 = c1
    anchor_floor = np.full(n, -np.inf, np.float64)
    is_act = np.zeros(n, np.bool_)
    for s in range(activations.shape[0]):
        a = activations[s]
        is_act[a] = True
        fe = fever_ends[s]
        if fe > n - 1:
            fe = n - 1
        if a + 1 < n and hit_ms[a] > anchor_floor[a + 1]:
            anchor_floor[a + 1] = hit_ms[a]
        if fe + 1 < n and hit_ms[fe] > anchor_floor[fe + 1]:
            anchor_floor[fe + 1] = hit_ms[fe]
    af = -np.inf
    for i in range(n):
        if anchor_floor[i] > af:
            af = anchor_floor[i]
        if not great[i] or is_act[i]:
            early[i] = False
            continue
        t = 1 if is_tail[i] else 0
        if not early[i]:
            late_i = hit_ms[i] + bands_2[t, 2, 0]
            room_late = next_late_ms[i] - late_i
            room_early = from_last[i] + bands_2[t, 1, 1]
            if room_late < FRAME_MARGIN_MS and room_early > room_late:
                early[i] = True
        if early[i] and hit_ms[i] + bands_2[t, 1, 1] - FRAME_MARGIN_MS < af:
            early[i] = False
    return early


@jit(nopython=True, cache=True, nogil=True)
def ranked_times_kernel(hit_ms, great, is_tail, early, bands_2):
    """Per-note tie-break times for input_order: chart time, late Great past the combo ramp, early Great shifted early."""
    n = hit_ms.shape[0]
    ramp_end = HEAD_NOTES if HEAD_NOTES < n else n
    while 0 < ramp_end < n and hit_ms[ramp_end] == hit_ms[ramp_end - 1]:
        ramp_end += 1
    times = np.empty(n, np.float64)
    for i in range(n):
        t = 1 if is_tail[i] else 0
        if early[i]:
            times[i] = hit_ms[i] + bands_2[t, 1, 1] - FRAME_MARGIN_MS
        elif i >= ramp_end and great[i]:
            times[i] = hit_ms[i] + bands_2[t, 2, 0]
        else:
            times[i] = hit_ms[i]
    return times


@jit(nopython=True, cache=True, nogil=True)
def build_schedule_inputs(plan_cols, order, bands_2, act_positions, precise):
    """Build `Inputs` in input order in one compiled pass over `order` without per-note (N, 3, 2) band arrays."""
    hit_ms, is_tail, lanes, great, fever, early = plan_cols
    n = order.shape[0]
    out_chart = np.empty(n, np.float64)
    out_low = np.empty(n, np.float64)
    out_high = np.empty(n, np.float64)
    out_reach = np.empty(n, np.float64)
    out_elo = np.empty(n, np.float64)
    out_ehi = np.empty(n, np.float64)
    out_lane = np.empty(n, np.int64)
    out_tail = np.empty(n, np.bool_)
    out_great = np.empty(n, np.bool_)
    out_fever = np.empty(n, np.bool_)
    is_act = np.zeros(n, np.bool_)
    for i in range(act_positions.shape[0]):
        is_act[act_positions[i]] = True
    for pos in range(n):
        idx = order[pos]
        h = hit_ms[idx]
        tail = is_tail[idx]
        t = 1 if tail else 0
        g = great[idx]
        fe = early[idx]
        out_chart[pos] = h
        out_lane[pos] = lanes[idx]
        out_tail[pos] = tail
        out_great[pos] = g
        out_fever[pos] = fever[idx]
        if fe:
            lo_off = bands_2[t, 1, 0]
            hi_off = bands_2[t, 1, 1]
        elif g:
            lo_off = bands_2[t, 2, 0]
            hi_off = bands_2[t, 2, 1]
        elif precise:
            lo_off = bands_2[t, 0, 0]
            hi_off = bands_2[t, 0, 1]
        else:
            lo_off = 0.0
            hi_off = 0.0
        out_low[pos] = h + lo_off
        out_high[pos] = h + hi_off
        out_reach[pos] = 0.0 if g else (bands_2[t, 0, 1] - hi_off)
        if g and not fe and not is_act[pos]:
            out_elo[pos] = h + bands_2[t, 1, 0]
            out_ehi[pos] = h + bands_2[t, 1, 1]
        else:
            out_elo[pos] = np.inf
            out_ehi[pos] = -np.inf
    return Inputs(
        out_chart, out_low, out_high, out_reach, out_elo, out_ehi, out_lane, out_tail, out_great, out_fever
    )


@jit(nopython=True, cache=True, nogil=True)
def _scored_pairs(inputs, activation, wasted):
    """The inputs on two lanes whose order scores, as (m, 2) positions."""
    n = inputs.chart_ms.shape[0]
    special = np.empty(n, np.int64)
    n_sp = 0
    for i in range(HEAD_NOTES, n):
        if activation[i] or wasted[i]:
            special[n_sp] = i
            n_sp += 1
    pairs = np.empty((64, 2), np.int64)
    used = 0
    sp_cursor = 0
    for x in range(n):
        if x < HEAD_NOTES or activation[x] or wasted[x]:
            if activation[x] and inputs.great[x] and x >= HEAD_NOTES:
                continue
            x_chart = inputs.chart_ms[x]
            x_lane = inputs.lane[x]
            x_great = inputs.great[x]
            x_hi = inputs.high_ms[x] + FRAME_MARGIN_MS
            x_act_or_wasted = activation[x] or wasted[x]
            for y in range(x + 1, n):
                if inputs.chart_ms[y] - x_chart > _PAIR_SPAN_MS:
                    break
                if x_lane == inputs.lane[y] or x_great == inputs.great[y]:
                    continue
                if min(inputs.low_ms[y], inputs.early_low_ms[y]) >= x_hi:
                    continue
                if y < HEAD_NOTES or x_act_or_wasted or activation[y] or wasted[y]:
                    if used == pairs.shape[0]:
                        pairs = np.concatenate((pairs, pairs))
                    pairs[used, 0], pairs[used, 1] = x, y
                    used += 1
        else:
            while sp_cursor < n_sp and special[sp_cursor] <= x:
                sp_cursor += 1
            if sp_cursor >= n_sp:
                break
            x_chart = inputs.chart_ms[x]
            if inputs.chart_ms[special[sp_cursor]] - x_chart > _PAIR_SPAN_MS + 390.0:
                continue
            x_lane = inputs.lane[x]
            x_great = inputs.great[x]
            x_hi = inputs.high_ms[x] + FRAME_MARGIN_MS
            for j in range(sp_cursor, n_sp):
                y = special[j]
                dy = inputs.chart_ms[y] - x_chart
                if dy > _PAIR_SPAN_MS:
                    if dy > _PAIR_SPAN_MS + 390.0:
                        break
                    continue
                if x_lane == inputs.lane[y] or x_great == inputs.great[y]:
                    continue
                if min(inputs.low_ms[y], inputs.early_low_ms[y]) >= x_hi:
                    continue
                if used == pairs.shape[0]:
                    pairs = np.concatenate((pairs, pairs))
                pairs[used, 0], pairs[used, 1] = x, y
                used += 1
    return pairs[:used]


@jit(nopython=True, cache=True, nogil=True)
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
    m_pairs = pairs.shape[0]
    total = used + m_pairs
    out_before = np.empty(total, np.int64)
    out_after = np.empty(total, np.int64)
    out_fixed = np.zeros(total, np.float64)
    into_start = np.zeros(n + 1, np.int64)
    n_fwd = 0
    n_back = 0
    for i in range(used):
        b, a = before[i], after[i]
        out_before[i], out_after[i], out_fixed[i] = b, a, fixed[i]
        if b < a:
            into_start[a + 1] += 1
            n_fwd += 1
        elif b > a:
            n_back += 1
    for i in range(m_pairs):
        b, a = pairs[i, 0], pairs[i, 1]
        idx = used + i
        out_before[idx], out_after[idx] = b, a
        if b < a:
            into_start[a + 1] += 1
            n_fwd += 1
        elif b > a:
            n_back += 1
    for k in range(n):
        into_start[k + 1] += into_start[k]
    fill = into_start[:n].copy()
    into = np.empty(n_fwd, np.int64)
    back = np.empty(n_back, np.int64)
    bi = 0
    for i in range(total):
        b, a = out_before[i], out_after[i]
        if b < a:
            into[fill[a]] = i
            fill[a] += 1
        elif b > a:
            back[bi] = i
            bi += 1
    return _Links(out_before, out_after, out_fixed, into, into_start, back)


@jit(nopython=True, cache=True, nogil=True)
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


@jit(nopython=True, cache=True, nogil=True)
def _earliest(links, margin, low_ms, ceiling_ms, earliest, source):
    """Fills each input's earliest hit and what set it (-1 its band, -2 the input before it, else a link); returns the
    first input past its ceiling, or -1."""
    n = low_ms.shape[0]
    earliest[:] = low_ms
    source[:] = -1
    lo = 0
    while True:
        for k in range(lo, n):
            if k and earliest[k - 1] > earliest[k] + _SLACK_MS:
                earliest[k], source[k] = earliest[k - 1], -2
            for c in range(links.into_start[k], links.into_start[k + 1]):
                link = links.into[c]
                hit = earliest[links.before[link]] + links.fixed[link] + margin[link]
                if hit > earliest[k] + _SLACK_MS:
                    earliest[k], source[k] = hit, link
            if earliest[k] > ceiling_ms[k] + _SLACK_MS:
                return k
        if links.back.shape[0] == 0:
            return -1
        next_lo = n
        for idx in range(links.back.shape[0]):
            link = links.back[idx]
            target = links.after[link]
            hit = earliest[links.before[link]] + links.fixed[link] + margin[link]
            if hit > earliest[target] + _SLACK_MS:
                earliest[target], source[target] = hit, link
                if target < next_lo:
                    next_lo = target
        if next_lo == n:
            return -1
        lo = next_lo


@jit(nopython=True, cache=True, nogil=True)
def _latest(links, margin, ceiling_ms, latest):
    """Fills each input's latest hit."""
    n = ceiling_ms.shape[0]
    latest[:] = ceiling_ms
    hi = n - 1
    while True:
        for k in range(hi, -1, -1):
            for c in range(links.into_start[k], links.into_start[k + 1]):
                link = links.into[c]
                latest[links.before[link]] = min(latest[links.before[link]], latest[k] - links.fixed[link] - margin[link])
            if k:
                latest[k - 1] = min(latest[k - 1], latest[k])
        if links.back.shape[0] == 0:
            return
        next_hi = -1
        for idx in range(links.back.shape[0]):
            link = links.back[idx]
            b = links.before[link]
            hit = latest[links.after[link]] - links.fixed[link] - margin[link]
            if hit < latest[b] - _SLACK_MS:
                latest[b] = hit
                if b > next_hi:
                    next_hi = b
        if next_hi < 0:
            return
        hi = next_hi


@jit(nopython=True, cache=True, nogil=True)
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


@jit(nopython=True, cache=True, nogil=True)
def _hits(links, inputs, low_ms, margin, ceiling_ms, sections, middle):
    """The hits under settled margins: the activations first, as their pick moves everything fever ties to them."""
    n = low_ms.shape[0]
    low_ms, ceiling_ms = low_ms.copy(), ceiling_ms.copy()
    earliest, latest = np.empty(n, np.float64), np.empty(n, np.float64)
    source = np.empty(n, np.int64)
    if sections.shape[0]:
        _earliest(links, margin, low_ms, ceiling_ms, earliest, source)
        _latest(links, margin, ceiling_ms, latest)
        max_after = np.arange(1, n + 1, dtype=np.int64)
        for link in links.into:
            b, a = links.before[link], links.after[link]
            if a > max_after[b]:
                max_after[b] = a
        n_back = links.back.shape[0]
        back_before = np.empty(n_back, np.int64)
        back_after = np.empty(n_back, np.int64)
        back_step = np.empty(n_back, np.float64)
        min_back, max_back = n, -1
        for bi in range(n_back):
            link = links.back[bi]
            b = links.before[link]
            back_before[bi] = b
            back_after[bi] = links.after[link]
            back_step[bi] = links.fixed[link] + margin[link]
            if b < min_back:
                min_back = b
            if b > max_back:
                max_back = b
        for row in range(sections.shape[0]):
            k = int(sections[row, 0])
            at = (
                0.5 * (earliest[k] + latest[k])
                if middle[row]
                else min(max(inputs.chart_ms[k], earliest[k]), latest[k])
            )
            low_ms[k], ceiling_ms[k] = at, at
            if at > earliest[k]:
                earliest[k] = at
                limit = min(n - 1, max_after[k])
                j = k
                while j <= limit:
                    if j > k and earliest[j - 1] > earliest[j]:
                        earliest[j] = earliest[j - 1]
                        if max_after[j] > limit:
                            limit = min(n - 1, max_after[j])
                    for c in range(links.into_start[j], links.into_start[j + 1]):
                        link = links.into[c]
                        hit = earliest[links.before[link]] + links.fixed[link] + margin[link]
                        if hit > earliest[j]:
                            earliest[j] = hit
                            if max_after[j] > limit:
                                limit = min(n - 1, max_after[j])
                    jumped_to = j
                    if min_back <= j <= max_back:
                        for bi in range(n_back):
                            if back_before[bi] == j:
                                hit = earliest[j] + back_step[bi]
                                target = back_after[bi]
                                if hit > earliest[target] + _SLACK_MS:
                                    earliest[target] = hit
                                    if max_after[target] > limit:
                                        limit = min(n - 1, max_after[target])
                                    if target < jumped_to:
                                        jumped_to = target
                    if jumped_to < j:
                        j = jumped_to
                        continue
                    j += 1
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


@jit(nopython=True, cache=True, nogil=True)
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
    bands_2 = np.zeros((2, 3, 2), np.float64)
    input_order(lane, lane, no_links, no_links)
    early_greats_kernel(one_ms, flag, lane, flag, bands_2, no_links, no_links)
    ranked_times_kernel(one_ms, flag, flag, flag, bands_2)
    schedule_hits(
        build_schedule_inputs((one_ms, flag, lane, flag, flag, flag), lane, bands_2, no_links, True),
        np.empty((0, 3), np.float64),
        np.empty(0, np.bool_),
    )
