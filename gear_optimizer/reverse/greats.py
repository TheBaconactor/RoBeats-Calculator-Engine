"""Plays with Greats: what the Casual score tells of them, and the stat lines that give their score.

A Great costs the Compete score a loss that depends on the line and the Casual score a loss that does not: 100 or 300
points in the body, 51 to 300 at a head note. So a Casual score tells how many Greats lie in the head and, near enough,
where: a class. The rest runs backwards from the score. A surface and a base leave a deficit; a class says what the deficit
is per point of base - Great, so it gives the Great points; they give the Perfect Points stat; and Gear Power then gives
FT + FF, a diagonal of cells instead of all of them.

Cost: O(u (B + J b + p c)) for the u extended surfaces, B = 400 blocks, b blocks that survive, p (pair, base) rows and c
classes, each row one head sum, O(100); then O(r D) for r rows and D ~ 161 cells on a diagonal.
"""

from __future__ import annotations

import numpy as np

from gear_optimizer.core.jit_setup import jit
from gear_optimizer.rules import MAX_STAT

from .invert import _ceiling_at, _shape_terms

_AXIS = MAX_STAT + 1
_TILE = 8
# Greats listed note by note in a class; a class with more holds their count and the span of their positions.
HEAD_LISTED = 3
# The most Greats a class puts in the head.
_HEAD_SPANNED = 16
_CLASS_COLUMNS = 9
_SUM_WORDS = (2 * MAX_STAT + 1 + 63) // 64
# Over any line, base - Great is under base / 3 + this: Great points are 2/3 of the elements + 150, and Perfect Points at
# most 485.
_GREAT_GAP = 185.0
ROW_COLUMNS = 8
# Head sums a search keeps: most (pair, base) rows of a song share a head, its notes outside fever.
_HEAD_MEMO = 1 << 16


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
    head fever and only the sum of positions matters; then the lowest and highest Casual loss of the head). timelines: per Casual timeline, its score with no Greats and what a
    Great costs at each head note there. A body Great costs 100 outside the Casual fever, 300 inside."""
    rows: set[tuple[int, ...]] = set()
    listed = np.empty((1 << 12, 3), dtype=np.int64)
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
                    if found > listed.shape[0]:
                        raise ValueError("Casual classes: more head sets than the table holds")
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
def _great_options(elements, single_color, out):
    """The Great points of a line whose elements give `elements` (2 x primary + secondary), into out; returns how many:
    4/3 of the primary and 2/3 of the secondary, each floored, leave two values at most."""
    if single_color:
        if elements % 3:
            return 0
        out[0] = 2 * elements // 3 + 150
        return 1
    found = 0
    for rest in range(3):
        value = (2 * elements - rest - (2 * ((elements - 2 * rest) % 3)) % 3) // 3 + 150
        if found == 0 or value != out[0]:
            out[found] = value
            found += 1
    return found


@jit(nopython=True, cache=True)
def _head_weight(row, mask, ramp, combo, fever):
    """What a class's head Greats weigh at a line: the sum of their multipliers."""
    head = row[0]
    if row[4] < 0 and head > 0:
        return head + (combo - 1.0) * 0.005 * (row[2] + row[3])
    weight = 0.0
    for place in range(4, 4 + head):
        note = row[place]
        weight += ramp[note] * (fever if (mask[note >> 5] >> (note & 31)) & 1 else 1.0)
    return weight


@jit(nopython=True, cache=True)
def _head_loss(row, mask, line, lengths):
    """Exactly what a class's listed head Greats lose at a line, or (for more) the fewest and the most, each point of
    their floors allowed."""
    base, great = line
    ramp, combo, fever = lengths
    head = row[0]
    if row[4] < 0 and head > 0:
        step = (combo - 1.0) * 0.01 * (base - great)
        return (base - great) * head + row[2] * step - head, (base - great) * head + row[3] * step + head
    loss = 0
    for place in range(4, 4 + head):
        note = row[place]
        if (mask[note >> 5] >> (note & 31)) & 1:
            loss += int(np.floor(base * ramp[note] * fever)) - int(np.floor(great * ramp[note] * fever))
        else:
            loss += int(np.floor(base * ramp[note])) - int(np.floor(great * ramp[note]))
    return float(loss), float(loss)


