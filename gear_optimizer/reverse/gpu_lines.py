"""The stat lines of a score, on the GPU: every (surface, CM, FM, base, Perfect Points stat), and for a play with Greats
every class, Great points and body Greats in fever that give it.

A lookup hands surfaces over in fixed chunks, so a search cut short keeps the same sample on every run, whatever order the
GPU's threads wrote their rows in. Each chunk runs three packed stages, each thread of a stage one item of the stage before:

  tiles  8 x 8 (CM, FM) blocks whose best corner reaches the score under the ceiling, at an FT + FF the surface has
  pairs  the (CM, FM) of those likewise, as entries of up to 16 base values
  rows   a thread per base value: each Perfect Points stat of it and each class, in float32, and those that can hold in the game's
         float64, the head's notes summed

The float32 test never waits for float64: a value float32 cannot floor keeps both floors and a Great's floors are left to the
exact test. A SIMD group runs as long as its slowest thread, so a rare slow path in a common test costs every lane of the group.
The exact test is inline for the same reason a list of what to test costs more: threads queue for its one atomic counter (320 ns a
candidate on the M4 against 2 ns to test one), and a row is a thirtieth of the candidates.

Cost: O(U (B + J b + p J + b' (log s + s' o c) + h r)) for U surfaces, B = 441 tiles, b tiles left, p pairs left, J vertices, b'
base values, s stats of a residue of which s' give a sum the surface has, o <= 3 Great points, c classes, h head notes and r
candidates: on the M4 5 to 50 ms for most plays (numba: 20 ms to 4 s, the same rows).
"""

from dataclasses import dataclass

import numpy as np

from gear_optimizer.gpu.runtime import init_taichi, ti
from gear_optimizer.gpu.scoring import _FLOAT32_ERROR, _float64_bits, _float64_floor, _float64_of, _float64_product
from gear_optimizer.rules import MAX_STAT

_AXIS = MAX_STAT + 1
_TILE = 8
_BLOCKS = (_AXIS + _TILE - 1) // _TILE
_TILES = _BLOCKS * _BLOCKS
_HEAD = 100
_MASK_WORDS = 4
_SUM_WORDS = 12
_MAX_VERTICES = 64
MAX_CLASSES = 1 << 13
CHUNK_SURFACES = 512
_MAX_TILES = CHUNK_SURFACES * _TILES
_MAX_PAIRS = 1 << 23
_BASE_BITS = 4
_ENTRY_BASES = 1 << _BASE_BITS
_CLASSES_PER_BASE = 16  # classes of a play that cost as much as its base value's other tests
MAX_ROWS = 1 << 22
_CLASS_COLUMNS = 9
_MARGIN = 2.0e-6  # Relative, over float32's order of a bound; rows past the ceiling by this much have no loadout.
_FLOOR_LOW, _FLOOR_HIGH = 1.0 - _FLOAT32_ERROR, 1.0 + _FLOAT32_ERROR
# Over any line, base - Great is under base / 3 + this: Great points are 2/3 of the elements + 150, and Perfect Points at
# most 485.
_GREAT_GAP = 185.0
_SPAN_EDGE = 1.0e-3
_HEAD_FLOAT_POINTS = 4
_SPANNED_EDGE = 0.02  # Over float32's order of a class's head span; `lookup._named_set` confirms each point of it.
_COUNTERS = 4
_LIVE, _PAIRS, _BASES, _ROWS = range(_COUNTERS)
READ_COLUMNS = 6

_Search = ti.types.struct(
    score=ti.i32,
    wanted=ti.f32,
    vertices=ti.i32,
    greats=ti.i32,
    power=ti.i32,
    head_len=ti.i32,
    body_total=ti.i32,
    single_color=ti.i32,
    class_count=ti.i32,
    term_low=ti.f32,
    term_high=ti.f32,
)
_Vec2i = ti.types.vector(2, ti.i32)
_Vec2f = ti.types.vector(2, ti.f32)
_Vec2u = ti.types.vector(2, ti.u32)
_Vec3i = ti.types.vector(3, ti.i32)
_Vec4i = ti.types.vector(4, ti.i32)
_Vec4f = ti.types.vector(4, ti.f32)
_Vec9i = ti.types.vector(_CLASS_COLUMNS, ti.i32)
_I32_ARRAY = ti.types.ndarray(dtype=ti.i32)

