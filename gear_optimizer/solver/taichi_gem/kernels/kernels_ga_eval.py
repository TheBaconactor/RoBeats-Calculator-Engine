"""
Taichi Kernels - GA Evaluation and Reduction Pipeline.

This module contains GPU-native GA evaluation kernels:
- Initialization: init_genome_results_kernel, init_chunk_best_key_kernel
- Reduction: reduce_chunk_to_best_key_kernel, merge_chunk_best_to_genomes_kernel
- Best combo finder: ga_find_best_combo_key_kernel
- Result writer: ga_write_best_results_from_key_kernel
- Legacy reduction: reduce_chunk_to_genomes_kernel

These kernels implement race-free reduction patterns using atomic operations
and packed keys to safely aggregate results across parallel threads.
"""
import taichi as ti

from . import kernels_helpers

from .kernels_scoring import optimize_core_device


@ti.kernel
def init_genome_results_kernel(n_genomes: ti.i32):
    """
    Initialize genome result fields to -1 (no valid result yet).

    Args:
        n_genomes: Number of genomes to initialize
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        kernels_helpers.genome_result_stats[g] = ti.Vector([-1, 0, 0, 0, 0, 0, 0])


@ti.kernel
def init_chunk_best_key_kernel(n_genomes: ti.i32):
    """
    Initialize per-chunk best-key storage.

    Key format: ((score + 1) << 32) | work_item_index.
    A zero key means "no candidate yet".

    Args:
        n_genomes: Number of genomes to initialize keys for
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        kernels_helpers.chunk_best_key[g] = ti.u64(0)


@ti.kernel
def reduce_chunk_to_best_key_kernel(n_work_items: ti.i32):
    """
    Race-free GPU-side reduction: find best (score, work_item_index) per genome.

    This avoids the data-race in reduce_chunk_to_genomes_kernel where a losing thread
    could overwrite a winning score by writing a full vector after atomic_max.

    Uses packed key format: ((score + 1) << 32) | work_item_index for atomic operations.

    Args:
        n_work_items: Number of work items to reduce
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for i in range(n_work_items):
        gid = kernels_helpers.work_items[i][6]
        score = kernels_helpers.result_stats[i][0]
        if score >= 0:
            key = (ti.cast(score + 1, ti.u64) << 32) | ti.cast(i, ti.u64)
            ti.atomic_max(kernels_helpers.chunk_best_key[gid], key)


@ti.kernel
def merge_chunk_best_to_genomes_kernel(n_genomes: ti.i32):
    """
    Merge this chunk's best candidates into genome_result_stats (one thread per genome).

    Unpacks the best key, retrieves the corresponding work item and result,
    and updates genome_result_stats if the score is better than the current best.

    Args:
        n_genomes: Number of genomes to merge results for
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        key = kernels_helpers.chunk_best_key[g]
        if key != 0:
            i = ti.cast(key & ti.u64(0xFFFFFFFF), ti.i32)
            score = ti.cast((key >> 32) - 1, ti.i32)
            if score > kernels_helpers.genome_result_stats[g][0]:
                item = kernels_helpers.work_items[i]
                res = kernels_helpers.result_stats[i]
                kernels_helpers.genome_result_stats[g] = ti.Vector([
                    score,
                    item[3],  # ft
                    item[4],  # ff
                    res[1],   # pp
                    res[2],   # cm
                    res[3],   # fm
                    res[4],   # ov
                ])


