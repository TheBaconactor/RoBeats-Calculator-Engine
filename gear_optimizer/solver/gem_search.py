"""The exact gem search: for each loadout, the best gem allocation over the surfaces of the frontiers it reaches, in
CPU f64 numba (FG response surfaces; the Base timing surfaces are the same without Greats).

Each song's (FT, FF) frontier grid (161 x 161) is summarized once in GemMemo as per-cell frontier shapes and their 2D
prefix maxima. Each loadout searches its reachable (FT, FF) gem splits directly on that grid via two-level 2D tiles
(_GRID_COARSE x _GRID_COARSE -> _GRID_FINE x _GRID_FINE), sharing (CM, FM) bound tables across loadouts with equal
(PP, CM, FM) (or (CM, FM) off Chill) and computing term_max rows and block tables lazily only where needed.

Per surviving cell, (CM, FM) gem pairs are visited in _TILE_CM x _TILE_FM blocks: the score bound is monotone in CM and
FM gems and base is linear in them, so a block's corner bounds every pair in it. A surface misses its frontier's most
by some amount at any block, so one ceiling from the group's peak rejects nearly every surface before its blocks; Great
notes lower the bound by what they lose at the least.

Cost per solve in real sizes (COMPLEXITY.md, sections 3, 16, and 29): O(G_grid) = O(161^2) once per song for the grid
bounds, O(T B_c) for column chords across T distinct stat lines plus lazy term_max rows and lazy block tables only on
surviving stat lines, and O(L * (G_cap / _GRID_COARSE)^2) coarse tile checks across L loadouts plus surviving fine
tiles, cells, surfaces, and exact scores.
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import os
import threading
from typing import Any

import numpy as np

from gear_optimizer.core.jit_setup import jit
from gear_optimizer.frontier.types import SurfacePool
from gear_optimizer.gamedata import StatCurves
from gear_optimizer.rules import (
    ELEMENT_GEM_GAIN,
    GEM_BUDGET,
    MAX_STAT,
    STAT_GEM_ELEMENT_GAIN,
    STAT_GEM_GAIN_FEVER,
    STAT_GEM_GAIN_NORMAL,
)
from gear_optimizer.stats import STAT_GEMS

# (CM, FM) gem pairs per bound block: CM has low curvature (3 keeps column count low), FM is steep (2 sharpens bounds).
_TILE_CM = 3
_TILE_FM = 2
# Two-level 2D tile dimensions over reachable (FT, FF) gem splits on the 161 x 161 frontier grid.
_GRID_COARSE = 9
_GRID_FINE = 3
# Contiguous chunks of loadouts scored on separate threads.
_FG_CPU_SEARCH_WORKERS = max(1, min(4, (os.cpu_count() or 1)))
_FG_CPU_SEARCH_CHUNKS_PER_WORKER = 2
_fg_cpu_search_pool: ThreadPoolExecutor | None = None
_fg_cpu_search_pool_lock = threading.Lock()


@dataclass(slots=True)
class GemMemo:
    """Song-level cache shared across batches of one song and pool: frontier bound shapes and the 161 x 161 2D prefix
    grid (~600 KB per song)."""

    frontier_shapes: np.ndarray | None = None
    grid_bounds: tuple[Any, ...] | None = None
    frontier_idx_ref: np.ndarray | None = None
    pool_ref: SurfacePool | None = None
    body_total: int = -1


@dataclass(frozen=True, slots=True)
class GemWinner:
    """A loadout's gem-search winner: its FT/FF gems and stat keys, the row (best score, surface index in its frontier,
    PP/CM/FM/element gems) and the winning surface (11 ints)."""

    ft: int
    ff: int
    ft_stat: int
    ff_stat: int
    inner_row: tuple[int, ...]
    surface: tuple[int, ...]


def color_flags(primary_color: str, secondary_color: str, selected_color: str) -> tuple[int, ...]:
    """Which gem elements raise the song's colors: (PP->primary, PP->secondary, CM->p, CM->s, FM->p, FM->s,
    element->p, element->s, single color)."""
    gem_flags = []
    for stat in ("Perfect Points", "Combo Multiplier", "Fever Multiplier"):
        element = STAT_GEMS[stat][1]
        gem_flags += [int(primary_color == element), int(secondary_color == element)]
    return (
        *gem_flags,
        int(bool(selected_color) and primary_color == selected_color),
        int(bool(selected_color) and secondary_color == selected_color),
        int(primary_color == secondary_color),
    )


@jit(inline="always")
def _stat_row(stat):
    if stat < 0:
        return 0
    if stat > MAX_STAT:
        return MAX_STAT
    return stat


@jit(nopython=True, cache=True)
def _surface_score(words, surface, notes, primary_val, secondary_val, pp_factor, multipliers, single_color):
    """Exact score of one surface at a gem-allocated stat line: the game's per-note values with their per-term floor
    order. A Great note scores the lower of its Perfect and Great value."""
    body_fever, body_great, body_fever_great = surface
    head_len, body_total = notes
    combo_mul, combo_ramp, fever_mul = multipliers
    base_value = float((primary_val * 2) + secondary_val) + pp_factor
    combo_val = int(np.floor(base_value * combo_mul))
    fever_val = int(np.floor(base_value * combo_mul * fever_mul))
    score = body_fever * fever_val + (body_total - body_fever) * combo_val

    great_or = int(words[4]) | int(words[5]) | int(words[6]) | int(words[7])
    great_base = 0.0
    if body_great > 0 or great_or != 0:
        great_base = float(
            primary_val * 2 + 150 if single_color else
            int(np.floor(float(primary_val) * (4.0 / 3.0))) + int(np.floor(float(secondary_val) * (2.0 / 3.0))) + 150
        )
        if body_great > 0:
            score -= (body_great - body_fever_great) * max(0, combo_val - int(np.floor(great_base * combo_mul)))
            score -= body_fever_great * max(0, fever_val - int(np.floor(great_base * combo_mul * fever_mul)))

    if great_or == 0:
        for i in range(head_len):
            scaling = combo_ramp[i]
            if ((int(words[i >> 5]) >> (i & 31)) & 1) != 0:
                score += int(np.floor(base_value * scaling * fever_mul))
            else:
                score += int(np.floor(base_value * scaling))
        return score

    for i in range(head_len):
        wi, b = i >> 5, i & 31
        is_fever = (int(words[wi]) >> b) & 1
        scaling = combo_ramp[i]
        perfect_val = int(np.floor(base_value * scaling * fever_mul)) if is_fever else int(np.floor(base_value * scaling))
        if ((int(words[4 + wi]) >> b) & 1) != 0:
            great_val = int(np.floor(great_base * scaling * fever_mul)) if is_fever else int(np.floor(great_base * scaling))
            perfect_val = min(perfect_val, great_val)
        score += perfect_val
    return score


@jit(inline="always")
def _surface_shape(body_fever, body_normal, n_hn, n_hf, sigma_hn, sigma_hf):
    """The (A, E, F, G) of a surface's upper bound at one stat line, every head note at its Perfect value."""
    ramp_fever, ramp_normal = sigma_hf * 0.01, sigma_hn * 0.01
    return body_fever + ramp_fever, body_normal + ramp_normal, n_hf - ramp_fever, n_hn - ramp_normal


