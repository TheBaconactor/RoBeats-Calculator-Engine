"""Shared Taichi helpers for GA and skyline warmstart kernels."""

import taichi as ti

from . import kernels_helpers
from .kernels_scoring import (
    optimize_core_device_exact_bound,
    response_score_upper_bound_relaxed,
    score_solution_from_gems_preloaded,
)

MAX_STAT = 160  # gear_optimizer.core.constants.MAX_STAT_INDEX


@ti.func
def same_grid_sig(song_slot: ti.i32, sig0: ti.u64, sig1: ti.u64, ft_i: ti.i32, ff_i: ti.i32) -> ti.i32:
    same = ti.i32(0)
    frontier_count = ti.cast(kernels_helpers.grid_frontier_count[song_slot, ft_i, ff_i], ti.i32)
    if frontier_count <= 1:
        same = ti.cast(
            (kernels_helpers.grid_sig0[song_slot, ft_i, ff_i] == sig0)
            & (kernels_helpers.grid_sig1[song_slot, ft_i, ff_i] == sig1),
            ti.i32,
        )
    return same


@ti.func
def solve_combo_warmstart_preloaded(
    genome_idx: ti.i32,
    combo_idx: ti.i32,
    combo_budget: ti.i32,
    gem_scale_fever: ti.i32,
    is_p_ft: ti.i32,
    is_s_ft: ti.i32,
    is_p_ff: ti.i32,
    is_s_ff: ti.i32,
    is_p_pp: ti.i32,
    is_s_pp: ti.i32,
    is_p_cm: ti.i32,
    is_s_cm: ti.i32,
    is_p_fm: ti.i32,
    is_s_fm: ti.i32,
    is_p_ov: ti.i32,
    is_s_ov: ti.i32,
    song_slot: ti.i32,
    w_ft: ti.i32,
    w_ff: ti.i32,
    base_pp: ti.i32,
    base_cm: ti.i32,
    base_fm: ti.i32,
    base_p_val: ti.i32,
    base_s_val: ti.i32,
    base_ft_stat: ti.i32,
    base_ff_stat: ti.i32,
    max_ft_gems: ti.i32,
    max_ff_gems: ti.i32,
    prune_plateaus: ti.template(),
    use_exact_inner_solver: ti.template(),
    use_timing_response_antichain: ti.template(),
    score_cull_threshold: ti.i32,
) -> ti.types.vector(5, ti.i32):
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    out_res = ti.Vector([ti.i32(-1), ti.i32(0), ti.i32(0), ti.i32(0), ti.i32(0)])

    ft: ti.i32 = 0
    ff: ti.i32 = 0
    combo_valid: ti.i32 = 1
    if ti.static(use_timing_response_antichain):
        length = kernels_helpers.timing_response_genome_length[genome_idx]
        if combo_idx < length:
            table_idx = kernels_helpers.timing_response_genome_offset[genome_idx] + combo_idx
            ft = kernels_helpers.timing_response_combo_ft[table_idx]
            ff = kernels_helpers.timing_response_combo_ff[table_idx]
        else:
            combo_valid = 0
    else:
        ft = kernels_helpers.ftff_combo_ft[combo_idx]
        ff = kernels_helpers.ftff_combo_ff[combo_idx]

    if combo_valid != 0 and ft <= max_ft_gems and ff <= max_ff_gems:
        ft_stat_val: ti.i32 = base_ft_stat + (ft * gem_scale_fever)
        ff_stat_val: ti.i32 = base_ff_stat + (ff * gem_scale_fever)
        ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
        ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))

        pruned: ti.i32 = 0
        if ti.static(prune_plateaus):
            sig0 = kernels_helpers.grid_sig0[song_slot, ft_idx, ff_idx]
            sig1 = kernels_helpers.grid_sig1[song_slot, ft_idx, ff_idx]

            if pruned == 0 and w_ft == 0 and ft > 0:
                ft2 = ft - 1
                ff2 = ff
                if ff2 <= ti.min(combo_budget - ft2, max_ff_gems):
                    ft2_val = ft_stat_val - gem_scale_fever
                    ft2_idx = ti.min(MAX_STAT, ti.max(0, ft2_val))
                    if same_grid_sig(song_slot, sig0, sig1, ft2_idx, ff_idx) != 0:
                        pruned = 1

            if pruned == 0 and w_ff == 0 and ff > 0:
                ft2 = ft
                ff2 = ff - 1
                if ff2 <= ti.min(combo_budget - ft2, max_ff_gems):
                    ff2_val = ff_stat_val - gem_scale_fever
                    ff2_idx = ti.min(MAX_STAT, ti.max(0, ff2_val))
                    if same_grid_sig(song_slot, sig0, sig1, ft_idx, ff2_idx) != 0:
                        pruned = 1

            if pruned == 0 and w_ft > w_ff and ff > 0 and (ft + 1) <= max_ft_gems:
                ft2 = ft + 1
                ff2 = ff - 1
                if ff2 <= ti.min(combo_budget - ft2, max_ff_gems):
                    ft2_val = ft_stat_val + gem_scale_fever
                    ff2_val = ff_stat_val - gem_scale_fever
                    ft2_idx = ti.min(MAX_STAT, ti.max(0, ft2_val))
                    ff2_idx = ti.min(MAX_STAT, ti.max(0, ff2_val))
                    if same_grid_sig(song_slot, sig0, sig1, ft2_idx, ff2_idx) != 0:
                        pruned = 1

            if pruned == 0 and w_ff > w_ft and ft > 0 and (ff + 1) <= max_ff_gems:
                ft2 = ft - 1
                ff2 = ff + 1
                if ff2 <= ti.min(combo_budget - ft2, max_ff_gems):
                    ft2_val = ft_stat_val - gem_scale_fever
                    ff2_val = ff_stat_val + gem_scale_fever
                    ft2_idx = ti.min(MAX_STAT, ti.max(0, ft2_val))
                    ff2_idx = ti.min(MAX_STAT, ti.max(0, ff2_val))
                    if same_grid_sig(song_slot, sig0, sig1, ft2_idx, ff2_idx) != 0:
                        pruned = 1

            if pruned == 0 and w_ff == w_ft and w_ft != 0 and ft > 0 and (ff + 1) <= max_ff_gems:
                ft2 = ft - 1
                ff2 = ff + 1
                if ff2 <= ti.min(combo_budget - ft2, max_ff_gems):
                    ft2_val = ft_stat_val - gem_scale_fever
                    ff2_val = ff_stat_val + gem_scale_fever
                    ft2_idx = ti.min(MAX_STAT, ti.max(0, ft2_val))
                    ff2_idx = ti.min(MAX_STAT, ti.max(0, ff2_val))
                    if same_grid_sig(song_slot, sig0, sig1, ft2_idx, ff2_idx) != 0:
                        pruned = 1

        if pruned == 0:
            count_fever: ti.i32 = kernels_helpers.grid_count_body_fever[song_slot, ft_idx, ff_idx]
            count_normal: ti.i32 = kernels_helpers.grid_count_body_normal[song_slot, ft_idx, ff_idx]
            head_len: ti.i32 = kernels_helpers.grid_head_len[song_slot, ft_idx, ff_idx]
            budget: ti.i32 = combo_budget - ft - ff
            p_val: ti.i32 = base_p_val + (ft * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff * GEM_STAT_TO_ELEMENT * is_p_ff)
            s_val: ti.i32 = base_s_val + (ft * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff * GEM_STAT_TO_ELEMENT * is_s_ff)

            if score_cull_threshold > 0:
                ub_score = response_score_upper_bound_relaxed(
                    budget,
                    base_pp,
                    base_cm,
                    base_fm,
                    p_val,
                    s_val,
                    is_p_pp,
                    is_s_pp,
                    is_p_cm,
                    is_s_cm,
                    is_p_fm,
                    is_s_fm,
                    is_p_ov,
                    is_s_ov,
                    head_len,
                    count_fever,
                    count_normal,
                )
                if ub_score < ti.cast(score_cull_threshold, ti.f32):
                    pruned = 1

            if pruned == 0:
                res_vec = optimize_core_device_exact_bound(
                    budget,
                    base_pp,
                    base_cm,
                    base_fm,
                    p_val,
                    s_val,
                    is_p_pp,
                    is_s_pp,
                    is_p_cm,
                    is_s_cm,
                    is_p_fm,
                    is_s_fm,
                    is_p_ov,
                    is_s_ov,
                    head_len,
                    count_fever,
                    count_normal,
                    song_slot,
                    ft_idx,
                    ff_idx,
                )
                if res_vec[0] >= 0:
                    score = score_solution_from_gems_preloaded(
                        ft,
                        ff,
                        res_vec[1],
                        res_vec[2],
                        res_vec[3],
                        res_vec[4],
                        base_pp,
                        base_cm,
                        base_fm,
                        base_p_val,
                        base_s_val,
                        base_ft_stat,
                        base_ff_stat,
                        gem_scale_fever,
                        is_p_ft,
                        is_s_ft,
                        is_p_ff,
                        is_s_ff,
                        is_p_pp,
                        is_s_pp,
                        is_p_cm,
                        is_s_cm,
                        is_p_fm,
                        is_s_fm,
                        is_p_ov,
                        is_s_ov,
                        song_slot,
                        ft_idx,
                        ff_idx,
                        head_len,
                        count_fever,
                        count_normal,
                    )
                    out_res = ti.Vector([score, res_vec[1], res_vec[2], res_vec[3], res_vec[4]])
    return out_res
