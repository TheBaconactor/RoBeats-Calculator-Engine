"""
Taichi Kernels - GA FT/FF combo search.

Includes:
- ga_find_best_combo_key_kernel
"""

import sys

import taichi as ti

from .. import kernels_helpers
from ..kernels_scoring import optimize_core_device

# Platform detection for atomic operations
IS_METAL = sys.platform == "darwin"


@ti.kernel
def ga_find_best_combo_key_kernel(
    n_genomes: ti.i32,
    n_combos: ti.i32,
    combo_offset: ti.i32,
    combo_count: ti.i32,
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
):
    """
    GPU-parallel evaluation across (genome, ft/ff combo) without materializing work_items.

    This kernel performs FT/FF combo search inline on the GPU, avoiding the overhead
    of transferring work item data. It uses the precomputed timeline grid for O(1) lookups.

    Writes best key per genome into chunk_best_key:
      key = ((score + 1) << 32) | combo_idx

    Args:
        n_genomes: Number of genomes to evaluate
        n_combos: Total number of FT/FF combinations
        combo_offset: Starting index in combo tables (for chunked processing)
        combo_count: Number of combos in this chunk
        total_budget: Total gem budget
        gem_scale_fever: Gems per fever stat point
        is_*: Color contribution flags (0/1)
        song_slot: Grid slot for batch coalescing
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160

    for genome_idx, local_c in ti.ndrange(n_genomes, combo_count):
        combo_idx: ti.i32 = combo_offset + local_c
        if combo_idx >= n_combos:
            continue

        ft: ti.i32 = kernels_helpers.ftff_combo_ft[combo_idx]
        ff: ti.i32 = kernels_helpers.ftff_combo_ff[combo_idx]

        # Skip combos outside budget (defensive, should not happen if tables match total_budget).
        if ft + ff > total_budget:
            continue

        # Load genome base stats: [pp, cm, fm, p_val, s_val, ft, ff]
        stats = kernels_helpers.genome_base_stats[genome_idx]
        base_pp: ti.i32 = stats[0]
        base_cm: ti.i32 = stats[1]
        base_fm: ti.i32 = stats[2]
        base_p_val: ti.i32 = stats[3]
        base_s_val: ti.i32 = stats[4]
        base_ft_stat: ti.i32 = stats[5]
        base_ff_stat: ti.i32 = stats[6]

        # Per-genome FT/FF headroom (match solve_genomes_with_ftff_kernel).
        remaining_ft: ti.i32 = MAX_STAT - base_ft_stat
        remaining_ff: ti.i32 = MAX_STAT - base_ff_stat
        max_ft_gems: ti.i32 = remaining_ft // gem_scale_fever if remaining_ft > 0 else 0
        max_ff_gems: ti.i32 = remaining_ff // gem_scale_fever if remaining_ff > 0 else 0
        if max_ft_gems > total_budget:
            max_ft_gems = total_budget
        if max_ff_gems > total_budget:
            max_ff_gems = total_budget

        if ft > max_ft_gems:
            continue
        if ff > ti.min(total_budget - ft, max_ff_gems):
            continue

        # Stat indices for grid lookup (clamped).
        ft_stat_val: ti.i32 = base_ft_stat + (ft * gem_scale_fever)
        ff_stat_val: ti.i32 = base_ff_stat + (ff * gem_scale_fever)
        ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
        ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))

        # O(1) lookup from timeline grid using song_slot.
        count_fever: ti.i32 = kernels_helpers.grid_count_body_fever[song_slot, ft_idx, ff_idx]
        count_normal: ti.i32 = kernels_helpers.grid_count_body_normal[song_slot, ft_idx, ff_idx]
        head_len: ti.i32 = kernels_helpers.grid_head_len[song_slot, ft_idx, ff_idx]

        # Budget remaining for PP/CM/FM/OV gems.
        budget: ti.i32 = total_budget - ft - ff

        # Adjust p/s values with FT/FF elemental contributions.
        p_val: ti.i32 = base_p_val + (ft * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff * GEM_STAT_TO_ELEMENT * is_p_ff)
        s_val: ti.i32 = base_s_val + (ft * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff * GEM_STAT_TO_ELEMENT * is_s_ff)

        res_vec = optimize_core_device(
            0,
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
            1,
            song_slot,
            ft_idx,
            ff_idx,
        )

        score: ti.i32 = res_vec[0]
        if score >= 0:
            if ti.static(not IS_METAL):
                key = (ti.cast(score + 1, ti.u64) << 32) | ti.cast(combo_idx, ti.u64)
                ti.atomic_max(kernels_helpers.chunk_best_key[genome_idx], key)
            else:
                old = ti.atomic_max(kernels_helpers.chunk_best_score[genome_idx], score)
                if old < score:
                    kernels_helpers.chunk_best_idx[genome_idx] = combo_idx
