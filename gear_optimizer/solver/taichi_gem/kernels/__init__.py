"""
Taichi Kernels Package - Public Kernel Entry Points.

This package splits the monolithic kernels.py (1,757 lines) into 6 focused modules:
1. kernels_helpers.py - Field placeholders & lookup functions
2. kernels_skyline.py - 8 skyline kernels (selection, crossover, mutation, etc.)
3. kernels_scoring.py - Score calculation & optimize_core_device
4. kernels_solvers_batch.py - Batch solver kernels
5. skyline_eval/ (kernels_skyline_eval.py) - skyline evaluation & reduction kernels
6. kernels_timeline.py - Timeline computation kernel

This module re-exports kernel entry points used by the Taichi gem solver runtime.
"""

# Import all field placeholders from helpers
from .kernels_helpers import (
    _KERNEL_BLOCK_DIM,
    ref_pp_field,
    ref_cm_field,
    ref_fm_field,
    ref_ft_field,
    ref_ff_field,
    grid_count_body_fever,
    grid_count_body_normal,
    grid_head_len,
    grid_fever_masks,
    grid_fever_masks_bits,
    song_timestamps,
    song_total_notes,
    song_long_notes,
    song_last_note_time,
    genome_base_stats,
    population_indices,
    population_next_indices,
    item_stats,
    base_fixed_stats,
    skyline_scores,
    skyline_rng_state,
    skyline_parent_a,
    skyline_parent_b,
    skyline_exact_eval_hash_used,
    skyline_exact_eval_hash_keys,
    skyline_exact_eval_rep_idx,
    skyline_exact_eval_unique_count,
    slot_start,
    slot_count,
    genome_result_stats,
    chunk_best_key,
    ftff_combo_ft,
    ftff_combo_ff,
)

# Import helper functions
from .kernels_helpers import (
    _clamp_stat_idx,
    lookup_ref_pp,
    lookup_ref_cm,
    lookup_ref_fm,
    lookup_ref_ft,
    lookup_ref_ff,
    _xorshift32,
    # Search helpers
    binary_search_left_from,
    binary_search_left,
    # Scoring helpers
    _calc_body_score,
    _calc_head_factor,
    _calc_head_score_bits,
    calc_score_with_grid,
    calc_score_with_grid_bits,
)

# Import skyline kernels
from .kernels_skyline import (
    skyline_seed_rng_kernel,
    skyline_seed_rng_runs_kernel,
    skyline_load_initial_population_kernel,
    skyline_load_initial_populations_batch_kernel,
    skyline_generate_initial_populations_kernel,
    skyline_upload_item_stats_and_slots_kernel,
    skyline_copy_population_indices_from_ndarray_kernel,
    SKYLINE_build_exact_eval_reuse_map_kernel,
    SKYLINE_build_exact_eval_reuse_map_from_base_stats_kernel,
    SKYLINE_propagate_exact_eval_reuse_base_stats_kernel,
    SKYLINE_propagate_exact_eval_reuse_chunk_best_kernel,
    skyline_select_parents_tournament_kernel,
    SKYLINE_crossover_mutate_kernel,
    SKYLINE_swap_populations_kernel,
    skyline_copy_elites_kernel,
    skyline_copy_island_elites_kernel,  # GPU-resident elitism (avoids CPU download)
    skyline_aggregate_genome_stats_kernel,
    skyline_copy_scores_kernel,
    # FUSED kernels
    skyline_aggregate_and_init_best_kernel,
    skyline_select_crossover_mutate_kernel,
    skyline_next_generation_full_kernel,  # FULLY FUSED: select+crossover+mutate+elitism
    skyline_next_generation_full_islands_kernel,  # FUSED: island elites computed on-the-fly
    skyline_next_generation_full_runs_kernel,  # FUSED: independent multi-run batching
    skyline_refresh_scores_update_runs_best_and_next_generation_full_runs_kernel,
    SKYLINE_swap_population_kernel,  # FUSED: swap
)

# Import scoring functions and optimize_core_device
from .kernels_scoring import (
    _calc_head_score_grid,
    calc_score_cached_device,
    optimize_core_device,
)

# Import batch solver kernels
from .kernels_solvers_batch import (
    solve_genomes_with_ftff_kernel,
    solve_genomes_with_ftff_block_kernel,
    copy_genome_result_stats_to_download_staging_kernel,
)

# Import skyline evaluation & reduction kernels
from .skyline_eval import (
    skyline_find_best_combo_key_kernel,
    skyline_refresh_scores_and_update_runs_best_kernel,
    skyline_write_best_results_from_key_kernel,
    skyline_write_best_results_and_update_runs_best_kernel,
    # GPU-side global best tracking
    SKYLINE_INIT_global_best_kernel,
    skyline_pack_global_best_kernel,
    skyline_update_global_best_kernel,
    skyline_pack_and_store_run_payload_kernel,
    skyline_pack_and_store_run_payload_segmented_kernel,
    skyline_pack_fg_candidates_table_segmented_kernel,
    skyline_pack_run_payload_kernel,
    skyline_copy_run_payload_to_download_staging_kernel,
    skyline_copy_runs_payload_to_download_staging_kernel,
    skyline_copy_fg_candidates_table_to_download_staging_kernel,
    skyline_select_fg_candidates_coords_kernel,
    skyline_copy_fg_selected_payload_to_download_staging_kernel,
    SKYLINE_INIT_runs_best_kernel,
    skyline_update_runs_best_kernel,
    skyline_store_runs_payload_snapshot_segmented_kernel,
    # GPU-side island elitism
    skyline_find_island_elites_kernel,
    # GPU-side island migration
    skyline_island_migration_kernel,
    skyline_island_migration_runs_kernel,
    # Exact skyline evaluation
    skyline_find_best_combo_warmstart_kernel,
    # FUSED kernels
    skyline_write_best_and_update_global_kernel,
)

