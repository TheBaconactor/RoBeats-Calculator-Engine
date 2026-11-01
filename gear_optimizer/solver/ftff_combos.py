"""
Shared FT/FF gem-pair enumeration.

The GA's GPU-resident FT/FF combo table and the CPU gem search (FG and Base) enumerate
the splits in this one triangular order.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import NamedTuple

import numpy as np

from numba import prange

from gear_optimizer.core.jit_setup import jit
from gear_optimizer.rules import MAX_STAT


logger = logging.getLogger(__name__)


def _normalize_budget(total_budget: int) -> int:
    budget = int(total_budget)
    return max(0, budget)


def _normalize_cap(value: int | None, total_budget: int) -> int:
    if value is None:
        return int(total_budget)
    try:
        cap = int(value)
    except Exception as e:
        logger.debug(f"ftff_combos:_normalize_cap: {e}")
        cap = int(total_budget)
    return max(0, min(int(total_budget), int(cap)))


@lru_cache(maxsize=64)
def _ftff_combo_arrays_cached(total_budget: int, cap_ft: int, cap_ff: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    dim = int(total_budget) + 1
    tri_i, tri_j = np.triu_indices(dim)
    ft = tri_i.astype(np.int32, copy=False)
    ff = (tri_j - tri_i).astype(np.int32, copy=False)
    if int(cap_ft) < int(total_budget) or int(cap_ff) < int(total_budget):
        valid = (ft <= int(cap_ft)) & (ff <= int(cap_ff))
        ft = np.ascontiguousarray(ft[valid], dtype=np.int32)
        ff = np.ascontiguousarray(ff[valid], dtype=np.int32)
    else:
        ft = np.ascontiguousarray(ft, dtype=np.int32)
        ff = np.ascontiguousarray(ff, dtype=np.int32)
    budget_left = (int(total_budget) - ft - ff).astype(np.int32, copy=False)
    ft.setflags(write=False)
    ff.setflags(write=False)
    budget_left.setflags(write=False)
    return ft, ff, budget_left


def ftff_combo_arrays(
    total_budget: int,
    *,
    max_ft_gems: int | None = None,
    max_ff_gems: int | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Return FT, FF, and remaining-budget arrays in combo-table order.

    Order:
      ft=0,ff=0..B ; ft=1,ff=0..B-1 ; ... ; ft=B,ff=0
    """

    budget = _normalize_budget(total_budget)
    cap_ft = _normalize_cap(max_ft_gems, budget)
    cap_ff = _normalize_cap(max_ff_gems, budget)
    return _ftff_combo_arrays_cached(int(budget), int(cap_ft), int(cap_ff))


class FtffShortlist(NamedTuple):
    """ftff_shortlist's result: key ft * (MAX_STAT + 1) + ff owns combos[start[key] : start[key] + count[key]],
    ascending indices into the combo table of (total_budget, max_ft_gems, max_ff_gems)."""

    start: np.ndarray
    count: np.ndarray
    combos: np.ndarray
    total_budget: int
    max_ft_gems: int
    max_ff_gems: int


def ftff_shortlist(
    payload,
    *,
    total_budget: int,
    max_ft_gems: int,
    max_ff_gems: int,
    gem_scale_fever: int,
    element_gains: tuple[int, int, int],
) -> FtffShortlist:
    """Per pre-gem (FT, FF) key, the combos of the (total_budget, max_ft_gems, max_ff_gems) combo table that can hold
    the key's Base winner.

    A combo spends `a` FT and `b` FF gems (never past MAX_STAT, as the GA's gem search) and reaches a cell; each of the
    cell's timing surfaces is an option with residual gems r = budget - a - b and value v = gain_ft a + gain_ff b +
    gain_element r (the Perfect base, 2 x primary + secondary, if every residual gem went to the element). An option is
    beaten by one on a surface containing its fever notes (head fever bits a superset, body fever >=) with r >= and
    v >=: that option copies any PP/CM/FM gems and puts the rest in the element, and fever only multiplies, so it
    scores at least as much, strictly more unless the two are identical. Of identical options only the highest combo
    index is kept (the GA's tie-break). A combo stays when one of its options does.

    element_gains: (per FT gem, per FF gem, per element gem) change of the Perfect base.
    """
    combo_ft, combo_ff, _ = ftff_combo_arrays(total_budget, max_ft_gems=max_ft_gems, max_ff_gems=max_ff_gems)
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
        np.stack([combo_ft, combo_ff]).astype(np.int64), int(total_budget), int(gem_scale_fever),
        np.stack([cell_start, cell_count], axis=1), np.concatenate(cell_surfaces), np.ascontiguousarray(surfaces),
        np.asarray(element_gains, dtype=np.int64), keep_bits,
    )
    start, count, combos = _decode_keep(keep_bits, len(combo_ft))
    return FtffShortlist(start, count, combos, int(total_budget), int(max_ft_gems), int(max_ff_gems))


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


