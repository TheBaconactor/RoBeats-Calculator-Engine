"""
Taichi Kernels Package - Backward-Compatible Imports.

This package splits the monolithic kernels.py (1,757 lines) into 6 focused modules:
1. kernels_helpers.py - Field placeholders & lookup functions
2. kernels_ga.py - 8 GA kernels (selection, crossover, mutation, etc.)
3. kernels_scoring.py - Score calculation & optimize_core_device
4. kernels_solvers_batch.py - Batch solver kernels
5. ga_eval/ (kernels_ga_eval.py) - GA evaluation & reduction kernels
6. kernels_timeline.py - Timeline computation kernel

This __init__.py provides backward-compatible imports so existing code continues to work.
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
    fever_masks,
    work_items,
    genome_base_stats,
    song_flags,
    population_indices,
    population_next_indices,
    item_stats,
    base_fixed_stats,
    ga_scores,
    ga_rng_state,
    ga_parent_a,
    ga_parent_b,
    slot_start,
    slot_count,
    result_stats,
    genome_result_stats,
    genome_hint_allocation,  # Warm-start hints for local search optimization
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
    calc_score_with_grid_bits,
)

# Import GA kernels
from .kernels_ga import (
    ga_seed_rng_kernel,
    ga_load_initial_population_kernel,
    ga_select_parents_tournament_kernel,
    ga_crossover_mutate_kernel,
    ga_swap_populations_kernel,
    ga_copy_elites_kernel,
    ga_copy_island_elites_kernel,  # GPU-resident elitism (avoids CPU download)
    ga_aggregate_genome_stats_kernel,
    ga_copy_scores_kernel,
    # Warm-start optimization
    ga_store_hints_kernel,
    ga_inherit_hints_kernel,
    # FUSED kernels
    ga_aggregate_and_init_best_kernel,
    ga_select_crossover_mutate_kernel,
    ga_next_generation_full_kernel,      # FULLY FUSED: select+crossover+mutate+elitism
    ga_swap_and_inherit_hints_kernel,    # FUSED: swap+hints
)

# Import scoring functions and optimize_core_device
from .kernels_scoring import (
    _calc_head_score_masks,
    _calc_head_score_grid,
    calc_score_device,
    calc_score_with_grid,
    calc_score_cached_device,
    optimize_core_device,
    local_search_from_hint,  # Warm-start local search function
)

# Import batch solver kernels
from .kernels_solvers_batch import (
    solve_batch_kernel,
    solve_genomes_with_ftff_kernel,
    solve_ftff_parallel_kernel,
)

# Import GA evaluation & reduction kernels
from .ga_eval import (
    init_genome_results_kernel,
    init_chunk_best_key_kernel,
    reduce_chunk_to_best_key_kernel,
    merge_chunk_best_to_genomes_kernel,
    ga_find_best_combo_key_kernel,
    ga_write_best_results_from_key_kernel,
    # GPU-side global best tracking
    ga_init_global_best_kernel,
    ga_update_global_best_kernel,
    ga_pack_and_store_run_payload_kernel,
    ga_pack_run_payload_kernel,
    # GPU-side island elitism
    ga_find_island_elites_kernel,
    # GPU-side island migration
    ga_island_migration_kernel,
    # Warm-start evaluation
    ga_find_best_combo_warmstart_kernel,
    # FUSED kernels
    ga_write_best_and_update_global_kernel,
)

# Import timeline kernel
from .kernels_timeline import (
    compute_timeline_grid_kernel,
)

# Export all public names for backward compatibility
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
    "fever_masks",
    "work_items",
    "genome_base_stats",
    "song_flags",
    "population_indices",
    "population_next_indices",
    "item_stats",
    "base_fixed_stats",
    "ga_scores",
    "ga_rng_state",
    "ga_parent_a",
    "ga_parent_b",
    "slot_start",
    "slot_count",
    "result_stats",
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
    # GA kernels
    "ga_seed_rng_kernel",
    "ga_load_initial_population_kernel",
    "ga_select_parents_tournament_kernel",
    "ga_crossover_mutate_kernel",
    "ga_swap_populations_kernel",
    "ga_copy_elites_kernel",
    "ga_copy_island_elites_kernel",
    "ga_aggregate_genome_stats_kernel",
    "ga_copy_scores_kernel",
    # FUSED GA kernels
    "ga_aggregate_and_init_best_kernel",
    "ga_select_crossover_mutate_kernel",
    "ga_next_generation_full_kernel",
    "ga_swap_and_inherit_hints_kernel",
    "ga_write_best_and_update_global_kernel",
    # Scoring functions
    "_calc_body_score",
    "_calc_head_factor",
    "_calc_head_score_masks",
    "_calc_head_score_grid",
    "_calc_head_score_bits",
    "calc_score_device",
    "calc_score_with_grid",
    "calc_score_with_grid_bits",
    "calc_score_cached_device",
    "optimize_core_device",
    # Batch solver kernels
    "solve_batch_kernel",
    "solve_genomes_with_ftff_kernel",
    "solve_ftff_parallel_kernel",
    # GA evaluation kernels
    "init_genome_results_kernel",
    "init_chunk_best_key_kernel",
    "reduce_chunk_to_best_key_kernel",
    "merge_chunk_best_to_genomes_kernel",
    "ga_find_best_combo_key_kernel",
    "ga_write_best_results_from_key_kernel",
    # GPU-side global best tracking
    "ga_init_global_best_kernel",
    "ga_update_global_best_kernel",
    "ga_pack_and_store_run_payload_kernel",
    "ga_pack_run_payload_kernel",
    # GPU-side island migration
    "ga_island_migration_kernel",
    # GPU-side island elitism
    "ga_find_island_elites_kernel",
    # Warm-start optimization
    "genome_hint_allocation",
    "ga_store_hints_kernel",
    "ga_inherit_hints_kernel",
    "ga_find_best_combo_warmstart_kernel",
    "local_search_from_hint",
    # Timeline kernels
    "binary_search_left_from",
    "binary_search_left",
    "compute_timeline_grid_kernel",
]
