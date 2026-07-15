"""Shared Taichi helpers for exact candidate result materialization."""

import taichi as ti

from . import kernels_helpers
from .kernels_scoring import optimize_core_device_exact_bound, score_solution_from_gems_frontier


@ti.func
def solve_best_combo_uncached(
    loadout_idx: ti.i32,
    ft: ti.i32,
    ff: ti.i32,
    total_budget: ti.i32,
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
    rescore_result: ti.template(),
) -> ti.types.vector(5, ti.i32):
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160
    stats = kernels_helpers.loadout_base_stats[loadout_idx]
    base_pp: ti.i32 = stats[0]
    base_cm: ti.i32 = stats[1]
    base_fm: ti.i32 = stats[2]
    base_p_val: ti.i32 = stats[3]
    base_s_val: ti.i32 = stats[4]
    base_ft_stat: ti.i32 = stats[5]
    base_ff_stat: ti.i32 = stats[6]
    ft_stat_val: ti.i32 = base_ft_stat + (ft * gem_scale_fever)
    ff_stat_val: ti.i32 = base_ff_stat + (ff * gem_scale_fever)
    ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
    ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))
    head_len: ti.i32 = kernels_helpers.grid_head_len[song_slot, ft_idx, ff_idx]
    p_val: ti.i32 = base_p_val + (ft * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff * GEM_STAT_TO_ELEMENT * is_p_ff)
    s_val: ti.i32 = base_s_val + (ft * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff * GEM_STAT_TO_ELEMENT * is_s_ff)
    budget: ti.i32 = total_budget - ft - ff
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
    score: ti.i32 = res_vec[0]
    if ti.static(rescore_result):
        score = -1
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
    return ti.Vector([score, res_vec[1], res_vec[2], res_vec[3], res_vec[4]])
