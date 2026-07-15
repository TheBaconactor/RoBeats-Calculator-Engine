"""
Taichi Kernels Package - Public Kernel Entry Points.

This package splits the GPU solver kernels into focused modules:
1. kernels_helpers.py - Field placeholders & lookup functions
2. kernels_scoring.py - Score calculation & exact-bound gem optimizer
3. kernels_solvers_batch.py - Result staging kernels
4. kernels_skyline.py / skyline_eval - exact candidate evaluation
5. exact_base_semiring.py - exact Base outer search
6. kernels_timeline.py - timeline computation

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
    loadout_base_stats,
    loadout_indices,
    item_stats,
    base_fixed_stats,
    slot_start,
    slot_count,
    loadout_result_stats,
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
    # Search helpers
    binary_search_left_from,
    binary_search_left,
    # Scoring helpers
    _calc_body_score,
    _calc_head_factor,
    _calc_head_score_bits,
    calc_score_with_grid_bits,
)

# Import exact Base semiring primitives
from .exact_base_semiring import (
    exact_base_compact_combined_pairs_kernel,
    exact_base_compact_gear_pairs_kernel,
    exact_base_fill_i32_kernel,
    exact_base_fill_u64_kernel,
    exact_base_gather_witness_chains_kernel,
    exact_base_scatter_combined_pairs_kernel,
    exact_base_scatter_gear_pairs_kernel,
    exact_base_score_frontier_bounds_kernel,
    exact_base_suffix_cm_fm_u64,
    exact_base_suffix_cm_u64_kernel,
    exact_base_suffix_fm_u64_kernel,
)

# Import scoring functions
from .kernels_scoring import (
    calc_score_cached_device,
)

# Import batch solver kernels
from .kernels_solvers_batch import (
    copy_loadout_result_stats_to_download_staging_kernel,
)

# Import timeline kernel
from .kernels_timeline import (
    precompute_fever_end_idx_kernel,
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
    "loadout_base_stats",
    "loadout_indices",
    "item_stats",
    "base_fixed_stats",
    "slot_start",
    "slot_count",
    "loadout_result_stats",
    "chunk_best_key",
    "ftff_combo_ft",
    "ftff_combo_ff",
    # Exact Base semiring primitives
    "exact_base_compact_combined_pairs_kernel",
    "exact_base_compact_gear_pairs_kernel",
    "exact_base_fill_i32_kernel",
    "exact_base_fill_u64_kernel",
    "exact_base_gather_witness_chains_kernel",
    "exact_base_scatter_combined_pairs_kernel",
    "exact_base_scatter_gear_pairs_kernel",
    "exact_base_score_frontier_bounds_kernel",
    "exact_base_suffix_cm_fm_u64",
    "exact_base_suffix_cm_u64_kernel",
    "exact_base_suffix_fm_u64_kernel",
    # Helper functions
    "_clamp_stat_idx",
    "lookup_ref_pp",
    "lookup_ref_cm",
    "lookup_ref_fm",
    "lookup_ref_ft",
    "lookup_ref_ff",
    # Scoring functions
    "_calc_body_score",
    "_calc_head_factor",
    "_calc_head_score_bits",
    "calc_score_with_grid_bits",
    "calc_score_cached_device",
    # Batch solver kernels
    "copy_loadout_result_stats_to_download_staging_kernel",
    # Timeline kernels
    "binary_search_left_from",
    "binary_search_left",
    "precompute_fever_end_idx_kernel",
]

try:
    from .kernels_skyline import (
        skyline_upload_item_stats_and_slots_kernel,
        skyline_copy_loadout_indices_from_ndarray_kernel,
        skyline_aggregate_loadouts_and_init_best_kernel,
    )
    from .skyline_eval import (
        skyline_find_best_combo_warmstart_kernel,
        skyline_write_scores_from_key_kernel,
        skyline_write_best_results_from_key_kernel,
    )
except ImportError as _skyline_import_error:
    # Swallowing this error would silently disable every skyline kernel and the
    # production registry-solve path that uses them.
    raise RuntimeError(
        "skyline kernel surface failed to import; the exact evaluator must be complete"
    ) from _skyline_import_error
else:
    _SKYLINE_KERNEL_REEXPORTS = {
        "skyline_upload_item_stats_and_slots_kernel": skyline_upload_item_stats_and_slots_kernel,
        "skyline_copy_loadout_indices_from_ndarray_kernel": skyline_copy_loadout_indices_from_ndarray_kernel,
        "skyline_aggregate_loadouts_and_init_best_kernel": skyline_aggregate_loadouts_and_init_best_kernel,
        "skyline_find_best_combo_warmstart_kernel": skyline_find_best_combo_warmstart_kernel,
        "skyline_write_scores_from_key_kernel": skyline_write_scores_from_key_kernel,
        "skyline_write_best_results_from_key_kernel": skyline_write_best_results_from_key_kernel,
    }
    __all__.extend(_SKYLINE_KERNEL_REEXPORTS)
