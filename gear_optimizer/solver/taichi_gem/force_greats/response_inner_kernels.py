import sys

import numpy as np
import taichi as ti

from gear_optimizer.core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
    MAX_STAT_INDEX,
    TOTAL_GEM_BUDGET,
    TOTAL_ROWS,
)

# Hardware-gated solver fp for the FG response-inner gem search. The RX 7900 XTX (and any
# Vulkan device with shaderFloat64) runs the search in f64 -- its native mixed-precision
# form, bit-identical to today. MoltenVK/Metal (macOS) has no shaderFloat64, so the same
# kernel compiles at f32 there. This is a required-hardware-safety-boundary split (the only
# branch the canonical-path rule permits), mirroring the IS_METAL gate in runtime.py. The
# search only selects the argmax gem allocation; the served score is CPU-f64 exact-rescored,
# so the final score is lossless regardless of which fp the search ran at.
FP = ti.f32 if sys.platform == "darwin" else ti.f64
# The numpy dtype the host must feed the GPU kernel's ref arrays, kept in lockstep with FP
# (one gate). The CPU exact-rescore path stays float64 regardless.
SOLVER_NP_FP = np.float32 if sys.platform == "darwin" else np.float64


@ti.func
def _fg_response_lookup_ref(ref: ti.template(), idx: ti.i32) -> FP:
    safe_idx: ti.i32 = idx
    if safe_idx < 0:
        safe_idx = 0
    if safe_idx > TOTAL_ROWS:
        safe_idx = TOTAL_ROWS
    return ref[safe_idx]


@ti.func
def _fg_response_bit(word: ti.u32, bit_idx: ti.i32) -> ti.i32:
    return ti.cast((word >> ti.cast(bit_idx, ti.u32)) & ti.u32(1), ti.i32)


@ti.func
def _fg_response_head_score(
    base_value: FP,
    combo_slope: FP,
    fever_mul: FP,
    note_idx: ti.i32,
    is_fever: ti.i32,
) -> ti.i32:
    scaling: FP = combo_slope * ti.cast(note_idx + 1, FP) + FP(1.0)
    score: ti.i32 = ti.cast(ti.floor(base_value * scaling), ti.i32)
    if is_fever != 0:
        score = ti.cast(ti.floor(base_value * scaling * fever_mul), ti.i32)
    return score