@ti.kernel
def ga_find_best_combo_key_kernel(
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
            key = (ti.cast(score + 1, ti.u64) << 32) | ti.cast(combo_idx, ti.u64)
            ti.atomic_max(kernels_helpers.chunk_best_key[genome_idx], key)


@ti.kernel
def ga_write_best_results_from_key_kernel(
    n_genomes: ti.i32,
    total_budget: ti.i32,
    gem_scale_fever: ti.i32,
    is_p_ft: ti.i32, is_s_ft: ti.i32,
    is_p_ff: ti.i32, is_s_ff: ti.i32,
    is_p_pp: ti.i32, is_s_pp: ti.i32,
    is_p_cm: ti.i32, is_s_cm: ti.i32,
    is_p_fm: ti.i32, is_s_fm: ti.i32,
    is_p_ov: ti.i32, is_s_ov: ti.i32,
    song_slot: ti.i32,
):
    """
    Finalize best (ft, ff, gem counts) per genome from chunk_best_key.

    Unpacks the best combo index from each genome's key, re-runs optimize_core_device
    to get the full result, and writes:
      - genome_result_stats[g] = [score, ft, ff, pp, cm, fm, ov]
      - ga_scores[g] = score

    This kernel is called after ga_find_best_combo_key_kernel to materialize
    the full results from the packed keys.

    Args:
        n_genomes: Number of genomes to write results for
        total_budget: Total gem budget
        gem_scale_fever: Gems per fever stat point
        is_*: Color contribution flags (0/1)
        song_slot: Grid slot for batch coalescing
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160

    for genome_idx in range(n_genomes):
        key = kernels_helpers.chunk_best_key[genome_idx]
        if key == 0:
            kernels_helpers.genome_result_stats[genome_idx] = ti.Vector([-1, 0, 0, 0, 0, 0, 0])
            kernels_helpers.ga_scores[genome_idx] = -1
            continue

        combo_idx: ti.i32 = ti.cast(key & ti.u64(0xFFFFFFFF), ti.i32)
        ft: ti.i32 = kernels_helpers.ftff_combo_ft[combo_idx]
        ff: ti.i32 = kernels_helpers.ftff_combo_ff[combo_idx]

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

        count_fever: ti.i32 = kernels_helpers.grid_count_body_fever[song_slot, ft_idx, ff_idx]
        count_normal: ti.i32 = kernels_helpers.grid_count_body_normal[song_slot, ft_idx, ff_idx]
        head_len: ti.i32 = kernels_helpers.grid_head_len[song_slot, ft_idx, ff_idx]

        budget: ti.i32 = total_budget - ft - ff
        p_val: ti.i32 = base_p_val + (ft * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff * GEM_STAT_TO_ELEMENT * is_p_ff)
        s_val: ti.i32 = base_s_val + (ft * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff * GEM_STAT_TO_ELEMENT * is_s_ff)

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
        kernels_helpers.genome_result_stats[genome_idx] = ti.Vector([
            score,
            ft,
            ff,
            res_vec[1],  # pp gems
            res_vec[2],  # cm gems
            res_vec[3],  # fm gems
            res_vec[4],  # ov gems
        ])
        kernels_helpers.ga_scores[genome_idx] = score


@ti.kernel
def reduce_chunk_to_genomes_kernel(n_work_items: ti.i32):
    """
    GPU-side reduction: find best score per genome from work item results.

    WARNING: This kernel has a benign race condition where multiple threads
    with the same max score may overwrite each other's results. For production use,
    prefer reduce_chunk_to_best_key_kernel + merge_chunk_best_to_genomes_kernel
    which implement a race-free reduction pattern.

    Args:
        n_work_items: Number of work items to reduce
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)

    for i in range(n_work_items):
        # Unpack from Vector field: [score, pp, cm, fm, ov, p_val, s_val]
        res = kernels_helpers.result_stats[i]
        score = res[0]
        # work_items layout: [budget, count_fever, count_normal, ft_gems, ff_gems, head_len, genome_id]
        gid = kernels_helpers.work_items[i][6]

        # Atomic compare-and-swap pattern for max score
        old = ti.atomic_max(kernels_helpers.genome_result_stats[gid][0], score)

        # If we won (our score is the new max), write associated data
        # Note: benign race - if two threads have same max, one wins
        if old < score:
            # Layout: [score, ft, ff, pp, cm, fm, ov]

            # Need to get ft/ff from work_items
            item = kernels_helpers.work_items[i]
            ft = item[3]
            ff = item[4]

            # pp, cm, fm, ov from res
            pp = res[1]
            cm = res[2]
            fm = res[3]
            ov = res[4]

            kernels_helpers.genome_result_stats[gid] = ti.Vector([score, ft, ff, pp, cm, fm, ov])
