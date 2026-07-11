import taichi as ti

from gear_optimizer.core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
    MAX_STAT_INDEX,
    TOTAL_GEM_BUDGET,
)

from .response_inner_kernels import (
    FP,
    _fg_response_body_score_device,
    _fg_response_lookup_ref,
    _fg_response_pattern_result_is_better,
    _fg_response_score_device,
    _fg_response_surface_upper_bound,
)


@ti.kernel
def _fg_response_inner_pattern_batch_kernel(
    pair_count_total: ti.i32,
    surface_pattern_words: ti.types.ndarray(dtype=ti.u32, ndim=2),
    surface_counts: ti.types.ndarray(dtype=ti.i32, ndim=2),
    surface_pattern_head_coeffs: ti.types.ndarray(dtype=ti.i32, ndim=2),
    group_offsets: ti.types.ndarray(dtype=ti.i32, ndim=1),
    pair_owners: ti.types.ndarray(dtype=ti.i32, ndim=1),
    pair_pattern_ids: ti.types.ndarray(dtype=ti.i32, ndim=1),
    pair_surface_offsets: ti.types.ndarray(dtype=ti.i32, ndim=1),
    pair_local_surfaces: ti.types.ndarray(dtype=ti.i32, ndim=1),
    row_meta: ti.types.ndarray(dtype=ti.i32, ndim=2),
    color_flags: ti.types.ndarray(dtype=ti.i32, ndim=1),
    ref_pp: ti.types.ndarray(dtype=FP, ndim=1),
    ref_cm: ti.types.ndarray(dtype=FP, ndim=1),
    ref_fm: ti.types.ndarray(dtype=FP, ndim=1),
    out_scores: ti.types.ndarray(dtype=ti.i32, ndim=1),
    out_details: ti.types.ndarray(dtype=ti.i32, ndim=2),
    allow_pp_template: ti.template(),
):
    """Score one exact ``(owner, head-pattern)`` pair per GPU thread.

    All rows in a pair share the complete head input, so each allocation evaluates that head once.
    Body counts remain distinct, and original local-surface ordinals are compared explicitly before
    allocation order. The result is therefore independent of this pattern-major traversal order.
    """
    for pair_row in range(pair_count_total):
        owner: ti.i32 = pair_owners[pair_row]
        pattern_row: ti.i32 = pair_pattern_ids[pair_row]
        pair_start: ti.i32 = pair_surface_offsets[pair_row]
        pair_count: ti.i32 = pair_surface_offsets[pair_row + 1] - pair_start
        assert pair_count > 0
        surface_start: ti.i32 = group_offsets[owner]

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
        is_single_color: ti.i32 = color_flags[8]

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
        max_pp_gems = ti.min(max_pp_gems, residual_budget)
        max_cm_gems = ti.min(max_cm_gems, residual_budget)
        max_fm_gems = ti.min(max_fm_gems, residual_budget)

        w_pp: ti.i32 = (pp_p_delta << 1) + pp_s_delta
        w_cm: ti.i32 = (cm_p_delta << 1) + cm_s_delta
        w_fm: ti.i32 = (fm_p_delta << 1) + fm_s_delta
        w_ov: ti.i32 = (ov_p_delta << 1) + ov_s_delta
        delta_pp_vs_ov: ti.i32 = w_pp - w_ov
        pp_primary_delta: ti.i32 = pp_p_delta - ov_p_delta
        pp_secondary_delta: ti.i32 = pp_s_delta - ov_s_delta
        base_init: ti.i32 = (cur_primary << 1) + cur_secondary
        pp_ref_base: FP = _fg_response_lookup_ref(ref_pp, cur_pp)

        cm_ref_cache = ti.Vector.zero(FP, TOTAL_GEM_BUDGET + 1)
        fm_ref_cache = ti.Vector.zero(FP, TOTAL_GEM_BUDGET + 1)
        pp_ref_cache = ti.Vector.zero(FP, TOTAL_GEM_BUDGET + 1)
        pp_bound_prefix_max = ti.Vector.zero(FP, TOTAL_GEM_BUDGET + 1)
        if ti.static(allow_pp_template):
            g_pp_cache: ti.i32 = 0
            running_pp_bound_max: FP = FP(-1e30)
            while g_pp_cache <= max_pp_gems:
                pp_stat_cache: ti.i32 = cur_pp + g_pp_cache * GEM_SCALE_NORMAL
                pp_ref_val: FP = _fg_response_lookup_ref(ref_pp, pp_stat_cache)
                pp_ref_cache[g_pp_cache] = pp_ref_val
                pp_bound_val: FP = ti.cast(g_pp_cache * delta_pp_vs_ov, FP) + pp_ref_val
                if pp_bound_val > running_pp_bound_max:
                    running_pp_bound_max = pp_bound_val
                pp_bound_prefix_max[g_pp_cache] = running_pp_bound_max
                g_pp_cache += 1
        g_cm_cache: ti.i32 = 0
        while g_cm_cache <= max_cm_gems:
            cm_ref_cache[g_cm_cache] = _fg_response_lookup_ref(
                ref_cm, cur_cm + g_cm_cache * GEM_SCALE_NORMAL
            )
            g_cm_cache += 1
        g_fm_cache: ti.i32 = 0
        while g_fm_cache <= max_fm_gems:
            fm_ref_cache[g_fm_cache] = _fg_response_lookup_ref(
                ref_fm, cur_fm + g_fm_cache * GEM_SCALE_FEVER
            )
            g_fm_cache += 1

        fever0: ti.u32 = surface_pattern_words[pattern_row, 0]
        fever1: ti.u32 = surface_pattern_words[pattern_row, 1]
        fever2: ti.u32 = surface_pattern_words[pattern_row, 2]
        fever3: ti.u32 = surface_pattern_words[pattern_row, 3]
        great0: ti.u32 = surface_pattern_words[pattern_row, 4]
        great1: ti.u32 = surface_pattern_words[pattern_row, 5]
        great2: ti.u32 = surface_pattern_words[pattern_row, 6]
        great3: ti.u32 = surface_pattern_words[pattern_row, 7]
        n_hn: ti.i32 = surface_pattern_head_coeffs[pattern_row, 0]
        n_hf: ti.i32 = surface_pattern_head_coeffs[pattern_row, 1]
        sigma_hn: ti.i32 = surface_pattern_head_coeffs[pattern_row, 2]
        sigma_hf: ti.i32 = surface_pattern_head_coeffs[pattern_row, 3]

        best_score: ti.i32 = -1
        best_surface: ti.i32 = 0x7FFFFFFF
        best_pp: ti.i32 = 0
        best_cm: ti.i32 = 0
        best_fm: ti.i32 = 0
        best_ov: ti.i32 = residual_budget
        best_final_pp: ti.i32 = cur_pp
        best_final_cm: ti.i32 = cur_cm
        best_final_fm: ti.i32 = cur_fm
        best_final_primary: ti.i32 = cur_primary + best_ov * ov_p_delta
        best_final_secondary: ti.i32 = cur_secondary + best_ov * ov_s_delta

        g_cm: ti.i32 = 0
        while g_cm <= max_cm_gems:
            leftover_after_cm: ti.i32 = residual_budget - g_cm
            if leftover_after_cm < 0:
                break
            cm_stat: ti.i32 = cur_cm + g_cm * GEM_SCALE_NORMAL
            cm_mul: FP = cm_ref_cache[g_cm]
            g_fm_max: ti.i32 = ti.min(max_fm_gems, leftover_after_cm)
            g_fm: ti.i32 = 0
            while g_fm <= g_fm_max:
                leftover_after_fm: ti.i32 = leftover_after_cm - g_fm
                fm_stat: ti.i32 = cur_fm + g_fm * GEM_SCALE_FEVER
                fm_mul: FP = fm_ref_cache[g_fm]
                g_pp_max: ti.i32 = ti.min(max_pp_gems, leftover_after_fm)
                base_linear_common: ti.i32 = (
                    base_init
                    + g_cm * w_cm
                    + g_fm * w_fm
                    + leftover_after_fm * w_ov
                )
                max_base_value: FP = ti.cast(base_linear_common, FP) + pp_ref_base
                if ti.static(allow_pp_template):
                    max_base_value = (
                        ti.cast(base_linear_common, FP) + pp_bound_prefix_max[g_pp_max]
                    )

                pair_ub: FP = FP(-1e30)
                pair_pos: ti.i32 = 0
                while pair_pos < pair_count:
                    local_surface: ti.i32 = pair_local_surfaces[pair_start + pair_pos]
                    surface_row: ti.i32 = surface_start + local_surface
                    body_fever: ti.i32 = surface_counts[surface_row, 0]
                    body_normal: ti.i32 = ti.max(0, body_total - body_fever)
                    ub: FP = _fg_response_surface_upper_bound(
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
                    if ub > pair_ub:
                        pair_ub = ub
                    pair_pos += 1

                # Equality remains live because a tied score can carry an earlier surface ordinal.
                if pair_ub >= ti.cast(best_score, FP):
                    primary_base: ti.i32 = (
                        cur_primary
                        + g_cm * cm_p_delta
                        + g_fm * fm_p_delta
                        + leftover_after_fm * ov_p_delta
                    )
                    secondary_base: ti.i32 = (
                        cur_secondary
                        + g_cm * cm_s_delta
                        + g_fm * fm_s_delta
                        + leftover_after_fm * ov_s_delta
                    )
                    if ti.static(allow_pp_template):
                        if max_pp_gems > 0:
                            g_pp: ti.i32 = 0
                            while g_pp <= g_pp_max:
                                g_ov: ti.i32 = leftover_after_fm - g_pp
                                pp_stat: ti.i32 = cur_pp + g_pp * GEM_SCALE_NORMAL
                                primary_val: ti.i32 = primary_base + g_pp * pp_primary_delta
                                secondary_val: ti.i32 = (
                                    secondary_base + g_pp * pp_secondary_delta
                                )
                                pp_base_value: FP = (
                                    ti.cast(base_linear_common + g_pp * delta_pp_vs_ov, FP)
                                    + pp_ref_cache[g_pp]
                                )
                                pp_pair_ub: FP = FP(-1e30)
                                pair_pos = 0
                                while pair_pos < pair_count:
                                    local_surface = pair_local_surfaces[pair_start + pair_pos]
                                    surface_row = surface_start + local_surface
                                    body_fever = surface_counts[surface_row, 0]
                                    body_normal = ti.max(0, body_total - body_fever)
                                    ub = _fg_response_surface_upper_bound(
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
                                    if ub > pp_pair_ub:
                                        pp_pair_ub = ub
                                    pair_pos += 1
                                if pp_pair_ub >= ti.cast(best_score, FP):
                                    head_score: ti.i32 = _fg_response_score_device(
                                        fever0,
                                        fever1,
                                        fever2,
                                        fever3,
                                        great0,
                                        great1,
                                        great2,
                                        great3,
                                        0,
                                        0,
                                        0,
                                        head_len,
                                        0,
                                        primary_val,
                                        secondary_val,
                                        pp_ref_cache[g_pp],
                                        cm_mul,
                                        fm_mul,
                                        is_single_color,
                                    )
                                    pair_pos = 0
                                    while pair_pos < pair_count:
                                        local_surface = pair_local_surfaces[pair_start + pair_pos]
                                        surface_row = surface_start + local_surface
                                        score: ti.i32 = (
                                            head_score
                                            + _fg_response_body_score_device(
                                                surface_counts[surface_row, 0],
                                                surface_counts[surface_row, 1],
                                                surface_counts[surface_row, 2],
                                                body_total,
                                                primary_val,
                                                secondary_val,
                                                pp_ref_cache[g_pp],
                                                cm_mul,
                                                fm_mul,
                                                is_single_color,
                                            )
                                        )
                                        if _fg_response_pattern_result_is_better(
                                            score,
                                            local_surface,
                                            g_cm,
                                            g_fm,
                                            g_pp,
                                            best_score,
                                            best_surface,
                                            best_cm,
                                            best_fm,
                                            best_pp,
                                        ) != 0:
                                            best_score = score
                                            best_surface = local_surface
                                            best_pp = g_pp
                                            best_cm = g_cm
                                            best_fm = g_fm
                                            best_ov = g_ov
                                            best_final_pp = pp_stat
                                            best_final_cm = cm_stat
                                            best_final_fm = fm_stat
                                            best_final_primary = primary_val
                                            best_final_secondary = secondary_val
                                        pair_pos += 1
                                g_pp += 1
                        else:
                            head_score = _fg_response_score_device(
                                fever0,
                                fever1,
                                fever2,
                                fever3,
                                great0,
                                great1,
                                great2,
                                great3,
                                0,
                                0,
                                0,
                                head_len,
                                0,
                                primary_base,
                                secondary_base,
                                pp_ref_cache[0],
                                cm_mul,
                                fm_mul,
                                is_single_color,
                            )
                            pair_pos = 0
                            while pair_pos < pair_count:
                                local_surface = pair_local_surfaces[pair_start + pair_pos]
                                surface_row = surface_start + local_surface
                                score = head_score + _fg_response_body_score_device(
                                    surface_counts[surface_row, 0],
                                    surface_counts[surface_row, 1],
                                    surface_counts[surface_row, 2],
                                    body_total,
                                    primary_base,
                                    secondary_base,
                                    pp_ref_cache[0],
                                    cm_mul,
                                    fm_mul,
                                    is_single_color,
                                )
                                if _fg_response_pattern_result_is_better(
                                    score,
                                    local_surface,
                                    g_cm,
                                    g_fm,
                                    0,
                                    best_score,
                                    best_surface,
                                    best_cm,
                                    best_fm,
                                    best_pp,
                                ) != 0:
                                    best_score = score
                                    best_surface = local_surface
                                    best_pp = 0
                                    best_cm = g_cm
                                    best_fm = g_fm
                                    best_ov = leftover_after_fm
                                    best_final_pp = cur_pp
                                    best_final_cm = cm_stat
                                    best_final_fm = fm_stat
                                    best_final_primary = primary_base
                                    best_final_secondary = secondary_base
                                pair_pos += 1
                    else:
                        head_score = _fg_response_score_device(
                            fever0,
                            fever1,
                            fever2,
                            fever3,
                            great0,
                            great1,
                            great2,
                            great3,
                            0,
                            0,
                            0,
                            head_len,
                            0,
                            primary_base,
                            secondary_base,
                            pp_ref_base,
                            cm_mul,
                            fm_mul,
                            is_single_color,
                        )
                        pair_pos = 0
                        while pair_pos < pair_count:
                            local_surface = pair_local_surfaces[pair_start + pair_pos]
                            surface_row = surface_start + local_surface
                            score = head_score + _fg_response_body_score_device(
                                surface_counts[surface_row, 0],
                                surface_counts[surface_row, 1],
                                surface_counts[surface_row, 2],
                                body_total,
                                primary_base,
                                secondary_base,
                                pp_ref_base,
                                cm_mul,
                                fm_mul,
                                is_single_color,
                            )
                            if _fg_response_pattern_result_is_better(
                                score,
                                local_surface,
                                g_cm,
                                g_fm,
                                0,
                                best_score,
                                best_surface,
                                best_cm,
                                best_fm,
                                best_pp,
                            ) != 0:
                                best_score = score
                                best_surface = local_surface
                                best_pp = 0
                                best_cm = g_cm
                                best_fm = g_fm
                                best_ov = leftover_after_fm
                                best_final_pp = cur_pp
                                best_final_cm = cm_stat
                                best_final_fm = fm_stat
                                best_final_primary = primary_base
                                best_final_secondary = secondary_base
                            pair_pos += 1
                g_fm += 1
            g_cm += 1

        out_scores[pair_row] = best_score
        out_details[pair_row, 0] = best_surface
        out_details[pair_row, 1] = best_pp
        out_details[pair_row, 2] = best_cm
        out_details[pair_row, 3] = best_fm
        out_details[pair_row, 4] = best_ov
        out_details[pair_row, 5] = best_final_pp
        out_details[pair_row, 6] = best_final_cm
        out_details[pair_row, 7] = best_final_fm
        out_details[pair_row, 8] = best_final_primary
        out_details[pair_row, 9] = best_final_secondary
