"""
Taichi Kernels - Warm-start GA evaluation.

Includes:
- ga_find_best_combo_warmstart_kernel
"""

import sys

import taichi as ti

from .. import kernels_helpers
from ..kernels_scoring import local_search_from_hint, optimize_core_device

# Platform detection for atomic operations
IS_METAL = (sys.platform == "darwin")


@ti.kernel
def ga_find_best_combo_warmstart_kernel(
    n_genomes: ti.i32,
    n_combos: ti.i32,
    combo_offset: ti.i32,
    combo_count: ti.i32,
    total_budget: ti.i32,
    gem_scale_fever: ti.i32,
    is_p_ft: ti.i32, is_s_ft: ti.i32,
    is_p_ff: ti.i32, is_s_ff: ti.i32,
    is_p_pp: ti.i32, is_s_pp: ti.i32,
    is_p_cm: ti.i32, is_s_cm: ti.i32,
    is_p_fm: ti.i32, is_s_fm: ti.i32,
    is_p_ov: ti.i32, is_s_ov: ti.i32,
    song_slot: ti.i32,
    use_hints: ti.i32,  # 0 = cold start (full greedy), 1 = warm start (local search from hint)
):
    """
    GPU-parallel evaluation with optional warm-start from hints.

    When use_hints=1, uses local_search_from_hint() with the genome's stored hint.
    When use_hints=0, falls back to full optimize_core_device() (cold start).

    This enables fast evaluation after Gen 0 by reusing previous generation's
    best allocations as starting points for local refinement.

    Args:
        n_genomes: Number of genomes to evaluate
        n_combos: Total number of FT/FF combinations
        combo_offset: Starting index in combo tables (for chunked processing)
        combo_count: Number of combos in this chunk
        total_budget: Total gem budget
        gem_scale_fever: Gems per fever stat point
        is_*: Color contribution flags (0/1)
        song_slot: Grid slot for batch coalescing
        use_hints: 0=cold start, 1=warm start from hints
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

        # Skip combos outside budget
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

        # Per-genome FT/FF headroom
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

        # Stat indices for grid lookup (clamped)
        ft_stat_val: ti.i32 = base_ft_stat + (ft * gem_scale_fever)
        ff_stat_val: ti.i32 = base_ff_stat + (ff * gem_scale_fever)
        ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
        ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))

        # O(1) lookup from timeline grid
        count_fever: ti.i32 = kernels_helpers.grid_count_body_fever[song_slot, ft_idx, ff_idx]
        count_normal: ti.i32 = kernels_helpers.grid_count_body_normal[song_slot, ft_idx, ff_idx]
        head_len: ti.i32 = kernels_helpers.grid_head_len[song_slot, ft_idx, ff_idx]

        # Budget remaining for PP/CM/FM/OV gems
        budget: ti.i32 = total_budget - ft - ff

        # Adjust p/s values with FT/FF elemental contributions
        p_val: ti.i32 = base_p_val + (ft * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff * GEM_STAT_TO_ELEMENT * is_p_ff)
        s_val: ti.i32 = base_s_val + (ft * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff * GEM_STAT_TO_ELEMENT * is_s_ff)

        res_vec = ti.Vector([0, 0, 0, 0, 0, 0, 0])

        if use_hints != 0:
            # Warm start: use hint from previous generation
            hint = kernels_helpers.genome_hint_allocation[genome_idx]
            res_vec = local_search_from_hint(
                hint[0], hint[1], hint[2], hint[3],  # pp, cm, fm, ov hints
                budget,
                base_pp, base_cm, base_fm,
                p_val, s_val,
                is_p_pp, is_s_pp,
                is_p_cm, is_s_cm,
                is_p_fm, is_s_fm,
                is_p_ov, is_s_ov,
                head_len, count_fever, count_normal,
                song_slot, ft_idx, ff_idx,
            )
        else:
            # Cold start: full greedy search
            res_vec = optimize_core_device(
                0, budget,
                base_pp, base_cm, base_fm,
                p_val, s_val,
                is_p_pp, is_s_pp,
                is_p_cm, is_s_cm,
                is_p_fm, is_s_fm,
                is_p_ov, is_s_ov,
                head_len, count_fever, count_normal,
                1, song_slot, ft_idx, ff_idx,
            )

        score: ti.i32 = res_vec[0]
        if score >= 0:
            if ti.static(not IS_METAL):
                key = (ti.cast(score + 1, ti.u64) << 32) | ti.cast(combo_idx, ti.u64)
                old_key = ti.atomic_max(kernels_helpers.chunk_best_key[genome_idx], key)
                # Cache results if we won the atomic race (our key was better)
                if key > old_key:
                    kernels_helpers.chunk_best_results[genome_idx, 0] = res_vec[1]  # pp
                    kernels_helpers.chunk_best_results[genome_idx, 1] = res_vec[2]  # cm
                    kernels_helpers.chunk_best_results[genome_idx, 2] = res_vec[3]  # fm
                    kernels_helpers.chunk_best_results[genome_idx, 3] = res_vec[4]  # ov
            else:
                old = ti.atomic_max(kernels_helpers.chunk_best_score[genome_idx], score)
                if old < score:
                    kernels_helpers.chunk_best_idx[genome_idx] = combo_idx
                    # Cache results for Metal path too
                    kernels_helpers.chunk_best_results[genome_idx, 0] = res_vec[1]  # pp
                    kernels_helpers.chunk_best_results[genome_idx, 1] = res_vec[2]  # cm
                    kernels_helpers.chunk_best_results[genome_idx, 2] = res_vec[3]  # fm
                    kernels_helpers.chunk_best_results[genome_idx, 3] = res_vec[4]  # ov

