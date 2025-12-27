"""
Taichi Kernels - GA evaluation reductions.

Includes:
- init_genome_results_kernel
- init_chunk_best_key_kernel
- reduce_chunk_to_best_key_kernel
- merge_chunk_best_to_genomes_kernel
"""

import sys

import taichi as ti

from .. import kernels_helpers

# Platform detection for atomic operations
IS_METAL = (sys.platform == "darwin")


@ti.kernel
def init_genome_results_kernel(n_genomes: ti.i32):
    """
    Initialize genome result fields to -1 (no valid result yet).

    Args:
        n_genomes: Number of genomes to initialize
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        kernels_helpers.genome_result_stats[g] = ti.Vector([-1, 0, 0, 0, 0, 0, 0])


@ti.kernel
def init_chunk_best_key_kernel(n_genomes: ti.i32):
    """
    Initialize per-chunk best-key storage.

    Key format: ((score + 1) << 32) | work_item_index.
    A zero key means "no candidate yet".

    Args:
        n_genomes: Number of genomes to initialize keys for
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        if ti.static(not IS_METAL):
            kernels_helpers.chunk_best_key[g] = ti.u64(0)
        else:
            kernels_helpers.chunk_best_score[g] = ti.cast(-2147483648, ti.i32)
            kernels_helpers.chunk_best_idx[g] = -1


@ti.kernel
def reduce_chunk_to_best_key_kernel(n_work_items: ti.i32):
    """
    Race-free GPU-side reduction: find best (score, work_item_index) per genome.

    This avoids the data-race in reduce_chunk_to_genomes_kernel where a losing thread
    could overwrite a winning score by writing a full vector after atomic_max.

    Uses packed key format: ((score + 1) << 32) | work_item_index for atomic operations.

    Args:
        n_work_items: Number of work items to reduce
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for i in range(n_work_items):
        gid = kernels_helpers.work_items[i][6]
        score = kernels_helpers.result_stats[i][0]
        if score >= 0:
            if ti.static(not IS_METAL):
                key = (ti.cast(score + 1, ti.u64) << 32) | ti.cast(i, ti.u64)
                ti.atomic_max(kernels_helpers.chunk_best_key[gid], key)
            else:
                # Metal: update score first, then index (benign race)
                old = ti.atomic_max(kernels_helpers.chunk_best_score[gid], score)
                if old < score:
                    kernels_helpers.chunk_best_idx[gid] = i


@ti.kernel
def merge_chunk_best_to_genomes_kernel(n_genomes: ti.i32):
    """
    Merge this chunk's best candidates into genome_result_stats (one thread per genome).

    Unpacks the best key, retrieves the corresponding work item and result,
    and updates genome_result_stats if the score is better than the current best.

    Args:
        n_genomes: Number of genomes to merge results for
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        score = 0
        i = 0
        valid = False

        if ti.static(not IS_METAL):
            key = kernels_helpers.chunk_best_key[g]
            if key != 0:
                i = ti.cast(key & ti.u64(0xFFFFFFFF), ti.i32)
                score = ti.cast((key >> 32) - 1, ti.i32)
                valid = True
        else:
            score = kernels_helpers.chunk_best_score[g]
            i = kernels_helpers.chunk_best_idx[g]
            valid = (i >= 0)

        if valid:
            if score > kernels_helpers.genome_result_stats[g][0]:
                item = kernels_helpers.work_items[i]
                res = kernels_helpers.result_stats[i]
                kernels_helpers.genome_result_stats[g] = ti.Vector([
                    score,
                    item[3],  # ft
                    item[4],  # ff
                    res[1],   # pp
                    res[2],   # cm
                    res[3],   # fm
                    res[4],   # ov
                ])

