"""
Taichi Kernels - GA Evaluation and Reduction Pipeline (compat module).

The original `kernels_ga_eval.py` grew large and was split into the
`gear_optimizer.solver.taichi_gem.kernels.ga_eval` subpackage to make it easier
to navigate.

This module re-exports the same public kernel functions for backward
compatibility.
"""

from .ga_eval import (
    ga_find_best_combo_key_kernel,
    ga_find_best_combo_warmstart_kernel,
    ga_find_island_elites_kernel,
    ga_init_global_best_kernel,
    ga_island_migration_kernel,
    ga_pack_and_store_run_payload_kernel,
    ga_pack_run_payload_kernel,
    ga_update_global_best_kernel,
    ga_write_best_and_update_global_kernel,
    ga_write_best_results_from_key_kernel,
    init_chunk_best_key_kernel,
    init_genome_results_kernel,
    merge_chunk_best_to_genomes_kernel,
    reduce_chunk_to_best_key_kernel,
)

__all__ = [
    "init_genome_results_kernel",
    "init_chunk_best_key_kernel",
    "reduce_chunk_to_best_key_kernel",
    "merge_chunk_best_to_genomes_kernel",
    "ga_find_best_combo_key_kernel",
    "ga_write_best_results_from_key_kernel",
    "ga_write_best_and_update_global_kernel",
    "ga_init_global_best_kernel",
    "ga_update_global_best_kernel",
    "ga_pack_run_payload_kernel",
    "ga_pack_and_store_run_payload_kernel",
    "ga_find_island_elites_kernel",
    "ga_find_best_combo_warmstart_kernel",
    "ga_island_migration_kernel",
]
