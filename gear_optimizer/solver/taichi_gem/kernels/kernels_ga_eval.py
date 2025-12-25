"""
Taichi Kernels - GA Evaluation and Reduction Pipeline.

This module contains GPU-native GA evaluation kernels:
- Initialization: init_genome_results_kernel, init_chunk_best_key_kernel
- Reduction: reduce_chunk_to_best_key_kernel, merge_chunk_best_to_genomes_kernel
- Best combo finder: ga_find_best_combo_key_kernel
- Result writer: ga_write_best_results_from_key_kernel

These kernels implement race-free reduction patterns using atomic operations
and packed keys to safely aggregate results across parallel threads.
"""
import sys
import taichi as ti

# Platform detection for atomic operations
IS_METAL = (sys.platform == "darwin")

from . import kernels_helpers

from .kernels_scoring import optimize_core_device, local_search_from_hint


MAX_ELITES_PER_ISLAND = 16  # Static limit for local arrays in island elitism kernel


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
        if ti.static(not IS_METAL):
            kernels_helpers.chunk_best_key[g] = ti.u64(0)
        else:
            kernels_helpers.chunk_best_score[g] = ti.cast(-2147483648, ti.i32)
            kernels_helpers.chunk_best_idx[g] = -1


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
            if ti.static(not IS_METAL):
                key = (ti.cast(score + 1, ti.u64) << 32) | ti.cast(i, ti.u64)
                ti.atomic_max(kernels_helpers.chunk_best_key[gid], key)
            else:
                # Metal: update score first, then index (benign race)
                old = ti.atomic_max(kernels_helpers.chunk_best_score[gid], score)
                if old < score:
                    kernels_helpers.chunk_best_idx[gid] = i


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
        score = 0
        i = 0
        valid = False

        if ti.static(not IS_METAL):
            key = kernels_helpers.chunk_best_key[g]
            if key != 0:
                i = ti.cast(key & ti.u64(0xFFFFFFFF), ti.i32)
                score = ti.cast((key >> 32) - 1, ti.i32)
                valid = True
        else:
            score = kernels_helpers.chunk_best_score[g]
            i = kernels_helpers.chunk_best_idx[g]
            valid = (i >= 0)

        if valid:
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
            if ti.static(not IS_METAL):
                key = (ti.cast(score + 1, ti.u64) << 32) | ti.cast(combo_idx, ti.u64)
                ti.atomic_max(kernels_helpers.chunk_best_key[genome_idx], key)
            else:
                old = ti.atomic_max(kernels_helpers.chunk_best_score[genome_idx], score)
                if old < score:
                    kernels_helpers.chunk_best_idx[genome_idx] = combo_idx


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
        combo_idx = 0
        valid = False

        if ti.static(not IS_METAL):
            key = kernels_helpers.chunk_best_key[genome_idx]
            if key != 0:
                combo_idx = ti.cast(key & ti.u64(0xFFFFFFFF), ti.i32)
                valid = True
        else:
            i = kernels_helpers.chunk_best_idx[genome_idx]
            if i >= 0:
                combo_idx = i
                valid = True

        if not valid:
            kernels_helpers.genome_result_stats[genome_idx] = ti.Vector([-1, 0, 0, 0, 0, 0, 0])
            kernels_helpers.ga_scores[genome_idx] = -1
            continue
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
def ga_write_best_and_update_global_kernel(
    n_genomes: ti.i32,
    n_slots: ti.i32,
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
    FUSED: Write best results + store hints + update global best in one kernel.

    FIX: Re-evaluates the winning combo to get correct gem allocations, instead of
    reading cached results which may have race conditions with the combo selection.

    For each genome:
    1. Unpack best combo_idx from chunk_best_key (or chunk_best_idx on Metal)
    2. Re-evaluate with optimize_core_device to get correct gems for this combo
    3. Write genome_result_stats and ga_scores
    4. Store hints for next generation (warm-start)
    5. Atomically update global best if improved

    Args:
        n_genomes: Number of genomes
        n_slots: Number of equipment slots
        total_budget: Total gem budget
        gem_scale_fever: Gems per fever stat point
        is_*: Color contribution flags
        song_slot: Grid slot for batch coalescing
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160

    for genome_idx in range(n_genomes):
        combo_idx = 0
        valid = False

        if ti.static(not IS_METAL):
            key = kernels_helpers.chunk_best_key[genome_idx]
            if key != 0:
                combo_idx = ti.cast(key & ti.u64(0xFFFFFFFF), ti.i32)
                valid = True
        else:
            idx = kernels_helpers.chunk_best_idx[genome_idx]
            if idx >= 0:
                combo_idx = idx
                valid = True

        if not valid:
            kernels_helpers.genome_result_stats[genome_idx] = ti.Vector([-1, 0, 0, 0, 0, 0, 0])
            kernels_helpers.ga_scores[genome_idx] = -1
            continue

        # Read FT/FF from combo table
        ft: ti.i32 = kernels_helpers.ftff_combo_ft[combo_idx]
        ff: ti.i32 = kernels_helpers.ftff_combo_ff[combo_idx]

        # Load genome base stats: [pp, cm, fm, p_val, s_val, ft_stat, ff_stat]
        stats = kernels_helpers.genome_base_stats[genome_idx]
        base_pp: ti.i32 = stats[0]
        base_cm: ti.i32 = stats[1]
        base_fm: ti.i32 = stats[2]
        base_p_val: ti.i32 = stats[3]
        base_s_val: ti.i32 = stats[4]
        base_ft_stat: ti.i32 = stats[5]
        base_ff_stat: ti.i32 = stats[6]

        # Calculate stat indices for grid lookup
        ft_stat_val: ti.i32 = base_ft_stat + (ft * gem_scale_fever)
        ff_stat_val: ti.i32 = base_ff_stat + (ff * gem_scale_fever)
        ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
        ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))

        # Get song structure from grid
        count_fever: ti.i32 = kernels_helpers.grid_count_body_fever[song_slot, ft_idx, ff_idx]
        count_normal: ti.i32 = kernels_helpers.grid_count_body_normal[song_slot, ft_idx, ff_idx]
        head_len: ti.i32 = kernels_helpers.grid_head_len[song_slot, ft_idx, ff_idx]

        # Calculate budget for PP/CM/FM/OV gems (CRITICAL: must match the winning combo's FT/FF)
        budget: ti.i32 = total_budget - ft - ff

        # Adjust p/s values with FT/FF elemental contributions
        p_val: ti.i32 = base_p_val + (ft * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff * GEM_STAT_TO_ELEMENT * is_p_ff)
        s_val: ti.i32 = base_s_val + (ft * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff * GEM_STAT_TO_ELEMENT * is_s_ff)

        # RE-EVALUATE: Get correct gem allocation for this specific combo
        # This fixes the race condition where cached results could be from a different combo
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
        pp_gems: ti.i32 = res_vec[1]
        cm_gems: ti.i32 = res_vec[2]
        fm_gems: ti.i32 = res_vec[3]
        ov_gems: ti.i32 = res_vec[4]

        kernels_helpers.genome_result_stats[genome_idx] = ti.Vector([
            score, ft, ff, pp_gems, cm_gems, fm_gems, ov_gems
        ])
        kernels_helpers.ga_scores[genome_idx] = score

        kernels_helpers.genome_hint_allocation[genome_idx][0] = pp_gems
        kernels_helpers.genome_hint_allocation[genome_idx][1] = cm_gems
        kernels_helpers.genome_hint_allocation[genome_idx][2] = fm_gems
        kernels_helpers.genome_hint_allocation[genome_idx][3] = ov_gems

        old_best: ti.i32 = ti.atomic_max(kernels_helpers.ga_global_best_score[0], score)
        if old_best < score:
            for s in range(n_slots):
                kernels_helpers.ga_global_best_genome[s] = kernels_helpers.population_indices[genome_idx, s]
            for r in ti.static(range(7)):
                kernels_helpers.ga_global_best_results[r] = kernels_helpers.genome_result_stats[genome_idx][r]

