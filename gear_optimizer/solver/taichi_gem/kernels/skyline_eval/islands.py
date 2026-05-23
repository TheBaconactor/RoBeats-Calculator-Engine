"""
Taichi Kernels - Island elitism.

Includes:
- skyline_find_island_elites_kernel
"""

import taichi as ti

from .. import kernels_helpers


MAX_ELITES_PER_ISLAND = 16  # Static limit for local arrays in island elitism kernel


@ti.kernel
def skyline_find_island_elites_kernel(
    n_genomes: ti.i32,
    n_islands: ti.i32,
    elites_per_island: ti.i32,
):
    """
    GPU-side island elite selection: find top-k genomes per island.

    Uses insertion sort within each thread to find top elites_per_island
    genomes per island, avoiding CPU downloads for elitism.

    Prerequisites:
    - island_boundaries must be uploaded: [start0, start1, ..., end_last]
    - skyline_scores must be populated from evaluation

    Outputs:
    - island_elite_indices: flattened list of elite genome indices
    - island_elite_count: total number of elites (n_islands * elites_per_island)

    Args:
        n_genomes: Total population size
        n_islands: Number of islands (must match island_boundaries)
        elites_per_island: Number of elites to select per island
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)

    for isl in range(n_islands):
        isl_start: ti.i32 = kernels_helpers.island_boundaries[isl]
        isl_end: ti.i32 = kernels_helpers.island_boundaries[isl + 1]
        isl_size: ti.i32 = isl_end - isl_start

        # Local arrays for top-k tracking (insertion sort)
        top_scores = ti.Vector([-1] * MAX_ELITES_PER_ISLAND)
        top_indices = ti.Vector([-1] * MAX_ELITES_PER_ISLAND)

        k: ti.i32 = ti.min(elites_per_island, isl_size)
        k = ti.min(k, MAX_ELITES_PER_ISLAND)

        # Scan all genomes in island, maintain top-k via insertion
        for local_idx in range(isl_size):
            g: ti.i32 = isl_start + local_idx
            score: ti.i32 = kernels_helpers.skyline_scores[g]

            # Check if this score belongs in top-k
            if score > top_scores[k - 1]:
                # Insert in sorted position
                insert_pos: ti.i32 = k - 1
                found_better: ti.i32 = 0
                for j in ti.static(range(MAX_ELITES_PER_ISLAND)):
                    if found_better == 0 and j < k and score > top_scores[j]:
                        insert_pos = j
                        found_better = 1

                # Shift down to make room
                for j in ti.static(range(MAX_ELITES_PER_ISLAND - 1, 0, -1)):
                    if j > insert_pos and j < k:
                        top_scores[j] = top_scores[j - 1]
                        top_indices[j] = top_indices[j - 1]

                top_scores[insert_pos] = score
                top_indices[insert_pos] = g

        # Write elites to output (flattened: island i at offset i * elites_per_island)
        out_base: ti.i32 = isl * elites_per_island
        for j in range(k):
            if top_indices[j] >= 0:
                kernels_helpers.island_elite_indices[out_base + j] = top_indices[j]

    # Set total elite count
    kernels_helpers.island_elite_count[0] = n_islands * elites_per_island
