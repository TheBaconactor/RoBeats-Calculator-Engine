"""The exact gem search: for each loadout, the best gem allocation over the surfaces of the frontiers it reaches, in
CPU f64 numba (FG response surfaces; the Base timing surfaces are the same without Greats).

A loadout's candidate groups are its FT/FF gem splits that reach distinct frontiers (build_response_group_rows); every
consumer reads only each loadout's argmax group (first occurrence), so groups that cannot beat the loadout's best so
far, or a floor the caller gives it, are pruned. Per surface, (CM, FM) gem pairs are visited in TILE x TILE blocks: the
score bound is monotone in CM and FM gems and base is linear in them, so a block's corner bounds every pair in it.
Block bounds are dot products of a surface's six bound statistics with per-block coefficients built once per loadout
and residual budget; their per-statistic maxima bound a column of blocks, a whole surface and, at a frontier's most of
each statistic, a whole group; inside a block a CM row is bounded before its pairs. Cost per loadout: O(R B) for the
tables + O(G) group bounds + the surface bounds of surviving groups + C column bounds per surviving surface + the
blocks of surviving columns + the rows of surviving blocks + the pairs of surviving rows (R residual budgets, B blocks
and C columns per budget, G groups; COMPLEXITY.md, section 3).
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import os
import threading
from typing import Any

import numba
import numpy as np

from gear_optimizer.core.jit_setup import jit
from gear_optimizer.gamedata import StatCurves
from gear_optimizer.rules import (
    ELEMENT_GEM_GAIN,
    GEM_BUDGET,
    MAX_STAT,
    STAT_GEM_ELEMENT_GAIN,
    STAT_GEM_GAIN_FEVER,
    STAT_GEM_GAIN_NORMAL,
)
from gear_optimizer.solver.ftff_combos import ftff_combo_arrays
from gear_optimizer.stats import STAT_GEMS

# (CM, FM) gem pairs per bound block side.
_TILE = 8
# Contiguous group chunks scored on separate threads; a chunk boundary is always a loadout's first group, so a loadout
# is scored by one call and every row equals the serial call's.
_FG_CPU_SEARCH_WORKERS = max(1, min(8, (os.cpu_count() or 1)))
_FG_CPU_SEARCH_CHUNKS_PER_WORKER = 4
_FG_CPU_SEARCH_MIN_GROUPS_PER_CHUNK = 4
_fg_cpu_search_pool: ThreadPoolExecutor | None = None
_fg_cpu_search_pool_lock = threading.Lock()


@dataclass(frozen=True, slots=True)
class SurfacePool:
    """The surfaces a gem search scores. Frontier f holds rows frontier_offsets[f] .. frontier_offsets[f] +
    frontier_lengths[f]; row r is head pattern pattern_ids[r] (pattern_words: its 4 fever and 4 Great words over the
    head notes; head_coeffs: its surface_head_coeffs) with body counts counts[r] (fever notes, Great notes, both)."""

    frontier_offsets: np.ndarray
    frontier_lengths: np.ndarray
    pattern_ids: np.ndarray
    pattern_words: np.ndarray
    counts: np.ndarray
    head_coeffs: np.ndarray


@dataclass(frozen=True, slots=True)
class GemGroups:
    """A batch's gem-search groups (build_response_group_rows) and the frontier each scores."""

    meta: np.ndarray
    ft: np.ndarray
    ff: np.ndarray
    ft_stat: np.ndarray
    ff_stat: np.ndarray
    frontiers: np.ndarray
    candidate_slices: np.ndarray


@dataclass(frozen=True, slots=True)
class GemWinner:
    """A loadout's gem-search winner: its FT/FF gems and stat keys, the 11-int row (best score, surface index in its
    frontier, PP/CM/FM/element gems, final PP/CM/FM/primary/secondary) and the winning surface (11 ints)."""

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


