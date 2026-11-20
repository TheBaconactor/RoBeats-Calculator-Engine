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
from numba.cpython.unsafe.numbers import leading_zeros, trailing_zeros
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
        nxt = np.zeros((side, side), dtype=bool)
        for d_ft, d_ff in set(map(tuple, item_stats[start : start + count, 3:5].tolist())):
            if d_ft == 0 and d_ff == 0:
                nxt |= reach
            elif d_ft < 0 or d_ff < 0:
                ft, ff = np.nonzero(reach)
                nxt[np.minimum(ft + d_ft, MAX_STAT), np.minimum(ff + d_ff, MAX_STAT)] = True
            else:
                dx, dy = min(d_ft, MAX_STAT), min(d_ff, MAX_STAT)
                x_lim, y_lim = MAX_STAT - dx, MAX_STAT - dy
                if x_lim > 0 and y_lim > 0:
                    nxt[dx:MAX_STAT, dy:MAX_STAT] |= reach[:x_lim, :y_lim]
                if y_lim > 0:
                    nxt[MAX_STAT, dy:MAX_STAT] |= reach[x_lim:, :y_lim].any(axis=0)
                if x_lim > 0:
                    nxt[dx:MAX_STAT, MAX_STAT] |= reach[:x_lim, y_lim:].any(axis=1)
                nxt[MAX_STAT, MAX_STAT] |= reach[x_lim:, y_lim:].any()
        reach = nxt
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
    total_keys = (MAX_STAT + 1) ** 2
    reach_flat = np.asarray(reach, dtype=np.bool_).ravel()
    used = int(payload.frontier_pool_used)
    if not used or not bool(reach_flat.any()):
        start = np.zeros(total_keys, dtype=np.int32)
        count = np.zeros(total_keys, dtype=np.int32)
        combos = np.empty(0, dtype=np.int32)
        for values in (start, count, combos):
            values.setflags(write=False)
        return FtffShortlist(start, count, combos)
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
    frontier = (np.asarray(payload.grid_frontier_offset[0], dtype=np.int64).ravel(),
                np.asarray(payload.grid_frontier_count[0], dtype=np.int64).ravel(), surface_of_row)
    surfaces = rows[order[is_first]]
    min_y, active_yo = _shortlist_min_y(frontier, surfaces, weights)
    start, count, combos = _emit_shortlist(reach_flat, min_y, active_yo)
    for values in (start, count, combos):
        values.setflags(write=False)
    return FtffShortlist(start, count, combos)


@jit(nopython=True, cache=True, nogil=True)
def _popcount64(x):
    x = x - ((x >> np.uint64(1)) & np.uint64(0x5555555555555555))
    x = (x & np.uint64(0x3333333333333333)) + ((x >> np.uint64(2)) & np.uint64(0x3333333333333333))
    x = (x + (x >> np.uint64(4))) & np.uint64(0x0F0F0F0F0F0F0F0F)
    return np.int32((x * np.uint64(0x0101010101010101)) >> np.uint64(56))


