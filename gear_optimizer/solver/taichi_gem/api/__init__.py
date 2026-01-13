"""
Taichi API Package - Python wrapper functions for GPU gem optimization.

This package splits the monolithic api.py (1,754 lines) into 6 focused modules:
1. initialization.py - Reference arrays, staging buffers, GPU initialization
2. single_batch.py - Single-item and batch gem optimization
3. mega_batch.py - Multi-genome mega batch solver
4. timeline.py - GPU timeline precomputation and grid upload
5. parallel_solvers.py - Maximum parallelism genome solvers
6. ga_operations.py - GPU-native genetic algorithm operators

This __init__.py provides backward-compatible imports so existing code continues to work.
"""

# Import from initialization
try:
    from .initialization import (
        ensure_ready,
        load_ref_arrays,
        is_refs_loaded,
        hard_reset_taichi,
        _ensure_batch_staging,
        _ensure_mega_staging,
        _ensure_parallel_staging,
        _upload_song_flags,
        _ensure_ftff_combo_tables,
        _maybe_sync,
    )
except ImportError:
    pass

# Import from single_batch
try:
    from .single_batch import (
        optimize_gems_gpu,
        optimize_gems_batch_gpu,
    )
except ImportError:
    pass

# Import from mega_batch
try:
    from .mega_batch import (
        mega_batch_solve_population,
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
        solve_genomes_parallel,
        solve_genomes_parallel_merged,
        solve_genomes_from_registry,
    )
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
        # Warm-start
        ga_store_hints,
        ga_inherit_hints,
        # FUSED kernel APIs
        ga_write_best_and_update_global,
        ga_write_best_and_store_hints,
    )
except ImportError:
    pass

# Export all public names for backward compatibility
__all__ = [
    # Initialization
    "ensure_ready",
    "load_ref_arrays",
    "is_refs_loaded",
    "hard_reset_taichi",
    "_ensure_batch_staging",
    "_ensure_mega_staging",
    "_ensure_parallel_staging",
    "_upload_song_flags",
    "_ensure_ftff_combo_tables",
    "_maybe_sync",
    # Single & batch
    "optimize_gems_gpu",
    "optimize_gems_batch_gpu",
    # Mega batch
    "mega_batch_solve_population",
    # Timeline
    "precompute_timeline_gpu",
    "_upload_timeline_grid",
    # Parallel solvers
    "solve_genomes_with_ftff",
    "solve_genomes_parallel",
    "solve_genomes_parallel_merged",
    "solve_genomes_from_registry",
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
    # Warm-start
    "ga_store_hints",
    "ga_inherit_hints",
    # FUSED kernel APIs
    "ga_write_best_and_update_global",
    "ga_write_best_and_store_hints",
]
