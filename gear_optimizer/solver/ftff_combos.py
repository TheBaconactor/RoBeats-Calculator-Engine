"""
Shared FT/FF gem-pair enumeration.

The GA's GPU-resident FT/FF combo table and the CPU gem search (FG and Base) enumerate
the splits in this one triangular order.
"""

from __future__ import annotations

from functools import lru_cache
from typing import NamedTuple

import numpy as np

from numba.cpython.unsafe.numbers import leading_zeros, trailing_zeros

from gear_optimizer.core.jit_setup import jit
from gear_optimizer.rules import ELEMENT_GEM_GAIN, GEM_BUDGET, MAX_STAT, STAT_GEM_ELEMENT_GAIN, STAT_GEM_GAIN_FEVER


@lru_cache(maxsize=8)
def ftff_combo_arrays(total_budget: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Return FT, FF, and remaining-budget arrays in combo-table order (read-only).

    Order:
      ft=0,ff=0..B ; ft=1,ff=0..B-1 ; ... ; ft=B,ff=0
    """
    tri_i, tri_j = np.triu_indices(total_budget + 1)
    ft = tri_i.astype(np.int32)
    ff = (tri_j - tri_i).astype(np.int32)
    budget_left = (total_budget - ft - ff).astype(np.int32)
    for values in (ft, ff, budget_left):
        values.setflags(write=False)
    return ft, ff, budget_left


class FtffShortlist(NamedTuple):
    """ftff_shortlist's result: key ft * (MAX_STAT + 1) + ff owns combos[start[key] : start[key] + count[key]],
    ascending indices into the combo table of GEM_BUDGET (ftff_combo_arrays)."""

    start: np.ndarray
    count: np.ndarray
    combos: np.ndarray


def reachable_ftff_keys(item_stats, slot_start, slot_count, base_fixed_stats_arr) -> np.ndarray:
    """(MAX_STAT + 1, MAX_STAT + 1) bool: the pre-gem (FT, FF) keys, each stat capped at MAX_STAT, of the loadouts that
    take one item per slot (the sum over slots of each slot's (FT, FF) values)."""
    side = MAX_STAT + 1
    reach = np.zeros((side, side), dtype=bool)
    reach[min(int(base_fixed_stats_arr[3]), MAX_STAT), min(int(base_fixed_stats_arr[4]), MAX_STAT)] = True
    for start, count in zip(slot_start, slot_count):
        ft, ff = np.nonzero(reach)
        reach = np.zeros((side, side), dtype=bool)
        for d_ft, d_ff in set(map(tuple, item_stats[start : start + count, 3:5].tolist())):
            reach[np.minimum(ft + d_ft, MAX_STAT), np.minimum(ff + d_ff, MAX_STAT)] = True
    return reach


def ftff_shortlist(payload, *, reach: np.ndarray, color_flags: dict[str, int]) -> FtffShortlist:
    """Per reachable pre-gem (FT, FF) key (reach: reachable_ftff_keys), the combos of the GEM_BUDGET combo table that
    can hold the key's Base winner in the song's timing frontier payload; an unreachable key keeps none.

    A combo spends `a` FT and `b` FF gems (never past MAX_STAT, as the GA's gem search) and reaches a cell; each of the
    cell's timing surfaces is an option with residual gems r = GEM_BUDGET - a - b and value v = gain_ft a + gain_ff b +
    gain_element r (the Perfect base, 2 x primary + secondary, if every residual gem went to the element). An option is
    beaten by one on a surface containing its fever notes (head fever bits a superset, body fever >=) with r >= and
    v >=: that option copies any PP/CM/FM gems and puts the rest in the element, and fever only multiplies, so it
    scores at least as much, strictly more unless the two are identical. Of identical options only the highest combo
    index is kept (the GA's tie-break). A combo stays when one of its options does.

    color_flags: build_color_flags, the song's primary element selected.
    """
    combo_ft, combo_ff, _ = ftff_combo_arrays(GEM_BUDGET)
    combo_index = np.full((GEM_BUDGET + 1, GEM_BUDGET + 1), -1, dtype=np.int64)
    combo_index[combo_ft, combo_ff] = np.arange(len(combo_ft))
    used = int(payload.frontier_pool_used)
    rows = np.concatenate(
        [np.asarray(payload.grid_frontier_masks_bits_pool[0, :used, :4], dtype=np.int64),
         np.asarray(payload.grid_frontier_body_fever_pool[0, :used], dtype=np.int64)[:, None]],
        axis=1,
    )
    order = np.lexsort(rows.T)
    is_first = np.ones(used, dtype=bool)
    is_first[1:] = (rows[order[1:]] != rows[order[:-1]]).any(axis=1)
    surface_of_row = np.empty(used, dtype=np.int64)
    surface_of_row[order] = np.cumsum(is_first) - 1
    gain_element = ELEMENT_GEM_GAIN * (2 * color_flags["is_p_ov"] + color_flags["is_s_ov"])
    weights = (STAT_GEM_ELEMENT_GAIN * (2 * color_flags["is_p_ft"] + color_flags["is_s_ft"]) - gain_element,
               STAT_GEM_ELEMENT_GAIN * (2 * color_flags["is_p_ff"] + color_flags["is_s_ff"]) - gain_element)
    keep_bits = np.zeros(((MAX_STAT + 1) ** 2, (len(combo_ft) + 63) // 64), dtype=np.uint64)
    frontier = (np.asarray(payload.grid_frontier_offset[0], dtype=np.int64).ravel(),
                np.asarray(payload.grid_frontier_count[0], dtype=np.int64).ravel(), surface_of_row)
    surfaces = rows[order[is_first]]
    _shortlist_keep(np.ascontiguousarray(reach.ravel()), combo_index, frontier, surfaces, weights, keep_bits)
    count = np.bitwise_count(keep_bits).sum(axis=1, dtype=np.int32)
    return FtffShortlist(np.cumsum(count, dtype=np.int32) - count, count, _decode_keep(keep_bits, int(count.sum())))


@jit(nopython=True, cache=True, nogil=True)
def _decode_keep(keep_bits, kept):
    """The `kept` set bits of keep_bits, row by row, ascending combo index."""
    combos = np.empty(kept, dtype=np.int32)
    pos = 0
    for key in range(keep_bits.shape[0]):
        for w in range(keep_bits.shape[1]):
            x = keep_bits[key, w]
            while x:
                combos[pos] = w * 64 + trailing_zeros(x)
                pos += 1
                x &= x - np.uint64(1)
    return combos


@jit(nopython=True, cache=True, nogil=True)
def _shortlist_keep(reach, combo_index, frontier, surfaces, weights, keep_bits):
    """Set keep_bits[key, c] (bit c % 64 of word c // 64) for every reachable key's kept combos.

    Which option beats which does not depend on the key: with g = STAT_GEM_GAIN_FEVER, from key (ft0, ff0) an option at
    cell (x, y) has r = GEM_BUDGET - (x - ft0 + y - ff0) / g, v = const + (wx x + wy y) / g (weights wx, wy: an FT and
    an FF gem's Perfect base against an element gem's, negative: 12 or 18 for the element, at most 9 for a stat gem),
    and its combo index grows with (x, y). So per residue class (x, y mod g), in lattice units (cell (i + g X, j + g
    Y)), an option's beaters are the cells of a wedge: X' + Y' <= X + Y and wx X' + wy Y' >= wx X + wy Y, which is at
    most rise[X' - X + lattice - 1] above Y in column X'. A beater at (xp, yp) is reachable exactly from the keys with
    ft0 <= xp and ff0 <= yp (it has r >= the option's, so it fits the budget wherever the option does): the option is
    kept for the keys it fits (ft0 <= x, ff0 <= y within the budget) outside the quadrants below its beaters' corners
    (min(xp, x), min(yp, y)), a staircase that only each column's highest beater shapes.

    So per surface: one word per lattice column (at most 64 cells high; the classes side by side) marks the options of
    the surfaces beating it, and another its own options, which beat it too except an equal (r, v) from a lower combo
    index. Each option reads them right to left, emitting a column's unbeaten keys as it goes. O(S^2) surface pairs,
    O(options x columns) reads and O(kept) emission, against O(options^2 / (2 g^2)) option pairs. Surfaces mostly beat
    from above an option's diagonal, so each list stops at the surface's own highest diagonal.

    frontier: per cell its first row and row count, then each row's surface; surfaces: (S, 5) four head fever words
    and the body fever count."""
    offsets, counts, surface_of_row = frontier
    masks, body = surfaces[:, :4], surfaces[:, 4]
    wx, wy = weights
    g = STAT_GEM_GAIN_FEVER
    side, lattice = MAX_STAT + 1, MAX_STAT // g + 1
    n_surfaces = surfaces.shape[0]
    # Each surface's options by diagonal x + y, with their word and bit in the columns.
    option_start = np.zeros(n_surfaces + 1, dtype=np.int64)
    for cell in range(side * side):
        for row in range(offsets[cell], offsets[cell] + counts[cell]):
            option_start[surface_of_row[row] + 1] += 1
    option_start = np.cumsum(option_start)
    next_option = option_start[:-1].copy()
    option_cell = np.empty(option_start[-1], dtype=np.int64)
    option_word = np.empty(option_start[-1], dtype=np.int64)
    option_bit = np.empty(option_start[-1], dtype=np.uint64)
    option_diagonal = np.empty(option_start[-1], dtype=np.int64)
    for diagonal in range(2 * side - 1):
        for x in range(max(0, diagonal - side + 1), min(side, diagonal + 1)):
            y = diagonal - x
            cell = x * side + y
            for row in range(offsets[cell], offsets[cell] + counts[cell]):
                o = next_option[surface_of_row[row]]
                next_option[surface_of_row[row]] += 1
                option_cell[o], option_word[o], option_diagonal[o] = cell, x * g + y % g, diagonal
                option_bit[o] = np.uint64(1) << np.uint64(y // g)
    rise = np.empty(2 * lattice - 1, dtype=np.int64)
    for k in range(2 * lattice - 1):
        rise[k] = min(lattice - 1 - k, (wx * (k - lattice + 1)) // -wy)
    low_bits = np.full(2 * lattice + 1, ~np.uint64(0), dtype=np.uint64)  # low_bits[k]: the k lowest bits of a word
    for k in range(min(2 * lattice + 1, 64)):
        low_bits[k] = (np.uint64(1) << np.uint64(k)) - np.uint64(1)
    beaters = np.empty(side * g, dtype=np.uint64)
    own = np.empty(side * g, dtype=np.uint64)
    for s in range(n_surfaces):
        beaters[:] = 0
        own[:] = 0
        highest_diagonal = option_diagonal[option_start[s + 1] - 1]
        for other in range(n_surfaces):
            if (other != s and body[other] >= body[s]
                    and ((masks[s, 0] & ~masks[other, 0]) | (masks[s, 1] & ~masks[other, 1])
                         | (masks[s, 2] & ~masks[other, 2]) | (masks[s, 3] & ~masks[other, 3])) == 0):
                for o in range(option_start[other], option_start[other + 1]):
                    if option_diagonal[o] > highest_diagonal:
                        break
                    beaters[option_word[o]] |= option_bit[o]
        for o in range(option_start[s], option_start[s + 1]):
            own[option_word[o]] |= option_bit[o]
        for o in range(option_start[s], option_start[s + 1]):
            x, y = option_cell[o] // side, option_cell[o] % side
            i, j, xo, yo = x % g, y % g, x // g, y // g
            beaten_up_to = -1
            for X in range(min((MAX_STAT - i) // g, xo + min(yo, (yo * wy) // wx)), -1, -1):
                top = yo + rise[X - xo + lattice - 1]
                word = (i + g * X) * g + j
                # An equal (r, v) on the option's surface beats only from a higher combo index: its own cell and, with
                # equal weights, the diagonal to its left stay out.
                own_top = top - (X == xo or (X < xo and wx == wy))
                found = (beaters[word] & low_bits[top + 1]) | (own[word] & low_bits[own_top + 1])
                if found:
                    beaten_up_to = max(beaten_up_to, min(63 - int(leading_zeros(found)), yo))
                    if beaten_up_to == yo:
                        break
                if X <= xo:
                    a = xo - X
                    for Y in range(yo, max(beaten_up_to + 1, yo - (GEM_BUDGET - a), 0) - 1, -1):
                        key = (i + g * X) * side + j + g * Y
                        if reach[key]:
                            c = combo_index[a, yo - Y]
                            keep_bits[key, c >> 6] |= np.uint64(1) << np.uint64(c & 63)


__all__ = ["FtffShortlist", "ftff_combo_arrays", "ftff_shortlist", "reachable_ftff_keys"]
