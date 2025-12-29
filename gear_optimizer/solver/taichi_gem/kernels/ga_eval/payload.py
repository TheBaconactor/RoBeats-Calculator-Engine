"""
Taichi Kernels - Pack GA snapshots for CPU download.

Includes:
- ga_pack_run_payload_kernel
- ga_pack_and_store_run_payload_kernel
"""

import taichi as ti

from .. import kernels_helpers


@ti.kernel
def ga_pack_run_payload_kernel(n_genomes: ti.i32, n_slots: ti.i32):
    """
    Pack a GA snapshot into `ga_run_payload_packed` for a single CPU download.

    Layout (int32):
      - Row 0: [best_score, best_genome_ids (n_slots), best_results (7)]
      - Row g+1: [score, genome_ids (n_slots), genome_result_stats (7)]
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)

    # Row 0: global best (single thread)
    for _ in range(1):
        kernels_helpers.ga_run_payload_packed[0, 0] = kernels_helpers.ga_global_best_score[0]
        for s in range(n_slots):
            kernels_helpers.ga_run_payload_packed[0, 1 + s] = kernels_helpers.ga_global_best_genome[s]
        for r in ti.static(range(7)):
            kernels_helpers.ga_run_payload_packed[0, 1 + n_slots + r] = kernels_helpers.ga_global_best_results[r]

    # Rows 1..n_genomes: per-genome snapshot
    for g in range(n_genomes):
        out_row = g + 1
        kernels_helpers.ga_run_payload_packed[out_row, 0] = kernels_helpers.ga_scores[g]
        for s in range(n_slots):
            kernels_helpers.ga_run_payload_packed[out_row, 1 + s] = kernels_helpers.population_indices[g, s]
        res = kernels_helpers.genome_result_stats[g]
        for r in ti.static(range(7)):
            kernels_helpers.ga_run_payload_packed[out_row, 1 + n_slots + r] = res[r]


@ti.kernel
def ga_pack_and_store_run_payload_kernel(run_idx: ti.i32, n_genomes: ti.i32, n_slots: ti.i32):
    """
    Pack a GA snapshot directly into the multi-run buffer `ga_runs_payload_packed`.

    Layout (int32):
      - [run_idx, 0]: [best_score, best_genome_ids (n_slots), best_results (7)]
      - [run_idx, g+1]: [score, genome_ids (n_slots), genome_result_stats (7)]
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)

    # Row 0: global best (single thread)
    for _ in range(1):
        kernels_helpers.ga_runs_payload_packed[run_idx, 0, 0] = kernels_helpers.ga_global_best_score[0]
        for s in range(n_slots):
            kernels_helpers.ga_runs_payload_packed[run_idx, 0, 1 + s] = kernels_helpers.ga_global_best_genome[s]
        for r in ti.static(range(7)):
            kernels_helpers.ga_runs_payload_packed[run_idx, 0, 1 + n_slots + r] = (
                kernels_helpers.ga_global_best_results[r]
            )

    # Rows 1..n_genomes: per-genome snapshot
    for g in range(n_genomes):
        out_row = g + 1
        kernels_helpers.ga_runs_payload_packed[run_idx, out_row, 0] = kernels_helpers.ga_scores[g]
        for s in range(n_slots):
            kernels_helpers.ga_runs_payload_packed[run_idx, out_row, 1 + s] = kernels_helpers.population_indices[g, s]
        res = kernels_helpers.genome_result_stats[g]
        for r in ti.static(range(7)):
            kernels_helpers.ga_runs_payload_packed[run_idx, out_row, 1 + n_slots + r] = res[r]
