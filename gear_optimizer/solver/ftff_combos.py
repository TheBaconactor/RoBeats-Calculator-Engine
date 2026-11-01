"""
Shared FT/FF gem-pair enumeration.

The GA's GPU-resident FT/FF combo table and the CPU gem search (FG and Base) enumerate
the splits in this one triangular order.
"""

from __future__ import annotations

from functools import lru_cache
from typing import NamedTuple

import numpy as np

from gear_optimizer.core.jit_setup import jit
from gear_optimizer.rules import MAX_STAT


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
    ascending indices into the combo table of total_budget (ftff_combo_arrays)."""

    start: np.ndarray
    count: np.ndarray
    combos: np.ndarray
    total_budget: int


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


def ftff_shortlist(
    payload,
    *,
    reach: np.ndarray,
    total_budget: int,
    gem_scale_fever: int,
    element_gains: tuple[int, int, int],
) -> FtffShortlist:
    """Per reachable pre-gem (FT, FF) key (reach: reachable_ftff_keys), the combos of the total_budget combo table that
    can hold the key's Base winner; an unreachable key keeps none.

    A combo spends `a` FT and `b` FF gems (never past MAX_STAT, as the GA's gem search) and reaches a cell; each of the
    cell's timing surfaces is an option with residual gems r = budget - a - b and value v = gain_ft a + gain_ff b +
    gain_element r (the Perfect base, 2 x primary + secondary, if every residual gem went to the element). An option is
    beaten by one on a surface containing its fever notes (head fever bits a superset, body fever >=) with r >= and
    v >=: that option copies any PP/CM/FM gems and puts the rest in the element, and fever only multiplies, so it
    scores at least as much, strictly more unless the two are identical. Of identical options only the highest combo
    index is kept (the GA's tie-break). A combo stays when one of its options does.

    element_gains: (per FT gem, per FF gem, per element gem) change of the Perfect base.
    """
    combo_ft, combo_ff, _ = ftff_combo_arrays(total_budget)
    combo_index = np.full((total_budget + 1, total_budget + 1), -1, dtype=np.int64)
    combo_index[combo_ft, combo_ff] = np.arange(len(combo_ft))
    used = int(payload.frontier_pool_used)
    rows = np.concatenate(
        [np.asarray(payload.grid_frontier_masks_bits_pool[0, :used, :4], dtype=np.int64),
         np.asarray(payload.grid_frontier_body_fever_pool[0, :used], dtype=np.int64)[:, None]],
        axis=1,
    )
    surfaces, surface_of_row = np.unique(rows, axis=0, return_inverse=True)
    surface_of_row = surface_of_row.reshape(-1)
    offsets = np.asarray(payload.grid_frontier_offset[0], dtype=np.int64).ravel()
    counts = np.asarray(payload.grid_frontier_count[0], dtype=np.int64).ravel()
    cell_surfaces = [np.unique(surface_of_row[o : o + n]) for o, n in zip(offsets.tolist(), counts.tolist())]
    cell_count = np.asarray([len(s) for s in cell_surfaces], dtype=np.int64)
    cell_start = np.concatenate([[0], np.cumsum(cell_count)[:-1]]).astype(np.int64)
    side = MAX_STAT + 1
    keep_bits = np.zeros((side * side, (len(combo_ft) + 63) // 64), dtype=np.uint64)
    _shortlist_keep(
        np.ascontiguousarray(reach.ravel()), combo_index, int(total_budget), int(gem_scale_fever),
        np.stack([cell_start, cell_count], axis=1), np.concatenate(cell_surfaces), np.ascontiguousarray(surfaces),
        np.asarray(element_gains, dtype=np.int64), keep_bits,
    )
    start, count, combos = _decode_keep(keep_bits, len(combo_ft))
    return FtffShortlist(start, count, combos, int(total_budget))


@jit(nopython=True, cache=True, nogil=True)
def _decode_keep(keep_bits, n_combos):
    """(start, count, combos) of the set bits of keep_bits, row by row, ascending combo index."""
    n_keys = keep_bits.shape[0]
    count = np.zeros(n_keys, dtype=np.int32)
    for key in range(n_keys):
        for w in range(keep_bits.shape[1]):
            x = keep_bits[key, w]
            while x:
                x &= x - np.uint64(1)
                count[key] += 1
    start = np.zeros(n_keys, dtype=np.int32)
    for key in range(1, n_keys):
        start[key] = start[key - 1] + count[key - 1]
    combos = np.empty(start[-1] + count[-1], dtype=np.int32)
    for key in range(n_keys):
        pos = start[key]
        for c in range(n_combos):
            if (keep_bits[key, c >> 6] >> np.uint64(c & 63)) & np.uint64(1):
                combos[pos] = c
                pos += 1
    return start, count, combos


@jit(nopython=True, cache=True, nogil=True)
def _shortlist_keep(reach, combo_index, budget, gem_scale, cell_ranges, cell_surfaces, surfaces, gains, keep_bits):
    """Set keep_bits[key, c] (bit c % 64 of word c // 64) for every reachable key's kept combos.

    Which option beats which does not depend on the key: from key (ft0, ff0) an option at cell (x, y) has r = budget -
    (x - ft0 + y - ff0) / gem_scale (higher for a lower x + y), v = const + ((gain_ft - gain_element) x + (gain_ff -
    gain_element) y) / gem_scale, and its combo index grows with (x, y). So per residue class (x, y mod gem_scale) each
    option's beaters are found once. A beater at (xp, yp) is reachable exactly from the keys with ft0 <= xp and
    ff0 <= yp (it has r >= the option's, so it fits the budget wherever the option does): the option is kept for the
    keys it fits (ft0 <= x, ff0 <= y within the budget) outside the quadrants below its beaters' corners
    (min(xp, x), min(yp, y)), a staircase. O(options^2 / gem_scale^2) beater checks and O(kept) emission, against
    O(keys x options per key x log) for scoring every key apart.

    combo_index: (a, b) -> index in the combo table; cell_ranges: (cells, 2) start and count into cell_surfaces;
    surfaces: (n, 5) four head fever words and the body fever count; gains: the Perfect base per FT, FF and element
    gem."""
    side = MAX_STAT + 1
    masks, body = surfaces[:, :4], surfaces[:, 4]
    wx, wy = gains[0] - gains[2], gains[1] - gains[2]
    for i in range(gem_scale):
        for j in range(gem_scale):
            # Options of the class in lattice units: cell (i + gem_scale X, j + gem_scale Y).
            nx, ny = (MAX_STAT - i) // gem_scale + 1, (MAX_STAT - j) // gem_scale + 1
            n = 0
            for X in range(nx):
                for Y in range(ny):
                    n += cell_ranges[(i + gem_scale * X) * side + j + gem_scale * Y, 1]
            ox = np.empty(n, dtype=np.int64)
            oy = np.empty(n, dtype=np.int64)
            osf = np.empty(n, dtype=np.int64)
            n = 0
            for X in range(nx):
                for Y in range(ny):
                    cell = (i + gem_scale * X) * side + j + gem_scale * Y
                    for q in range(cell_ranges[cell, 0], cell_ranges[cell, 0] + cell_ranges[cell, 1]):
                        ox[n], oy[n], osf[n] = X, Y, cell_surfaces[q]
                        n += 1
            # stair[X]: the highest beaten Y of keys in column X (before the running maximum), -1 none.
            stair = np.empty(nx, dtype=np.int64)
            for o in range(n):
                xo, yo, so = ox[o], oy[o], osf[o]
                w_o = wx * xo + wy * yo
                stair[: xo + 1] = -1
                dead = False
                for p in range(n):
                    xp, yp, sp = ox[p], oy[p], osf[p]
                    w_p = wx * xp + wy * yp
                    if xp + yp > xo + yo or w_p < w_o:
                        continue
                    if sp == so:
                        # Same surface: an equal (r, v) beats only from a higher combo index.
                        if xp + yp == xo + yo and w_p == w_o and (xp < xo or (xp == xo and yp <= yo)):
                            continue
                    elif body[sp] < body[so] or ((masks[so, 0] & ~masks[sp, 0]) | (masks[so, 1] & ~masks[sp, 1])
                                                 | (masks[so, 2] & ~masks[sp, 2]) | (masks[so, 3] & ~masks[sp, 3])) != 0:
                        continue
                    cx, cy = min(xp, xo), min(yp, yo)
                    if cx == xo and cy == yo:  # a beater on the option's own cell: beaten from every key
                        dead = True
                        break
                    stair[cx] = max(stair[cx], cy)
                if dead:
                    continue
                beaten_up_to = -1
                for X in range(xo, max(xo - budget, 0) - 1, -1):
                    beaten_up_to = max(beaten_up_to, stair[X])
                    a = xo - X
                    for Y in range(yo, max(beaten_up_to + 1, yo - (budget - a), 0) - 1, -1):
                        key = (i + gem_scale * X) * side + j + gem_scale * Y
                        if reach[key]:
                            c = combo_index[a, yo - Y]
                            keep_bits[key, c >> 6] |= np.uint64(1) << np.uint64(c & 63)


__all__ = ["FtffShortlist", "ftff_combo_arrays", "ftff_shortlist", "reachable_ftff_keys"]
