"""
Core scoring computation layer.

This module contains the "Compute Layer" - pure math functions that can be
ported to GPU (Taichi). These functions perform:
- Reference array lookups
- Score calculations
- Greedy gem optimization

GPU port only needs to reimplement these functions in Taichi.
"""
from math import floor

from ..core.jit_setup import jit
from ..core.constants import (
    TOTAL_ROWS,
    MAX_STAT_INDEX,
    GEM_SCALE_NORMAL,
    GEM_SCALE_FEVER,
    GEM_STAT_TO_ELEMENT_SCALE,
    ELEMENTAL_GEM_SCALE,
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
    combo_val_per_note = floor(base_value * combo_mul)
    fever_val_per_note = floor(base_value * combo_mul * fever_mul)

    body_score = (count_body_fever * fever_val_per_note) + (
        count_body_normal * combo_val_per_note
    )

    # OLD PATCH REMOVED - no longer needed with corrected timeline

    factor = (combo_mul - 1) * base_value / 100.0
    total_head = 0.0
    n_head = len(fever_mask_head)

    for i in range(n_head):
        current_ramp_val = base_value + ((i + 1) * factor)
        if fever_mask_head[i]:
            val = floor(current_ramp_val * fever_mul)
        else:
            val = floor(current_ramp_val)
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

    while remaining_budget > 0:
        fill_budget = remaining_budget - 1
        fill_bonus = (fill_budget * ELEMENTAL_GEM_SCALE) if fill_budget > 0 else 0

        # Precompute multipliers for current CM/FM (unchanged for PP/OV checks)
        c_mul_cur = lookup_reference_jit(cur_cm, ref_cm, TOTAL_ROWS)
        f_mul_cur = lookup_reference_jit(cur_fm, ref_fm, TOTAL_ROWS)

        # Start with OV as the default winner so OV wins exact ties.
        t_p = cur_p_val + (ELEMENTAL_GEM_SCALE * is_p_ov) + (fill_bonus * is_p_ov)
        t_s = cur_s_val + (ELEMENTAL_GEM_SCALE * is_s_ov) + (fill_bonus * is_s_ov)
        pp_factor = lookup_reference_jit(cur_pp, ref_pp, TOTAL_ROWS)
        base = (t_p * 2) + t_s + pp_factor
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
        if cur_pp < MAX_STAT_INDEX:
            t_pp = cur_pp + GEM_SCALE_NORMAL
            t_p = cur_p_val + (GEM_STAT_TO_ELEMENT_SCALE * is_p_pp) + (
                fill_bonus * is_p_ov
            )
            t_s = cur_s_val + (GEM_STAT_TO_ELEMENT_SCALE * is_s_pp) + (
                fill_bonus * is_s_ov
            )
            pp_factor = lookup_reference_jit(t_pp, ref_pp, TOTAL_ROWS)
            base = (t_p * 2) + t_s + pp_factor
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
        if cur_cm < MAX_STAT_INDEX:
            t_cm = cur_cm + GEM_SCALE_NORMAL
            t_p = cur_p_val + (GEM_STAT_TO_ELEMENT_SCALE * is_p_cm) + (
                fill_bonus * is_p_ov
            )
            t_s = cur_s_val + (GEM_STAT_TO_ELEMENT_SCALE * is_s_cm) + (
                fill_bonus * is_s_ov
            )
            pp_factor = lookup_reference_jit(cur_pp, ref_pp, TOTAL_ROWS)
            base = (t_p * 2) + t_s + pp_factor
            c_mul = lookup_reference_jit(t_cm, ref_cm, TOTAL_ROWS)
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
            t_p = cur_p_val + (GEM_STAT_TO_ELEMENT_SCALE * is_p_fm) + (
                fill_bonus * is_p_ov
            )
            t_s = cur_s_val + (GEM_STAT_TO_ELEMENT_SCALE * is_s_fm) + (
                fill_bonus * is_s_ov
            )
            pp_factor = lookup_reference_jit(cur_pp, ref_pp, TOTAL_ROWS)
            base = (t_p * 2) + t_s + pp_factor
            f_mul = lookup_reference_jit(t_fm, ref_fm, TOTAL_ROWS)
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
        if (
            best_opt_idx == 3
            and pp_score == best_score
            and remaining_budget > 1
        ):
            max_k = remaining_budget
            if max_k > PP_TIE_LOOKAHEAD_MAX:
                max_k = PP_TIE_LOOKAHEAD_MAX
            k = 2
            while k <= max_k:
                fill_bonus_k = (remaining_budget - k) * ELEMENTAL_GEM_SCALE
                t_pp = cur_pp + (k * GEM_SCALE_NORMAL)
                t_p = cur_p_val + (k * GEM_STAT_TO_ELEMENT_SCALE * is_p_pp) + (
                    fill_bonus_k * is_p_ov
                )
                t_s = cur_s_val + (k * GEM_STAT_TO_ELEMENT_SCALE * is_s_pp) + (
                    fill_bonus_k * is_s_ov
                )
                pp_factor = lookup_reference_jit(t_pp, ref_pp, TOTAL_ROWS)
                base = (t_p * 2) + t_s + pp_factor
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
