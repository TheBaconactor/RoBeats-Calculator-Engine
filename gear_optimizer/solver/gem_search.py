"""The exact gem search: for each loadout, the best gem allocation over the surfaces of the frontiers it reaches, in
CPU f64 numba (FG response surfaces; the Base timing surfaces are the same without Greats).

A loadout's candidate groups are its FT/FF gem splits that reach distinct frontiers. They depend on its pre-gem (FT, FF)
only, so a batch holds them once per distinct (FT, FF), a song's batches can share them (GemMemo), and loadouts with equal
PP, CM and FM share their bound tables.
Consumers read each loadout's first group with the highest score, so anything that cannot reach the loadout's best so
far, or a floor the caller gives it, is pruned. Per surface, (CM, FM) gem pairs are visited in TILE x TILE blocks: the
score bound is monotone in CM and FM gems and base is linear in them, so a block's corner bounds every pair in it. The
bound of a whole group, of a column of blocks and of a block at the frontier's most of each shape coordinate leave each
group its list of live blocks. A surface misses the frontier's most by some amount at any block, so one bound from the
group's peak rejects nearly every surface before its blocks; inside a live block a CM row is bounded before its pairs.
Great notes lower the bound by what they lose at the least: their count times the gap between the Perfect and the Great
base.

Cost per solve in real sizes (COMPLEXITY.md, sections 3 and 16): O(S K) to keep K pre-gem (FT, FF) rows' groups of S = 4,186
splits, O(T (B + R J)) for the bound tables of T distinct (PP, CM, FM) (B blocks in J columns, R = 91 budgets), then per
loadout O(G) group bounds + the blocks of surviving groups' columns + one bound per surface + the live blocks of surviving
surfaces + the rows of surviving blocks + the pairs of surviving rows.
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
import os
import threading
from typing import Any

import numba
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
from gear_optimizer.solver.ftff_combos import ftff_combo_arrays
from gear_optimizer.stats import STAT_GEMS

# (CM, FM) gem pairs per bound block side.
_TILE = 3
# Contiguous chunks of loadouts scored on separate threads.
_FG_CPU_SEARCH_WORKERS = max(1, min(4, (os.cpu_count() or 1)))
_FG_CPU_SEARCH_CHUNKS_PER_WORKER = 2
_fg_cpu_search_pool: ThreadPoolExecutor | None = None
_fg_cpu_search_pool_lock = threading.Lock()


@dataclass(slots=True)
class GemMemo:
    """What the batches of one song and pool share: each pre-gem (FT, FF)'s groups, and each frontier's bound shape."""

    key_groups: dict[int, np.ndarray] = field(default_factory=dict)
    frontier_shapes: np.ndarray = field(default_factory=lambda: np.empty((0, 4), dtype=np.float64))
    shapes_done: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.bool_))


@dataclass(frozen=True, slots=True)
class GemGroups:
    """A batch's gem-search groups. loadouts: (C, 6) PP, CM, FM, primary, secondary, its key. keys: (K, 2) the distinct
    pre-gem FT, FF. key_starts: (K + 1) each key's first group. groups: (G, 5) residual gems, primary and secondary gain
    of the FT/FF split, the frontier it reaches, the split's position in ftff_combo_arrays(GEM_BUDGET). head_len and
    body_total: the song's head and body notes."""

    loadouts: np.ndarray
    keys: np.ndarray
    key_starts: np.ndarray
    groups: np.ndarray
    head_len: int
    body_total: int
    memo: GemMemo = field(default_factory=GemMemo)


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
def _kept_splits(
    keys,
    residual_values,
    frontier_idx_by_stat,
    primary_gains,
    secondary_gains,
    score_elements_constant,
):
    """The groups of each pre-gem (FT, FF) row of keys (GemGroups.groups), flat in row order, and per-row counts (a
    loadout's base colors add to every split alike: its groups depend on FT and FF only). Arrays per split in the order of
    ftff_combo_arrays.

    A row's splits reach frontiers (frontier_idx_by_stat at the split's clipped FT/FF stats); per frontier, in
    first-reached order, it keeps the split with the most residual gems (the first one on a tie), or, when the splits
    reaching it give the song's colors different gains, every split no other split there matches or beats in
    (residual, primary gain, secondary gain) (the earlier split wins an exact tie), in split order. O(splits) per row,
    plus the pairwise check inside a frontier reached by splits of different color gains."""
    key_count = keys.shape[0]
    pair_count = residual_values.shape[0]
    budget = residual_values[0]
    frontier_count = int(frontier_idx_by_stat.max()) + 1
    stamp = np.full(frontier_count, -1, dtype=np.int64)
    head = np.empty(frontier_count, dtype=np.int64)
    tail = np.empty(frontier_count, dtype=np.int64)
    best = np.empty(frontier_count, dtype=np.int64)
    next_pos = np.full(pair_count, -1, dtype=np.int64)
    reached = np.empty(pair_count, dtype=np.int64)
    ft_stats = np.empty(budget + 1, dtype=np.int64)
    ff_stats = np.empty(budget + 1, dtype=np.int64)
    rows = np.empty((key_count * pair_count, 5), dtype=np.int32)
    counts = np.zeros(key_count, dtype=np.int64)
    write = 0
    for c in range(key_count):
        for gems in range(budget + 1):
            ft_stats[gems] = min(max(keys[c, 0] + gems * STAT_GEM_GAIN_FEVER, 0), MAX_STAT)
            ff_stats[gems] = min(max(keys[c, 1] + gems * STAT_GEM_GAIN_FEVER, 0), MAX_STAT)
        reached_count = 0
        first_of_row = 0
        for ft_gems in range(budget + 1):
            row_frontiers = frontier_idx_by_stat[ft_stats[ft_gems]]
            ff_gems = 0
            ff_top = budget - ft_gems
            while ff_gems <= ff_top:
                fid = row_frontiers[ff_stats[ff_gems]]
                pos = first_of_row + ff_gems
                if fid < 0:
                    raise ValueError("FG response frontier scoring bundle does not cover a requested stat key")
                if stamp[fid] != c:
                    stamp[fid] = c
                    head[fid] = tail[fid] = best[fid] = pos
                    reached[reached_count] = fid
                    reached_count += 1
                else:
                    if not score_elements_constant:
                        next_pos[tail[fid]] = pos
                        tail[fid] = pos
                    if residual_values[pos] > residual_values[best[fid]]:
                        best[fid] = pos
                ff_gems += 1
                # Past a stat's cap a gem reaches the same frontier with fewer residual gems.
                if score_elements_constant and ff_gems <= ff_top and ff_stats[ff_gems] == ff_stats[ff_gems - 1]:
                    break
            first_of_row += budget + 1 - ft_gems
            if score_elements_constant and ft_gems < budget and ft_stats[ft_gems + 1] == ft_stats[ft_gems]:
                break
        start = write
        for r in range(reached_count):
            fid = reached[r]
            first = head[fid]
            same_colors = True
            if not score_elements_constant:
                pos = next_pos[first]
                while pos >= 0:
                    if primary_gains[pos] != primary_gains[first] or secondary_gains[pos] != secondary_gains[first]:
                        same_colors = False
                        break
                    pos = next_pos[pos]
            row = best[fid] if same_colors else first
            while row >= 0:
                dominated = False
                other = -1 if same_colors else first
                while other >= 0:
                    if other != row and (
                        residual_values[other] >= residual_values[row]
                        and primary_gains[other] >= primary_gains[row]
                        and secondary_gains[other] >= secondary_gains[row]
                        and (
                            residual_values[other] > residual_values[row]
                            or primary_gains[other] > primary_gains[row]
                            or secondary_gains[other] > secondary_gains[row]
                            or other < row
                        )
                    ):
                        dominated = True
                        break
                    other = next_pos[other]
                if not dominated:
                    written = rows[write]
                    written[0], written[1], written[2] = residual_values[row], primary_gains[row], secondary_gains[row]
                    written[3], written[4] = fid, row
                    write += 1
                row = -1 if same_colors else next_pos[row]
        if not score_elements_constant:
            for r in range(reached_count):
                row = head[reached[r]]
                while row >= 0:
                    following = next_pos[row]
                    next_pos[row] = -1
                    row = following
        counts[c] = write - start
    return rows[:write], counts


