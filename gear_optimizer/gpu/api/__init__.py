"""The GPU's public surface: initialization (reference arrays, staging buffers), timeline (a song's frontier upload) and
ga_operations (the GA's operators)."""

from .initialization import (
    ensure_ready,
    load_curves,
    hard_reset_taichi,
    _ensure_ftff_combo_tables,
)
from .timeline import precompute_timeline_gpu
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
    ga_upload_ftff_shortlist,
    ga_prepare_population_base_stats,
    ga_evaluate_prepared_population,
    ga_refresh_scores_and_update_runs_best,
    ga_refresh_scores_update_runs_best_and_next_generation_fused_runs,
    ga_init_runs_best,
    ga_pack_fg_candidates_table_segmented,
    ga_download_fg_selected_payload,
)

# Public API
__all__ = [
    # Initialization
    "ensure_ready",
    "load_curves",
    "hard_reset_taichi",
    "_ensure_ftff_combo_tables",
    # Timeline
    "precompute_timeline_gpu",
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
    "ga_upload_ftff_shortlist",
    "ga_prepare_population_base_stats",
    "ga_evaluate_prepared_population",
    "ga_refresh_scores_and_update_runs_best",
    "ga_refresh_scores_update_runs_best_and_next_generation_fused_runs",
    "ga_init_runs_best",
    "ga_pack_fg_candidates_table_segmented",
    "ga_download_fg_selected_payload",
]