# Name: (type, shape), or (type, shape, vector size). Shapes are baked into the compiled kernels, as in gpu.fields.
_FIELDS = {
    # The song.
    "combo": (ti.f32, _AXIS),
    "fever": (ti.f32, _AXIS),
    "combo_bits": (ti.u32, _AXIS, 2),
    "fever_bits": (ti.u32, _AXIS, 2),
    "ramp": (ti.f32, (_AXIS, _HEAD)),
    "ramp_bits": (ti.u32, (_AXIS, _HEAD), 2),
    "vertex_values": (ti.f32, _MAX_VERTICES),
    "vertex_prices": (ti.f32, _MAX_VERTICES, 2),
    "points": (ti.i32, _AXIS),
    "stat_terms": (ti.i32, _AXIS),  # 5 x stat - 2 x its points, sorted within each residue of it mod 5
    "stats_by_term": (ti.i32, _AXIS),
    "residue_start": (ti.i32, 6),
    # A chunk of surfaces.
    "surface_id": (ti.i32, CHUNK_SURFACES),
    "shape_terms": (ti.f32, CHUNK_SURFACES, 4),
    "head_terms": (ti.f32, CHUNK_SURFACES, 4),
    "head_words": (ti.u32, CHUNK_SURFACES, _MASK_WORDS),
    "body_fever": (ti.i32, CHUNK_SURFACES),
    "sum_bits": (ti.u32, (CHUNK_SURFACES, _SUM_WORDS)),
    "sum_span": (ti.i32, CHUNK_SURFACES, 2),
    "relief": (ti.f32, (CHUNK_SURFACES, _MAX_VERTICES)),
    # A play.
    "classes": (ti.i32, MAX_CLASSES, _CLASS_COLUMNS),
    # The lists.
    "counters": (ti.i32, _COUNTERS),
    "live": (ti.i32, _MAX_TILES),
    "pairs": (ti.i32, _MAX_PAIRS, 3),  # (surface << 16 | CM << 8 | FM, first base, last base)
    "rows": (ti.i32, MAX_ROWS, READ_COLUMNS),
}


class _Tables:
    """The fields of _FIELDS, by name."""


tables = _Tables()


def _allocate() -> None:
    for name, (dtype, shape, *vector) in _FIELDS.items():
        field = ti.Vector.field(vector[0], dtype=dtype, shape=shape) if vector else ti.field(dtype=dtype, shape=shape)
        setattr(tables, name, field)


@ti.func
def _floored(base: ti.i32, value: ti.f32, bits: _Vec2u) -> ti.i32:
    """floor(base x value) in the game's float64."""
    rough: ti.f32 = ti.cast(base, ti.f32) * value
    whole: ti.f32 = ti.floor(rough)
    out = ti.cast(whole, ti.i32)
    if ti.abs(rough - whole - 0.5) >= 0.5 - (rough * _FLOAT32_ERROR):
        out = _float64_floor(_float64_product(_float64_of(base), _float64_bits(bits)))
    return out


@ti.func
def _floored_twice(base: ti.i32, value: ti.f32, bits: _Vec2u, more: ti.f32, more_bits: _Vec2u) -> ti.i32:
    """floor(base x value x more) in the game's float64 and order."""
    rough: ti.f32 = ti.cast(base, ti.f32) * value * more
    whole: ti.f32 = ti.floor(rough)
    out = ti.cast(whole, ti.i32)
    if ti.abs(rough - whole - 0.5) >= 0.5 - (rough * _FLOAT32_ERROR):
        exact = _float64_product(_float64_of(base), _float64_bits(bits))
        out = _float64_floor(_float64_product(exact, _float64_bits(more_bits)))
    return out


@ti.func
def _ceiling(u: ti.i32, cm: ti.i32, fm: ti.i32, floor: ti.f32, vertices: ti.i32) -> ti.f32:
    """The lowest vertex bound on surface u's base value at this CM and FM, or the first under floor."""
    best: ti.f32 = 1.0e18
    j = 0
    while j < vertices:
        prices = tables.vertex_prices[j]
        bound: ti.f32 = tables.vertex_values[j] - prices[0] * ti.cast(cm, ti.f32) - prices[1] * ti.cast(fm, ti.f32) + tables.relief[u, j]
        if bound < best:
            best = bound
            if best < floor:
                break
        j += 1
    return best


@ti.func
def _shape_at(terms: _Vec4f, combo: ti.f32, fever: ti.f32) -> ti.f32:
    return combo * (terms[0] * fever + terms[1]) + terms[2] * fever + terms[3]


