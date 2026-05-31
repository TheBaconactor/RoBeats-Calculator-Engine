"""
Taichi Kernels - Materialize best results from packed keys.

Includes:
- skyline_write_best_results_from_key_kernel
- skyline_write_best_and_update_global_kernel
"""

import sys

import taichi as ti

from .. import kernels_helpers
from ..kernels_scoring import score_solution_from_gems_preloaded
from ..write_results_common import solve_best_combo_uncached

# Platform detection for atomic operations
IS_METAL = sys.platform == "darwin"
# Small populations are faster with a serial scan than a fully contended atomic reduction.
SKYLINE_GLOBAL_BEST_SERIAL_THRESHOLD = 512


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

    count_fever: ti.i32 = kernels_helpers.grid_count_body_fever[song_slot, ft_idx, ff_idx]
    count_normal: ti.i32 = kernels_helpers.grid_count_body_normal[song_slot, ft_idx, ff_idx]
    head_len: ti.i32 = kernels_helpers.grid_head_len[song_slot, ft_idx, ff_idx]

    return score_solution_from_gems_preloaded(
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
        ft_idx,
        ff_idx,
        head_len,
        count_fever,
        count_normal,
    )


@ti.func
def _best_combo_idx_from_chunk_state(genome_idx: ti.i32) -> ti.i32:
    out_idx = ti.i32(-1)
    if ti.static(not IS_METAL):
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
    if ti.static(not IS_METAL):
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
    use_exact_inner_solver: ti.template(),
) -> ti.types.vector(7, ti.i32):
    ft: ti.i32 = kernels_helpers.ftff_combo_ft[combo_idx]
    ff: ti.i32 = kernels_helpers.ftff_combo_ff[combo_idx]
    budget: ti.i32 = total_budget - ft - ff

    score: ti.i32 = -1
    pp_gems: ti.i32 = 0
    cm_gems: ti.i32 = 0
    fm_gems: ti.i32 = 0
    ov_gems: ti.i32 = 0

    if ti.static(not IS_METAL):
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
            )
        else:
            uncached = solve_best_combo_uncached(
                genome_idx,
                ft,
                ff,
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
                use_exact_inner_solver,
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
            use_exact_inner_solver,
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
    if ti.static(not IS_METAL):
        corrected_key: ti.u64 = (ti.cast(result_stats[0] + 1, ti.u64) << ti.u64(32)) | ti.cast(combo_idx, ti.u64)
        kernels_helpers.chunk_best_key[genome_idx] = corrected_key


@ti.func
def _write_invalid_materialized_result(genome_idx: ti.i32):
    kernels_helpers.genome_result_stats[genome_idx] = ti.Vector([-1, 0, 0, 0, 0, 0, 0])
    kernels_helpers.skyline_scores[genome_idx] = -1


@ti.func
def _write_run_best_payload_row(
    run_idx: ti.i32,
    n_slots: ti.i32,
    best_g: ti.i32,
    result_stats: ti.types.vector(7, ti.i32),
):
    kernels_helpers.skyline_runs_payload_packed[run_idx, 0, 0] = result_stats[0]
    for s in range(n_slots):
        kernels_helpers.skyline_runs_payload_packed[run_idx, 0, 1 + s] = kernels_helpers.population_indices[best_g, s]
    for j in ti.static(range(7)):
        kernels_helpers.skyline_runs_payload_packed[run_idx, 0, 1 + n_slots + j] = result_stats[j]


@ti.kernel
def skyline_write_best_results_from_key_kernel(
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
    use_exact_inner_solver: ti.template(),
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
            use_exact_inner_solver,
        )
        _write_materialized_result(genome_idx, combo_idx, result_stats)


@ti.kernel
def skyline_write_best_results_and_update_runs_best_kernel(
    run_idx_start: ti.i32,
    n_runs: ti.i32,
    n_genomes_per_run: ti.i32,
    n_slots: ti.i32,
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
    use_exact_inner_solver: ti.template(),
):
    """
    FUSED: materialize per-genome best results and refresh per-run best rows.
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    n_total = n_runs * n_genomes_per_run

    for genome_idx in range(n_total):
        combo_idx = _best_combo_idx_from_chunk_state(genome_idx)
        if combo_idx < 0:
            _write_invalid_materialized_result(genome_idx)
            continue

        result_stats = _materialize_best_combo_stats(
            genome_idx,
            combo_idx,
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
            use_exact_inner_solver,
        )
        _write_materialized_result(genome_idx, combo_idx, result_stats)

    for r in range(n_runs):
        start_offset: ti.i32 = r * n_genomes_per_run
        best_score: ti.i32 = -1
        best_g: ti.i32 = start_offset
        for local_g in range(n_genomes_per_run):
            g = start_offset + local_g
            score = kernels_helpers.skyline_scores[g]
            if score > best_score:
                best_score = score
                best_g = g

        run_idx = run_idx_start + r
        prev_best: ti.i32 = kernels_helpers.skyline_runs_payload_packed[run_idx, 0, 0]
        if best_score > prev_best:
            res_best = kernels_helpers.genome_result_stats[best_g]
            _write_run_best_payload_row(run_idx, n_slots, best_g, res_best)


@ti.kernel
def skyline_refresh_scores_and_update_runs_best_kernel(
    run_idx_start: ti.i32,
    n_runs: ti.i32,
    n_genomes_per_run: ti.i32,
    n_slots: ti.i32,
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
    use_exact_inner_solver: ti.template(),
):
    """
    Lightweight live-score refresh:
    - keep `skyline_scores` exact from the reduction state
    - refresh per-run row 0 with exact materialization only when improved
    - avoid full-pop `genome_result_stats` writes
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    n_total = n_runs * n_genomes_per_run

    for genome_idx in range(n_total):
        kernels_helpers.skyline_scores[genome_idx] = _best_score_from_chunk_state(genome_idx)

    for r in range(n_runs):
        start_offset: ti.i32 = r * n_genomes_per_run
        best_score: ti.i32 = -1
        best_g: ti.i32 = start_offset
        for local_g in range(n_genomes_per_run):
            g = start_offset + local_g
            score = kernels_helpers.skyline_scores[g]
            if score > best_score:
                best_score = score
                best_g = g

        run_idx = run_idx_start + r
        prev_best: ti.i32 = kernels_helpers.skyline_runs_payload_packed[run_idx, 0, 0]
        if best_score > prev_best:
            combo_idx = _best_combo_idx_from_chunk_state(best_g)
            if combo_idx >= 0:
                result_stats = _materialize_best_combo_stats(
                    best_g,
                    combo_idx,
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
                    use_exact_inner_solver,
                )
                _write_run_best_payload_row(run_idx, n_slots, best_g, result_stats)


@ti.kernel
def skyline_write_best_and_update_global_kernel(
    n_genomes: ti.i32,
    n_slots: ti.i32,
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
    use_exact_inner_solver: ti.template(),
):
    """
    FUSED: write best results + update global best in one kernel.
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
            use_exact_inner_solver,
        )
        _write_materialized_result(genome_idx, combo_idx, result_stats)

    prev_best: ti.i32 = kernels_helpers.skyline_global_best_score[0]
    if n_genomes <= SKYLINE_GLOBAL_BEST_SERIAL_THRESHOLD:
        best_score_serial: ti.i32 = -1
        best_g_serial: ti.i32 = -1
        for g in range(n_genomes):
            score: ti.i32 = kernels_helpers.skyline_scores[g]
            if score > best_score_serial:
                best_score_serial = score
                best_g_serial = g
        if best_g_serial >= 0 and best_score_serial > prev_best:
            kernels_helpers.skyline_global_best_score[0] = best_score_serial
            for s in range(n_slots):
                kernels_helpers.skyline_global_best_genome[s] = kernels_helpers.population_indices[best_g_serial, s]
            res = kernels_helpers.genome_result_stats[best_g_serial]
            for r in ti.static(range(7)):
                kernels_helpers.skyline_global_best_results[r] = res[r]
    else:
        kernels_helpers.skyline_global_best_scan_key[0] = ti.u64(0)
        for g in range(n_genomes):
            score: ti.i32 = kernels_helpers.skyline_scores[g]
            if score >= 0:
                inv_g: ti.u64 = ti.u64(0xFFFFFFFF) - ti.cast(g, ti.u64)
                key: ti.u64 = (ti.cast(score + 1, ti.u64) << ti.u64(32)) | inv_g
                ti.atomic_max(kernels_helpers.skyline_global_best_scan_key[0], key)

        key = kernels_helpers.skyline_global_best_scan_key[0]
        if key != ti.u64(0):
            best_score: ti.i32 = ti.cast(key >> ti.u64(32), ti.i32) - 1
            if best_score > prev_best:
                inv_g_u32: ti.u32 = ti.cast(key & ti.u64(0xFFFFFFFF), ti.u32)
                best_g: ti.i32 = ti.cast(ti.u32(0xFFFFFFFF) - inv_g_u32, ti.i32)
                kernels_helpers.skyline_global_best_score[0] = best_score
                for s in range(n_slots):
                    kernels_helpers.skyline_global_best_genome[s] = kernels_helpers.population_indices[best_g, s]
                res = kernels_helpers.genome_result_stats[best_g]
                for r in ti.static(range(7)):
                    kernels_helpers.skyline_global_best_results[r] = res[r]