@jit(nopython=True, cache=True)
def _kept_split_positions(
    base_components,
    ft_values,
    ff_values,
    residual_values,
    frontier_idx_by_stat,
    primary_ftff_delta_values,
    secondary_ftff_delta_values,
    score_elements_constant,
):
    """Each loadout's groups as positions into the FT/FF split arrays, flat in loadout order, and per-loadout counts.

    A loadout's splits reach frontiers (frontier_idx_by_stat at the split's clipped FT/FF stats); per frontier, in
    first-reached order, it keeps the split with the most residual gems (the first one on a tie), or, when the splits
    reaching it give the song's colors different values, every split no other split there matches or beats in
    (residual, primary, secondary) (the earlier split wins an exact tie), in split order. O(splits) per loadout, plus
    the pairwise check inside a frontier reached by splits of different color values."""
    candidate_count = base_components.shape[0]
    pair_count = ft_values.shape[0]
    frontier_count = int(frontier_idx_by_stat.max()) + 1
    stamp = np.full(frontier_count, -1, dtype=np.int64)
    head = np.empty(frontier_count, dtype=np.int64)
    tail = np.empty(frontier_count, dtype=np.int64)
    best = np.empty(frontier_count, dtype=np.int64)
    next_pos = np.empty(pair_count, dtype=np.int64)
    reached = np.empty(pair_count, dtype=np.int64)
    positions = np.empty(candidate_count * pair_count, dtype=np.int32)
    counts = np.zeros(candidate_count, dtype=np.int64)
    write = 0
    for c in range(candidate_count):
        base_primary = base_components[c, 3]
        base_secondary = base_components[c, 4]
        reached_count = 0
        for pos in range(pair_count):
            ft_stat = min(max(base_components[c, 5] + ft_values[pos] * STAT_GEM_GAIN_FEVER, 0), MAX_STAT)
            ff_stat = min(max(base_components[c, 6] + ff_values[pos] * STAT_GEM_GAIN_FEVER, 0), MAX_STAT)
            fid = frontier_idx_by_stat[ft_stat, ff_stat]
            if fid < 0:
                raise ValueError("FG response frontier scoring bundle does not cover a requested stat key")
            next_pos[pos] = -1
            if stamp[fid] != c:
                stamp[fid] = c
                head[fid] = pos
                tail[fid] = pos
                best[fid] = pos
                reached[reached_count] = fid
                reached_count += 1
            else:
                next_pos[tail[fid]] = pos
                tail[fid] = pos
                if residual_values[pos] > residual_values[best[fid]]:
                    best[fid] = pos
        start = write
        for r in range(reached_count):
            fid = reached[r]
            first = head[fid]
            same_colors = True
            if not score_elements_constant:
                pos = next_pos[first]
                while pos >= 0:
                    if (
                        primary_ftff_delta_values[pos] != primary_ftff_delta_values[first]
                        or secondary_ftff_delta_values[pos] != secondary_ftff_delta_values[first]
                    ):
                        same_colors = False
                        break
                    pos = next_pos[pos]
            if same_colors:
                positions[write] = best[fid]
                write += 1
                continue
            row = first
            while row >= 0:
                row_primary = base_primary + primary_ftff_delta_values[row]
                row_secondary = base_secondary + secondary_ftff_delta_values[row]
                dominated = False
                other = first
                while other >= 0:
                    if other != row:
                        other_primary = base_primary + primary_ftff_delta_values[other]
                        other_secondary = base_secondary + secondary_ftff_delta_values[other]
                        if (
                            residual_values[other] >= residual_values[row]
                            and other_primary >= row_primary
                            and other_secondary >= row_secondary
                            and (
                                residual_values[other] > residual_values[row]
                                or other_primary > row_primary
                                or other_secondary > row_secondary
                                or other < row
                            )
                        ):
                            dominated = True
                            break
                    other = next_pos[other]
                if not dominated:
                    positions[write] = row
                    write += 1
                row = next_pos[row]
        counts[c] = write - start
    return positions[:write], counts


