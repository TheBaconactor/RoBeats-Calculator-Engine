"""
Taichi Kernels - skyline evaluation.

Includes:
- skyline_find_best_combo_warmstart_kernel
"""

import taichi as ti

from .. import kernels_helpers
from ..kernels_helpers import GpuColorFlags
from .....rules import MAX_STAT
from ..warmstart_common import solve_combo_warmstart_preloaded


@ti.kernel
def skyline_find_best_combo_warmstart_kernel(
    n_genomes: ti.i32,
    combo_offset: ti.i32,
    combo_count: ti.i32,
    total_budget: ti.i32,
    gem_scale_fever: ti.i32,
    flags: GpuColorFlags,
    song_slot: ti.i32,
    reuse_exact_eval_results: ti.template(),
    use_timing_response_antichain: ti.template(),
    score_cull_threshold: ti.i32,
):
    """
    GPU-parallel evaluation with exact per-(genome, FT/FF) solving.

    Vulkan path reduces the winning key into `chunk_best_key` via an exact
    per-genome `ti.atomic_max` and intentionally does NOT write
    `chunk_best_results` (materialization validates cached payloads and recomputes
    when needed).

    Args:
        n_genomes: Number of genomes to evaluate
        n_combos: Total number of FT/FF combinations
        combo_offset: Starting index in combo tables (for chunked processing)
        combo_count: Number of combos in this chunk
        total_budget: Total gem budget
        gem_scale_fever: Gems per fever stat point
        flags: the song's color flags (GpuColorFlags)
        song_slot: Grid slot for batch coalescing
    """
    # One thread per genome reduces the combo dimension serially, so each genome's (score, combo) slot has a
    # single owner: no atomics. Ties keep the higher combo index.
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for genome_idx in range(n_genomes):
        if ti.static(reuse_exact_eval_results):
            if kernels_helpers.skyline_exact_eval_rep_idx[genome_idx] != genome_idx:
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

        best_score: ti.i32 = -1
        best_idx: ti.i32 = -1
        for local_c in range(combo_count):
            combo_idx: ti.i32 = combo_offset + local_c
            res_vec = solve_combo_warmstart_preloaded(
                genome_idx,
                combo_idx,
                total_budget,  # combo_budget
                gem_scale_fever,
                flags,
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
                use_timing_response_antichain,
                score_cull_threshold,
            )
            score = res_vec[0]
            if score >= 0:
                # Match the Vulkan packed-key atomic_max tie-break (key = (score+1)<<32 |
                # combo_idx): on equal score the HIGHEST combo_idx wins, so Mac (f32, serial
                # reduction) and AMD (f64, u64 atomic) select the same gem layout, not just the
                # same score.
                if score > best_score or (score == best_score and combo_idx > best_idx):
                    best_score = score
                    best_idx = combo_idx
        # Single owner thread per genome -> score and combo_idx stay paired. Accumulate the
        # max across combo chunks (sequential kernel invocations; no cross-thread contention).
        # Same tie-break as the inner loop and the Vulkan path: on an equal-score cross-chunk tie
        # keep the higher combo_idx (later chunks hold higher indices) so the winner matches AMD.
        if best_score >= 0 and (
            best_score > kernels_helpers.chunk_best_score[genome_idx]
            or (
                best_score == kernels_helpers.chunk_best_score[genome_idx]
                and best_idx > kernels_helpers.chunk_best_idx[genome_idx]
            )
        ):
            kernels_helpers.chunk_best_score[genome_idx] = best_score
            kernels_helpers.chunk_best_idx[genome_idx] = best_idx