@jit(inline="always")
def _shape_value(shape, combo, fever):
    a, e, f, g = shape
    return combo * (a * fever + e) + f * fever + g


@jit(inline="always")
def _block_bound(block, delta, shape):
    """The surface bound at a block's best corner (base value, combo, fever), with the margin of _budget_bound."""
    return (block[0] + delta) * _shape_value(shape, block[1], block[2]) + 1025.0


@jit(inline="always")
def _surface_ceiling(ceil_params, frontier_shape, shape, great_shape):
    """At least a surface's bound less what its Greats lose at each live block."""
    peak, ceil_ka, ceil_df, low_wc, low_wf, gw_cf = ceil_params
    dx = frontier_shape[0] - shape[0]
    dy = frontier_shape[2] - shape[2]
    great_loss = great_shape[0] * gw_cf + great_shape[1] * low_wc + great_shape[2] * low_wf + great_shape[3]
    return peak - (ceil_ka * dx + ceil_df * dy) - great_loss


@jit(inline="always")
def _budget_bound(c, d_rel, shape):
    """The surface bound over a budget's columns, parameterized in d_rel = delta - delta_lo >= 0."""
    a, e, f, g = shape
    return (
        a * (c[0] + d_rel * c[1]) + e * (c[2] + d_rel * c[3])
        + f * (c[4] + d_rel * c[5]) + g * (c[6] + d_rel * c[7]) + 1025.0
    )


@jit(inline="always")
def _column_bound(combo, column, col_d_rel, shape):
    """The surface bound over a column of blocks of one combo."""
    a, e, f, g = shape
    return (column[1] + col_d_rel * column[2]) * (combo * a + f) + (column[0] + col_d_rel) * (combo * e + g) + 1025.0


@jit(inline="always")
def _dominates(a, b):
    """True iff split (r, val, pg, sg, pos) `a` dominates `b` on the same frontier. Color gains are multiples of 3, so a
    Great's base (4/3 primary + 2/3 secondary floored) rises with Perfect base: a dominated split never wins."""
    r1, v1, pg1, sg1, p1 = a
    r2, v2, pg2, sg2, p2 = b
    return r1 >= r2 and (
        v1 > v2 or (pg1 >= pg2 and sg1 >= sg2 and (r1 > r2 or pg1 > pg2 or sg1 > sg2 or p1 < p2))
    )


