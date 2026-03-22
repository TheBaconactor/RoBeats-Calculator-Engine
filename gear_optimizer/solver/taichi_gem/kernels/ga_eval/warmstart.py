"""
Taichi Kernels - Warm-start GA evaluation.

Includes:
- ga_find_best_combo_warmstart_kernel
"""

import sys

import taichi as ti
from taichi.lang import simt

from .. import kernels_helpers
from ..kernels_scoring import local_search_from_hint, optimize_core_device

# Platform detection for atomic operations
IS_METAL = sys.platform == "darwin"
MAX_STAT = 160  # gear_optimizer.core.constants.MAX_STAT_INDEX


@ti.func
def _same_grid_sig(song_slot: ti.i32, sig0: ti.u64, sig1: ti.u64, ft_i: ti.i32, ff_i: ti.i32) -> ti.i32:
    return ti.cast(
        (kernels_helpers.grid_sig0[song_slot, ft_i, ff_i] == sig0)
        & (kernels_helpers.grid_sig1[song_slot, ft_i, ff_i] == sig1),
        ti.i32,
    )


@ti.func
def _compute_combo_key_warmstart(
    genome_idx: ti.i32,
    combo_idx: ti.i32,
    n_combos: ti.i32,
    combo_budget: ti.i32,
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
    w_ft: ti.i32,
    w_ff: ti.i32,
    use_hints: ti.template(),
    prune_plateaus: ti.template(),
    out_gems: ti.template(),  # [pp, cm, fm, ov] for this combo when key != 0
) -> ti.u64:
    """
    Compute a packed max-key for a single (genome, combo) work item.

    Returns:
        u64 key in format: ((score + 1) << 32) | combo_idx
        0 when the combo is invalid/pruned or yields a negative score.
    """
    GEM_STAT_TO_ELEMENT: ti.i32 = 3

    out_key = ti.u64(0)
    out_gems[0] = 0
    out_gems[1] = 0
    out_gems[2] = 0
    out_gems[3] = 0

    if combo_idx < n_combos:
        ft: ti.i32 = kernels_helpers.ftff_combo_ft[combo_idx]
        ff: ti.i32 = kernels_helpers.ftff_combo_ff[combo_idx]

        if ft + ff <= combo_budget:
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
            if max_ft_gems > combo_budget:
                max_ft_gems = combo_budget
            if max_ff_gems > combo_budget:
                max_ff_gems = combo_budget

            if ft <= max_ft_gems and ff <= ti.min(combo_budget - ft, max_ff_gems):
                ft_stat_val: ti.i32 = base_ft_stat + (ft * gem_scale_fever)
                ff_stat_val: ti.i32 = base_ff_stat + (ff * gem_scale_fever)
                ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
                ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))

                pruned: ti.i32 = 0
                if ti.static(prune_plateaus):
                    sig0 = kernels_helpers.grid_sig0[song_slot, ft_idx, ff_idx]
                    sig1 = kernels_helpers.grid_sig1[song_slot, ft_idx, ff_idx]

                    if pruned == 0 and w_ft == 0 and ft > 0:
                        ft2 = ft - 1
                        ff2 = ff
                        if ff2 <= ti.min(combo_budget - ft2, max_ff_gems):
                            ft2_val = ft_stat_val - gem_scale_fever
                            ft2_idx = ti.min(MAX_STAT, ti.max(0, ft2_val))
                            if _same_grid_sig(song_slot, sig0, sig1, ft2_idx, ff_idx) != 0:
                                pruned = 1

                    if pruned == 0 and w_ff == 0 and ff > 0:
                        ft2 = ft
                        ff2 = ff - 1
                        if ff2 <= ti.min(combo_budget - ft2, max_ff_gems):
                            ff2_val = ff_stat_val - gem_scale_fever
                            ff2_idx = ti.min(MAX_STAT, ti.max(0, ff2_val))
                            if _same_grid_sig(song_slot, sig0, sig1, ft_idx, ff2_idx) != 0:
                                pruned = 1

                    if pruned == 0 and w_ft > w_ff and ff > 0 and (ft + 1) <= max_ft_gems:
                        ft2 = ft + 1
                        ff2 = ff - 1
                        if ff2 <= ti.min(combo_budget - ft2, max_ff_gems):
                            ft2_val = ft_stat_val + gem_scale_fever
                            ff2_val = ff_stat_val - gem_scale_fever
                            ft2_idx = ti.min(MAX_STAT, ti.max(0, ft2_val))
                            ff2_idx = ti.min(MAX_STAT, ti.max(0, ff2_val))
                            if _same_grid_sig(song_slot, sig0, sig1, ft2_idx, ff2_idx) != 0:
                                pruned = 1

                    if pruned == 0 and w_ff > w_ft and ft > 0 and (ff + 1) <= max_ff_gems:
                        ft2 = ft - 1
                        ff2 = ff + 1
                        if ff2 <= ti.min(combo_budget - ft2, max_ff_gems):
                            ft2_val = ft_stat_val - gem_scale_fever
                            ff2_val = ff_stat_val + gem_scale_fever
                            ft2_idx = ti.min(MAX_STAT, ti.max(0, ft2_val))
                            ff2_idx = ti.min(MAX_STAT, ti.max(0, ff2_val))
                            if _same_grid_sig(song_slot, sig0, sig1, ft2_idx, ff2_idx) != 0:
                                pruned = 1

                    if pruned == 0 and w_ff == w_ft and w_ft != 0 and ft > 0 and (ff + 1) <= max_ff_gems:
                        ft2 = ft - 1
                        ff2 = ff + 1
                        if ff2 <= ti.min(combo_budget - ft2, max_ff_gems):
                            ft2_val = ft_stat_val - gem_scale_fever
                            ff2_val = ff_stat_val + gem_scale_fever
                            ft2_idx = ti.min(MAX_STAT, ti.max(0, ft2_val))
                            ff2_idx = ti.min(MAX_STAT, ti.max(0, ff2_val))
                            if _same_grid_sig(song_slot, sig0, sig1, ft2_idx, ff2_idx) != 0:
                                pruned = 1

                if pruned == 0:
                    count_fever: ti.i32 = kernels_helpers.grid_count_body_fever[song_slot, ft_idx, ff_idx]
                    count_normal: ti.i32 = kernels_helpers.grid_count_body_normal[song_slot, ft_idx, ff_idx]
                    head_len: ti.i32 = kernels_helpers.grid_head_len[song_slot, ft_idx, ff_idx]

                    budget: ti.i32 = combo_budget - ft - ff

                    p_val: ti.i32 = (
                        base_p_val + (ft * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff * GEM_STAT_TO_ELEMENT * is_p_ff)
                    )
                    s_val: ti.i32 = (
                        base_s_val + (ft * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff * GEM_STAT_TO_ELEMENT * is_s_ff)
                    )

                    res_vec = ti.Vector([0, 0, 0, 0, 0, 0, 0])
                    if ti.static(use_hints):
                        hint = kernels_helpers.genome_hint_allocation[genome_idx]
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
                        out_key = (ti.cast(score + 1, ti.u64) << 32) | ti.cast(combo_idx, ti.u64)
                        out_gems[0] = res_vec[1]
                        out_gems[1] = res_vec[2]
                        out_gems[2] = res_vec[3]
                        out_gems[3] = res_vec[4]

    return out_key


