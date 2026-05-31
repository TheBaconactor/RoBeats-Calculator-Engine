"""Taichi Kernels - GPU-side island migration for packed GA runs."""

import taichi as ti

from .. import kernels_helpers


MAX_MIGRATE_COUNT = 8  # Static limit for local arrays in migration kernel
MAX_MIGRATION_ISLANDS = 16  # Must match fields.MAX_ISLANDS


@ti.kernel
def ga_island_migration_runs_kernel(
    n_runs: ti.i32,
    n_genomes_per_run: ti.i32,
    n_islands: ti.i32,
    migrate_count: ti.i32,
    n_slots: ti.i32,
):
    """
    GPU-side island migration (ring topology) for multiple independent runs.

    Each run is treated as an independent ring of islands; migrations never cross
    run boundaries.
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)

    n_runs_i = n_runs
    n_genomes_per_run_i = n_genomes_per_run
    n_islands_i = n_islands

    if n_runs_i > 0 and n_genomes_per_run_i > 0:
        if n_islands_i < 1:
            n_islands_i = 1
        if n_islands_i > n_genomes_per_run_i:
            n_islands_i = n_genomes_per_run_i
        if n_islands_i > MAX_MIGRATION_ISLANDS:
            n_islands_i = MAX_MIGRATION_ISLANDS

        island_size: ti.i32 = n_genomes_per_run_i // n_islands_i
        if island_size < 1:
            island_size = 1

        # Select all emigrants/replacements first so migrations do not cascade within one call.
        for run in range(n_runs_i):
            run_start: ti.i32 = run * n_genomes_per_run_i

            k_per_isl = ti.Vector.zero(ti.i32, MAX_MIGRATION_ISLANDS)
            top_indices_per_isl = ti.Matrix.zero(ti.i32, MAX_MIGRATION_ISLANDS, MAX_MIGRATE_COUNT)
            bot_indices_per_isl = ti.Matrix.zero(ti.i32, MAX_MIGRATION_ISLANDS, MAX_MIGRATE_COUNT)

            for isl in range(n_islands_i):
                src_start_local: ti.i32 = isl * island_size
                src_end_local: ti.i32 = (isl + 1) * island_size
                if isl == n_islands_i - 1:
                    src_end_local = n_genomes_per_run_i

                dst_isl: ti.i32 = (isl + 1) % n_islands_i
                dst_start_local: ti.i32 = dst_isl * island_size
                dst_end_local: ti.i32 = (dst_isl + 1) * island_size
                if dst_isl == n_islands_i - 1:
                    dst_end_local = n_genomes_per_run_i

                src_start: ti.i32 = run_start + src_start_local
                src_end: ti.i32 = run_start + src_end_local
                dst_start: ti.i32 = run_start + dst_start_local
                dst_end: ti.i32 = run_start + dst_end_local

                src_size: ti.i32 = src_end - src_start
                dst_size: ti.i32 = dst_end - dst_start

                k: ti.i32 = ti.min(migrate_count, src_size)
                k = ti.min(k, dst_size)
                k = ti.min(k, MAX_MIGRATE_COUNT)
                if k < 0:
                    k = 0
                k_per_isl[isl] = k
                if k <= 0:
                    continue

                # Top-k in source island (highest scores -> emigrants)
                top_scores = ti.Vector([-1] * MAX_MIGRATE_COUNT)
                top_indices = ti.Vector([-1] * MAX_MIGRATE_COUNT)
                for local_idx in range(src_size):
                    g: ti.i32 = src_start + local_idx
                    score: ti.i32 = kernels_helpers.ga_scores[g]
                    if score > top_scores[k - 1]:
                        insert_pos: ti.i32 = k - 1
                        found_better: ti.i32 = 0
                        for j in ti.static(range(MAX_MIGRATE_COUNT)):
                            if found_better == 0 and j < k and score > top_scores[j]:
                                insert_pos = j
                                found_better = 1
                        for j in ti.static(range(MAX_MIGRATE_COUNT - 1, 0, -1)):
                            if j > insert_pos and j < k:
                                top_scores[j] = top_scores[j - 1]
                                top_indices[j] = top_indices[j - 1]
                        top_scores[insert_pos] = score
                        top_indices[insert_pos] = g

                # Bottom-k in destination island (lowest scores -> to be replaced)
                bot_scores = ti.Vector([2147483647] * MAX_MIGRATE_COUNT)
                bot_indices = ti.Vector([-1] * MAX_MIGRATE_COUNT)
                for local_idx in range(dst_size):
                    g: ti.i32 = dst_start + local_idx
                    score: ti.i32 = kernels_helpers.ga_scores[g]
                    if score < bot_scores[k - 1]:
                        insert_pos: ti.i32 = k - 1
                        found_worse: ti.i32 = 0
                        for j in ti.static(range(MAX_MIGRATE_COUNT)):
                            if found_worse == 0 and j < k and score < bot_scores[j]:
                                insert_pos = j
                                found_worse = 1
                        for j in ti.static(range(MAX_MIGRATE_COUNT - 1, 0, -1)):
                            if j > insert_pos and j < k:
                                bot_scores[j] = bot_scores[j - 1]
                                bot_indices[j] = bot_indices[j - 1]
                        bot_scores[insert_pos] = score
                        bot_indices[insert_pos] = g

                for m in range(k):
                    top_indices_per_isl[isl, m] = top_indices[m]
                    bot_indices_per_isl[isl, m] = bot_indices[m]

            # Apply copies (now safe: selection was based on pre-migration scores).
            for isl in range(n_islands_i):
                k = k_per_isl[isl]
                for m in range(k):
                    src_g: ti.i32 = top_indices_per_isl[isl, m]
                    dst_g: ti.i32 = bot_indices_per_isl[isl, m]
                    if src_g >= 0 and dst_g >= 0:
                        for s in range(n_slots):
                            kernels_helpers.population_indices[dst_g, s] = kernels_helpers.population_indices[src_g, s]
                        kernels_helpers.ga_scores[dst_g] = kernels_helpers.ga_scores[src_g]