@jit(nopython=True, cache=True)
def _fill_gem_curve(out, ref, stat, gain, allowed):
    """Fill out[0..gems] with ref at stat + k * gain for k = 0..gems; returns gems."""
    gems = min(max(0, (MAX_STAT - stat + gain - 1) // gain), GEM_BUDGET) if allowed else 0
    for k in range(gems + 1):
        out[k] = ref[_stat_row(stat + k * gain)]
    return gems


@jit(nopython=True, cache=True)
def _block_bound_tables():
    """Empty bound tables, refilled per stat line."""
    side_cm = (GEM_BUDGET + _TILE_CM) // _TILE_CM
    side_fm = (GEM_BUDGET + _TILE_FM) // _TILE_FM
    return (
        np.empty((GEM_BUDGET + 1, 8), dtype=np.float64),
        np.empty(side_cm, dtype=np.float64),
        np.empty(side_cm + 1, dtype=np.int64),
        np.empty((side_cm, side_fm, 3), dtype=np.float64),
        np.empty((side_cm * side_fm, 5), dtype=np.float64),
        np.empty((side_cm * side_fm, 4), dtype=np.int64),
    )


@jit(nopython=True, cache=True)
def _fill_column_terms(column_combo, column_terms, gem_bases, cm_ref_cache, fm_ref_cache, limits, delta_range):
    """Per block column, its combo multiplier and chord bounds over delta_range in d_rel = delta - delta_lo >= 0."""
    w_cm, w_fm, w_ov = gem_bases
    _full_pp, full_cm, full_fm, _allow_pp = limits
    delta_lo, delta_hi = delta_range
    inv_span = 1.0 / (delta_hi - delta_lo)
    cm_lin_up, fm_lin_up = w_cm > w_ov, w_fm > w_ov
    cm_step, fm_step = w_cm - w_ov, w_fm - w_ov
    for j in range(full_cm // _TILE_CM + 1):
        cm0 = j * _TILE_CM
        cm1 = min(cm0 + _TILE_CM - 1, full_cm)
        column_combo[j] = cm_ref_cache[cm1]
        cm_base = (cm1 if cm_lin_up else cm0) * cm_step
        most_base = most_low = most_high = -1.0e30
        for k in range(min(full_fm, GEM_BUDGET - cm0) // _TILE_FM + 1):
            fm0 = k * _TILE_FM
            fm1 = min(fm0 + _TILE_FM - 1, full_fm)
            base = float(cm_base + (fm1 if fm_lin_up else fm0) * fm_step)
            fever = fm_ref_cache[fm1]
            most_base = max(most_base, base)
            most_low = max(most_low, (base + delta_lo) * fever)
            most_high = max(most_high, (base + delta_hi) * fever)
            terms = column_terms[j, k]
            terms[0], terms[1], terms[2] = most_base + delta_lo, most_low, (most_high - most_low) * inv_span


@jit(nopython=True, cache=True)
def _fill_blocks(column_first, blocks, corners, gem_bases, cm_ref_cache, fm_ref_cache, limits):
    """Fill every _TILE_CM x _TILE_FM block's corner table (called lazily only on stat lines with a surviving cell)."""
    w_cm, w_fm, w_ov = gem_bases
    _full_pp, full_cm, full_fm, _allow_pp = limits
    cm_lin_up, fm_lin_up = w_cm > w_ov, w_fm > w_ov
    cm_step, fm_step = w_cm - w_ov, w_fm - w_ov
    b = 0
    for j in range(full_cm // _TILE_CM + 1):
        cm0 = j * _TILE_CM
        cm1 = min(cm0 + _TILE_CM - 1, full_cm)
        column_first[j] = b
        cm_base = (cm1 if cm_lin_up else cm0) * cm_step
        cm_hi, cm_lo = cm_ref_cache[cm1], cm_ref_cache[cm0]
        for k in range(min(full_fm, GEM_BUDGET - cm0) // _TILE_FM + 1):
            fm0 = k * _TILE_FM
            fm1 = min(fm0 + _TILE_FM - 1, full_fm)
            base = float(cm_base + (fm1 if fm_lin_up else fm0) * fm_step)
            block = blocks[b]
            block[0], block[1], block[2], block[3], block[4] = base, cm_hi, fm_ref_cache[fm1], cm_lo, fm_ref_cache[fm0]
            corners[b, 0], corners[b, 1], corners[b, 2], corners[b, 3] = cm0, cm1, fm0, fm1
            b += 1


@jit(inline="always")
def _fill_term_max_row(term_max, r, column_combo, column_terms, pp_bound_prefix_max, pp_0, w_ov, limits):
    """Populate `term_max[r]` over columns reachable with residual budget `r`."""
    full_pp, full_cm, full_fm, allow_pp = limits
    most = term_max[r]
    for j in range(min(full_cm, r) // _TILE_CM + 1):
        cm0 = j * _TILE_CM
        combo = column_combo[j]
        terms = column_terms[j, min(full_fm, r - cm0) // _TILE_FM]
        shift_rel = float(r * w_ov) + (pp_bound_prefix_max[min(full_pp, r - cm0)] - pp_0 if allow_pp else 0.0)
        base, base_fever, slope = terms[0] + shift_rel, terms[1] + shift_rel * terms[2], terms[2]
        if j == 0:
            most[0], most[1], most[2], most[3] = combo * base_fever, combo * slope, combo * base, combo
            most[4], most[5], most[6], most[7] = base_fever, slope, base, 1.0
        else:
            most[0], most[1] = max(most[0], combo * base_fever), max(most[1], combo * slope)
            most[2], most[3] = max(most[2], combo * base), max(most[3], combo)
            most[4], most[5], most[6] = max(most[4], base_fever), max(most[5], slope), max(most[6], base)


@jit(inline="always")
def _ensure_term_max(r, term_ctx):
    """Return `term_max[r]`, computing it lazily on first access for the active stat line."""
    term_max, term_done, column_combo, column_terms, pp_bound_prefix_max, pp_0, w_ov, limits = term_ctx
    if not term_done[r]:
        _fill_term_max_row(term_max, r, column_combo, column_terms, pp_bound_prefix_max, pp_0, w_ov, limits)
        term_done[r] = True
    return term_max[r]


@jit(nopython=True, cache=True)
def _stat_line_deltas(loadouts, c, allow_pp, ref_pp, most_gain, budget_gain, pp_bound_prefix_max, full_pp):
    """The range of delta_for_bounds over contiguous loadouts sharing c's stat line ((PP, CM, FM) if allow_pp else (CM, FM))."""
    base0 = float((int(loadouts[c, 3]) << 1) + int(loadouts[c, 4])) + (
        pp_bound_prefix_max[0] if allow_pp else ref_pp[_stat_row(int(loadouts[c, 0]))]
    )
    lowest = highest = base0
    last = c + 1
    while last < loadouts.shape[0] and (
        loadouts[last, 1] == loadouts[c, 1]
        and loadouts[last, 2] == loadouts[c, 2]
        and (not allow_pp or loadouts[last, 0] == loadouts[c, 0])
    ):
        val = float((int(loadouts[last, 3]) << 1) + int(loadouts[last, 4])) + (
            pp_bound_prefix_max[0] if allow_pp else ref_pp[_stat_row(int(loadouts[last, 0]))]
        )
        lowest, highest = min(lowest, val), max(highest, val)
        last += 1
    pp_extra = (pp_bound_prefix_max[full_pp] - pp_bound_prefix_max[0]) if allow_pp else 0.0
    return lowest, highest + float(most_gain + budget_gain) + pp_extra + 1.0


@jit(nopython=True, cache=True)
def _live_summary(blocks, live_blocks, live_deltas, live, frontier_shape):
    """Over a group's live blocks: the highest frontier bound, the lowest base value, best corner's combo and fever, and
    worst corner's combo and fever."""
    peak = 0.0
    low_base = low_combo = low_fever = low_worst_combo = low_worst_fever = 1.0e30
    for position in range(live):
        block = blocks[live_blocks[position]]
        peak = max(peak, _block_bound(block, live_deltas[position], frontier_shape))
        low_base = min(low_base, block[0] + live_deltas[position])
        low_combo, low_fever = min(low_combo, block[1]), min(low_fever, block[2])
        low_worst_combo, low_worst_fever = min(low_worst_combo, block[3]), min(low_worst_fever, block[4])
    return peak, low_base, low_combo, low_fever, low_worst_combo, low_worst_fever


@jit(nopython=True, cache=True)
def _frontier_shapes(group_frontiers, pool_shapes, body_total, shapes, done):
    """Into shapes, per frontier not done yet, a shape bounding its surfaces' (_surface_shape).
    O(frontiers + the surfaces of those frontiers)."""
    frontier_offsets, frontier_lengths, pattern_ids, counts, head_coeffs = pool_shapes
    for f in group_frontiers:
        if f >= 0 and not done[f]:
            done[f] = True
            most = shapes[f]
            for row in range(frontier_offsets[f], frontier_offsets[f] + frontier_lengths[f]):
                coeffs = head_coeffs[pattern_ids[row]]
                shape = _surface_shape(counts[row, 0], body_total - counts[row, 0], coeffs[0], coeffs[1], coeffs[2], coeffs[3])
                most[0], most[2] = max(most[0], shape[0]), max(most[2], shape[2])
                most[1], most[3] = shape[0] + shape[1], shape[2] + shape[3]
            most[1] -= most[0]
            most[3] -= most[2]


@jit(nopython=True, cache=True)
def _build_grid_bounds(frontier_idx_by_stat, frontier_shapes):
    """Per-cell (A, F) and 2D prefix maxima over the 161 x 161 frontier grid, plus song totals (s_ae, s_fg)."""
    side = MAX_STAT + 1
    pref_a = np.zeros((side, side), dtype=np.float64)
    pref_f = np.zeros((side, side), dtype=np.float64)
    cell_a = np.zeros((side, side), dtype=np.float64)
    cell_f = np.zeros((side, side), dtype=np.float64)
    s_ae = s_fg = 0.0
    for x in range(side):
        for y in range(side):
            f = frontier_idx_by_stat[x, y]
            a = fv = 0.0
            if f >= 0:
                a, e, fv, gv = frontier_shapes[f, 0], frontier_shapes[f, 1], frontier_shapes[f, 2], frontier_shapes[f, 3]
                s_ae, s_fg = max(s_ae, a + e), max(s_fg, fv + gv)
            cell_a[x, y], cell_f[x, y] = a, fv
            pa, pf = a, fv
            if x > 0:
                pa, pf = max(pa, pref_a[x - 1, y]), max(pf, pref_f[x - 1, y])
            if y > 0:
                pa, pf = max(pa, pref_a[x, y - 1]), max(pf, pref_f[x, y - 1])
            pref_a[x, y], pref_f[x, y] = pa, pf
    return pref_a, pref_f, cell_a, cell_f, s_ae, s_fg


@jit(nopython=True, cache=True)
def _first_pos_of_frontier(ft0, ff0, fid, frontier_idx_by_stat, ft_cap, ff_cap, budget):
    """Smallest split index in triangular (ft, ff) order from (ft0, ff0) that reaches `fid`."""
    g = STAT_GEM_GAIN_FEVER
    pos = 0
    for a in range(ft_cap + 1):
        row = frontier_idx_by_stat[_stat_row(ft0 + a * g)]
        for b in range(min(ff_cap, budget - a) + 1):
            if row[_stat_row(ff0 + b * g)] == fid:
                return pos + b
        pos += budget + 1 - a
    return 1 << 30


@jit(nopython=True, cache=True)
def _beats_on_tie(cand, win, origin, frontier_idx_by_stat, caps, gains):
    """True iff candidate (a1, b1, fid1) beats incumbent (a2, b2, fid2) on an exact score tie: first-reached frontier
    wins across distinct frontiers; within one frontier, a dominating or earlier split wins."""
    a1, b1, fid1 = cand
    a2, b2, fid2 = win
    ft0, ff0, budget = origin
    ft_cap, ff_cap = caps
    if fid1 != fid2:
        p1 = _first_pos_of_frontier(ft0, ff0, fid1, frontier_idx_by_stat, ft_cap, ff_cap, budget)
        p2 = _first_pos_of_frontier(ft0, ff0, fid2, frontier_idx_by_stat, ft_cap, ff_cap, budget)
        return p1 < p2
    ft_p, ft_s, ff_p, ff_s, elem_val = gains
    r1, r2 = budget - a1 - b1, budget - a2 - b2
    pg1, sg1 = a1 * ft_p + b1 * ff_p, a1 * ft_s + b1 * ff_s
    pg2, sg2 = a2 * ft_p + b2 * ff_p, a2 * ft_s + b2 * ff_s
    s1 = (r1, (pg1 << 1) + sg1 + elem_val * r1, pg1, sg1, a1 * (2 * budget + 3 - a1) // 2 + b1)
    s2 = (r2, (pg2 << 1) + sg2 + elem_val * r2, pg2, sg2, a2 * (2 * budget + 3 - a2) // 2 + b2)
    if _dominates(s1, s2):
        return True
    if _dominates(s2, s1):
        return False
    return s1[4] < s2[4]


@jit(nopython=True, cache=True)
def _find_seed_cell(origin, caps, base0, delta_lo, grid_info, term_ctx, gain_info):
    """Best-bound (ft_gems, ff_gems) cell in the highest-bound coarse tile, to seed floorless loadouts."""
    ft0, ff0, budget = origin
    ft_cap, ff_cap = caps
    _fid_grid, pref_a, pref_f, cell_a, cell_f, s_ae, s_fg = grid_info
    ft_gain, ff_gain = gain_info
    g = STAT_GEM_GAIN_FEVER

    best_a0 = best_b0 = 0
    best_tub = -1.0
    for a0 in range(0, ft_cap + 1, _GRID_COARSE):
        a1 = min(ft_cap, a0 + _GRID_COARSE - 1)
        x1 = _stat_row(ft0 + g * a1)
        b_lim = min(ff_cap, budget - a0)
        for b0 in range(0, b_lim + 1, _GRID_COARSE):
            b1 = min(b_lim, b0 + _GRID_COARSE - 1)
            y1 = _stat_row(ff0 + g * b1)
            pa, pf = pref_a[x1, y1], pref_f[x1, y1]
            ub = _budget_bound(
                _ensure_term_max(budget - a0 - b0, term_ctx),
                base0 + float(a1 * ft_gain + b1 * ff_gain) - delta_lo,
                (pa, s_ae - pa, pf, s_fg - pf),
            )
            if ub > best_tub:
                best_tub, best_a0, best_b0 = ub, a0, b0

    seed_a = seed_b = -1
    best_ub = -1.0
    for aa in range(best_a0, min(ft_cap, best_a0 + _GRID_COARSE - 1) + 1):
        xx = _stat_row(ft0 + g * aa)
        for bb in range(best_b0, min(min(ff_cap, budget - aa), best_b0 + _GRID_COARSE - 1) + 1):
            yy = _stat_row(ff0 + g * bb)
            ca, cf = cell_a[xx, yy], cell_f[xx, yy]
            ub = _budget_bound(
                _ensure_term_max(budget - aa - bb, term_ctx),
                base0 + float(aa * ft_gain + bb * ff_gain) - delta_lo,
                (ca, s_ae - ca, cf, s_fg - cf),
            )
            if ub > best_ub:
                best_ub, seed_a, seed_b = ub, aa, bb
    return seed_a, seed_b


@jit(inline="always")
def _best_pp_no_greats(p_words, body_fever, notes, base_state, pp_info, multipliers, threshold_state, single_color):
    """On a Great-free surface at fixed (g_cm, g_fm), find the PP gem count maximizing base value and break exact ties
    toward the fewest PP gems."""
    base_linear_common, primary_base, secondary_base, pair_value = base_state
    g_pp_max, delta_pp_vs_ov, pp_primary_delta, pp_secondary_delta, pp_ref_cache = pp_info
    threshold, best_score, g_cm, g_fm, best_cm, best_fm = threshold_state

    best_gp = 0
    best_bv = float(base_linear_common) + pp_ref_cache[0]
    for gp in range(1, g_pp_max + 1):
        bv = float(base_linear_common + gp * delta_pp_vs_ov) + pp_ref_cache[gp]
        if bv > best_bv:
            best_bv, best_gp = bv, gp
    if best_bv * pair_value + 1024.0 < threshold:
        return -1, 0
    score = _surface_score(
        p_words, (body_fever, 0, 0), notes,
        primary_base + best_gp * pp_primary_delta, secondary_base + best_gp * pp_secondary_delta,
        pp_ref_cache[best_gp], multipliers, single_color,
    )
    if score < best_score or (score == best_score and (g_cm, g_fm) > (best_cm, best_fm)):
        return -1, 0
    win_gp = best_gp
    if best_gp > 0:
        score_floor = float(score)
        rec_bv = -1.0e30
        for gp in range(best_gp):
            bv = float(base_linear_common + gp * delta_pp_vs_ov) + pp_ref_cache[gp]
            if bv <= rec_bv:
                continue
            rec_bv = bv
            if bv * pair_value + 1024.0 < score_floor:
                continue
            tie_score = _surface_score(
                p_words, (body_fever, 0, 0), notes,
                primary_base + gp * pp_primary_delta, secondary_base + gp * pp_secondary_delta,
                pp_ref_cache[gp], multipliers, single_color,
            )
            if tie_score == score:
                win_gp = gp
                break
    return score, win_gp


@jit(nopython=True, cache=True)
def _score_group(g_row, cur_stats, caches, tables, surfaces, refs, flags_info, work):
    """Exact gem search over one frontier cell once its budget bound survived."""
    residual_budget, cur_primary, cur_secondary, frontier, candidate_best = g_row
    cur_cm, pp_ref_base, pp_0, delta_lo, full_pp_gems, full_cm_gems, full_fm_gems, allow_pp = cur_stats
    pp_ref_cache, cm_ref_cache, fm_ref_cache, pp_bound_prefix_max = caches
    column_combo, column_first, column_terms, blocks, block_corners = tables
    frontier_offsets, frontier_lengths, frontier_shapes, pattern_ids, pattern_words, surface_counts, head_coeffs, \
        head_greats = surfaces
    ref_ramp, head_len, body_total = refs
    (
        w_cm, w_fm, w_ov, delta_pp_vs_ov, fm_lin_up,
        cm_p_delta, cm_s_delta, fm_p_delta, fm_s_delta, ov_p_delta, ov_s_delta,
        pp_primary_delta, pp_secondary_delta, single_color,
    ) = flags_info
    live_blocks, live_deltas = work

    base_init = (cur_primary << 1) + cur_secondary
    delta_for_bounds = float(base_init) + pp_ref_base
    most = frontier_shapes[frontier]
    frontier_shape = (most[0], most[1], most[2], most[3])
    budget_delta = delta_for_bounds + float(residual_budget * w_ov)
    group_best_score = -1
    group_best_surface = group_best_pp = group_best_cm = group_best_fm = 0
    live = 0
    cand_f = float(candidate_best)
    for j in range(min(full_cm_gems, residual_budget) // _TILE_CM + 1):
        cm0 = j * _TILE_CM
        last_block = min(full_fm_gems, residual_budget - cm0) // _TILE_FM
        column_delta = budget_delta + (
            pp_bound_prefix_max[min(full_pp_gems, residual_budget - cm0)] - pp_0 if allow_pp else 0.0
        )
        if _column_bound(column_combo[j], column_terms[j, last_block], column_delta - delta_lo, frontier_shape) >= cand_f:
            for bi in range(column_first[j], column_first[j] + last_block + 1):
                block_delta = (
                    budget_delta + pp_bound_prefix_max[min(full_pp_gems, residual_budget - cm0 - block_corners[bi, 2])] - pp_0
                    if allow_pp else column_delta
                )
                if _block_bound(blocks[bi], block_delta, frontier_shape) >= cand_f:
                    live_blocks[live], live_deltas[live] = bi, block_delta
                    live += 1
    if live == 0:
        return -1, 0, 0, 0, 0
    # A note's Great base is at most 2/3 of its base without PP + 150, and gems only raise what is left.
    gap = float(base_init) / 3.0 + pp_ref_base - 150.0
    start = frontier_offsets[frontier]
    peak, low_base, low_combo, low_fever, low_wc, low_wf = _live_summary(
        blocks, live_blocks, live_deltas, live, frontier_shape
    )
    ceil_df = low_base * (low_fever - 1.0)
    ceil_params = (peak, ceil_df * low_combo, ceil_df, low_wc, low_wf, low_wc * low_wf)
    notes = (head_len, body_total)
    for ls in range(frontier_lengths[frontier]):
        sr = start + ls
        pattern_row = pattern_ids[sr]
        body_fever, body_great, body_fever_great = int(surface_counts[sr, 0]), int(surface_counts[sr, 1]), int(surface_counts[sr, 2])
        coeffs = head_coeffs[pattern_row]
        shape = _surface_shape(body_fever, body_total - body_fever, coeffs[0], coeffs[1], coeffs[2], coeffs[3])
        great_shape = (
            (
                gap * body_fever_great, gap * (body_great - body_fever_great),
                gap * head_greats[pattern_row, 1], gap * head_greats[pattern_row, 0] - body_great,
            )
            if gap >= 1.0 else (0.0, 0.0, 0.0, 0.0)
        )
        best_score, best_pp, best_cm, best_fm = group_best_score, group_best_pp, group_best_cm, group_best_fm
        threshold = float(max(best_score, candidate_best))
        if _surface_ceiling(ceil_params, frontier_shape, shape, great_shape) < threshold:
            continue
        p_words = pattern_words[pattern_row]
        no_greats = body_great == 0 and head_greats[pattern_row, 0] == 0 and head_greats[pattern_row, 1] == 0
        for position in range(live):
            bi = live_blocks[position]
            block = blocks[bi]
            if _block_bound(block, live_deltas[position], shape) - _shape_value(great_shape, block[3], block[4]) < threshold:
                continue
            cm0, cm1 = block_corners[bi, 0], min(block_corners[bi, 1], residual_budget)
            fm0, fm1 = block_corners[bi, 2], block_corners[bi, 3]
            for g_cm in range(cm0, cm1 + 1):
                leftover_after_cm = residual_budget - g_cm
                cm_mul = cm_ref_cache[g_cm]
                fm_hi = min(fm1, leftover_after_cm)
                alpha, beta = shape[0] * cm_mul + shape[2], shape[1] * cm_mul + shape[3]
                gamma, eta = great_shape[0] * cm_mul + great_shape[2], great_shape[1] * cm_mul + great_shape[3]
                lin_fm = fm_hi if fm_lin_up else fm0
                row_base = float(base_init + g_cm * w_cm + lin_fm * w_fm + (leftover_after_cm - lin_fm) * w_ov)
                row_base += pp_bound_prefix_max[min(full_pp_gems, leftover_after_cm - fm0)] if allow_pp else pp_ref_base
                if row_base * (alpha * fm_ref_cache[fm_hi] + beta) + 1024.0 - (gamma * fm_ref_cache[fm0] + eta) < threshold:
                    continue
                cm_ramp = ref_ramp[_stat_row(cur_cm + g_cm * STAT_GEM_GAIN_NORMAL)]
                for g_fm in range(fm0, fm_hi + 1):
                    leftover_after_fm = leftover_after_cm - g_fm
                    fm_mul = fm_ref_cache[g_fm]
                    g_pp_max = min(full_pp_gems, leftover_after_fm)
                    base_linear_common = base_init + g_cm * w_cm + g_fm * w_fm + leftover_after_fm * w_ov
                    max_base_value = (
                        float(base_linear_common) + pp_bound_prefix_max[g_pp_max]
                        if allow_pp else float(base_linear_common) + pp_ref_base
                    )
                    pair_value, pair_loss = alpha * fm_mul + beta, gamma * fm_mul + eta
                    if max_base_value * pair_value + 1024.0 - pair_loss < threshold:
                        continue
                    primary_base = cur_primary + g_cm * cm_p_delta + g_fm * fm_p_delta + leftover_after_fm * ov_p_delta
                    secondary_base = cur_secondary + g_cm * cm_s_delta + g_fm * fm_s_delta + leftover_after_fm * ov_s_delta
                    if no_greats:
                        score, win_gp = _best_pp_no_greats(
                            p_words, body_fever, notes,
                            (base_linear_common, primary_base, secondary_base, pair_value),
                            (g_pp_max, delta_pp_vs_ov, pp_primary_delta, pp_secondary_delta, pp_ref_cache),
                            (cm_mul, cm_ramp, fm_mul),
                            (threshold, best_score, g_cm, g_fm, best_cm, best_fm),
                            single_color,
                        )
                        if score >= 0 and (
                            score > best_score or (score == best_score and (g_cm, g_fm, win_gp) < (best_cm, best_fm, best_pp))
                        ):
                            best_score, best_pp, best_cm, best_fm = score, win_gp, g_cm, g_fm
                            threshold = float(max(best_score, candidate_best))
                    else:
                        for g_pp in range(g_pp_max + 1):
                            pp_base_value = float(base_linear_common + g_pp * delta_pp_vs_ov) + pp_ref_cache[g_pp]
                            if pp_base_value * pair_value + 1024.0 - pair_loss < threshold:
                                continue
                            score = _surface_score(
                                p_words, (body_fever, body_great, body_fever_great), notes,
                                primary_base + g_pp * pp_primary_delta, secondary_base + g_pp * pp_secondary_delta,
                                pp_ref_cache[g_pp], (cm_mul, cm_ramp, fm_mul), single_color,
                            )
                            if score > best_score or (score == best_score and (g_cm, g_fm, g_pp) < (best_cm, best_fm, best_pp)):
                                best_score, best_pp, best_cm, best_fm = score, g_pp, g_cm, g_fm
                                threshold = float(max(best_score, candidate_best))
        if best_score > group_best_score:
            group_best_score, group_best_surface = best_score, ls
            group_best_pp, group_best_cm, group_best_fm = best_pp, best_cm, best_fm
    return group_best_score, group_best_surface, group_best_pp, group_best_cm, group_best_fm


@jit(nopython=True, cache=True)
def _score_grid_loadouts(loadouts, budgets, floors, grid_info, surfaces, color_flags, curves, song_cfg):
    """Each loadout's best gem allocation over its reachable (FT, FF) splits on the 161 x 161 frontier grid:
    (rows, winning [ft_gems, ff_gems, frontier_id]). Row columns: [best_score, best_surface, g_pp, g_cm, g_fm, g_ov]."""
    frontier_idx_by_stat, pref_a, pref_f, cell_a, cell_f, s_ae, s_fg = grid_info
    head_len, body_total, ft_p, ft_s, ff_p, ff_s = song_cfg
    ref_pp, ref_cm, ref_ramp, ref_fm = curves
    out = np.zeros((loadouts.shape[0], 6), dtype=np.int64)
    out[:, 0] = -1
    win_ftff = np.zeros((loadouts.shape[0], 3), dtype=np.int32)

    pp_p, pp_s = STAT_GEM_ELEMENT_GAIN * int(color_flags[0]), STAT_GEM_ELEMENT_GAIN * int(color_flags[1])
    cm_p, cm_s = STAT_GEM_ELEMENT_GAIN * int(color_flags[2]), STAT_GEM_ELEMENT_GAIN * int(color_flags[3])
    fm_p, fm_s = STAT_GEM_ELEMENT_GAIN * int(color_flags[4]), STAT_GEM_ELEMENT_GAIN * int(color_flags[5])
    ov_p, ov_s = ELEMENT_GEM_GAIN * int(color_flags[6]), ELEMENT_GEM_GAIN * int(color_flags[7])
    single_color = color_flags[8]
    allow_pp = pp_p != 0 or pp_s != 0
    w_pp, w_cm, w_fm, w_ov = (pp_p << 1) + pp_s, (cm_p << 1) + cm_s, (fm_p << 1) + fm_s, (ov_p << 1) + ov_s
    ft_gain, ff_gain = (ft_p << 1) + ft_s, (ff_p << 1) + ff_s
    ft_caps = (ft_gain < w_ov) or (ft_gain == 0)
    ff_caps = (ff_gain < w_ov) or (ff_gain == 0)
    most_gain = GEM_BUDGET * (ft_gain if ft_gain > ff_gain else ff_gain)
    gains_tie = (ft_p, ft_s, ff_p, ff_s, w_ov)
    g = STAT_GEM_GAIN_FEVER

    flags_info = (
        w_cm, w_fm, w_ov, w_pp - w_ov, w_fm > w_ov,
        cm_p, cm_s, fm_p, fm_s, ov_p, ov_s, pp_p - ov_p, pp_s - ov_s, single_color,
    )
    refs = (ref_ramp, head_len, body_total)
    pp_ref_cache = np.empty(GEM_BUDGET + 1, dtype=np.float64)
    cm_ref_cache = np.empty(GEM_BUDGET + 1, dtype=np.float64)
    fm_ref_cache = np.empty(GEM_BUDGET + 1, dtype=np.float64)
    pp_bound_prefix_max = np.empty(GEM_BUDGET + 1, dtype=np.float64)
    caches = (pp_ref_cache, cm_ref_cache, fm_ref_cache, pp_bound_prefix_max)
    term_max, column_combo, column_first, column_terms, blocks, block_corners = _block_bound_tables()
    block_tables = (column_combo, column_first, column_terms, blocks, block_corners)
    term_done = np.zeros(GEM_BUDGET + 1, dtype=np.bool_)
    blocks_ready = False
    work = (np.empty(blocks.shape[0], dtype=np.int64), np.empty(blocks.shape[0], dtype=np.float64))
    full_pp = full_cm = full_fm = 0
    pp_0 = delta_lo = 0.0

    # Track already-scored frontiers per loadout so dominated splits on the same frontier skip _score_group.
    seen_fid = np.empty(64, dtype=np.int32)
    seen_r = np.empty(64, dtype=np.int32)
    seen_val = np.empty(64, dtype=np.int32)
    seen_pg = np.empty(64, dtype=np.int32)
    seen_sg = np.empty(64, dtype=np.int32)
    seen_pos = np.empty(64, dtype=np.int32)

    for c in range(loadouts.shape[0]):
        cur_pp, cur_cm, cur_fm = int(loadouts[c, 0]), int(loadouts[c, 1]), int(loadouts[c, 2])
        if (
            c == 0
            or cur_cm != loadouts[c - 1, 1]
            or cur_fm != loadouts[c - 1, 2]
            or (allow_pp and cur_pp != loadouts[c - 1, 0])
        ):
            full_cm = _fill_gem_curve(cm_ref_cache, ref_cm, cur_cm, STAT_GEM_GAIN_NORMAL, True)
            full_fm = _fill_gem_curve(fm_ref_cache, ref_fm, cur_fm, STAT_GEM_GAIN_FEVER, True)
            if allow_pp:
                full_pp = _fill_gem_curve(pp_ref_cache, ref_pp, cur_pp, STAT_GEM_GAIN_NORMAL, True)
                pp_0 = pp_ref_cache[0]
                pp_bound_prefix_max[0] = pp_0
                for gp in range(1, full_pp + 1):
                    pp_bound_prefix_max[gp] = max(
                        pp_bound_prefix_max[gp - 1], float(gp * (w_pp - w_ov)) + pp_ref_cache[gp]
                    )
            else:
                full_pp, pp_0, pp_bound_prefix_max[0] = 0, 0.0, 0.0
            delta_range = _stat_line_deltas(
                loadouts, c, allow_pp, ref_pp, most_gain, GEM_BUDGET * w_ov, pp_bound_prefix_max, full_pp
            )
            delta_lo = delta_range[0]
            limits = (full_pp, full_cm, full_fm, allow_pp)
            _fill_column_terms(
                column_combo, column_terms, (w_cm, w_fm, w_ov), cm_ref_cache, fm_ref_cache, limits, delta_range
            )
            term_done[:] = False
            blocks_ready = False
        pp_ref_base = pp_0 if allow_pp else ref_pp[_stat_row(cur_pp)]
        if not allow_pp:
            pp_ref_cache[0] = pp_ref_base
        limits = (full_pp, full_cm, full_fm, allow_pp)
        cur_stats = (cur_cm, pp_ref_base, pp_0, delta_lo, full_pp, full_cm, full_fm, allow_pp)
        term_ctx = (term_max, term_done, column_combo, column_terms, pp_bound_prefix_max, pp_0, w_ov, limits)
        base_p, base_s = int(loadouts[c, 3]), int(loadouts[c, 4])
        ft0, ff0, budget = int(loadouts[c, 5]), int(loadouts[c, 6]), int(budgets[c])
        ft_cap = min(budget, max(0, (MAX_STAT - ft0 + g - 1) // g)) if ft_caps else budget
        ff_cap = min(budget, max(0, (MAX_STAT - ff0 + g - 1) // g)) if ff_caps else budget
        origin, caps = (ft0, ff0, budget), (ft_cap, ff_cap)
        base0 = float((base_p << 1) + base_s) + pp_ref_base

        candidate_best = int(floors[c])
        loadout_best = -2
        win_a = win_b = n_seen = 0
        win_fid = seed_a = seed_b = -1

        if floors[c] < 0:
            seed_a, seed_b = _find_seed_cell(origin, caps, base0, delta_lo, grid_info, term_ctx, (ft_gain, ff_gain))
            if seed_a >= 0:
                fid = int(frontier_idx_by_stat[_stat_row(ft0 + g * seed_a), _stat_row(ff0 + g * seed_b)])
                if fid < 0:
                    raise ValueError("FG response frontier scoring bundle does not cover a requested stat key")
                if not blocks_ready:
                    _fill_blocks(column_first, blocks, block_corners, (w_cm, w_fm, w_ov), cm_ref_cache, fm_ref_cache, limits)
                    blocks_ready = True
                r_s = budget - seed_a - seed_b
                pg, sg = seed_a * ft_p + seed_b * ff_p, seed_a * ft_s + seed_b * ff_s
                sc, surf, g_pp, g_cm, g_fm = _score_group(
                    (r_s, base_p + pg, base_s + sg, fid, candidate_best),
                    cur_stats, caches, block_tables, surfaces, refs, flags_info, work,
                )
                seen_fid[0], seen_r[0], seen_val[0] = fid, r_s, (pg << 1) + sg + w_ov * r_s
                seen_pg[0], seen_sg[0], seen_pos[0] = pg, sg, seed_a * (2 * budget + 3 - seed_a) // 2 + seed_b
                n_seen = 1
                if sc >= 0:
                    loadout_best, win_a, win_b, win_fid = sc, seed_a, seed_b, fid
                    row = out[c]
                    row[0], row[1], row[2], row[3], row[4], row[5] = sc, surf, g_pp, g_cm, g_fm, r_s - g_pp - g_cm - g_fm
                    candidate_best = max(candidate_best, sc)

        for a0 in range(0, ft_cap + 1, _GRID_COARSE):
            a1 = min(ft_cap, a0 + _GRID_COARSE - 1)
            x1 = _stat_row(ft0 + g * a1)
            b_lim = min(ff_cap, budget - a0)
            for b0 in range(0, b_lim + 1, _GRID_COARSE):
                b1 = min(b_lim, b0 + _GRID_COARSE - 1)
                y1 = _stat_row(ff0 + g * b1)
                pa, pf = pref_a[x1, y1], pref_f[x1, y1]
                if _budget_bound(
                    _ensure_term_max(budget - a0 - b0, term_ctx),
                    base0 + float(a1 * ft_gain + b1 * ff_gain) - delta_lo,
                    (pa, s_ae - pa, pf, s_fg - pf),
                ) < float(candidate_best):
                    continue
                for fa0 in range(a0, a1 + 1, _GRID_FINE):
                    fa1 = min(a1, fa0 + _GRID_FINE - 1)
                    fx1 = _stat_row(ft0 + g * fa1)
                    fb_lim = min(b1, budget - fa0)
                    for fb0 in range(b0, fb_lim + 1, _GRID_FINE):
                        fb1 = min(fb_lim, fb0 + _GRID_FINE - 1)
                        fy1 = _stat_row(ff0 + g * fb1)
                        fpa, fpf = pref_a[fx1, fy1], pref_f[fx1, fy1]
                        if _budget_bound(
                            _ensure_term_max(budget - fa0 - fb0, term_ctx),
                            base0 + float(fa1 * ft_gain + fb1 * ff_gain) - delta_lo,
                            (fpa, s_ae - fpa, fpf, s_fg - fpf),
                        ) < float(candidate_best):
                            continue
                        for aa in range(fa0, fa1 + 1):
                            xx = _stat_row(ft0 + g * aa)
                            for bb in range(fb0, min(fb1, budget - aa) + 1):
                                if aa == seed_a and bb == seed_b:
                                    continue
                                r = budget - aa - bb
                                yy = _stat_row(ff0 + g * bb)
                                ca, cf = cell_a[xx, yy], cell_f[xx, yy]
                                gn = aa * ft_gain + bb * ff_gain
                                if _budget_bound(
                                    _ensure_term_max(r, term_ctx), base0 + float(gn) - delta_lo, (ca, s_ae - ca, cf, s_fg - cf)
                                ) < float(candidate_best):
                                    continue
                                fid = int(frontier_idx_by_stat[xx, yy])
                                if fid < 0:
                                    raise ValueError("FG response frontier scoring bundle does not cover a requested stat key")
                                pg, sg = aa * ft_p + bb * ff_p, aa * ft_s + bb * ff_s
                                split = (r, gn + w_ov * r, pg, sg, aa * (2 * budget + 3 - aa) // 2 + bb)
                                skip = False
                                for si in range(n_seen):
                                    if seen_fid[si] == fid and _dominates(
                                        (seen_r[si], seen_val[si], seen_pg[si], seen_sg[si], seen_pos[si]), split
                                    ):
                                        skip = True
                                        break
                                if skip:
                                    continue
                                if n_seen < 64:
                                    seen_fid[n_seen], seen_r[n_seen], seen_val[n_seen] = fid, split[0], split[1]
                                    seen_pg[n_seen], seen_sg[n_seen], seen_pos[n_seen] = pg, sg, split[4]
                                    n_seen += 1
                                if not blocks_ready:
                                    _fill_blocks(
                                        column_first, blocks, block_corners, (w_cm, w_fm, w_ov), cm_ref_cache, fm_ref_cache, limits
                                    )
                                    blocks_ready = True
                                sc, surf, g_pp, g_cm, g_fm = _score_group(
                                    (r, base_p + pg, base_s + sg, fid, candidate_best),
                                    cur_stats, caches, block_tables, surfaces, refs, flags_info, work,
                                )
                                if sc >= 0 and (
                                    sc > loadout_best
                                    or (
                                        sc == loadout_best
                                        and _beats_on_tie(
                                            (aa, bb, fid), (win_a, win_b, win_fid), origin, frontier_idx_by_stat, caps, gains_tie
                                        )
                                    )
                                ):
                                    loadout_best, win_a, win_b, win_fid = sc, aa, bb, fid
                                    row = out[c]
                                    row[0], row[1], row[2], row[3], row[4], row[5] = sc, surf, g_pp, g_cm, g_fm, r - g_pp - g_cm - g_fm
                                    candidate_best = max(candidate_best, sc)
        win_ftff[c, 0], win_ftff[c, 1], win_ftff[c, 2] = win_a, win_b, win_fid
    return out, win_ftff


def _prepare_grid_memo(
    memo: GemMemo, frontier_idx_by_stat: np.ndarray, pool: SurfacePool, body_total: int
) -> tuple[np.ndarray, tuple[Any, ...]]:
    """Build or reuse the song's frontier shapes and 2D prefix grid bounds."""
    if (
        memo.grid_bounds is not None
        and memo.frontier_idx_ref is frontier_idx_by_stat
        and memo.pool_ref is pool
        and memo.body_total == body_total
    ):
        return memo.frontier_shapes, memo.grid_bounds
    frontier_count = pool.frontier_offsets.shape[0]
    shapes = np.zeros((frontier_count, 4), dtype=np.float64)
    done = np.zeros(frontier_count, dtype=np.bool_)
    pool_shapes = (pool.frontier_offsets, pool.frontier_lengths, pool.pattern_ids, pool.counts, pool.head_coeffs)
    _frontier_shapes(frontier_idx_by_stat.ravel(), pool_shapes, body_total, shapes, done)
    grid_bounds = (frontier_idx_by_stat, *_build_grid_bounds(frontier_idx_by_stat, shapes))
    memo.frontier_shapes = shapes
    memo.grid_bounds = grid_bounds
    memo.frontier_idx_ref = frontier_idx_by_stat
    memo.pool_ref = pool
    memo.body_total = body_total
    return shapes, grid_bounds


def gem_winners(
    base_components: np.ndarray,
    frontier_grid: tuple[np.ndarray, SurfacePool],
    *,
    colors: tuple[str, str, str],
    curves: StatCurves,
    notes: tuple[int, int],
    budgets: np.ndarray | None = None,
    floors: np.ndarray | None = None,
    memo: GemMemo | None = None,
) -> list[GemWinner | None]:
    """Each loadout's winner over `pool`'s surfaces reachable on `frontier_idx_by_stat` from its pre-gem totals
    (rows: PP, CM, FM, primary, secondary, FT, FF). With `floors` (a score per loadout) a loadout staying below its
    floor returns None; `memo` shares the song's 2D frontier grid across batches."""
    loadouts = np.ascontiguousarray(base_components, dtype=np.int32)
    count = int(loadouts.shape[0])
    if count == 0:
        return []
    frontier_idx_by_stat, pool = frontier_grid
    head_len, body_total = int(notes[0]), int(notes[1])
    floors_arr = np.full(count, -1, dtype=np.int64) if floors is None else np.ascontiguousarray(floors, dtype=np.int64)
    budgets_arr = np.full(count, GEM_BUDGET, dtype=np.int32) if budgets is None else np.ascontiguousarray(budgets, dtype=np.int32)
    flags = color_flags(*colors)
    allow_pp = bool(flags[0] or flags[1])
    order = np.lexsort(loadouts[:, 2::-1].T) if allow_pp else np.lexsort(loadouts[:, 2:0:-1].T)
    ordered = np.ascontiguousarray(loadouts[order], dtype=np.int32)
    shapes, grid_info = _prepare_grid_memo(GemMemo() if memo is None else memo, frontier_idx_by_stat, pool, body_total)
    surfaces = (
        pool.frontier_offsets, pool.frontier_lengths, shapes, pool.pattern_ids, pool.pattern_words, pool.counts,
        pool.head_coeffs, pool.head_greats,
    )
    tables = (curves.f64["Perfect Points"], curves.f64["Combo Multiplier"], curves.combo_ramp, curves.f64["Fever Multiplier"])
    ft_el, ff_el = STAT_GEMS["Fever Time"][1], STAT_GEMS["Fever Fill Rate"][1]
    primary, secondary, _selected = colors
    song_cfg = (
        head_len, body_total,
        int(primary == ft_el) * STAT_GEM_ELEMENT_GAIN, int(secondary == ft_el) * STAT_GEM_ELEMENT_GAIN,
        int(primary == ff_el) * STAT_GEM_ELEMENT_GAIN, int(secondary == ff_el) * STAT_GEM_ELEMENT_GAIN,
    )
    shared = (grid_info, surfaces, np.asarray(flags, dtype=np.int32), tables, song_cfg)
    rows, win_ftff = _score_on_cpu_cores(
        ordered, np.ascontiguousarray(budgets_arr[order], dtype=np.int32), np.ascontiguousarray(floors_arr[order], dtype=np.int64), shared
    )
    winners: list[GemWinner | None] = [None] * count
    hits = np.flatnonzero((rows[:, 0] >= 0) & (rows[:, 0] >= floors_arr[order]))
    for position in hits.tolist():
        index = int(order[position])
        ft, ff, frontier = int(win_ftff[position, 0]), int(win_ftff[position, 1]), int(win_ftff[position, 2])
        base_ft, base_ff = int(loadouts[index, 5]), int(loadouts[index, 6])
        surface = int(pool.frontier_offsets[frontier]) + int(rows[position, 1])
        winners[index] = GemWinner(
            ft=ft,
            ff=ff,
            ft_stat=min(max(base_ft + ft * STAT_GEM_GAIN_FEVER, 0), MAX_STAT),
            ff_stat=min(max(base_ff + ff * STAT_GEM_GAIN_FEVER, 0), MAX_STAT),
            inner_row=tuple(rows[position].tolist()),
            surface=tuple(int(v) for v in (*pool.pattern_words[pool.pattern_ids[surface]], *pool.counts[surface])),
        )
    return winners


def configure_fg_cpu_search_workers(max_workers: int) -> None:
    """Set the per-process thread count used by ``_score_on_cpu_cores``."""
    global _FG_CPU_SEARCH_WORKERS, _fg_cpu_search_pool
    target = max(1, int(max_workers))
    with _fg_cpu_search_pool_lock:
        if target == _FG_CPU_SEARCH_WORKERS:
            return
        old_pool = _fg_cpu_search_pool
        _FG_CPU_SEARCH_WORKERS = target
        _fg_cpu_search_pool = None
    if old_pool is not None:
        old_pool.shutdown(wait=False)


def _fg_cpu_search_executor() -> ThreadPoolExecutor:
    global _fg_cpu_search_pool
    with _fg_cpu_search_pool_lock:
        if _fg_cpu_search_pool is None:
            _fg_cpu_search_pool = ThreadPoolExecutor(
                max_workers=_FG_CPU_SEARCH_WORKERS, thread_name_prefix="fg-cpu-search"
            )
        return _fg_cpu_search_pool


def _score_on_cpu_cores(
    loadouts: np.ndarray, budgets: np.ndarray, floors: np.ndarray, shared_args: tuple[Any, ...]
) -> tuple[np.ndarray, np.ndarray]:
    """``_score_grid_loadouts`` over contiguous chunks of loadouts on several cores."""
    count = int(loadouts.shape[0])
    chunk_count = min(_FG_CPU_SEARCH_WORKERS * _FG_CPU_SEARCH_CHUNKS_PER_WORKER, count)
    if _FG_CPU_SEARCH_WORKERS <= 1 or chunk_count <= 1:
        return _score_grid_loadouts(loadouts, budgets, floors, *shared_args)
    cuts = np.unique(np.linspace(0, count, chunk_count + 1, dtype=np.int64))
    futures = [
        _fg_cpu_search_executor().submit(
            _score_grid_loadouts, loadouts[start:stop], budgets[start:stop], floors[start:stop], *shared_args
        )
        for start, stop in zip(cuts[:-1], cuts[1:])
    ]
    rows, win_ftff = zip(*(future.result() for future in futures))
    return np.concatenate(rows), np.concatenate(win_ftff)