@ti.func
def _sum_in_span(u: ti.i32, low: ti.f32, high: ti.f32) -> ti.i32:
    """Whether surface u has an FT + FF in low..high."""
    first: ti.i32 = ti.max(ti.cast(ti.ceil(low), ti.i32), 0)
    last: ti.i32 = ti.min(ti.cast(ti.floor(high), ti.i32), 2 * MAX_STAT)
    hit = 0
    if last >= first:
        word = first >> 5
        while word <= (last >> 5):
            value: ti.u32 = tables.sum_bits[u, word]
            if word == first >> 5:
                value &= ~((ti.u32(1) << ti.cast(first & 31, ti.u32)) - ti.u32(1))
            if word == last >> 5 and (last & 31) < 31:
                value &= (ti.u32(1) << ti.cast((last & 31) + 1, ti.u32)) - ti.u32(1)
            if value != ti.u32(0):
                hit = 1
                break
            word += 1
    return hit


@ti.func
def _highest_base(q: _Search, bound: ti.f32, shape: ti.f32, combo: ti.f32, fever: ti.f32) -> ti.f32:
    """Over any base value of a play at this pair: each Great loses at most its base less Great points, a third of the base."""
    loses: ti.f32 = ti.cast(q.greats, ti.f32) * combo * fever * (bound / 3.0 + _GREAT_GAP)
    return ti.min(bound, (q.wanted + loses) / shape + 1.0) * (1.0 + _MARGIN)