@ti.func
def _fg_response_score_device(
    fever0: ti.u32,
    fever1: ti.u32,
    fever2: ti.u32,
    fever3: ti.u32,
    great0: ti.u32,
    great1: ti.u32,
    great2: ti.u32,
    great3: ti.u32,
    body_fever: ti.i32,
    body_great: ti.i32,
    body_fever_great: ti.i32,
    head_len: ti.i32,
    body_total: ti.i32,
    primary_val: ti.i32,
    secondary_val: ti.i32,
    pp_factor: FP,
    combo_mul: FP,
    fever_mul: FP,
) -> ti.i32:
    base_value: FP = ti.cast((primary_val * 2) + secondary_val, FP) + pp_factor
    combo_val: ti.i32 = ti.cast(ti.floor(base_value * combo_mul), ti.i32)
    fever_val: ti.i32 = ti.cast(ti.floor(base_value * combo_mul * fever_mul), ti.i32)
    body_normal: ti.i32 = body_total - body_fever
    if body_normal < 0:
        body_normal = 0
    score: ti.i32 = body_fever * fever_val + body_normal * combo_val

    combo_span: FP = combo_mul - FP(1.0)
    combo_slope: FP = combo_span / FP(100.0)
    n0 = ti.min(head_len, 32)
    for i in range(n0):
        score += _fg_response_head_score(
            base_value,
            combo_slope,
            fever_mul,
            i,
            _fg_response_bit(fever0, i),
        )
    if head_len > 32:
        n1 = ti.min(head_len, 64)
        for i in range(32, n1):
            score += _fg_response_head_score(
                base_value,
                combo_slope,
                fever_mul,
                i,
                _fg_response_bit(fever1, i - 32),
            )
    if head_len > 64:
        n2 = ti.min(head_len, 96)
        for i in range(64, n2):
            score += _fg_response_head_score(
                base_value,
                combo_slope,
                fever_mul,
                i,
                _fg_response_bit(fever2, i - 64),
            )
    if head_len > 96:
        for i in range(96, head_len):
            score += _fg_response_head_score(
                base_value,
                combo_slope,
                fever_mul,
                i,
                _fg_response_bit(fever3, i - 96),
            )

    great_bits: ti.u32 = great0 | great1 | great2 | great3
    if body_great > 0 or great_bits != ti.u32(0):
        great_head_base: ti.i32 = (
            ti.cast(ti.floor(ti.cast(primary_val, FP) * FP(4.0 / 3.0)), ti.i32)
            + ti.cast(ti.floor(ti.cast(secondary_val, FP) * FP(2.0 / 3.0)), ti.i32)
            + 150
        )
        great_base: FP = ti.cast(great_head_base, FP)
        great_combo_val: ti.i32 = ti.cast(ti.floor(great_base * combo_mul), ti.i32)
        great_fever_val: ti.i32 = ti.cast(ti.floor(great_base * combo_mul * fever_mul), ti.i32)
        if body_great > 0:
            body_normal_great: ti.i32 = body_great - body_fever_great
            if body_normal_great < 0:
                body_normal_great = 0
            body_normal_penalty: ti.i32 = combo_val - great_combo_val
            if body_normal_penalty < 0:
                body_normal_penalty = 0
            body_fever_penalty: ti.i32 = fever_val - great_fever_val
            if body_fever_penalty < 0:
                body_fever_penalty = 0
            score -= body_normal_great * body_normal_penalty
            score -= body_fever_great * body_fever_penalty

        if great_bits != ti.u32(0):
            for i in range(n0):
                if _fg_response_bit(great0, i) != 0:
                    is_fever: ti.i32 = _fg_response_bit(fever0, i)
                    perfect_val: ti.i32 = _fg_response_head_score(
                        base_value,
                        combo_slope,
                        fever_mul,
                        i,
                        is_fever,
                    )
                    great_val: ti.i32 = _fg_response_head_score(
                        great_base,
                        combo_slope,
                        fever_mul,
                        i,
                        is_fever,
                    )
                    penalty: ti.i32 = perfect_val - great_val
                    if penalty > 0:
                        score -= penalty
            if head_len > 32:
                for i in range(32, ti.min(head_len, 64)):
                    if _fg_response_bit(great1, i - 32) != 0:
                        is_fever: ti.i32 = _fg_response_bit(fever1, i - 32)
                        perfect_val: ti.i32 = _fg_response_head_score(
                            base_value,
                            combo_slope,
                            fever_mul,
                            i,
                            is_fever,
                        )
                        great_val: ti.i32 = _fg_response_head_score(
                            great_base,
                            combo_slope,
                            fever_mul,
                            i,
                            is_fever,
                        )
                        penalty: ti.i32 = perfect_val - great_val
                        if penalty > 0:
                            score -= penalty
            if head_len > 64:
                for i in range(64, ti.min(head_len, 96)):
                    if _fg_response_bit(great2, i - 64) != 0:
                        is_fever: ti.i32 = _fg_response_bit(fever2, i - 64)
                        perfect_val: ti.i32 = _fg_response_head_score(
                            base_value,
                            combo_slope,
                            fever_mul,
                            i,
                            is_fever,
                        )
                        great_val: ti.i32 = _fg_response_head_score(
                            great_base,
                            combo_slope,
                            fever_mul,
                            i,
                            is_fever,
                        )
                        penalty: ti.i32 = perfect_val - great_val
                        if penalty > 0:
                            score -= penalty
            if head_len > 96:
                for i in range(96, head_len):
                    if _fg_response_bit(great3, i - 96) != 0:
                        is_fever: ti.i32 = _fg_response_bit(fever3, i - 96)
                        perfect_val: ti.i32 = _fg_response_head_score(
                            base_value,
                            combo_slope,
                            fever_mul,
                            i,
                            is_fever,
                        )
                        great_val: ti.i32 = _fg_response_head_score(
                            great_base,
                            combo_slope,
                            fever_mul,
                            i,
                            is_fever,
                        )
                        penalty: ti.i32 = perfect_val - great_val
                        if penalty > 0:
                            score -= penalty
    return score


@ti.func
def _fg_response_surface_upper_bound(
    base_value: FP,
    combo_mul: FP,
    fever_mul: FP,
    body_fever: ti.i32,
    body_normal: ti.i32,
    n_hn: ti.i32,
    n_hf: ti.i32,
    sigma_hn: ti.i32,
    sigma_hf: ti.i32,
) -> FP:
    ub_eps = FP(1024.0)
    combo_val = ti.cast(ti.floor(base_value * combo_mul), ti.i32)
    fever_val = ti.cast(ti.floor(base_value * combo_mul * fever_mul), ti.i32)
    body_score = body_fever * fever_val + body_normal * combo_val
    factor = (combo_mul - FP(1.0)) * base_value / FP(100.0)
    head_upper = base_value * (ti.cast(n_hn, FP) + fever_mul * ti.cast(n_hf, FP)) + factor * (
        ti.cast(sigma_hn, FP) + fever_mul * ti.cast(sigma_hf, FP)
    )
    return ti.cast(body_score, FP) + head_upper + ub_eps


