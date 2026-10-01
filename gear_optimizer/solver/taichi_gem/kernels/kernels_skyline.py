"""
Taichi Kernels - GPU-Native Skyline candidate Operations.

This module contains the kernels that stage and aggregate Skyline candidate populations:
- skyline_upload_item_stats_and_slots_kernel: Upload item stats and slot pools
- skyline_copy_population_indices_from_ndarray_kernel: Upload an encoded population
- skyline_aggregate_and_init_best_kernel: Aggregate stats and initialize each genome's best key
"""

import taichi as ti

from .. import fields as gpu_fields

from . import kernels_helpers
from .kernels_helpers import GpuColorFlags


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
def skyline_copy_population_indices_from_ndarray_kernel(
    n_genomes: ti.i32,
    n_slots: ti.i32,
    population_src: ti.types.ndarray(dtype=ti.i32, ndim=2),
):
    """
    Copy a variable-length population buffer into GPU `population_indices`.

    This avoids full MAX_GENOMES x MAX_SLOTS host padding and upload when only a
    small active population slice is needed.
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for g, s in ti.ndrange(n_genomes, n_slots):
        kernels_helpers.population_indices[g, s] = population_src[g, s]


@ti.kernel
def skyline_aggregate_and_init_best_kernel(
    n_genomes: ti.i32,
    n_slots: ti.i32,
    flags: GpuColorFlags,
    reuse_exact_genome_base_stats: ti.i32,
):
    """
    FUSED: Aggregate item stats AND initialize chunk_best_key in one kernel.

    Aggregates each genome's item stats and initializes its chunk_best_key in one launch.

    Args:
        n_genomes: Number of genomes
        n_slots: Number of equipment slots
        flags: the song's color flags (GpuColorFlags)
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)

    # Platform detection for atomic operations

    for g in range(n_genomes):
        if ti.static(not gpu_fields.IS_METAL):
            kernels_helpers.chunk_best_key[g] = ti.u64(0)
        else:
            kernels_helpers.chunk_best_score[g] = ti.cast(-2147483648, ti.i32)
            kernels_helpers.chunk_best_idx[g] = -1
        kernels_helpers.chunk_best_results[g, 0] = 0
        kernels_helpers.chunk_best_results[g, 1] = 0
        kernels_helpers.chunk_best_results[g, 2] = 0
        kernels_helpers.chunk_best_results[g, 3] = 0

        if reuse_exact_genome_base_stats != 0 and kernels_helpers.skyline_exact_eval_rep_idx[g] != g:
            continue

        b = kernels_helpers.base_stats7(
            ti.Vector([kernels_helpers.population_indices[g, s] for s in ti.static(range(9))]), n_slots, flags
        )
        for i in ti.static(range(7)):
            kernels_helpers.genome_base_stats[g][i] = ti.cast(b[i], ti.i16)
