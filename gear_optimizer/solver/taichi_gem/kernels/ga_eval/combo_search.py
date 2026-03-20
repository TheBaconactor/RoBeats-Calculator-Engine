"""
Taichi Kernels - GA FT/FF combo search.

Includes:
- ga_find_best_combo_key_kernel
"""

import sys

import taichi as ti
from taichi.lang import simt

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
    Vulkan path also writes winning [pp, cm, fm, ov] gems into chunk_best_results.

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
    # Vulkan fast path uses a fixed block size to match scratch indexing.
    if ti.static(IS_METAL):
        ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    else:
        ti.loop_config(block_dim=kernels_helpers.GA_FTFF_REDUCE_BLOCK_DIM)
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160

    if ti.static(IS_METAL):
        # Metal: keep the original per-combo score atomic approach (no u64 atomics).
        for genome_idx, local_c in ti.ndrange(n_genomes, combo_count):
            combo_idx: ti.i32 = combo_offset + local_c
            if combo_idx >= n_combos:
                continue
            ft: ti.i32 = kernels_helpers.ftff_combo_ft[combo_idx]
            ff: ti.i32 = kernels_helpers.ftff_combo_ff[combo_idx]
            if ft + ff > total_budget:
                continue

            stats = kernels_helpers.genome_base_stats[genome_idx]
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

            count_fever: ti.i32 = kernels_helpers.grid_count_body_fever[song_slot, ft_idx, ff_idx]
            count_normal: ti.i32 = kernels_helpers.grid_count_body_normal[song_slot, ft_idx, ff_idx]
            head_len: ti.i32 = kernels_helpers.grid_head_len[song_slot, ft_idx, ff_idx]

            budget: ti.i32 = total_budget - ft - ff
            p_val: ti.i32 = base_p_val + (ft * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff * GEM_STAT_TO_ELEMENT * is_p_ff)
            s_val: ti.i32 = base_s_val + (ft * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff * GEM_STAT_TO_ELEMENT * is_s_ff)

            res_vec = optimize_core_device(
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
            score: ti.i32 = res_vec[0]
            if score >= 0:
                old = ti.atomic_max(kernels_helpers.chunk_best_score[genome_idx], score)
                if old < score:
                    kernels_helpers.chunk_best_idx[genome_idx] = combo_idx
    else:
        # Vulkan: atomic-free block-per-genome reduction.
        #
        # Important: we must not derive `lane` from the Python loop index (Taichi can remap loop
        # iterations onto physical threads on Vulkan). Always use the real SPIR-V invocation IDs.
        block_dim = ti.cast(kernels_helpers.GA_FTFF_REDUCE_BLOCK_DIM, ti.i32)
        waves = ti.cast(kernels_helpers.GA_FTFF_REDUCE_WAVE_STRIDE, ti.i32)
        shared_waves_key = simt.block.SharedArray((kernels_helpers.GA_FTFF_REDUCE_WAVE_STRIDE,), ti.u64)
        shared_waves_pp = simt.block.SharedArray((kernels_helpers.GA_FTFF_REDUCE_WAVE_STRIDE,), ti.i32)
        shared_waves_cm = simt.block.SharedArray((kernels_helpers.GA_FTFF_REDUCE_WAVE_STRIDE,), ti.i32)
        shared_waves_fm = simt.block.SharedArray((kernels_helpers.GA_FTFF_REDUCE_WAVE_STRIDE,), ti.i32)
        shared_waves_ov = simt.block.SharedArray((kernels_helpers.GA_FTFF_REDUCE_WAVE_STRIDE,), ti.i32)
        total_threads = n_genomes * block_dim

        ti.loop_config(block_dim=kernels_helpers.GA_FTFF_REDUCE_BLOCK_DIM)
        for tid in range(total_threads):
            # On Vulkan, `simt.block.global_thread_idx()` is not consistently available across Taichi builds.
            # Use the loop's linear index for the block mapping, and the real SPIR-V `localInvocationId`
            # for lane-local shared memory indexing.
            genome_idx = tid // block_dim
            lane = ti.cast(simt.block.thread_idx(), ti.i32)

            if lane < waves:
                shared_waves_key[lane] = ti.u64(0)
                shared_waves_pp[lane] = 0
                shared_waves_cm[lane] = 0
                shared_waves_fm[lane] = 0
                shared_waves_ov[lane] = 0
            simt.block.sync()

            local_best_key = ti.u64(0)
            local_pp = ti.i32(0)
            local_cm = ti.i32(0)
            local_fm = ti.i32(0)
            local_ov = ti.i32(0)

            # Stride over the chunk's combos.
            local_c: ti.i32 = lane
            while local_c < combo_count:
                combo_idx: ti.i32 = combo_offset + local_c
                if combo_idx < n_combos:
                    ft: ti.i32 = kernels_helpers.ftff_combo_ft[combo_idx]
                    ff: ti.i32 = kernels_helpers.ftff_combo_ff[combo_idx]
                    if ft + ff <= total_budget:
                        stats = kernels_helpers.genome_base_stats[genome_idx]
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
                        if ft <= max_ft_gems and ff <= ti.min(total_budget - ft, max_ff_gems):
                            ft_stat_val: ti.i32 = base_ft_stat + (ft * gem_scale_fever)
                            ff_stat_val: ti.i32 = base_ff_stat + (ff * gem_scale_fever)
                            ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
                            ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))

                            count_fever: ti.i32 = kernels_helpers.grid_count_body_fever[song_slot, ft_idx, ff_idx]
                            count_normal: ti.i32 = kernels_helpers.grid_count_body_normal[song_slot, ft_idx, ff_idx]
                            head_len: ti.i32 = kernels_helpers.grid_head_len[song_slot, ft_idx, ff_idx]

                            budget: ti.i32 = total_budget - ft - ff
                            p_val: ti.i32 = (
                                base_p_val
                                + (ft * GEM_STAT_TO_ELEMENT * is_p_ft)
                                + (ff * GEM_STAT_TO_ELEMENT * is_p_ff)
                            )
                            s_val: ti.i32 = (
                                base_s_val
                                + (ft * GEM_STAT_TO_ELEMENT * is_s_ft)
                                + (ff * GEM_STAT_TO_ELEMENT * is_s_ff)
                            )

                            res_vec = optimize_core_device(
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
                            score: ti.i32 = res_vec[0]
                            if score >= 0:
                                key: ti.u64 = (ti.cast(score + 1, ti.u64) << 32) | ti.cast(combo_idx, ti.u64)
                                if key > local_best_key:
                                    local_best_key = key
                                    local_pp = res_vec[1]
                                    local_cm = res_vec[2]
                                    local_fm = res_vec[3]
                                    local_ov = res_vec[4]

                local_c += block_dim

            best = simt.subgroup.reduce_max(local_best_key)
            win_pp = ti.i32(0)
            win_cm = ti.i32(0)
            win_fm = ti.i32(0)
            win_ov = ti.i32(0)
            if best != ti.u64(0):
                # Do not assume the elected lane is the argmax lane.
                # Reduce payloads gated by the winner predicate so the elected lane can write.
                is_winner = ti.cast(local_best_key == best, ti.i32)
                win_pp = simt.subgroup.reduce_max(is_winner * local_pp)
                win_cm = simt.subgroup.reduce_max(is_winner * local_cm)
                win_fm = simt.subgroup.reduce_max(is_winner * local_fm)
                win_ov = simt.subgroup.reduce_max(is_winner * local_ov)

            if simt.subgroup.elect() and best != ti.u64(0):
                wave_slot = lane >> 5  # lane//32, works for wave32 and wave64 (wave64 uses even slots)
                shared_waves_key[wave_slot] = best
                shared_waves_pp[wave_slot] = win_pp
                shared_waves_cm[wave_slot] = win_cm
                shared_waves_fm[wave_slot] = win_fm
                shared_waves_ov[wave_slot] = win_ov
            simt.block.sync()

            if lane == 0:
                block_best = shared_waves_key[0]
                block_best_wave: ti.i32 = 0
                for i in range(1, kernels_helpers.GA_FTFF_REDUCE_WAVE_STRIDE):
                    v = shared_waves_key[i]
                    if v > block_best:
                        block_best = v
                        block_best_wave = i

                if block_best != ti.u64(0):
                    prev = kernels_helpers.chunk_best_key[genome_idx]
                    if block_best > prev:
                        kernels_helpers.chunk_best_key[genome_idx] = block_best
                        kernels_helpers.chunk_best_results[genome_idx, 0] = shared_waves_pp[block_best_wave]
                        kernels_helpers.chunk_best_results[genome_idx, 1] = shared_waves_cm[block_best_wave]
                        kernels_helpers.chunk_best_results[genome_idx, 2] = shared_waves_fm[block_best_wave]
                        kernels_helpers.chunk_best_results[genome_idx, 3] = shared_waves_ov[block_best_wave]
