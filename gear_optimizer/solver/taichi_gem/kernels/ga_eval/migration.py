"""
Taichi Kernels - GPU-side island migration.

Includes:
- ga_island_migration_kernel
"""

import taichi as ti

from .. import kernels_helpers


MAX_MIGRATE_COUNT = 8  # Static limit for local arrays in migration kernel


@ti.kernel
def ga_island_migration_kernel(
    n_genomes: ti.i32,
    n_islands: ti.i32,
    migrate_count: ti.i32,
    n_slots: ti.i32,
):
    """
    GPU-side island migration using ring topology.

    Each island i sends its top-k genomes to island (i+1) % n_islands,
    replacing the worst-k genomes in the destination island.

    This eliminates the expensive CPU round-trip previously required for migration:
    - No ga_download_scores()
    - No ga_download_population_indices()
    - No ga_upload_population_indices()

    Prerequisites:
    - island_boundaries must be uploaded: [start0, start1, ..., end_last]
    - ga_scores must be populated from evaluation

    Args:
        n_genomes: Total population size
        n_islands: Number of islands (must match island_boundaries)
        migrate_count: Number of genomes to migrate per island
        n_slots: Number of equipment slots per genome
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)

    for isl in range(n_islands):
        # Source island boundaries
        src_start: ti.i32 = kernels_helpers.island_boundaries[isl]
        src_end: ti.i32 = kernels_helpers.island_boundaries[isl + 1]
        src_size: ti.i32 = src_end - src_start

        # Destination island (ring topology: i -> (i+1) % n)
        dst_isl: ti.i32 = (isl + 1) % n_islands
        dst_start: ti.i32 = kernels_helpers.island_boundaries[dst_isl]
        dst_end: ti.i32 = kernels_helpers.island_boundaries[dst_isl + 1]
        dst_size: ti.i32 = dst_end - dst_start

        k: ti.i32 = ti.min(migrate_count, src_size)
        k = ti.min(k, dst_size)
        k = ti.min(k, MAX_MIGRATE_COUNT)

        if k <= 0:
            continue

        # Find top-k in source island (highest scores -> emigrants)
        top_scores = ti.Vector([-1] * MAX_MIGRATE_COUNT)
        top_indices = ti.Vector([-1] * MAX_MIGRATE_COUNT)

        for local_idx in range(src_size):
            g: ti.i32 = src_start + local_idx
            score: ti.i32 = kernels_helpers.ga_scores[g]

            if score > top_scores[k - 1]:
                # Insert in sorted position (descending)
                insert_pos: ti.i32 = k - 1
                found_better: ti.i32 = 0
                for j in ti.static(range(MAX_MIGRATE_COUNT)):
                    if found_better == 0 and j < k and score > top_scores[j]:
                        insert_pos = j
                        found_better = 1

                # Shift down
                for j in ti.static(range(MAX_MIGRATE_COUNT - 1, 0, -1)):
                    if j > insert_pos and j < k:
                        top_scores[j] = top_scores[j - 1]
                        top_indices[j] = top_indices[j - 1]

                top_scores[insert_pos] = score
                top_indices[insert_pos] = g

        # Find bottom-k in destination island (lowest scores -> to be replaced)
        bot_scores = ti.Vector([2147483647] * MAX_MIGRATE_COUNT)  # Start with max int
        bot_indices = ti.Vector([-1] * MAX_MIGRATE_COUNT)

        for local_idx in range(dst_size):
            g: ti.i32 = dst_start + local_idx
            score: ti.i32 = kernels_helpers.ga_scores[g]

            if score < bot_scores[k - 1]:
                # Insert in sorted position (ascending - worst first)
                insert_pos: ti.i32 = k - 1
                found_worse: ti.i32 = 0
                for j in ti.static(range(MAX_MIGRATE_COUNT)):
                    if found_worse == 0 and j < k and score < bot_scores[j]:
                        insert_pos = j
                        found_worse = 1

                # Shift down
                for j in ti.static(range(MAX_MIGRATE_COUNT - 1, 0, -1)):
                    if j > insert_pos and j < k:
                        bot_scores[j] = bot_scores[j - 1]
                        bot_indices[j] = bot_indices[j - 1]

                bot_scores[insert_pos] = score
                bot_indices[insert_pos] = g

        # Copy genomes: top[m] from source -> bot[m] in destination
        for m in range(k):
            src_g: ti.i32 = top_indices[m]
            dst_g: ti.i32 = bot_indices[m]
            if src_g >= 0 and dst_g >= 0:
                for s in range(n_slots):
                    kernels_helpers.population_indices[dst_g, s] = kernels_helpers.population_indices[src_g, s]
                # Also copy the score to avoid re-evaluation issues
                kernels_helpers.ga_scores[dst_g] = kernels_helpers.ga_scores[src_g]
