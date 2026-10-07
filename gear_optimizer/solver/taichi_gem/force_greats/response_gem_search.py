"""The exact FG gem search: for each loadout, the best gem allocation over its response surfaces, in CPU f64 numba.

A loadout's candidate groups are its FT/FF gem splits that reach distinct frontiers (build_response_group_rows); every
consumer reads only each loadout's argmax group (first occurrence), so groups that cannot beat the loadout's best so
far, or a floor the caller gives it, are pruned. Per surface, (CM, FM) gem pairs are visited in TILE x TILE blocks: the score bound is monotone in
CM and FM gems and base is linear in them, so a block's corner bounds every pair in it.
Cost per loadout: Theta(G S K2) bound checks before (G groups, S surfaces per group, K2 (CM, FM) pairs), now
O(G S + sum over surviving surfaces of K2 / TILE^2 + pairs in surviving blocks) (COMPLEXITY.md, section 3).
"""

from concurrent.futures import ThreadPoolExecutor
import os
import threading
from typing import Any

import numpy as np

from gear_optimizer.core.jit_setup import jit
from gear_optimizer.gamedata import StatCurves
from gear_optimizer.rules import (
    ELEMENT_GEM_GAIN,
    MAX_STAT,
    STAT_GEM_ELEMENT_GAIN,
    STAT_GEM_GAIN_FEVER,
    STAT_GEM_GAIN_NORMAL,
)

# (CM, FM) gem pairs per bound block side.
_TILE = 8
# Contiguous group chunks scored on separate threads; a chunk boundary is always a loadout's first group, so a loadout
# is scored by one call and every row equals the serial call's.
_FG_CPU_SEARCH_WORKERS = max(1, min(8, (os.cpu_count() or 1)))
_FG_CPU_SEARCH_CHUNKS_PER_WORKER = 4
_FG_CPU_SEARCH_MIN_GROUPS_PER_CHUNK = 4
_fg_cpu_search_pool: ThreadPoolExecutor | None = None
_fg_cpu_search_pool_lock = threading.Lock()


def color_flags(primary_color: str, secondary_color: str, selected_color: str) -> tuple[int, ...]:
    """Which gem elements raise the song's colors: (PP->primary, PP->secondary, CM->p, CM->s, FM->p, FM->s,
    element->p, element->s, single color)."""
    primary = str(primary_color or "")
    secondary = str(secondary_color or "")
    selected = str(selected_color or "")
    return (
        int(primary == "Chill"),
        int(secondary == "Chill"),
        int(primary == "Flow"),
        int(secondary == "Flow"),
        int(primary == "Rush"),
        int(secondary == "Rush"),
        int(primary == selected and bool(selected)),
        int(secondary == selected and bool(selected)),
        int(primary == secondary),
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


@jit(nopython=True, cache=True)
def _stat_row(stat):
    if stat < 0:
        return 0
    if stat > MAX_STAT:
        return MAX_STAT
    return stat


@jit(nopython=True, cache=True)
def _fg_response_upper_bound_native_f64(
    base_value,
    combo_mul,
    fever_mul,
    body_fever,
    body_normal,
    n_hn,
    n_hf,
    sigma_hn,
    sigma_hf,
):
    """Upper bound of a surface's score at one stat line: every head note at its Perfect value. Non-decreasing in
    base_value, combo_mul and fever_mul."""
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
    fever_mul,
    single_color,
):
    """Exact score of one surface at a gem-allocated stat line: the game's per-note values with their per-term floor
    order; a Great note scores the lower of its Perfect and Great value."""
    base_value = float((primary_val * 2) + secondary_val) + pp_factor
    combo_val = int(np.floor(base_value * combo_mul))
    fever_val = int(np.floor(base_value * combo_mul * fever_mul))
    body_normal = body_total - body_fever
    if body_normal < 0:
        body_normal = 0
    score = body_fever * fever_val + body_normal * combo_val
    combo_slope = (combo_mul - 1.0) / 100.0

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
        scaling = combo_slope * float(i + 1) + 1.0
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


