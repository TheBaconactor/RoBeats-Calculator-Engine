"""
Core scoring computation layer.

This module contains the "Compute Layer" - pure math functions that can be
ported to GPU (Taichi). These functions perform:
- Reference array lookups
- Score calculations
- Greedy gem optimization

GPU port only needs to reimplement these functions in Taichi.
"""

import numpy as np

from ..core.jit_setup import jit
from ..core.constants import (
    TOTAL_ROWS,
)


def lookup_reference_py(value, ref_array, total_rows=TOTAL_ROWS):
    """
    Python implementation of reference lookup.
    Clamps value to valid range and returns corresponding reference value.
    """
    clamped = max(0, min(total_rows, int(value)))
    return ref_array[clamped]


@jit(nopython=True, cache=True)
def lookup_reference_jit(value, ref_array, total_rows):
    """
    JIT-compiled reference lookup for performance.
    Used in hot paths where speed is critical.
    """
    idx = int(value)
    if idx > total_rows:
        idx = total_rows
    elif idx < 0:
        idx = 0
    return ref_array[idx]


@jit(nopython=True, cache=True)
def fast_calculate_score(
    base_value,
    combo_mul,
    fever_mul,
    fever_mask_head,
    count_body_fever,
    count_body_normal,
):
    """
    Fast JIT-compiled score calculation.

    NOTE: The old fever_activations_count adjustment has been REMOVED.
    The timeline calculation now correctly handles note allocation per fever cycle,
    so no adjustment is needed.

    Args:
        base_value: Base score value per note
        combo_mul: Combo multiplier
        fever_mul: Fever multiplier
        fever_mask_head: Boolean array marking fever notes in head (first 100)
        count_body_fever: Number of fever notes after head
        count_body_normal: Number of normal notes after head

    Returns:
        int: Total calculated score
    """
    # Force float32 math so CPU and GPU paths share identical numeric behavior.
    # This significantly reduces divergence from float64 boundary rounding.
    base_f = np.float32(base_value)
    combo_mul_f = np.float32(combo_mul)
    fever_mul_f = np.float32(fever_mul)

    # floor(x) for positive x is equivalent to int(x) truncation.
    combo_val_per_note = int(base_f * combo_mul_f)
    fever_val_per_note = int(base_f * combo_mul_f * fever_mul_f)

    body_score = (count_body_fever * fever_val_per_note) + (count_body_normal * combo_val_per_note)

    factor = (combo_mul_f - np.float32(1.0)) * base_f / np.float32(100.0)
    total_head = 0
    n_head = len(fever_mask_head)

    for i in range(n_head):
        current_ramp_val = base_f + (np.float32(i + 1) * factor)
        if fever_mask_head[i]:
            val = int(current_ramp_val * fever_mul_f)
        else:
            val = int(current_ramp_val)
        total_head += val

    return int(body_score + total_head)


