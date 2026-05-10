"""Taichi Kernels - skyline evaluation kernels (split package)."""

from .combo_search import skyline_find_best_combo_key_kernel
from .global_best import SKYLINE_INIT_global_best_kernel, skyline_pack_global_best_kernel, skyline_update_global_best_kernel
from .islands import skyline_find_island_elites_kernel
from .migration import skyline_island_migration_kernel, skyline_island_migration_runs_kernel
from .payload import (
    skyline_copy_run_payload_to_download_staging_kernel,
    skyline_copy_runs_payload_to_download_staging_kernel,
    skyline_copy_fg_candidates_table_to_download_staging_kernel,
    skyline_copy_fg_selected_payload_to_download_staging_kernel,
    SKYLINE_INIT_runs_best_kernel,
    skyline_pack_and_store_run_payload_kernel,
    skyline_pack_and_store_run_payload_segmented_kernel,
    skyline_pack_fg_candidates_table_segmented_kernel,
    skyline_pack_run_payload_kernel,
    skyline_select_fg_candidates_coords_kernel,
    skyline_store_runs_payload_snapshot_segmented_kernel,
    skyline_update_runs_best_kernel,
)
from .warmstart import skyline_find_best_combo_warmstart_kernel
from .write_results import (
    skyline_refresh_scores_and_update_runs_best_kernel,
    skyline_write_best_and_update_global_kernel,
    skyline_write_best_results_and_update_runs_best_kernel,
    skyline_write_best_results_from_key_kernel,
)

__all__ = [
    "skyline_find_best_combo_key_kernel",
    "skyline_write_best_results_from_key_kernel",
    "skyline_refresh_scores_and_update_runs_best_kernel",
    "skyline_write_best_results_and_update_runs_best_kernel",
    "skyline_write_best_and_update_global_kernel",
    "SKYLINE_INIT_global_best_kernel",
    "skyline_pack_global_best_kernel",
    "skyline_update_global_best_kernel",
    "skyline_pack_run_payload_kernel",
    "skyline_pack_and_store_run_payload_kernel",
    "skyline_pack_and_store_run_payload_segmented_kernel",
    "skyline_pack_fg_candidates_table_segmented_kernel",
    "SKYLINE_INIT_runs_best_kernel",
    "skyline_update_runs_best_kernel",
    "skyline_store_runs_payload_snapshot_segmented_kernel",
    "skyline_copy_run_payload_to_download_staging_kernel",
    "skyline_copy_runs_payload_to_download_staging_kernel",
    "skyline_copy_fg_candidates_table_to_download_staging_kernel",
    "skyline_select_fg_candidates_coords_kernel",
    "skyline_copy_fg_selected_payload_to_download_staging_kernel",
    "skyline_find_island_elites_kernel",
    "skyline_find_best_combo_warmstart_kernel",
    "skyline_island_migration_kernel",
    "skyline_island_migration_runs_kernel",
]
