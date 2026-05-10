"""
Taichi Kernels - GPU-side global best tracking.

Includes:
- SKYLINE_INIT_global_best_kernel
- skyline_update_global_best_kernel
"""

import taichi as ti

from .. import kernels_helpers


@ti.kernel
def SKYLINE_INIT_global_best_kernel():
    """
    Initialize global best tracking fields at the start of a skyline run.

    Sets skyline_global_best_score[0] = -1 (no best yet).
    This should be called once at the start of each skyline run.
    """
    kernels_helpers.skyline_global_best_score[0] = -1
    kernels_helpers.skyline_global_best_scan_key[0] = ti.u64(0)


@ti.kernel
def skyline_update_global_best_kernel(n_genomes: ti.i32, n_slots: ti.i32):
    """
    GPU-side global best update: track best genome across all generations.

    IMPORTANT: This must update `skyline_global_best_score`, `skyline_global_best_genome`, and
    `skyline_global_best_results` *consistently*. The previous atomic-max approach could
    leave the score from one genome but the IDs/results from another due to races.

    Args:
        n_genomes: Number of genomes to check
        n_slots: Number of equipment slots per genome
    """
    # Parallel best-score reduction.
    kernels_helpers.skyline_global_best_scan_key[0] = ti.u64(0)
    for g in range(n_genomes):
        score: ti.i32 = kernels_helpers.skyline_scores[g]
        if score >= 0:
            inv_g: ti.u64 = ti.u64(0xFFFFFFFF) - ti.cast(g, ti.u64)
            key: ti.u64 = (ti.cast(score + 1, ti.u64) << ti.u64(32)) | inv_g
            ti.atomic_max(kernels_helpers.skyline_global_best_scan_key[0], key)

    # Deterministic materialization keeps score/ids/results aligned.
    key = kernels_helpers.skyline_global_best_scan_key[0]
    if key != ti.u64(0):
        best_score: ti.i32 = ti.cast(key >> ti.u64(32), ti.i32) - 1
        prev_best: ti.i32 = kernels_helpers.skyline_global_best_score[0]
        if best_score > prev_best:
            inv_g_u32: ti.u32 = ti.cast(key & ti.u64(0xFFFFFFFF), ti.u32)
            best_g: ti.i32 = ti.cast(ti.u32(0xFFFFFFFF) - inv_g_u32, ti.i32)
            kernels_helpers.skyline_global_best_score[0] = best_score
            for s in range(n_slots):
                kernels_helpers.skyline_global_best_genome[s] = kernels_helpers.population_indices[best_g, s]
            res = kernels_helpers.genome_result_stats[best_g]
            for r in ti.static(range(7)):
                kernels_helpers.skyline_global_best_results[r] = res[r]


@ti.kernel
def skyline_pack_global_best_kernel():
    """
    Pack skyline global best into a single field for efficient download.

    Layout: [score(1), genome_ids(9), results(7)] = 17 values
    This reduces 3 separate to_numpy() calls (3 GPU syncs) to 1.
    """
    # Pack: [score, genome_ids..., results...]
    kernels_helpers.skyline_global_best_packed[0] = kernels_helpers.skyline_global_best_score[0]
    for s in ti.static(range(9)):
        kernels_helpers.skyline_global_best_packed[1 + s] = kernels_helpers.skyline_global_best_genome[s]
    for r in ti.static(range(7)):
        kernels_helpers.skyline_global_best_packed[10 + r] = kernels_helpers.skyline_global_best_results[r]
