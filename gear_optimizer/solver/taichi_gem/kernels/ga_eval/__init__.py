"""Taichi Kernels - GA evaluation kernels (split package)."""

from .migration import ga_island_migration_runs_kernel
from .payload import (
    ga_copy_fg_selected_payload_to_download_staging_kernel,
    ga_init_runs_best_kernel,
    ga_pack_fg_candidates_table_segmented_kernel,
    ga_select_top_base_fg_candidate_coords_kernel,
    ga_update_runs_best_kernel,
)
from .warmstart import (
    ga_compute_exact_eval_rep_kernel,
    ga_finalize_warmstart_lane_best_kernel,
    ga_find_best_combo_warmstart_kernel,
    ga_scatter_dup_results_kernel,
)
from .write_results import (
    ga_refresh_scores_and_update_runs_best_kernel,
)

__all__ = [
    "ga_refresh_scores_and_update_runs_best_kernel",
    "ga_pack_fg_candidates_table_segmented_kernel",
    "ga_init_runs_best_kernel",
    "ga_update_runs_best_kernel",
    "ga_select_top_base_fg_candidate_coords_kernel",
    "ga_copy_fg_selected_payload_to_download_staging_kernel",
    "ga_find_best_combo_warmstart_kernel",
    "ga_finalize_warmstart_lane_best_kernel",
    "ga_compute_exact_eval_rep_kernel",
    "ga_scatter_dup_results_kernel",
    "ga_island_migration_runs_kernel",
]
