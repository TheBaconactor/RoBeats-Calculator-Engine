"""
Taichi Kernels - island elitism.

This GA source module is retained for Skyline's source-derived kernels.
The non-Skyline GA production route computes packed-run island elites inline.
"""

import taichi as ti

from .. import kernels_helpers


MAX_ELITES_PER_ISLAND = 16


@ti.kernel
def ga_find_island_elites_kernel(
    n_genomes: ti.i32,
    n_islands: ti.i32,
    elites_per_island: ti.i32,
):
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)

    for isl in range(n_islands):
        isl_start: ti.i32 = kernels_helpers.island_boundaries[isl]
        isl_end: ti.i32 = kernels_helpers.island_boundaries[isl + 1]
        isl_size: ti.i32 = isl_end - isl_start

        top_scores = ti.Vector([-1] * MAX_ELITES_PER_ISLAND)
        top_indices = ti.Vector([-1] * MAX_ELITES_PER_ISLAND)

        k: ti.i32 = ti.min(elites_per_island, isl_size)
        k = ti.min(k, MAX_ELITES_PER_ISLAND)

        for local_idx in range(isl_size):
            g: ti.i32 = isl_start + local_idx
            score: ti.i32 = kernels_helpers.ga_scores[g]

            if score > top_scores[k - 1]:
                insert_pos: ti.i32 = k - 1
                found_better: ti.i32 = 0
                for j in ti.static(range(MAX_ELITES_PER_ISLAND)):
                    if found_better == 0 and j < k and score > top_scores[j]:
                        insert_pos = j
                        found_better = 1

                for j in ti.static(range(MAX_ELITES_PER_ISLAND - 1, 0, -1)):
                    if j > insert_pos and j < k:
                        top_scores[j] = top_scores[j - 1]
                        top_indices[j] = top_indices[j - 1]

                top_scores[insert_pos] = score
                top_indices[insert_pos] = g

        out_base: ti.i32 = isl * elites_per_island
        for j in range(k):
            if top_indices[j] >= 0:
                kernels_helpers.island_elite_indices[out_base + j] = top_indices[j]

    kernels_helpers.island_elite_count[0] = n_islands * elites_per_island
