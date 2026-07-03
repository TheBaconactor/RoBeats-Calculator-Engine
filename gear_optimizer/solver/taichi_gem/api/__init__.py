"""
Taichi API Package - Python wrapper functions for GPU gem optimization.

This package splits the monolithic api.py (1,754 lines) into focused modules:
1. initialization.py - Reference arrays, staging buffers, GPU initialization
2. timeline.py - GPU timeline precomputation and grid upload
3. ga_operations.py - GPU-native genetic algorithm operators

This __init__.py defines the public Taichi gem solver API surface.
"""

from .initialization import (
    ensure_ready,
    load_ref_arrays,
    hard_reset_taichi,
    _ensure_ftff_combo_tables,
    _maybe_sync,
)
from .timeline import precompute_timeline_gpu
from .parallel_solvers import solve_genomes_from_registry
from .skyline_operations import (
    skyline_upload_population_indices,
    skyline_upload_item_stats,
    skyline_upload_base_fixed_stats,
    skyline_upload_fg_effective_tables,
    skyline_aggregate_stats,
    skyline_evaluate_population,
    skyline_download_scores,
    skyline_download_results,
)
from .ga_operations import (
    ga_upload_initial_populations,
    ga_upload_init_heuristic_topk,
    ga_load_initial_populations_batch,
    ga_generate_initial_populations,
    ga_seed_rng_runs,
    ga_seed_rng_runs_indexed,
    ga_download_runs_best,
    ga_refresh_fg_candidates_row0,
    ga_upload_item_stats,
    ga_upload_base_fixed_stats,
    ga_upload_fg_effective_tables,
    ga_prepare_population_base_stats,
    ga_evaluate_prepared_population,
    ga_refresh_scores_and_update_runs_best,
    ga_next_generation_fused_runs,
    ga_refresh_scores_update_runs_best_and_next_generation_fused_runs,
    ga_init_runs_best,
    ga_update_runs_best,
    ga_pack_fg_candidates_table_segmented,
    ga_download_fg_selected_payload,
    ga_island_migration_runs,
)

# Public API
__all__ = [
    # Initialization
    "ensure_ready",
    "load_ref_arrays",
    "hard_reset_taichi",
    "_ensure_ftff_combo_tables",
    "_maybe_sync",
    # Timeline
    "precompute_timeline_gpu",
    # Parallel solvers
    "solve_genomes_from_registry",
    # Skyline operations
    "skyline_upload_population_indices",
    "skyline_upload_item_stats",
    "skyline_upload_base_fixed_stats",
    "skyline_upload_fg_effective_tables",
    "skyline_aggregate_stats",
    "skyline_evaluate_population",
    "skyline_download_scores",
    "skyline_download_results",
    # GA operations
    "ga_upload_initial_populations",
    "ga_upload_init_heuristic_topk",
    "ga_load_initial_populations_batch",
    "ga_generate_initial_populations",
    "ga_seed_rng_runs",
    "ga_seed_rng_runs_indexed",
    "ga_download_runs_best",
    "ga_refresh_fg_candidates_row0",
    "ga_upload_item_stats",
    "ga_upload_base_fixed_stats",
    "ga_upload_fg_effective_tables",
    "ga_prepare_population_base_stats",
    "ga_evaluate_prepared_population",
    "ga_refresh_scores_and_update_runs_best",
    "ga_next_generation_fused_runs",
    "ga_refresh_scores_update_runs_best_and_next_generation_fused_runs",
    "ga_init_runs_best",
    "ga_update_runs_best",
    "ga_pack_fg_candidates_table_segmented",
    "ga_download_fg_selected_payload",
    # GPU-side island migration
    "ga_island_migration_runs",
]