@jit(nopython=True, cache=True)
def _score_fg_response_groups_native_f64(
    group_offsets,
    group_lengths,
    row_meta,
    candidate_floor,
    surface_pattern_ids,
    surface_pattern_words,
    surface_counts,
    surface_pattern_head_coeffs,
    color_flags,
    ref_pp,
    ref_cm,
    ref_fm,
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

    Output columns: [best_score, best_surface, g_pp, g_cm, g_fm, g_ov, final_pp, final_cm, final_fm, final_primary,
    final_secondary].
    """
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
    pp_primary_delta = pp_p_delta - ov_p_delta
    pp_secondary_delta = pp_s_delta - ov_s_delta

    candidate_best = -1
    for g in range(group_count):
        if candidate_floor[g] >= -1:
            candidate_best = candidate_floor[g]
        residual_budget = int(row_meta[g, 0])
        cur_pp = int(row_meta[g, 1])
        cur_cm = int(row_meta[g, 2])
        cur_fm = int(row_meta[g, 3])
        cur_primary = int(row_meta[g, 4])
        cur_secondary = int(row_meta[g, 5])
        head_len = min(int(row_meta[g, 6]), 100)
        body_total = int(row_meta[g, 7])

        max_pp_gems = 0
        if allow_pp and cur_pp < MAX_STAT:
            max_pp_gems = (MAX_STAT - cur_pp + STAT_GEM_GAIN_NORMAL - 1) // STAT_GEM_GAIN_NORMAL
        max_cm_gems = 0
        if cur_cm < MAX_STAT:
            max_cm_gems = (MAX_STAT - cur_cm + STAT_GEM_GAIN_NORMAL - 1) // STAT_GEM_GAIN_NORMAL
        max_fm_gems = 0
        if cur_fm < MAX_STAT:
            max_fm_gems = (MAX_STAT - cur_fm + STAT_GEM_GAIN_FEVER - 1) // STAT_GEM_GAIN_FEVER
        max_pp_gems = min(max_pp_gems, residual_budget)
        max_cm_gems = min(max_cm_gems, residual_budget)
        max_fm_gems = min(max_fm_gems, residual_budget)

        base_init = (cur_primary << 1) + cur_secondary
        pp_ref_base = ref_pp[_stat_row(cur_pp)]
        cm_ref_cache = np.empty(max_cm_gems + 1, dtype=np.float64)
        for gc in range(max_cm_gems + 1):
            cm_ref_cache[gc] = ref_cm[_stat_row(cur_cm + gc * STAT_GEM_GAIN_NORMAL)]
        fm_ref_cache = np.empty(max_fm_gems + 1, dtype=np.float64)
        for gf in range(max_fm_gems + 1):
            fm_ref_cache[gf] = ref_fm[_stat_row(cur_fm + gf * STAT_GEM_GAIN_FEVER)]
        # pp_bound_prefix_max[k]: the best base_value PP can add with at most k PP gems (in place of element gems).
        pp_ref_cache = np.empty(max_pp_gems + 1, dtype=np.float64)
        pp_bound_prefix_max = np.empty(max_pp_gems + 1, dtype=np.float64)
        pp_ref_cache[0] = pp_ref_base
        pp_bound_prefix_max[0] = pp_ref_base
        if allow_pp:
            running = -1.0e30
            for gp in range(max_pp_gems + 1):
                v = ref_pp[_stat_row(cur_pp + gp * STAT_GEM_GAIN_NORMAL)]
                pp_ref_cache[gp] = v
                bound = float(gp * delta_pp_vs_ov) + v
                if bound > running:
                    running = bound
                pp_bound_prefix_max[gp] = running
        # The base_value bound of a block of gem pairs: base_value is linear in (CM gems, FM gems) beyond the PP part.
        cm_lin_up = w_cm > w_ov
        fm_lin_up = w_fm > w_ov
        # No allocation's base_value exceeds every residual gem on the heaviest weight plus the best PP part.
        surface_base_max = float(base_init + residual_budget * max(w_cm, w_fm, w_ov))
        if allow_pp:
            surface_base_max += pp_bound_prefix_max[max_pp_gems]
        else:
            surface_base_max += pp_ref_base

        group_best_score = -1
        group_best_surface = 0
        group_best_pp = 0
        group_best_cm = 0
        group_best_fm = 0
        group_best_ov = residual_budget
        group_best_final_pp = cur_pp
        group_best_final_cm = cur_cm
        group_best_final_fm = cur_fm
        group_best_final_primary = cur_primary + group_best_ov * ov_p_delta
        group_best_final_secondary = cur_secondary + group_best_ov * ov_s_delta

        start = int(group_offsets[g])
        for ls in range(int(group_lengths[g])):
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

            best_score = group_best_score
            best_pp = group_best_pp
            best_cm = group_best_cm
            best_fm = group_best_fm
            best_ov = group_best_ov
            best_final_pp = group_best_final_pp
            best_final_cm = group_best_final_cm
            best_final_fm = group_best_final_fm
            best_final_primary = group_best_final_primary
            best_final_secondary = group_best_final_secondary

            surface_ub = _fg_response_upper_bound_native_f64(
                surface_base_max, cm_ref_cache[max_cm_gems], fm_ref_cache[max_fm_gems], body_fever, body_normal,
                n_hn, n_hf, sigma_hn, sigma_hf,
            )
            if surface_ub < float(max(best_score, candidate_best)):
                continue
            for cm0 in range(0, max_cm_gems + 1, _TILE):
                cm1 = min(cm0 + _TILE - 1, max_cm_gems)
                fm_top = min(max_fm_gems, residual_budget - cm0)
                for fm0 in range(0, fm_top + 1, _TILE):
                    fm1 = min(fm0 + _TILE - 1, fm_top)
                    lin_cm = cm1 if cm_lin_up else cm0
                    lin_fm = fm1 if fm_lin_up else fm0
                    block_base = float(
                        base_init + lin_cm * w_cm + lin_fm * w_fm + (residual_budget - lin_cm - lin_fm) * w_ov
                    )
                    if allow_pp:
                        block_base += pp_bound_prefix_max[min(max_pp_gems, residual_budget - cm0 - fm0)]
                    else:
                        block_base += pp_ref_base
                    block_ub = _fg_response_upper_bound_native_f64(
                        block_base, cm_ref_cache[cm1], fm_ref_cache[fm1], body_fever, body_normal, n_hn, n_hf,
                        sigma_hn, sigma_hf,
                    )
                    if block_ub < float(max(best_score, candidate_best)):
                        continue
                    for g_cm in range(cm0, cm1 + 1):
                        leftover_after_cm = residual_budget - g_cm
                        cm_stat = cur_cm + g_cm * STAT_GEM_GAIN_NORMAL
                        cm_mul = cm_ref_cache[g_cm]
                        for g_fm in range(fm0, min(fm1, max_fm_gems, leftover_after_cm) + 1):
                            leftover_after_fm = leftover_after_cm - g_fm
                            fm_stat = cur_fm + g_fm * STAT_GEM_GAIN_FEVER
                            fm_mul = fm_ref_cache[g_fm]
                            g_pp_max = min(max_pp_gems, leftover_after_fm)
                            base_linear_common = base_init + g_cm * w_cm + g_fm * w_fm + leftover_after_fm * w_ov
                            if allow_pp:
                                max_base_value = float(base_linear_common) + pp_bound_prefix_max[g_pp_max]
                            else:
                                max_base_value = float(base_linear_common) + pp_ref_base
                            ub = _fg_response_upper_bound_native_f64(
                                max_base_value, cm_mul, fm_mul, body_fever, body_normal, n_hn, n_hf, sigma_hn,
                                sigma_hf,
                            )
                            if ub < float(max(best_score, candidate_best)):
                                continue
                            primary_base = (
                                cur_primary + g_cm * cm_p_delta + g_fm * fm_p_delta + leftover_after_fm * ov_p_delta
                            )
                            secondary_base = (
                                cur_secondary + g_cm * cm_s_delta + g_fm * fm_s_delta + leftover_after_fm * ov_s_delta
                            )
                            if allow_pp and max_pp_gems > 0:
                                record_base_value = -1.0e30
                                for g_pp in range(g_pp_max + 1):
                                    g_ov = leftover_after_fm - g_pp
                                    pp_stat = cur_pp + g_pp * STAT_GEM_GAIN_NORMAL
                                    primary_val = primary_base + g_pp * pp_primary_delta
                                    secondary_val = secondary_base + g_pp * pp_secondary_delta
                                    pp_base_value = (
                                        float(base_linear_common + g_pp * delta_pp_vs_ov) + pp_ref_cache[g_pp]
                                    )
                                    # Great bases are nonincreasing only when both coordinates are.
                                    if pp_primary_delta <= 0 and pp_secondary_delta <= 0:
                                        if pp_base_value <= record_base_value:
                                            continue
                                        record_base_value = pp_base_value
                                    pp_ub = _fg_response_upper_bound_native_f64(
                                        pp_base_value, cm_mul, fm_mul, body_fever, body_normal, n_hn, n_hf,
                                        sigma_hn, sigma_hf,
                                    )
                                    if pp_ub < float(max(best_score, candidate_best)):
                                        continue
                                    score = _fg_response_surface_score_native_f64(
                                        surface_pattern_words, pattern_row, body_fever, body_great, body_fever_great,
                                        head_len, body_total, primary_val, secondary_val, pp_ref_cache[g_pp], cm_mul,
                                        fm_mul, single_color,
                                    )
                                    if score > best_score or (
                                        score == best_score
                                        and (
                                            g_cm < best_cm
                                            or (
                                                g_cm == best_cm
                                                and (g_fm < best_fm or (g_fm == best_fm and g_pp < best_pp))
                                            )
                                        )
                                    ):
                                        best_score = score
                                        best_pp = g_pp
                                        best_cm = g_cm
                                        best_fm = g_fm
                                        best_ov = g_ov
                                        best_final_pp = pp_stat
                                        best_final_cm = cm_stat
                                        best_final_fm = fm_stat
                                        best_final_primary = primary_val
                                        best_final_secondary = secondary_val
                            else:
                                score = _fg_response_surface_score_native_f64(
                                    surface_pattern_words, pattern_row, body_fever, body_great, body_fever_great,
                                    head_len, body_total, primary_base, secondary_base, pp_ref_base, cm_mul, fm_mul,
                                    single_color,
                                )
                                if score > best_score or (
                                    score == best_score
                                    and (
                                        g_cm < best_cm
                                        or (g_cm == best_cm and (g_fm < best_fm or (g_fm == best_fm and 0 < best_pp)))
                                    )
                                ):
                                    best_score = score
                                    best_pp = 0
                                    best_cm = g_cm
                                    best_fm = g_fm
                                    best_ov = leftover_after_fm
                                    best_final_pp = cur_pp
                                    best_final_cm = cm_stat
                                    best_final_fm = fm_stat
                                    best_final_primary = primary_base
                                    best_final_secondary = secondary_base

            if best_score > group_best_score:
                group_best_score = best_score
                group_best_surface = ls
                group_best_pp = best_pp
                group_best_cm = best_cm
                group_best_fm = best_fm
                group_best_ov = best_ov
                group_best_final_pp = best_final_pp
                group_best_final_cm = best_final_cm
                group_best_final_fm = best_final_fm
                group_best_final_primary = best_final_primary
                group_best_final_secondary = best_final_secondary

        out[g, 0] = group_best_score
        out[g, 1] = group_best_surface
        out[g, 2] = group_best_pp
        out[g, 3] = group_best_cm
        out[g, 4] = group_best_fm
        out[g, 5] = group_best_ov
        out[g, 6] = group_best_final_pp
        out[g, 7] = group_best_final_cm
        out[g, 8] = group_best_final_fm
        out[g, 9] = group_best_final_primary
        out[g, 10] = group_best_final_secondary
        if group_best_score > candidate_best:
            candidate_best = group_best_score
    return out


def _score_response_group_meta_cpu(
    *,
    group_meta: np.ndarray,
    group_offsets: np.ndarray,
    group_lengths: np.ndarray,
    candidate_slices: tuple[tuple[int, int], ...],
    primary_color: str,
    secondary_color: str,
    selected_color: str,
    curves: StatCurves,
    surface_pattern_ids: np.ndarray,
    surface_pattern_words: np.ndarray,
    surface_counts: np.ndarray,
    surface_pattern_head_coeffs: np.ndarray,
    floors: np.ndarray | None = None,
) -> np.ndarray:
    """The groups' best gem allocations (rows as in _score_fg_response_groups_native_f64) over CPU cores; only each
    loadout's argmax row (candidate_slices: its (first group, group count)) is exact, and with `floors` (one score per
    loadout) only when it reaches the loadout's floor."""
    group_meta = np.ascontiguousarray(group_meta, dtype=np.int32)
    if int(np.unique(group_meta[:, 6]).shape[0]) != 1:
        raise ValueError("response frontier CPU group metadata has inconsistent head length")
    candidate_floor = np.full(int(group_meta.shape[0]), -2, dtype=np.int64)
    candidate_floor[[int(start) for start, _count in candidate_slices]] = -1 if floors is None else floors
    shared = (
        np.ascontiguousarray(surface_pattern_ids, dtype=np.int32),
        np.ascontiguousarray(surface_pattern_words, dtype=np.uint32),
        np.ascontiguousarray(surface_counts, dtype=np.int32),
        np.ascontiguousarray(surface_pattern_head_coeffs, dtype=np.int32),
        np.asarray(color_flags(primary_color, secondary_color, selected_color), dtype=np.int32),
        np.ascontiguousarray(curves.f64["Perfect Points"], dtype=np.float64),
        np.ascontiguousarray(curves.f64["Combo Multiplier"], dtype=np.float64),
        np.ascontiguousarray(curves.f64["Fever Multiplier"], dtype=np.float64),
    )
    rows = _score_fg_response_groups_on_cpu_cores(
        np.ascontiguousarray(group_offsets, dtype=np.int64),
        np.ascontiguousarray(group_lengths, dtype=np.int64),
        group_meta,
        candidate_floor,
        shared,
    )
    return np.asarray(rows, dtype=np.int32)


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
            group_offsets, group_lengths, group_meta, candidate_floor, *shared_args
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
            *shared_args,
        )
        for start, stop in zip(cuts[:-1], cuts[1:])
        if stop > start
    ]
    return np.concatenate([future.result() for future in futures], axis=0)