def gem_groups(
    base_components: np.ndarray,
    *,
    primary_color: str,
    secondary_color: str,
    frontier_idx_by_stat: np.ndarray,
    total_notes: int,
    memo: GemMemo | None = None,
) -> GemGroups:
    """The gem-search groups of a batch of loadouts (base_components rows: PP, CM, FM, primary, secondary, FT, FF) over
    every FT/FF split of the gem budget (FT gems raise Beat, FF gems Vibe); `memo`: what earlier batches of the song and
    its colors left."""
    memo = GemMemo() if memo is None else memo
    base_components = np.ascontiguousarray(base_components, dtype=np.int32)
    packed = base_components[:, 5].astype(np.int64) * (1 << 32) + base_components[:, 6]
    packed_keys, first_rows, key_of = np.unique(packed, return_index=True, return_inverse=True)
    keys = base_components[first_rows, 5:7]
    new_keys = [index for index, key in enumerate(packed_keys.tolist()) if key not in memo.key_groups]
    if new_keys:
        ft_values, ff_values, residual_values = ftff_combo_arrays(GEM_BUDGET)
        ft_element, ff_element = STAT_GEMS["Fever Time"][1], STAT_GEMS["Fever Fill Rate"][1]
        primary_gains, secondary_gains = (
            np.asarray(
                (ft_values * int(color == ft_element) + ff_values * int(color == ff_element)) * STAT_GEM_ELEMENT_GAIN,
                dtype=np.int32,
            )
            for color in (primary_color, secondary_color)
        )
        constant = not {primary_color, secondary_color} & {ft_element, ff_element}
        rows, counts = zip(*_fg_cpu_search_executor().map(
            lambda chunk: _kept_splits(chunk, residual_values, frontier_idx_by_stat, primary_gains, secondary_gains, constant),
            np.array_split(keys[new_keys], min(_FG_CPU_SEARCH_WORKERS, len(new_keys))),
        ))
        kept = np.split(np.concatenate(rows), np.cumsum(np.concatenate(counts))[:-1])
        memo.key_groups.update(zip(packed_keys[new_keys].tolist(), kept, strict=True))
    key_rows = [memo.key_groups[key] for key in packed_keys.tolist()]
    return GemGroups(
        np.column_stack((base_components[:, :5], key_of.reshape(-1))).astype(np.int32),
        keys,
        np.cumsum([0, *map(len, key_rows)], dtype=np.int64),
        np.concatenate(key_rows),
        min(int(total_notes), 100),
        max(0, int(total_notes) - 100),
        memo,
    )


