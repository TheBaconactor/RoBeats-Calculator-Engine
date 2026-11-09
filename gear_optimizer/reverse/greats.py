"""Plays with Greats: what the Casual score tells of them, and from a search's rows to stat lines.

A Great costs the Compete score a loss that depends on the line and the Casual score a loss that does not: 100 or 300
points in the body, 51 to 300 at a head note. So a Casual score tells how many Greats lie in the head and, near enough,
where: a class. The rest runs backwards from the score on the GPU (gpu_lines). FT + FF follow from Gear Power, a diagonal of
cells instead of all of them.

Cost: O(r w log c) from r rows to lines, for w walked surfaces in a row's band and c cells of a surface.
"""

from __future__ import annotations

import numpy as np

from gear_optimizer.core.jit_setup import jit
from gear_optimizer.rules import MAX_STAT

_AXIS = MAX_STAT + 1
# Greats listed note by note in a class, and the sets of notes a count may list; a class with more holds their count and the span
# of their positions.
HEAD_LISTED = 3
_LISTED_SETS = 1 << 12
# The most Greats a class puts in the head.
_HEAD_SPANNED = 16
_CLASS_COLUMNS = 9
_SUM_WORDS = (2 * MAX_STAT + 1 + 63) // 64
ROW_COLUMNS = 8
NOTE_COST = 1.0
FAR_COST = 6.0


@jit(nopython=True, cache=True)
def _listed_head(losses, count, target, out):
    """Every set of `count` <= 3 head notes whose losses sum into target (lowest, highest), into out as rows of notes, -1
    past them; returns the rows, out's rows + 1 when more exist."""
    low, high = target
    head = losses.shape[0]
    found = 0
    if count == 0:
        if low <= 0 <= high:
            out[0, 0], out[0, 1], out[0, 2] = -1, -1, -1
            return 1
        return 0
    for a in range(head):
        if count == 1:
            if low <= losses[a] <= high:
                if found == out.shape[0]:
                    return found + 1
                out[found, 0], out[found, 1], out[found, 2] = a, -1, -1
                found += 1
            continue
        for b in range(a + 1, head):
            if count == 2:
                if low <= losses[a] + losses[b] <= high:
                    if found == out.shape[0]:
                        return found + 1
                    out[found, 0], out[found, 1], out[found, 2] = a, b, -1
                    found += 1
                continue
            for c in range(b + 1, head):
                if low <= losses[a] + losses[b] + losses[c] <= high:
                    if found == out.shape[0]:
                        return found + 1
                    out[found, 0], out[found, 1], out[found, 2] = a, b, c
                    found += 1
    return found


@jit(nopython=True, cache=True)
def _position_spans(losses, count, top):
    """For every set size up to `count` and every sum of head losses up to top, the fewest and the most summed 1-based
    positions, a walk over the notes; the most is negative where no set sums to it."""
    fewest = np.full((count + 1, top + 1), 1 << 30, dtype=np.int64)
    most = np.full((count + 1, top + 1), -1, dtype=np.int64)
    fewest[0, 0], most[0, 0] = 0, 0
    for k in range(losses.shape[0]):
        loss = int(losses[k])
        for used in range(count - 1, -1, -1):
            for total in range(top - loss, -1, -1):
                if most[used, total] >= 0:
                    fewest[used + 1, total + loss] = min(fewest[used + 1, total + loss], fewest[used, total] + k + 1)
                    most[used + 1, total + loss] = max(most[used + 1, total + loss], most[used, total] + k + 1)
    return fewest, most


def casual_classes(casual: tuple[float, float], timelines: list[tuple[int, np.ndarray]], greats: int, listed_up_to: int) -> np.ndarray:
    """Where a play with this many Greats can have them, for a Casual score within casual: rows (head Greats, body Greats,
    fewest and most summed head positions, the head notes when listed: up to listed_up_to of them, none where no surface has
    head fever and only the sum of positions matters; then the lowest and highest Casual loss of the head). timelines: per
    Casual timeline, its score with no Greats and what a Great costs at each head note there. A body Great costs 100 outside
    the Casual fever, 300 inside."""
    rows: set[tuple[int, ...]] = set()
    listed = np.empty((_LISTED_SETS, 3), dtype=np.int64)
    spans: dict[bytes, tuple[np.ndarray, np.ndarray]] = {}
    wider: dict[tuple[int, int], list[int]] = {}
    for clean, losses in timelines:
        for head in range(min(greats, _HEAD_SPANNED) + 1):
            body = greats - head
            for inside in range(body + 1):
                low = int(np.ceil(clean - casual[1])) - 100 * (body - inside) - 300 * inside
                high = int(np.floor(clean - casual[0])) - 100 * (body - inside) - 300 * inside
                if high < 0 or (head == 0 and low > 0):
                    continue
                if head <= listed_up_to:
                    found = _listed_head(losses, head, (low, high), listed)
                    if found <= listed.shape[0]:
                        for row in listed[:found].tolist():
                            total = sum(note + 1 for note in row if note >= 0)
                            rows.add((head, body, total, total, *row, low, high))
                        continue
                key = losses.tobytes()
                if key not in spans:
                    spans[key] = _position_spans(losses, _HEAD_SPANNED, int(_HEAD_SPANNED * losses.max()))
                fewest, most = spans[key][0][head], spans[key][1][head]
                hits = [total for total in range(max(low, 0), min(high, most.shape[0] - 1) + 1) if most[total] >= 0]
                if hits:
                    wide = wider.setdefault((head, body), [1 << 30, -1, 1 << 30, -1])
                    wide[0], wide[1] = min(wide[0], int(fewest[hits].min())), max(wide[1], int(most[hits].max()))
                    wide[2], wide[3] = min(wide[2], hits[0]), max(wide[3], hits[-1])
    for (head, body), (first, last, low, high) in wider.items():
        rows.add((head, body, first, last, -1, -1, -1, low, high))
    return np.asarray(sorted(rows), dtype=np.int64).reshape(-1, _CLASS_COLUMNS)


