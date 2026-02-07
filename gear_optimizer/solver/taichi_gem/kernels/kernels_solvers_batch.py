"""
Taichi Kernels - Batch Solver Strategies.

This module contains batch solving kernels:
- solve_batch_kernel: Process work items in parallel
- solve_genomes_with_ftff_kernel: Iterate FT/FF combos per genome (GPU-internal)
- solve_ftff_parallel_kernel: Parallelize across (genome, FT, FF) combinations

All kernels use optimize_core_device from kernels_scoring for greedy gem allocation.
"""

import os

import taichi as ti
from taichi.lang import simt

from . import kernels_helpers

from .kernels_scoring import optimize_core_device

try:
    GA_FTFF_BLOCK_DIM = int(os.environ.get("GA_FTFF_BLOCK_DIM", "64") or "64")
except Exception:
    GA_FTFF_BLOCK_DIM = 64
GA_FTFF_BLOCK_DIM = max(32, min(int(GA_FTFF_BLOCK_DIM), 256))
GA_FTFF_BLOCK_DIM = (GA_FTFF_BLOCK_DIM // 32) * 32
if GA_FTFF_BLOCK_DIM <= 0:
    GA_FTFF_BLOCK_DIM = 32
GA_FTFF_BLOCK_WAVES = (GA_FTFF_BLOCK_DIM + 31) // 32


@ti.kernel
def copy_work_items_from_ndarray_kernel(n_items: ti.i32, src: ti.types.ndarray(dtype=ti.i32, ndim=2)):
    """
    Copy a variable-length host work-item buffer into the resident work_items field.

    This avoids full-field from_numpy() uploads when only the first `n_items` rows
    are valid in a chunk.
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for i, j in ti.ndrange(n_items, 8):
        kernels_helpers.work_items[i][j] = src[i, j]


@ti.kernel
def solve_batch_kernel(
    n_items: ti.i32,
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
):
    """
    Main kernel - processes all work items in parallel.

    Each work item represents one (FT_gems, FF_gems) timeline combination
    for one genome. The kernel parallelizes across all work items.

    Unpacks from Vector fields.

    Args:
        n_items: Number of work items to process
        is_*: Color contribution flags (0/1) for primary/secondary
    """
    # Honor TAICHI_BLOCK_DIM (work-group size) for Vulkan kernels.
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    GEM_STAT_TO_ELEMENT: ti.i32 = 3

    for i in range(n_items):
        # Unpack work item
        # [budget, count_fever, count_normal, ft_gems, ff_gems, head_len, genome_id]
        item = kernels_helpers.work_items[i]
        budget = item[0]
        count_fever = item[1]
        count_normal = item[2]
        ft_gems = item[3]
        ff_gems = item[4]
        head_len = item[5]
        genome_id = item[6]

        # Look up per-genome base stats
        # [pp, cm, fm, p_val, s_val, ft, ff]
        stats = kernels_helpers.genome_base_stats[genome_id]
        base_pp = stats[0]
        base_cm = stats[1]
        base_fm = stats[2]
        base_p_val = stats[3]
        base_s_val = stats[4]

        # Adjust elemental stats
        p_val = base_p_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff_gems * GEM_STAT_TO_ELEMENT * is_p_ff)
        s_val = base_s_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff_gems * GEM_STAT_TO_ELEMENT * is_s_ff)

        score_vec = optimize_core_device(
            i,
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
            0,
            0,
            0,
            0,
        )
        # [score, pp, cm, fm, ov, p_val, s_val]
        kernels_helpers.result_stats[i] = score_vec


@ti.kernel
def solve_genomes_with_ftff_kernel(
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
    song_slot: ti.i32,  # Grid slot for batch coalescing (0 for single-song)
):
    """
    New kernel that iterates FT/FF combinations INSIDE the GPU thread.

    Each thread handles one genome and iterates through all valid FT/FF
    combinations, using the preloaded timeline grid for O(1) lookups.

    This eliminates ~400k work item transfers per generation.

    Args:
        n_genomes: Number of genomes to process
        total_budget: Total gem budget (typically 90)
        gem_scale_fever: Gems per fever stat point (typically 3)
        is_*: Color contribution flags (0/1)
        song_slot: Grid slot for batch coalescing (0 for single-song)
    """
    # Honor TAICHI_BLOCK_DIM (work-group size) for Vulkan kernels.
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160

    for genome_idx in range(n_genomes):
        # [pp, cm, fm, p_val, s_val, ft, ff]
        stats = kernels_helpers.genome_base_stats[genome_idx]
        base_pp = stats[0]
        base_cm = stats[1]
        base_fm = stats[2]
        base_p_val = stats[3]
        base_s_val = stats[4]
        base_ft_stat = stats[5]
        base_ff_stat = stats[6]

        # Compute max FT/FF gems based on stat headroom
        remaining_ft = MAX_STAT - base_ft_stat
        remaining_ff = MAX_STAT - base_ff_stat
        max_ft_gems: ti.i32 = remaining_ft // gem_scale_fever if remaining_ft > 0 else 0
        max_ff_gems: ti.i32 = remaining_ff // gem_scale_fever if remaining_ff > 0 else 0

        # Track best result across all FT/FF combinations
        best_score: ti.i32 = -1
        best_ft: ti.i32 = 0
        best_ff: ti.i32 = 0
        best_g_pp: ti.i32 = 0
        best_g_cm: ti.i32 = 0
        best_g_fm: ti.i32 = 0
        best_g_ov: ti.i32 = 0

        # Iterate all valid FT/FF combinations
        for ft in range(ti.min(total_budget, max_ft_gems) + 1):
            remaining_for_ff: ti.i32 = total_budget - ft

            for ff in range(ti.min(remaining_for_ff, max_ff_gems) + 1):
                # Compute stat indices for grid lookup
                ft_stat_val: ti.i32 = base_ft_stat + (ft * gem_scale_fever)
                ff_stat_val: ti.i32 = base_ff_stat + (ff * gem_scale_fever)
                ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
                ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))

                # O(1) lookup from grid using song_slot
                count_fever: ti.i32 = ti.cast(kernels_helpers.grid_count_body_fever[song_slot, ft_idx, ff_idx], ti.i32)
                count_normal: ti.i32 = ti.cast(
                    kernels_helpers.grid_count_body_normal[song_slot, ft_idx, ff_idx], ti.i32
                )
                head_len: ti.i32 = ti.cast(kernels_helpers.grid_head_len[song_slot, ft_idx, ff_idx], ti.i32)

                # Budget remaining for PP/CM/FM/OV gems
                budget: ti.i32 = total_budget - ft - ff

                # Adjust p/s values for FT/FF gem contributions
                p_val: ti.i32 = base_p_val + (ft * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff * GEM_STAT_TO_ELEMENT * is_p_ff)
                s_val: ti.i32 = base_s_val + (ft * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff * GEM_STAT_TO_ELEMENT * is_s_ff)

                # Run greedy gem allocation (shared optimize_core_device) for exact behavioral match
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
                local_best_score: ti.i32 = res_vec[0]
                gems_pp: ti.i32 = res_vec[1]
                gems_cm: ti.i32 = res_vec[2]
                gems_fm: ti.i32 = res_vec[3]
                gems_ov: ti.i32 = res_vec[4]

                # Check if this FT/FF combo is better
                if local_best_score > best_score:
                    best_score = local_best_score
                    best_ft = ft
                    best_ff = ff
                    best_g_pp = gems_pp
                    best_g_cm = gems_cm
                    best_g_fm = gems_fm
                    best_g_ov = gems_ov

        # Store result
        # [score, ft, ff, pp, cm, fm, ov]
        kernels_helpers.genome_result_stats[genome_idx] = ti.Vector(
            [best_score, best_ft, best_ff, best_g_pp, best_g_cm, best_g_fm, best_g_ov]
        )


@ti.kernel
def solve_genomes_with_ftff_block_kernel(
    n_genomes: ti.i32,
    n_combos: ti.i32,
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
    song_slot: ti.i32,  # Grid slot for batch coalescing (0 for single-song)
):
    """
    Block-per-owner FT/FF search (Vulkan): one workgroup per genome.

    Threads stride across combo indices and reduce to a single packed winner per genome.
    Avoids atomics while keeping enough parallelism per genome to increase occupancy.
    """
    ti.loop_config(block_dim=GA_FTFF_BLOCK_DIM)
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160

    # One entry per "wave slot" (see wave_slot computation below). We track the best packed key and
    # the winning lane's gem allocation payload, so lane 0 can write the full result without
    # recomputing `optimize_core_device()` for the winning combo.
    shared_waves_key = simt.block.SharedArray((GA_FTFF_BLOCK_WAVES,), ti.u64)
    shared_waves_combo = simt.block.SharedArray((GA_FTFF_BLOCK_WAVES,), ti.i32)
    shared_waves_pp = simt.block.SharedArray((GA_FTFF_BLOCK_WAVES,), ti.i32)
    shared_waves_cm = simt.block.SharedArray((GA_FTFF_BLOCK_WAVES,), ti.i32)
    shared_waves_fm = simt.block.SharedArray((GA_FTFF_BLOCK_WAVES,), ti.i32)
    shared_waves_ov = simt.block.SharedArray((GA_FTFF_BLOCK_WAVES,), ti.i32)
    shared_prefix_end = simt.block.SharedArray((1,), ti.i32)
    shared_max_ft = simt.block.SharedArray((1,), ti.i32)
    shared_max_ff = simt.block.SharedArray((1,), ti.i32)
    total_threads = n_genomes * GA_FTFF_BLOCK_DIM

    for tid in range(total_threads):
        genome_idx = tid // GA_FTFF_BLOCK_DIM
        lane = tid - (genome_idx * GA_FTFF_BLOCK_DIM)

        if lane < GA_FTFF_BLOCK_WAVES:
            shared_waves_key[lane] = ti.u64(0)
            shared_waves_combo[lane] = 0
            shared_waves_pp[lane] = 0
            shared_waves_cm[lane] = 0
            shared_waves_fm[lane] = 0
            shared_waves_ov[lane] = 0
        simt.block.sync()

        # Load genome base stats
        # [pp, cm, fm, p_val, s_val, ft, ff]
        stats = kernels_helpers.genome_base_stats[genome_idx]
        base_pp = stats[0]
        base_cm = stats[1]
        base_fm = stats[2]
        base_p_val = stats[3]
        base_s_val = stats[4]
        base_ft_stat = stats[5]
        base_ff_stat = stats[6]

        # Compute per-genome FT/FF headroom and combo prefix once, then share.
        if lane == 0:
            remaining_ft_0: ti.i32 = MAX_STAT - base_ft_stat
            max_ft_gems_0: ti.i32 = remaining_ft_0 // gem_scale_fever if remaining_ft_0 > 0 else 0
            if max_ft_gems_0 > total_budget:
                max_ft_gems_0 = total_budget

            remaining_ff_0: ti.i32 = MAX_STAT - base_ff_stat
            max_ff_gems_0: ti.i32 = remaining_ff_0 // gem_scale_fever if remaining_ff_0 > 0 else 0
            if max_ff_gems_0 > total_budget:
                max_ff_gems_0 = total_budget

            # combo table order: ft=0,ff=0..B ; ft=1,ff=0..B-1 ; ...
            prefix_end_0: ti.i32 = (max_ft_gems_0 + 1) * (total_budget + 1) - (
                (max_ft_gems_0 * (max_ft_gems_0 + 1)) // 2
            )
            if max_ft_gems_0 == 0:
                prefix_end_0 = ti.min(prefix_end_0, max_ff_gems_0 + 1)
            if prefix_end_0 > n_combos:
                prefix_end_0 = n_combos

            shared_prefix_end[0] = prefix_end_0
            shared_max_ft[0] = max_ft_gems_0
            shared_max_ff[0] = max_ff_gems_0
        simt.block.sync()

        max_ft_gems: ti.i32 = shared_max_ft[0]
        max_ff_gems: ti.i32 = shared_max_ff[0]
        limit_combo: ti.i32 = shared_prefix_end[0]

        local_best_key: ti.u64 = ti.u64(0)
        local_best_combo: ti.i32 = 0
        local_best_pp: ti.i32 = 0
        local_best_cm: ti.i32 = 0
        local_best_fm: ti.i32 = 0
        local_best_ov: ti.i32 = 0

        # Stride combos across lanes in the block.
        combo_idx: ti.i32 = lane
        while combo_idx < limit_combo:
            ft: ti.i32 = kernels_helpers.ftff_combo_ft[combo_idx]
            ff: ti.i32 = kernels_helpers.ftff_combo_ff[combo_idx]
            valid: ti.i32 = 1
            if ft > max_ft_gems:
                valid = 0
            if ff > ti.min(total_budget - ft, max_ff_gems):
                valid = 0

            if valid != 0:
                ft_stat_val: ti.i32 = base_ft_stat + (ft * gem_scale_fever)
                ff_stat_val: ti.i32 = base_ff_stat + (ff * gem_scale_fever)
                ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
                ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))

                count_fever: ti.i32 = ti.cast(
                    kernels_helpers.grid_count_body_fever[song_slot, ft_idx, ff_idx], ti.i32
                )
                count_normal: ti.i32 = ti.cast(
                    kernels_helpers.grid_count_body_normal[song_slot, ft_idx, ff_idx], ti.i32
                )
                head_len: ti.i32 = ti.cast(kernels_helpers.grid_head_len[song_slot, ft_idx, ff_idx], ti.i32)

                budget: ti.i32 = total_budget - ft - ff
                p_val: ti.i32 = (
                    base_p_val + (ft * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff * GEM_STAT_TO_ELEMENT * is_p_ff)
                )
                s_val: ti.i32 = (
                    base_s_val + (ft * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff * GEM_STAT_TO_ELEMENT * is_s_ff)
                )

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
                    inv_idx = ti.u64(0xFFFFFFFF) - ti.cast(combo_idx, ti.u64)
                    key = (ti.cast(score + 1, ti.u64) << 32) | inv_idx
                    if key > local_best_key:
                        local_best_key = key
                        local_best_combo = combo_idx
                        local_best_pp = res_vec[1]
                        local_best_cm = res_vec[2]
                        local_best_fm = res_vec[3]
                        local_best_ov = res_vec[4]

            combo_idx += GA_FTFF_BLOCK_DIM

        best = simt.subgroup.reduce_max(local_best_key)
        win_combo: ti.i32 = 0
        win_pp: ti.i32 = 0
        win_cm: ti.i32 = 0
        win_fm: ti.i32 = 0
        win_ov: ti.i32 = 0

        if best != ti.u64(0):
            # Pick the winning lane's payload without needing an argmax primitive:
            # only the winning lane contributes a non-zero value.
            is_winner: ti.i32 = ti.cast(local_best_key == best, ti.i32)
            win_combo = simt.subgroup.reduce_max(is_winner * local_best_combo)
            win_pp = simt.subgroup.reduce_max(is_winner * local_best_pp)
            win_cm = simt.subgroup.reduce_max(is_winner * local_best_cm)
            win_fm = simt.subgroup.reduce_max(is_winner * local_best_fm)
            win_ov = simt.subgroup.reduce_max(is_winner * local_best_ov)

        if simt.subgroup.elect() and best != ti.u64(0):
            wave_slot = lane >> 5  # lane//32, valid for wave32 and wave64 (wave64 uses even slots)
            shared_waves_key[wave_slot] = best
            shared_waves_combo[wave_slot] = win_combo
            shared_waves_pp[wave_slot] = win_pp
            shared_waves_cm[wave_slot] = win_cm
            shared_waves_fm[wave_slot] = win_fm
            shared_waves_ov[wave_slot] = win_ov
        simt.block.sync()

        if lane == 0:
            block_best = shared_waves_key[0]
            block_best_wave: ti.i32 = 0
            for i in range(1, GA_FTFF_BLOCK_WAVES):
                v = shared_waves_key[i]
                if v > block_best:
                    block_best = v
                    block_best_wave = i

            if block_best == ti.u64(0):
                kernels_helpers.genome_result_stats[genome_idx] = ti.Vector([-1, 0, 0, 0, 0, 0, 0])
            else:
                combo_idx = shared_waves_combo[block_best_wave]
                ft: ti.i32 = kernels_helpers.ftff_combo_ft[combo_idx]
                ff: ti.i32 = kernels_helpers.ftff_combo_ff[combo_idx]
                score: ti.i32 = ti.cast((block_best >> 32), ti.i32) - 1

                kernels_helpers.genome_result_stats[genome_idx] = ti.Vector(
                    [
                        score,
                        ft,
                        ff,
                        shared_waves_pp[block_best_wave],
                        shared_waves_cm[block_best_wave],
                        shared_waves_fm[block_best_wave],
                        shared_waves_ov[block_best_wave],
                    ]
                )


@ti.kernel
def solve_ftff_parallel_kernel(
    n_work_items: ti.i32,
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
):
    """
    V2 kernel: Parallelize across (genome, ft, ff) combinations.

    Uses Vector fields for work items.
    Supports multi-song batch coalescing via song_flags and song_slot.

    Args:
        n_work_items: Number of work items (genome × FT/FF combos)
        total_budget: Total gem budget
        gem_scale_fever: Gems per fever stat point
        is_*: Default color contribution flags (overridden by song_flags)
    """
    # Honor TAICHI_BLOCK_DIM (work-group size) for Vulkan kernels.
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160

    for i in range(n_work_items):
        item = kernels_helpers.work_items[i]
        # [budget, count_fever, count_normal, ft_gems, ff_gems, head_len, genome_id, song_slot]

        budget: ti.i32 = item[0]
        count_fever: ti.i32 = item[1]
        count_normal: ti.i32 = item[2]
        ft: ti.i32 = item[3]
        ff: ti.i32 = item[4]
        head_len: ti.i32 = item[5]
        genome_idx: ti.i32 = item[6]
        song_slot: ti.i32 = item[7]  # Song grid slot for batch coalescing

        # Per-song-slot flags (override kernel args for multi-song batching)
        # [is_p_ft, is_s_ft, is_p_ff, is_s_ff, is_p_pp, is_s_pp,
        #  is_p_cm, is_s_cm, is_p_fm, is_s_fm, is_p_ov, is_s_ov]
        f_is_p_ft: ti.i32 = kernels_helpers.song_flags[song_slot, 0]
        f_is_s_ft: ti.i32 = kernels_helpers.song_flags[song_slot, 1]
        f_is_p_ff: ti.i32 = kernels_helpers.song_flags[song_slot, 2]
        f_is_s_ff: ti.i32 = kernels_helpers.song_flags[song_slot, 3]
        f_is_p_pp: ti.i32 = kernels_helpers.song_flags[song_slot, 4]
        f_is_s_pp: ti.i32 = kernels_helpers.song_flags[song_slot, 5]
        f_is_p_cm: ti.i32 = kernels_helpers.song_flags[song_slot, 6]
        f_is_s_cm: ti.i32 = kernels_helpers.song_flags[song_slot, 7]
        f_is_p_fm: ti.i32 = kernels_helpers.song_flags[song_slot, 8]
        f_is_s_fm: ti.i32 = kernels_helpers.song_flags[song_slot, 9]
        f_is_p_ov: ti.i32 = kernels_helpers.song_flags[song_slot, 10]
        f_is_s_ov: ti.i32 = kernels_helpers.song_flags[song_slot, 11]

        # Load genome base stats
        stats = kernels_helpers.genome_base_stats[genome_idx]
        base_pp: ti.i32 = stats[0]
        base_cm: ti.i32 = stats[1]
        base_fm: ti.i32 = stats[2]
        base_p_val: ti.i32 = stats[3]
        base_s_val: ti.i32 = stats[4]
        base_ft_stat: ti.i32 = stats[5]
        base_ff_stat: ti.i32 = stats[6]

        # Compute stat indices for grid lookup (re-calculated to ensure correctness with base_ft_stat/base_ff_stat)
        ft_stat_val: ti.i32 = base_ft_stat + (ft * gem_scale_fever)
        ff_stat_val: ti.i32 = base_ff_stat + (ff * gem_scale_fever)
        ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
        ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))

        # O(1) lookup from grid using song_slot for batch coalescing
        count_fever = ti.cast(kernels_helpers.grid_count_body_fever[song_slot, ft_idx, ff_idx], ti.i32)
        count_normal = ti.cast(kernels_helpers.grid_count_body_normal[song_slot, ft_idx, ff_idx], ti.i32)
        head_len = ti.cast(kernels_helpers.grid_head_len[song_slot, ft_idx, ff_idx], ti.i32)

        # Adjust p/s values
        p_val: ti.i32 = base_p_val + (ft * GEM_STAT_TO_ELEMENT * f_is_p_ft) + (ff * GEM_STAT_TO_ELEMENT * f_is_p_ff)
        s_val: ti.i32 = base_s_val + (ft * GEM_STAT_TO_ELEMENT * f_is_s_ft) + (ff * GEM_STAT_TO_ELEMENT * f_is_s_ff)

        # Run greedy gem allocation
        res_vec = optimize_core_device(
            i,
            budget,
            base_pp,
            base_cm,
            base_fm,
            p_val,
            s_val,
            f_is_p_pp,
            f_is_s_pp,
            f_is_p_cm,
            f_is_s_cm,
            f_is_p_fm,
            f_is_s_fm,
            f_is_p_ov,
            f_is_s_ov,
            head_len,
            count_fever,
            count_normal,
            1,
            song_slot,
            ft_idx,
            ff_idx,
        )

        kernels_helpers.result_stats[i] = res_vec


@ti.kernel
def copy_genome_result_stats_to_download_staging_kernel(out_stats: ti.template(), n_genomes: ti.i32):
    """
    Copy the populated slice of `genome_result_stats` into a smaller staging field.

    On Vulkan, `to_numpy()` transfers the full field shape, so downloading the padded
    MAX_GENOMES=4096 buffer can dominate throughput when only ~250 genomes are active.
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        out_stats[g] = kernels_helpers.genome_result_stats[g]
