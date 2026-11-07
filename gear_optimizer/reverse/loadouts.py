"""The released loadouts of one song as a search space: the upper bound of what they reach, and the loadouts themselves.

A target is a final (CM, FM, FT, FF) and base value. Pricing those four stats and Perfect Points relaxes the loadout's
choices apart: each slot takes its item worth most at the prices and every gem the gem worth most, so the sum, less the
target at the same prices, bounds the base value of every loadout that reaches the target (a Lagrangian dual). At its
lowest the bound sits a few points over the true best (stored rows: 2,148 vs 2,144 and 1,935.6 vs 1,935), so an item
stays only if what it gives up against its slot's best fits the bound's slack.

Cost: O(I) per bound for I = 368 items (~1.6 us), 200 bounds per target; the walk then takes the items the slack leaves,
near the top of a song a few per slot.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from gear_optimizer.core.jit_setup import jit
from gear_optimizer.core.team_buff import TEAM_BUFF_TIER_EFFECTS
from gear_optimizer.data.game_export import Catalog
from gear_optimizer.gamedata import ELEMENTS, Gear, song_minis
from gear_optimizer.rules import (
    ELEMENT_GEM_GAIN,
    GEM_BUDGET,
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
_ITEMS_EQUIPPED = len(GEAR_SLOTS) + 3
# What a selected element gem adds: to the primary, to the secondary, to neither.
_ELEMENT_ROWS = 3
_GEM_ROWS = len(STAT_GEMS) + _ELEMENT_ROWS


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
    for _ in range(steps):
        value = _price_bound(items, starts, gems, points, target, current, used)
        if value < best:
            best = value
            best_prices[:] = current
        norm = np.sqrt(np.sum(used * used))
        if norm < 1.0e-9:
            break
        current -= step * used / norm
        step *= 0.985
    prices[:] = best_prices
    return best


@jit(nopython=True, cache=True)
def _leaf_gems(total, target, gems, points, bases, counts):
    """Into counts the gems (PP, CM, FM, FT, FF, element, element row) that take a pre-gem total to the target and a base
    value in bases (lowest, highest, Gear Power or negative); counts[0] = -1 when none do. target: CM, FM, FT, FF in places
    1..4."""
    bought = 0
    primary, secondary = total[5], total[6]
    for d in range(1, 5):
        gap = target[d] - total[d]
        gain = gems[d, d]
        if gap < 0 or gap % gain != 0:
            counts[0] = -1
            return
        counts[d] = gap // gain
        bought += counts[d]
        primary += counts[d] * gems[d, 5]
        secondary += counts[d] * gems[d, 6]
    if bought > GEM_BUDGET:
        counts[0] = -1
        return
    left = GEM_BUDGET - bought
    fever_stats = target[1] + target[2] + target[3] + target[4]
    for pp_gems in range(left + 1):
        stat = min(total[0] + pp_gems * gems[0, 0], points.shape[0] - 1)
        colors = 2 * (primary + pp_gems * gems[0, 5]) + secondary + pp_gems * gems[0, 6]
        element = left - pp_gems
        for row in range(5, 8):
            value = colors + element * (2 * gems[row, 5] + gems[row, 6])
            if bases[0] <= value + int(points[stat]) <= bases[1] and (bases[2] < 0 or 5 * (stat + fever_stats) + 2 * value == bases[2]):
                counts[0], counts[5], counts[6] = pp_gems, element, row
                return
    counts[0] = -1


@jit(nopython=True, cache=True)
def walk_loadouts(items, starts, gems, points, query, found, budget):
    """The loadouts that reach a target, into found (rows: 9 item indices, 7 gem values from _leaf_gems), cheapest first;
    returns (found rows, items tried), budget + 1 tried when it stopped early. query: (target row, base values (lowest,
    highest, Gear Power or negative), bound slack at prices, prices, fixed row).

    A loadout gives up what each of its items falls short of its slot's best at the prices, and the bound's slack is all
    it may give up, so a slot walks only the items inside the slack, and a walk stops at the first that does not fit
    what the items before it left (a slot's items are in that order). Minis are distinct and in value order, so the
    third mini measures from the third best."""
    target, bases, slack, prices, fixed = query
    n = items.shape[0]
    values = np.empty(n)
    for i in range(n):
        values[i] = _row_value(items[i], prices)
    order = np.empty(n, dtype=np.int64)
    lost = np.empty(n)
    for slot in range(starts.shape[0] - 1):
        first, stop = starts[slot], starts[slot + 1]
        ranked = np.argsort(-values[first:stop])
        order[first:stop] = first + ranked
        lost[first:stop] = values[first + ranked[0]] - values[first + ranked]
    mini_first, mini_stop = starts[6], starts[7]
    nodes = 0
    positions = np.zeros(_ITEMS_EQUIPPED + 1, dtype=np.int64)
    spent = np.zeros(_ITEMS_EQUIPPED + 1)
    partial = np.zeros((_ITEMS_EQUIPPED + 1, 7), dtype=np.int64)
    partial[0] = fixed
    positions[0] = starts[0]
    counts = np.zeros(7, dtype=np.int64)
    depth = 0
    written = 0
    while True:
        if depth == _ITEMS_EQUIPPED:
            _leaf_gems(partial[depth], target, gems, points, bases, counts)
            if counts[0] >= 0:
                if written >= found.shape[0]:
                    return written, budget + 1
                for d in range(_ITEMS_EQUIPPED):
                    found[written, d] = order[positions[d] - 1]
                found[written, _ITEMS_EQUIPPED:] = counts
                written += 1
            depth -= 1
            continue
        stop = starts[depth + 1] if depth < 6 else mini_stop
        i = positions[depth]
        if i >= stop:
            if depth == 0:
                return written, nodes
            depth -= 1
            continue
        positions[depth] = i + 1
        nodes += 1
        if nodes > budget:
            return written, nodes
        shortfall = lost[i]
        if depth >= 6:
            # The mini at this depth stands against the (depth - 6)-th best mini.
            shortfall = values[order[mini_first + depth - 6]] - values[order[i]]
        if spent[depth] + shortfall > slack + 1.0e-6:
            positions[depth] = stop
            continue
        spent[depth + 1] = spent[depth] + max(shortfall, 0.0)
        partial[depth + 1] = partial[depth] + items[order[i]]
        depth += 1
        if depth < 6:
            positions[depth] = starts[depth]
        elif depth == 6:
            positions[depth] = mini_first
        elif depth < _ITEMS_EQUIPPED:
            positions[depth] = i + 1


def prices_at_gems(space: LoadoutSpace) -> np.ndarray:
    """The prices a stat cannot pass while a gem buys it: what the best element gem gives up for one point of it."""
    element = 2 * space.gems[len(PRICED):, PRIMARY] + space.gems[len(PRICED):, SECONDARY]
    best = float(element.max())
    prices = np.zeros(5)
    for d in range(5):
        prices[d] = max(0.0, (best - float(2 * space.gems[d, PRIMARY] + space.gems[d, SECONDARY])) / float(space.gems[d, d]))
    return prices