@jit(nopython=True, cache=True)
def optimize_core_jit(
    budget,
    cur_pp,
    cur_cm,
    cur_fm,
    cur_p_val,
    cur_s_val,
    is_p_pp,
    is_s_pp,
    is_p_cm,
    is_s_cm,
    is_p_fm,
    is_s_fm,
    is_p_ov,
    is_s_ov,
    ref_pp,
    ref_cm,
    ref_fm,
    fever_mask_head,
    count_body_fever,
    count_body_normal,
    GEM_SCALE_NORMAL,
    GEM_SCALE_FEVER,
    GEM_STAT_TO_ELEMENT_SCALE,
    ELEMENTAL_GEM_SCALE,
    TOTAL_ROWS,
    MAX_STAT_INDEX,
):
    """
    JIT-compiled greedy gem allocation optimizer.

    At each iteration, evaluates 4 options (PP, CM, FM, Overflow) and picks
    the one that maximizes score. Continues until gem budget is exhausted.

    This is the performance-critical hot path and MUST be JIT-compiled.

    Returns:
        tuple: (final_pp, final_cm, final_fm, final_p_val, final_s_val,
                gems_pp, gems_cm, gems_fm, gems_ov)
    """
    gems_pp = 0
    gems_cm = 0
    gems_fm = 0
    gems_ov = 0
    remaining_budget = budget
    # Tie-breaking / secondary objective:
    # - Primary: maximize score
    # - Secondary (when scores tie): maximize Overflow (OV) usage
    #
    # IMPORTANT: Pure "prefer OV on ties" can prevent reaching score breakpoints that
    # require several PP gems (because early PP steps may tie). To address this,
    # we add a small lookahead: if PP ties with OV now but investing a few PP gems
    # would strictly improve score within the lookahead window, we still pick PP.
    PP_TIE_LOOKAHEAD_MAX = 8
    # CM can also have discrete breakpoint plateaus (multiplier lookup table + integer rounding),
    # where the first CM gem doesn't improve but a small streak of CM gems does.
    CM_LOOKAHEAD_MAX = 10

    while remaining_budget > 0:
        fill_budget = remaining_budget - 1
        fill_bonus = (fill_budget * ELEMENTAL_GEM_SCALE) if fill_budget > 0 else 0

        # Precompute multipliers for current CM/FM (unchanged for PP/OV checks)
        c_mul_cur = np.float32(lookup_reference_jit(cur_cm, ref_cm, TOTAL_ROWS))
        f_mul_cur = np.float32(lookup_reference_jit(cur_fm, ref_fm, TOTAL_ROWS))
        pp_factor_cur = np.float32(lookup_reference_jit(cur_pp, ref_pp, TOTAL_ROWS))

        # Start with OV as the default winner so OV wins exact ties.
        t_p = cur_p_val + (ELEMENTAL_GEM_SCALE * is_p_ov) + (fill_bonus * is_p_ov)
        t_s = cur_s_val + (ELEMENTAL_GEM_SCALE * is_s_ov) + (fill_bonus * is_s_ov)
        base = np.float32((t_p * 2) + t_s) + pp_factor_cur
        best_score = fast_calculate_score(
            base,
            c_mul_cur,
            f_mul_cur,
            fever_mask_head,
            count_body_fever,
            count_body_normal,
        )
        best_opt_idx = 3

        pp_score = -1
        fill_budget = remaining_budget - 1
        fill_bonus = (fill_budget * ELEMENTAL_GEM_SCALE) if fill_budget > 0 else 0

        # Option 0: PP gem
        # Optimization: Skip PP upgrades if Chill is not in Primary/Secondary (user request)
        allow_pp = (is_p_pp > 0) or (is_s_pp > 0)

        if allow_pp and cur_pp < MAX_STAT_INDEX:
            t_pp = cur_pp + GEM_SCALE_NORMAL
            t_p = cur_p_val + (GEM_STAT_TO_ELEMENT_SCALE * is_p_pp) + (fill_bonus * is_p_ov)
            t_s = cur_s_val + (GEM_STAT_TO_ELEMENT_SCALE * is_s_pp) + (fill_bonus * is_s_ov)
            pp_factor_pp = np.float32(lookup_reference_jit(t_pp, ref_pp, TOTAL_ROWS))
            base = np.float32((t_p * 2) + t_s) + pp_factor_pp
            pp_score = fast_calculate_score(
                base,
                c_mul_cur,
                f_mul_cur,
                fever_mask_head,
                count_body_fever,
                count_body_normal,
            )
            if pp_score > best_score:
                best_score = pp_score
                best_opt_idx = 0

        # Option 1: CM gem
        if cur_cm < MAX_STAT_INDEX and (cur_cm <= 50 or is_p_cm or is_s_cm):
            t_cm = cur_cm + GEM_SCALE_NORMAL
            t_p = cur_p_val + (GEM_STAT_TO_ELEMENT_SCALE * is_p_cm) + (fill_bonus * is_p_ov)
            t_s = cur_s_val + (GEM_STAT_TO_ELEMENT_SCALE * is_s_cm) + (fill_bonus * is_s_ov)
            base = np.float32((t_p * 2) + t_s) + pp_factor_cur
            c_mul = np.float32(lookup_reference_jit(t_cm, ref_cm, TOTAL_ROWS))
            score = fast_calculate_score(
                base,
                c_mul,
                f_mul_cur,
                fever_mask_head,
                count_body_fever,
                count_body_normal,
            )
            if score > best_score:
                best_score = score
                best_opt_idx = 1

        # Option 2: FM gem
        if cur_fm < MAX_STAT_INDEX:
            t_fm = cur_fm + GEM_SCALE_FEVER
            t_p = cur_p_val + (GEM_STAT_TO_ELEMENT_SCALE * is_p_fm) + (fill_bonus * is_p_ov)
            t_s = cur_s_val + (GEM_STAT_TO_ELEMENT_SCALE * is_s_fm) + (fill_bonus * is_s_ov)
            base = np.float32((t_p * 2) + t_s) + pp_factor_cur
            f_mul = np.float32(lookup_reference_jit(t_fm, ref_fm, TOTAL_ROWS))
            score = fast_calculate_score(
                base,
                c_mul_cur,
                f_mul,
                fever_mask_head,
                count_body_fever,
                count_body_normal,
            )
            if score > best_score:
                best_score = score
                best_opt_idx = 2

        # PP lookahead: if OV wins a tie *now*, but a few PP gems would break the tie
        # into a real improvement soon, start investing in PP.
        if allow_pp and best_opt_idx == 3 and pp_score == best_score and remaining_budget > 1:
            max_k = remaining_budget
            if max_k > PP_TIE_LOOKAHEAD_MAX:
                max_k = PP_TIE_LOOKAHEAD_MAX
            k = 2
            while k <= max_k:
                fill_bonus_k = (remaining_budget - k) * ELEMENTAL_GEM_SCALE
                t_pp = cur_pp + (k * GEM_SCALE_NORMAL)
                t_p = cur_p_val + (k * GEM_STAT_TO_ELEMENT_SCALE * is_p_pp) + (fill_bonus_k * is_p_ov)
                t_s = cur_s_val + (k * GEM_STAT_TO_ELEMENT_SCALE * is_s_pp) + (fill_bonus_k * is_s_ov)
                pp_factor = np.float32(lookup_reference_jit(t_pp, ref_pp, TOTAL_ROWS))
                base = np.float32((t_p * 2) + t_s) + pp_factor
                score_k = fast_calculate_score(
                    base,
                    c_mul_cur,
                    f_mul_cur,
                    fever_mask_head,
                    count_body_fever,
                    count_body_normal,
                )
                if score_k > best_score:
                    best_opt_idx = 0
                    break
                k += 1

        # CM lookahead: if OV wins now but investing a few CM gems would cross a breakpoint
        # and strictly improve score soon, start investing in CM.
        if (
            best_opt_idx == 3
            and remaining_budget > 1
            and cur_cm < MAX_STAT_INDEX
            and (cur_cm <= 50 or is_p_cm or is_s_cm)
        ):
            max_k = remaining_budget
            if max_k > CM_LOOKAHEAD_MAX:
                max_k = CM_LOOKAHEAD_MAX
            max_k_by_cap = (MAX_STAT_INDEX - cur_cm) // GEM_SCALE_NORMAL
            if max_k > max_k_by_cap:
                max_k = max_k_by_cap
            k = 2
            while k <= max_k:
                fill_bonus_k = (remaining_budget - k) * ELEMENTAL_GEM_SCALE
                t_cm = cur_cm + (k * GEM_SCALE_NORMAL)
                t_p = cur_p_val + (k * GEM_STAT_TO_ELEMENT_SCALE * is_p_cm) + (fill_bonus_k * is_p_ov)
                t_s = cur_s_val + (k * GEM_STAT_TO_ELEMENT_SCALE * is_s_cm) + (fill_bonus_k * is_s_ov)
                base = np.float32((t_p * 2) + t_s) + pp_factor_cur
                c_mul = np.float32(lookup_reference_jit(t_cm, ref_cm, TOTAL_ROWS))
                score_k = fast_calculate_score(
                    base,
                    c_mul,
                    f_mul_cur,
                    fever_mask_head,
                    count_body_fever,
                    count_body_normal,
                )
                if score_k > best_score:
                    best_opt_idx = 1
                    break
                k += 1

        # Apply the best option
        if best_opt_idx == 0:
            cur_pp += GEM_SCALE_NORMAL
            cur_p_val += GEM_STAT_TO_ELEMENT_SCALE * is_p_pp
            cur_s_val += GEM_STAT_TO_ELEMENT_SCALE * is_s_pp
            gems_pp += 1
        elif best_opt_idx == 1:
            cur_cm += GEM_SCALE_NORMAL
            cur_p_val += GEM_STAT_TO_ELEMENT_SCALE * is_p_cm
            cur_s_val += GEM_STAT_TO_ELEMENT_SCALE * is_s_cm
            gems_cm += 1
        elif best_opt_idx == 2:
            cur_fm += GEM_SCALE_FEVER
            cur_p_val += GEM_STAT_TO_ELEMENT_SCALE * is_p_fm
            cur_s_val += GEM_STAT_TO_ELEMENT_SCALE * is_s_fm
            gems_fm += 1
        else:
            cur_p_val += ELEMENTAL_GEM_SCALE * is_p_ov
            cur_s_val += ELEMENTAL_GEM_SCALE * is_s_ov
            gems_ov += 1
        remaining_budget -= 1

    return (
        cur_pp,
        cur_cm,
        cur_fm,
        cur_p_val,
        cur_s_val,
        gems_pp,
        gems_cm,
        gems_fm,
        gems_ov,
    )