@ti.kernel
def _find_tiles(surfaces: ti.i32, q: _Search):
    for i in range(surfaces * _TILES):
        u = i // _TILES
        tile = i % _TILES
        cm_low = (tile // _BLOCKS) * _TILE
        fm_low = (tile % _BLOCKS) * _TILE
        cm_top = ti.min(cm_low + _TILE - 1, MAX_STAT)
        fm_top = ti.min(fm_low + _TILE - 1, MAX_STAT)
        lowest: ti.f32 = q.wanted * (1.0 - _MARGIN) / _shape_at(tables.shape_terms[u], tables.combo[cm_top], tables.fever[fm_top])
        bound: ti.f32 = _ceiling(u, cm_low, fm_low, lowest, q.vertices)
        keep = bound >= lowest
        if keep and q.power >= 0:
            rest_low: ti.f32 = ti.cast(q.power - 5 * (cm_top + fm_top), ti.f32)
            rest_high: ti.f32 = ti.cast(q.power - 5 * (cm_low + fm_low), ti.f32)
            low: ti.f32 = (rest_low - 2.0 * bound - q.term_high) / 5.0 - _SPAN_EDGE
            keep = _sum_in_span(u, low, (rest_high - 2.0 * lowest - q.term_low) / 5.0 + _SPAN_EDGE) != 0
        if keep:
            slot = ti.atomic_add(tables.counters[_LIVE], 1)
            tables.live[slot] = i


@ti.kernel
def _find_pairs(q: _Search):
    for i in range(tables.counters[_LIVE] * _TILE * _TILE):
        at = tables.live[i >> 6]
        u = at // _TILES
        tile = at % _TILES
        cm = (tile // _BLOCKS) * _TILE + ((i >> 3) & 7)
        fm = (tile % _BLOCKS) * _TILE + (i & 7)
        if cm <= MAX_STAT and fm <= MAX_STAT:
            combo: ti.f32 = tables.combo[cm]
            fever: ti.f32 = tables.fever[fm]
            shape: ti.f32 = _shape_at(tables.shape_terms[u], combo, fever)
            floor: ti.f32 = q.wanted * (1.0 - _MARGIN) / shape
            bound: ti.f32 = _ceiling(u, cm, fm, floor, q.vertices)
            keep = bound >= floor
            highest: ti.f32 = _highest_base(q, bound, shape, combo, fever)
            if keep and q.power >= 0:
                rest: ti.f32 = ti.cast(q.power - 5 * (cm + fm), ti.f32)
                low: ti.f32 = (rest - 2.0 * highest - q.term_high) / 5.0 - _SPAN_EDGE
                keep = _sum_in_span(u, low, (rest - 2.0 * floor - q.term_low) / 5.0 + _SPAN_EDGE) != 0
            if keep:
                first: ti.i32 = ti.cast(ti.ceil(floor), ti.i32)
                last: ti.i32 = ti.cast(highest, ti.i32)
                bases: ti.i32 = last - first + 1
                if bases > 0:
                    ti.atomic_add(tables.counters[_BASES], bases)
                    entries: ti.i32 = (bases + _ENTRY_BASES - 1) >> _BASE_BITS
                    slot = ti.atomic_add(tables.counters[_PAIRS], entries)
                    if slot + entries <= _MAX_PAIRS:
                        packed: ti.i32 = (u << 16) | (cm << 8) | fm
                        for entry in range(entries):
                            start = first + (entry << _BASE_BITS)
                            tables.pairs[slot + entry] = ti.Vector([packed, start, ti.min(start + _ENTRY_BASES - 1, last)])


@ti.func
def _note_value(base: ti.i32, cm: ti.i32, note: ti.i32, fm: ti.i32, in_fever: ti.i32) -> ti.i32:
    value: ti.i32 = 0
    if in_fever != 0:
        value = _floored_twice(base, tables.ramp[cm, note], tables.ramp_bits[cm, note], tables.fever[fm], tables.fever_bits[fm])
    else:
        value = _floored(base, tables.ramp[cm, note], tables.ramp_bits[cm, note])
    return value


@ti.func
def _in_fever(u: ti.i32, note: ti.i32) -> ti.i32:
    return ti.cast((tables.head_words[u][note >> 5] >> ti.cast(note & 31, ti.u32)) & ti.u32(1), ti.i32)


@ti.func
def _keeps(pair: _Vec3i, base: ti.i32, klass: ti.i32, great: ti.i32, need: ti.i32) -> ti.i32:
    """Whether a class and its body Greats in fever lose exactly a line's deficit, the head's listed notes exact to the point; a
    class that holds only their span has it float32, with an edge."""
    u, cm, fm = pair[0], pair[1], pair[2]
    spec = tables.classes[klass >> 16]
    fevered: ti.i32 = klass & 65535
    held: ti.i32 = spec[0]
    combo: ti.f32 = tables.combo[cm]
    lost_normal: ti.i32 = _floored(base, combo, tables.combo_bits[cm]) - _floored(great, combo, tables.combo_bits[cm])
    full: ti.i32 = _floored_twice(base, combo, tables.combo_bits[cm], tables.fever[fm], tables.fever_bits[fm])
    gap: ti.i32 = full - _floored_twice(great, combo, tables.combo_bits[cm], tables.fever[fm], tables.fever_bits[fm]) - lost_normal
    rest: ti.i32 = need - spec[1] * lost_normal - fevered * gap
    keep = 0
    if gap > 0 or fevered == 0:
        if held > 0 and spec[4] < 0:
            drop: ti.f32 = ti.cast(base - great, ti.f32)
            step: ti.f32 = (combo - 1.0) * 0.01 * drop
            whole: ti.f32 = drop * ti.cast(held, ti.f32) - ti.cast(held, ti.f32)
            low: ti.f32 = whole + ti.cast(spec[2], ti.f32) * step - _SPANNED_EDGE
            high: ti.f32 = whole + 2.0 * ti.cast(held, ti.f32) + ti.cast(spec[3], ti.f32) * step + _SPANNED_EDGE
            keep = ti.cast(ti.cast(rest, ti.f32) >= low and ti.cast(rest, ti.f32) <= high, ti.i32)
        else:
            for place in range(held):
                note = spec[4 + place]
                in_fever = _in_fever(u, note)
                rest -= _note_value(base, cm, note, fm, in_fever) - _note_value(great, cm, note, fm, in_fever)
            keep = ti.cast(rest == 0, ti.i32)
    return keep


@ti.func
def _clean_score(q: _Search, pair: _Vec3i, base: ti.i32) -> ti.i32:
    """A line's score with no Greats, in the game's float64."""
    u, cm, fm = pair[0], pair[1], pair[2]
    combo: ti.f32 = tables.combo[cm]
    bf: ti.i32 = tables.body_fever[u]
    normal: ti.i32 = _floored(base, combo, tables.combo_bits[cm])
    full: ti.i32 = _floored_twice(base, combo, tables.combo_bits[cm], tables.fever[fm], tables.fever_bits[fm])
    clean: ti.i32 = bf * full + (q.body_total - bf) * normal
    for note in range(q.head_len):
        clean += _note_value(base, cm, note, fm, _in_fever(u, note))
    return clean


@ti.func
def _row(pair: _Vec3i, base: ti.i32, klass: ti.i32, great: ti.i32, stat: ti.i32):
    slot = ti.atomic_add(tables.counters[_ROWS], 1)
    if slot < MAX_ROWS:
        tables.rows[slot] = ti.Vector([tables.surface_id[pair[0]], (pair[1] << 8) | pair[2], base, klass, great, stat])


@ti.func
def _great_points(elements: ti.i32, single_color: ti.i32, option: ti.i32) -> ti.i32:
    """A Great's points at these elements, 4/3 of the primary and 2/3 of the secondary floored: three cases of how the
    elements part, 2 x primary + secondary. On a one-color song 3 divides them, and 0 points means no such line."""
    value: ti.i32 = (2 * elements - option - (2 * ((elements - 2 * option) % 3)) % 3) // 3 + 150
    if single_color != 0:
        value = 0
        if elements % 3 == 0 and option == 0:
            value = 2 * elements // 3 + 150
    return value


@ti.func
def _head_loss_span(row: _Vec9i, u: ti.i32, cm: ti.i32, drop: ti.f32, multipliers: _Vec2f):
    """What a class's head Greats lose at a line, float32: a listed class note by note, others by their span of positions."""
    held: ti.i32 = row[0]
    fewest: ti.f32 = 0.0
    most: ti.f32 = 0.0
    if held > 0 and row[4] < 0:
        step: ti.f32 = (multipliers[0] - 1.0) * 0.01 * drop
        fewest = drop * ti.cast(held, ti.f32) + ti.cast(row[2], ti.f32) * step
        most = drop * ti.cast(held, ti.f32) + ti.cast(row[3], ti.f32) * step
    else:
        for place in range(held):
            note = row[4 + place]
            value: ti.f32 = drop * tables.ramp[cm, note]
            if ((tables.head_words[u][note >> 5] >> ti.cast(note & 31, ti.u32)) & ti.u32(1)) != ti.u32(0):
                value *= multipliers[1]
            fewest += value
        most = fewest
    return ti.Vector([fewest, most])


@ti.func
def _class_rows(q: _Search, pair: _Vec3i, line: _Vec4i, need: _Vec2i, multipliers: _Vec2f) -> ti.i32:
    """The rows of the classes and body Greats in fever a line's deficit can give: a division, within the notes of the surface's
    body. A Great's floors move its loss by a point each way, in fever and out of it. The first class past float32 sums the
    head, a thread's slow path: the rest test the exact deficit. line: (base, Great points, stat, its clean score or -1). Returns
    the clean score."""
    u, cm = pair[0], pair[1]
    base, great, stat, clean = line[0], line[1], line[2], line[3]
    drop: ti.f32 = ti.cast(base - great, ti.f32)
    lost: ti.f32 = drop * multipliers[0]
    gap: ti.f32 = lost * (multipliers[1] - 1.0)
    bf: ti.i32 = tables.body_fever[u]
    outside: ti.i32 = q.body_total - bf
    low, high = need[0], need[1]
    if clean >= 0:
        low, high = clean - q.score, clean - q.score
    for k in range(q.class_count):
        row = tables.classes[k]
        bodies: ti.i32 = row[1]
        span = _head_loss_span(row, u, cm, drop, multipliers)
        spare: ti.f32 = ti.cast(row[0] + 2 * bodies, ti.f32) + 1.0
        body_lost: ti.f32 = ti.cast(bodies, ti.f32) * lost
        fevered: ti.i32 = ti.max(ti.cast(ti.ceil((ti.cast(low, ti.f32) - span[1] - spare - body_lost) / gap), ti.i32), ti.max(0, bodies - outside))
        last: ti.i32 = ti.min(ti.cast(ti.floor((ti.cast(high, ti.f32) - span[0] + spare - body_lost) / gap), ti.i32), ti.min(bodies, bf))
        if fevered <= last and clean < 0:
            clean = _clean_score(q, pair, base)
            low, high = clean - q.score, clean - q.score
            fevered = ti.max(ti.cast(ti.ceil((ti.cast(low, ti.f32) - span[1] - spare - body_lost) / gap), ti.i32), ti.max(0, bodies - outside))
            last = ti.min(ti.cast(ti.floor((ti.cast(high, ti.f32) - span[0] + spare - body_lost) / gap), ti.i32), ti.min(bodies, bf))
        while fevered <= last:
            if low > 0 and _keeps(pair, base, (k << 16) | fevered, great, low) != 0:
                _row(pair, base, (k << 16) | fevered, great, stat)
            fevered += 1
    return clean


@ti.func
def _stat_range(residue: ti.i32, low: ti.i32, high: ti.i32) -> _Vec2i:
    """The stats of a residue whose term lies in low..high: where they start and end in stats_by_term."""
    start: ti.i32 = tables.residue_start[residue]
    end: ti.i32 = tables.residue_start[residue + 1]
    first, last = start, end
    while first < last:
        middle = (first + last) >> 1
        if tables.stat_terms[middle] < low:
            first = middle + 1
        else:
            last = middle
    stop, last = first, end
    while stop < last:
        middle = (stop + last) >> 1
        if tables.stat_terms[middle] <= high:
            stop = middle + 1
        else:
            last = middle
    return ti.Vector([first, stop])


@ti.func
def _stat_rows(q: _Search, pair: _Vec3i, base: ti.i32, need: _Vec2i, multipliers: _Vec2f):
    """A base value's Perfect Points stats: Gear Power ties each to an FT + FF, and the surface must have it. A base's clean score
    is summed once, for the first line that needs it."""
    u = pair[0]
    rest: ti.i32 = q.power - 5 * (pair[1] + pair[2]) - 2 * base
    span = tables.sum_span[u]
    stats = _stat_range((2 * base - q.power) % 5, rest - 5 * span[1], rest - 5 * span[0])
    clean: ti.i32 = -1
    for at in range(stats[0], stats[1]):
        total: ti.i32 = (rest - tables.stat_terms[at]) // 5
        if ((tables.sum_bits[u, total >> 5] >> ti.cast(total & 31, ti.u32)) & ti.u32(1)) != ti.u32(0):
            stat = tables.stats_by_term[at]
            elements: ti.i32 = base - tables.points[stat]
            if q.greats == 0:
                if clean < 0:
                    clean = _clean_score(q, pair, base)
                if clean == q.score:
                    _row(pair, base, 0, 0, stat)
            elif elements > 0:
                previous = -1
                for option in range(3):
                    great = _great_points(elements, q.single_color, option)
                    if great != previous and great != 0 and great < base:
                        previous = great
                        clean = _class_rows(q, pair, ti.Vector([base, great, stat, clean]), need, multipliers)


@ti.kernel
def _find_rows(q: _Search):
    for i in range(ti.min(tables.counters[_PAIRS], _MAX_PAIRS) * _ENTRY_BASES):
        entry = tables.pairs[i >> _BASE_BITS]
        base: ti.i32 = entry[1] + (i & (_ENTRY_BASES - 1))
        if base <= entry[2] and tables.counters[_ROWS] <= MAX_ROWS:
            u = entry[0] >> 16
            cm = (entry[0] >> 8) & 255
            fm = entry[0] & 255
            combo: ti.f32 = tables.combo[cm]
            fever: ti.f32 = tables.fever[fm]
            bf: ti.i32 = tables.body_fever[u]
            rough: ti.f32 = ti.cast(base, ti.f32) * combo
            rough_fever: ti.f32 = rough * fever
            body_low: ti.i32 = bf * ti.cast(rough_fever * _FLOOR_LOW, ti.i32) + (q.body_total - bf) * ti.cast(rough * _FLOOR_LOW, ti.i32)
            body_high: ti.i32 = bf * ti.cast(rough_fever * _FLOOR_HIGH, ti.i32) + (q.body_total - bf) * ti.cast(rough * _FLOOR_HIGH, ti.i32)
            # A head's floors lie within head_len of base x its shape.
            head: ti.i32 = ti.cast(ti.cast(base, ti.f32) * _shape_at(tables.head_terms[u], combo, fever), ti.i32)
            need_high: ti.i32 = body_high + head - q.score + _HEAD_FLOAT_POINTS
            need_low: ti.i32 = body_low + head - q.score - q.head_len - _HEAD_FLOAT_POINTS
            if need_high >= 0 and (q.greats > 0 or need_low <= 0):
                if q.power < 0:
                    if _clean_score(q, ti.Vector([u, cm, fm]), base) == q.score:
                        _row(ti.Vector([u, cm, fm]), base, 0, 0, -1)
                else:
                    _stat_rows(q, ti.Vector([u, cm, fm]), base, ti.Vector([need_low, need_high]), ti.Vector([combo, fever]))


@ti.kernel
def _clear_chunk():
    for slot in range(_ROWS):
        tables.counters[slot] = 0


@ti.kernel
def _clear_rows():
    for slot in range(_COUNTERS):
        tables.counters[slot] = 0


@ti.kernel
def _read_counters(out: _I32_ARRAY):
    for slot in range(_COUNTERS):
        out[slot] = tables.counters[slot]


@ti.kernel
def _read_rows(count: ti.i32, out: _I32_ARRAY):
    for i in range(count):
        row = tables.rows[i]
        for column in ti.static(range(READ_COLUMNS)):
            out[i, column] = row[column]


@ti.kernel
def _load(field: ti.template(), count: ti.i32, values: ti.types.ndarray()):
    for i in range(count):
        field[i] = values[i]


@ti.kernel
def _load_vectors(field: ti.template(), count: ti.i32, values: ti.types.ndarray()):
    for i in range(count):
        for j in ti.static(range(field.n)):
            field[i][j] = values[i, j]


@ti.kernel
def _load_grid(field: ti.template(), rows: ti.i32, columns: ti.i32, values: ti.types.ndarray()):
    for i in range(rows):
        for j in range(columns):
            field[i, j] = values[i, j]


@ti.kernel
def _load_grid_vectors(field: ti.template(), rows: ti.i32, columns: ti.i32, values: ti.types.ndarray()):
    for i in range(rows):
        for j in range(columns):
            for k in ti.static(range(field.n)):
                field[i, j][k] = values[i, j, k]


def _float64_words(values: np.ndarray) -> np.ndarray:
    return np.ascontiguousarray(values, dtype=np.float64).view(np.uint32).reshape(*values.shape, 2)


@dataclass(frozen=True, slots=True, eq=False)
class SongTables:
    """What a song's searches read: its multipliers and vertices."""

    combo: np.ndarray
    ramp: np.ndarray
    fever: np.ndarray
    points: np.ndarray
    vertex_values: np.ndarray
    vertex_prices: np.ndarray  # CM and FM
    head_len: int
    body_total: int
    single_color: bool


@dataclass(frozen=True, slots=True, eq=False)
class SurfaceTables:
    """The surfaces a search walks, in that order: `ids` their places in the arrays the rows name."""

    ids: np.ndarray
    words: np.ndarray  # per surface its head mask
    head_terms: np.ndarray
    shape_terms: np.ndarray
    body_fever: np.ndarray
    sums: np.ndarray  # per surface, FT + FF as 32-bit words of bits
    relief: np.ndarray


def surface_tables(ids: np.ndarray, patterns: tuple[np.ndarray, np.ndarray], surfaces: tuple[np.ndarray, np.ndarray], sums: np.ndarray, relief: np.ndarray, body_total: int) -> SurfaceTables:
    """The surfaces `ids` of arrays by surface. patterns: (words, coeffs) per head pattern; surfaces: (pattern, body fever)."""
    words, coeffs = patterns
    pattern, bodies = surfaces
    picked = coeffs[pattern[ids]].astype(np.float64)
    ramp_fever, ramp_normal = picked[:, 3] * 0.01, picked[:, 2] * 0.01
    head = np.column_stack((ramp_fever, ramp_normal, picked[:, 1] - ramp_fever, picked[:, 0] - ramp_normal))
    shape = head.copy()
    shape[:, 0] += bodies[ids]
    shape[:, 1] += body_total - bodies[ids]
    bits = np.ascontiguousarray(sums[ids]).view(np.uint32).reshape(ids.shape[0], _SUM_WORDS)
    return SurfaceTables(ids, words[pattern[ids], :_MASK_WORDS].astype(np.uint32), head.astype(np.float32), shape.astype(np.float32), bodies[ids].astype(np.int32), bits, relief[ids].astype(np.float32))


def _sum_spans(bits: np.ndarray) -> np.ndarray:
    """Per surface the lowest and highest FT + FF of its bits."""
    unpacked = np.unpackbits(bits.view(np.uint8), axis=1, bitorder="little").astype(bool)
    return np.column_stack((unpacked.argmax(axis=1), unpacked.shape[1] - 1 - unpacked[:, ::-1].argmax(axis=1))).astype(np.int32)


def _stats_by_term(points: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The stats by residue of 2 x their points mod 5, each residue by term: 5 x stat - 2 x points, what Gear Power holds."""
    terms = 5 * np.arange(points.shape[0]) - 2 * points
    residues = (2 * points) % 5
    order = np.lexsort((terms, residues))
    return order.astype(np.int32), terms[order].astype(np.int32), np.searchsorted(residues[order], np.arange(6)).astype(np.int32)


_ready = False
_loaded_song = None


def _start() -> None:
    """The fields, once per process; on macOS on the main thread, as gpu.runtime asks."""
    global _ready
    if not _ready:
        init_taichi()
        _allocate()
        _ready = True


def _load_song(song: SongTables) -> None:
    global _loaded_song
    if song is _loaded_song:
        return
    if song.vertex_values.shape[0] > _MAX_VERTICES:
        raise ValueError(f"reverse lookup: {song.vertex_values.shape[0]} vertices, the GPU tables hold {_MAX_VERTICES}")
    points = song.points.astype(np.int32)
    by_term, terms, starts = _stats_by_term(points.astype(np.int64))
    _load(tables.combo, _AXIS, song.combo.astype(np.float32))
    _load(tables.fever, _AXIS, song.fever.astype(np.float32))
    _load_vectors(tables.combo_bits, _AXIS, _float64_words(song.combo))
    _load_vectors(tables.fever_bits, _AXIS, _float64_words(song.fever))
    _load_grid(tables.ramp, _AXIS, song.head_len, song.ramp[:, : song.head_len].astype(np.float32))
    _load_grid_vectors(tables.ramp_bits, _AXIS, song.head_len, _float64_words(song.ramp[:, : song.head_len]))
    _load(tables.vertex_values, song.vertex_values.shape[0], song.vertex_values.astype(np.float32))
    _load_vectors(tables.vertex_prices, song.vertex_values.shape[0], song.vertex_prices.astype(np.float32))
    _load(tables.points, _AXIS, points)
    _load(tables.stat_terms, _AXIS, terms)
    _load(tables.stats_by_term, _AXIS, by_term)
    _load(tables.residue_start, 6, starts)
    _loaded_song = song


def _load_chunk(surfaces: SurfaceTables, first: int, last: int, vertices: int) -> None:
    span = slice(first, last)
    count = last - first
    _load(tables.surface_id, count, surfaces.ids[span].astype(np.int32))
    _load_vectors(tables.shape_terms, count, surfaces.shape_terms[span])
    _load_vectors(tables.head_terms, count, surfaces.head_terms[span])
    _load_vectors(tables.head_words, count, surfaces.words[span])
    _load(tables.body_fever, count, surfaces.body_fever[span])
    _load_grid(tables.sum_bits, count, _SUM_WORDS, surfaces.sums[span])
    _load_vectors(tables.sum_span, count, _sum_spans(surfaces.sums[span]))
    _load_grid(tables.relief, count, vertices, surfaces.relief[span])


@dataclass(frozen=True, slots=True)
class LineQuery:
    score: int
    power: int  # Gear Power, negative when unknown
    greats: int
    classes: np.ndarray  # greats.casual_classes, empty for a clean play
    bases: int  # the base values of (surface, CM, FM) pairs the search may walk; a play's classes multiply what one counts for


def line_rows(song: SongTables, surfaces: SurfaceTables, query: LineQuery) -> tuple[np.ndarray, bool]:
    """Every row (surface, CM << 8 | FM, base, class << 16 | body Greats in fever, Great points, Perfect Points stat) of a
    score, in no order, and whether they are all: the search stops before a chunk that would pass `bases`, or at MAX_ROWS rows."""
    _start()
    _load_song(song)
    if query.classes.shape[0]:
        _load_vectors(tables.classes, query.classes.shape[0], query.classes.astype(np.int32))
    terms = 5.0 * np.arange(song.points.shape[0]) - 2.0 * song.points
    vertices = song.vertex_values.shape[0]
    search = _Search(
        score=query.score, wanted=float(query.score), vertices=vertices, greats=query.greats, power=query.power, head_len=song.head_len,
        body_total=song.body_total, single_color=int(song.single_color), class_count=query.classes.shape[0], term_low=float(terms.min()), term_high=float(terms.max()),
    )
    counters = np.zeros(_COUNTERS, dtype=np.int32)
    _clear_rows()
    walked = kept = 0
    complete = True
    for first in range(0, surfaces.ids.shape[0], CHUNK_SURFACES):
        last = min(first + CHUNK_SURFACES, surfaces.ids.shape[0])
        _load_chunk(surfaces, first, last, vertices)
        _clear_chunk()
        _find_tiles(last - first, search)
        _find_pairs(search)
        _read_counters(counters)
        walked += int(counters[_BASES]) * (1 + query.classes.shape[0] // _CLASSES_PER_BASE)
        if counters[_PAIRS] > _MAX_PAIRS or walked > query.bases:
            complete = False
            break
        _find_rows(search)
        _read_counters(counters)
        # A list that overflowed holds what the threads' race left: the chunk goes, so a run repeats.
        if counters[_ROWS] > MAX_ROWS:
            complete = False
            break
        kept = int(counters[_ROWS])
    rows = np.empty((kept, READ_COLUMNS), dtype=np.int32)
    if kept:
        _read_rows(kept, rows)
    return rows, complete