# Import timeline kernel
from .kernels_timeline import (
    precompute_fever_end_idx_kernel,
    unpack_timeline_grid_masks_kernel,
)

# Public API
__all__ = [
    # Constants
    "_KERNEL_BLOCK_DIM",
    # Field placeholders
    "ref_pp_field",
    "ref_cm_field",
    "ref_fm_field",
    "ref_ft_field",
    "ref_ff_field",
    "grid_count_body_fever",
    "grid_count_body_normal",
    "grid_head_len",
    "grid_fever_masks",
    "grid_fever_masks_bits",
    "song_timestamps",
    "song_total_notes",
    "song_long_notes",
    "song_last_note_time",
    "genome_base_stats",
    "population_indices",
    "population_next_indices",
    "item_stats",
    "base_fixed_stats",
    "skyline_scores",
    "skyline_rng_state",
    "skyline_parent_a",
    "skyline_parent_b",
    "skyline_exact_eval_hash_used",
    "skyline_exact_eval_hash_keys",
    "skyline_exact_eval_rep_idx",
    "skyline_exact_eval_unique_count",
    "slot_start",
    "slot_count",
    "genome_result_stats",
    "chunk_best_key",
    "ftff_combo_ft",
    "ftff_combo_ff",
    # Helper functions
    "_clamp_stat_idx",
    "lookup_ref_pp",
    "lookup_ref_cm",
    "lookup_ref_fm",
    "lookup_ref_ft",
    "lookup_ref_ff",
    "_xorshift32",
    # skyline kernels
    "skyline_seed_rng_kernel",
    "skyline_seed_rng_runs_kernel",
    "skyline_load_initial_population_kernel",
    "skyline_load_initial_populations_batch_kernel",
    "skyline_generate_initial_populations_kernel",
    "skyline_upload_item_stats_and_slots_kernel",
    "skyline_copy_population_indices_from_ndarray_kernel",
    "SKYLINE_build_exact_eval_reuse_map_kernel",
    "SKYLINE_build_exact_eval_reuse_map_from_base_stats_kernel",
    "SKYLINE_propagate_exact_eval_reuse_base_stats_kernel",
    "SKYLINE_propagate_exact_eval_reuse_chunk_best_kernel",
    "skyline_select_parents_tournament_kernel",
    "SKYLINE_crossover_mutate_kernel",
    "SKYLINE_swap_populations_kernel",
    "skyline_copy_elites_kernel",
    "skyline_copy_island_elites_kernel",
    "skyline_aggregate_genome_stats_kernel",
    "skyline_copy_scores_kernel",
    # FUSED skyline kernels
    "skyline_aggregate_and_init_best_kernel",
    "skyline_select_crossover_mutate_kernel",
    "skyline_next_generation_full_kernel",
    "skyline_next_generation_full_islands_kernel",
    "skyline_next_generation_full_runs_kernel",
    "skyline_refresh_scores_update_runs_best_and_next_generation_full_runs_kernel",
    "SKYLINE_swap_population_kernel",
    "skyline_write_best_and_update_global_kernel",
    # Scoring functions
    "_calc_body_score",
    "_calc_head_factor",
    "_calc_head_score_grid",
    "_calc_head_score_bits",
    "calc_score_with_grid",
    "calc_score_with_grid_bits",
    "calc_score_cached_device",
    "optimize_core_device",
    # Batch solver kernels
    "solve_genomes_with_ftff_kernel",
    "solve_genomes_with_ftff_block_kernel",
    "copy_genome_result_stats_to_download_staging_kernel",
    # skyline evaluation kernels
    "skyline_find_best_combo_key_kernel",
    "skyline_refresh_scores_and_update_runs_best_kernel",
    "skyline_write_best_results_from_key_kernel",
    "skyline_write_best_results_and_update_runs_best_kernel",
    # GPU-side global best tracking
    "SKYLINE_INIT_global_best_kernel",
    "skyline_pack_global_best_kernel",
    "skyline_update_global_best_kernel",
    "skyline_pack_and_store_run_payload_kernel",
    "skyline_pack_and_store_run_payload_segmented_kernel",
    "skyline_pack_fg_candidates_table_segmented_kernel",
    "skyline_pack_run_payload_kernel",
    "skyline_copy_run_payload_to_download_staging_kernel",
    "skyline_copy_runs_payload_to_download_staging_kernel",
    "skyline_copy_fg_candidates_table_to_download_staging_kernel",
    "skyline_select_fg_candidates_coords_kernel",
    "skyline_copy_fg_selected_payload_to_download_staging_kernel",
    "SKYLINE_INIT_runs_best_kernel",
    "skyline_update_runs_best_kernel",
    "skyline_store_runs_payload_snapshot_segmented_kernel",
    # GPU-side island migration
    "skyline_island_migration_kernel",
    "skyline_island_migration_runs_kernel",
    # GPU-side island elitism
    "skyline_find_island_elites_kernel",
    # Exact skyline evaluation
    "skyline_find_best_combo_warmstart_kernel",
    # Timeline kernels
    "binary_search_left_from",
    "binary_search_left",
    "precompute_fever_end_idx_kernel",
    "unpack_timeline_grid_masks_kernel",
]