@jit(nopython=True, cache=True)
def _base_rows(need, pair, tables, classes, keep):
    """Writes every line a surface gives at one base and deficit. Gear Power leaves a few Perfect Points stats, each its Great
    points; a class then leaves how many body Greats lie in fever, by a division. pair: (surface, CM, FM, base); tables: (mask,
    ramp at CM, combo, fever, points per stat, stats per residue of 2 x their points mod 5 and where each residue starts, one
    color, the Gear Power less 5 x (CM + FM), the surface's FT + FF); keep: (out, found). Returns the rows held."""
    u, cm, fm, base = pair
    mask, ramp, combo, fever, points, by_residue, residue_start, single_color, power, sums = tables
    out, found = keep
    options = np.empty(3, dtype=np.int64)
    wanted = (2 * base - power) % 5
    for at in range(residue_start[wanted], residue_start[wanted + 1]):
        stat = by_residue[at]
        elements = base - int(points[stat])
        left = power - 5 * stat - 2 * elements
        if left < 0 or left >= 5 * (2 * MAX_STAT + 1):
            continue
        total = left // 5
        if not (sums[total >> 6] >> (total & 63)) & 1:
            continue
        for option in range(_great_options(elements, single_color, options)):
            great = options[option]
            if great >= base:
                continue
            body_normal = int(np.floor(float(base) * combo)) - int(np.floor(float(great) * combo))
            body_fever = int(np.floor(float(base) * combo * fever)) - int(np.floor(float(great) * combo * fever))
            gap = body_fever - body_normal
            for c in range(classes.shape[0]):
                row = classes[c]
                low, high = _head_loss(row, mask, (float(base), float(great)), (ramp, combo, fever))
                body = row[1]
                rest_low, rest_high = need - high - body * body_normal, need - low - body * body_normal
                fevered = max(0, int(np.ceil(rest_low / gap))) if gap > 0 else 0
                while fevered <= body and fevered * gap <= rest_high:
                    if fevered * gap >= rest_low:
                        if found == out.shape[0]:
                            return found + 1
                        written = out[found]
                        written[0], written[1], written[2], written[3] = u, cm, fm, base
                        written[4], written[5], written[6], written[7] = c, great, stat, fevered
                        found += 1
                    fevered += 1
                    if gap <= 0:
                        break
    return found


@jit(nopython=True, cache=True)
def _sum_in_span(bits, low, high):
    """Whether a surface reaches an FT + FF within low..high."""
    first, last = max(int(np.ceil(low)), 0), min(int(high), 2 * MAX_STAT)
    for word in range(first >> 6, (last >> 6) + 1 if last >= 0 else 0):
        value = bits[word]
        if word == first >> 6:
            value &= -1 << (first & 63)
        if word == last >> 6 and (last & 63) < 63:
            value &= (1 << ((last & 63) + 1)) - 1
        if value != 0:
            return True
    return False


@jit(nopython=True, cache=True)
def _head_sum(mask, ramp, fever, base):
    """The score of the head notes, all Perfect, as gem_search._surface_score sums them."""
    total = 0
    for note in range(ramp.shape[0]):
        if (int(mask[note >> 5]) >> (note & 31)) & 1:
            total += int(np.floor(base * ramp[note] * fever))
        else:
            total += int(np.floor(base * ramp[note]))
    return total


@jit(nopython=True, cache=True)
def _residues(points):
    """Perfect Points stats by 2 x their points mod 5, and where each residue starts."""
    order = np.empty(points.shape[0], dtype=np.int64)
    start = np.zeros(6, dtype=np.int64)
    at = 0
    for residue in range(5):
        start[residue] = at
        for stat in range(points.shape[0]):
            if (2 * int(points[stat])) % 5 == residue:
                order[at] = stat
                at += 1
    start[5] = at
    return order, start


