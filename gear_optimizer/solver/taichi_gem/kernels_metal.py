"""
Metal-safe kernel alternatives for macOS.

This module provides replacements for kernels that use 64-bit atomics,
which are not supported on Metal Shading Language (MSL).

Strategy: Use two separate 32-bit fields (score + index) instead of
a packed 64-bit key, and use 32-bit atomics.

IMPORTANT: The kernel definitions are created lazily by create_metal_kernels()
to ensure fields are bound before Taichi JIT-compiles the kernels.
"""

import taichi as ti

from .runtime import get_block_dim

_KERNEL_BLOCK_DIM = get_block_dim()

# ============================================================================
# FIELD REFERENCES (must be set before create_metal_kernels() is called)
# ============================================================================

# These are the Metal-specific 32-bit fields
chunk_best_score = None  # (MAX_GENOMES,) i32 - best score per genome
chunk_best_idx = None  # (MAX_GENOMES,) i32 - work item index for best score

# Shared fields (bound at runtime)
work_items = None
result_stats = None
genome_result_stats = None
genome_base_stats = None
ga_scores = None
ftff_combo_ft = None
ftff_combo_ff = None
grid_count_body_fever = None
grid_count_body_normal = None
grid_head_len = None
grid_fever_masks_bits = None
grid_sig0 = None
grid_sig1 = None
genome_hint_allocation = None  # Warm-start hints for local search

# Kernel function references (populated by create_metal_kernels)
init_chunk_best_key_kernel = None
reduce_chunk_to_best_key_kernel = None
merge_chunk_best_to_genomes_kernel = None
ga_find_best_combo_key_kernel = None
ga_write_best_results_from_key_kernel = None
ga_find_best_combo_warmstart_kernel = None

_kernels_created = False