def build_response_group_rows(
    base_components: np.ndarray,
    ft_values: np.ndarray,
    ff_values: np.ndarray,
    residual_values: np.ndarray,
    frontier_idx_by_stat: np.ndarray,
    primary_ftff_delta_values: np.ndarray,
    secondary_ftff_delta_values: np.ndarray,
    score_elements_constant: bool,
    head_len: int,
    body_total: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """The gem search's groups for a batch of loadouts (base_components rows: PP, CM, FM, primary, secondary, FT, FF):
    (group_meta, group_ft, group_ff, group_ft_stat, group_ff_stat, candidate_slices). group_meta rows: residual gems,
    PP, CM, FM, primary and secondary with the split's element gains, head length, body notes; candidate_slices rows:
    (first group, group count) per loadout."""
    base_components = np.ascontiguousarray(base_components, dtype=np.int32)
    positions, counts = _kept_split_positions(
        base_components,
        np.ascontiguousarray(ft_values, dtype=np.int32),
        np.ascontiguousarray(ff_values, dtype=np.int32),
        np.ascontiguousarray(residual_values, dtype=np.int32),
        np.ascontiguousarray(frontier_idx_by_stat, dtype=np.int32),
        np.ascontiguousarray(primary_ftff_delta_values, dtype=np.int32),
        np.ascontiguousarray(secondary_ftff_delta_values, dtype=np.int32),
        bool(score_elements_constant),
    )
    owner = np.repeat(np.arange(base_components.shape[0]), counts)
    base = base_components[owner]
    group_ft = np.ascontiguousarray(ft_values[positions], dtype=np.int32)
    group_ff = np.ascontiguousarray(ff_values[positions], dtype=np.int32)
    group_meta = np.empty((positions.shape[0], 8), dtype=np.int32)
    group_meta[:, 0] = residual_values[positions]
    group_meta[:, 1:4] = base[:, 0:3]
    group_meta[:, 4] = base[:, 3] + primary_ftff_delta_values[positions]
    group_meta[:, 5] = base[:, 4] + secondary_ftff_delta_values[positions]
    group_meta[:, 6] = head_len
    group_meta[:, 7] = body_total
    candidate_slices = np.empty((base_components.shape[0], 2), dtype=np.int32)
    candidate_slices[:, 0] = np.cumsum(counts) - counts
    candidate_slices[:, 1] = counts
    return (
        group_meta,
        group_ft,
        group_ff,
        np.clip(base[:, 5] + group_ft * STAT_GEM_GAIN_FEVER, 0, MAX_STAT).astype(np.int32),
        np.clip(base[:, 6] + group_ff * STAT_GEM_GAIN_FEVER, 0, MAX_STAT).astype(np.int32),
        candidate_slices,
    )


def gem_groups(
    base_components: np.ndarray,
    *,
    primary_color: str,
    secondary_color: str,
    frontier_idx_by_stat: np.ndarray,
    total_notes: int,
    total_budget: int,
) -> GemGroups:
    """The gem-search groups of a batch of loadouts (base_components rows: PP, CM, FM, primary, secondary, FT, FF) over
    every FT/FF split of total_budget (FT gems raise Beat, FF gems Vibe)."""
    ft_values, ff_values, residual_values = ftff_combo_arrays(int(total_budget))
    ft_element, ff_element = STAT_GEMS["Fever Time"][1], STAT_GEMS["Fever Fill Rate"][1]
    primary_delta, secondary_delta = (
        np.asarray(
            (ft_values * int(color == ft_element) + ff_values * int(color == ff_element)) * STAT_GEM_ELEMENT_GAIN,
            dtype=np.int32,
        )
        for color in (primary_color, secondary_color)
    )
    meta, ft, ff, ft_stat, ff_stat, candidate_slices = build_response_group_rows(
        base_components,
        ft_values,
        ff_values,
        residual_values,
        frontier_idx_by_stat,
        primary_delta,
        secondary_delta,
        not {primary_color, secondary_color} & {ft_element, ff_element},
        min(int(total_notes), 100),
        max(0, int(total_notes) - 100),
    )
    return GemGroups(meta, ft, ff, ft_stat, ff_stat, frontier_idx_by_stat[ft_stat, ff_stat], candidate_slices)


def gem_winners(
    groups: GemGroups,
    pool: SurfacePool,
    *,
    colors: tuple[str, str, str],
    curves: StatCurves,
    floors: np.ndarray | None = None,
) -> list[GemWinner]:
    """Each loadout's winner (its first group with the highest score) over `pool`'s surfaces of its groups' frontiers,
    in batch order; colors = (primary, secondary, selected). With `floors` (a score per loadout) a winner is exact only
    when it reaches its floor."""
    offsets = np.ascontiguousarray(pool.frontier_offsets[groups.frontiers], dtype=np.int64)
    lengths = np.ascontiguousarray(pool.frontier_lengths[groups.frontiers], dtype=np.int64)
    candidate_floor = np.full(groups.meta.shape[0], -2, dtype=np.int64)
    candidate_floor[groups.candidate_slices[:, 0]] = -1 if floors is None else floors
    surfaces = (
        np.ascontiguousarray(pool.pattern_ids, dtype=np.int32),
        np.ascontiguousarray(pool.pattern_words, dtype=np.uint32),
        np.ascontiguousarray(pool.counts, dtype=np.int32),
        np.ascontiguousarray(pool.head_coeffs, dtype=np.int32),
    )
    tables = tuple(
        np.ascontiguousarray(table, dtype=np.float64)
        for table in (curves.f64["Perfect Points"], curves.f64["Combo Multiplier"], curves.combo_ramp,
                      curves.f64["Fever Multiplier"])
    )
    rows = _score_fg_response_groups_on_cpu_cores(
        offsets,
        lengths,
        np.ascontiguousarray(groups.meta, dtype=np.int32),
        candidate_floor,
        _group_bound_stats(offsets, lengths, surfaces),
        (surfaces, np.asarray(color_flags(*colors), dtype=np.int32), tables),
    )
    winners = []
    for start, count in groups.candidate_slices.tolist():
        g = start + int(np.argmax(rows[start : start + count, 0]))
        surface = int(offsets[g]) + int(rows[g, 1])
        winners.append(
            GemWinner(
                ft=int(groups.ft[g]),
                ff=int(groups.ff[g]),
                ft_stat=int(groups.ft_stat[g]),
                ff_stat=int(groups.ff_stat[g]),
                inner_row=tuple(int(v) for v in rows[g]),
                surface=tuple(int(v) for v in (*pool.pattern_words[pool.pattern_ids[surface]], *pool.counts[surface])),
            )
        )
    return winners


@jit(nopython=True, cache=True)
def _stat_row(stat):
    if stat < 0:
        return 0
    if stat > MAX_STAT:
        return MAX_STAT
    return stat


@jit(nopython=True, cache=True)
def _fg_response_upper_bound_native_f64(base_value, combo_mul, fever_mul, stats):
    """Upper bound of a surface's score at one stat line: every head note at its Perfect value (stats: the surface's
    body fever and normal notes, head normal and fever notes, their combo ramp sums). Non-decreasing in base_value,
    combo_mul and fever_mul."""
    body_fever, body_normal, n_hn, n_hf, sigma_hn, sigma_hf = stats
    ub_eps = 1024.0
    combo_val = int(np.floor(base_value * combo_mul))
    fever_val = int(np.floor(base_value * combo_mul * fever_mul))
    body_score = body_fever * fever_val + body_normal * combo_val
    factor = (combo_mul - 1.0) * base_value / 100.0
    head_upper = base_value * (float(n_hn) + fever_mul * float(n_hf)) + factor * (
        float(sigma_hn) + fever_mul * float(sigma_hf)
    )
    return float(body_score) + head_upper + ub_eps


@jit(nopython=True, cache=True)
def _fg_response_surface_score_native_f64(
    surface_words,
    sr,
    body_fever,
    body_great,
    body_fever_great,
    head_len,
    body_total,
    primary_val,
    secondary_val,
    pp_factor,
    combo_mul,
    combo_ramp,
    fever_mul,
    single_color,
):
    """Exact score of one surface at a gem-allocated stat line: the game's per-note values with their per-term floor
    order (combo_ramp: the combo multiplier at head notes 1..100); a Great note scores the lower of its Perfect and
    Great value."""
    base_value = float((primary_val * 2) + secondary_val) + pp_factor
    combo_val = int(np.floor(base_value * combo_mul))
    fever_val = int(np.floor(base_value * combo_mul * fever_mul))
    body_normal = body_total - body_fever
    if body_normal < 0:
        body_normal = 0
    score = body_fever * fever_val + body_normal * combo_val

    great_or = (
        int(surface_words[sr, 4])
        | int(surface_words[sr, 5])
        | int(surface_words[sr, 6])
        | int(surface_words[sr, 7])
    )
    great_base = 0.0
    if body_great > 0 or great_or != 0:
        great_base = float(
            primary_val * 2 + 150 if single_color else
            int(np.floor(float(primary_val) * (4.0 / 3.0))) + int(np.floor(float(secondary_val) * (2.0 / 3.0))) + 150
        )
        great_combo_val = int(np.floor(great_base * combo_mul))
        great_fever_val = int(np.floor(great_base * combo_mul * fever_mul))
        if body_great > 0:
            body_normal_great = body_great - body_fever_great
            if body_normal_great < 0:
                body_normal_great = 0
            body_normal_penalty = combo_val - great_combo_val
            if body_normal_penalty < 0:
                body_normal_penalty = 0
            body_fever_penalty = fever_val - great_fever_val
            if body_fever_penalty < 0:
                body_fever_penalty = 0
            score -= body_normal_great * body_normal_penalty
            score -= body_fever_great * body_fever_penalty

    for i in range(head_len):
        wi = i >> 5
        b = i & 31
        is_fever = (int(surface_words[sr, wi]) >> b) & 1
        scaling = combo_ramp[i]
        if is_fever != 0:
            perfect_val = int(np.floor(base_value * scaling * fever_mul))
        else:
            perfect_val = int(np.floor(base_value * scaling))

        if ((int(surface_words[sr, 4 + wi]) >> b) & 1) != 0:
            if is_fever != 0:
                great_val = int(np.floor(great_base * scaling * fever_mul))
            else:
                great_val = int(np.floor(great_base * scaling))
            perfect_val = min(perfect_val, great_val)
        score += perfect_val
    return score


@numba.njit(cache=True, nogil=True, inline="always")
def _block_dot(c, delta, stats):
    """A block bound: its coefficients c (per surface statistic, a value and its slope in base_init) at a surface's
    stats (as in _fg_response_upper_bound_native_f64) and the group's base_init (delta), with the bound's margin (+1
    against the float order)."""
    body_fever, body_normal, n_hn, n_hf, sigma_hn, sigma_hf = stats
    return (
        body_fever * (c[0] + delta * c[1]) + body_normal * (c[2] + delta * c[3]) + n_hn * (c[4] + delta * c[5])
        + n_hf * (c[6] + delta * c[7]) + sigma_hn * (c[8] + delta * c[9]) + sigma_hf * (c[10] + delta * c[11])
        + 1025.0
    )


@jit(nopython=True, cache=True)
def _gem_curve(ref, stat, gain, allowed):
    """ref at stat + k * gain for k = 0 .. the gems that take stat to MAX_STAT (at most GEM_BUDGET; none unless
    allowed)."""
    gems = min(max(0, (MAX_STAT - stat + gain - 1) // gain), GEM_BUDGET) if allowed else 0
    out = np.empty(gems + 1, dtype=np.float64)
    for k in range(gems + 1):
        out[k] = ref[_stat_row(stat + k * gain)]
    return out


@jit(nopython=True, cache=True)
def _block_bound_tables():
    """Empty bound tables, refilled per loadout (_fill_block_bounds): per residual budget the coefficients' maxima, the
    same per column of its blocks, each column's first block (and the end of its last), its column count; then every
    budget's block coefficients and (cm0, cm1, fm0, fm1) corners, flat in (budget, column) order."""
    side = (GEM_BUDGET + _TILE) // _TILE
    return (
        np.empty((GEM_BUDGET + 1, 12), dtype=np.float64),
        np.empty((GEM_BUDGET + 1, side, 12), dtype=np.float64),
        np.empty((GEM_BUDGET + 1, side + 1), dtype=np.int64),
        np.empty(GEM_BUDGET + 1, dtype=np.int64),
        np.empty(((GEM_BUDGET + 1) * side * side, 12), dtype=np.float64),
        np.empty(((GEM_BUDGET + 1) * side * side, 4), dtype=np.int64),
    )


@jit(nopython=True, cache=True)
def _fill_block_bounds(tables, w_cm, w_fm, w_ov, pp_bound_prefix_max, cm_ref_cache, fm_ref_cache):
    """A loadout's bound tables (_block_bound_tables): per residual budget r (0..GEM_BUDGET), its (CM, FM) blocks of
    _TILE x _TILE gem pairs in columns of equal cm0, each block's bound coefficients at its best corner
    (_fg_response_upper_bound_native_f64 without its floors, base_value = the corner's base without base_init +
    base_init) and their maxima per column and over r. The caches hold one entry per gem count the loadout can spend on
    PP, CM and FM."""
    term_max, columns, first, column_count, blocks, corners = tables
    cm_lin_up = w_cm > w_ov
    fm_lin_up = w_fm > w_ov
    full_pp, full_cm, full_fm = len(pp_bound_prefix_max) - 1, len(cm_ref_cache) - 1, len(fm_ref_cache) - 1
    b = 0
    for r in range(GEM_BUDGET + 1):
        max_cm = min(full_cm, r)
        column_count[r] = max_cm // _TILE + 1
        for j in range(column_count[r]):
            cm0 = j * _TILE
            cm1 = min(cm0 + _TILE - 1, max_cm)
            fm_top = min(full_fm, r - cm0)
            first[r, j] = b
            for fm0 in range(0, fm_top + 1, _TILE):
                fm1 = min(fm0 + _TILE - 1, fm_top)
                lin_cm = cm1 if cm_lin_up else cm0
                lin_fm = fm1 if fm_lin_up else fm0
                base = float(lin_cm * w_cm + lin_fm * w_fm + (r - lin_cm - lin_fm) * w_ov)
                base += pp_bound_prefix_max[min(full_pp, r - cm0 - fm0)]
                cm, fm = cm_ref_cache[cm1], fm_ref_cache[fm1]
                ramp = (cm - 1.0) / 100.0
                c = blocks[b]
                c[0], c[1], c[2], c[3] = base * cm * fm, cm * fm, base * cm, cm
                c[4], c[5], c[6], c[7] = base, 1.0, base * fm, fm
                c[8], c[9], c[10], c[11] = ramp * base, ramp, ramp * base * fm, ramp * fm
                corners[b, 0], corners[b, 1], corners[b, 2], corners[b, 3] = cm0, cm1, fm0, fm1
                for t in range(12):
                    columns[r, j, t] = max(columns[r, j, t], c[t]) if fm0 else c[t]
                b += 1
            for t in range(12):
                term_max[r, t] = max(term_max[r, t], columns[r, j, t]) if j else columns[r, j, t]
        first[r, column_count[r]] = b


@jit(nopython=True, cache=True)
def _group_bound_stats(group_offsets, group_lengths, pool):
    """Per group, over its frontier's surfaces (pool as in _score_fg_response_groups_native_f64): the most body fever
    notes, the fewest, and the most of each head coefficient (normal and fever notes, their combo ramp sums)."""
    pattern_ids, _words, counts, head_coeffs = pool
    out = np.zeros((group_offsets.shape[0], 6), dtype=np.int64)
    for g in range(group_offsets.shape[0]):
        out[g, 1] = 1 << 40 if group_lengths[g] else 0
        for row in range(group_offsets[g], group_offsets[g] + group_lengths[g]):
            out[g, 0] = max(out[g, 0], counts[row, 0])
            out[g, 1] = min(out[g, 1], counts[row, 0])
            for t in range(4):
                out[g, 2 + t] = max(out[g, 2 + t], head_coeffs[pattern_ids[row], t])
    return out


@jit(nopython=True, cache=True)
def _score_fg_response_groups_native_f64(
    group_offsets, group_lengths, row_meta, candidate_floor, group_stats, pool, color_flags, curves
):
    """Each group's best gem allocation over its surfaces (the residual budget's CM / FM / PP / element split).

    A loadout's groups run in order; candidate_floor holds, at a loadout's first group, the score its winner must reach
    (-1: any), and -2 at every other group. The loadout's winner is its first group with the highest score; within it
    the first surface reaching that score, with the lexicographically smallest (CM, FM, PP) gems. Every surface and gem
    pair whose bound cannot reach max(this group's best, the loadout's best so far or its floor) is skipped; a skipped
    pair can at most tie an earlier group, so the winner's row is exact when it reaches the floor, a loadout whose best
    is below its floor reports a row below it, and a losing group's row may hold less than its own best. Pair checks
    are non-strict (a tie is still scored) because blocks visit pairs out of lexicographic order and the explicit
    tie-break must see every tie.

    Bounds, each at least every pair score under it: per loadout and residual budget, each (CM, FM) block's bound is a
    dot product of six surface statistics (stats: body fever and normal notes, head normal and fever notes and their
    combo ramp sums) with the block's coefficients at its best corner; a column of blocks (equal cm0) uses each
    coefficient's maximum over its blocks (the max of a sum is at most the sum of the maxes), a surface the maxima over
    all blocks, and a group the surface's at the most of each statistic over its frontier's surfaces (group_stats:
    _group_bound_stats). Inside a block, a CM row's bound takes the row's best linear base, PP part and FM multiplier
    (each monotone along it) before its pairs' own bounds. A skipped group or surface writes what an all-skipped one
    did.

    pool: the surfaces' (pattern ids, pattern words, body counts, head coefficients), as in SurfacePool; curves: the
    Perfect Points, Combo Multiplier, combo ramp and Fever Multiplier f64 tables. Output columns: [best_score,
    best_surface, g_pp, g_cm, g_fm, g_ov, final_pp, final_cm, final_fm, final_primary, final_secondary].
    """
    surface_pattern_ids, surface_pattern_words, surface_counts, surface_pattern_head_coeffs = pool
    ref_pp, ref_cm, ref_ramp, ref_fm = curves
    group_count = int(row_meta.shape[0])
    out = np.zeros((group_count, 11), dtype=np.int64)

    pp_p_delta = STAT_GEM_ELEMENT_GAIN * int(color_flags[0])
    pp_s_delta = STAT_GEM_ELEMENT_GAIN * int(color_flags[1])
    cm_p_delta = STAT_GEM_ELEMENT_GAIN * int(color_flags[2])
    cm_s_delta = STAT_GEM_ELEMENT_GAIN * int(color_flags[3])
    fm_p_delta = STAT_GEM_ELEMENT_GAIN * int(color_flags[4])
    fm_s_delta = STAT_GEM_ELEMENT_GAIN * int(color_flags[5])
    ov_p_delta = ELEMENT_GEM_GAIN * int(color_flags[6])
    ov_s_delta = ELEMENT_GEM_GAIN * int(color_flags[7])
    single_color = color_flags[8]
    # PP gems raise Chill: only a Chill song can want them.
    allow_pp = pp_p_delta != 0 or pp_s_delta != 0
    w_pp = (pp_p_delta << 1) + pp_s_delta
    w_cm = (cm_p_delta << 1) + cm_s_delta
    w_fm = (fm_p_delta << 1) + fm_s_delta
    w_ov = (ov_p_delta << 1) + ov_s_delta
    delta_pp_vs_ov = w_pp - w_ov
    fm_lin_up = w_fm > w_ov
    pp_primary_delta = pp_p_delta - ov_p_delta
    pp_secondary_delta = pp_s_delta - ov_s_delta

    candidate_best = full_pp_gems = 0
    pp_ref_base = 0.0
    loadout_pp = loadout_cm = loadout_fm = -1  # no loadout yet: a group before its loadout's first group raises
    pp_ref_cache = cm_ref_cache = fm_ref_cache = pp_bound_prefix_max = np.empty(1, dtype=np.float64)
    tables = _block_bound_tables()
    term_max, columns, column_first, column_count, blocks, block_corners = tables
    for g in range(group_count):
        residual_budget = int(row_meta[g, 0])
        cur_pp = int(row_meta[g, 1])
        cur_cm = int(row_meta[g, 2])
        cur_fm = int(row_meta[g, 3])
        cur_primary = int(row_meta[g, 4])
        cur_secondary = int(row_meta[g, 5])
        head_len = min(int(row_meta[g, 6]), 100)
        body_total = int(row_meta[g, 7])

        if candidate_floor[g] >= -1:
            # A loadout's first group: its floor, its stat curves per gem count (its groups share its PP, CM and FM and
            # differ only in residual gems) and, per residual budget, its (CM, FM) blocks with their bound coefficients.
            candidate_best = candidate_floor[g]
            loadout_pp, loadout_cm, loadout_fm = cur_pp, cur_cm, cur_fm
            pp_ref_cache = _gem_curve(ref_pp, cur_pp, STAT_GEM_GAIN_NORMAL, allow_pp)
            cm_ref_cache = _gem_curve(ref_cm, cur_cm, STAT_GEM_GAIN_NORMAL, True)
            fm_ref_cache = _gem_curve(ref_fm, cur_fm, STAT_GEM_GAIN_FEVER, True)
            full_pp_gems = len(pp_ref_cache) - 1
            pp_ref_base = pp_ref_cache[0]
            # pp_bound_prefix_max[k]: the best base_value PP can add with at most k PP gems (in place of element gems).
            pp_bound_prefix_max = pp_ref_cache.copy()
            for gp in range(1, full_pp_gems + 1):
                pp_bound_prefix_max[gp] = max(
                    pp_bound_prefix_max[gp - 1], float(gp * delta_pp_vs_ov) + pp_ref_cache[gp]
                )
            _fill_block_bounds(tables, w_cm, w_fm, w_ov, pp_bound_prefix_max, cm_ref_cache, fm_ref_cache)
        elif cur_pp != loadout_pp or cur_cm != loadout_cm or cur_fm != loadout_fm:
            raise ValueError("a loadout's groups must follow its first group and share its PP, CM and FM")
        base_init = (cur_primary << 1) + cur_secondary
        delta = float(base_init)
        terms = term_max[residual_budget]
        fs = group_stats[g]
        group_ub = _block_dot(terms, delta, (fs[0], max(0, body_total - fs[1]), fs[2], fs[3], fs[4], fs[5]))

        group_best_score = -1
        group_best_surface = group_best_pp = group_best_cm = group_best_fm = 0
        start = int(group_offsets[g])
        for ls in range(int(group_lengths[g]) if group_ub >= float(candidate_best) else 0):
            sr = start + ls
            pattern_row = int(surface_pattern_ids[sr])
            body_fever = int(surface_counts[sr, 0])
            body_great = int(surface_counts[sr, 1])
            body_fever_great = int(surface_counts[sr, 2])
            body_normal = max(0, body_total - body_fever)
            n_hn = int(surface_pattern_head_coeffs[pattern_row, 0])
            n_hf = int(surface_pattern_head_coeffs[pattern_row, 1])
            sigma_hn = int(surface_pattern_head_coeffs[pattern_row, 2])
            sigma_hf = int(surface_pattern_head_coeffs[pattern_row, 3])
            stats = (body_fever, body_normal, n_hn, n_hf, sigma_hn, sigma_hf)
            best_score, best_pp, best_cm, best_fm = group_best_score, group_best_pp, group_best_cm, group_best_fm

            if _block_dot(terms, delta, stats) < float(max(best_score, candidate_best)):
                continue
            for j in range(column_count[residual_budget]):
                if _block_dot(columns[residual_budget, j], delta, stats) < float(max(best_score, candidate_best)):
                    continue
                for bi in range(column_first[residual_budget, j], column_first[residual_budget, j + 1]):
                    if _block_dot(blocks[bi], delta, stats) < float(max(best_score, candidate_best)):
                        continue
                    cm0, cm1 = block_corners[bi, 0], block_corners[bi, 1]
                    fm0, fm1 = block_corners[bi, 2], block_corners[bi, 3]
                    for g_cm in range(cm0, cm1 + 1):
                        leftover_after_cm = residual_budget - g_cm
                        cm_mul = cm_ref_cache[g_cm]
                        fm_hi = min(fm1, leftover_after_cm)
                        # The row's bound.
                        lin_fm = fm_hi if fm_lin_up else fm0
                        row_base = float(base_init + g_cm * w_cm + lin_fm * w_fm + (leftover_after_cm - lin_fm) * w_ov)
                        row_base += pp_bound_prefix_max[min(full_pp_gems, leftover_after_cm - fm0)]
                        if _fg_response_upper_bound_native_f64(row_base, cm_mul, fm_ref_cache[fm_hi], stats) < float(
                            max(best_score, candidate_best)
                        ):
                            continue
                        cm_ramp = ref_ramp[_stat_row(cur_cm + g_cm * STAT_GEM_GAIN_NORMAL)]
                        for g_fm in range(fm0, fm_hi + 1):
                            leftover_after_fm = leftover_after_cm - g_fm
                            fm_mul = fm_ref_cache[g_fm]
                            g_pp_max = min(full_pp_gems, leftover_after_fm)
                            base_linear_common = base_init + g_cm * w_cm + g_fm * w_fm + leftover_after_fm * w_ov
                            if allow_pp:
                                max_base_value = float(base_linear_common) + pp_bound_prefix_max[g_pp_max]
                            else:
                                max_base_value = float(base_linear_common) + pp_ref_base
                            if _fg_response_upper_bound_native_f64(max_base_value, cm_mul, fm_mul, stats) < float(
                                max(best_score, candidate_best)
                            ):
                                continue
                            primary_base = (
                                cur_primary + g_cm * cm_p_delta + g_fm * fm_p_delta + leftover_after_fm * ov_p_delta
                            )
                            secondary_base = (
                                cur_secondary + g_cm * cm_s_delta + g_fm * fm_s_delta + leftover_after_fm * ov_s_delta
                            )
                            record_base_value = -1.0e30
                            for g_pp in range(g_pp_max + 1):
                                pp_base_value = float(base_linear_common + g_pp * delta_pp_vs_ov) + pp_ref_cache[g_pp]
                                # Great bases are nonincreasing only when both coordinates are.
                                if pp_primary_delta <= 0 and pp_secondary_delta <= 0:
                                    if pp_base_value <= record_base_value:
                                        continue
                                    record_base_value = pp_base_value
                                if _fg_response_upper_bound_native_f64(pp_base_value, cm_mul, fm_mul, stats) < float(
                                    max(best_score, candidate_best)
                                ):
                                    continue
                                score = _fg_response_surface_score_native_f64(
                                    surface_pattern_words, pattern_row, body_fever, body_great, body_fever_great,
                                    head_len, body_total, primary_base + g_pp * pp_primary_delta,
                                    secondary_base + g_pp * pp_secondary_delta, pp_ref_cache[g_pp], cm_mul, cm_ramp,
                                    fm_mul, single_color,
                                )
                                if score > best_score or (
                                    score == best_score and (g_cm, g_fm, g_pp) < (best_cm, best_fm, best_pp)
                                ):
                                    best_score, best_pp, best_cm, best_fm = score, g_pp, g_cm, g_fm

            if best_score > group_best_score:
                group_best_score, group_best_surface = best_score, ls
                group_best_pp, group_best_cm, group_best_fm = best_pp, best_cm, best_fm

        g_ov = residual_budget - group_best_pp - group_best_cm - group_best_fm
        out[g, 0] = group_best_score
        out[g, 1] = group_best_surface
        out[g, 2] = group_best_pp
        out[g, 3] = group_best_cm
        out[g, 4] = group_best_fm
        out[g, 5] = g_ov
        out[g, 6] = cur_pp + group_best_pp * STAT_GEM_GAIN_NORMAL
        out[g, 7] = cur_cm + group_best_cm * STAT_GEM_GAIN_NORMAL
        out[g, 8] = cur_fm + group_best_fm * STAT_GEM_GAIN_FEVER
        out[g, 9] = (
            cur_primary + group_best_pp * pp_p_delta + group_best_cm * cm_p_delta + group_best_fm * fm_p_delta
            + g_ov * ov_p_delta
        )
        out[g, 10] = (
            cur_secondary + group_best_pp * pp_s_delta + group_best_cm * cm_s_delta + group_best_fm * fm_s_delta
            + g_ov * ov_s_delta
        )
        candidate_best = max(candidate_best, group_best_score)
    return out


def _fg_cpu_search_executor() -> ThreadPoolExecutor:
    global _fg_cpu_search_pool
    with _fg_cpu_search_pool_lock:
        if _fg_cpu_search_pool is None:
            _fg_cpu_search_pool = ThreadPoolExecutor(
                max_workers=_FG_CPU_SEARCH_WORKERS, thread_name_prefix="fg-cpu-search"
            )
        return _fg_cpu_search_pool


def _score_fg_response_groups_on_cpu_cores(
    group_offsets: np.ndarray,
    group_lengths: np.ndarray,
    group_meta: np.ndarray,
    candidate_floor: np.ndarray,
    group_stats: np.ndarray,
    shared_args: tuple[Any, ...],
) -> np.ndarray:
    """``_score_fg_response_groups_native_f64`` over contiguous chunks of whole loadouts on several cores.

    Chunks hold roughly equal surface rows (the search cost) and outnumber the workers so uneven loadouts still
    balance; every cut sits on a loadout's first group, so the rows equal one serial call's.
    """
    group_count = int(group_meta.shape[0])
    chunk_count = min(
        _FG_CPU_SEARCH_WORKERS * _FG_CPU_SEARCH_CHUNKS_PER_WORKER,
        group_count // _FG_CPU_SEARCH_MIN_GROUPS_PER_CHUNK,
    )
    if _FG_CPU_SEARCH_WORKERS <= 1 or chunk_count <= 1:
        return _score_fg_response_groups_native_f64(
            group_offsets, group_lengths, group_meta, candidate_floor, group_stats, *shared_args
        )
    cumulative = np.cumsum(group_lengths, dtype=np.int64)
    targets = cumulative[-1] * np.arange(1, chunk_count, dtype=np.int64) // chunk_count
    loadout_starts = np.append(np.flatnonzero(candidate_floor >= -1), group_count)
    cut_groups = np.searchsorted(cumulative, targets, side="right")
    cuts = np.unique(np.concatenate(([0], loadout_starts[np.searchsorted(loadout_starts, cut_groups)], [group_count])))
    futures = [
        _fg_cpu_search_executor().submit(
            _score_fg_response_groups_native_f64,
            group_offsets[start:stop],
            group_lengths[start:stop],
            group_meta[start:stop],
            candidate_floor[start:stop],
            group_stats[start:stop],
            *shared_args,
        )
        for start, stop in zip(cuts[:-1], cuts[1:])
        if stop > start
    ]
    return np.concatenate([future.result() for future in futures], axis=0)
