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
    GPU-side global best update: track best genome across all generations.

    IMPORTANT: This must update `ga_global_best_score`, `ga_global_best_genome`, and
    `ga_global_best_results` *consistently*. The previous atomic-max approach could
    leave the score from one genome but the IDs/results from another due to races.

    Args:
        n_genomes: Number of genomes to check
        n_slots: Number of equipment slots per genome
    """
    # Single-thread deterministic scan to keep score/ids/results aligned.
    for _ in range(1):
        prev_best: ti.i32 = kernels_helpers.ga_global_best_score[0]
        best_score: ti.i32 = prev_best
        best_g: ti.i32 = -1

        for g in range(n_genomes):
            score: ti.i32 = kernels_helpers.ga_scores[g]
            if score > best_score:
                best_score = score
                best_g = g

        if best_g >= 0:
            kernels_helpers.ga_global_best_score[0] = best_score
            for s in range(n_slots):
                kernels_helpers.ga_global_best_genome[s] = kernels_helpers.population_indices[best_g, s]
            res = kernels_helpers.genome_result_stats[best_g]
            for r in ti.static(range(7)):
                kernels_helpers.ga_global_best_results[r] = res[r]