@jit(nopython=True, cache=True, nogil=True, parallel=True)
def _shortlist_keep(combos, budget, gem_scale, cell_ranges, cell_surfaces, surfaces, gains, keep_bits):
    """Set keep_bits[key, c] (bit c % 64 of word c // 64) for every key's kept combos (keys in parallel).
    combos: (2, n) FT and FF gems; cell_ranges: (cells, 2) start and count into cell_surfaces; surfaces: (n, 5) four
    head fever words and the body fever count; gains: the Perfect base per FT, FF and element gem."""
    side = MAX_STAT + 1
    combo_ft, combo_ff = combos[0], combos[1]
    cell_start, cell_count = cell_ranges[:, 0], cell_ranges[:, 1]
    masks, body_fever = surfaces[:, :4], surfaces[:, 4]
    gain_ft, gain_ff, gain_element = gains[0], gains[1], gains[2]
    n_combos = combo_ft.shape[0]
    max_per_cell = cell_count.max()
    for key in prange(side * side):
        ft0 = key // side
        ff0 = key % side
        max_a = min((MAX_STAT - ft0) // gem_scale, budget)
        max_b = min((MAX_STAT - ff0) // gem_scale, budget)
        cap = n_combos * max_per_cell
        opt_s = np.empty(cap, dtype=np.int64)
        opt_r = np.empty(cap, dtype=np.int64)
        opt_v = np.empty(cap, dtype=np.int64)
        opt_c = np.empty(cap, dtype=np.int64)
        m = 0
        for c in range(n_combos):
            a = combo_ft[c]
            b = combo_ff[c]
            if a > max_a or b > max_b:
                continue
            cell = (ft0 + gem_scale * a) * side + ff0 + gem_scale * b
            r = budget - a - b
            v = gain_ft * a + gain_ff * b + gain_element * r
            for q in range(cell_start[cell], cell_start[cell] + cell_count[cell]):
                opt_s[m] = cell_surfaces[q]
                opt_r[m] = r
                opt_v[m] = v
                opt_c[m] = c
                m += 1
        # Surface ascending, then r, v and the combo index descending: per surface, an option survives only when its v
        # beats every option with r >= its own (identical options: the first, i.e. highest combo index, survives).
        order = np.argsort((opt_s[:m] << 40) | ((127 - opt_r[:m]) << 32) | ((4095 - opt_v[:m]) << 13)
                           | (8191 - opt_c[:m]))
        surv = np.empty(m, dtype=np.int64)
        n_surv = 0
        i = 0
        while i < m:
            s = opt_s[order[i]]
            best_v = -1
            while i < m and opt_s[order[i]] == s:
                o = order[i]
                if opt_v[o] > best_v:
                    best_v = opt_v[o]
                    surv[n_surv] = o
                    n_surv += 1
                i += 1
        for x in range(n_surv):
            o = surv[x]
            s = opt_s[o]
            beaten = False
            for y in range(n_surv):
                p = surv[y]
                t = opt_s[p]
                if t == s or opt_r[p] < opt_r[o] or opt_v[p] < opt_v[o] or body_fever[t] < body_fever[s]:
                    continue
                if ((masks[s, 0] & ~masks[t, 0]) | (masks[s, 1] & ~masks[t, 1]) | (masks[s, 2] & ~masks[t, 2])
                        | (masks[s, 3] & ~masks[t, 3])) == 0:
                    beaten = True
                    break
            if not beaten:
                c = opt_c[o]
                keep_bits[key, c >> 6] |= np.uint64(1) << np.uint64(c & 63)


__all__ = ["FtffShortlist", "ftff_combo_arrays", "ftff_shortlist"]
