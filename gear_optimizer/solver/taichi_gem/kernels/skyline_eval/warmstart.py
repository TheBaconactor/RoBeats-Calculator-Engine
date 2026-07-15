"""
Taichi Kernels - skyline evaluation.

Includes:
- skyline_find_best_combo_warmstart_kernel
"""

import taichi as ti

from ... import fields as gpu_fields
from .. import kernels_helpers
from ..warmstart_common import MAX_STAT, solve_combo_warmstart_preloaded


@ti.func
def _compute_combo_key_warmstart_preloaded(
    combo_idx: ti.i32,
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
    base_pp: ti.i32,
    base_cm: ti.i32,
    base_fm: ti.i32,
    base_p_val: ti.i32,
    base_s_val: ti.i32,
    base_ft_stat: ti.i32,
    base_ff_stat: ti.i32,
    max_ft_gems: ti.i32,
    max_ff_gems: ti.i32,
) -> ti.u64:
    """
    Compute a packed max-key for one FT/FF combo.

    Returns:
        u64 key in format: ((score + 1) << 32) | combo_idx
        0 when the combo is invalid/pruned or yields a negative score.
    """
    res_vec = solve_combo_warmstart_preloaded(
        combo_idx,
        combo_budget,
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
        base_pp,
        base_cm,
        base_fm,
        base_p_val,
        base_s_val,
        base_ft_stat,
        base_ff_stat,
        max_ft_gems,
        max_ff_gems,
    )
    score = res_vec[0]
    out_key = ti.u64(0)
    if score >= 0:
        out_key = (ti.cast(score + 1, ti.u64) << 32) | ti.cast(combo_idx, ti.u64)
    return out_key


@ti.kernel
def skyline_find_best_combo_warmstart_kernel(
    n_loadouts: ti.i32,
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
    GPU-parallel evaluation with exact per-(loadout, FT/FF) solving.

    Vulkan path reduces the winning key into `chunk_best_key` via an exact
    per-loadout `ti.atomic_max` and intentionally does NOT write
    `chunk_best_results` (materialization validates cached payloads and recomputes
    when needed).

    Args:
        n_loadouts: Number of loadouts to evaluate
        n_combos: Total number of FT/FF combinations
        combo_offset: Starting index in combo tables (for chunked processing)
        combo_count: Number of combos in this chunk
        total_budget: Total gem budget
        gem_scale_fever: Gems per fever stat point
        is_*: Color contribution flags (0/1)
        song_slot: Grid slot for batch coalescing
    """
    if ti.static(gpu_fields.IS_METAL):
        # Metal/MoltenVK has no u64 atomics, so it cannot atomic_max the packed (score, combo_idx)
        # key the way the Vulkan path below does. The previous Metal code split that into
        # atomic_max(score) + a NON-atomic combo_idx write, which RACED: two threads improving the
        # same loadout's score could leave chunk_best_score and chunk_best_idx desynchronized,
        # dropping the optimal allocation (observed as a wrong, ~-21% base re-solve on macOS).
        # Instead, parallelize over loadouts and reduce the combo dimension serially per loadout:
        # each loadout's slot is then owned by exactly one thread, so score and combo_idx always
        # stay paired -- no atomics, no race. Same exact argmax as the Vulkan path; only the
        # reduction strategy differs (required hardware-safety boundary: no u64 atomics on Metal).
        ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
        for loadout_idx in range(n_loadouts):
            stats = kernels_helpers.loadout_base_stats[loadout_idx]
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

            best_score: ti.i32 = -1
            best_idx: ti.i32 = -1
            for local_c in range(combo_count):
                combo_idx: ti.i32 = combo_offset + local_c
                key = _compute_combo_key_warmstart_preloaded(
                    combo_idx,
                    total_budget,  # combo_budget
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
                    base_pp,
                    base_cm,
                    base_fm,
                    base_p_val,
                    base_s_val,
                    base_ft_stat,
                    base_ff_stat,
                    max_ft_gems,
                    max_ff_gems,
                )
                if key != 0:
                    score = ti.cast((key >> 32), ti.i32) - 1
                    # Match the Vulkan packed-key atomic_max tie-break (key = (score+1)<<32 |
                    # combo_idx): on equal score the HIGHEST combo_idx wins, so Mac (f32, serial
                    # reduction) and AMD (f64, u64 atomic) select the same gem layout, not just the
                    # same score.
                    if score > best_score or (score == best_score and combo_idx > best_idx):
                        best_score = score
                        best_idx = combo_idx
            # Single owner thread per loadout -> score and combo_idx stay paired. Accumulate the
            # max across combo chunks (sequential kernel invocations; no cross-thread contention).
            # Same tie-break as the inner loop and the Vulkan path: on an equal-score cross-chunk tie
            # keep the higher combo_idx (later chunks hold higher indices) so the winner matches AMD.
            if best_score >= 0 and (
                best_score > kernels_helpers.chunk_best_score[loadout_idx]
                or (
                    best_score == kernels_helpers.chunk_best_score[loadout_idx]
                    and best_idx > kernels_helpers.chunk_best_idx[loadout_idx]
                )
            ):
                kernels_helpers.chunk_best_score[loadout_idx] = best_score
                kernels_helpers.chunk_best_idx[loadout_idx] = best_idx
    else:
        # Vulkan: use deterministic logical lanes from the loop index and
        # combine per-lane maxima via atomic_max on the packed key only.
        #
        # This keeps combo coverage complete even when Taichi remaps loop
        # iterations to physical invocations, and it avoids carrying cached
        # payloads through the warmstart reduction while we validate key
        # correctness. Materialization will recompute the winning allocation
        # from the selected combo when needed.
        block_dim = ti.cast(kernels_helpers.SKYLINE_FTFF_REDUCE_BLOCK_DIM, ti.i32)
        total_threads = n_loadouts * block_dim

        ti.loop_config(block_dim=kernels_helpers.SKYLINE_FTFF_REDUCE_BLOCK_DIM)
        for tid in range(total_threads):
            loadout_idx = tid // block_dim
            lane = tid - loadout_idx * block_dim

            # Hoist per-loadout values out of the per-combo loop to reduce memory traffic.
            stats = kernels_helpers.loadout_base_stats[loadout_idx]
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

            local_best_key = ti.u64(0)
            local_c: ti.i32 = lane
            while local_c < combo_count:
                combo_idx: ti.i32 = combo_offset + local_c
                res_vec = solve_combo_warmstart_preloaded(
                    combo_idx,
                    total_budget,  # combo_budget
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
                    base_pp,
                    base_cm,
                    base_fm,
                    base_p_val,
                    base_s_val,
                    base_ft_stat,
                    base_ff_stat,
                    max_ft_gems,
                    max_ff_gems,
                )
                score = res_vec[0]
                if score >= 0:
                    key = (ti.cast(score + 1, ti.u64) << 32) | ti.cast(combo_idx, ti.u64)
                    if key > local_best_key:
                        local_best_key = key
                local_c += block_dim

            if local_best_key != ti.u64(0):
                ti.atomic_max(kernels_helpers.chunk_best_key[loadout_idx], local_best_key)