@jit(nopython=True, cache=True)
def cell_sums(cell_start, cells):
    """Per surface, as a bit set, the FT + FF of its cells."""
    bits = np.zeros((cell_start.shape[0] - 1, _SUM_WORDS), dtype=np.int64)
    for u in range(cell_start.shape[0] - 1):
        for k in range(cell_start[u], cell_start[u + 1]):
            total = cells[k] // _AXIS + cells[k] % _AXIS
            bits[u, total >> 6] |= 1 << (total & 63)
    return bits


@jit(nopython=True, cache=True)
def _cell_sum(cell):
    return cell // _AXIS + cell % _AXIS


@jit(nopython=True, cache=True)
def _first_of_sum(cells, first, last, total):
    """Where cells[first : last], sorted by FT + FF, reaches this sum."""
    while first < last:
        middle = (first + last) >> 1
        if _cell_sum(cells[middle]) < total:
            first = middle + 1
        else:
            last = middle
    return first


@jit(nopython=True, cache=True)
def cell_lines(rows, power, points, cells_of, ceiling, out):
    """The cells of rows (surface, CM, FM, base, class, Great points, Perfect Points stat, body Greats in fever) whose surface
    reaches them under the vertices; Gear Power leaves their FT + FF, and a row with no stat takes all of them. Into out as lines
    (row, CM, FM, FT, FF, base, vertex, stat); returns how many, out's rows + 1 when more exist. cells_of: (per surface the first
    and last walked surface of its band, cell_start, cells sorted by FT + FF within a surface); ceiling: (vertex values, prices)."""
    bands, cell_start, cells = cells_of
    values, prices = ceiling
    found = 0
    for r in range(rows.shape[0]):
        u, cm, fm, base, stat = rows[r, 0], rows[r, 1], rows[r, 2], rows[r, 3], rows[r, 6]
        total = -1
        if stat >= 0:
            left = power - 5 * (cm + fm + stat) - 2 * (base - int(points[stat]))
            if left < 0 or left % 5:
                continue
            total = left // 5
        for walked in range(bands[u, 0], bands[u, 1]):
            k = cell_start[walked] if total < 0 else _first_of_sum(cells, cell_start[walked], cell_start[walked + 1], total)
            while k < cell_start[walked + 1] and (total < 0 or _cell_sum(cells[k]) == total):
                ft, ff = cells[k] // _AXIS, cells[k] % _AXIS
                k += 1
                lowest, vertex = 1.0e18, 0
                for j in range(values.shape[0]):
                    bound = values[j] - prices[j, 1] * cm - prices[j, 2] * fm - prices[j, 3] * ft - prices[j, 4] * ff
                    if bound < lowest:
                        lowest, vertex = bound, j
                        if lowest < base:
                            break
                if lowest >= base:
                    if found == out.shape[0]:
                        return found + 1
                    line = out[found]
                    line[0], line[1], line[2], line[3], line[4], line[5], line[6], line[7] = r, cm, fm, ft, ff, base, vertex, stat
                    found += 1
    return found


@jit(nopython=True, cache=True)
def _log_binomial(picked, total, chance, log_factorial):
    return (
        log_factorial[total] - log_factorial[picked] - log_factorial[total - picked]
        + picked * np.log(chance) + (total - picked) * np.log(1.0 - chance)
    )


@jit(nopython=True, cache=True)
def explanation_costs(held, rows, classes, tables, spans, out):
    """Into out, per line of `spans` (first and last + 1 of its held rows), how far-fetched the likeliest play behind it is, in
    nats. A timeline sits on the chart-time timeline of its cell, or a note off: hits land near their notes and a fever window ends
    on one of few notes. Each note off costs NOTE_COST up to FAR_COST, what a play that moves its fever on purpose costs (a Force
    Great plan). Each Great falls in a song's head or fever by the share of notes there. held: cell_lines rows; rows: their rows;
    tables: (per cell its chart-time body fever, per surface its body fever, body notes, head notes, log factorials)."""
    chart_fever, body_fever, body_total, head_len, log_factorial = tables
    notes = max(body_total + head_len, 1)
    for t in range(spans.shape[0]):
        best = 1.0e18
        for k in range(spans[t, 0], spans[t, 1]):
            row = rows[held[k, 0]]
            bf = body_fever[row[0]]
            cost = min(NOTE_COST * abs(bf - chart_fever[held[k, 3] * _AXIS + held[k, 4]]), FAR_COST)
            if classes.shape[0]:
                head, body = classes[row[4], 0], classes[row[4], 1]
                cost -= _log_binomial(row[7], body, min(max(bf / max(body_total, 1), 1.0e-3), 0.999), log_factorial)
                cost -= _log_binomial(head, head + body, min(max(head_len / notes, 1.0e-3), 0.999), log_factorial)
            best = min(best, cost)
        out[t] = best


