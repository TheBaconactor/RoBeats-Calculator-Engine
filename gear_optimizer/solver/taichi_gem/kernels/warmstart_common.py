"""Shared Taichi helpers for GA warmstart kernels."""

import taichi as ti

from ....rules import MAX_STAT
from . import kernels_helpers
from .kernels_helpers import GpuColorFlags
from .kernels_scoring import (
    optimize_core_device_exact_bound,
    response_score_upper_bound_relaxed,
)


@ti.func
def solve_combo_warmstart_preloaded(
    combo_idx: ti.i32,
    combo_budget: ti.i32,
    gem_scale_fever: ti.i32,
    flags: GpuColorFlags,
    song_slot: ti.i32,
    base_pp: ti.i32,
    base_cm: ti.i32,
    base_fm: ti.i32,
    base_p_val: ti.i32,
    base_s_val: ti.i32,
    base_ft_stat: ti.i32,
    base_ff_stat: ti.i32,
    score_cull_threshold: ti.i32,
) -> ti.types.vector(5, ti.i32):
    """(score, PP, CM, FM, element gems) of the best gem allocation spending combo combo_idx's FT/FF gems (a combo of
    the genome's key shortlist, none past MAX_STAT) on the genome's pre-gem stats; score -1 when the combo's relaxed
    upper bound is below score_cull_threshold."""
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    out_res = ti.Vector([ti.i32(-1), ti.i32(0), ti.i32(0), ti.i32(0), ti.i32(0)])

    ft: ti.i32 = kernels_helpers.ftff_combo_ft[combo_idx]
    ff: ti.i32 = kernels_helpers.ftff_combo_ff[combo_idx]
    ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, base_ft_stat + (ft * gem_scale_fever)))
    ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, base_ff_stat + (ff * gem_scale_fever)))
    body_total: ti.i32 = (
        kernels_helpers.grid_count_body_fever[song_slot, ft_idx, ff_idx]
        + kernels_helpers.grid_count_body_normal[song_slot, ft_idx, ff_idx]
    )
    head_len: ti.i32 = kernels_helpers.grid_head_len[song_slot, ft_idx, ff_idx]
    budget: ti.i32 = combo_budget - ft - ff
    p_val: ti.i32 = base_p_val + (ft * GEM_STAT_TO_ELEMENT * flags.is_p_ft) + (ff * GEM_STAT_TO_ELEMENT * flags.is_p_ff)
    s_val: ti.i32 = base_s_val + (ft * GEM_STAT_TO_ELEMENT * flags.is_s_ft) + (ff * GEM_STAT_TO_ELEMENT * flags.is_s_ff)

    pruned: ti.i32 = 0
    if score_cull_threshold > 0:
        ub_score = response_score_upper_bound_relaxed(
            budget,
            base_pp,
            base_cm,
            base_fm,
            p_val,
            s_val,
            flags,
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
            flags,
            head_len,
            song_slot,
            ft_idx,
            ff_idx,
            score_cull_threshold,
        )
        if res_vec[0] >= 0:
            # The exact solver already maximized over every retained timing variant.
            out_res = ti.Vector([res_vec[0], res_vec[1], res_vec[2], res_vec[3], res_vec[4]])
    return out_res