def gem_winners(
    groups: GemGroups,
    pool: SurfacePool,
    *,
    colors: tuple[str, str, str],
    curves: StatCurves,
    floors: np.ndarray | None = None,
) -> list[GemWinner | None]:
    """Each loadout's winner (its first group with the highest score) over `pool`'s surfaces of its groups' frontiers,
    in batch order; colors = (primary, secondary, selected). With `floors` (a score per loadout) a loadout that stays
    below its floor has no winner (None)."""
    loadout_count = groups.loadouts.shape[0]
    floors = np.full(loadout_count, -1, dtype=np.int64) if floors is None else np.ascontiguousarray(floors, dtype=np.int64)
    # Loadouts with equal PP, CM and FM side by side share their bound tables.
    order = np.lexsort(groups.loadouts[:, 2::-1].T)
    offsets = np.ascontiguousarray(pool.frontier_offsets, dtype=np.int64)
    lengths = np.ascontiguousarray(pool.frontier_lengths, dtype=np.int64)
    pattern_ids = np.ascontiguousarray(pool.pattern_ids, dtype=np.int32)
    counts = np.ascontiguousarray(pool.counts, dtype=np.int32)
    head_coeffs = np.ascontiguousarray(pool.head_coeffs, dtype=np.int32)
    memo = groups.memo
    if memo.shapes_done.shape[0] != offsets.shape[0]:
        memo.frontier_shapes = np.zeros((offsets.shape[0], 4), dtype=np.float64)
        memo.shapes_done = np.zeros(offsets.shape[0], dtype=np.bool_)
    _frontier_shapes(
        groups.groups[:, 3], offsets, lengths, pattern_ids, counts, head_coeffs, groups.body_total, memo.frontier_shapes,
        memo.shapes_done,
    )
    surfaces = (
        offsets, lengths, memo.frontier_shapes,
        pattern_ids, np.ascontiguousarray(pool.pattern_words, dtype=np.uint32), counts, head_coeffs,
        np.ascontiguousarray(pool.head_greats, dtype=np.int32),
    )
    tables = tuple(
        np.ascontiguousarray(table, dtype=np.float64)
        for table in (curves.f64["Perfect Points"], curves.f64["Combo Multiplier"], curves.combo_ramp,
                      curves.f64["Fever Multiplier"])
    )
    loadouts = np.ascontiguousarray(groups.loadouts[order])
    most_gain = int((2 * groups.groups[:, 1] + groups.groups[:, 2]).max())
    rows, winner_groups = _score_on_cpu_cores(
        loadouts,
        floors[order],
        np.diff(groups.key_starts)[loadouts[:, 5]],
        (groups.key_starts, groups.groups, surfaces, np.asarray(color_flags(*colors), dtype=np.int32), tables,
         (groups.head_len, groups.body_total, most_gain)),
    )
    ft_values, ff_values, _residual = ftff_combo_arrays(GEM_BUDGET)
    winners: list[GemWinner | None] = [None] * loadout_count
    for position, index in enumerate(order.tolist()):
        if rows[position, 0] < floors[index]:
            continue
        _residual_gems, _primary, _secondary, frontier, split = groups.groups[winner_groups[position]].tolist()
        base_ft, base_ff = groups.keys[loadouts[position, 5]].tolist()
        ft, ff = int(ft_values[split]), int(ff_values[split])
        surface = int(offsets[frontier]) + int(rows[position, 1])
        winners[index] = GemWinner(
            ft=ft,
            ff=ff,
            ft_stat=min(max(base_ft + ft * STAT_GEM_GAIN_FEVER, 0), MAX_STAT),
            ff_stat=min(max(base_ff + ff * STAT_GEM_GAIN_FEVER, 0), MAX_STAT),
            inner_row=tuple(rows[position].tolist()),
            surface=tuple(int(v) for v in (*pool.pattern_words[pool.pattern_ids[surface]], *pool.counts[surface])),
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
def _surface_score(words, surface, notes, primary_val, secondary_val, pp_factor, multipliers, single_color):
    """Exact score of one surface at a gem-allocated stat line: the game's per-note values with their per-term floor
    order. words: its head pattern; surface: its body fever, Great and fever-Great notes; notes: head and body notes;
    multipliers: combo, combo ramp (the combo multiplier at head notes 1..100), fever. A Great note scores the lower of
    its Perfect and Great value."""
    body_fever, body_great, body_fever_great = surface
    head_len, body_total = notes
    combo_mul, combo_ramp, fever_mul = multipliers
    base_value = float((primary_val * 2) + secondary_val) + pp_factor
    combo_val = int(np.floor(base_value * combo_mul))
    fever_val = int(np.floor(base_value * combo_mul * fever_mul))
    body_normal = body_total - body_fever
    if body_normal < 0:
        body_normal = 0
    score = body_fever * fever_val + body_normal * combo_val

    great_or = int(words[4]) | int(words[5]) | int(words[6]) | int(words[7])
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
        is_fever = (int(words[wi]) >> b) & 1
        scaling = combo_ramp[i]
        if is_fever != 0:
            perfect_val = int(np.floor(base_value * scaling * fever_mul))
        else:
            perfect_val = int(np.floor(base_value * scaling))

        if ((int(words[4 + wi]) >> b) & 1) != 0:
            if is_fever != 0:
                great_val = int(np.floor(great_base * scaling * fever_mul))
            else:
                great_val = int(np.floor(great_base * scaling))
            perfect_val = min(perfect_val, great_val)
        score += perfect_val
    return score


@numba.njit(cache=True, nogil=True, inline="always")
def _surface_shape(body_fever, body_normal, n_hn, n_hf, sigma_hn, sigma_hf):
    """The (A, E, F, G) of a surface's upper bound at one stat line, every head note at its Perfect value: base value x
    _shape_value at its combo and fever (body fever and normal notes, head normal and fever notes, their combo ramp sums).
    A note's bound is its base value times its multipliers, so it holds without the score's floors."""
    ramp_fever, ramp_normal = sigma_hf * 0.01, sigma_hn * 0.01
    return body_fever + ramp_fever, body_normal + ramp_normal, n_hf - ramp_fever, n_hn - ramp_normal


@numba.njit(cache=True, nogil=True, inline="always")
def _shape_value(shape, combo, fever):
    a, e, f, g = shape
    return combo * (a * fever + e) + f * fever + g


@numba.njit(cache=True, nogil=True, inline="always")
def _block_bound(block, delta, shape):
    """The surface bound at a block's best corner (base value, combo, fever), with the margin of _budget_bound."""
    return (block[0] + delta) * _shape_value(shape, block[1], block[2]) + 1025.0


@numba.njit(cache=True, nogil=True, inline="always")
def _budget_bound(c, delta, shape):
    """The surface bound over a budget's columns: each term of _column_bound at its most (c, the terms' maxima as a value
    and its slope in delta)."""
    a, e, f, g = shape
    return (
        a * (c[0] + delta * c[1]) + e * (c[2] + delta * c[3]) + f * (c[4] + delta * c[5]) + g * (c[6] + delta * c[7]) + 1025.0
    )


@numba.njit(cache=True, nogil=True, inline="always")
def _column_bound(combo, column, delta, shape):
    """The surface bound over a column of blocks of one combo: column, (the most base value, the most base value x fever
    as a chord in delta: intercept, slope). Each term of the block bound at the column's most of it."""
    a, e, f, g = shape
    return (column[1] + delta * column[2]) * (combo * a + f) + (column[0] + delta) * (combo * e + g) + 1025.0


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
    """Empty bound tables, refilled per (PP, CM, FM) (_fill_block_bounds): per residual budget its terms (_budget_bound);
    per column of blocks its combo, its first block, and per count of its first blocks their _column_bound terms; then every
    block: (base value without delta, combo and fever at the best corner, combo and fever at the worst) and its (cm0, cm1,
    fm0, fm1) corners."""
    side = (GEM_BUDGET + _TILE) // _TILE
    return (
        np.empty((GEM_BUDGET + 1, 8), dtype=np.float64),
        np.empty(side, dtype=np.float64),
        np.empty(side + 1, dtype=np.int64),
        np.empty((side, side, 3), dtype=np.float64),
        np.empty((side * side, 5), dtype=np.float64),
        np.empty((side * side, 4), dtype=np.int64),
    )


@jit(nopython=True, cache=True)
def _fill_block_bounds(tables, gem_bases, pp_bound_prefix_max, cm_ref_cache, fm_ref_cache, delta_range):
    """The bound tables (_block_bound_tables) of a pre-gem (PP, CM, FM): its (CM, FM) blocks of _TILE x _TILE gem pairs in
    columns of equal cm0, each block's best corner (the highest multipliers, and what its gems add to the base value over
    element gems), and per residual budget its most of each term of the bound over its columns (the max of a sum is at most
    the sum of the maxes). A budget takes a column's blocks its gems can reach, and adds its element gems to delta.

    The most base value x fever of a column's blocks is convex in delta, a maximum of lines, so its chord over delta_range
    (the deltas the stat line's loadouts can have) bounds it there: far tighter than its value at no delta plus delta x
    the highest fever. gem_bases: what a CM, FM and element gem add to the base. The caches hold one entry per gem count the
    loadout can spend on PP, CM and FM."""
    term_max, column_combo, column_first, column_terms, blocks, corners = tables
    w_cm, w_fm, w_ov = gem_bases
    delta_lo, delta_hi = delta_range
    cm_lin_up = w_cm > w_ov
    fm_lin_up = w_fm > w_ov
    full_pp, full_cm, full_fm = len(pp_bound_prefix_max) - 1, len(cm_ref_cache) - 1, len(fm_ref_cache) - 1
    b = 0
    for j in range(full_cm // _TILE + 1):
        cm0 = j * _TILE
        cm1 = min(cm0 + _TILE - 1, full_cm)
        column_combo[j] = cm_ref_cache[cm1]
        column_first[j] = b
        most_base = most_low = most_high = -1.0e30
        for k in range(min(full_fm, GEM_BUDGET - cm0) // _TILE + 1):
            fm0 = k * _TILE
            fm1 = min(fm0 + _TILE - 1, full_fm)
            base = float((cm1 if cm_lin_up else cm0) * (w_cm - w_ov) + (fm1 if fm_lin_up else fm0) * (w_fm - w_ov))
            fever = fm_ref_cache[fm1]
            block = blocks[b]
            block[0], block[1], block[2], block[3], block[4] = base, cm_ref_cache[cm1], fever, cm_ref_cache[cm0], fm_ref_cache[fm0]
            corners[b, 0], corners[b, 1], corners[b, 2], corners[b, 3] = cm0, cm1, fm0, fm1
            most_base = max(most_base, base)
            most_low = max(most_low, (base + delta_lo) * fever)
            most_high = max(most_high, (base + delta_hi) * fever)
            slope = (most_high - most_low) / (delta_hi - delta_lo)
            terms = column_terms[j, k]
            terms[0], terms[1], terms[2] = most_base, most_low - delta_lo * slope, slope
            b += 1
    for r in range(GEM_BUDGET + 1):
        most = term_max[r]
        for j in range(min(full_cm, r) // _TILE + 1):
            cm0 = j * _TILE
            combo = column_combo[j]
            terms = column_terms[j, min(full_fm, r - cm0) // _TILE]
            shift = float(r * w_ov) + pp_bound_prefix_max[min(full_pp, r - cm0)]
            base, base_fever, slope = terms[0] + shift, terms[1] + shift * terms[2], terms[2]
            budget_terms = (combo * base_fever, combo * slope, combo * base, combo, base_fever, slope, base, 1.0)
            for t in range(8):
                most[t] = max(most[t], budget_terms[t]) if j else budget_terms[t]


@jit(nopython=True, cache=True)
def _frontier_shapes(group_frontiers, frontier_offsets, frontier_lengths, pattern_ids, counts, head_coeffs, body_total, shapes, done):
    """Into shapes, per frontier a group reaches that is not done yet, the most of each coordinate of its surfaces' shapes
    (_surface_shape). O(groups + the surfaces of those frontiers)."""
    for f in group_frontiers:
        if not done[f]:
            done[f] = True
            most = shapes[f]
            for row in range(frontier_offsets[f], frontier_offsets[f] + frontier_lengths[f]):
                coeffs = head_coeffs[pattern_ids[row]]
                shape = _surface_shape(
                    counts[row, 0], max(0, body_total - counts[row, 0]), coeffs[0], coeffs[1], coeffs[2], coeffs[3]
                )
                for t in range(4):
                    most[t] = max(most[t], shape[t])


@jit(nopython=True, cache=True)
def _score_loadouts(loadouts, floors, key_starts, groups, surfaces, color_flags, curves, song):
    """Each loadout's best gem allocation over its groups (GemGroups): (rows, winning groups).

    A loadout's winner is its first group with the highest score; within it the first surface reaching that score, with
    the lexicographically smallest (CM, FM, PP) gems. Everything whose bound cannot reach max(this group's best, the
    loadout's best so far or its floor) is skipped; a skipped pair is strictly below that, so the winner's row is exact
    when it reaches the floor, and a loadout whose best is below its floor reports a row below it. Checks are non-strict
    (a tie is still scored) because blocks visit pairs out of lexicographic order and the explicit tie-break must see
    every tie.

    Bounds, each at least every pair score under it: per (CM, FM) block the score at the block's best corner with every
    note Perfect (_block_bound); a column of blocks (equal cm0) takes each term's maximum over its blocks (the max of a sum
    is at most the sum of the maxes), a budget the maxima over its columns, and a group a budget at the most of each shape
    coordinate over its frontier's surfaces, which also leaves the group the blocks a surface can use. At a block a
    surface's bound is the frontier's less base value x its shape's distance from the frontier's, so the group's highest
    block bound less that distance at the live blocks' lowest values bounds the surface over them all. Inside a block, a
    CM row's bound takes the row's best linear base, PP part and FM multiplier (each monotone along it). Each subtracts
    what the surface's Greats lose at the least, at the lowest multipliers under it.

    surfaces: frontier offsets and lengths, their bound shapes (_frontier_shapes), then SurfacePool's pattern ids, pattern
    words, body counts, head coefficients and head Greats; curves: the Perfect Points, Combo Multiplier, combo ramp and
    Fever Multiplier f64 tables; song: head and body notes and the most a group's FT and FF gems add to delta. Row columns:
    [best_score, best_surface, g_pp, g_cm, g_fm, g_ov, final_pp, final_cm, final_fm, final_primary, final_secondary].
    """
    frontier_offsets, frontier_lengths, frontier_shapes, pattern_ids, pattern_words, surface_counts, head_coeffs, \
        head_greats = surfaces
    ref_pp, ref_cm, ref_ramp, ref_fm = curves
    head_len, body_total, most_gain = song
    out = np.zeros((loadouts.shape[0], 11), dtype=np.int64)
    winners = np.zeros(loadouts.shape[0], dtype=np.int64)

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

    full_pp_gems = 0
    pp_ref_base = 0.0
    pp_ref_cache = cm_ref_cache = fm_ref_cache = pp_bound_prefix_max = np.empty(1, dtype=np.float64)
    tables = _block_bound_tables()
    term_max, column_combo, column_first, column_terms, blocks, block_corners = tables
    live_blocks = np.empty(blocks.shape[0], dtype=np.int64)
    live_deltas = np.empty(blocks.shape[0], dtype=np.float64)
    for c in range(loadouts.shape[0]):
        cur_pp, cur_cm, cur_fm = int(loadouts[c, 0]), int(loadouts[c, 1]), int(loadouts[c, 2])
        if c == 0 or cur_pp != loadouts[c - 1, 0] or cur_cm != loadouts[c - 1, 1] or cur_fm != loadouts[c - 1, 2]:
            # The stat curves per gem count and, per residual budget, the (CM, FM) blocks with their bounds.
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
            lowest_colors = highest_colors = (int(loadouts[c, 3]) << 1) + int(loadouts[c, 4])
            last = c + 1
            while last < loadouts.shape[0] and (
                loadouts[last, 0] == cur_pp and loadouts[last, 1] == cur_cm and loadouts[last, 2] == cur_fm
            ):
                colors = (int(loadouts[last, 3]) << 1) + int(loadouts[last, 4])
                lowest_colors, highest_colors = min(lowest_colors, colors), max(highest_colors, colors)
                last += 1
            delta_range = (
                float(lowest_colors) + pp_bound_prefix_max[0],
                float(highest_colors + most_gain + GEM_BUDGET * w_ov) + pp_bound_prefix_max[full_pp_gems] + 1.0,
            )
            _fill_block_bounds(tables, (w_cm, w_fm, w_ov), pp_bound_prefix_max, cm_ref_cache, fm_ref_cache, delta_range)
        candidate_best = int(floors[c])
        loadout_best = -2
        key = loadouts[c, 5]
        for g in range(key_starts[key], key_starts[key + 1]):
            residual_budget = int(groups[g, 0])
            cur_primary = int(loadouts[c, 3]) + int(groups[g, 1])
            cur_secondary = int(loadouts[c, 4]) + int(groups[g, 2])
            frontier = groups[g, 3]
            base_init = (cur_primary << 1) + cur_secondary
            delta = float(base_init)
            budget_delta = delta + float(residual_budget * w_ov)
            most = frontier_shapes[frontier]
            frontier_shape = (most[0], most[1], most[2], most[3])

            group_best_score = -1
            group_best_surface = group_best_pp = group_best_cm = group_best_fm = 0
            live = 0
            peak = 0.0
            low_base = low_combo = low_fever = low_worst_combo = low_worst_fever = 1.0e30
            if _budget_bound(term_max[residual_budget], delta, frontier_shape) >= float(candidate_best):
                for j in range(min(len(cm_ref_cache) - 1, residual_budget) // _TILE + 1):
                    cm0 = j * _TILE
                    last_block = min(len(fm_ref_cache) - 1, residual_budget - cm0) // _TILE
                    column_delta = budget_delta + pp_bound_prefix_max[min(full_pp_gems, residual_budget - cm0)]
                    if _column_bound(column_combo[j], column_terms[j, last_block], column_delta, frontier_shape) >= float(candidate_best):
                        for bi in range(column_first[j], column_first[j] + last_block + 1):
                            block = blocks[bi]
                            block_delta = column_delta
                            if allow_pp:
                                block_delta = budget_delta + pp_bound_prefix_max[min(full_pp_gems, residual_budget - cm0 - block_corners[bi, 2])]
                            bound = _block_bound(block, block_delta, frontier_shape)
                            if bound >= float(candidate_best):
                                live_blocks[live] = bi
                                live_deltas[live] = block_delta
                                live += 1
                                peak = max(peak, bound)
                                low_base = min(low_base, block[0] + block_delta)
                                low_combo, low_fever = min(low_combo, block[1]), min(low_fever, block[2])
                                low_worst_combo, low_worst_fever = min(low_worst_combo, block[3]), min(low_worst_fever, block[4])
            # A note's Great base is at most 2/3 of its base without PP + 150, and gems only raise what is left.
            gap = delta / 3.0 + pp_ref_base - 150.0
            start = frontier_offsets[frontier]
            for ls in range(frontier_lengths[frontier] if live else 0):
                sr = start + ls
                pattern_row = pattern_ids[sr]
                body_fever = int(surface_counts[sr, 0])
                body_great = int(surface_counts[sr, 1])
                body_fever_great = int(surface_counts[sr, 2])
                coeffs = head_coeffs[pattern_row]
                shape = _surface_shape(
                    body_fever, max(0, body_total - body_fever), coeffs[0], coeffs[1], coeffs[2], coeffs[3]
                )
                # What the Greats lose at the least, as a shape: each is worth gap x its multipliers less, past the score's
                # floors (one point a body note). A head note's combo ramp is at least 1.
                if gap >= 1.0:
                    great_shape = (
                        gap * body_fever_great, gap * max(0, body_great - body_fever_great),
                        gap * head_greats[pattern_row, 1], gap * head_greats[pattern_row, 0] - body_great,
                    )
                else:
                    great_shape = (0.0, 0.0, 0.0, 0.0)
                best_score, best_pp, best_cm, best_fm = group_best_score, group_best_pp, group_best_cm, group_best_fm
                threshold = float(max(best_score, candidate_best))
                distance = (
                    frontier_shape[0] - shape[0], frontier_shape[1] - shape[1], frontier_shape[2] - shape[2],
                    frontier_shape[3] - shape[3],
                )
                if (
                    peak - low_base * _shape_value(distance, low_combo, low_fever)
                    - _shape_value(great_shape, low_worst_combo, low_worst_fever) < threshold
                ):
                    continue
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
                        # At the row's combo, a bound is base value x (alpha x fever + beta) and the Greats lose at
                        # least gamma x fever + eta.
                        alpha, beta = shape[0] * cm_mul + shape[2], shape[1] * cm_mul + shape[3]
                        gamma, eta = great_shape[0] * cm_mul + great_shape[2], great_shape[1] * cm_mul + great_shape[3]
                        # The row's bound.
                        lin_fm = fm_hi if fm_lin_up else fm0
                        row_base = float(base_init + g_cm * w_cm + lin_fm * w_fm + (leftover_after_cm - lin_fm) * w_ov)
                        row_base += pp_bound_prefix_max[min(full_pp_gems, leftover_after_cm - fm0)]
                        row_fever = fm_ref_cache[fm_hi]
                        row_loss = gamma * fm_ref_cache[fm0] + eta
                        if row_base * (alpha * row_fever + beta) + 1024.0 - row_loss < threshold:
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
                            pair_value = alpha * fm_mul + beta
                            pair_loss = gamma * fm_mul + eta
                            if max_base_value * pair_value + 1024.0 - pair_loss < threshold:
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
                                if pp_base_value * pair_value + 1024.0 - pair_loss < threshold:
                                    continue
                                score = _surface_score(
                                    pattern_words[pattern_row], (body_fever, body_great, body_fever_great),
                                    (head_len, body_total), primary_base + g_pp * pp_primary_delta,
                                    secondary_base + g_pp * pp_secondary_delta, pp_ref_cache[g_pp],
                                    (cm_mul, cm_ramp, fm_mul), single_color,
                                )
                                if score > best_score or (
                                    score == best_score and (g_cm, g_fm, g_pp) < (best_cm, best_fm, best_pp)
                                ):
                                    best_score, best_pp, best_cm, best_fm = score, g_pp, g_cm, g_fm
                                    threshold = float(max(best_score, candidate_best))

                if best_score > group_best_score:
                    group_best_score, group_best_surface = best_score, ls
                    group_best_pp, group_best_cm, group_best_fm = best_pp, best_cm, best_fm

            if group_best_score > loadout_best:
                loadout_best = group_best_score
                winners[c] = g
                g_ov = residual_budget - group_best_pp - group_best_cm - group_best_fm
                row = out[c]
                row[0], row[1] = group_best_score, group_best_surface
                row[2], row[3], row[4], row[5] = group_best_pp, group_best_cm, group_best_fm, g_ov
                row[6] = cur_pp + group_best_pp * STAT_GEM_GAIN_NORMAL
                row[7] = cur_cm + group_best_cm * STAT_GEM_GAIN_NORMAL
                row[8] = cur_fm + group_best_fm * STAT_GEM_GAIN_FEVER
                row[9] = (
                    cur_primary + group_best_pp * pp_p_delta + group_best_cm * cm_p_delta + group_best_fm * fm_p_delta
                    + g_ov * ov_p_delta
                )
                row[10] = (
                    cur_secondary + group_best_pp * pp_s_delta + group_best_cm * cm_s_delta + group_best_fm * fm_s_delta
                    + g_ov * ov_s_delta
                )
            candidate_best = max(candidate_best, group_best_score)
    return out, winners


def _fg_cpu_search_executor() -> ThreadPoolExecutor:
    global _fg_cpu_search_pool
    with _fg_cpu_search_pool_lock:
        if _fg_cpu_search_pool is None:
            _fg_cpu_search_pool = ThreadPoolExecutor(
                max_workers=_FG_CPU_SEARCH_WORKERS, thread_name_prefix="fg-cpu-search"
            )
        return _fg_cpu_search_pool


def _score_on_cpu_cores(
    loadouts: np.ndarray, floors: np.ndarray, costs: np.ndarray, shared_args: tuple[Any, ...]
) -> tuple[np.ndarray, np.ndarray]:
    """``_score_loadouts`` over contiguous chunks of loadouts on several cores: chunks hold roughly equal groups (`costs`,
    the search's work) and outnumber the workers, so uneven loadouts still balance."""
    count = int(loadouts.shape[0])
    chunk_count = min(_FG_CPU_SEARCH_WORKERS * _FG_CPU_SEARCH_CHUNKS_PER_WORKER, count)
    if _FG_CPU_SEARCH_WORKERS <= 1 or chunk_count <= 1:
        return _score_loadouts(loadouts, floors, *shared_args)
    cumulative = np.cumsum(costs, dtype=np.int64)
    targets = cumulative[-1] * np.arange(1, chunk_count, dtype=np.int64) // chunk_count
    cuts = np.unique(np.concatenate(([0], np.searchsorted(cumulative, targets, side="right"), [count])))
    futures = [
        _fg_cpu_search_executor().submit(_score_loadouts, loadouts[start:stop], floors[start:stop], *shared_args)
        for start, stop in zip(cuts[:-1], cuts[1:])
    ]
    rows, winners = zip(*(future.result() for future in futures))
    return np.concatenate(rows), np.concatenate(winners)