@ti.kernel
def ga_init_global_best_kernel():
    """
    Initialize global best tracking fields at the start of a GA run.
    
    Sets ga_global_best_score[0] = -1 (no best yet).
    This should be called once at the start of each GA run.
    """
    kernels_helpers.ga_global_best_score[0] = -1


@ti.kernel
def ga_update_global_best_kernel(n_genomes: ti.i32, n_slots: ti.i32):
    """
    GPU-side global best update: atomically track best genome across all generations.
    
    For each genome, if its score is better than the current global best,
    atomically update the best score and copy the genome's item IDs AND results.
    
    This avoids expensive per-generation CPU downloads by keeping the best
    genome on GPU until the end of the run.
    
    Args:
        n_genomes: Number of genomes to check
        n_slots: Number of equipment slots per genome
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        score: ti.i32 = kernels_helpers.ga_scores[g]
        old_best: ti.i32 = ti.atomic_max(kernels_helpers.ga_global_best_score[0], score)
        
        # If we improved the global best, copy our genome AND results
        # Note: Race condition possible if two threads have same max score,
        # but both would copy valid genomes with that score, so result is correct.
        if old_best < score:
            for s in range(n_slots):
                kernels_helpers.ga_global_best_genome[s] = kernels_helpers.population_indices[g, s]
            # Also copy gem allocation results: [score, ft, ff, pp, cm, fm, ov]
            res = kernels_helpers.genome_result_stats[g]
            for r in ti.static(range(7)):
                kernels_helpers.ga_global_best_results[r] = res[r]


@ti.kernel
def ga_pack_run_payload_kernel(n_genomes: ti.i32, n_slots: ti.i32):
    """
    Pack a GA snapshot into `ga_run_payload_packed` for a single CPU download.

    Layout (int32):
      - Row 0: [best_score, best_genome_ids (n_slots), best_results (7)]
      - Row g+1: [score, genome_ids (n_slots), genome_result_stats (7)]
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)

    # Row 0: global best (single thread)
    for _ in range(1):
        kernels_helpers.ga_run_payload_packed[0, 0] = kernels_helpers.ga_global_best_score[0]
        for s in range(n_slots):
            kernels_helpers.ga_run_payload_packed[0, 1 + s] = kernels_helpers.ga_global_best_genome[s]
        for r in ti.static(range(7)):
            kernels_helpers.ga_run_payload_packed[0, 1 + n_slots + r] = kernels_helpers.ga_global_best_results[r]

    # Rows 1..n_genomes: per-genome snapshot
    for g in range(n_genomes):
        out_row = g + 1
        kernels_helpers.ga_run_payload_packed[out_row, 0] = kernels_helpers.ga_scores[g]
        for s in range(n_slots):
            kernels_helpers.ga_run_payload_packed[out_row, 1 + s] = kernels_helpers.population_indices[g, s]
        res = kernels_helpers.genome_result_stats[g]
        for r in ti.static(range(7)):
            kernels_helpers.ga_run_payload_packed[out_row, 1 + n_slots + r] = res[r]


