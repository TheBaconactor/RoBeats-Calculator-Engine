"""
Taichi Kernels - Materialize best results from packed keys.

Includes:
- ga_write_best_results_from_key_kernel
- ga_write_best_and_update_global_kernel
"""

import sys

import taichi as ti

from .. import kernels_helpers
from ..kernels_scoring import calc_score_with_grid, optimize_core_device

# Platform detection for atomic operations
IS_METAL = sys.platform == "darwin"


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
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
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

    pp_stat: ti.i32 = ti.min(MAX_STAT, base_pp + (pp_gems * GEM_STAT_TO_ELEMENT))
    cm_stat: ti.i32 = ti.min(MAX_STAT, base_cm + (cm_gems * GEM_STAT_TO_ELEMENT))
    fm_stat: ti.i32 = ti.min(MAX_STAT, base_fm + (fm_gems * GEM_STAT_TO_ELEMENT))

    p_val: ti.i32 = (
        base_p_val
        + (ft * GEM_STAT_TO_ELEMENT * is_p_ft)
        + (ff * GEM_STAT_TO_ELEMENT * is_p_ff)
        + (pp_gems * GEM_STAT_TO_ELEMENT * is_p_pp)
        + (cm_gems * GEM_STAT_TO_ELEMENT * is_p_cm)
        + (fm_gems * GEM_STAT_TO_ELEMENT * is_p_fm)
        + (ov_gems * GEM_STAT_TO_ELEMENT * is_p_ov)
    )
    s_val: ti.i32 = (
        base_s_val
        + (ft * GEM_STAT_TO_ELEMENT * is_s_ft)
        + (ff * GEM_STAT_TO_ELEMENT * is_s_ff)
        + (pp_gems * GEM_STAT_TO_ELEMENT * is_s_pp)
        + (cm_gems * GEM_STAT_TO_ELEMENT * is_s_cm)
        + (fm_gems * GEM_STAT_TO_ELEMENT * is_s_fm)
        + (ov_gems * GEM_STAT_TO_ELEMENT * is_s_ov)
    )

    pp_factor = kernels_helpers.lookup_ref_pp(pp_stat)
    combo_mul = kernels_helpers.lookup_ref_cm(cm_stat)
    fever_mul = kernels_helpers.lookup_ref_fm(fm_stat)
    base_value = ti.cast((p_val * 2) + s_val, ti.f32) + pp_factor

    return calc_score_with_grid(
        base_value,
        combo_mul,
        fever_mul,
        song_slot,
        ft_idx,
        ff_idx,
        head_len,
        count_fever,
        count_normal,
    )


