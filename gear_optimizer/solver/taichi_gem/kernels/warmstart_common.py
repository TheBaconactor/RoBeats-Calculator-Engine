"""Shared Taichi helpers for GA and skyline warmstart kernels."""

import taichi as ti

from . import kernels_helpers
from .kernels_scoring import (
    optimize_core_device_exact_bound,
    response_score_upper_bound_relaxed,
    score_solution_from_gems_frontier,
)

MAX_STAT = 160  # gear_optimizer.core.constants.MAX_STAT_INDEX


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

        # Incumbent-based upper-bound cull (score_cull_threshold) is the only gate here;
        # the former timeline-plateau prune was removed (bit-exact but perf-neutral on
        # both GA and Skyline -- see docs/Implementation Records).
        pruned: ti.i32 = 0
        if pruned == 0:
            body_total: ti.i32 = (
                kernels_helpers.grid_count_body_fever[song_slot, ft_idx, ff_idx]
                + kernels_helpers.grid_count_body_normal[song_slot, ft_idx, ff_idx]
            )
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
                    body_total,
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
                    song_slot,
                    ft_idx,
                    ff_idx,
                )
                if res_vec[0] >= 0:
                    score = score_solution_from_gems_frontier(
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
                    )
                    out_res = ti.Vector([score, res_vec[1], res_vec[2], res_vec[3], res_vec[4]])
    return out_res
