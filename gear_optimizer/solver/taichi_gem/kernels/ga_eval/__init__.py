"""
Taichi Kernels - GA Evaluation and Reduction (split package).

This subpackage contains the kernels previously defined in
`gear_optimizer.solver.taichi_gem.kernels.kernels_ga_eval`.
"""

from .combo_search import ga_find_best_combo_key_kernel
from .global_best import ga_init_global_best_kernel, ga_update_global_best_kernel
from .islands import ga_find_island_elites_kernel
from .migration import ga_island_migration_kernel, ga_island_migration_runs_kernel
from .payload import (
    ga_copy_runs_payload_to_download_staging_kernel,
    ga_init_runs_best_kernel,
    ga_pack_and_store_run_payload_kernel,
    ga_pack_and_store_run_payload_segmented_kernel,
    ga_pack_run_payload_kernel,
    ga_store_runs_payload_snapshot_segmented_kernel,
    ga_update_runs_best_kernel,
)
from .reduction import (
    init_chunk_best_key_kernel,
    init_genome_results_kernel,
    merge_chunk_best_to_genomes_kernel,
    reduce_chunk_to_best_key_kernel,
)
from .warmstart import ga_find_best_combo_warmstart_kernel
from .write_results import (
    ga_write_best_and_store_hints_kernel,
    ga_write_best_and_update_global_kernel,
    ga_write_best_results_from_key_kernel,
)

__all__ = [
    "init_genome_results_kernel",
    "init_chunk_best_key_kernel",
    "reduce_chunk_to_best_key_kernel",
    "merge_chunk_best_to_genomes_kernel",
    "ga_find_best_combo_key_kernel",
    "ga_write_best_results_from_key_kernel",
    "ga_write_best_and_update_global_kernel",
    "ga_write_best_and_store_hints_kernel",
    "ga_init_global_best_kernel",
    "ga_update_global_best_kernel",
    "ga_pack_run_payload_kernel",
    "ga_pack_and_store_run_payload_kernel",
    "ga_pack_and_store_run_payload_segmented_kernel",
    "ga_init_runs_best_kernel",
    "ga_update_runs_best_kernel",
    "ga_store_runs_payload_snapshot_segmented_kernel",
    "ga_copy_runs_payload_to_download_staging_kernel",
    "ga_find_island_elites_kernel",
    "ga_find_best_combo_warmstart_kernel",
    "ga_island_migration_kernel",
    "ga_island_migration_runs_kernel",
]
