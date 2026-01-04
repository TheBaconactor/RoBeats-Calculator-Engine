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
IS_METAL = sys.platform == "darwin"


@ti.func
def _same_grid_sig(song_slot: ti.i32, sig0: ti.u64, sig1: ti.u64, ft_i: ti.i32, ff_i: ti.i32) -> ti.i32:
    return ti.cast(
        (kernels_helpers.grid_sig0[song_slot, ft_i, ff_i] == sig0)
        & (kernels_helpers.grid_sig1[song_slot, ft_i, ff_i] == sig1),
        ti.i32,
    )


@ti.kernel
def ga_find_best_combo_warmstart_kernel(
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
    use_hints: ti.template(),  # 0 = cold start (full greedy), 1 = warm start (local search from hint)
    prune_plateaus: ti.template(),  # 0 = disabled, 1 = prune timeline plateaus via dominated representatives
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

    # FT/FF elemental contribution weights in base_value space (2*p + s).
    # Each FT/FF gem adds GEM_STAT_TO_ELEMENT to the corresponding color stat.
    w_ft: ti.i32 = GEM_STAT_TO_ELEMENT * ((is_p_ft << 1) + is_s_ft)
    w_ff: ti.i32 = GEM_STAT_TO_ELEMENT * ((is_p_ff << 1) + is_s_ff)

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

        # GPU-only plateau pruning:
        # - Bucket by "same timeline outcome" (grid_sig0/grid_sig1 equality).
        # - Within a bucket, drop combos dominated by an adjacent combo with:
        #     * same budget (ft+ff constant) but strictly higher FT/FF element weight, OR
        #     * strictly higher budget when the corresponding FT/FF weight is zero.
        # This avoids calling optimize_core_device/local_search for redundant plateau interiors.
        if ti.static(prune_plateaus):
            sig0 = kernels_helpers.grid_sig0[song_slot, ft_idx, ff_idx]
            sig1 = kernels_helpers.grid_sig1[song_slot, ft_idx, ff_idx]

            pruned: ti.i32 = 0

            # If FT doesn't contribute to base_value, any extra FT within the same timeline is pure waste.
            if pruned == 0 and w_ft == 0 and ft > 0:
                ft2 = ft - 1
                ff2 = ff
                if ff2 <= ti.min(total_budget - ft2, max_ff_gems):
                    ft2_val = ft_stat_val - gem_scale_fever
                    ft2_idx = ti.min(MAX_STAT, ti.max(0, ft2_val))
                    if _same_grid_sig(song_slot, sig0, sig1, ft2_idx, ff_idx) != 0:
                        pruned = 1

            # If FF doesn't contribute to base_value, any extra FF within the same timeline is pure waste.
            if pruned == 0 and w_ff == 0 and ff > 0:
                ft2 = ft
                ff2 = ff - 1
                if ff2 <= ti.min(total_budget - ft2, max_ff_gems):
                    ff2_val = ff_stat_val - gem_scale_fever
                    ff2_idx = ti.min(MAX_STAT, ti.max(0, ff2_val))
                    if _same_grid_sig(song_slot, sig0, sig1, ft_idx, ff2_idx) != 0:
                        pruned = 1

            # For fixed cost (ft+ff), prefer the distribution that maximizes FT/FF element contribution.
            # We only prune when the neighbor is valid AND shares the same timeline signature.
            if pruned == 0 and w_ft > w_ff and ff > 0 and (ft + 1) <= max_ft_gems:
                ft2 = ft + 1
                ff2 = ff - 1
                if ff2 <= ti.min(total_budget - ft2, max_ff_gems):
                    ft2_val = ft_stat_val + gem_scale_fever
                    ff2_val = ff_stat_val - gem_scale_fever
                    ft2_idx = ti.min(MAX_STAT, ti.max(0, ft2_val))
                    ff2_idx = ti.min(MAX_STAT, ti.max(0, ff2_val))
                    if _same_grid_sig(song_slot, sig0, sig1, ft2_idx, ff2_idx) != 0:
                        pruned = 1

            if pruned == 0 and w_ff > w_ft and ft > 0 and (ff + 1) <= max_ff_gems:
                ft2 = ft - 1
                ff2 = ff + 1
                if ff2 <= ti.min(total_budget - ft2, max_ff_gems):
                    ft2_val = ft_stat_val - gem_scale_fever
                    ff2_val = ff_stat_val + gem_scale_fever
                    ft2_idx = ti.min(MAX_STAT, ti.max(0, ft2_val))
                    ff2_idx = ti.min(MAX_STAT, ti.max(0, ff2_val))
                    if _same_grid_sig(song_slot, sig0, sig1, ft2_idx, ff2_idx) != 0:
                        pruned = 1

            # If both weights are equal, all same-cost distributions are base_value-equivalent.
            # Canonicalize toward smaller FT to remove redundant equal-value plateau interiors.
            if pruned == 0 and w_ff == w_ft and w_ft != 0 and ft > 0 and (ff + 1) <= max_ff_gems:
                ft2 = ft - 1
                ff2 = ff + 1
                if ff2 <= ti.min(total_budget - ft2, max_ff_gems):
                    ft2_val = ft_stat_val - gem_scale_fever
                    ff2_val = ff_stat_val + gem_scale_fever
                    ft2_idx = ti.min(MAX_STAT, ti.max(0, ft2_val))
                    ff2_idx = ti.min(MAX_STAT, ti.max(0, ff2_val))
                    if _same_grid_sig(song_slot, sig0, sig1, ft2_idx, ff2_idx) != 0:
                        pruned = 1

            if pruned != 0:
                continue

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

        if ti.static(use_hints):
            # Warm start: use hint from previous generation
            hint = kernels_helpers.genome_hint_allocation[genome_idx]
            res_vec = local_search_from_hint(
                hint[0],
                hint[1],
                hint[2],
                hint[3],  # pp, cm, fm, ov hints
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
        else:
            # Cold start: full greedy search
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
                tile = combo_idx % kernels_helpers.CHUNK_BEST_KEY_TILES
                ti.atomic_max(kernels_helpers.chunk_best_key_tiles[genome_idx, tile], key)
            else:
                old = ti.atomic_max(kernels_helpers.chunk_best_score[genome_idx], score)
                if old < score:
                    kernels_helpers.chunk_best_idx[genome_idx] = combo_idx
