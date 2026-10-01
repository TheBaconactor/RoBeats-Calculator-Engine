"""
Taichi Kernels - Materialize best results from packed keys.

Includes:
- skyline_write_scores_from_key_kernel
- skyline_write_best_results_from_key_kernel
"""

import taichi as ti

from ... import fields as gpu_fields
from .. import kernels_helpers
from ..kernels_helpers import GpuColorFlags
from ..kernels_scoring import score_solution_from_gems_frontier
from ..write_results_common import solve_best_combo_uncached


@ti.func
def _score_cached_combo_from_gems(
    genome_idx: ti.i32,
    ft: ti.i32,
    ff: ti.i32,
    pp_gems: ti.i32,
    cm_gems: ti.i32,
    fm_gems: ti.i32,
    ov_gems: ti.i32,
    gem_scale_fever: ti.i32,
    flags: GpuColorFlags,
    song_slot: ti.i32,
) -> ti.i32:
    MAX_STAT: ti.i32 = 160

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

    head_len: ti.i32 = kernels_helpers.grid_head_len[song_slot, ft_idx, ff_idx]

    return score_solution_from_gems_frontier(
        ft,
        ff,
        pp_gems,
        cm_gems,
        fm_gems,
        ov_gems,
        base_pp,
        base_cm,
        base_fm,
        base_p_val,
        base_s_val,
        base_ft_stat,
        base_ff_stat,
        gem_scale_fever,
        flags,
        song_slot,
        ft_idx,
        ff_idx,
        head_len,
    )


@ti.func
def _best_combo_idx_from_chunk_state(genome_idx: ti.i32) -> ti.i32:
    out_idx = ti.i32(-1)
    if ti.static(not gpu_fields.IS_METAL):
        best_key = kernels_helpers.chunk_best_key[genome_idx]
        if best_key != ti.u64(0):
            out_idx = ti.cast(best_key & ti.u64(0xFFFFFFFF), ti.i32)
    else:
        best_idx = kernels_helpers.chunk_best_idx[genome_idx]
        if best_idx >= 0:
            out_idx = best_idx
    return out_idx


@ti.func
def _best_score_from_chunk_state(genome_idx: ti.i32) -> ti.i32:
    out_score = ti.i32(-1)
    if ti.static(not gpu_fields.IS_METAL):
        best_key = kernels_helpers.chunk_best_key[genome_idx]
        if best_key != ti.u64(0):
            out_score = ti.cast(best_key >> ti.u64(32), ti.i32) - 1
    else:
        best_idx = kernels_helpers.chunk_best_idx[genome_idx]
        if best_idx >= 0:
            out_score = kernels_helpers.chunk_best_score[genome_idx]
    return out_score


@ti.kernel
def skyline_write_scores_from_key_kernel(n_genomes: ti.i32):
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for genome_idx in range(n_genomes):
        kernels_helpers.skyline_scores[genome_idx] = _best_score_from_chunk_state(genome_idx)


@ti.func
def _materialize_best_combo_stats(
    genome_idx: ti.i32,
    combo_idx: ti.i32,
    total_budget: ti.i32,
    gem_scale_fever: ti.i32,
    flags: GpuColorFlags,
    song_slot: ti.i32,
) -> ti.types.vector(7, ti.i32):
    ft: ti.i32 = kernels_helpers.ftff_combo_ft[combo_idx]
    ff: ti.i32 = kernels_helpers.ftff_combo_ff[combo_idx]
    budget: ti.i32 = total_budget - ft - ff

    score: ti.i32 = -1
    pp_gems: ti.i32 = 0
    cm_gems: ti.i32 = 0
    fm_gems: ti.i32 = 0
    ov_gems: ti.i32 = 0

    if ti.static(not gpu_fields.IS_METAL):
        pp_gems = kernels_helpers.chunk_best_results[genome_idx, 0]
        cm_gems = kernels_helpers.chunk_best_results[genome_idx, 1]
        fm_gems = kernels_helpers.chunk_best_results[genome_idx, 2]
        ov_gems = kernels_helpers.chunk_best_results[genome_idx, 3]

        cached_sum: ti.i32 = pp_gems + cm_gems + fm_gems + ov_gems
        if cached_sum == budget and pp_gems >= 0 and cm_gems >= 0 and fm_gems >= 0 and ov_gems >= 0:
            score = _score_cached_combo_from_gems(
                genome_idx,
                ft,
                ff,
                pp_gems,
                cm_gems,
                fm_gems,
                ov_gems,
                gem_scale_fever,
                flags,
                song_slot,
            )
        else:
            uncached = solve_best_combo_uncached(
                genome_idx,
                ft,
                ff,
                total_budget,
                gem_scale_fever,
                flags,
                song_slot,
                False,
            )
            score = uncached[0]
            pp_gems = uncached[1]
            cm_gems = uncached[2]
            fm_gems = uncached[3]
            ov_gems = uncached[4]
    else:
        uncached = solve_best_combo_uncached(
            genome_idx,
            ft,
            ff,
            total_budget,
            gem_scale_fever,
            flags,
            song_slot,
            False,
        )
        score = uncached[0]
        pp_gems = uncached[1]
        cm_gems = uncached[2]
        fm_gems = uncached[3]
        ov_gems = uncached[4]

    return ti.Vector([score, ft, ff, pp_gems, cm_gems, fm_gems, ov_gems])


@ti.func
def _write_materialized_result(genome_idx: ti.i32, combo_idx: ti.i32, result_stats: ti.types.vector(7, ti.i32)):
    kernels_helpers.genome_result_stats[genome_idx] = result_stats
    kernels_helpers.skyline_scores[genome_idx] = result_stats[0]
    if ti.static(not gpu_fields.IS_METAL):
        corrected_key: ti.u64 = (ti.cast(result_stats[0] + 1, ti.u64) << ti.u64(32)) | ti.cast(combo_idx, ti.u64)
        kernels_helpers.chunk_best_key[genome_idx] = corrected_key


@ti.func
def _write_invalid_materialized_result(genome_idx: ti.i32):
    kernels_helpers.genome_result_stats[genome_idx] = ti.Vector([-1, 0, 0, 0, 0, 0, 0])
    kernels_helpers.skyline_scores[genome_idx] = -1


@ti.kernel
def skyline_write_best_results_from_key_kernel(
    n_genomes: ti.i32,
    total_budget: ti.i32,
    gem_scale_fever: ti.i32,
    flags: GpuColorFlags,
    song_slot: ti.i32,
):
    """
    Finalize best (ft, ff, gem counts) per genome from chunk_best_key.
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)

    for genome_idx in range(n_genomes):
        combo_idx = _best_combo_idx_from_chunk_state(genome_idx)
        if combo_idx < 0:
            _write_invalid_materialized_result(genome_idx)
            continue

        result_stats = _materialize_best_combo_stats(
            genome_idx,
            combo_idx,
            total_budget,
            gem_scale_fever,
            flags,
            song_slot,
        )
        _write_materialized_result(genome_idx, combo_idx, result_stats)


