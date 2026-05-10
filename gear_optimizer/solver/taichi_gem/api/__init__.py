"""
Taichi API Package - Python wrapper functions for GPU gem optimization.

This package splits the monolithic api.py (1,754 lines) into focused modules:
1. initialization.py - Reference arrays, staging buffers, GPU initialization
2. timeline.py - GPU timeline precomputation and grid upload
3. parallel_solvers.py - Genome solvers (FT/FF-on-GPU + parallel variants)
4. skyline_operations.py - GPU-native Skyline candidate operators

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

# Import from skyline_operations
try:
    from .skyline_operations import (
        skyline_upload_population_indices,
        skyline_upload_initial_populations,
        skyline_upload_init_heuristic_topk,
        skyline_load_initial_population,
        skyline_load_initial_populations_batch,
        skyline_generate_initial_populations,
        skyline_seed_rng,
        skyline_seed_rng_runs,
        skyline_upload_item_stats,
        skyline_upload_base_fixed_stats,
        skyline_aggregate_stats,
        skyline_evaluate_population,
        skyline_write_best_results_from_key,
        skyline_refresh_scores_and_update_runs_best,
        skyline_set_scores,
        skyline_next_generation,
        skyline_next_generation_gpu_elites,  # GPU-resident elitism (avoids CPU download)
        skyline_next_generation_fused,  # FULLY FUSED (2 kernels instead of 4)
        skyline_next_generation_fused_runs,  # FULLY FUSED multi-run batching
        skyline_refresh_scores_update_runs_best_and_next_generation_fused_runs,
        skyline_download_population_indices,
        skyline_download_scores,
        skyline_download_results,
        skyline_download_run_payload,
        skyline_store_run_payload,
        SKYLINE_INIT_runs_best,
        skyline_update_runs_best,
        skyline_store_runs_payload_snapshot_segmented,
        skyline_store_run_payload_segmented,
        skyline_download_runs_payload,
        skyline_pack_fg_candidates_table_segmented,
        skyline_download_fg_selected_payload,
        # GPU-side global best tracking
        SKYLINE_INIT_global_best,
        skyline_update_global_best,
        skyline_download_global_best,
        # GPU-side island elitism
        skyline_upload_island_boundaries,
        skyline_find_island_elites,
        skyline_download_island_elite_indices,
        # GPU-side island migration
        skyline_island_migration,
        skyline_island_migration_runs,
        warmup_skyline_live_request_kernels,
        # FUSED kernel APIs
        skyline_write_best_and_update_global,
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
    # Parallel solvers
    "solve_genomes_with_ftff",
    "solve_genomes_from_registry",
    # Fixed score
    "score_fixed_stats_gpu",
    # skyline operations
    "skyline_upload_population_indices",
    "skyline_upload_initial_populations",
    "skyline_upload_init_heuristic_topk",
    "skyline_load_initial_population",
    "skyline_load_initial_populations_batch",
    "skyline_generate_initial_populations",
    "skyline_seed_rng",
    "skyline_seed_rng_runs",
    "skyline_upload_item_stats",
    "skyline_upload_base_fixed_stats",
    "skyline_aggregate_stats",
    "skyline_evaluate_population",
    "skyline_write_best_results_from_key",
    "skyline_refresh_scores_and_update_runs_best",
    "skyline_set_scores",
    "skyline_next_generation",
    "skyline_next_generation_gpu_elites",
    "skyline_next_generation_fused",
    "skyline_next_generation_fused_runs",
    "skyline_refresh_scores_update_runs_best_and_next_generation_fused_runs",
    "skyline_download_population_indices",
    "skyline_download_scores",
    "skyline_download_results",
    "skyline_download_run_payload",
    "skyline_store_run_payload",
    "SKYLINE_INIT_runs_best",
    "skyline_update_runs_best",
    "skyline_store_runs_payload_snapshot_segmented",
    "skyline_store_run_payload_segmented",
    "skyline_download_runs_payload",
    "skyline_pack_fg_candidates_table_segmented",
    "skyline_download_fg_selected_payload",
    # GPU-side global best tracking
    "SKYLINE_INIT_global_best",
    "skyline_update_global_best",
    "skyline_download_global_best",
    # GPU-side island elitism
    "skyline_upload_island_boundaries",
    "skyline_find_island_elites",
    "skyline_download_island_elite_indices",
    # GPU-side island migration
    "skyline_island_migration",
    "skyline_island_migration_runs",
    "warmup_skyline_live_request_kernels",
    # FUSED kernel APIs
    "skyline_write_best_and_update_global",
]