@ti.kernel
def ga_pack_and_store_run_payload_kernel(run_idx: ti.i32, n_genomes: ti.i32, n_slots: ti.i32):
    """
    Pack a GA snapshot directly into the multi-run buffer `ga_runs_payload_packed`.

    Layout (int32):
      - [run_idx, 0]: [best_score, best_genome_ids (n_slots), best_results (7)]
      - [run_idx, g+1]: [score, genome_ids (n_slots), genome_result_stats (7)]
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)

    # Row 0: global best (single thread)
    for _ in range(1):
        kernels_helpers.ga_runs_payload_packed[run_idx, 0, 0] = kernels_helpers.ga_global_best_score[0]
        for s in range(n_slots):
            kernels_helpers.ga_runs_payload_packed[run_idx, 0, 1 + s] = kernels_helpers.ga_global_best_genome[s]
        for r in ti.static(range(7)):
            kernels_helpers.ga_runs_payload_packed[run_idx, 0, 1 + n_slots + r] = kernels_helpers.ga_global_best_results[r]

    # Rows 1..n_genomes: per-genome snapshot
    for g in range(n_genomes):
        out_row = g + 1
        kernels_helpers.ga_runs_payload_packed[run_idx, out_row, 0] = kernels_helpers.ga_scores[g]
        for s in range(n_slots):
            kernels_helpers.ga_runs_payload_packed[run_idx, out_row, 1 + s] = kernels_helpers.population_indices[g, s]
        res = kernels_helpers.genome_result_stats[g]
        for r in ti.static(range(7)):
            kernels_helpers.ga_runs_payload_packed[run_idx, out_row, 1 + n_slots + r] = res[r]


@ti.kernel
def ga_find_island_elites_kernel(
    n_genomes: ti.i32,
    n_islands: ti.i32,
    elites_per_island: ti.i32,
):
    """
    GPU-side island elite selection: find top-k genomes per island.
    
    Uses insertion sort within each thread to find top elites_per_island
    genomes per island, avoiding CPU downloads for elitism.
    
    Prerequisites:
    - island_boundaries must be uploaded: [start0, start1, ..., end_last]
    - ga_scores must be populated from evaluation
    
    Outputs:
    - island_elite_indices: flattened list of elite genome indices
    - island_elite_count: total number of elites (n_islands * elites_per_island)
    
    Args:
        n_genomes: Total population size
        n_islands: Number of islands (must match island_boundaries)
        elites_per_island: Number of elites to select per island
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    
    for isl in range(n_islands):
        isl_start: ti.i32 = kernels_helpers.island_boundaries[isl]
        isl_end: ti.i32 = kernels_helpers.island_boundaries[isl + 1]
        isl_size: ti.i32 = isl_end - isl_start
        
        # Local arrays for top-k tracking (insertion sort)
        top_scores = ti.Vector([-1] * MAX_ELITES_PER_ISLAND)
        top_indices = ti.Vector([-1] * MAX_ELITES_PER_ISLAND)
        
        k: ti.i32 = ti.min(elites_per_island, isl_size)
        k = ti.min(k, MAX_ELITES_PER_ISLAND)
        
        # Scan all genomes in island, maintain top-k via insertion
        for local_idx in range(isl_size):
            g: ti.i32 = isl_start + local_idx
            score: ti.i32 = kernels_helpers.ga_scores[g]
            
            # Check if this score belongs in top-k
            if score > top_scores[k - 1]:
                # Insert in sorted position
                insert_pos: ti.i32 = k - 1
                found_better: ti.i32 = 0
                for j in ti.static(range(MAX_ELITES_PER_ISLAND)):
                    if found_better == 0 and j < k and score > top_scores[j]:
                        insert_pos = j
                        found_better = 1
                
                # Shift down to make room
                for j in ti.static(range(MAX_ELITES_PER_ISLAND - 1, 0, -1)):
                    if j > insert_pos and j < k:
                        top_scores[j] = top_scores[j - 1]
                        top_indices[j] = top_indices[j - 1]
                
                top_scores[insert_pos] = score
                top_indices[insert_pos] = g
        
        # Write elites to output (flattened: island i at offset i * elites_per_island)
        out_base: ti.i32 = isl * elites_per_island
        for j in range(k):
            if top_indices[j] >= 0:
                kernels_helpers.island_elite_indices[out_base + j] = top_indices[j]
    
    # Set total elite count
    kernels_helpers.island_elite_count[0] = n_islands * elites_per_island



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


