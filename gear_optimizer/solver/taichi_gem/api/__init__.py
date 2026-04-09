"""
Taichi API Package - Python wrapper functions for GPU gem optimization.

This package splits the monolithic api.py (1,754 lines) into focused modules:
1. initialization.py - Reference arrays, staging buffers, GPU initialization
2. timeline.py - GPU timeline precomputation and grid upload
3. parallel_solvers.py - Genome solvers (FT/FF-on-GPU + parallel variants)
4. ga_operations.py - GPU-native genetic algorithm operators

This __init__.py defines the public Taichi gem solver API surface.
"""

# Import from initialization
try:
    from .initialization import (
        ensure_ready,
        load_ref_arrays,
        is_refs_loaded,
        hard_reset_taichi,
        _ensure_ftff_combo_tables,
        _maybe_sync,
    )
except ImportError:
    pass

# Import from timeline
try:
    from .timeline import (
        precompute_timeline_gpu,
        _upload_timeline_grid,
    )
except ImportError:
    pass

# Import from parallel_solvers
try:
    from .parallel_solvers import (
        solve_genomes_with_ftff,
        solve_genomes_from_registry,
    )
except ImportError:
    pass

# Import from fixed_scoring
try:
    from .fixed_scoring import score_fixed_stats_gpu
except ImportError:
    pass

# Import from ga_operations
try:
    from .ga_operations import (
        ga_upload_population_indices,
        ga_upload_initial_populations,
        ga_upload_init_heuristic_topk,
        ga_load_initial_population,
        ga_load_initial_populations_batch,
        ga_generate_initial_populations,
        ga_seed_rng,
        ga_seed_rng_runs,
        ga_upload_item_stats,
        ga_upload_base_fixed_stats,
        ga_aggregate_stats,
        ga_evaluate_population,
        ga_set_scores,
        ga_next_generation,
        ga_next_generation_gpu_elites,  # GPU-resident elitism (avoids CPU download)
        ga_next_generation_fused,  # FULLY FUSED (2 kernels instead of 4)
        ga_next_generation_fused_runs,  # FULLY FUSED multi-run batching
        ga_download_population_indices,
        ga_download_scores,
        ga_download_results,
        ga_download_run_payload,
        ga_store_run_payload,
        ga_init_runs_best,
        ga_update_runs_best,
        ga_store_runs_payload_snapshot_segmented,
        ga_store_run_payload_segmented,
        ga_download_runs_payload,
        ga_pack_fg_candidates_table_segmented,
        ga_download_fg_selected_payload,
        ga_stage_genome_base_stats_from_fg_candidates_table,
        # GPU-side global best tracking
        ga_init_global_best,
        ga_update_global_best,
        ga_download_global_best,
        # GPU-side island elitism
        ga_upload_island_boundaries,
        ga_find_island_elites,
        ga_download_island_elite_indices,
        # GPU-side island migration
        ga_island_migration,
        ga_island_migration_runs,
        # FUSED kernel APIs
        ga_write_best_and_update_global,
    )
except ImportError:
    pass

# Public API
__all__ = [
    # Initialization
    "ensure_ready",
    "load_ref_arrays",
    "is_refs_loaded",
    "hard_reset_taichi",
    "_ensure_ftff_combo_tables",
    "_maybe_sync",
    # Timeline
    "precompute_timeline_gpu",
    "_upload_timeline_grid",
    # Parallel solvers
    "solve_genomes_with_ftff",
    "solve_genomes_from_registry",
    # Fixed score
    "score_fixed_stats_gpu",
    # GA operations
    "ga_upload_population_indices",
    "ga_upload_initial_populations",
    "ga_upload_init_heuristic_topk",
    "ga_load_initial_population",
    "ga_load_initial_populations_batch",
    "ga_generate_initial_populations",
    "ga_seed_rng",
    "ga_seed_rng_runs",
    "ga_upload_item_stats",
    "ga_upload_base_fixed_stats",
    "ga_aggregate_stats",
    "ga_evaluate_population",
    "ga_set_scores",
    "ga_next_generation",
    "ga_next_generation_gpu_elites",
    "ga_next_generation_fused",
    "ga_next_generation_fused_runs",
    "ga_download_population_indices",
    "ga_download_scores",
    "ga_download_results",
    "ga_download_run_payload",
    "ga_store_run_payload",
    "ga_init_runs_best",
    "ga_update_runs_best",
    "ga_store_runs_payload_snapshot_segmented",
    "ga_store_run_payload_segmented",
    "ga_download_runs_payload",
    "ga_pack_fg_candidates_table_segmented",
    "ga_download_fg_selected_payload",
    "ga_stage_genome_base_stats_from_fg_candidates_table",
    # GPU-side global best tracking
    "ga_init_global_best",
    "ga_update_global_best",
    "ga_download_global_best",
    # GPU-side island elitism
    "ga_upload_island_boundaries",
    "ga_find_island_elites",
    "ga_download_island_elite_indices",
    # GPU-side island migration
    "ga_island_migration",
    "ga_island_migration_runs",
    # FUSED kernel APIs
    "ga_write_best_and_update_global",
]
