"""
Taichi Kernels - GPU-side global best tracking.

This GA source module is retained for Skyline's source-derived kernels.
The non-Skyline GA production route tracks per-run best rows instead.
"""

import taichi as ti

from .. import kernels_helpers


@ti.kernel
def ga_init_global_best_kernel():
    kernels_helpers.ga_global_best_score[0] = -1
    kernels_helpers.ga_global_best_scan_key[0] = ti.u64(0)


@ti.kernel
def ga_update_global_best_kernel(n_genomes: ti.i32, n_slots: ti.i32):
    kernels_helpers.ga_global_best_scan_key[0] = ti.u64(0)
    for g in range(n_genomes):
        score: ti.i32 = kernels_helpers.ga_scores[g]
        if score >= 0:
            inv_g: ti.u64 = ti.u64(0xFFFFFFFF) - ti.cast(g, ti.u64)
            key: ti.u64 = (ti.cast(score + 1, ti.u64) << ti.u64(32)) | inv_g
            ti.atomic_max(kernels_helpers.ga_global_best_scan_key[0], key)

    key = kernels_helpers.ga_global_best_scan_key[0]
    if key != ti.u64(0):
        best_score: ti.i32 = ti.cast(key >> ti.u64(32), ti.i32) - 1
        prev_best: ti.i32 = kernels_helpers.ga_global_best_score[0]
        if best_score > prev_best:
            inv_g_u32: ti.u32 = ti.cast(key & ti.u64(0xFFFFFFFF), ti.u32)
            best_g: ti.i32 = ti.cast(ti.u32(0xFFFFFFFF) - inv_g_u32, ti.i32)
            kernels_helpers.ga_global_best_score[0] = best_score
            for s in range(n_slots):
                kernels_helpers.ga_global_best_genome[s] = kernels_helpers.population_indices[best_g, s]
            res = kernels_helpers.genome_result_stats[best_g]
            for r in ti.static(range(7)):
                kernels_helpers.ga_global_best_results[r] = res[r]


@ti.kernel
def ga_pack_global_best_kernel():
    kernels_helpers.ga_global_best_packed[0] = kernels_helpers.ga_global_best_score[0]
    for s in ti.static(range(9)):
        kernels_helpers.ga_global_best_packed[1 + s] = kernels_helpers.ga_global_best_genome[s]
    for r in ti.static(range(7)):
        kernels_helpers.ga_global_best_packed[10 + r] = kernels_helpers.ga_global_best_results[r]