@jit(nopython=True, cache=True)
def great_rows(score, surfaces, multipliers, notes, ceiling, game, out):
    """Every (surface, CM, FM, base, class, Great points, Perfect Points stat) whose clean score less the class's loss is
    this score, under the ceiling, at a cell the surface reaches and the Gear Power leaves, into out; returns how many rows,
    and whether they are all. surfaces: (words, coeffs, pattern, body fever, FT + FF bit sets, their lowest and
    highest); ceiling: (vertex values, prices, relief per surface); game: (classes, points per Perfect Points, one color,
    Gear Power, the class tests it may spend). Gear Power holds 2 x base + 5 x PP - 2 x its points + 5 x the other stats, so at a pair it leaves a span of
    FT + FF, and a surface whose cells miss the span is skipped before any head is summed."""
    words, coeffs, pattern, body_fevers, sums = surfaces
    combo, ramp, fever = multipliers
    head_len, body_total = notes
    values, prices, relief = ceiling
    classes, points, single_color, power, pairs = game
    wanted = float(score)
    greats = classes[0, 0] + classes[0, 1]
    by_residue, residue_start = _residues(points)
    memo_keys = np.full(_HEAD_MEMO, -1, dtype=np.int64)
    memo_values = np.empty(_HEAD_MEMO, dtype=np.int64)
    walked = 0
    term_low, term_high = 1.0e18, -1.0e18
    for stat in range(points.shape[0]):
        term_low, term_high = min(term_low, 5.0 * stat - 2.0 * points[stat]), max(term_high, 5.0 * stat - 2.0 * points[stat])
    found = 0
    for u in range(pattern.shape[0]):
        p = pattern[u]
        bf = int(body_fevers[u])
        a, e, f, g = _shape_terms(coeffs[p], bf, body_total, 0.0)
        mask = words[p]
        for cm_block in range(0, _AXIS, _TILE):
            cm_top = min(cm_block + _TILE - 1, MAX_STAT)
            alpha_top, beta_top = a * combo[cm_top] + f, e * combo[cm_top] + g
            for fm_block in range(0, _AXIS, _TILE):
                fm_top = min(fm_block + _TILE - 1, MAX_STAT)
                shape = alpha_top * fever[fm_top] + beta_top
                if _ceiling_at(values, prices, relief, u, cm_block, fm_block, wanted / shape) * shape < wanted:
                    continue
                for cm in range(cm_block, cm_top + 1):
                    alpha, beta = a * combo[cm] + f, e * combo[cm] + g
                    for fm in range(fm_block, fm_top + 1):
                        shape = alpha * fever[fm] + beta
                        lowest = wanted / shape
                        bound = _ceiling_at(values, prices, relief, u, cm, fm, lowest)
                        if bound < lowest:
                            continue
                        loses = greats * combo[cm] * fever[fm] * (bound / 3.0 + _GREAT_GAP)
                        highest = min(bound, (wanted + loses) / shape + 1.0)
                        rest = float(power - 5 * (cm + fm))
                        if not _sum_in_span(sums[u], (rest - 2.0 * highest - term_high) / 5.0, (rest - 2.0 * lowest - term_low) / 5.0):
                            continue
                        rest_power = power - 5 * (cm + fm)
                        tables = (mask, ramp[cm][:head_len], combo[cm], fever[fm], points, by_residue, residue_start, single_color, rest_power, sums[u])
                        head_fever = int(mask[0]) | int(mask[1]) | int(mask[2]) | int(mask[3])
                        for base in range(int(np.ceil(lowest)), int(highest) + 1):
                            key = (int(p) << 40) | (cm << 32) | ((fm if head_fever else 0) << 24) | base
                            slot = ((key * 0x1E3779B97F4A7C15) >> 40) & (_HEAD_MEMO - 1)
                            if memo_keys[slot] != key:
                                memo_keys[slot] = key
                                memo_values[slot] = _head_sum(mask, ramp[cm][:head_len], fever[fm], float(base))
                            normal = float(base) * combo[cm]
                            clean = memo_values[slot] + bf * int(np.floor(normal * fever[fm])) + (body_total - bf) * int(np.floor(normal))
                            need = clean - score
                            if need <= 0:
                                continue
                            found = _base_rows(need, (u, cm, fm, base), tables, classes, (out, found))
                            if found > out.shape[0]:
                                return out.shape[0], False
                            if walked > pairs:
                                return found, False
                            walked += classes.shape[0]
    return found, True


@jit(nopython=True, cache=True)
def cell_lines(rows, power, points, cells_of, ceiling, out):
    """The cells of rows (great_rows) whose surface reaches them and Gear Power leaves: FT + FF follows from it. Into out as
    lines (row, CM, FM, FT, FF, base, vertex, Perfect Points stat); returns how many, out's rows + 1 when more exist.
    cells_of: (per surface the first and last walked surface of its band, cell_start, cells); ceiling: (vertex values, prices)."""
    bands, cell_start, cells = cells_of
    values, prices = ceiling
    found = 0
    for r in range(rows.shape[0]):
        u, cm, fm, base, stat = rows[r, 0], rows[r, 1], rows[r, 2], rows[r, 3], rows[r, 6]
        left = power - 5 * (cm + fm + stat) - 2 * (base - int(points[stat]))
        if left < 0 or left % 5:
            continue
        total = left // 5
        for k in range(cell_start[bands[u, 0]], cell_start[bands[u, 1]]):
            ft, ff = cells[k] // _AXIS, cells[k] % _AXIS
            if ft + ff != total:
                continue
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
def band_surfaces(surfaces, relief, sums, band, body_total):
    """Per head pattern every body fever count within `band` of a walked surface: most Greats do not move a timeline, and a
    few move it a few notes. Returns (pattern, body fever, relief, FT + FF bits, lowest and highest, per surface the first
    and last + 1 walked surface in its band); walked surfaces come sorted by pattern, then body fever. surfaces: (pattern,
    body fever)."""
    pattern, body_fever = surfaces
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
            at += 1
        first = last + 1
    return out_pattern, out_body, out_relief, out_sums, bands


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
