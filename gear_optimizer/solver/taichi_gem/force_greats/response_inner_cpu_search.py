"""Canonical CPU (native-f64, numba) FG response gem-search.

This is the CPU twin of the GPU `_fg_response_inner_group_kernel` gem-budget search. It is a
native-f64 transcription (same ops, same order, native doubles), so it is bit-for-bit identical
to the GPU f64 kernel by construction. It handles BOTH the gems-fixed replay (residual_budget==0,
the search collapses to scoring each surface once) AND the lossless-exact re-solve
(residual_budget>0). Used on the serving host (macOS/MoltenVK), where the GPU cannot run native
f64; the offline GA keeps the GPU path on f64-capable hardware (AMD RX 7900 XTX).

Validated bit-exact vs the canonical f64 kernel over random groups (budgets 0 and 3); see
`tests/test_fg_cpu_search_parity.py`. No upper-bound pruning here (it would only speed the search,
never change the exact argmax): the on-demand re-solve set is small and cached.
"""
import math

import numpy as np

from gear_optimizer.core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
    MAX_STAT_INDEX,
    TOTAL_ROWS,
)
from gear_optimizer.core.jit_setup import jit


@jit(nopython=True, cache=True)
def _bit(words, base_idx, i):
    return (words[base_idx + (i >> 5)] >> (i & 31)) & 1


@jit(nopython=True, cache=True)
def _head_score(base_value, combo_slope, fever_mul, note_idx, is_fever):
    scaling = combo_slope * float(note_idx + 1) + 1.0
    if is_fever != 0:
        return int(math.floor(base_value * scaling * fever_mul))
    return int(math.floor(base_value * scaling))


@jit(nopython=True, cache=True)
def _score_device(fw, gw, body_fever, body_great, body_fever_great, head_len, body_total,
                  primary_val, secondary_val, pp_factor, combo_mul, fever_mul, is_single_color):
    base_value = float((primary_val * 2) + secondary_val) + pp_factor
    combo_val = int(math.floor(base_value * combo_mul))
    fever_val = int(math.floor(base_value * combo_mul * fever_mul))
    body_normal = body_total - body_fever
    if body_normal < 0:
        body_normal = 0
    score = body_fever * fever_val + body_normal * combo_val
    combo_slope = (combo_mul - 1.0) / 100.0
    for i in range(head_len):
        score += _head_score(base_value, combo_slope, fever_mul, i, _bit(fw, 0, i))
    great_bits = gw[0] | gw[1] | gw[2] | gw[3]
    if body_great > 0 or great_bits != 0:
        if is_single_color != 0:
            great_head_base = (primary_val * 2) + 150
        else:
            great_head_base = (int(math.floor(primary_val * (4.0 / 3.0)))
                               + int(math.floor(secondary_val * (2.0 / 3.0))) + 150)
        great_base = float(great_head_base)
        great_combo_val = int(math.floor(great_base * combo_mul))
        great_fever_val = int(math.floor(great_base * combo_mul * fever_mul))
        if body_great > 0:
            body_normal_great = body_great - body_fever_great
            if body_normal_great < 0:
                body_normal_great = 0
            bnp = combo_val - great_combo_val
            if bnp < 0:
                bnp = 0
            bfp = fever_val - great_fever_val
            if bfp < 0:
                bfp = 0
            score -= body_normal_great * bnp
            score -= body_fever_great * bfp
        if great_bits != 0:
            for i in range(head_len):
                if _bit(gw, 0, i) != 0:
                    isf = _bit(fw, 0, i)
                    pen = (_head_score(base_value, combo_slope, fever_mul, i, isf)
                           - _head_score(great_base, combo_slope, fever_mul, i, isf))
                    if pen > 0:
                        score -= pen
    return score


@jit(nopython=True, cache=True)
def _ref(ref, idx):
    s = idx
    if s < 0:
        s = 0
    if s > TOTAL_ROWS:
        s = TOTAL_ROWS
    return ref[s]