@ti.kernel
def _fg_response_inner_batch_kernel(
    row_count: ti.i32,
    surface_pattern_ids: ti.types.ndarray(dtype=ti.i32, ndim=1),
    surface_pattern_words: ti.types.ndarray(dtype=ti.u32, ndim=2),
    surface_counts: ti.types.ndarray(dtype=ti.i32, ndim=2),
    surface_pattern_head_coeffs: ti.types.ndarray(dtype=ti.i32, ndim=2),
    group_offsets: ti.types.ndarray(dtype=ti.i32, ndim=1),
    logical_owners: ti.types.ndarray(dtype=ti.i32, ndim=1),
    logical_surfaces: ti.types.ndarray(dtype=ti.i32, ndim=1),
    row_meta: ti.types.ndarray(dtype=ti.i32, ndim=2),
    color_flags: ti.types.ndarray(dtype=ti.i32, ndim=1),
    ref_pp: ti.types.ndarray(dtype=FP, ndim=1),
    ref_cm: ti.types.ndarray(dtype=FP, ndim=1),
    ref_fm: ti.types.ndarray(dtype=FP, ndim=1),
    out_scores: ti.types.ndarray(dtype=ti.i32, ndim=1),
    out_details: ti.types.ndarray(dtype=ti.i32, ndim=2),
    allow_pp_template: ti.template(),
):
    for row in range(row_count):
        owner: ti.i32 = logical_owners[row]
        local_surface: ti.i32 = logical_surfaces[row]
        surface_row: ti.i32 = group_offsets[owner] + local_surface
        residual_budget: ti.i32 = row_meta[owner, 0]
        cur_pp: ti.i32 = row_meta[owner, 1]
        cur_cm: ti.i32 = row_meta[owner, 2]
        cur_fm: ti.i32 = row_meta[owner, 3]
        cur_primary: ti.i32 = row_meta[owner, 4]
        cur_secondary: ti.i32 = row_meta[owner, 5]
        head_len: ti.i32 = row_meta[owner, 6]
        body_total: ti.i32 = row_meta[owner, 7]

        is_p_pp: ti.i32 = color_flags[0]
        is_s_pp: ti.i32 = color_flags[1]
        is_p_cm: ti.i32 = color_flags[2]
        is_s_cm: ti.i32 = color_flags[3]
        is_p_fm: ti.i32 = color_flags[4]
        is_s_fm: ti.i32 = color_flags[5]
        is_p_ov: ti.i32 = color_flags[6]
        is_s_ov: ti.i32 = color_flags[7]

        pp_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_p_pp
        pp_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_s_pp
        cm_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_p_cm
        cm_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_s_cm
        fm_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_p_fm
        fm_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_s_fm
        ov_p_delta: ti.i32 = ELEMENTAL_GEM_SCALE * is_p_ov
        ov_s_delta: ti.i32 = ELEMENTAL_GEM_SCALE * is_s_ov

        max_pp_gems: ti.i32 = 0
        if ti.static(allow_pp_template):
            if cur_pp < MAX_STAT_INDEX:
                rem_pp: ti.i32 = MAX_STAT_INDEX - cur_pp
                max_pp_gems = rem_pp // GEM_SCALE_NORMAL
                if rem_pp % GEM_SCALE_NORMAL != 0:
                    max_pp_gems += 1

        max_cm_gems: ti.i32 = 0
        if cur_cm < MAX_STAT_INDEX:
            rem_cm: ti.i32 = MAX_STAT_INDEX - cur_cm
            max_cm_gems = rem_cm // GEM_SCALE_NORMAL
            if rem_cm % GEM_SCALE_NORMAL != 0:
                max_cm_gems += 1

        max_fm_gems: ti.i32 = 0
        if cur_fm < MAX_STAT_INDEX:
            rem_fm: ti.i32 = MAX_STAT_INDEX - cur_fm
            max_fm_gems = rem_fm // GEM_SCALE_FEVER
            if rem_fm % GEM_SCALE_FEVER != 0:
                max_fm_gems += 1

        if max_pp_gems > residual_budget:
            max_pp_gems = residual_budget
        if max_cm_gems > residual_budget:
            max_cm_gems = residual_budget
        if max_fm_gems > residual_budget:
            max_fm_gems = residual_budget

        w_pp: ti.i32 = (pp_p_delta << 1) + pp_s_delta
        w_cm: ti.i32 = (cm_p_delta << 1) + cm_s_delta
        w_fm: ti.i32 = (fm_p_delta << 1) + fm_s_delta
        w_ov: ti.i32 = (ov_p_delta << 1) + ov_s_delta
        delta_pp_vs_ov: ti.i32 = w_pp - w_ov
        pp_primary_delta: ti.i32 = pp_p_delta - ov_p_delta
        pp_secondary_delta: ti.i32 = pp_s_delta - ov_s_delta
        base_init: ti.i32 = (cur_primary << 1) + cur_secondary
        pp_ref_base = _fg_response_lookup_ref(ref_pp, cur_pp)
        pp_bound_prefix_max = ti.Vector.zero(FP, TOTAL_GEM_BUDGET + 1)
        if ti.static(allow_pp_template):
            g_pp_cache: ti.i32 = 0
            running_pp_bound_max: FP = FP(-1e30)
            while g_pp_cache <= max_pp_gems:
                pp_stat_cache: ti.i32 = cur_pp + g_pp_cache * GEM_SCALE_NORMAL
                pp_ref_val: FP = _fg_response_lookup_ref(ref_pp, pp_stat_cache)
                pp_bound_val: FP = ti.cast(g_pp_cache * delta_pp_vs_ov, FP) + pp_ref_val
                if pp_bound_val > running_pp_bound_max:
                    running_pp_bound_max = pp_bound_val
                pp_bound_prefix_max[g_pp_cache] = running_pp_bound_max
                g_pp_cache += 1

        pattern_row: ti.i32 = surface_pattern_ids[surface_row]
        fever0: ti.u32 = surface_pattern_words[pattern_row, 0]
        fever1: ti.u32 = surface_pattern_words[pattern_row, 1]
        fever2: ti.u32 = surface_pattern_words[pattern_row, 2]
        fever3: ti.u32 = surface_pattern_words[pattern_row, 3]
        great0: ti.u32 = surface_pattern_words[pattern_row, 4]
        great1: ti.u32 = surface_pattern_words[pattern_row, 5]
        great2: ti.u32 = surface_pattern_words[pattern_row, 6]
        great3: ti.u32 = surface_pattern_words[pattern_row, 7]
        body_fever: ti.i32 = surface_counts[surface_row, 0]
        body_great: ti.i32 = surface_counts[surface_row, 1]
        body_fever_great: ti.i32 = surface_counts[surface_row, 2]

        best_score: ti.i32 = -1
        best_pp: ti.i32 = 0
        best_cm: ti.i32 = 0
        best_fm: ti.i32 = 0
        best_ov: ti.i32 = residual_budget
        best_final_pp: ti.i32 = cur_pp
        best_final_cm: ti.i32 = cur_cm
        best_final_fm: ti.i32 = cur_fm
        best_final_primary: ti.i32 = cur_primary + best_ov * ov_p_delta
        best_final_secondary: ti.i32 = cur_secondary + best_ov * ov_s_delta

        body_normal: ti.i32 = body_total - body_fever
        if body_normal < 0:
            body_normal = 0
        n_hn = surface_pattern_head_coeffs[pattern_row, 0]
        n_hf = surface_pattern_head_coeffs[pattern_row, 1]
        sigma_hn = surface_pattern_head_coeffs[pattern_row, 2]
        sigma_hf = surface_pattern_head_coeffs[pattern_row, 3]

        g_cm: ti.i32 = 0
        while g_cm <= max_cm_gems:
            leftover_after_cm: ti.i32 = residual_budget - g_cm
            if leftover_after_cm < 0:
                break
            cm_stat: ti.i32 = cur_cm + g_cm * GEM_SCALE_NORMAL
            cm_mul = _fg_response_lookup_ref(ref_cm, cm_stat)
            g_fm_max: ti.i32 = max_fm_gems
            if g_fm_max > leftover_after_cm:
                g_fm_max = leftover_after_cm
            g_fm: ti.i32 = 0
            while g_fm <= g_fm_max:
                leftover_after_fm: ti.i32 = leftover_after_cm - g_fm
                fm_stat: ti.i32 = cur_fm + g_fm * GEM_SCALE_FEVER
                fm_mul = _fg_response_lookup_ref(ref_fm, fm_stat)
                g_pp_max: ti.i32 = max_pp_gems
                if g_pp_max > leftover_after_fm:
                    g_pp_max = leftover_after_fm

                base_linear_common: ti.i32 = base_init + (g_cm * w_cm) + (g_fm * w_fm) + (leftover_after_fm * w_ov)
                max_base_value: FP = ti.cast(base_linear_common, FP) + pp_ref_base
                if ti.static(allow_pp_template):
                    max_base_value = ti.cast(base_linear_common, FP) + pp_bound_prefix_max[g_pp_max]
                ub = _fg_response_surface_upper_bound(
                    max_base_value,
                    cm_mul,
                    fm_mul,
                    body_fever,
                    body_normal,
                    n_hn,
                    n_hf,
                    sigma_hn,
                    sigma_hf,
                )

                if ub > ti.cast(best_score, FP):
                    primary_base: ti.i32 = (
                        cur_primary + g_cm * cm_p_delta + g_fm * fm_p_delta + leftover_after_fm * ov_p_delta
                    )
                    secondary_base: ti.i32 = (
                        cur_secondary + g_cm * cm_s_delta + g_fm * fm_s_delta + leftover_after_fm * ov_s_delta
                    )
                    if ti.static(allow_pp_template):
                        if max_pp_gems <= 0:
                            score: ti.i32 = _fg_response_score_device(
                                fever0,
                                fever1,
                                fever2,
                                fever3,
                                great0,
                                great1,
                                great2,
                                great3,
                                body_fever,
                                body_great,
                                body_fever_great,
                                head_len,
                                body_total,
                                primary_base,
                                secondary_base,
                                _fg_response_lookup_ref(ref_pp, cur_pp),
                                cm_mul,
                                fm_mul,
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
                        else:
                            g_pp: ti.i32 = 0
                            while g_pp <= g_pp_max:
                                g_ov: ti.i32 = leftover_after_fm - g_pp
                                pp_stat: ti.i32 = cur_pp + g_pp * GEM_SCALE_NORMAL
                                primary_val: ti.i32 = primary_base + g_pp * pp_primary_delta
                                secondary_val: ti.i32 = secondary_base + g_pp * pp_secondary_delta
                                pp_base_value: FP = ti.cast(
                                    base_linear_common + g_pp * delta_pp_vs_ov,
                                    FP,
                                ) + _fg_response_lookup_ref(ref_pp, pp_stat)
                                pp_ub = _fg_response_surface_upper_bound(
                                    pp_base_value,
                                    cm_mul,
                                    fm_mul,
                                    body_fever,
                                    body_normal,
                                    n_hn,
                                    n_hf,
                                    sigma_hn,
                                    sigma_hf,
                                )
                                should_score: ti.i32 = 1
                                if pp_ub < ti.cast(best_score, FP):
                                    should_score = 0
                                if should_score != 0:
                                    score = _fg_response_score_device(
                                        fever0,
                                        fever1,
                                        fever2,
                                        fever3,
                                        great0,
                                        great1,
                                        great2,
                                        great3,
                                        body_fever,
                                        body_great,
                                        body_fever_great,
                                        head_len,
                                        body_total,
                                        primary_val,
                                        secondary_val,
                                        _fg_response_lookup_ref(ref_pp, pp_stat),
                                        cm_mul,
                                        fm_mul,
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
                        score: ti.i32 = _fg_response_score_device(
                            fever0,
                            fever1,
                            fever2,
                            fever3,
                            great0,
                            great1,
                            great2,
                            great3,
                            body_fever,
                            body_great,
                            body_fever_great,
                            head_len,
                            body_total,
                            primary_base,
                            secondary_base,
                            pp_ref_base,
                            cm_mul,
                            fm_mul,
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

        out_scores[row] = best_score
        out_details[row, 0] = best_pp
        out_details[row, 1] = best_cm
        out_details[row, 2] = best_fm
        out_details[row, 3] = best_ov
        out_details[row, 4] = best_final_pp
        out_details[row, 5] = best_final_cm
        out_details[row, 6] = best_final_fm
        out_details[row, 7] = best_final_primary
        out_details[row, 8] = best_final_secondary

@ti.kernel
def _fg_response_inner_group_kernel(
    group_count: ti.i32,
    surface_pattern_ids: ti.types.ndarray(dtype=ti.i32, ndim=1),
    surface_pattern_words: ti.types.ndarray(dtype=ti.u32, ndim=2),
    surface_counts: ti.types.ndarray(dtype=ti.i32, ndim=2),
    surface_pattern_head_coeffs: ti.types.ndarray(dtype=ti.i32, ndim=2),
    group_offsets: ti.types.ndarray(dtype=ti.i32, ndim=1),
    group_lengths: ti.types.ndarray(dtype=ti.i32, ndim=1),
    row_meta: ti.types.ndarray(dtype=ti.i32, ndim=2),
    color_flags: ti.types.ndarray(dtype=ti.i32, ndim=1),
    ref_pp: ti.types.ndarray(dtype=FP, ndim=1),
    ref_cm: ti.types.ndarray(dtype=FP, ndim=1),
    ref_fm: ti.types.ndarray(dtype=FP, ndim=1),
    out_rows: ti.types.ndarray(dtype=ti.i32, ndim=2),
    allow_pp_template: ti.template(),
):
    for group in range(group_count):
        residual_budget: ti.i32 = row_meta[group, 0]
        cur_pp: ti.i32 = row_meta[group, 1]
        cur_cm: ti.i32 = row_meta[group, 2]
        cur_fm: ti.i32 = row_meta[group, 3]
        cur_primary: ti.i32 = row_meta[group, 4]
        cur_secondary: ti.i32 = row_meta[group, 5]
        head_len: ti.i32 = row_meta[group, 6]
        body_total: ti.i32 = row_meta[group, 7]

        is_p_pp: ti.i32 = color_flags[0]
        is_s_pp: ti.i32 = color_flags[1]
        is_p_cm: ti.i32 = color_flags[2]
        is_s_cm: ti.i32 = color_flags[3]
        is_p_fm: ti.i32 = color_flags[4]
        is_s_fm: ti.i32 = color_flags[5]
        is_p_ov: ti.i32 = color_flags[6]
        is_s_ov: ti.i32 = color_flags[7]

        pp_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_p_pp
        pp_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_s_pp
        cm_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_p_cm
        cm_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_s_cm
        fm_p_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_p_fm
        fm_s_delta: ti.i32 = GEM_STAT_TO_ELEMENT_SCALE * is_s_fm
        ov_p_delta: ti.i32 = ELEMENTAL_GEM_SCALE * is_p_ov
        ov_s_delta: ti.i32 = ELEMENTAL_GEM_SCALE * is_s_ov

        max_pp_gems: ti.i32 = 0
        if ti.static(allow_pp_template):
            if cur_pp < MAX_STAT_INDEX:
                rem_pp: ti.i32 = MAX_STAT_INDEX - cur_pp
                max_pp_gems = rem_pp // GEM_SCALE_NORMAL
                if rem_pp % GEM_SCALE_NORMAL != 0:
                    max_pp_gems += 1

        max_cm_gems: ti.i32 = 0
        if cur_cm < MAX_STAT_INDEX:
            rem_cm: ti.i32 = MAX_STAT_INDEX - cur_cm
            max_cm_gems = rem_cm // GEM_SCALE_NORMAL
            if rem_cm % GEM_SCALE_NORMAL != 0:
                max_cm_gems += 1

        max_fm_gems: ti.i32 = 0
        if cur_fm < MAX_STAT_INDEX:
            rem_fm: ti.i32 = MAX_STAT_INDEX - cur_fm
            max_fm_gems = rem_fm // GEM_SCALE_FEVER
            if rem_fm % GEM_SCALE_FEVER != 0:
                max_fm_gems += 1

        if max_pp_gems > residual_budget:
            max_pp_gems = residual_budget
        if max_cm_gems > residual_budget:
            max_cm_gems = residual_budget
        if max_fm_gems > residual_budget:
            max_fm_gems = residual_budget

        w_pp: ti.i32 = (pp_p_delta << 1) + pp_s_delta
        w_cm: ti.i32 = (cm_p_delta << 1) + cm_s_delta
        w_fm: ti.i32 = (fm_p_delta << 1) + fm_s_delta
        w_ov: ti.i32 = (ov_p_delta << 1) + ov_s_delta
        delta_pp_vs_ov: ti.i32 = w_pp - w_ov
        pp_primary_delta: ti.i32 = pp_p_delta - ov_p_delta
        pp_secondary_delta: ti.i32 = pp_s_delta - ov_s_delta
        base_init: ti.i32 = (cur_primary << 1) + cur_secondary
        pp_ref_base = _fg_response_lookup_ref(ref_pp, cur_pp)
        pp_bound_prefix_max = ti.Vector.zero(FP, TOTAL_GEM_BUDGET + 1)
        if ti.static(allow_pp_template):
            g_pp_cache: ti.i32 = 0
            running_pp_bound_max: FP = FP(-1e30)
            while g_pp_cache <= max_pp_gems:
                pp_stat_cache: ti.i32 = cur_pp + g_pp_cache * GEM_SCALE_NORMAL
                pp_ref_val: FP = _fg_response_lookup_ref(ref_pp, pp_stat_cache)
                pp_bound_val: FP = ti.cast(g_pp_cache * delta_pp_vs_ov, FP) + pp_ref_val
                if pp_bound_val > running_pp_bound_max:
                    running_pp_bound_max = pp_bound_val
                pp_bound_prefix_max[g_pp_cache] = running_pp_bound_max
                g_pp_cache += 1

        group_best_score: ti.i32 = -1
        group_best_surface: ti.i32 = 0
        group_best_pp: ti.i32 = 0
        group_best_cm: ti.i32 = 0
        group_best_fm: ti.i32 = 0
        group_best_ov: ti.i32 = residual_budget
        group_best_final_pp: ti.i32 = cur_pp
        group_best_final_cm: ti.i32 = cur_cm
        group_best_final_fm: ti.i32 = cur_fm
        group_best_final_primary: ti.i32 = cur_primary + group_best_ov * ov_p_delta
        group_best_final_secondary: ti.i32 = cur_secondary + group_best_ov * ov_s_delta

        start: ti.i32 = group_offsets[group]
        length: ti.i32 = group_lengths[group]
        local_surface: ti.i32 = 0
        while local_surface < length:
            surface_row: ti.i32 = start + local_surface
            pattern_row: ti.i32 = surface_pattern_ids[surface_row]
            fever0: ti.u32 = surface_pattern_words[pattern_row, 0]
            fever1: ti.u32 = surface_pattern_words[pattern_row, 1]
            fever2: ti.u32 = surface_pattern_words[pattern_row, 2]
            fever3: ti.u32 = surface_pattern_words[pattern_row, 3]
            great0: ti.u32 = surface_pattern_words[pattern_row, 4]
            great1: ti.u32 = surface_pattern_words[pattern_row, 5]
            great2: ti.u32 = surface_pattern_words[pattern_row, 6]
            great3: ti.u32 = surface_pattern_words[pattern_row, 7]
            body_fever: ti.i32 = surface_counts[surface_row, 0]
            body_great: ti.i32 = surface_counts[surface_row, 1]
            body_fever_great: ti.i32 = surface_counts[surface_row, 2]

            best_score: ti.i32 = group_best_score
            best_pp: ti.i32 = group_best_pp
            best_cm: ti.i32 = group_best_cm
            best_fm: ti.i32 = group_best_fm
            best_ov: ti.i32 = group_best_ov
            best_final_pp: ti.i32 = group_best_final_pp
            best_final_cm: ti.i32 = group_best_final_cm
            best_final_fm: ti.i32 = group_best_final_fm
            best_final_primary: ti.i32 = group_best_final_primary
            best_final_secondary: ti.i32 = group_best_final_secondary

            body_normal: ti.i32 = body_total - body_fever
            if body_normal < 0:
                body_normal = 0
            n_hn = surface_pattern_head_coeffs[pattern_row, 0]
            n_hf = surface_pattern_head_coeffs[pattern_row, 1]
            sigma_hn = surface_pattern_head_coeffs[pattern_row, 2]
            sigma_hf = surface_pattern_head_coeffs[pattern_row, 3]

            g_cm: ti.i32 = 0
            while g_cm <= max_cm_gems:
                leftover_after_cm: ti.i32 = residual_budget - g_cm
                if leftover_after_cm < 0:
                    break
                cm_stat: ti.i32 = cur_cm + g_cm * GEM_SCALE_NORMAL
                cm_mul = _fg_response_lookup_ref(ref_cm, cm_stat)
                g_fm_max: ti.i32 = max_fm_gems
                if g_fm_max > leftover_after_cm:
                    g_fm_max = leftover_after_cm
                g_fm: ti.i32 = 0
                while g_fm <= g_fm_max:
                    leftover_after_fm: ti.i32 = leftover_after_cm - g_fm
                    fm_stat: ti.i32 = cur_fm + g_fm * GEM_SCALE_FEVER
                    fm_mul = _fg_response_lookup_ref(ref_fm, fm_stat)
                    g_pp_max: ti.i32 = max_pp_gems
                    if g_pp_max > leftover_after_fm:
                        g_pp_max = leftover_after_fm

                    base_linear_common: ti.i32 = base_init + (g_cm * w_cm) + (g_fm * w_fm) + (leftover_after_fm * w_ov)
                    max_base_value: FP = ti.cast(base_linear_common, FP) + pp_ref_base
                    if ti.static(allow_pp_template):
                        max_base_value = ti.cast(base_linear_common, FP) + pp_bound_prefix_max[g_pp_max]
                    ub = _fg_response_surface_upper_bound(
                        max_base_value,
                        cm_mul,
                        fm_mul,
                        body_fever,
                        body_normal,
                        n_hn,
                        n_hf,
                        sigma_hn,
                        sigma_hf,
                    )

                    if ub > ti.cast(best_score, FP):
                        primary_base: ti.i32 = (
                            cur_primary + g_cm * cm_p_delta + g_fm * fm_p_delta + leftover_after_fm * ov_p_delta
                        )
                        secondary_base: ti.i32 = (
                            cur_secondary + g_cm * cm_s_delta + g_fm * fm_s_delta + leftover_after_fm * ov_s_delta
                        )
                        if ti.static(allow_pp_template):
                            if max_pp_gems <= 0:
                                score: ti.i32 = _fg_response_score_device(
                                    fever0,
                                    fever1,
                                    fever2,
                                    fever3,
                                    great0,
                                    great1,
                                    great2,
                                    great3,
                                    body_fever,
                                    body_great,
                                    body_fever_great,
                                    head_len,
                                    body_total,
                                    primary_base,
                                    secondary_base,
                                    _fg_response_lookup_ref(ref_pp, cur_pp),
                                    cm_mul,
                                    fm_mul,
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
                            else:
                                g_pp: ti.i32 = 0
                                while g_pp <= g_pp_max:
                                    g_ov: ti.i32 = leftover_after_fm - g_pp
                                    pp_stat: ti.i32 = cur_pp + g_pp * GEM_SCALE_NORMAL
                                    primary_val: ti.i32 = primary_base + g_pp * pp_primary_delta
                                    secondary_val: ti.i32 = secondary_base + g_pp * pp_secondary_delta
                                    pp_base_value: FP = ti.cast(
                                        base_linear_common + g_pp * delta_pp_vs_ov,
                                        FP,
                                    ) + _fg_response_lookup_ref(ref_pp, pp_stat)
                                    pp_ub = _fg_response_surface_upper_bound(
                                        pp_base_value,
                                        cm_mul,
                                        fm_mul,
                                        body_fever,
                                        body_normal,
                                        n_hn,
                                        n_hf,
                                        sigma_hn,
                                        sigma_hf,
                                    )
                                    should_score: ti.i32 = 1
                                    if pp_ub < ti.cast(best_score, FP):
                                        should_score = 0
                                    if should_score != 0:
                                        score = _fg_response_score_device(
                                            fever0,
                                            fever1,
                                            fever2,
                                            fever3,
                                            great0,
                                            great1,
                                            great2,
                                            great3,
                                            body_fever,
                                            body_great,
                                            body_fever_great,
                                            head_len,
                                            body_total,
                                            primary_val,
                                            secondary_val,
                                            _fg_response_lookup_ref(ref_pp, pp_stat),
                                            cm_mul,
                                            fm_mul,
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
                            score: ti.i32 = _fg_response_score_device(
                                fever0,
                                fever1,
                                fever2,
                                fever3,
                                great0,
                                great1,
                                great2,
                                great3,
                                body_fever,
                                body_great,
                                body_fever_great,
                                head_len,
                                body_total,
                                primary_base,
                                secondary_base,
                                pp_ref_base,
                                cm_mul,
                                fm_mul,
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
                group_best_surface = local_surface
                group_best_pp = best_pp
                group_best_cm = best_cm
                group_best_fm = best_fm
                group_best_ov = best_ov
                group_best_final_pp = best_final_pp
                group_best_final_cm = best_final_cm
                group_best_final_fm = best_final_fm
                group_best_final_primary = best_final_primary
                group_best_final_secondary = best_final_secondary
            local_surface += 1

        out_rows[group, 0] = group_best_score
        out_rows[group, 1] = group_best_surface
        out_rows[group, 2] = group_best_pp
        out_rows[group, 3] = group_best_cm
        out_rows[group, 4] = group_best_fm
        out_rows[group, 5] = group_best_ov
        out_rows[group, 6] = group_best_final_pp
        out_rows[group, 7] = group_best_final_cm
        out_rows[group, 8] = group_best_final_fm
        out_rows[group, 9] = group_best_final_primary
        out_rows[group, 10] = group_best_final_secondary
