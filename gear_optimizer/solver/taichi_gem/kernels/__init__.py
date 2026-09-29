"""
Taichi Kernels Package - Public Kernel Entry Points.

This package splits the monolithic kernels.py (1,757 lines) into focused modules:
1. kernels_helpers.py - Field placeholders & lookup functions
2. kernels_ga.py - 8 GA kernels (selection, crossover, mutation, etc.)
3. kernels_scoring.py - Score calculation & exact-bound gem optimizer
4. kernels_solvers_batch.py - Result staging kernels
5. ga_eval/ (kernels_ga_eval.py) - GA evaluation & reduction kernels

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
    ga_scores,
    ga_rng_state,
    ga_parent_a,
    ga_parent_b,
    ga_exact_eval_hash_used,
    ga_exact_eval_hash_keys,
    ga_exact_eval_rep_idx,
    ga_exact_eval_unique_count,
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
    _xorshift32,
    # Scoring helpers
    _calc_body_score,
    _calc_head_factor,
    _calc_head_score_bits,
    calc_score_with_grid_bits,
)

# Import GA kernels
from .kernels_ga import (
    ga_seed_rng_runs_kernel,
    ga_seed_rng_runs_indexed_kernel,
    ga_load_initial_populations_batch_kernel,
    ga_generate_initial_populations_kernel,
    ga_aggregate_genome_stats_kernel,
    # FUSED kernels
    ga_next_generation_full_runs_kernel,  # FUSED: multi-run batching + population swap
    ga_refresh_scores_update_runs_best_and_next_generation_full_runs_kernel,
)

# Import scoring functions
from .kernels_scoring import (
    calc_score_cached_device,
)

# Import batch solver kernels
from .kernels_solvers_batch import (
    copy_genome_result_stats_to_download_staging_kernel,
)

# Import GA evaluation & reduction kernels
from .ga_eval import (
    ga_refresh_scores_and_update_runs_best_kernel,
    ga_pack_fg_candidates_table_segmented_kernel,
    ga_select_top_base_fg_candidate_coords_kernel,
    ga_copy_fg_selected_payload_to_download_staging_kernel,
    ga_copy_runs_best_to_download_staging_kernel,
    ga_refresh_fg_candidates_row0_kernel,
    ga_init_runs_best_kernel,
    # GPU-side island migration
    # Exact GA evaluation
    ga_compute_exact_eval_rep_kernel,
    ga_build_unique_slot_table_kernel,
    ga_finalize_warmstart_lane_best_kernel,
    ga_find_best_combo_warmstart_kernel,
    ga_scatter_dup_results_kernel,
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
    "ga_scores",
    "ga_rng_state",
    "ga_parent_a",
    "ga_parent_b",
    "ga_exact_eval_hash_used",
    "ga_exact_eval_hash_keys",
    "ga_exact_eval_rep_idx",
    "ga_exact_eval_unique_count",
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
    "_xorshift32",
    # GA kernels
    "ga_seed_rng_runs_kernel",
    "ga_seed_rng_runs_indexed_kernel",
    "ga_load_initial_populations_batch_kernel",
    "ga_generate_initial_populations_kernel",
    "ga_aggregate_genome_stats_kernel",
    # FUSED GA kernels
    "ga_next_generation_full_runs_kernel",
    "ga_refresh_scores_update_runs_best_and_next_generation_full_runs_kernel",
    # Scoring functions
    "_calc_body_score",
    "_calc_head_factor",
    "_calc_head_score_bits",
    "calc_score_with_grid_bits",
    "calc_score_cached_device",
    # Batch solver kernels
    "copy_genome_result_stats_to_download_staging_kernel",
    # GA evaluation kernels
    "ga_refresh_scores_and_update_runs_best_kernel",
    "ga_pack_fg_candidates_table_segmented_kernel",
    "ga_select_top_base_fg_candidate_coords_kernel",
    "ga_copy_fg_selected_payload_to_download_staging_kernel",
    "ga_copy_runs_best_to_download_staging_kernel",
    "ga_refresh_fg_candidates_row0_kernel",
    "ga_init_runs_best_kernel",
    # GPU-side island migration
    # Exact GA evaluation
    "ga_find_best_combo_warmstart_kernel",
    "ga_finalize_warmstart_lane_best_kernel",
    "ga_compute_exact_eval_rep_kernel",
    "ga_build_unique_slot_table_kernel",
    "ga_scatter_dup_results_kernel",
]

from .kernels_skyline import (
    skyline_load_initial_population_kernel,
    skyline_generate_initial_populations_kernel,
    skyline_upload_item_stats_and_slots_kernel,
    skyline_copy_population_indices_from_ndarray_kernel,
    skyline_aggregate_genome_stats_kernel,
    skyline_aggregate_and_init_best_kernel,
)
from .skyline_eval import (
    skyline_find_best_combo_warmstart_kernel,
    skyline_write_scores_from_key_kernel,
    skyline_write_best_results_from_key_kernel,
)

__all__.extend([
    "skyline_load_initial_population_kernel",
    "skyline_generate_initial_populations_kernel",
    "skyline_upload_item_stats_and_slots_kernel",
    "skyline_copy_population_indices_from_ndarray_kernel",
    "skyline_aggregate_genome_stats_kernel",
    "skyline_aggregate_and_init_best_kernel",
    "skyline_find_best_combo_warmstart_kernel",
    "skyline_write_scores_from_key_kernel",
    "skyline_write_best_results_from_key_kernel",
])