@ti.kernel
def ga_write_best_results_from_key_kernel(
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
    """
    Finalize best (ft, ff, gem counts) per genome from chunk_best_key.

    Unpacks the best combo index from each genome's key and writes:
      - genome_result_stats[g] = [score, ft, ff, pp, cm, fm, ov]
      - ga_scores[g] = score

    Vulkan path reads cached gem allocations from chunk_best_results (filled during
    combo search). Metal keeps re-eval fallback because it reduces by score atomics.

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
        best_key = ti.u64(0)

        if ti.static(not IS_METAL):
            best_key = kernels_helpers.chunk_best_key[genome_idx]
            for t in ti.static(range(kernels_helpers.CHUNK_BEST_KEY_TILES)):
                k = kernels_helpers.chunk_best_key_tiles[genome_idx, t]
                if k > best_key:
                    best_key = k
            if best_key != 0:
                combo_idx = ti.cast(best_key & ti.u64(0xFFFFFFFF), ti.i32)
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
        if ti.static(not IS_METAL):
            pp_gems = kernels_helpers.chunk_best_results[genome_idx, 0]
            cm_gems = kernels_helpers.chunk_best_results[genome_idx, 1]
            fm_gems = kernels_helpers.chunk_best_results[genome_idx, 2]
            ov_gems = kernels_helpers.chunk_best_results[genome_idx, 3]
            score: ti.i32 = _score_cached_combo_from_gems(
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

            kernels_helpers.genome_result_stats[genome_idx] = ti.Vector(
                [score, ft, ff, pp_gems, cm_gems, fm_gems, ov_gems]
            )
            kernels_helpers.ga_scores[genome_idx] = score
        else:
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
            kernels_helpers.genome_result_stats[genome_idx] = ti.Vector(
                [
                    score,
                    ft,
                    ff,
                    res_vec[1],  # pp gems
                    res_vec[2],  # cm gems
                    res_vec[3],  # fm gems
                    res_vec[4],  # ov gems
                ]
            )
            kernels_helpers.ga_scores[genome_idx] = score


@ti.kernel
def ga_write_best_and_update_global_kernel(
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
):
    """
    FUSED: Write best results + store hints + update global best in one kernel.

    For each genome:
    1. Unpack best combo_idx from chunk_best_key (or chunk_best_idx on Metal)
    2. Resolve gems for this combo (cached on Vulkan, re-eval on Metal)
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
        best_key = ti.u64(0)

        if ti.static(not IS_METAL):
            best_key = kernels_helpers.chunk_best_key[genome_idx]
            for t in ti.static(range(kernels_helpers.CHUNK_BEST_KEY_TILES)):
                k = kernels_helpers.chunk_best_key_tiles[genome_idx, t]
                if k > best_key:
                    best_key = k
            if best_key != 0:
                combo_idx = ti.cast(best_key & ti.u64(0xFFFFFFFF), ti.i32)
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
        score: ti.i32 = 0
        pp_gems: ti.i32 = 0
        cm_gems: ti.i32 = 0
        fm_gems: ti.i32 = 0
        ov_gems: ti.i32 = 0

        if ti.static(not IS_METAL):
            pp_gems = kernels_helpers.chunk_best_results[genome_idx, 0]
            cm_gems = kernels_helpers.chunk_best_results[genome_idx, 1]
            fm_gems = kernels_helpers.chunk_best_results[genome_idx, 2]
            ov_gems = kernels_helpers.chunk_best_results[genome_idx, 3]
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

            # Metal keeps re-eval path because its key reduction is score-only atomics.
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

            score = res_vec[0]
            pp_gems = res_vec[1]
            cm_gems = res_vec[2]
            fm_gems = res_vec[3]
            ov_gems = res_vec[4]

        kernels_helpers.genome_result_stats[genome_idx] = ti.Vector([score, ft, ff, pp_gems, cm_gems, fm_gems, ov_gems])
        kernels_helpers.ga_scores[genome_idx] = score

        kernels_helpers.genome_hint_allocation[genome_idx][0] = pp_gems
        kernels_helpers.genome_hint_allocation[genome_idx][1] = cm_gems
        kernels_helpers.genome_hint_allocation[genome_idx][2] = fm_gems
        kernels_helpers.genome_hint_allocation[genome_idx][3] = ov_gems

    # Deterministic global-best update (single thread) to keep score/ids/results aligned.
    for _ in range(1):
        prev_best: ti.i32 = kernels_helpers.ga_global_best_score[0]
        best_score: ti.i32 = prev_best
        best_g: ti.i32 = -1

        for g in range(n_genomes):
            score: ti.i32 = kernels_helpers.ga_scores[g]
            if score > best_score:
                best_score = score
                best_g = g

        if best_g >= 0:
            kernels_helpers.ga_global_best_score[0] = best_score
            for s in range(n_slots):
                kernels_helpers.ga_global_best_genome[s] = kernels_helpers.population_indices[best_g, s]
            res = kernels_helpers.genome_result_stats[best_g]
            for r in ti.static(range(7)):
                kernels_helpers.ga_global_best_results[r] = res[r]


@ti.kernel
def ga_write_best_and_store_hints_kernel(
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
    """
    Materialize best results + store hints (no global-best update).

    This is used for batched multi-run execution where each run is packed into
    a segment of the population arrays and global best is computed during packing.
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160

    for genome_idx in range(n_genomes):
        combo_idx = 0
        valid = False
        best_key = ti.u64(0)

        if ti.static(not IS_METAL):
            best_key = kernels_helpers.chunk_best_key[genome_idx]
            for t in ti.static(range(kernels_helpers.CHUNK_BEST_KEY_TILES)):
                k = kernels_helpers.chunk_best_key_tiles[genome_idx, t]
                if k > best_key:
                    best_key = k
            if best_key != 0:
                combo_idx = ti.cast(best_key & ti.u64(0xFFFFFFFF), ti.i32)
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

        ft: ti.i32 = kernels_helpers.ftff_combo_ft[combo_idx]
        ff: ti.i32 = kernels_helpers.ftff_combo_ff[combo_idx]
        score: ti.i32 = 0
        pp_gems: ti.i32 = 0
        cm_gems: ti.i32 = 0
        fm_gems: ti.i32 = 0
        ov_gems: ti.i32 = 0

        if ti.static(not IS_METAL):
            pp_gems = kernels_helpers.chunk_best_results[genome_idx, 0]
            cm_gems = kernels_helpers.chunk_best_results[genome_idx, 1]
            fm_gems = kernels_helpers.chunk_best_results[genome_idx, 2]
            ov_gems = kernels_helpers.chunk_best_results[genome_idx, 3]
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

            score = res_vec[0]
            pp_gems = res_vec[1]
            cm_gems = res_vec[2]
            fm_gems = res_vec[3]
            ov_gems = res_vec[4]

        kernels_helpers.genome_result_stats[genome_idx] = ti.Vector([score, ft, ff, pp_gems, cm_gems, fm_gems, ov_gems])
        kernels_helpers.ga_scores[genome_idx] = score

        kernels_helpers.genome_hint_allocation[genome_idx][0] = pp_gems
        kernels_helpers.genome_hint_allocation[genome_idx][1] = cm_gems
        kernels_helpers.genome_hint_allocation[genome_idx][2] = fm_gems
        kernels_helpers.genome_hint_allocation[genome_idx][3] = ov_gems
