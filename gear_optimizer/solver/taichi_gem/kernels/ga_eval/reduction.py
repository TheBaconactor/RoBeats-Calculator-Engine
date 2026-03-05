"""
Taichi Kernels - GA evaluation reductions.

Includes:
- init_genome_results_kernel
- init_chunk_best_key_kernel
- reduce_chunk_to_best_key_kernel
- merge_chunk_best_to_genomes_kernel
- ga_clear_chunk_best_key_waves_kernel
- ga_merge_chunk_best_key_waves_to_global_kernel
"""

import sys

import taichi as ti

from .. import kernels_helpers

# Platform detection for atomic operations
IS_METAL = sys.platform == "darwin"


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
            for t in ti.static(range(kernels_helpers.CHUNK_BEST_KEY_TILES)):
                kernels_helpers.chunk_best_key_tiles[g, t] = ti.u64(0)
        else:
            kernels_helpers.chunk_best_score[g] = ti.cast(-2147483648, ti.i32)
            kernels_helpers.chunk_best_idx[g] = -1
        kernels_helpers.chunk_best_results[g, 0] = 0
        kernels_helpers.chunk_best_results[g, 1] = 0
        kernels_helpers.chunk_best_results[g, 2] = 0
        kernels_helpers.chunk_best_results[g, 3] = 0


@ti.kernel
def ga_clear_chunk_best_key_waves_kernel(n_genomes: ti.i32, n_tiles: ti.i32):
    """
    Clear Vulkan FT/FF reduction scratch buffer for the next combo chunk.

    This prepares `chunk_best_key_waves[g, :]` so the FT/FF search kernel can
    write per-wave best keys without atomics.

    Args:
        n_genomes: Number of genomes being evaluated
        n_tiles: Number of 256-combo tiles in this combo chunk
    """
    if ti.static(IS_METAL):
        # Metal path does not allocate the u64 scratch buffer.
        for _ in range(1):
            pass
    else:
        n_entries = n_tiles * ti.cast(kernels_helpers.GA_FTFF_REDUCE_WAVE_STRIDE, ti.i32)
        ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
        for g, i in ti.ndrange(n_genomes, n_entries):
            kernels_helpers.chunk_best_key_waves[g, i] = ti.u64(0)


@ti.kernel
def ga_merge_chunk_best_key_waves_to_global_kernel(n_genomes: ti.i32, n_tiles: ti.i32):
    """
    Merge Vulkan FT/FF reduction scratch buffer into `chunk_best_key`.

    One thread per genome scans the per-wave scratch keys and updates
    `chunk_best_key[g]` with the best key found for this combo chunk.

    Args:
        n_genomes: Number of genomes being evaluated
        n_tiles: Number of 256-combo tiles in this combo chunk
    """
    if ti.static(IS_METAL):
        # Metal path uses chunk_best_score/chunk_best_idx atomics; no u64 scratch exists.
        for _ in range(1):
            pass
    else:
        n_entries = n_tiles * ti.cast(kernels_helpers.GA_FTFF_REDUCE_WAVE_STRIDE, ti.i32)
        ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
        for g in range(n_genomes):
            best = kernels_helpers.chunk_best_key[g]
            for i in range(n_entries):
                k = kernels_helpers.chunk_best_key_waves[g, i]
                if k > best:
                    best = k
            kernels_helpers.chunk_best_key[g] = best


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
def reduce_chunk_to_best_key_ranges_kernel(n_genomes: ti.i32):
    """
    Atomic-free GPU-side reduction using per-genome work-item ranges.

    Each genome owns a contiguous slice of work items in the current chunk
    (defined by chunk_genome_start/chunk_genome_len). This kernel scans those
    ranges and writes the best packed key into chunk_best_key[g].
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        start = kernels_helpers.chunk_genome_start[g]
        count = kernels_helpers.chunk_genome_len[g]

        if ti.static(IS_METAL):
            # Metal: avoid u64 reductions (no 64-bit subgroup ops); write score+idx directly.
            best_score: ti.i32 = ti.cast(-2147483648, ti.i32)
            best_idx: ti.i32 = -1
            if count > 0 and start >= 0:
                end = start + count
                for i in range(start, end):
                    score = kernels_helpers.result_stats[i][0]
                    if score >= 0:
                        if (score > best_score) or (score == best_score and i > best_idx):
                            best_score = score
                            best_idx = i
            kernels_helpers.chunk_best_score[g] = best_score
            kernels_helpers.chunk_best_idx[g] = best_idx
        else:
            best = ti.u64(0)
            if count > 0 and start >= 0:
                end = start + count
                for i in range(start, end):
                    score = kernels_helpers.result_stats[i][0]
                    if score >= 0:
                        key = (ti.cast(score + 1, ti.u64) << 32) | ti.cast(i, ti.u64)
                        if key > best:
                            best = key
            kernels_helpers.chunk_best_key[g] = best


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
            valid = i >= 0

        if valid:
            if score > kernels_helpers.genome_result_stats[g][0]:
                item = kernels_helpers.work_items[i]
                res = kernels_helpers.result_stats[i]
                kernels_helpers.genome_result_stats[g] = ti.Vector(
                    [
                        score,
                        item[3],  # ft
                        item[4],  # ff
                        res[1],  # pp
                        res[2],  # cm
                        res[3],  # fm
                        res[4],  # ov
                    ]
                )