@ti.func
def _compute_combo_key_warmstart_precomputed(
    genome_idx: ti.i32,
    combo_idx: ti.i32,
    n_combos: ti.i32,
    combo_budget: ti.i32,
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
    w_ft: ti.i32,
    w_ff: ti.i32,
    max_ft_gems: ti.i32,
    max_ff_gems: ti.i32,
    use_hints: ti.template(),
    prune_plateaus: ti.template(),
    out_gems: ti.template(),  # [pp, cm, fm, ov] for this combo when key != 0
) -> ti.u64:
    """
    Like _compute_combo_key_warmstart(), but with per-genome FT/FF headroom precomputed.

    This avoids recomputing remaining/max headroom for every combo iteration on Vulkan.
    """
    GEM_STAT_TO_ELEMENT: ti.i32 = 3

    out_key = ti.u64(0)
    out_gems[0] = 0
    out_gems[1] = 0
    out_gems[2] = 0
    out_gems[3] = 0

    if combo_idx < n_combos:
        ft: ti.i32 = kernels_helpers.ftff_combo_ft[combo_idx]
        ff: ti.i32 = kernels_helpers.ftff_combo_ff[combo_idx]

        if (ft + ff) <= combo_budget and ft <= max_ft_gems and ff <= ti.min(combo_budget - ft, max_ff_gems):
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

            pruned: ti.i32 = 0
            if ti.static(prune_plateaus):
                sig0 = kernels_helpers.grid_sig0[song_slot, ft_idx, ff_idx]
                sig1 = kernels_helpers.grid_sig1[song_slot, ft_idx, ff_idx]

                if pruned == 0 and w_ft == 0 and ft > 0:
                    ft2 = ft - 1
                    ff2 = ff
                    if ff2 <= ti.min(combo_budget - ft2, max_ff_gems):
                        ft2_val = ft_stat_val - gem_scale_fever
                        ft2_idx = ti.min(MAX_STAT, ti.max(0, ft2_val))
                        if _same_grid_sig(song_slot, sig0, sig1, ft2_idx, ff_idx) != 0:
                            pruned = 1

                if pruned == 0 and w_ff == 0 and ff > 0:
                    ft2 = ft
                    ff2 = ff - 1
                    if ff2 <= ti.min(combo_budget - ft2, max_ff_gems):
                        ff2_val = ff_stat_val - gem_scale_fever
                        ff2_idx = ti.min(MAX_STAT, ti.max(0, ff2_val))
                        if _same_grid_sig(song_slot, sig0, sig1, ft_idx, ff2_idx) != 0:
                            pruned = 1

                if pruned == 0 and w_ft > w_ff and ff > 0 and (ft + 1) <= max_ft_gems:
                    ft2 = ft + 1
                    ff2 = ff - 1
                    if ff2 <= ti.min(combo_budget - ft2, max_ff_gems):
                        ft2_val = ft_stat_val + gem_scale_fever
                        ff2_val = ff_stat_val - gem_scale_fever
                        ft2_idx = ti.min(MAX_STAT, ti.max(0, ft2_val))
                        ff2_idx = ti.min(MAX_STAT, ti.max(0, ff2_val))
                        if _same_grid_sig(song_slot, sig0, sig1, ft2_idx, ff2_idx) != 0:
                            pruned = 1

                if pruned == 0 and w_ft < w_ff and ft > 0 and (ff + 1) <= max_ff_gems:
                    ft2 = ft - 1
                    ff2 = ff + 1
                    if ff2 <= ti.min(combo_budget - ft2, max_ff_gems):
                        ft2_val = ft_stat_val - gem_scale_fever
                        ff2_val = ff_stat_val + gem_scale_fever
                        ft2_idx = ti.min(MAX_STAT, ti.max(0, ft2_val))
                        ff2_idx = ti.min(MAX_STAT, ti.max(0, ff2_val))
                        if _same_grid_sig(song_slot, sig0, sig1, ft2_idx, ff2_idx) != 0:
                            pruned = 1

                if pruned == 0 and w_ff == w_ft and w_ft != 0 and ft > 0 and (ff + 1) <= max_ff_gems:
                    ft2 = ft - 1
                    ff2 = ff + 1
                    if ff2 <= ti.min(combo_budget - ft2, max_ff_gems):
                        ft2_val = ft_stat_val - gem_scale_fever
                        ff2_val = ff_stat_val + gem_scale_fever
                        ft2_idx = ti.min(MAX_STAT, ti.max(0, ft2_val))
                        ff2_idx = ti.min(MAX_STAT, ti.max(0, ff2_val))
                        if _same_grid_sig(song_slot, sig0, sig1, ft2_idx, ff2_idx) != 0:
                            pruned = 1

            if pruned == 0:
                count_fever: ti.i32 = kernels_helpers.grid_count_body_fever[song_slot, ft_idx, ff_idx]
                count_normal: ti.i32 = kernels_helpers.grid_count_body_normal[song_slot, ft_idx, ff_idx]
                head_len: ti.i32 = kernels_helpers.grid_head_len[song_slot, ft_idx, ff_idx]

                budget: ti.i32 = combo_budget - ft - ff

                p_val: ti.i32 = (
                    base_p_val + (ft * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff * GEM_STAT_TO_ELEMENT * is_p_ff)
                )
                s_val: ti.i32 = (
                    base_s_val + (ft * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff * GEM_STAT_TO_ELEMENT * is_s_ff)
                )

                res_vec = ti.Vector([0, 0, 0, 0, 0, 0, 0])
                if ti.static(use_hints):
                    hint = kernels_helpers.genome_hint_allocation[genome_idx]
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
                    out_key = (ti.cast(score + 1, ti.u64) << 32) | ti.cast(combo_idx, ti.u64)
                    out_gems[0] = res_vec[1]
                    out_gems[1] = res_vec[2]
                    out_gems[2] = res_vec[3]
                    out_gems[3] = res_vec[4]

    return out_key


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
    reuse_exact_eval_results: ti.i32,
):
    """
    GPU-parallel evaluation with optional warm-start from hints.

    When use_hints=1, uses local_search_from_hint() with the genome's stored hint.
    When use_hints=0, falls back to full optimize_core_device() (cold start).

    Vulkan path also caches winning [pp, cm, fm, ov] gem allocations into
    chunk_best_results so materialization kernels can avoid re-running scoring.

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
    GEM_STAT_TO_ELEMENT: ti.i32 = 3

    # FT/FF elemental contribution weights in base_value space (2*p + s).
    # Each FT/FF gem adds GEM_STAT_TO_ELEMENT to the corresponding color stat.
    w_ft: ti.i32 = GEM_STAT_TO_ELEMENT * ((is_p_ft << 1) + is_s_ft)
    w_ff: ti.i32 = GEM_STAT_TO_ELEMENT * ((is_p_ff << 1) + is_s_ff)

    if ti.static(IS_METAL):
        # Metal: keep the original per-combo score atomic approach (no u64 atomics).
        ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
        for genome_idx, local_c in ti.ndrange(n_genomes, combo_count):
            if reuse_exact_eval_results != 0 and kernels_helpers.ga_exact_eval_rep_idx[genome_idx] != genome_idx:
                continue
            combo_idx: ti.i32 = combo_offset + local_c
            scratch = ti.Vector.zero(ti.i32, 4)
            key = _compute_combo_key_warmstart(
                genome_idx,
                combo_idx,
                n_combos,
                total_budget,
                gem_scale_fever,
                is_p_ft,
                is_s_ft,
                is_p_ff,
                is_s_ff,
                is_p_pp,
                is_s_pp,
                is_p_cm,
                is_s_cm,
                is_p_fm,
                is_s_fm,
                is_p_ov,
                is_s_ov,
                song_slot,
                w_ft,
                w_ff,
                use_hints,
                prune_plateaus,
                scratch,
            )
            if key != 0:
                score = ti.cast((key >> 32), ti.i32) - 1
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
        # Full-lane shared buffers for deterministic, portable reductions.
        # Avoid simt.subgroup.* here: we've observed rare nondeterministic failures on Vulkan/AMD
        # where some genomes can fail to publish a non-zero best key (yielding score=-1).
        shared_lane_key = simt.block.SharedArray((kernels_helpers.GA_FTFF_REDUCE_BLOCK_DIM,), ti.u64)
        shared_lane_pp = simt.block.SharedArray((kernels_helpers.GA_FTFF_REDUCE_BLOCK_DIM,), ti.i32)
        shared_lane_cm = simt.block.SharedArray((kernels_helpers.GA_FTFF_REDUCE_BLOCK_DIM,), ti.i32)
        shared_lane_fm = simt.block.SharedArray((kernels_helpers.GA_FTFF_REDUCE_BLOCK_DIM,), ti.i32)
        shared_lane_ov = simt.block.SharedArray((kernels_helpers.GA_FTFF_REDUCE_BLOCK_DIM,), ti.i32)
        total_threads = n_genomes * block_dim

        ti.loop_config(block_dim=kernels_helpers.GA_FTFF_REDUCE_BLOCK_DIM)
        for tid in range(total_threads):
            # On Vulkan, `simt.block.global_thread_idx()` is not consistently available across Taichi builds.
            # Use the real global invocation id for the block mapping when available, and the real SPIR-V
            # `localInvocationId` for lane-local shared memory indexing.
            #
            # Some Taichi/Vulkan builds can remap the Python loop index; using `tid` for block assignment
            # can therefore cause cross-genome interference in shared memory and sporadic score=-1 results.
            tid_global = tid
            if ti.static(hasattr(simt.block, "global_thread_idx")):
                tid_global = ti.cast(simt.block.global_thread_idx(), ti.i32)
            genome_idx = tid_global // block_dim
            lane = ti.cast(simt.block.thread_idx(), ti.i32)
            if genome_idx >= n_genomes:
                continue

            if lane < waves:
                shared_waves_key[lane] = ti.u64(0)
                shared_waves_pp[lane] = 0
                shared_waves_cm[lane] = 0
                shared_waves_fm[lane] = 0
                shared_waves_ov[lane] = 0
            simt.block.sync()

            is_rep: ti.i32 = 1
            if reuse_exact_eval_results != 0 and kernels_helpers.ga_exact_eval_rep_idx[genome_idx] != genome_idx:
                is_rep = 0

            local_best_key = ti.u64(0)
            local_pp = ti.i32(0)
            local_cm = ti.i32(0)
            local_fm = ti.i32(0)
            local_ov = ti.i32(0)

            scratch = ti.Vector.zero(ti.i32, 4)
            local_c: ti.i32 = lane
            while local_c < combo_count:
                if is_rep != 0:
                    combo_idx: ti.i32 = combo_offset + local_c
                    key = _compute_combo_key_warmstart(
                        genome_idx,
                        combo_idx,
                        n_combos,
                        total_budget,
                        gem_scale_fever,
                        is_p_ft,
                        is_s_ft,
                        is_p_ff,
                        is_s_ff,
                        is_p_pp,
                        is_s_pp,
                        is_p_cm,
                        is_s_cm,
                        is_p_fm,
                        is_s_fm,
                        is_p_ov,
                        is_s_ov,
                        song_slot,
                        w_ft,
                        w_ff,
                        use_hints,
                        prune_plateaus,
                        scratch,
                    )
                    if key > local_best_key:
                        local_best_key = key
                        local_pp = scratch[0]
                        local_cm = scratch[1]
                        local_fm = scratch[2]
                        local_ov = scratch[3]

                local_c += block_dim

            # Publish per-lane bests into shared memory.
            shared_lane_key[lane] = local_best_key
            shared_lane_pp[lane] = local_pp
            shared_lane_cm[lane] = local_cm
            shared_lane_fm[lane] = local_fm
            shared_lane_ov[lane] = local_ov
            simt.block.sync()

            # Reduce within each 32-lane wave deterministically.
            wave_lane = lane & 31
            for offset in ti.static([16, 8, 4, 2, 1]):
                if wave_lane < offset:
                    other = lane + offset
                    other_key = shared_lane_key[other]
                    if other_key > shared_lane_key[lane]:
                        shared_lane_key[lane] = other_key
                        shared_lane_pp[lane] = shared_lane_pp[other]
                        shared_lane_cm[lane] = shared_lane_cm[other]
                        shared_lane_fm[lane] = shared_lane_fm[other]
                        shared_lane_ov[lane] = shared_lane_ov[other]
                simt.block.sync()

            # Wave leaders publish into the wave-stride scratch for the final block reduce.
            if wave_lane == 0:
                wave_slot = lane >> 5  # lane//32 (two slots per wave64 subgroup; unused slots stay 0)
                shared_waves_key[wave_slot] = shared_lane_key[lane]
                shared_waves_pp[wave_slot] = shared_lane_pp[lane]
                shared_waves_cm[wave_slot] = shared_lane_cm[lane]
                shared_waves_fm[wave_slot] = shared_lane_fm[lane]
                shared_waves_ov[wave_slot] = shared_lane_ov[lane]
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