@jit(nopython=True, cache=True)
def great_points_fit(found, greats, held, rows, spans, out):
    """Into out, per found loadout (its target at column 16), whether a row of its line has its Great points."""
    for r in range(found.shape[0]):
        first, last = spans[found[r, 16], 0], spans[found[r, 16], 1]
        out[r] = False
        for k in range(first, last):
            if rows[held[k, 0], 5] == greats[r]:
                out[r] = True
                break


@jit(nopython=True, cache=True)
def band_surfaces(surfaces, relief, sums, band, body_total):
    """Per head pattern every body fever count within `band` of a walked surface: most Greats do not move a timeline, and a
    few move it a few notes. Returns (pattern, body fever, relief, FT + FF bits, per surface the first and last + 1 walked
    surface in its band, and the fewest notes its body fever lies off a cell's chart-time timeline there); walked surfaces come
    sorted by pattern, then body fever. surfaces: (pattern, body fever, cell_start, cells, per cell its chart-time body fever)."""
    pattern, body_fever, cell_start, cells, chart_fever = surfaces
    walked = pattern.shape[0]
    total = 0
    first = 0
    while first < walked:
        last = first
        while last + 1 < walked and pattern[last + 1] == pattern[first]:
            last += 1
        total += min(body_fever[last] + band, body_total) - max(body_fever[first] - band, 0) + 1
        first = last + 1
    out_pattern = np.empty(total, dtype=np.int32)
    out_body = np.empty(total, dtype=np.int32)
    out_relief = np.full((total, relief.shape[1]), -1.0e18)
    out_sums = np.zeros((total, sums.shape[1]), dtype=np.int64)
    bands = np.empty((total, 2), dtype=np.int64)
    off = np.full(total, body_total + 1, dtype=np.int64)
    at = first = 0
    while first < walked:
        last = first
        while last + 1 < walked and pattern[last + 1] == pattern[first]:
            last += 1
        low, high = first, first
        for body in range(max(body_fever[first] - band, 0), min(body_fever[last] + band, body_total) + 1):
            while low <= last and body_fever[low] < body - band:
                low += 1
            while high <= last and body_fever[high] <= body + band:
                high += 1
            out_pattern[at], out_body[at] = pattern[first], body
            bands[at, 0], bands[at, 1] = low, high
            for u in range(low, high):
                out_relief[at] = np.maximum(out_relief[at], relief[u])
                out_sums[at] |= sums[u]
            for k in range(cell_start[low], cell_start[high]):
                off[at] = min(off[at], abs(body - chart_fever[cells[k]]))
            at += 1
        first = last + 1
    kept = bands[:, 1] > bands[:, 0]
    return out_pattern[kept], out_body[kept], out_relief[kept], out_sums[kept], bands[kept], off[kept]


@jit(nopython=True, cache=True)
def head_witness(gear, casual, count, targets, out):
    """Into out `count` head notes that lose exactly targets[0] of the score and targets[1]..targets[2] of the Casual score;
    returns whether some set does. gear: each note's score loss, negative where the note is barred; casual: its Casual loss,
    non-decreasing along the notes. A depth-first walk that a set's sum bounds cut, 2^20 steps at the most."""
    wanted, casual_low, casual_high = targets
    head = gear.shape[0]
    stack = np.zeros(count + 1, dtype=np.int64)
    depth = 0
    steps = 0
    position = 0
    gear_sum, casual_sum = 0, 0
    while steps < 1 << 20:
        steps += 1
        if depth == count:
            if gear_sum == wanted and casual_low <= casual_sum <= casual_high:
                out[:count] = stack[:count]
                return True
            depth -= 1
            position = stack[depth] + 1
            gear_sum -= gear[stack[depth]]
            casual_sum -= casual[stack[depth]]
            continue
        left = count - depth
        if position + left > head or casual_sum + left * casual[position] > casual_high:
            if depth == 0:
                return False
            depth -= 1
            position = stack[depth] + 1
            gear_sum -= gear[stack[depth]]
            casual_sum -= casual[stack[depth]]
            continue
        if casual_sum + left * casual[head - 1] < casual_low or gear[position] < 0:
            position += 1
            continue
        stack[depth] = position
        gear_sum += gear[position]
        casual_sum += casual[position]
        depth += 1
        position += 1
    return False