@jit(nopython=True, cache=True)
def _ceil_div_pos_jit(n, d):
    if d <= 0:
        return 0
    if n <= 0:
        return 0
    return (n + d - 1) // d


@jit(nopython=True, cache=True)
def _head_mask_coefficients_jit(fever_mask_head):
    n_hn = 0
    n_hf = 0
    sigma_hn = 0
    sigma_hf = 0
    n_head = len(fever_mask_head)
    for i in range(n_head):
        pos = i + 1
        if fever_mask_head[i]:
            n_hf += 1
            sigma_hf += pos
        else:
            n_hn += 1
            sigma_hn += pos
    return n_hn, n_hf, sigma_hn, sigma_hf


@jit(nopython=True, cache=True)
def semi_exact_upper_bound_jit(
    base_value,
    combo_mul,
    fever_mul,
    count_body_fever,
    count_body_normal,
    n_hn,
    n_hf,
    sigma_hn,
    sigma_hf,
):
    base_f = np.float32(base_value)
    combo_mul_f = np.float32(combo_mul)
    fever_mul_f = np.float32(fever_mul)

    combo_val_per_note = int(base_f * combo_mul_f)
    fever_val_per_note = int(base_f * combo_mul_f * fever_mul_f)
    body_score = (count_body_fever * fever_val_per_note) + (count_body_normal * combo_val_per_note)

    factor = (combo_mul_f - np.float32(1.0)) * base_f / np.float32(100.0)
    head_upper = (
        base_f * (np.float32(n_hn) + (fever_mul_f * np.float32(n_hf)))
        + factor * (np.float32(sigma_hn) + (fever_mul_f * np.float32(sigma_hf)))
    )
    return np.float32(body_score) + head_upper


