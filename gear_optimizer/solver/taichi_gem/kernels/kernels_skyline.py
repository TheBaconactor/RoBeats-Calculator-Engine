"""Taichi kernels for exact loadout-candidate aggregation."""

import taichi as ti

from .. import fields as gpu_fields
from . import kernels_helpers

@ti.kernel
def skyline_upload_item_stats_and_slots_kernel(
    item_stats_src: ti.types.ndarray(dtype=ti.i32, ndim=2),
    n_items: ti.i32,
    slot_start_src: ti.types.ndarray(dtype=ti.i32, ndim=1),
    slot_count_src: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    """
    Upload per-item stats and slot pool boundaries without padded CPU buffers.

    This avoids uploading a full MAX_ITEMS x ITEM_STAT_DIM table for every song;
    only the first `n_items` rows are copied.
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for i, j in ti.ndrange(n_items, ti.static(10)):
        kernels_helpers.item_stats[i, j] = item_stats_src[i, j]

    for s in ti.static(range(9)):
        kernels_helpers.slot_start[s] = slot_start_src[s]
        kernels_helpers.slot_count[s] = slot_count_src[s]


@ti.kernel
def skyline_copy_loadout_indices_from_ndarray_kernel(
    n_loadouts: ti.i32,
    n_slots: ti.i32,
    loadout_src: ti.types.ndarray(dtype=ti.i32, ndim=2),
):
    """Copy a variable-length loadout buffer into GPU ``loadout_indices``."""
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for loadout_idx, slot_idx in ti.ndrange(n_loadouts, n_slots):
        kernels_helpers.loadout_indices[loadout_idx, slot_idx] = loadout_src[loadout_idx, slot_idx]

@ti.kernel
def skyline_aggregate_loadouts_and_init_best_kernel(
    n_loadouts: ti.i32,
    n_slots: ti.i32,
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
):
    """Aggregate each loadout's item stats and initialize its exact-result state."""
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)

    for g in range(n_loadouts):
        if ti.static(not gpu_fields.IS_METAL):
            kernels_helpers.chunk_best_key[g] = ti.u64(0)
        else:
            kernels_helpers.chunk_best_score[g] = ti.cast(-2147483648, ti.i32)
            kernels_helpers.chunk_best_idx[g] = -1
        kernels_helpers.chunk_best_results[g, 0] = 0
        kernels_helpers.chunk_best_results[g, 1] = 0
        kernels_helpers.chunk_best_results[g, 2] = 0
        kernels_helpers.chunk_best_results[g, 3] = 0

        pp = kernels_helpers.base_fixed_stats[0]
        cm = kernels_helpers.base_fixed_stats[1]
        fm = kernels_helpers.base_fixed_stats[2]
        ft = kernels_helpers.base_fixed_stats[3]
        ff = kernels_helpers.base_fixed_stats[4]
        beat = kernels_helpers.base_fixed_stats[5]
        vibe = kernels_helpers.base_fixed_stats[6]
        rush = kernels_helpers.base_fixed_stats[7]
        flow = kernels_helpers.base_fixed_stats[8]
        chill = kernels_helpers.base_fixed_stats[9]

        for s in range(n_slots):
            item_id = kernels_helpers.loadout_indices[g, s]
            if item_id > 0:
                pp += kernels_helpers.item_stats[item_id, 0]
                cm += kernels_helpers.item_stats[item_id, 1]
                fm += kernels_helpers.item_stats[item_id, 2]
                ft += kernels_helpers.item_stats[item_id, 3]
                ff += kernels_helpers.item_stats[item_id, 4]
                beat += kernels_helpers.item_stats[item_id, 5]
                vibe += kernels_helpers.item_stats[item_id, 6]
                rush += kernels_helpers.item_stats[item_id, 7]
                flow += kernels_helpers.item_stats[item_id, 8]
                chill += kernels_helpers.item_stats[item_id, 9]

        p_val = (beat * is_p_ft) + (vibe * is_p_ff) + (rush * is_p_fm) + (flow * is_p_cm) + (chill * is_p_pp)
        s_val = (beat * is_s_ft) + (vibe * is_s_ff) + (rush * is_s_fm) + (flow * is_s_cm) + (chill * is_s_pp)

        kernels_helpers.loadout_base_stats[g][0] = ti.cast(pp, ti.i16)
        kernels_helpers.loadout_base_stats[g][1] = ti.cast(cm, ti.i16)
        kernels_helpers.loadout_base_stats[g][2] = ti.cast(fm, ti.i16)
        kernels_helpers.loadout_base_stats[g][3] = ti.cast(p_val, ti.i16)
        kernels_helpers.loadout_base_stats[g][4] = ti.cast(s_val, ti.i16)
        kernels_helpers.loadout_base_stats[g][5] = ti.cast(ft, ti.i16)
        kernels_helpers.loadout_base_stats[g][6] = ti.cast(ff, ti.i16)
