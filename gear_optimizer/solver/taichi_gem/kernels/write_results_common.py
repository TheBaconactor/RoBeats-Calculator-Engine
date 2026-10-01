"""Shared Taichi helpers for GA and skyline result materialization."""

import taichi as ti

from . import kernels_helpers
from .kernels_helpers import GpuColorFlags
from .kernels_scoring import optimize_core_device_exact_bound, score_solution_from_gems_frontier


@ti.func
def score_combo_gems(
    genome_idx: ti.i32,
    ft: ti.i32,
    ff: ti.i32,
    pp_gems: ti.i32,
    cm_gems: ti.i32,
    fm_gems: ti.i32,
    ov_gems: ti.i32,
    gem_scale_fever: ti.i32,
    flags: GpuColorFlags,
    song_slot: ti.i32,
) -> ti.i32:
    """The exact score of genome_idx with (ft, ff) fever gems and the given PP/CM/FM/OV gem counts."""
    MAX_STAT: ti.i32 = 160

    stats = kernels_helpers.genome_base_stats[genome_idx]
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

    return score_solution_from_gems_frontier(
        ft,
        ff,
        pp_gems,
        cm_gems,
        fm_gems,
        ov_gems,
        base_pp,
        base_cm,
        base_fm,
        base_p_val,
        base_s_val,
        base_ft_stat,
        base_ff_stat,
        gem_scale_fever,
        flags,
        song_slot,
        ft_idx,
        ff_idx,
        head_len,
    )


@ti.func
def solve_best_combo_uncached(
    genome_idx: ti.i32,
    ft: ti.i32,
    ff: ti.i32,
    total_budget: ti.i32,
    gem_scale_fever: ti.i32,
    flags: GpuColorFlags,
    song_slot: ti.i32,
    rescore_result: ti.template(),
) -> ti.types.vector(5, ti.i32):
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160
    stats = kernels_helpers.genome_base_stats[genome_idx]
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
    p_val: ti.i32 = base_p_val + (ft * GEM_STAT_TO_ELEMENT * flags.is_p_ft) + (ff * GEM_STAT_TO_ELEMENT * flags.is_p_ff)
    s_val: ti.i32 = base_s_val + (ft * GEM_STAT_TO_ELEMENT * flags.is_s_ft) + (ff * GEM_STAT_TO_ELEMENT * flags.is_s_ff)
    budget: ti.i32 = total_budget - ft - ff
    res_vec = optimize_core_device_exact_bound(
        budget,
        base_pp,
        base_cm,
        base_fm,
        p_val,
        s_val,
        flags,
        head_len,
        song_slot,
        ft_idx,
        ff_idx,
    )
    score: ti.i32 = res_vec[0]
    if ti.static(rescore_result):
        score = -1
        if res_vec[0] >= 0:
            score = score_combo_gems(
                genome_idx, ft, ff, res_vec[1], res_vec[2], res_vec[3], res_vec[4], gem_scale_fever, flags, song_slot
            )
    return ti.Vector([score, res_vec[1], res_vec[2], res_vec[3], res_vec[4]])
