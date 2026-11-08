"""A partly upgraded set for a stat line no max-level set reaches: the best guess at what a player wears.

One row leaves many partly upgraded sets on a line and nothing public tells them apart. The search tries minis and gear in the
order a player gets along (the song's best minis by color at the highest ranks, then its best gear by color; a last pass from the
weakest up, a starting player's), and every choice of them settles the rest: Combo and Fever stats from ++ gems (a deficit the
gem's gain divides), Perfect Points from ascension and then ++ gems, elements from mini levels and element gems on one of the
song's colors, all within the 90 gems. Of the first _FITS exact fits it keeps the one furthest along: mini ranks and levels over
their caps, gems over the budget. Gems are the ++ kinds the Gear Calculator places; a mini's rank, level and ascension follow
PetUtils (gamedata.worn_mini_stats).

Cost: O(T (B + G R g)) for T mini triples at their ranks, B the bit set of their level sums (3 x 50 shifts of ~50 words), G gear
combinations of the shortlist, R TeamBuff rows and g element gem counts; _FITS fits or the work budget end a pass.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from gear_optimizer.core.jit_setup import jit
from gear_optimizer.data.game_export import Catalog
from gear_optimizer.gamedata import MINI_FIRST_CAP, MINI_LEVEL_STEP, MINI_RANKS, ascension_element_bonus, mini_level_cap
from gear_optimizer.rules import GEM_BUDGET

from .loadouts import GEAR_SLOTS, PRIMARY, SECONDARY, LoadoutSpace

_LEVELS = mini_level_cap(MINI_RANKS)
_ASCENSIONS = 11
_ASCENSION_POINTS = 2
_SUM_WORDS = 48  # level sums of three minis' elements fit 3,072 points
# Shortlists (minis, gear items per slot, from the weakest up), widest last, and the exact fits a pass weighs.
_WIDTHS = ((8, 3, 0), (16, 6, 0), (16, 6, 1))
_FITS = 16
# A guess as a row of ints: 6 gear rows (-1 a slot left empty), 3 mini rows, their ranks, levels and ascensions, the 5 stat gem
# counts (Perfect Points, CM, FM, FT, FF), the element gem count, its gem row and the TeamBuff row.
_MINIS, _RANKS, _LEVEL, _ASCENSION, _GEMS = 6, 9, 12, 15, 18
_ELEMENT_GEMS, _ELEMENT_ROW, _FIXED = 23, 24, 25
_WIDTH = 26
GEAR, MINIS, RANKS, LEVELS, ASCENSIONS = slice(0, _MINIS), slice(_MINIS, _RANKS), slice(_RANKS, _LEVEL), slice(_LEVEL, _ASCENSION), slice(_ASCENSION, _GEMS)
GEMS, ELEMENT_GEMS, ELEMENT_ROW, FIXED = slice(_GEMS, _ELEMENT_GEMS), _ELEMENT_GEMS, _ELEMENT_ROW, _FIXED


@dataclass(frozen=True, slots=True, eq=False)
class PartialSpace:
    """A song's items as the guess reads them. gear: rows (Perfect Points, CM, FM, FT, FF, primary, secondary), per slot
    gear_starts, best color first; per mini (best color first): its max Combo and Fever stats, its 2 x primary + secondary at
    each level 1..50 (column 0 unused), and at each ascension its elemental bonus as a song target; TeamBuff rows; the gems."""

    gear: np.ndarray
    gear_starts: np.ndarray
    names: tuple[str, ...]
    mini_names: tuple[str, ...]
    mini_perf: np.ndarray
    mini_elements: np.ndarray
    mini_ascension: np.ndarray
    fixed: np.ndarray
    gems: np.ndarray


def partial_space(catalog: Catalog, space: LoadoutSpace, fixed_rows: np.ndarray, song_name: str) -> PartialSpace:
    gear_end = int(space.starts[len(GEAR_SLOTS)])
    mini_names = space.names[gear_end:]
    primary, secondary = space.primary, space.secondary

    def scored(p: int, s: int) -> int:  # what the base value counts: 2 x primary + secondary, 3 x a one-color song's
        return 3 * p if primary == secondary else 2 * p + s

    perf = np.zeros((len(mini_names), 4), dtype=np.int64)
    elements = np.zeros((len(mini_names), _LEVELS + 1), dtype=np.int64)
    ascension = np.zeros((len(mini_names), _ASCENSIONS), dtype=np.int64)
    for m, name in enumerate(mini_names):
        mini = catalog.minis[name]
        perf[m] = [mini.stats[stat] for stat in ("Combo Multiplier", "Fever Multiplier", "Fever Time", "Fever Fill Rate")]
        first, second = mini.level1_elements.get(primary, 0), mini.level1_elements.get(secondary, 0)
        for level in range(1, _LEVELS + 1):
            line = 1.0 + (level - 1) * 4.0 / 49.0
            elements[m, level] = scored(int(np.floor(first * line)), int(np.floor(second * line)))
        if song_name in mini.song_targets:
            for a in range(_ASCENSIONS):
                bonus = ascension_element_bonus(mini, primary, secondary, a)
                ascension[m, a] = scored(bonus.get(primary, 0), bonus.get(secondary, 0))
    return PartialSpace(space.items[:gear_end], space.starts[: len(GEAR_SLOTS) + 1], space.names, mini_names, perf, elements, ascension, fixed_rows, space.gems)


@jit(nopython=True, cache=True)
def _level_sums(elements, minis, caps, scratch, out):
    """Into out, as a bit set, every sum of the three minis' element values at levels 1..their caps. scratch: two rows of out's
    size."""
    shifted, merged = scratch
    out[:] = 0
    out[0] = 1
    for k in range(3):
        merged[:] = 0
        for level in range(1, caps[k] + 1):
            value = elements[minis[k], level]
            whole, part = value >> 6, value & 63
            shifted[:] = 0
            for w in range(out.shape[0] - whole):
                bits = out[w]
                if bits != 0:
                    shifted[w + whole] |= bits << np.uint64(part)
                    if part and w + whole + 1 < out.shape[0]:
                        shifted[w + whole + 1] |= bits >> np.uint64(64 - part)
            merged |= shifted
        out[:] = merged


@jit(nopython=True, cache=True)
def _holds(bits, value):
    return 0 <= value and (value >> 6) < bits.shape[0] and bool((bits[value >> 6] >> np.uint64(value & 63)) & np.uint64(1))


@jit(nopython=True, cache=True)
def _levels_for(elements, minis, caps, need, out):
    """Levels, highest first, whose element values sum to need, into out; whether there are."""
    for first in range(caps[0], 0, -1):
        for second in range(caps[1], 0, -1):
            rest = need - elements[minis[0], first] - elements[minis[1], second]
            for third in range(caps[2], 0, -1):
                value = elements[minis[2], third]
                if value == rest:
                    out[0], out[1], out[2] = first, second, third
                    return True
                if value < rest:
                    break
    return False


@jit(nopython=True, cache=True)
def _guess(space, target, widths, budget, out):
    """Of the first _FITS exact fits (module docstring) of target (Perfect Points, CM, FM, FT, FF, 2 x primary + secondary), the
    one furthest along into out (the guess row); widths: (minis, gear items per slot, 1 from the weakest up). Returns (whether
    one fits, gear combinations visited); budget bounds the second."""
    gear, gear_starts, mini_perf, mini_elements, mini_ascension, fixed, gems = space
    mini_count, per_slot, weakest = widths
    mini_count = min(mini_count, mini_perf.shape[0])
    gains = np.array([gems[d, d] for d in range(5)])
    gem_value = 2 * gems[:, PRIMARY] + gems[:, SECONDARY]
    bits = np.empty(_SUM_WORDS, dtype=np.uint64)
    shifts = (np.empty(_SUM_WORDS, dtype=np.uint64), np.empty(_SUM_WORDS, dtype=np.uint64))
    minis, ranks, caps, levels = np.empty(3, dtype=np.int64), np.empty(3, dtype=np.int64), np.empty(3, dtype=np.int64), np.empty(3, dtype=np.int64)
    room = np.empty(4, dtype=np.int64)
    chosen = np.empty(6, dtype=np.int64)
    position = np.empty(6, dtype=np.int64)
    sums = np.zeros((7, 6), dtype=np.int64)  # per depth: Perfect Points, CM, FM, FT, FF, elements of the gear so far
    trial = np.zeros_like(out)
    best = -1.0
    work = fits = 0
    for i in range(mini_count):
        for j in range(i + 1, mini_count):
            for k in range(j + 1, mini_count):
                last_mini = mini_perf.shape[0] - 1
                minis[0], minis[1], minis[2] = (last_mini - i, last_mini - j, last_mini - k) if weakest else (i, j, k)
                for code in range(MINI_RANKS**3):
                    ranks[0], ranks[1], ranks[2] = MINI_RANKS - code // 16, MINI_RANKS - (code // 4) % 4, MINI_RANKS - code % 4
                    under = True
                    for d in range(4):
                        room[d] = target[1 + d]
                        for m in range(3):
                            room[d] -= mini_perf[minis[m], d] // MINI_RANKS * ranks[m]
                        under = under and room[d] >= 0
                    if not under:
                        continue
                    for m in range(3):
                        caps[m] = MINI_FIRST_CAP + MINI_LEVEL_STEP * (ranks[m] - 1)  # gamedata.mini_level_cap
                    _level_sums(mini_elements, minis, caps, shifts, bits)
                    # The gear, slot by slot, best color first, within what the minis leave; a slot's last choice is empty.
                    depth = 0
                    position[0] = 0
                    while depth >= 0:
                        if depth == 6:
                            work += 1
                            if work > budget:
                                return best >= 0.0, work
                            progress = _settled(target, sums[6], room, (gains, gem_value), fixed, mini_ascension, (minis, ranks, caps, levels, bits, mini_elements), trial)
                            if progress >= 0.0:
                                fits += 1
                                if progress > best:
                                    best = progress
                                    out[:] = trial
                                    out[:_MINIS] = chosen
                                    out[_MINIS:_RANKS] = minis
                                    out[_RANKS:_LEVEL] = ranks
                                if fits >= _FITS:
                                    return True, work
                            depth -= 1
                            continue
                        step = position[depth]
                        last = min(per_slot, gear_starts[depth + 1] - gear_starts[depth])
                        if step > last:
                            depth -= 1
                            continue
                        position[depth] = step + 1
                        at = -1 if step == last else (gear_starts[depth + 1] - 1 - step if weakest else gear_starts[depth] + step)
                        over = False
                        sums[depth + 1] = sums[depth]
                        if at >= 0:
                            for d in range(5):
                                sums[depth + 1, d] += gear[at, d]
                                over = over or (d > 0 and sums[depth + 1, d] > room[d - 1])
                            sums[depth + 1, 5] += 2 * gear[at, PRIMARY] + gear[at, SECONDARY]
                        if over:
                            continue
                        chosen[depth] = at
                        depth += 1
                        if depth < 6:
                            position[depth] = 0
    return best >= 0.0, work


@jit(nopython=True, cache=True)
def _settled(target, worn, room, gems_of, fixed, mini_ascension, minis_of, out):
    """Gems, ascension, levels and TeamBuff for a choice of gear and minis: of those that fit, the one furthest along into out's
    _LEVEL.. columns, and its progress, -1 when none fits. worn: the gear's sums (Perfect Points, CM, FM, FT, FF, elements); room:
    what the gear and gems may add to CM, FM, FT, FF past the minis; gems_of: (each stat gem's gain, each gem row's 2 x primary
    + secondary)."""
    gains, gem_value = gems_of
    minis, ranks, caps, levels, bits, mini_elements = minis_of
    best = -1.0
    stat_gems = 0
    elements = worn[5]
    for d in range(4):
        deficit = room[d] - worn[1 + d]
        if deficit % gains[1 + d]:
            return best
        out[_GEMS + 1 + d] = deficit // gains[1 + d]
        stat_gems += out[_GEMS + 1 + d]
        elements += out[_GEMS + 1 + d] * gem_value[1 + d]
    if stat_gems > GEM_BUDGET:
        return best
    for f in range(fixed.shape[0]):
        points = target[0] - fixed[f, 0] - worn[0]
        if points < 0 or points % _ASCENSION_POINTS:
            continue
        ascended = min(points // _ASCENSION_POINTS, 3 * (_ASCENSIONS - 1))
        rest = points - ascended * _ASCENSION_POINTS
        point_gems = rest // gains[0]
        if point_gems * gains[0] != rest or stat_gems + point_gems > GEM_BUDGET:
            continue
        top = _ASCENSIONS - 1
        ascensions = (min(top, ascended), min(top, max(0, ascended - top)), max(0, ascended - 2 * top))
        given = elements + 2 * fixed[f, PRIMARY] + fixed[f, SECONDARY] + point_gems * gem_value[0]
        for m in range(3):
            given += mini_ascension[minis[m], ascensions[m]]
        # Element gems on a color the song does not score would add nothing: slots left empty do the same.
        for count in range(GEM_BUDGET - stat_gems - point_gems, -1, -1):
            for row in range(5, gem_value.shape[0]):
                if gem_value[row] == 0 or (count == 0 and row > 5):
                    continue
                need = target[5] - given - count * gem_value[row]
                if _holds(bits, need) and _levels_for(mini_elements, minis, caps, need, levels):
                    progress = (stat_gems + point_gems + count) / GEM_BUDGET
                    for m in range(3):
                        progress += levels[m] / caps[m] + ranks[m] / MINI_RANKS
                    if progress > best:
                        best = progress
                        out[_LEVEL:_ASCENSION] = levels
                        out[_ASCENSION], out[_ASCENSION + 1], out[_ASCENSION + 2] = ascensions
                        out[_GEMS], out[_ELEMENT_GEMS], out[_ELEMENT_ROW], out[_FIXED] = point_gems, count, row, f
    return best


def guess_set(space: PartialSpace, target: np.ndarray, budget: int) -> tuple[np.ndarray | None, int]:
    """The guess for target (Perfect Points, CM, FM, FT, FF, 2 x primary + secondary) as a row (GEAR, MINIS, ... FIXED), the
    shortlists widening while none fits, None when none does; and the gear combinations visited, within `budget` (~1 us each)."""
    arrays = (space.gear, space.gear_starts, space.mini_perf, space.mini_elements, space.mini_ascension, space.fixed, space.gems)
    out = np.zeros(_WIDTH, dtype=np.int64)
    used = 0
    for widths in _WIDTHS:
        found, work = _guess(arrays, target.astype(np.int64), np.asarray(widths, dtype=np.int64), budget - used, out)
        used += work
        if found:
            return out, used
    return None, used
