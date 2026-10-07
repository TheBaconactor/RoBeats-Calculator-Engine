"""The exact FG gem search: for each loadout, the best gem allocation over its response surfaces, in CPU f64 numba."""

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

# The search scores each group independently (it writes only that group's output row), so contiguous group chunks
# scored on separate threads and concatenated in order equal one call.
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
def _fg_clamp_ref_idx_native(idx, total_rows):
    if idx < 0:
        return 0
    if idx > total_rows:
        return total_rows
    return idx


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
    surface_pattern_ids,
    surface_pattern_words,
    surface_counts,
    surface_pattern_head_coeffs,
    color_flags,
    ref_pp,
    ref_cm,
    ref_fm,
    allow_pp,
    total_rows,
):
    """Each group's best gem allocation over its surfaces (the residual budget's CM / FM / PP / element split): the
    first surface reaching the group's highest score, with the lexicographically smallest (CM, FM, PP) gems; a gem
    pair whose bound cannot beat the group's best so far is skipped. residual_budget == 0 scores the stats as they
    are (the gems-fixed serving path).

    Output columns: [best_score, best_surface, g_pp, g_cm, g_fm, g_ov, final_pp, final_cm, final_fm, final_primary,
    final_secondary].
    """
    group_count = int(row_meta.shape[0])
    out = np.zeros((group_count, 11), dtype=np.int64)

    is_p_pp = int(color_flags[0])
    is_s_pp = int(color_flags[1])
    is_p_cm = int(color_flags[2])
    is_s_cm = int(color_flags[3])
    is_p_fm = int(color_flags[4])
    is_s_fm = int(color_flags[5])
    is_p_ov = int(color_flags[6])
    is_s_ov = int(color_flags[7])

    pp_p_delta = STAT_GEM_ELEMENT_GAIN * is_p_pp
    pp_s_delta = STAT_GEM_ELEMENT_GAIN * is_s_pp
    cm_p_delta = STAT_GEM_ELEMENT_GAIN * is_p_cm
    cm_s_delta = STAT_GEM_ELEMENT_GAIN * is_s_cm
    fm_p_delta = STAT_GEM_ELEMENT_GAIN * is_p_fm
    fm_s_delta = STAT_GEM_ELEMENT_GAIN * is_s_fm
    ov_p_delta = ELEMENT_GEM_GAIN * is_p_ov
    ov_s_delta = ELEMENT_GEM_GAIN * is_s_ov
    w_pp = (pp_p_delta << 1) + pp_s_delta
    w_cm = (cm_p_delta << 1) + cm_s_delta
    w_fm = (fm_p_delta << 1) + fm_s_delta
    w_ov = (ov_p_delta << 1) + ov_s_delta
    delta_pp_vs_ov = w_pp - w_ov
    pp_primary_delta = pp_p_delta - ov_p_delta
    pp_secondary_delta = pp_s_delta - ov_s_delta

    for g in range(group_count):
        residual_budget = int(row_meta[g, 0])
        cur_pp = int(row_meta[g, 1])
        cur_cm = int(row_meta[g, 2])
        cur_fm = int(row_meta[g, 3])
        cur_primary = int(row_meta[g, 4])
        cur_secondary = int(row_meta[g, 5])
        head_len = int(row_meta[g, 6])
        body_total = int(row_meta[g, 7])
        if head_len > 100:
            head_len = 100

        max_pp_gems = 0
        if allow_pp and cur_pp < MAX_STAT:
            rem_pp = MAX_STAT - cur_pp
            max_pp_gems = rem_pp // STAT_GEM_GAIN_NORMAL
            if rem_pp % STAT_GEM_GAIN_NORMAL != 0:
                max_pp_gems += 1
        max_cm_gems = 0
        if cur_cm < MAX_STAT:
            rem_cm = MAX_STAT - cur_cm
            max_cm_gems = rem_cm // STAT_GEM_GAIN_NORMAL
            if rem_cm % STAT_GEM_GAIN_NORMAL != 0:
                max_cm_gems += 1
        max_fm_gems = 0
        if cur_fm < MAX_STAT:
            rem_fm = MAX_STAT - cur_fm
            max_fm_gems = rem_fm // STAT_GEM_GAIN_FEVER
            if rem_fm % STAT_GEM_GAIN_FEVER != 0:
                max_fm_gems += 1
        if max_pp_gems > residual_budget:
            max_pp_gems = residual_budget
        if max_cm_gems > residual_budget:
            max_cm_gems = residual_budget
        if max_fm_gems > residual_budget:
            max_fm_gems = residual_budget

        base_init = (cur_primary << 1) + cur_secondary
        pp_ref_base = ref_pp[_fg_clamp_ref_idx_native(cur_pp, total_rows)]
        cm_ref_cache = np.empty(max_cm_gems + 1, dtype=np.float64)
        for gc in range(max_cm_gems + 1):
            cm_ref_cache[gc] = ref_cm[_fg_clamp_ref_idx_native(cur_cm + gc * STAT_GEM_GAIN_NORMAL, total_rows)]
        fm_ref_cache = np.empty(max_fm_gems + 1, dtype=np.float64)
        for gf in range(max_fm_gems + 1):
            fm_ref_cache[gf] = ref_fm[_fg_clamp_ref_idx_native(cur_fm + gf * STAT_GEM_GAIN_FEVER, total_rows)]
        pp_ref_cache = np.empty(max_pp_gems + 1, dtype=np.float64)
        pp_bound_prefix_max = np.empty(max_pp_gems + 1, dtype=np.float64)
        pp_ref_cache[0] = pp_ref_base
        pp_bound_prefix_max[0] = pp_ref_base
        if allow_pp:
            running = -1.0e30
            for gp in range(max_pp_gems + 1):
                v = ref_pp[_fg_clamp_ref_idx_native(cur_pp + gp * STAT_GEM_GAIN_NORMAL, total_rows)]
                pp_ref_cache[gp] = v
                bound = float(gp * delta_pp_vs_ov) + v
                if bound > running:
                    running = bound
                pp_bound_prefix_max[gp] = running

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
        length = int(group_lengths[g])
        for ls in range(length):
            sr = start + ls
            pattern_row = int(surface_pattern_ids[sr])
            body_fever = int(surface_counts[sr, 0])
            body_great = int(surface_counts[sr, 1])
            body_fever_great = int(surface_counts[sr, 2])
            body_normal = body_total - body_fever
            if body_normal < 0:
                body_normal = 0
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

            g_cm = 0
            while g_cm <= max_cm_gems:
                leftover_after_cm = residual_budget - g_cm
                if leftover_after_cm < 0:
                    break
                cm_stat = cur_cm + g_cm * STAT_GEM_GAIN_NORMAL
                cm_mul = cm_ref_cache[g_cm]
                g_fm_max = max_fm_gems
                if g_fm_max > leftover_after_cm:
                    g_fm_max = leftover_after_cm
                g_fm = 0
                while g_fm <= g_fm_max:
                    leftover_after_fm = leftover_after_cm - g_fm
                    fm_stat = cur_fm + g_fm * STAT_GEM_GAIN_FEVER
                    fm_mul = fm_ref_cache[g_fm]
                    g_pp_max = max_pp_gems
                    if g_pp_max > leftover_after_fm:
                        g_pp_max = leftover_after_fm

                    base_linear_common = base_init + (g_cm * w_cm) + (g_fm * w_fm) + (leftover_after_fm * w_ov)
                    if allow_pp:
                        max_base_value = float(base_linear_common) + pp_bound_prefix_max[g_pp_max]
                    else:
                        max_base_value = float(base_linear_common) + pp_ref_base
                    ub = _fg_response_upper_bound_native_f64(
                        max_base_value, cm_mul, fm_mul, body_fever, body_normal, n_hn, n_hf, sigma_hn, sigma_hf
                    )

                    if ub > float(best_score):
                        primary_base = cur_primary + g_cm * cm_p_delta + g_fm * fm_p_delta + leftover_after_fm * ov_p_delta
                        secondary_base = (
                            cur_secondary + g_cm * cm_s_delta + g_fm * fm_s_delta + leftover_after_fm * ov_s_delta
                        )
                        if allow_pp and max_pp_gems > 0:
                            g_pp = 0
                            record_base_value = -1.0e30
                            while g_pp <= g_pp_max:
                                g_ov = leftover_after_fm - g_pp
                                pp_stat = cur_pp + g_pp * STAT_GEM_GAIN_NORMAL
                                primary_val = primary_base + g_pp * pp_primary_delta
                                secondary_val = secondary_base + g_pp * pp_secondary_delta
                                pp_base_value = float(base_linear_common + g_pp * delta_pp_vs_ov) + pp_ref_cache[g_pp]
                                # Great bases are nonincreasing only when both coordinates are.
                                if pp_primary_delta <= 0 and pp_secondary_delta <= 0:
                                    if pp_base_value <= record_base_value:
                                        g_pp += 1
                                        continue
                                    record_base_value = pp_base_value
                                pp_ub = _fg_response_upper_bound_native_f64(
                                    pp_base_value, cm_mul, fm_mul, body_fever, body_normal, n_hn, n_hf, sigma_hn, sigma_hf
                                )
                                if pp_ub >= float(best_score):
                                    score = _fg_response_surface_score_native_f64(
                                        surface_pattern_words,
                                        pattern_row,
                                        body_fever,
                                        body_great,
                                        body_fever_great,
                                        head_len,
                                        body_total,
                                        primary_val,
                                        secondary_val,
                                        pp_ref_cache[g_pp],
                                        cm_mul,
                                        fm_mul,
                                        color_flags[8],
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
                                g_pp += 1
                        else:
                            pp_factor = pp_ref_cache[0] if allow_pp else pp_ref_base
                            score = _fg_response_surface_score_native_f64(
                                surface_pattern_words,
                                pattern_row,
                                body_fever,
                                body_great,
                                body_fever_great,
                                head_len,
                                body_total,
                                primary_base,
                                secondary_base,
                                pp_factor,
                                cm_mul,
                                fm_mul,
                                color_flags[8],
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
                    g_fm += 1
                g_cm += 1

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
    return out


def _score_response_group_meta_cpu(
    *,
    group_meta: np.ndarray,
    group_offsets: np.ndarray,
    group_lengths: np.ndarray,
    primary_color: str,
    secondary_color: str,
    selected_color: str,
    curves: StatCurves,
    surface_pattern_ids: np.ndarray,
    surface_pattern_words: np.ndarray,
    surface_counts: np.ndarray,
    surface_pattern_head_coeffs: np.ndarray,
) -> np.ndarray:
    """The groups' best gem allocations (rows as in _score_fg_response_groups_native_f64), over CPU cores."""
    group_meta = np.ascontiguousarray(group_meta, dtype=np.int32)
    if int(np.unique(group_meta[:, 6]).shape[0]) != 1:
        raise ValueError("response frontier CPU group metadata has inconsistent head length")
    flags = color_flags(primary_color, secondary_color, selected_color)
    shared = (
        np.ascontiguousarray(surface_pattern_ids, dtype=np.int32),
        np.ascontiguousarray(surface_pattern_words, dtype=np.uint32),
        np.ascontiguousarray(surface_counts, dtype=np.int32),
        np.ascontiguousarray(surface_pattern_head_coeffs, dtype=np.int32),
        np.asarray(flags, dtype=np.int32),
        np.ascontiguousarray(curves.f64["Perfect Points"], dtype=np.float64),
        np.ascontiguousarray(curves.f64["Combo Multiplier"], dtype=np.float64),
        np.ascontiguousarray(curves.f64["Fever Multiplier"], dtype=np.float64),
        # PP gems raise Chill: only a Chill song can want them.
        bool(flags[0] or flags[1]),
        int(MAX_STAT),
    )
    rows = _score_fg_response_groups_on_cpu_cores(
        np.ascontiguousarray(group_offsets, dtype=np.int64),
        np.ascontiguousarray(group_lengths, dtype=np.int64),
        group_meta,
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
    shared_args: tuple[Any, ...],
) -> np.ndarray:
    """``_score_fg_response_groups_native_f64`` over contiguous group chunks on several cores.

    Chunks hold roughly equal surface rows (the search cost) and outnumber the workers so uneven groups still
    balance. Output rows come back in group order, identical to a single call.
    """
    group_count = int(group_meta.shape[0])
    chunk_count = min(
        _FG_CPU_SEARCH_WORKERS * _FG_CPU_SEARCH_CHUNKS_PER_WORKER,
        group_count // _FG_CPU_SEARCH_MIN_GROUPS_PER_CHUNK,
    )
    if _FG_CPU_SEARCH_WORKERS <= 1 or chunk_count <= 1:
        return _score_fg_response_groups_native_f64(group_offsets, group_lengths, group_meta, *shared_args)
    cumulative = np.cumsum(group_lengths, dtype=np.int64)
    targets = cumulative[-1] * np.arange(1, chunk_count, dtype=np.int64) // chunk_count
    cuts = np.unique(np.concatenate(([0], np.searchsorted(cumulative, targets, side="right"), [group_count])))
    futures = [
        _fg_cpu_search_executor().submit(
            _score_fg_response_groups_native_f64,
            group_offsets[start:stop],
            group_lengths[start:stop],
            group_meta[start:stop],
            *shared_args,
        )
        for start, stop in zip(cuts[:-1], cuts[1:])
        if stop > start
    ]
    return np.concatenate([future.result() for future in futures], axis=0)