def create_metal_kernels():
    """
    Create Metal-safe kernel implementations.

    This MUST be called AFTER all fields have been bound to this module.
    The kernels are defined here (not at module load time) to ensure
    Taichi JIT compiles them with the actual field references.
    """
    global init_chunk_best_key_kernel, reduce_chunk_to_best_key_kernel
    global merge_chunk_best_to_genomes_kernel, ga_find_best_combo_key_kernel
    global ga_write_best_results_from_key_kernel, ga_find_best_combo_warmstart_kernel
    global _kernels_created

    if _kernels_created:
        return

    # Import optimize_core_device and local_search_from_hint at kernel creation time
    from .kernels import optimize_core_device, local_search_from_hint

    @ti.kernel
    def _init_chunk_best_key_kernel(n_genomes: ti.i32):
        """Initialize per-chunk best-score storage (Metal-safe 32-bit version)."""
        ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
        for g in range(n_genomes):
            chunk_best_score[g] = -1
            chunk_best_idx[g] = -1

    @ti.kernel
    def _reduce_chunk_to_best_key_kernel(n_work_items: ti.i32):
        """Metal-safe GPU-side reduction: find best (score, index) per genome."""
        ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
        for i in range(n_work_items):
            gid = work_items[i][6]
            score = result_stats[i][0]
            if score >= 0:
                old = ti.atomic_max(chunk_best_score[gid], score)
                if old < score:
                    chunk_best_idx[gid] = i

    @ti.kernel
    def _merge_chunk_best_to_genomes_kernel(n_genomes: ti.i32):
        """Merge this chunk's best candidates into genome_result_stats."""
        ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
        for g in range(n_genomes):
            score = chunk_best_score[g]
            i = chunk_best_idx[g]
            if score >= 0 and i >= 0:
                if score > genome_result_stats[g][0]:
                    item = work_items[i]
                    res = result_stats[i]
                    genome_result_stats[g] = ti.Vector(
                        [
                            score,
                            item[3],  # ft
                            item[4],  # ff
                            res[1],  # pp
                            res[2],  # cm
                            res[3],  # fm
                            res[4],  # ov
                        ]
                    )

    @ti.kernel
    def _ga_find_best_combo_key_kernel(
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
        """Metal-safe GPU-parallel evaluation across (genome, ft/ff combo)."""
        ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
        GEM_STAT_TO_ELEMENT: ti.i32 = 3
        MAX_STAT: ti.i32 = 160

        for genome_idx, local_c in ti.ndrange(n_genomes, combo_count):
            combo_idx: ti.i32 = combo_offset + local_c
            if combo_idx >= n_combos:
                continue

            ft: ti.i32 = ftff_combo_ft[combo_idx]
            ff: ti.i32 = ftff_combo_ff[combo_idx]

            if ft + ff > total_budget:
                continue

            stats = genome_base_stats[genome_idx]
            base_pp: ti.i32 = stats[0]
            base_cm: ti.i32 = stats[1]
            base_fm: ti.i32 = stats[2]
            base_p_val: ti.i32 = stats[3]
            base_s_val: ti.i32 = stats[4]
            base_ft_stat: ti.i32 = stats[5]
            base_ff_stat: ti.i32 = stats[6]

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

            ft_stat_val: ti.i32 = base_ft_stat + (ft * gem_scale_fever)
            ff_stat_val: ti.i32 = base_ff_stat + (ff * gem_scale_fever)
            ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
            ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))

            count_fever: ti.i32 = grid_count_body_fever[song_slot, ft_idx, ff_idx]
            count_normal: ti.i32 = grid_count_body_normal[song_slot, ft_idx, ff_idx]
            head_len: ti.i32 = grid_head_len[song_slot, ft_idx, ff_idx]

            budget: ti.i32 = total_budget - ft - ff
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
                old = ti.atomic_max(chunk_best_score[genome_idx], score)
                if old < score:
                    chunk_best_idx[genome_idx] = combo_idx

    @ti.kernel
    def _ga_write_best_results_from_key_kernel(
        n_genomes: ti.i32,
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
        """Finalize best (ft, ff, gem counts) per genome from chunk_best_score/idx."""
        ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
        GEM_STAT_TO_ELEMENT: ti.i32 = 3
        MAX_STAT: ti.i32 = 160

        for genome_idx in range(n_genomes):
            score = chunk_best_score[genome_idx]
            combo_idx = chunk_best_idx[genome_idx]

            if score < 0 or combo_idx < 0:
                genome_result_stats[genome_idx] = ti.Vector([-1, 0, 0, 0, 0, 0, 0])
                ga_scores[genome_idx] = -1
                continue

            ft: ti.i32 = ftff_combo_ft[combo_idx]
            ff: ti.i32 = ftff_combo_ff[combo_idx]

            stats = genome_base_stats[genome_idx]
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

            count_fever: ti.i32 = grid_count_body_fever[song_slot, ft_idx, ff_idx]
            count_normal: ti.i32 = grid_count_body_normal[song_slot, ft_idx, ff_idx]
            head_len: ti.i32 = grid_head_len[song_slot, ft_idx, ff_idx]

            budget: ti.i32 = total_budget - ft - ff
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

            final_score: ti.i32 = res_vec[0]
            genome_result_stats[genome_idx] = ti.Vector(
                [
                    final_score,
                    ft,
                    ff,
                    res_vec[1],
                    res_vec[2],
                    res_vec[3],
                    res_vec[4],
                ]
            )
            ga_scores[genome_idx] = final_score

    @ti.kernel
    def _ga_find_best_combo_warmstart_kernel(
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
        use_hints: ti.i32,
        prune_plateaus: ti.i32,
    ):
        """Metal-safe warm-start kernel using 32-bit atomics."""
        ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
        GEM_STAT_TO_ELEMENT: ti.i32 = 3
        MAX_STAT: ti.i32 = 160
        w_ft: ti.i32 = GEM_STAT_TO_ELEMENT * ((is_p_ft << 1) + is_s_ft)
        w_ff: ti.i32 = GEM_STAT_TO_ELEMENT * ((is_p_ff << 1) + is_s_ff)

        for genome_idx, local_c in ti.ndrange(n_genomes, combo_count):
            combo_idx: ti.i32 = combo_offset + local_c
            if combo_idx >= n_combos:
                continue

            ft: ti.i32 = ftff_combo_ft[combo_idx]
            ff: ti.i32 = ftff_combo_ff[combo_idx]

            if ft + ff > total_budget:
                continue

            stats = genome_base_stats[genome_idx]
            base_pp: ti.i32 = stats[0]
            base_cm: ti.i32 = stats[1]
            base_fm: ti.i32 = stats[2]
            base_p_val: ti.i32 = stats[3]
            base_s_val: ti.i32 = stats[4]
            base_ft_stat: ti.i32 = stats[5]
            base_ff_stat: ti.i32 = stats[6]

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

            ft_stat_val: ti.i32 = base_ft_stat + (ft * gem_scale_fever)
            ff_stat_val: ti.i32 = base_ff_stat + (ff * gem_scale_fever)
            ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
            ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))

            if prune_plateaus != 0:
                sig0 = grid_sig0[song_slot, ft_idx, ff_idx]
                sig1 = grid_sig1[song_slot, ft_idx, ff_idx]
                pruned: ti.i32 = 0

                if pruned == 0 and w_ft == 0 and ft > 0:
                    ft2 = ft - 1
                    ff2 = ff
                    if ff2 <= ti.min(total_budget - ft2, max_ff_gems):
                        ft2_val = ft_stat_val - gem_scale_fever
                        ft2_idx = ti.min(MAX_STAT, ti.max(0, ft2_val))
                        if (
                            grid_sig0[song_slot, ft2_idx, ff_idx] == sig0
                            and grid_sig1[song_slot, ft2_idx, ff_idx] == sig1
                        ):
                            pruned = 1

                if pruned == 0 and w_ff == 0 and ff > 0:
                    ft2 = ft
                    ff2 = ff - 1
                    if ff2 <= ti.min(total_budget - ft2, max_ff_gems):
                        ff2_val = ff_stat_val - gem_scale_fever
                        ff2_idx = ti.min(MAX_STAT, ti.max(0, ff2_val))
                        if (
                            grid_sig0[song_slot, ft_idx, ff2_idx] == sig0
                            and grid_sig1[song_slot, ft_idx, ff2_idx] == sig1
                        ):
                            pruned = 1

                if pruned == 0 and w_ft > w_ff and ff > 0 and (ft + 1) <= max_ft_gems:
                    ft2 = ft + 1
                    ff2 = ff - 1
                    if ff2 <= ti.min(total_budget - ft2, max_ff_gems):
                        ft2_val = ft_stat_val + gem_scale_fever
                        ff2_val = ff_stat_val - gem_scale_fever
                        ft2_idx = ti.min(MAX_STAT, ti.max(0, ft2_val))
                        ff2_idx = ti.min(MAX_STAT, ti.max(0, ff2_val))
                        if (
                            grid_sig0[song_slot, ft2_idx, ff2_idx] == sig0
                            and grid_sig1[song_slot, ft2_idx, ff2_idx] == sig1
                        ):
                            pruned = 1

                if pruned == 0 and w_ff > w_ft and ft > 0 and (ff + 1) <= max_ff_gems:
                    ft2 = ft - 1
                    ff2 = ff + 1
                    if ff2 <= ti.min(total_budget - ft2, max_ff_gems):
                        ft2_val = ft_stat_val - gem_scale_fever
                        ff2_val = ff_stat_val + gem_scale_fever
                        ft2_idx = ti.min(MAX_STAT, ti.max(0, ft2_val))
                        ff2_idx = ti.min(MAX_STAT, ti.max(0, ff2_val))
                        if (
                            grid_sig0[song_slot, ft2_idx, ff2_idx] == sig0
                            and grid_sig1[song_slot, ft2_idx, ff2_idx] == sig1
                        ):
                            pruned = 1

                if pruned == 0 and w_ff == w_ft and w_ft != 0 and ft > 0 and (ff + 1) <= max_ff_gems:
                    ft2 = ft - 1
                    ff2 = ff + 1
                    if ff2 <= ti.min(total_budget - ft2, max_ff_gems):
                        ft2_val = ft_stat_val - gem_scale_fever
                        ff2_val = ff_stat_val + gem_scale_fever
                        ft2_idx = ti.min(MAX_STAT, ti.max(0, ft2_val))
                        ff2_idx = ti.min(MAX_STAT, ti.max(0, ff2_val))
                        if (
                            grid_sig0[song_slot, ft2_idx, ff2_idx] == sig0
                            and grid_sig1[song_slot, ft2_idx, ff2_idx] == sig1
                        ):
                            pruned = 1

                if pruned != 0:
                    continue

            count_fever: ti.i32 = grid_count_body_fever[song_slot, ft_idx, ff_idx]
            count_normal: ti.i32 = grid_count_body_normal[song_slot, ft_idx, ff_idx]
            head_len: ti.i32 = grid_head_len[song_slot, ft_idx, ff_idx]

            budget: ti.i32 = total_budget - ft - ff
            p_val: ti.i32 = base_p_val + (ft * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff * GEM_STAT_TO_ELEMENT * is_p_ff)
            s_val: ti.i32 = base_s_val + (ft * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff * GEM_STAT_TO_ELEMENT * is_s_ff)

            res_vec = ti.Vector([0, 0, 0, 0, 0, 0, 0])

            if use_hints != 0:
                # Warm start: use hint from previous generation
                hint = genome_hint_allocation[genome_idx]
                res_vec = local_search_from_hint(
                    hint[0],
                    hint[1],
                    hint[2],
                    hint[3],
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
                old = ti.atomic_max(chunk_best_score[genome_idx], score)
                if old < score:
                    chunk_best_idx[genome_idx] = combo_idx

    # Assign to module-level names
    init_chunk_best_key_kernel = _init_chunk_best_key_kernel
    reduce_chunk_to_best_key_kernel = _reduce_chunk_to_best_key_kernel
    merge_chunk_best_to_genomes_kernel = _merge_chunk_best_to_genomes_kernel
    ga_find_best_combo_key_kernel = _ga_find_best_combo_key_kernel
    ga_write_best_results_from_key_kernel = _ga_write_best_results_from_key_kernel
    ga_find_best_combo_warmstart_kernel = _ga_find_best_combo_warmstart_kernel

    _kernels_created = True