MAX_MIGRATE_COUNT = 8  # Static limit for local arrays in migration kernel


@ti.kernel
def ga_island_migration_kernel(
    n_genomes: ti.i32,
    n_islands: ti.i32,
    migrate_count: ti.i32,
    n_slots: ti.i32,
):
    """
    GPU-side island migration using ring topology.
    
    Each island i sends its top-k genomes to island (i+1) % n_islands,
    replacing the worst-k genomes in the destination island.
    
    This eliminates the expensive CPU round-trip previously required for migration:
    - No ga_download_scores()
    - No ga_download_population_indices()
    - No ga_upload_population_indices()
    
    Prerequisites:
    - island_boundaries must be uploaded: [start0, start1, ..., end_last]
    - ga_scores must be populated from evaluation
    
    Args:
        n_genomes: Total population size
        n_islands: Number of islands (must match island_boundaries)
        migrate_count: Number of genomes to migrate per island
        n_slots: Number of equipment slots per genome
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    
    for isl in range(n_islands):
        # Source island boundaries
        src_start: ti.i32 = kernels_helpers.island_boundaries[isl]
        src_end: ti.i32 = kernels_helpers.island_boundaries[isl + 1]
        src_size: ti.i32 = src_end - src_start
        
        # Destination island (ring topology: i -> (i+1) % n)
        dst_isl: ti.i32 = (isl + 1) % n_islands
        dst_start: ti.i32 = kernels_helpers.island_boundaries[dst_isl]
        dst_end: ti.i32 = kernels_helpers.island_boundaries[dst_isl + 1]
        dst_size: ti.i32 = dst_end - dst_start
        
        k: ti.i32 = ti.min(migrate_count, src_size)
        k = ti.min(k, dst_size)
        k = ti.min(k, MAX_MIGRATE_COUNT)
        
        if k <= 0:
            continue
        
        # Find top-k in source island (highest scores -> emigrants)
        top_scores = ti.Vector([-1] * MAX_MIGRATE_COUNT)
        top_indices = ti.Vector([-1] * MAX_MIGRATE_COUNT)
        
        for local_idx in range(src_size):
            g: ti.i32 = src_start + local_idx
            score: ti.i32 = kernels_helpers.ga_scores[g]
            
            if score > top_scores[k - 1]:
                # Insert in sorted position (descending)
                insert_pos: ti.i32 = k - 1
                found_better: ti.i32 = 0
                for j in ti.static(range(MAX_MIGRATE_COUNT)):
                    if found_better == 0 and j < k and score > top_scores[j]:
                        insert_pos = j
                        found_better = 1
                
                # Shift down
                for j in ti.static(range(MAX_MIGRATE_COUNT - 1, 0, -1)):
                    if j > insert_pos and j < k:
                        top_scores[j] = top_scores[j - 1]
                        top_indices[j] = top_indices[j - 1]
                
                top_scores[insert_pos] = score
                top_indices[insert_pos] = g
        
        # Find bottom-k in destination island (lowest scores -> to be replaced)
        bot_scores = ti.Vector([2147483647] * MAX_MIGRATE_COUNT)  # Start with max int
        bot_indices = ti.Vector([-1] * MAX_MIGRATE_COUNT)
        
        for local_idx in range(dst_size):
            g: ti.i32 = dst_start + local_idx
            score: ti.i32 = kernels_helpers.ga_scores[g]
            
            if score < bot_scores[k - 1]:
                # Insert in sorted position (ascending - worst first)
                insert_pos: ti.i32 = k - 1
                found_worse: ti.i32 = 0
                for j in ti.static(range(MAX_MIGRATE_COUNT)):
                    if found_worse == 0 and j < k and score < bot_scores[j]:
                        insert_pos = j
                        found_worse = 1
                
                # Shift down
                for j in ti.static(range(MAX_MIGRATE_COUNT - 1, 0, -1)):
                    if j > insert_pos and j < k:
                        bot_scores[j] = bot_scores[j - 1]
                        bot_indices[j] = bot_indices[j - 1]
                
                bot_scores[insert_pos] = score
                bot_indices[insert_pos] = g
        
        # Copy genomes: top[m] from source -> bot[m] in destination
        for m in range(k):
            src_g: ti.i32 = top_indices[m]
            dst_g: ti.i32 = bot_indices[m]
            if src_g >= 0 and dst_g >= 0:
                for s in range(n_slots):
                    kernels_helpers.population_indices[dst_g, s] = kernels_helpers.population_indices[src_g, s]
                # Also copy the score to avoid re-evaluation issues
                kernels_helpers.ga_scores[dst_g] = kernels_helpers.ga_scores[src_g]