@jit(nopython=True, cache=True)
def resolve_fg_response_groups_native_f64(group_offsets, group_lengths, row_meta,
                                          surface_words, surface_counts, color_flags,
                                          ref_pp, ref_cm, ref_fm, allow_pp):
    """Per group: search gem allocations (residual_budget) x candidate surfaces under the active
    color config and keep the exact argmax. residual_budget==0 collapses to scoring each surface
    at the current stats (the replay). Returns out[group, 11]:
    [best_score, best_surface, g_pp, g_cm, g_fm, g_ov, final_pp, final_cm, final_fm,
     final_primary, final_secondary]."""
    group_count = int(row_meta.shape[0])
    out = np.zeros((group_count, 11), dtype=np.int64)

    is_p_pp = int(color_flags[0]); is_s_pp = int(color_flags[1])
    is_p_cm = int(color_flags[2]); is_s_cm = int(color_flags[3])
    is_p_fm = int(color_flags[4]); is_s_fm = int(color_flags[5])
    is_p_ov = int(color_flags[6]); is_s_ov = int(color_flags[7])
    is_single_color = int(color_flags[8])

    pp_p_delta = GEM_STAT_TO_ELEMENT_SCALE * is_p_pp
    pp_s_delta = GEM_STAT_TO_ELEMENT_SCALE * is_s_pp
    cm_p_delta = GEM_STAT_TO_ELEMENT_SCALE * is_p_cm
    cm_s_delta = GEM_STAT_TO_ELEMENT_SCALE * is_s_cm
    fm_p_delta = GEM_STAT_TO_ELEMENT_SCALE * is_p_fm
    fm_s_delta = GEM_STAT_TO_ELEMENT_SCALE * is_s_fm
    ov_p_delta = ELEMENTAL_GEM_SCALE * is_p_ov
    ov_s_delta = ELEMENTAL_GEM_SCALE * is_s_ov
    w_cm = (cm_p_delta << 1) + cm_s_delta
    w_fm = (fm_p_delta << 1) + fm_s_delta
    w_ov = (ov_p_delta << 1) + ov_s_delta
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
        if allow_pp != 0 and cur_pp < MAX_STAT_INDEX:
            rem_pp = MAX_STAT_INDEX - cur_pp
            max_pp_gems = rem_pp // GEM_SCALE_NORMAL
            if rem_pp % GEM_SCALE_NORMAL != 0:
                max_pp_gems += 1
        max_cm_gems = 0
        if cur_cm < MAX_STAT_INDEX:
            rem_cm = MAX_STAT_INDEX - cur_cm
            max_cm_gems = rem_cm // GEM_SCALE_NORMAL
            if rem_cm % GEM_SCALE_NORMAL != 0:
                max_cm_gems += 1
        max_fm_gems = 0
        if cur_fm < MAX_STAT_INDEX:
            rem_fm = MAX_STAT_INDEX - cur_fm
            max_fm_gems = rem_fm // GEM_SCALE_FEVER
            if rem_fm % GEM_SCALE_FEVER != 0:
                max_fm_gems += 1
        if max_pp_gems > residual_budget:
            max_pp_gems = residual_budget
        if max_cm_gems > residual_budget:
            max_cm_gems = residual_budget
        if max_fm_gems > residual_budget:
            max_fm_gems = residual_budget

        pp_ref_base = _ref(ref_pp, cur_pp)

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
        for local_surface in range(length):
            sr = start + local_surface
            fw = surface_words[sr, 0:4]
            gw = surface_words[sr, 4:8]
            body_fever = int(surface_counts[sr, 0])
            body_great = int(surface_counts[sr, 1])
            body_fever_great = int(surface_counts[sr, 2])

            best_score = group_best_score
            best_pp = group_best_pp; best_cm = group_best_cm; best_fm = group_best_fm
            best_ov = group_best_ov
            best_final_pp = group_best_final_pp; best_final_cm = group_best_final_cm
            best_final_fm = group_best_final_fm; best_final_primary = group_best_final_primary
            best_final_secondary = group_best_final_secondary

            g_cm = 0
            while g_cm <= max_cm_gems:
                leftover_after_cm = residual_budget - g_cm
                if leftover_after_cm < 0:
                    break
                cm_stat = cur_cm + g_cm * GEM_SCALE_NORMAL
                cm_mul = _ref(ref_cm, cm_stat)
                g_fm_max = max_fm_gems
                if g_fm_max > leftover_after_cm:
                    g_fm_max = leftover_after_cm
                g_fm = 0
                while g_fm <= g_fm_max:
                    leftover_after_fm = leftover_after_cm - g_fm
                    fm_stat = cur_fm + g_fm * GEM_SCALE_FEVER
                    fm_mul = _ref(ref_fm, fm_stat)
                    g_pp_max = max_pp_gems
                    if g_pp_max > leftover_after_fm:
                        g_pp_max = leftover_after_fm
                    primary_base = cur_primary + g_cm * cm_p_delta + g_fm * fm_p_delta + leftover_after_fm * ov_p_delta
                    secondary_base = cur_secondary + g_cm * cm_s_delta + g_fm * fm_s_delta + leftover_after_fm * ov_s_delta
                    if allow_pp != 0 and max_pp_gems > 0:
                        g_pp = 0
                        while g_pp <= g_pp_max:
                            g_ov = leftover_after_fm - g_pp
                            pp_stat = cur_pp + g_pp * GEM_SCALE_NORMAL
                            primary_val = primary_base + g_pp * pp_primary_delta
                            secondary_val = secondary_base + g_pp * pp_secondary_delta
                            pp_factor = _ref(ref_pp, pp_stat)
                            score = _score_device(fw, gw, body_fever, body_great, body_fever_great,
                                                  head_len, body_total, primary_val, secondary_val,
                                                  pp_factor, cm_mul, fm_mul, is_single_color)
                            if score > best_score or (score == best_score and (g_cm < best_cm or (g_cm == best_cm and (g_fm < best_fm or (g_fm == best_fm and g_pp < best_pp))))):
                                best_score = score; best_pp = g_pp; best_cm = g_cm; best_fm = g_fm; best_ov = g_ov
                                best_final_pp = pp_stat; best_final_cm = cm_stat; best_final_fm = fm_stat
                                best_final_primary = primary_val; best_final_secondary = secondary_val
                            g_pp += 1
                    else:
                        score = _score_device(fw, gw, body_fever, body_great, body_fever_great,
                                              head_len, body_total, primary_base, secondary_base,
                                              pp_ref_base, cm_mul, fm_mul, is_single_color)
                        if score > best_score or (score == best_score and (g_cm < best_cm or (g_cm == best_cm and (g_fm < best_fm or (g_fm == best_fm and 0 < best_pp))))):
                            best_score = score; best_pp = 0; best_cm = g_cm; best_fm = g_fm; best_ov = leftover_after_fm
                            best_final_pp = cur_pp; best_final_cm = cm_stat; best_final_fm = fm_stat
                            best_final_primary = primary_base; best_final_secondary = secondary_base
                    g_fm += 1
                g_cm += 1

            if best_score > group_best_score:
                group_best_score = best_score; group_best_surface = local_surface
                group_best_pp = best_pp; group_best_cm = best_cm; group_best_fm = best_fm; group_best_ov = best_ov
                group_best_final_pp = best_final_pp; group_best_final_cm = best_final_cm
                group_best_final_fm = best_final_fm; group_best_final_primary = best_final_primary
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