@jit(nopython=True, cache=True, nogil=True)
def _shortlist_min_y(frontier, surfaces, weights):
    """Per (x_key, j = y % g, a = xo - X, yo = y // g), the smallest lattice row Y still unbeaten by any option on a
    beating surface (or higher combo on the same surface); `lattice` means no Y survives.

    Which option beats which does not depend on the key: with g = STAT_GEM_GAIN_FEVER, from key (ft0, ff0) an option at
    cell (x, y) has r = GEM_BUDGET - (x - ft0 + y - ff0) / g, v = const + (wx x + wy y) / g (weights wx, wy: an FT and
    an FF gem's Perfect base against an element gem's, negative), and its combo index grows with (x, y). Per residue
    class (i, j = x, y mod g), in lattice units (i + g X, j + g Y), an option's beaters lie in a wedge capped at
    yo + rise[X' - xo + lattice - 1] in column X'.

    Distinct surfaces ordered by descending (body, popcount(masks)) form a topological order of surface dominance:
    every beater of r has index < r. Walking r - 1 down to 0 while skipping ancestors already covered by an immediate
    dominator builds beaters[r] via Hasse edges only (O(E_hasse x side x g) bitwise ORs instead of O(S^2 + beater
    options)). Every surviving option marks a suffix Y in [y_min, yo] with fixed (x_key, j, a, yo), so multiple options
    collapse into a single scalar minimum `min_y` in O(1) without touching a key-by-combo bitset."""
    offsets, counts, surface_of_row = frontier
    masks, body = surfaces[:, :4], surfaces[:, 4]
    wx, wy = weights
    g = STAT_GEM_GAIN_FEVER
    side, lattice = MAX_STAT + 1, MAX_STAT // g + 1
    n_surfaces = surfaces.shape[0]

    # Topological order: descending (body, popcount(masks)); every surface beating r has strictly smaller rank.
    order_key = np.empty(n_surfaces, dtype=np.int64)
    for s in range(n_surfaces):
        pc = (
            _popcount64(np.uint64(masks[s, 0]))
            + _popcount64(np.uint64(masks[s, 1]))
            + _popcount64(np.uint64(masks[s, 2]))
            + _popcount64(np.uint64(masks[s, 3]))
        )
        order_key[s] = -(body[s] * 128 + np.int64(pc))
    topo = np.argsort(order_key, kind="mergesort")
    rank_of = np.empty(n_surfaces, dtype=np.int64)
    t_m0 = np.empty(n_surfaces, dtype=np.uint64)
    t_m1 = np.empty(n_surfaces, dtype=np.uint64)
    t_m2 = np.empty(n_surfaces, dtype=np.uint64)
    t_m3 = np.empty(n_surfaces, dtype=np.uint64)
    for r in range(n_surfaces):
        s = topo[r]
        rank_of[s] = r
        t_m0[r], t_m1[r] = np.uint64(masks[s, 0]), np.uint64(masks[s, 1])
        t_m2[r], t_m3[r] = np.uint64(masks[s, 2]), np.uint64(masks[s, 3])

    option_start = np.zeros(n_surfaces + 1, dtype=np.int64)
    for cell in range(side * side):
        for row in range(offsets[cell], offsets[cell] + counts[cell]):
            option_start[rank_of[surface_of_row[row]] + 1] += 1
    option_start = np.cumsum(option_start)
    next_option = option_start[:-1].copy()
    option_cell = np.empty(option_start[-1], dtype=np.int32)
    for cell in range(side * side):
        for row in range(offsets[cell], offsets[cell] + counts[cell]):
            r = rank_of[surface_of_row[row]]
            o = next_option[r]
            next_option[r] = o + 1
            option_cell[o] = np.int32(cell)

    rise = np.empty(2 * lattice - 1, dtype=np.int64)
    for k in range(2 * lattice - 1):
        rise[k] = min(lattice - 1 - k, (wx * (k - lattice + 1)) // -wy)
    low_bits = np.full(2 * lattice + 1, ~np.uint64(0), dtype=np.uint64)
    for k in range(min(2 * lattice + 1, 64)):
        low_bits[k] = (np.uint64(1) << np.uint64(k)) - np.uint64(1)

    n_words = side * g
    ancestors = np.zeros((n_surfaces, (n_surfaces + 63) >> 6), dtype=np.uint64)
    reach_all = np.zeros((n_surfaces, n_words), dtype=np.uint64)
    beaters = np.empty(n_words, dtype=np.uint64)
    own_r = np.empty(n_words, dtype=np.uint64)
    min_y = np.full((side, g, lattice, lattice), np.int8(lattice), dtype=np.int8)
    active_yo = np.zeros((side, g, lattice), dtype=np.uint64)

    for r in range(n_surfaces):
        beaters[:] = 0
        m0, m1, m2, m3 = t_m0[r], t_m1[r], t_m2[r], t_m3[r]
        anc_r = ancestors[r]
        for other in range(r - 1, -1, -1):
            if (anc_r[other >> 6] >> np.uint64(other & 63)) & np.uint64(1):
                continue
            if ((m0 & ~t_m0[other]) | (m1 & ~t_m1[other])
                    | (m2 & ~t_m2[other]) | (m3 & ~t_m3[other])) == np.uint64(0):
                anc_r[other >> 6] |= np.uint64(1) << np.uint64(other & 63)
                anc_o = ancestors[other]
                for w in range((other >> 6) + 1):
                    anc_r[w] |= anc_o[w]
                ro = reach_all[other]
                for w in range(n_words):
                    beaters[w] |= ro[w]

        own_r[:] = 0
        for o in range(option_start[r], option_start[r + 1]):
            cell = int(option_cell[o])
            x, y = cell // side, cell % side
            own_r[x * g + y % g] |= np.uint64(1) << np.uint64(y // g)
        rr = reach_all[r]
        for w in range(n_words):
            rr[w] = own_r[w] | beaters[w]

        for o in range(option_start[r], option_start[r + 1]):
            cell = int(option_cell[o])
            x, y = cell // side, cell % side
            i, j, xo, yo = x % g, y % g, x // g, y // g
            beaten_up_to = -1
            for X in range(min((MAX_STAT - i) // g, xo + min(yo, (yo * wy) // wx)), -1, -1):
                top = yo + rise[X - xo + lattice - 1]
                x_key = i + g * X
                word = x_key * g + j
                own_top = top - (X == xo or (X < xo and wx == wy))
                found = (beaters[word] & low_bits[top + 1]) | (own_r[word] & low_bits[own_top + 1])
                if found:
                    beaten_up_to = max(beaten_up_to, min(63 - np.int64(leading_zeros(found)), yo))
                    if beaten_up_to == yo:
                        break
                if X <= xo:
                    a = xo - X
                    y_min = max(beaten_up_to + 1, yo - (GEM_BUDGET - a), 0)
                    if y_min <= yo and y_min < int(min_y[x_key, j, a, yo]):
                        min_y[x_key, j, a, yo] = np.int8(y_min)
                        active_yo[x_key, j, a] |= np.uint64(1) << np.uint64(yo)
    return min_y, active_yo


@jit(nopython=True, cache=True, nogil=True)
def _emit_shortlist(reach_flat, min_y, active_yo):
    """Count kept combos via O(1) prefix-difference updates per active (x_key, j, a, yo), then write ascending combo
    indices directly into `combos` without an intermediate key-by-combo bitset."""
    g = STAT_GEM_GAIN_FEVER
    side, lattice = MAX_STAT + 1, MAX_STAT // g + 1
    total_keys = side * side
    combo_row_start = np.empty(lattice, dtype=np.int32)
    acc = np.int32(0)
    for a in range(min(lattice, GEM_BUDGET + 1)):
        combo_row_start[a] = acc
        acc += np.int32(GEM_BUDGET + 1 - a)

    count = np.zeros(total_keys, dtype=np.int32)
    diff = np.empty(lattice + 1, dtype=np.int32)
    kept = 0
    for x_key in range(side):
        max_a = min((MAX_STAT - x_key) // g, GEM_BUDGET)
        row_base = x_key * side
        for j in range(g):
            max_y = (MAX_STAT - j) // g
            any_reach = False
            for Y in range(max_y + 1):
                if reach_flat[row_base + j + g * Y]:
                    any_reach = True
                    break
            if not any_reach:
                continue
            for Y in range(max_y + 2):
                diff[Y] = 0
            for a in range(max_a + 1):
                mask = active_yo[x_key, j, a]
                while mask:
                    yo = np.int64(trailing_zeros(mask))
                    mask &= mask - np.uint64(1)
                    diff[int(min_y[x_key, j, a, yo])] += 1
                    diff[yo + 1] -= 1
            running = np.int32(0)
            for Y in range(max_y + 1):
                running += diff[Y]
                key = row_base + j + g * Y
                if reach_flat[key]:
                    count[key] = running
                    kept += int(running)

    start = np.empty(total_keys, dtype=np.int32)
    pos = np.int32(0)
    for k in range(total_keys):
        start[k] = pos
        pos += count[k]

    combos = np.empty(kept, dtype=np.int32)
    cursor = np.empty(lattice, dtype=np.int32)
    for x_key in range(side):
        max_a = min((MAX_STAT - x_key) // g, GEM_BUDGET)
        row_base = x_key * side
        for j in range(g):
            max_y = (MAX_STAT - j) // g
            any_reach = False
            for Y in range(max_y + 1):
                key = row_base + j + g * Y
                if reach_flat[key] and count[key] > 0:
                    cursor[Y] = start[key]
                    any_reach = True
                else:
                    cursor[Y] = -1
            if not any_reach:
                continue
            for a in range(max_a + 1):
                mask = active_yo[x_key, j, a]
                if not mask:
                    continue
                base_c = combo_row_start[a]
                while mask:
                    yo = np.int64(trailing_zeros(mask))
                    mask &= mask - np.uint64(1)
                    for Y in range(int(min_y[x_key, j, a, yo]), yo + 1):
                        p = cursor[Y]
                        if p >= 0:
                            combos[p] = base_c + (yo - Y)
                            cursor[Y] = p + 1
    return start, count, combos


__all__ = ["FtffShortlist", "ftff_combo_arrays", "ftff_shortlist", "reachable_ftff_keys"]
