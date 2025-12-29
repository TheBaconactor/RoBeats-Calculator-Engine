"""
Taichi Kernels - GPU-side global best tracking.

Includes:
- ga_init_global_best_kernel
- ga_update_global_best_kernel
"""

import taichi as ti

from .. import kernels_helpers


@ti.kernel
def ga_init_global_best_kernel():
    """
    Initialize global best tracking fields at the start of a GA run.

    Sets ga_global_best_score[0] = -1 (no best yet).
    This should be called once at the start of each GA run.
    """
    kernels_helpers.ga_global_best_score[0] = -1


@ti.kernel
def ga_update_global_best_kernel(n_genomes: ti.i32, n_slots: ti.i32):
    """
    GPU-side global best update: atomically track best genome across all generations.

    For each genome, if its score is better than the current global best,
    atomically update the best score and copy the genome's item IDs AND results.

    This avoids expensive per-generation CPU downloads by keeping the best
    genome on GPU until the end of the run.

    Args:
        n_genomes: Number of genomes to check
        n_slots: Number of equipment slots per genome
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        score: ti.i32 = kernels_helpers.ga_scores[g]
        old_best: ti.i32 = ti.atomic_max(kernels_helpers.ga_global_best_score[0], score)

        # If we improved the global best, copy our genome AND results
        # Note: Race condition possible if two threads have same max score,
        # but both would copy valid genomes with that score, so result is correct.
        if old_best < score:
            for s in range(n_slots):
                kernels_helpers.ga_global_best_genome[s] = kernels_helpers.population_indices[g, s]
            # Also copy gem allocation results: [score, ft, ff, pp, cm, fm, ov]
            res = kernels_helpers.genome_result_stats[g]
            for r in ti.static(range(7)):
                kernels_helpers.ga_global_best_results[r] = res[r]