@jit(nopython=True, cache=True)
def optimize_core_exact_bounded_jit(
    budget,
    cur_pp,
    cur_cm,
    cur_fm,
    cur_p_val,
    cur_s_val,
    is_p_pp,
    is_s_pp,
    is_p_cm,
    is_s_cm,
    is_p_fm,
    is_s_fm,
    is_p_ov,
    is_s_ov,
    ref_pp,
    ref_cm,
    ref_fm,
    fever_mask_head,
    count_body_fever,
    count_body_normal,
    GEM_SCALE_NORMAL,
    GEM_SCALE_FEVER,
    GEM_STAT_TO_ELEMENT_SCALE,
    ELEMENTAL_GEM_SCALE,
    TOTAL_ROWS,
    MAX_STAT_INDEX,
):
    if budget <= 0:
        return (
            cur_pp,
            cur_cm,
            cur_fm,
            cur_p_val,
            cur_s_val,
            0,
            0,
            0,
            0,
        )

    (
        greedy_pp_stat,
        greedy_cm_stat,
        greedy_fm_stat,
        greedy_p_val,
        greedy_s_val,
        greedy_pp_gems,
        greedy_cm_gems,
        greedy_fm_gems,
        greedy_ov_gems,
    ) = optimize_core_jit(
        budget,
        cur_pp,
        cur_cm,
        cur_fm,
        cur_p_val,
        cur_s_val,
        is_p_pp,
        is_s_pp,
        is_p_cm,
        is_s_cm,
        is_p_fm,
        is_s_fm,
        is_p_ov,
        is_s_ov,
        ref_pp,
        ref_cm,
        ref_fm,
        fever_mask_head,
        count_body_fever,
        count_body_normal,
        GEM_SCALE_NORMAL,
        GEM_SCALE_FEVER,
        GEM_STAT_TO_ELEMENT_SCALE,
        ELEMENTAL_GEM_SCALE,
        TOTAL_ROWS,
        MAX_STAT_INDEX,
    )

    greedy_base = np.float32((greedy_p_val * 2) + greedy_s_val) + np.float32(
        lookup_reference_jit(greedy_pp_stat, ref_pp, TOTAL_ROWS)
    )
    greedy_c_mul = np.float32(lookup_reference_jit(greedy_cm_stat, ref_cm, TOTAL_ROWS))
    greedy_f_mul = np.float32(lookup_reference_jit(greedy_fm_stat, ref_fm, TOTAL_ROWS))
    best_score = fast_calculate_score(
        greedy_base,
        greedy_c_mul,
        greedy_f_mul,
        fever_mask_head,
        count_body_fever,
        count_body_normal,
    )

    best_pp_gems = greedy_pp_gems
    best_cm_gems = greedy_cm_gems
    best_fm_gems = greedy_fm_gems
    best_ov_gems = greedy_ov_gems
    best_p_val = greedy_p_val
    best_s_val = greedy_s_val

    n_hn, n_hf, sigma_hn, sigma_hf = _head_mask_coefficients_jit(fever_mask_head)

    allow_pp = (is_p_pp > 0) or (is_s_pp > 0)
    allow_cm_color = (is_p_cm > 0) or (is_s_cm > 0)

    if cur_pp >= MAX_STAT_INDEX or not allow_pp:
        max_pp_gems = 0
    else:
        max_pp_gems = _ceil_div_pos_jit(MAX_STAT_INDEX - cur_pp, GEM_SCALE_NORMAL)

    if cur_cm >= MAX_STAT_INDEX:
        max_cm_gems = 0
    elif allow_cm_color:
        max_cm_gems = _ceil_div_pos_jit(MAX_STAT_INDEX - cur_cm, GEM_SCALE_NORMAL)
    elif cur_cm > 50:
        max_cm_gems = 0
    else:
        max_cm_gems = ((50 - cur_cm) // GEM_SCALE_NORMAL) + 1

    if cur_fm >= MAX_STAT_INDEX:
        max_fm_gems = 0
    else:
        max_fm_gems = _ceil_div_pos_jit(MAX_STAT_INDEX - cur_fm, GEM_SCALE_FEVER)

    if max_pp_gems > budget:
        max_pp_gems = budget
    if max_cm_gems > budget:
        max_cm_gems = budget
    if max_fm_gems > budget:
        max_fm_gems = budget
    if max_pp_gems < 0:
        max_pp_gems = 0
    if max_cm_gems < 0:
        max_cm_gems = 0
    if max_fm_gems < 0:
        max_fm_gems = 0

    w_pp = GEM_STAT_TO_ELEMENT_SCALE * ((is_p_pp * 2) + is_s_pp)
    w_cm = GEM_STAT_TO_ELEMENT_SCALE * ((is_p_cm * 2) + is_s_cm)
    w_fm = GEM_STAT_TO_ELEMENT_SCALE * ((is_p_fm * 2) + is_s_fm)
    w_ov = ELEMENTAL_GEM_SCALE * ((is_p_ov * 2) + is_s_ov)
    base_init = (cur_p_val * 2) + cur_s_val

    for g_cm in range(max_cm_gems + 1):
        leftover_after_cm = budget - g_cm
        if leftover_after_cm < 0:
            break
        cm_stat = cur_cm + (g_cm * GEM_SCALE_NORMAL)
        c_mul = np.float32(lookup_reference_jit(cm_stat, ref_cm, TOTAL_ROWS))

        max_fm_here = max_fm_gems
        if max_fm_here > leftover_after_cm:
            max_fm_here = leftover_after_cm

        for g_fm in range(max_fm_here + 1):
            leftover = budget - g_cm - g_fm
            if leftover < 0:
                break

            fm_stat = cur_fm + (g_fm * GEM_SCALE_FEVER)
            f_mul = np.float32(lookup_reference_jit(fm_stat, ref_fm, TOTAL_ROWS))

            max_pp_here = max_pp_gems
            if max_pp_here > leftover:
                max_pp_here = leftover

            best_pp_extra = np.float32(lookup_reference_jit(cur_pp, ref_pp, TOTAL_ROWS))
            g_pp_best = 0
            delta_pp_vs_ov = w_pp - w_ov
            for g_pp in range(1, max_pp_here + 1):
                pp_stat = cur_pp + (g_pp * GEM_SCALE_NORMAL)
                pp_extra = np.float32(g_pp * delta_pp_vs_ov) + np.float32(
                    lookup_reference_jit(pp_stat, ref_pp, TOTAL_ROWS)
                )
                if pp_extra > best_pp_extra:
                    best_pp_extra = pp_extra
                    g_pp_best = g_pp

            g_ov = leftover - g_pp_best
            base_value = (
                np.float32(base_init + (g_cm * w_cm) + (g_fm * w_fm) + (leftover * w_ov))
                + best_pp_extra
            )
            ub = semi_exact_upper_bound_jit(
                base_value,
                c_mul,
                f_mul,
                count_body_fever,
                count_body_normal,
                n_hn,
                n_hf,
                sigma_hn,
                sigma_hf,
            )
            if ub <= np.float32(best_score):
                continue

            score = fast_calculate_score(
                base_value,
                c_mul,
                f_mul,
                fever_mask_head,
                count_body_fever,
                count_body_normal,
            )
            if score > best_score:
                best_score = score
                best_pp_gems = g_pp_best
                best_cm_gems = g_cm
                best_fm_gems = g_fm
                best_ov_gems = g_ov
                best_p_val = (
                    cur_p_val
                    + (g_pp_best * GEM_STAT_TO_ELEMENT_SCALE * is_p_pp)
                    + (g_cm * GEM_STAT_TO_ELEMENT_SCALE * is_p_cm)
                    + (g_fm * GEM_STAT_TO_ELEMENT_SCALE * is_p_fm)
                    + (g_ov * ELEMENTAL_GEM_SCALE * is_p_ov)
                )
                best_s_val = (
                    cur_s_val
                    + (g_pp_best * GEM_STAT_TO_ELEMENT_SCALE * is_s_pp)
                    + (g_cm * GEM_STAT_TO_ELEMENT_SCALE * is_s_cm)
                    + (g_fm * GEM_STAT_TO_ELEMENT_SCALE * is_s_fm)
                    + (g_ov * ELEMENTAL_GEM_SCALE * is_s_ov)
                )

    return (
        cur_pp + (best_pp_gems * GEM_SCALE_NORMAL),
        cur_cm + (best_cm_gems * GEM_SCALE_NORMAL),
        cur_fm + (best_fm_gems * GEM_SCALE_FEVER),
        best_p_val,
        best_s_val,
        best_pp_gems,
        best_cm_gems,
        best_fm_gems,
        best_ov_gems,
    )
