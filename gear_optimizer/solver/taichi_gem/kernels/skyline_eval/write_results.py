"""Materialize exact candidate scores and result rows from packed keys."""

import taichi as ti

from ... import fields as gpu_fields
from .. import kernels_helpers
from ..write_results_common import solve_best_combo_uncached

@ti.func
def _best_combo_idx_from_chunk_state(loadout_idx: ti.i32) -> ti.i32:
    out_idx = ti.i32(-1)
    if ti.static(not gpu_fields.IS_METAL):
        best_key = kernels_helpers.chunk_best_key[loadout_idx]
        if best_key != ti.u64(0):
            out_idx = ti.cast(best_key & ti.u64(0xFFFFFFFF), ti.i32)
    else:
        best_idx = kernels_helpers.chunk_best_idx[loadout_idx]
        if best_idx >= 0:
            out_idx = best_idx
    return out_idx


@ti.func
def _best_score_from_chunk_state(loadout_idx: ti.i32) -> ti.i32:
    out_score = ti.i32(-1)
    if ti.static(not gpu_fields.IS_METAL):
        best_key = kernels_helpers.chunk_best_key[loadout_idx]
        if best_key != ti.u64(0):
            out_score = ti.cast(best_key >> ti.u64(32), ti.i32) - 1
    else:
        best_idx = kernels_helpers.chunk_best_idx[loadout_idx]
        if best_idx >= 0:
            out_score = kernels_helpers.chunk_best_score[loadout_idx]
    return out_score


@ti.kernel
def skyline_write_scores_from_key_kernel(n_loadouts: ti.i32):
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for loadout_idx in range(n_loadouts):
        kernels_helpers.skyline_scores[loadout_idx] = _best_score_from_chunk_state(loadout_idx)


@ti.func
def _materialize_best_combo_stats(
    loadout_idx: ti.i32,
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
) -> ti.types.vector(7, ti.i32):
    ft: ti.i32 = kernels_helpers.ftff_combo_ft[combo_idx]
    ff: ti.i32 = kernels_helpers.ftff_combo_ff[combo_idx]
    score: ti.i32 = -1
    pp_gems: ti.i32 = 0
    cm_gems: ti.i32 = 0
    fm_gems: ti.i32 = 0
    ov_gems: ti.i32 = 0

    # The Vulkan warmstart reduction intentionally retains only the packed
    # (score, combo) key.  ``chunk_best_results`` is not row-aligned with that
    # winning key and a coincidentally valid gem-sum can belong to another
    # combo.  Always reconstruct the selected combo from the authoritative
    # inner solver; candidate-surface materialization is small and requires the
    # score/result row to be bit-identical to the exact scan.
    uncached = solve_best_combo_uncached(
        loadout_idx,
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
        True,
    )
    score = uncached[0]
    pp_gems = uncached[1]
    cm_gems = uncached[2]
    fm_gems = uncached[3]
    ov_gems = uncached[4]

    return ti.Vector([score, ft, ff, pp_gems, cm_gems, fm_gems, ov_gems])


@ti.func
def _write_materialized_result(loadout_idx: ti.i32, combo_idx: ti.i32, result_stats: ti.types.vector(7, ti.i32)):
    kernels_helpers.loadout_result_stats[loadout_idx] = result_stats
    kernels_helpers.skyline_scores[loadout_idx] = result_stats[0]
    if ti.static(not gpu_fields.IS_METAL):
        corrected_key: ti.u64 = (ti.cast(result_stats[0] + 1, ti.u64) << ti.u64(32)) | ti.cast(combo_idx, ti.u64)
        kernels_helpers.chunk_best_key[loadout_idx] = corrected_key


@ti.func
def _write_invalid_materialized_result(loadout_idx: ti.i32):
    kernels_helpers.loadout_result_stats[loadout_idx] = ti.Vector([-1, 0, 0, 0, 0, 0, 0])
    kernels_helpers.skyline_scores[loadout_idx] = -1


@ti.kernel
def skyline_write_best_results_from_key_kernel(
    n_loadouts: ti.i32,
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
    """Finalize best (ft, ff, gem counts) per loadout from ``chunk_best_key``."""
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)

    for loadout_idx in range(n_loadouts):
        combo_idx = _best_combo_idx_from_chunk_state(loadout_idx)
        if combo_idx < 0:
            _write_invalid_materialized_result(loadout_idx)
            continue

        result_stats = _materialize_best_combo_stats(
            loadout_idx,
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
        )
        _write_materialized_result(loadout_idx, combo_idx, result_stats)
