"""The released loadouts of one song as a search space: the upper bound of what they reach, and the loadouts themselves.

A target is a final (CM, FM, FT, FF) and base value. Pricing those four stats and Perfect Points relaxes the loadout's
choices apart: each slot takes its item worth most at the prices and every gem the gem worth most, so the sum, less the
target at the same prices, bounds the base value of every loadout that reaches the target (a Lagrangian dual). At its
lowest the bound sits a few points over the true best (stored rows: 2,148 vs 2,144 and 1,935.6 vs 1,935).

Exact loadouts come from a subset sum over the slots (ValueTables), O(levels x I x 108 x V / 64) words per element choice,
~2 ms and 1.3 MB in all for V ~ 3,000 values, and a walk in order of what an item gives up at the target's prices. The walk
never enters a sum the tables do not hold and stops a slot where what it gave up passes the bound's slack. Cost: O(I) per
bound for I = 368 items (~1.6 us), and per target O(I log I) to order the items, O(element rows x fixed rows x 161) for the
openings, then near a song's top a handful of items per slot.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import prod

import numpy as np

from gear_optimizer.core.jit_setup import jit
from gear_optimizer.core.team_buff import TEAM_BUFF_TIER_EFFECTS
from gear_optimizer.data.game_export import Catalog
from gear_optimizer.gamedata import ELEMENTS, Gear, song_minis
from gear_optimizer.rules import (
    ELEMENT_GEM_GAIN,
    GEM_BUDGET,
    MAX_STAT,
    STAT_GEM_ELEMENT_GAIN,
    STAT_GEM_GAIN_FEVER,
    STAT_GEM_GAIN_NORMAL,
)
from gear_optimizer.stats import STAT_GEMS

# An item row: stats in PRICED order, then the song's primary and secondary element (a one-color song's in both).
PRICED = ("Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Time", "Fever Fill Rate")
PRIMARY, SECONDARY = len(PRICED), len(PRICED) + 1
_ROW = len(PRICED) + 2
GEAR_SLOTS = ("Hat", "Neck", "Face", "Shirt", "Back", "Pants")
# What a selected element gem adds: to the primary, to the secondary, to neither.
_ELEMENT_ROWS = 3
_GEM_ROWS = len(STAT_GEMS) + _ELEMENT_ROWS
_LAST_STEP = 0.02
_UNKNOWN_GAP = 0.008
# Over a bound's float sum: a loadout can sit exactly on the bound, and every test against it keeps that loadout.
BOUND_ROUNDING = 1.0e-6


@dataclass(frozen=True, slots=True, eq=False)
class LoadoutSpace:
    """A song's items: items[starts[s] : starts[s + 1]] per gear slot, then the minis, each sorted by element value.
    gems: what one gem of each kind adds (PRICED's stat gems, then the element gem on each color choice)."""

    items: np.ndarray
    starts: np.ndarray
    names: tuple[str, ...]
    gems: np.ndarray
    primary: str
    secondary: str


@dataclass(frozen=True, slots=True)
class FixedStats:
    """A TeamBuff tier on one team color, as the stats every loadout starts from."""

    tier: str
    team_color: str
    row: np.ndarray


def _item_row(stats: Mapping[str, int], primary: str, secondary: str) -> list[int]:
    return [stats[stat] for stat in PRICED] + [stats[primary], stats[secondary]]


def _gem_table(primary: str, secondary: str) -> np.ndarray:
    gems = np.zeros((_GEM_ROWS, _ROW), dtype=np.int64)
    gains = {"Perfect Points": STAT_GEM_GAIN_NORMAL, "Combo Multiplier": STAT_GEM_GAIN_NORMAL}
    for row, stat in enumerate(PRICED):
        element = STAT_GEMS[stat][1]
        gems[row, row] = gains.get(stat, STAT_GEM_GAIN_FEVER)
        gems[row, PRIMARY] = STAT_GEM_ELEMENT_GAIN * (element == primary)
        gems[row, SECONDARY] = STAT_GEM_ELEMENT_GAIN * (element == secondary)
    offset = len(PRICED)
    gems[offset, PRIMARY] = ELEMENT_GEM_GAIN
    gems[offset, SECONDARY] = ELEMENT_GEM_GAIN * (primary == secondary)
    gems[offset + 1, SECONDARY] = ELEMENT_GEM_GAIN
    gems[offset + 1, PRIMARY] = ELEMENT_GEM_GAIN * (primary == secondary)
    return gems


def loadout_space(catalog: Catalog, song_name: str, primary: str, secondary: str) -> LoadoutSpace:
    rows: list[np.ndarray] = []
    names: list[str] = []
    starts = [0]

    def add(items: Sequence[tuple[str, Mapping[str, int]]]) -> None:
        table = np.asarray([_item_row(stats, primary, secondary) for _name, stats in items], dtype=np.int64)
        order = np.argsort(-(2 * table[:, PRIMARY] + table[:, SECONDARY]), kind="stable")
        rows.append(table[order])
        names.extend(items[index][0] for index in order.tolist())
        starts.append(starts[-1] + len(items))

    gears: Sequence[Gear] = list(catalog.gears.values())
    for slot in GEAR_SLOTS:
        add([(gear.name, gear.stats) for gear in gears if gear.slot == slot])
    add([(mini.name, mini.stats) for mini in song_minis(catalog.minis.values(), song_name, primary, secondary)])
    return LoadoutSpace(
        np.concatenate(rows), np.asarray(starts, dtype=np.int64), tuple(names), _gem_table(primary, secondary), primary,
        secondary,
    )


def fixed_stats(space: LoadoutSpace, tiers: Sequence[str]) -> list[FixedStats]:
    """Each tier on the team colors that differ for this song: the primary, the secondary, any other."""
    other = next(color for color in ELEMENTS if color not in (space.primary, space.secondary))
    out = []
    for tier in tiers:
        effect = TEAM_BUFF_TIER_EFFECTS[tier]
        for color in dict.fromkeys((space.primary, space.secondary, other)):
            row = np.zeros(_ROW, dtype=np.int64)
            row[0] = effect["PP"]
            row[PRIMARY] = effect["Elem"] * (color == space.primary)
            row[SECONDARY] = effect["Elem"] * (color == space.secondary)
            out.append(FixedStats(tier, color, row))
    return out


@jit(nopython=True, cache=True)
def _row_value(row, prices):
    return float(2 * row[5] + row[6]) + prices[0] * row[0] + prices[1] * row[1] + prices[2] * row[2] + prices[3] * row[3] + prices[4] * row[4]


@jit(nopython=True, cache=True)
def relaxed_best(items, starts, gems, prices, used):
    """The best of each choice at these prices, every choice alone: its value, and into `used` the stats it spends."""
    used[:] = 0.0
    total = 0.0
    mini_slot = starts.shape[0] - 2
    for slot in range(mini_slot):
        best, chosen = -1.0e18, -1
        for i in range(starts[slot], starts[slot + 1]):
            value = _row_value(items[i], prices)
            if value > best:
                best, chosen = value, i
        total += best
        used += items[chosen, :5]
    first = second = third = -1.0e18
    first_i = second_i = third_i = -1
    for i in range(starts[mini_slot], starts[mini_slot + 1]):
        value = _row_value(items[i], prices)
        if value > first:
            third, third_i, second, second_i = second, second_i, first, first_i
            first, first_i = value, i
        elif value > second:
            third, third_i = second, second_i
            second, second_i = value, i
        elif value > third:
            third, third_i = value, i
    total += first + second + third
    used += items[first_i, :5] + items[second_i, :5] + items[third_i, :5]
    best, chosen = 0.0, -1
    for g in range(gems.shape[0]):
        value = _row_value(gems[g], prices)
        if value > best:
            best, chosen = value, g
    total += GEM_BUDGET * best
    if chosen >= 0:
        used += GEM_BUDGET * gems[chosen, :5]
    return total


@jit(nopython=True, cache=True)
def points_conjugate(points, price):
    """The most Perfect Points' points exceed price x the stat, and the stat there."""
    best, chosen = -1.0e18, 0
    for stat in range(points.shape[0]):
        value = points[stat] - price * stat
        if value > best:
            best, chosen = value, stat
    return best, chosen


@jit(nopython=True, cache=True)
def _price_bound(items, starts, gems, points, target, prices, used):
    """The bound at these prices on the base value of a target (place 0: minus the fixed Perfect Points; 1..4: CM, FM,
    FT, FF), before the fixed elements; `used` gets its subgradient."""
    conjugate, stat = points_conjugate(points, prices[0])
    value = relaxed_best(items, starts, gems, prices, used) + conjugate
    used[0] -= stat
    for d in range(5):
        value -= prices[d] * target[d]
        used[d] -= target[d]
    return value


@jit(nopython=True, cache=True)
def lowest_bound(items, starts, gems, points, target, prices, steps):
    """The lowest bound subgradient steps find from these prices (changed in place to the best found), and it."""
    best = 1.0e18
    best_prices = prices.copy()
    current = prices.copy()
    used = np.zeros(5)
    step = 1.0
    decay = _LAST_STEP ** (1.0 / steps)
    for _ in range(steps):
        value = _price_bound(items, starts, gems, points, target, current, used)
        if value < best:
            best = value
            best_prices[:] = current
        norm = np.sqrt(np.sum(used * used))
        if norm < 1.0e-9:
            break
        current -= step * used / norm
        step *= decay
    prices[:] = best_prices
    return best


@dataclass(frozen=True, slots=True, eq=False)
class ValueTables:
    """What a loadout's items are worth once its gems are accounted, per choice of element gem.

    A gem bought for a stat is an element gem not bought, so at a target's final stats the element value of the whole
    loadout is linear in its items: 2 x primary + secondary + each stat x what a point of it saves, in halves. Exact
    loadouts are then a subset sum over the slots, carried per residue of the five stats modulo their gem gains (only a
    matching residue leaves whole gems): layers[e, k, r] holds, as a bit set, the sums of levels k.. (the gear slots, then
    three minis) at residue r."""

    element_rows: np.ndarray
    values: np.ndarray  # per element row and item, its value in halves over its slot's lowest
    floors: np.ndarray  # per element row, the sum of the slots' lowest values
    layers: np.ndarray
    prices: np.ndarray  # per element row, in halves per point, PRICED's five
    removed: np.ndarray  # per item, the residue of its stats' negatives
    add: np.ndarray  # residue + residue
    lows: np.ndarray  # per level and stat, the least levels k.. add
    highs: np.ndarray

    @property
    def arrays(self) -> tuple[np.ndarray, ...]:
        return (self.element_rows, self.values, self.floors, self.layers, self.prices, self.removed, self.add, self.lows, self.highs)


_GAINS = (STAT_GEM_GAIN_NORMAL, STAT_GEM_GAIN_NORMAL, STAT_GEM_GAIN_FEVER, STAT_GEM_GAIN_FEVER, STAT_GEM_GAIN_FEVER)
_RESIDUES = prod(_GAINS)


@jit(nopython=True, cache=True)
def _residue(stats):
    """A row's five stats modulo their gem gains, as one number."""
    residue = 0
    for d in range(5):
        residue = residue * _GAINS[d] + stats[d] % _GAINS[d]
    return residue


@jit(nopython=True, cache=True)
def _residues_of(rows):
    out = np.empty(rows.shape[0], dtype=np.int64)
    for i in range(rows.shape[0]):
        out[i] = _residue(rows[i])
    return out


@jit(nopython=True, cache=True)
def _residue_sums():
    digits = np.empty((_RESIDUES, 5), dtype=np.int64)
    for residue in range(_RESIDUES):
        rest = residue
        for d in range(4, -1, -1):
            digits[residue, d] = rest % _GAINS[d]
            rest //= _GAINS[d]
    add = np.empty((_RESIDUES, _RESIDUES), dtype=np.int64)
    for left in range(_RESIDUES):
        for right in range(_RESIDUES):
            add[left, right] = _residue(digits[left] + digits[right])
    return add


@jit(nopython=True, cache=True)
def _fill_layers(layers, values, residues, starts, add):
    """Each layer from the one after it: every item of the level's slot over every sum of the levels after it."""
    words = layers.shape[2]
    levels = layers.shape[0] - 1
    layers[levels, 0, 0] = 1
    for level in range(levels - 1, -1, -1):
        slot = min(level, starts.shape[0] - 2)
        for i in range(starts[slot], starts[slot + 1]):
            whole, part = values[i] >> 6, values[i] & 63
            for source in range(_RESIDUES):
                from_words = layers[level + 1, source]
                to_words = layers[level, add[source, residues[i]]]
                for w in range(words - whole):
                    bits = from_words[w]
                    if bits != 0:
                        to_words[w + whole] |= bits << np.uint64(part)
                        if part and w + whole + 1 < words:
                            to_words[w + whole + 1] |= bits >> np.uint64(64 - part)


def value_tables(space: LoadoutSpace) -> ValueTables:
    worth = 2 * space.gems[:, PRIMARY] + space.gems[:, SECONDARY]
    element_rows = np.asarray(list(dict.fromkeys((PRIMARY, SECONDARY if space.primary != space.secondary else PRIMARY, SECONDARY + 1))))
    prices = np.asarray([[2 * (worth[row] - worth[d]) // space.gems[d, d] for d in range(len(PRICED))] for row in element_rows])
    items, starts = space.items, space.starts
    raw = (2 * (2 * items[:, PRIMARY] + items[:, SECONDARY]))[None, :] + prices @ items[:, : len(PRICED)].T
    slots = len(starts) - 1
    level_slots = [*range(slots), slots - 1, slots - 1]
    lows = np.zeros((len(level_slots) + 1, len(PRICED)), dtype=np.int64)
    highs = lows.copy()
    values = raw.copy()
    floors = np.zeros(len(element_rows), dtype=np.int64)
    tops = np.zeros(len(element_rows), dtype=np.int64)
    for level in range(len(level_slots) - 1, -1, -1):
        span = slice(starts[level_slots[level]], starts[level_slots[level] + 1])
        lows[level] = lows[level + 1] + items[span, : len(PRICED)].min(axis=0)
        highs[level] = highs[level + 1] + items[span, : len(PRICED)].max(axis=0)
        lowest = raw[:, span].min(axis=1)
        values[:, span] = raw[:, span] - lowest[:, None]
        floors += lowest
        tops += values[:, span].max(axis=1)
    layers = np.zeros((len(element_rows), len(level_slots) + 1, _RESIDUES, int(tops.max()) // 64 + 1), dtype=np.uint64)
    add = _residue_sums()
    residues = _residues_of(items)
    for e in range(len(element_rows)):
        _fill_layers(layers[e], values[e], residues, starts, add)
    return ValueTables(element_rows, values, floors, layers, prices, _residues_of(-items), add, lows, highs)


@jit(nopython=True, cache=True)
def holds_bit(words, value):
    """Whether a bit set (64-bit words) holds a value."""
    return value >= 0 and (value >> 6) < words.shape[0] and bool((words[value >> 6] >> np.uint64(value & 63)) & np.uint64(1))


@jit(nopython=True, cache=True)
def _openings(arrays, gems, points, query, out):
    """The Perfect Points stats a target can open with at one element row: rows (stat, the value left in halves), into
    out; returns how many. query: (final stats, their place 0 yours to change, base, Gear Power or negative, fixed row, the
    first and last stat to try)."""
    floor, first_layer, prices, element_row = arrays
    target, base, power, fixed, first_stat, last_stat = query
    fever_stats = 0
    priced = -2 * GEM_BUDGET * (2 * gems[element_row, 5] + gems[element_row, 6]) - 2 * (2 * fixed[5] + fixed[6])
    for d in range(1, 5):
        fever_stats += target[d]
        priced += prices[d] * (target[d] - fixed[d])
    found = 0
    for stat in range(first_stat, last_stat + 1):
        elements = base - int(points[stat])
        if power >= 0 and 5 * (stat + fever_stats) + 2 * elements != power:
            continue
        target[0] = stat
        value = 2 * elements + priced + prices[0] * (stat - fixed[0]) - floor
        if holds_bit(first_layer[_residue(target - fixed[:5])], value):
            out[found, 0], out[found, 1] = stat, value
            found += 1
    return found


@jit(nopython=True, cache=True)
def shortfalls(items, starts, prices):
    """What each item gives up at these prices against the bound (its slot's best, for a mini the third best), and the
    items of each slot in that order."""
    short = np.empty(items.shape[0])
    order = np.empty(items.shape[0], dtype=np.int64)
    for slot in range(starts.shape[0] - 1):
        first = starts[slot]
        values = np.empty(starts[slot + 1] - first)
        for i in range(values.shape[0]):
            values[i] = _row_value(items[first + i], prices)
        ranked = np.sort(values)
        reference = ranked[ranked.shape[0] - (3 if slot == starts.shape[0] - 2 else 1)]
        short[first : starts[slot + 1]] = np.maximum(reference - values, 0.0)
        order[first : starts[slot + 1]] = first + np.argsort(-values)
    return short, order


@jit(nopython=True, cache=True)
def _walk_exact(space, arrays, query, scratch, found, budget):
    """The loadouts of one opening, into found (rows: 9 item indices, 7 gem values); returns (rows, items tried), budget + 1
    tried when it stopped early. query: (final stats, fixed row, value left, shortfalls and their item order, the bound's
    slack). A walk never enters a sum the layers do not hold, gives up at most the slack, and keeps every stat within
    what the slots left and the gems can still add."""
    items, starts, gems = space
    values, removed, add, layers, lows, highs, element_row = arrays
    target, fixed, value, short, order, slack = query
    positions, partial, left, mods, given, chosen = scratch
    levels = layers.shape[0] - 1
    mini_level = starts.shape[0] - 2
    partial[0] = fixed
    left[0] = value
    mods[0] = _residue(target - fixed[:5])
    given[0] = 0.0
    positions[0] = starts[0]
    tried = written = depth = 0
    while True:
        if depth == levels:
            if written == found.shape[0]:
                return written, budget + 1
            row = found[written]
            row[:levels] = chosen
            spent = 0
            for d in range(5):
                row[levels + d] = (target[d] - partial[depth, d]) // gems[d, d]
                spent += row[levels + d]
            row[levels + 5] = GEM_BUDGET - spent
            row[levels + 6] = element_row
            written += 1
            depth -= 1
            continue
        at = positions[depth]
        i = order[at] if at < starts[min(depth, mini_level) + 1] else -1
        if i < 0 or given[depth] + short[i] > slack:
            if depth == 0:
                return written, tried
            depth -= 1
            continue
        positions[depth] = at + 1
        tried += 1
        if tried > budget:
            return written, tried
        rest = left[depth] - values[i]
        residue_left = add[mods[depth], removed[i]]
        if rest < 0 or not (layers[depth + 1, residue_left, rest >> 6] >> np.uint64(rest & 63)) & np.uint64(1):
            continue
        need = 0
        for d in range(7):
            partial[depth + 1, d] = partial[depth, d] + items[i, d]
        for d in range(5):
            room = target[d] - partial[depth + 1, d]
            if room < lows[depth + 1, d]:
                need = GEM_BUDGET + 1
                break
            if room > highs[depth + 1, d]:
                need += (room - highs[depth + 1, d] + gems[d, d] - 1) // gems[d, d]
        if need > GEM_BUDGET:
            continue
        left[depth + 1] = rest
        mods[depth + 1] = residue_left
        given[depth + 1] = given[depth] + short[i]
        chosen[depth] = i
        depth += 1
        if depth <= mini_level:
            positions[depth] = starts[depth]
        elif depth < levels:
            positions[depth] = at + 1


@jit(nopython=True, cache=True)
def _gift(fixed, price):
    """The most a TeamBuff gives at this Perfect Points price."""
    best = -1.0e18
    for f in range(fixed.shape[0]):
        best = max(best, 2.0 * fixed[f, 5] + fixed[f, 6] + price * fixed[f, 0])
    return best


@jit(nopython=True, cache=True)
def lowest_at(space, fixed, points, stats, prices, steps):
    """The lowest bound subgradient steps find on the base value at final stats (CM, FM, FT, FF at places 1..4), from these
    prices (changed in place to the best found), over every TeamBuff."""
    items, starts, gems = space
    top = np.max(fixed[:, 0])
    stats[0] = -top
    bound = lowest_bound(items, starts, gems, points, stats, prices, steps)
    return bound + _gift(fixed, prices[0]) - prices[0] * top + BOUND_ROUNDING


@jit(nopython=True, cache=True)
def search_targets(space, tables, fixed, points, vertices, query, found):
    """The loadouts of target rows (surface, CM, FM, FT, FF, base, vertex, Perfect Points stat or negative) in order, into
    found (rows: 9 item indices, 7 gem values, target, fixed row), until `limit` targets hold loadouts or the work budget
    ends; returns (rows, targets reached, whether every target was searched to its end). The vertex prices the target's walks.
    A target no subset sum holds costs its openings alone. query: (targets, Gear Power or negative, limit, budget, items a target may
    try, work per target with openings, rows per target)."""
    items, starts, gems = space
    element_rows, values, floors, layers, table_prices, removed, add, lows, highs = tables
    vertex_values, vertex_prices = vertices
    targets, power, limit, budget, per_target, setup, rows_per_target = query
    levels = layers.shape[1] - 1
    scratch = (
        np.empty(levels + 1, dtype=np.int64), np.empty((levels + 1, 7), dtype=np.int64), np.empty(levels + 1, dtype=np.int64),
        np.empty(levels + 1, dtype=np.int64), np.empty(levels + 1), np.empty(levels, dtype=np.int64),
    )
    final = np.zeros(5, dtype=np.int64)
    openings = np.empty((points.shape[0], 2), dtype=np.int64)
    short = np.empty(items.shape[0])
    order = np.empty(items.shape[0], dtype=np.int64)
    work = written = held = 0
    complete = True
    for t in range(targets.shape[0]):
        if held >= limit or work > budget:
            return written, t, False
        base = targets[t, 5]
        prices = vertex_prices[targets[t, 6]]
        bound = vertex_values[targets[t, 6]]
        for d in range(1, 5):
            final[d] = targets[t, d]
            bound -= prices[d] * targets[t, d]
        first_stat, last_stat = (0, points.shape[0] - 1) if targets[t, 7] < 0 else (targets[t, 7], targets[t, 7])
        gift = _gift(fixed, prices[0])
        best_points = points_conjugate(points, prices[0])[0]
        ranked = False
        walked = 0
        before = written
        for e in range(element_rows.shape[0]):
            arrays = (floors[e], layers[e, 0], table_prices[e], element_rows[e])
            walk_arrays = (values[e], removed, add, layers[e], lows, highs, element_rows[e])
            for f in range(fixed.shape[0]):
                slack = bound - gift + 2.0 * fixed[f, 5] + fixed[f, 6] + prices[0] * fixed[f, 0] - base
                if slack < 0.0:
                    continue
                count = _openings(arrays, gems, points, (final, base, power, fixed[f], first_stat, last_stat), openings)
                for k in range(count):
                    stat, value = openings[k, 0], openings[k, 1]
                    room = slack - best_points + points[stat] - prices[0] * stat
                    allowed = per_target - walked
                    if room < 0.0 or allowed < 0:
                        complete = complete and room < 0.0
                        continue
                    if not ranked:
                        short, order = shortfalls(items, starts, prices)
                        ranked = True
                        work += setup
                    final[0] = stat
                    rows_left = min(rows_per_target - (written - before), found.shape[0] - written)
                    rows, used = _walk_exact(space, walk_arrays, (final, fixed[f], value, short, order, room), scratch, found[written : written + rows_left], allowed)
                    complete = complete and used <= allowed
                    found[written : written + rows, 16] = t
                    found[written : written + rows, 17] = f
                    written += rows
                    walked += used
        work += walked
        held += written > before
    return written, targets.shape[0], complete


@jit(nopython=True, cache=True)
def _plain_score(stats, line_shape, combo, fever, points):
    """About a stat row's all-Perfect score at chart time: its base value x the bound shape of its cell's timeline."""
    cell = min(max(stats[3], 0), MAX_STAT) * (MAX_STAT + 1) + min(max(stats[4], 0), MAX_STAT)
    a, e, f, g = line_shape[cell, 0], line_shape[cell, 1], line_shape[cell, 2], line_shape[cell, 3]
    cm, fm = min(max(stats[1], 0), MAX_STAT), min(max(stats[2], 0), MAX_STAT)
    base = float(2 * stats[5] + stats[6]) + points[min(max(stats[0], 0), MAX_STAT)]
    return base * (combo[cm] * (a * fever[fm] + e) + f * fever[fm] + g)


@jit(nopython=True, cache=True)
def _gem_gap(stats, gems, held, element_row, trial, tables):
    """The share of a stat row's plain score the best move of one gem would add: a gem of a kind it holds (held[kind] > 0) to
    any stat or to its element row. tables: (per cell the (A, E, F, G) of its chart-time timeline, combo, fever, points per
    Perfect Points stat); trial: a row to work in."""
    line_shape, combo, fever, points = tables
    plain = _plain_score(stats, line_shape, combo, fever, points)
    best = plain
    for kind in range(gems.shape[0]):
        if held[kind] == 0:
            continue
        for other in range(gems.shape[0]):
            if other != kind and (other < 5 or other == element_row):
                for d in range(7):
                    trial[d] = stats[d] - gems[kind, d] + gems[other, d]
                best = max(best, _plain_score(trial, line_shape, combo, fever, points))
    return (best - plain) / plain


@jit(nopython=True, cache=True)
def gem_gaps(found, space, fixed, tables, single_color, gaps, greats):
    """Into gaps, per found loadout, _gem_gap at its own gems: players place their gems, so the set behind a play is one a
    move barely helps; and into greats its Great points. tables: _gem_gap's."""
    items, gems = space
    stats = np.empty(7, dtype=np.int64)
    trial = np.empty(7, dtype=np.int64)
    counts = np.empty(gems.shape[0], dtype=np.int64)
    for r in range(found.shape[0]):
        row = found[r]
        stats[:] = fixed[row[17]][:7]
        for level in range(9):
            stats += items[row[level]][:7]
        counts[:] = 0
        counts[:5] = row[9:14]
        counts[row[15]] = row[14]
        for kind in range(gems.shape[0]):
            stats += counts[kind] * gems[kind][:7]
        greats[r] = 2 * stats[5] + 150 if single_color else (4 * stats[5]) // 3 + (2 * stats[6]) // 3 + 150
        gaps[r] = _gem_gap(stats, gems, counts, row[15], trial, tables)


@jit(nopython=True, cache=True)
def line_gaps(lines, gems, tables, gaps):
    """Into gaps, per line (surface, CM, FM, FT, FF, base, vertex, Perfect Points stat), _gem_gap of a set that holds fever
    stat gems and the primary's element gems, with no loadout to find first: most sets hold no Perfect Points or Combo gems.
    A line with no stat has no such move: _UNKNOWN_GAP, about what a dev line's gap comes to."""
    stats = np.empty(7, dtype=np.int64)
    trial = np.empty(7, dtype=np.int64)
    held = np.zeros(gems.shape[0], dtype=np.int64)
    held[2 : PRIMARY + 1] = 1
    points = tables[3]
    for r in range(lines.shape[0]):
        row = lines[r]
        gaps[r] = _UNKNOWN_GAP
        if row[7] >= 0:
            stats[0], stats[1], stats[2], stats[3], stats[4] = row[7], row[1], row[2], row[3], row[4]
            stats[5], stats[6] = 0, row[5] - int(points[row[7]])
            gaps[r] = _gem_gap(stats, gems, held, PRIMARY, trial, tables)


def time_gem_losses(space: LoadoutSpace, prices: np.ndarray) -> np.ndarray:
    """Per price vector, what a gem that buys Perfect Time gives up against the gem worth most: PerfectTime+ (+1 with +1
    Chill, -1 Perfect Points) and PerfectTime++ (+2 with +3 Chill, -2 Combo Multiplier), EquipmentUpgradesSet1.lua:355-417."""
    time_gems = np.zeros((2, _ROW))
    time_gems[0, 0], time_gems[1, 1] = -1.0, -2.0
    for column, color in ((PRIMARY, space.primary), (SECONDARY, space.secondary)):
        if color == "Chill":
            time_gems[:, column] = (1.0, 3.0)

    def worth(rows: np.ndarray) -> np.ndarray:
        return prices @ rows[:, : len(PRICED)].T + 2.0 * rows[:, PRIMARY] + rows[:, SECONDARY]

    return np.maximum(worth(space.gems.astype(np.float64)).max(axis=1), 0.0) - worth(time_gems).max(axis=1)


def prices_at_gems(space: LoadoutSpace) -> np.ndarray:
    """The prices a stat cannot pass while a gem buys it: what the best element gem gives up for one point of it."""
    element = 2 * space.gems[len(PRICED):, PRIMARY] + space.gems[len(PRICED):, SECONDARY]
    best = float(element.max())
    prices = np.zeros(5)
    for d in range(5):
        prices[d] = max(0.0, (best - float(2 * space.gems[d, PRIMARY] + space.gems[d, SECONDARY])) / float(space.gems[d, d]))
    return prices
