"""
Taichi Fields - GPU field declarations and allocation.
This module handles:
- All ti.Field declarations (reference tables, work items, genome data, results)
- Field allocation functions
- Grid fields for timeline lookups
- bind_fields() to inject live field objects into kernels module
"""
import logging
import taichi as ti
from gear_optimizer.core.parsing import env_int
from .runtime import is_initialized, init_taichi
IS_METAL = False
logger = logging.getLogger(__name__)
GRID_SIZE = 161  # Timeline grid dimension (161x161 = 26,521 entries per song)
MAX_GENOMES = 4608  # Active-population genome pool. Sized to fit a full GA batch
# at production q24 geometry: 6 runs x 705 genomes = 4230 <= 4608 (was 4096, which
# only fit 5 of the 6 runs and capped batch width below the genome-unification target).
# +~25MB VRAM on the 24GB RX 7900 XTX across all MAX_GENOMES-sized buffers.
MAX_SLOTS = 9  # 6 gear + 3 minis (GPU-native GA representation)
MAX_ITEMS = 65536  # Upper bound for (type,Name)-deduped items per song (row 0 reserved)
ITEM_STAT_DIM = 10  # PP, CM, FM, FT, FF, Beat, Vibe, Rush, Flow, Chill
MAX_SONG_NOTES = 200000  # Maximum song length for GPU timeline computation
MAX_EVALS_PER_DISPATCH = 8_388_608  # Upper bound used for chunking (genomes * FT/FF combos)
def _clamp_song_slots(n: int) -> int:
    if n < 2:
        return 2
    if n > 256:
        try:
            logger.warning("[GPU] GPU_SONG_SLOTS=%s too large; clamping to 256 to avoid VRAM OOM.", int(n))
        except Exception as e:
            logger.debug(f"fields:_clamp_song_slots: {e}")
        return 256
    return n
MAX_TIMELINE_FRONTIER_SURFACES = 262144  # GPU frontier field-size cap (within [1, 1_048_576] VRAM bound)
MAX_SONG_SLOTS = _clamp_song_slots(env_int("GPU_SONG_SLOTS", 8))
MAX_TOTAL_BUDGET = 90  # Max supported total_budget for FT/FF combo tables
MAX_FTFF_COMBOS = (MAX_TOTAL_BUDGET + 1) * (MAX_TOTAL_BUDGET + 2) // 2  # 4186 when MAX_TOTAL_BUDGET=90
MAX_TIMING_RESPONSE_COMBOS = 2_000_000  # GPU antichain field-size cap (>> MAX_FTFF_COMBOS, within 8_000_000 VRAM bound)
GA_FTFF_REDUCE_BLOCK_DIM = 256  # Vulkan reduce block dim; MUST match kernels_helpers.py + kernels/ga_eval/warmstart.py
GA_FG_CANDIDATES_PER_RUN = 64  # MUST match kernels/ga_eval/payload.py _GA_FG_CANDIDATES_PER_RUN
GA_FG_CANDIDATE_COLS = 1 + MAX_SLOTS + 7 + 7
GA_INIT_HEURISTIC_K = 64  # heuristic-seeded initial genomes (was GPU_GA_INIT_HEURISTIC_K)
ref_pp_field: ti.Field = None
ref_cm_field: ti.Field = None
ref_fm_field: ti.Field = None
ref_ft_field: ti.Field = None  # Fever Time multipliers
ref_ff_field: ti.Field = None  # Fever Fill Rate multipliers
exact_pp_best_gems_prefix: ti.Field = None  # (16, 161, MAX_TOTAL_BUDGET+1) i16
grid_count_body_fever: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161) i32
grid_count_body_normal: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161) i32
grid_head_len: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161) i32
grid_N_hn: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161) i32 - count of normal head notes
grid_N_hf: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161) i32 - count of fever head notes
grid_Sigma_hn: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161) i32 - sum(i+1) over normal head notes
grid_Sigma_hf: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161) i32 - sum(i+1) over fever head notes
grid_fever_masks_bits: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161, 4) u32 - bitpacked head masks
grid_frontier_count: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161) i32 - retained packed frontier count
grid_frontier_offset: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161) i32 - packed frontier start offset
grid_frontier_body_fever_pool: ti.Field = None  # (MAX_SONG_SLOTS, MAX_TIMELINE_FRONTIER_SURFACES) i32
grid_frontier_body_normal_pool: ti.Field = None  # (MAX_SONG_SLOTS, MAX_TIMELINE_FRONTIER_SURFACES) i32
grid_frontier_masks_bits_pool: ti.Field = None  # (MAX_SONG_SLOTS, MAX_TIMELINE_FRONTIER_SURFACES, 4) u32
grid_sig0: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161) u64 - timeline signature (mask-derived)
grid_sig1: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161) u64 - timeline signature (counts-derived)
grid_gap: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161) i32 - gap to song end per (FT, FF)
grid_fever_activations: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161) i32 - fever activations per (FT, FF)
song_timestamps: ti.Field = None  # (MAX_SONG_NOTES,) f32
fever_end_idx_song: ti.Field = None  # (MAX_SONG_NOTES, GRID_SIZE) i32
song_note_group_idx: ti.Field = None  # (MAX_SONG_NOTES,) i32: note_idx -> group_idx
song_group_starts: ti.Field = None  # (MAX_SONG_NOTES,) i32: group_idx -> first note_idx
song_group_base_t_ms: ti.Field = None  # (MAX_SONG_NOTES,) i32: group_idx -> chart time in integer ms
song_group_low_ms: ti.Field = None  # (MAX_SONG_NOTES,) i32: group_idx -> min feasible carry (ms)
song_group_high_ms: ti.Field = None  # (MAX_SONG_NOTES,) i32: group_idx -> max feasible carry (ms)
genome_base_stats: ti.Field = None
population_indices: ti.Field = None  # (MAX_GENOMES, MAX_SLOTS) item_id per (genome,slot)
population_next_indices: ti.Field = None  # (MAX_GENOMES, MAX_SLOTS) next generation buffer
ga_initial_populations: ti.Field = None  # (MAX_GA_RUNS, MAX_GA_RUN_GENOMES, MAX_SLOTS) item_id per (run,genome,slot)
ga_init_heuristic_topk: ti.Field = None  # (MAX_SLOTS, GA_INIT_HEURISTIC_K) item_id per (slot,k)
item_stats: ti.Field = None  # (MAX_ITEMS, ITEM_STAT_DIM) dense item stats table
base_fixed_stats: ti.Field = None  # (ITEM_STAT_DIM,) fixed base stats (added to all genomes)
ga_scores: ti.Field = None  # (MAX_GENOMES,) int32 fitness scores (from evaluation)
ga_rng_state: ti.Field = None  # (MAX_GENOMES,) uint32 RNG state per genome/thread
ga_parent_a: ti.Field = None  # (MAX_GENOMES,) int32 selected parent index A
ga_parent_b: ti.Field = None  # (MAX_GENOMES,) int32 selected parent index B
GA_EXACT_EVAL_HASH_KEY_COLS = MAX_SLOTS  # encoded gear/minis genome IDs
GA_EXACT_EVAL_HASH_SIZE = 16384  # Open-addressing table for exact duplicate-genome detection.
ga_exact_eval_hash_used: ti.Field = None  # (HASH_SIZE,) i32 occupancy (0=empty, else rep_idx+1)
ga_exact_eval_hash_keys: ti.Field = None  # (HASH_SIZE, KEY_COLS) i32 exact genome key (trailing cols reserved)
ga_exact_eval_hash_sort_keys: ti.Field = None  # (MAX_GENOMES,) i32 hash keys for parallel sort grouping
ga_exact_eval_hash_sort_indices: ti.Field = None  # (MAX_GENOMES,) i32 genome indices permuted with sort keys
ga_exact_eval_rep_idx: ti.Field = None  # (MAX_GENOMES,) i32 representative genome index per row
ga_exact_eval_unique_count: ti.Field = None  # (1,) i32 number of unique genome rows
ga_warmstart_lane_best_key: ti.Field = None  # (MAX_GENOMES, REDUCE_BLOCK_DIM) u64 chunk-local lane winners
ga_warmstart_lane_best_results: ti.Field = None  # (MAX_GENOMES, REDUCE_BLOCK_DIM, 4) i32 [pp, cm, fm, ov]
ga_global_best_score: ti.Field = None  # (1,) i32 - best score across all generations
ga_global_best_genome: ti.Field = None  # (MAX_SLOTS,) i32 - item IDs of best genome
ga_global_best_results: ti.Field = None  # (7,) i32 - [score, ft, ff, pp, cm, fm, ov] for best genome
ga_global_best_scan_key: ti.Field = None  # (1,) u64 - reduction key ((score+1)<<32)|inv_genome_idx
ga_global_best_packed: ti.Field = None  # (17,) i32 - packed [score, genome_ids(9), results(7)] for single download
DEFAULT_MAX_GA_RUNS = 128  # Stores up to this many GA runs before a flush/download.
DEFAULT_MAX_GA_RUN_GENOMES = 1024  # Must be >= GA_POPULATION_SIZE.
MAX_GA_RUNS = DEFAULT_MAX_GA_RUNS
MAX_GA_RUN_GENOMES = DEFAULT_MAX_GA_RUN_GENOMES
# Non-env record of the last requested GA buffer sizing (replaces the
# GPU_NATIVE_GA_MAX_RUNS / GPU_NATIVE_GA_MAX_GENOMES env bridge). Re-applied
# before any early field allocation by _apply_requested_ga_run_buffers().
_REQUESTED_MAX_GA_RUNS: int | None = None
_REQUESTED_MAX_GA_RUN_GENOMES: int | None = None
ga_runs_payload_packed: ti.Field = None  # (MAX_GA_RUNS, MAX_GA_RUN_GENOMES+1, 17) i32
ga_fg_candidates_packed: ti.Field = (
    None  # (MAX_SONG_SLOTS, MAX_GA_RUNS, GA_FG_CANDIDATES_PER_RUN+1, GA_FG_CANDIDATE_COLS) i32
)
GA_FG_SELECTED_PAYLOAD_COLS = 2 + (1 + MAX_SLOTS + 7 + 7)  # (run,row) + packed candidate row (24)
GA_FG_SELECTED_MAX = 5000  # GPU GA->FG selection buffer capacity (safety bound; production funnel is LOADOUTS_PER_SONG_LIMIT).
GA_FG_SELECTED_HASH_SIZE = 65536  # Open-addressing table for dedupe (power of two).
GA_FG_SELECTED_STUBS_MAX = 20000  # Upper bound on unique stubs we support in GPU selection.
SKYLINE_FTFF_REDUCE_BLOCK_DIM = GA_FTFF_REDUCE_BLOCK_DIM
SKYLINE_FG_CANDIDATES_PER_RUN = GA_FG_CANDIDATES_PER_RUN
SKYLINE_FG_CANDIDATE_COLS = GA_FG_CANDIDATE_COLS
SKYLINE_INIT_HEURISTIC_K = GA_INIT_HEURISTIC_K
SKYLINE_EXACT_EVAL_HASH_KEY_COLS = GA_EXACT_EVAL_HASH_KEY_COLS
SKYLINE_EXACT_EVAL_HASH_SIZE = GA_EXACT_EVAL_HASH_SIZE
SKYLINE_FG_SELECTED_PAYLOAD_COLS = GA_FG_SELECTED_PAYLOAD_COLS
SKYLINE_FG_SELECTED_MAX = GA_FG_SELECTED_MAX
SKYLINE_FG_SELECTED_HASH_SIZE = GA_FG_SELECTED_HASH_SIZE
SKYLINE_FG_SELECTED_STUBS_MAX = GA_FG_SELECTED_STUBS_MAX
# GA->FG effective-dedup equivalence tables (Slice 1). Per-item i32 lookups the
# select kernel uses to fold name/color-equivalent loadouts before the top-N cut:
#   gear id  -> name rank (same gear Name => same rank)
#   mini id  -> effective signature id for the song's color context
# Uploaded once per (registry, color-context) at the ga_upload_item_stats site.
ga_fg_gear_name_rank: ti.Field = None  # (MAX_ITEMS,) i32 gear id -> name rank
ga_fg_mini_sig_id: ti.Field = None  # (MAX_ITEMS,) i32 mini id -> color-folded sig id
ga_fg_select_hash_used: ti.Field = None  # (HASH_SIZE,) i32 occupancy
ga_fg_select_hash_keys: ti.Field = None  # (HASH_SIZE, 9) i32
ga_fg_select_stub_count: ti.Field = None  # (1,) i32
ga_fg_select_stub_run: ti.Field = None  # (STUBS_MAX,) i32
ga_fg_select_stub_row: ti.Field = None  # (STUBS_MAX,) i32
ga_fg_select_stub_score: ti.Field = None  # (STUBS_MAX,) i32
ga_fg_select_stub_ids: ti.Field = None  # (STUBS_MAX, 9) i32
ga_fg_select_selected_mask: ti.Field = None  # (STUBS_MAX,) i32
ga_fg_selected_count: ti.Field = None  # (1,) i32
ga_fg_selected_coords: ti.Field = None  # (GA_FG_SELECTED_MAX, 2) i32
ga_fg_selected_payload_staging_256: ti.Field = None  # (257, GA_FG_SELECTED_PAYLOAD_COLS) i32
ga_fg_selected_payload_staging_1024: ti.Field = None  # (1025, GA_FG_SELECTED_PAYLOAD_COLS) i32
ga_fg_selected_payload_staging_5000: ti.Field = None  # (5001, GA_FG_SELECTED_PAYLOAD_COLS) i32
MAX_ISLANDS = 16  # Maximum number of islands
island_boundaries: ti.Field = None  # (MAX_ISLANDS+1,) i32 - island start indices + end sentinel
island_elite_indices: ti.Field = None  # (MAX_GENOMES,) i32 - output: elite genome indices
island_elite_count: ti.Field = None  # (1,) i32 - output: total elites found
slot_start: ti.Field = None  # (MAX_SLOTS,) int32 - first valid item_id for slot
slot_count: ti.Field = None  # (MAX_SLOTS,) int32 - number of items in slot pool
genome_result_stats: ti.Field = None  # Vector field [score, ft, ff, pp, cm, fm, ov]
genome_result_stats_download_staging_256: ti.Field = None  # (256,) vec7 i32
genome_result_stats_download_staging_1024: ti.Field = None  # (1024,) vec7 i32
chunk_best_key: ti.Field = None  # (MAX_GENOMES,) u64 packed key for safe per-chunk reduction
ga_eval_incumbent_score: ti.Field = None  # (MAX_GENOMES,) i32 shared exact-score incumbent for UB combo culling
ftff_combo_ft: ti.Field = None  # (MAX_FTFF_COMBOS,) i32 FT gems per combo
ftff_combo_ff: ti.Field = None  # (MAX_FTFF_COMBOS,) i32 FF gems per combo
timing_response_combo_ft: ti.Field = None  # (MAX_TIMING_RESPONSE_COMBOS,) i32 FT gems per antichain entry
timing_response_combo_ff: ti.Field = None  # (MAX_TIMING_RESPONSE_COMBOS,) i32 FF gems per antichain entry
timing_response_genome_offset: ti.Field = None  # (MAX_GENOMES,) i32 offset into timing_response_combo_*
timing_response_genome_length: ti.Field = None  # (MAX_GENOMES,) i32 antichain length per genome row
chunk_best_score: ti.Field = None  # (MAX_GENOMES,) i32 best score per genome
chunk_best_idx: ti.Field = None  # (MAX_GENOMES,) i32 winning combo index
chunk_best_results: ti.Field = None  # (MAX_GENOMES, 4) i32 - [pp, cm, fm, ov] from winning combo
DEFAULT_MAX_SKYLINE_RUNS = DEFAULT_MAX_GA_RUNS
DEFAULT_MAX_SKYLINE_RUN_GENOMES = DEFAULT_MAX_GA_RUN_GENOMES
MAX_SKYLINE_RUNS = MAX_GA_RUNS
MAX_SKYLINE_RUN_GENOMES = MAX_GA_RUN_GENOMES

skyline_initial_populations: ti.Field = None
skyline_init_heuristic_topk: ti.Field = None
skyline_scores: ti.Field = None
skyline_rng_state: ti.Field = None
skyline_parent_a: ti.Field = None
skyline_parent_b: ti.Field = None
skyline_exact_eval_hash_used: ti.Field = None
skyline_exact_eval_hash_keys: ti.Field = None
skyline_exact_eval_hash_sort_keys: ti.Field = None
skyline_exact_eval_hash_sort_indices: ti.Field = None
skyline_exact_eval_rep_idx: ti.Field = None
skyline_exact_eval_unique_count: ti.Field = None
skyline_global_best_score: ti.Field = None
skyline_global_best_genome: ti.Field = None
skyline_global_best_results: ti.Field = None
skyline_global_best_scan_key: ti.Field = None
skyline_global_best_packed: ti.Field = None
skyline_runs_payload_packed: ti.Field = None
skyline_fg_candidates_packed: ti.Field = None
skyline_fg_gear_name_rank: ti.Field = None
skyline_fg_mini_sig_id: ti.Field = None
skyline_fg_select_hash_used: ti.Field = None
skyline_fg_select_hash_keys: ti.Field = None
skyline_fg_select_stub_count: ti.Field = None
skyline_fg_select_stub_run: ti.Field = None
skyline_fg_select_stub_row: ti.Field = None
skyline_fg_select_stub_score: ti.Field = None
skyline_fg_select_stub_ids: ti.Field = None
skyline_fg_select_selected_mask: ti.Field = None
skyline_fg_selected_count: ti.Field = None
skyline_fg_selected_coords: ti.Field = None
skyline_fg_selected_payload_staging_256: ti.Field = None
skyline_fg_selected_payload_staging_1024: ti.Field = None
skyline_fg_selected_payload_staging_5000: ti.Field = None
_fields_allocated = False
_grid_fields_allocated = False


def _sync_skyline_aliases() -> None:
    global MAX_SKYLINE_RUNS, MAX_SKYLINE_RUN_GENOMES
    global skyline_initial_populations, skyline_init_heuristic_topk
    global skyline_scores, skyline_rng_state, skyline_parent_a, skyline_parent_b
    global skyline_exact_eval_hash_used, skyline_exact_eval_hash_keys
    global skyline_exact_eval_hash_sort_keys, skyline_exact_eval_hash_sort_indices
    global skyline_exact_eval_rep_idx, skyline_exact_eval_unique_count
    global skyline_global_best_score, skyline_global_best_genome, skyline_global_best_results
    global skyline_global_best_scan_key, skyline_global_best_packed
    global skyline_runs_payload_packed
    global skyline_fg_candidates_packed
    global skyline_fg_gear_name_rank, skyline_fg_mini_sig_id
    global skyline_fg_select_hash_used, skyline_fg_select_hash_keys
    global skyline_fg_select_stub_count, skyline_fg_select_stub_run, skyline_fg_select_stub_row
    global skyline_fg_select_stub_score, skyline_fg_select_stub_ids
    global skyline_fg_select_selected_mask, skyline_fg_selected_count, skyline_fg_selected_coords
    global skyline_fg_selected_payload_staging_256
    global skyline_fg_selected_payload_staging_1024
    global skyline_fg_selected_payload_staging_5000

    MAX_SKYLINE_RUNS = int(MAX_GA_RUNS)
    MAX_SKYLINE_RUN_GENOMES = int(MAX_GA_RUN_GENOMES)
    skyline_initial_populations = ga_initial_populations
    skyline_init_heuristic_topk = ga_init_heuristic_topk
    skyline_scores = ga_scores
    skyline_rng_state = ga_rng_state
    skyline_parent_a = ga_parent_a
    skyline_parent_b = ga_parent_b
    skyline_exact_eval_hash_used = ga_exact_eval_hash_used
    skyline_exact_eval_hash_keys = ga_exact_eval_hash_keys
    skyline_exact_eval_hash_sort_keys = ga_exact_eval_hash_sort_keys
    skyline_exact_eval_hash_sort_indices = ga_exact_eval_hash_sort_indices
    skyline_exact_eval_rep_idx = ga_exact_eval_rep_idx
    skyline_exact_eval_unique_count = ga_exact_eval_unique_count
    skyline_global_best_score = ga_global_best_score
    skyline_global_best_genome = ga_global_best_genome
    skyline_global_best_results = ga_global_best_results
    skyline_global_best_scan_key = ga_global_best_scan_key
    skyline_global_best_packed = ga_global_best_packed
    skyline_runs_payload_packed = ga_runs_payload_packed
    skyline_fg_candidates_packed = ga_fg_candidates_packed
    skyline_fg_gear_name_rank = ga_fg_gear_name_rank
    skyline_fg_mini_sig_id = ga_fg_mini_sig_id
    skyline_fg_select_hash_used = ga_fg_select_hash_used
    skyline_fg_select_hash_keys = ga_fg_select_hash_keys
    skyline_fg_select_stub_count = ga_fg_select_stub_count
    skyline_fg_select_stub_run = ga_fg_select_stub_run
    skyline_fg_select_stub_row = ga_fg_select_stub_row
    skyline_fg_select_stub_score = ga_fg_select_stub_score
    skyline_fg_select_stub_ids = ga_fg_select_stub_ids
    skyline_fg_select_selected_mask = ga_fg_select_selected_mask
    skyline_fg_selected_count = ga_fg_selected_count
    skyline_fg_selected_coords = ga_fg_selected_coords
    skyline_fg_selected_payload_staging_256 = ga_fg_selected_payload_staging_256
    skyline_fg_selected_payload_staging_1024 = ga_fg_selected_payload_staging_1024
    skyline_fg_selected_payload_staging_5000 = ga_fg_selected_payload_staging_5000


def is_fields_allocated() -> bool:
    """Check if main fields have been allocated."""
    return _fields_allocated
def is_grid_fields_allocated() -> bool:
    """Check if grid fields have been allocated."""
    return _grid_fields_allocated
def reset_fields_state() -> None:
    """
    Reset module-level allocation state after `ti.reset()`.
    All field objects become invalid after a Taichi runtime reset; we clear the
    globals so `ensure_fields_allocated()` can safely re-allocate and re-bind.
    """
    global _fields_allocated, _grid_fields_allocated
    global MAX_GA_RUNS, MAX_GA_RUN_GENOMES, _REQUESTED_MAX_GA_RUNS, _REQUESTED_MAX_GA_RUN_GENOMES
    global ref_pp_field, ref_cm_field, ref_fm_field, ref_ft_field, ref_ff_field
    global exact_pp_best_gems_prefix
    global grid_count_body_fever, grid_count_body_normal, grid_head_len
    global grid_N_hn, grid_N_hf, grid_Sigma_hn, grid_Sigma_hf
    global grid_fever_masks_bits
    global grid_frontier_count, grid_frontier_offset
    global grid_frontier_body_fever_pool, grid_frontier_body_normal_pool, grid_frontier_masks_bits_pool
    global grid_sig0, grid_sig1
    global grid_gap, grid_fever_activations
    global song_timestamps, fever_end_idx_song
    global song_note_group_idx, song_group_starts, song_group_base_t_ms, song_group_low_ms, song_group_high_ms
    global genome_base_stats
    global population_indices, population_next_indices, ga_initial_populations, ga_init_heuristic_topk
    global item_stats, base_fixed_stats
    global ga_scores, ga_rng_state, ga_parent_a, ga_parent_b
    global ga_exact_eval_hash_used, ga_exact_eval_hash_keys
    global ga_exact_eval_hash_sort_keys, ga_exact_eval_hash_sort_indices
    global ga_exact_eval_rep_idx, ga_exact_eval_unique_count
    global ga_warmstart_lane_best_key, ga_warmstart_lane_best_results
    global slot_start, slot_count
    global genome_result_stats
    global genome_result_stats_download_staging_256, genome_result_stats_download_staging_1024
    global chunk_best_key, chunk_best_score, chunk_best_idx, chunk_best_results
    global ga_eval_incumbent_score
    global ftff_combo_ft, ftff_combo_ff
    global timing_response_combo_ft, timing_response_combo_ff
    global timing_response_genome_offset, timing_response_genome_length
    global timing_response_combo_ft, timing_response_combo_ff
    global timing_response_genome_offset, timing_response_genome_length
    global ga_global_best_score, ga_global_best_genome, ga_global_best_results, ga_global_best_scan_key
    global ga_global_best_packed
    global ga_runs_payload_packed
    global ga_fg_candidates_packed
    global ga_fg_gear_name_rank, ga_fg_mini_sig_id
    global ga_fg_select_hash_used, ga_fg_select_hash_keys
    global ga_fg_select_stub_count, ga_fg_select_stub_run, ga_fg_select_stub_row, ga_fg_select_stub_score
    global ga_fg_select_stub_ids
    global ga_fg_select_selected_mask, ga_fg_selected_count, ga_fg_selected_coords
    global ga_fg_selected_payload_staging_256, ga_fg_selected_payload_staging_1024, ga_fg_selected_payload_staging_5000
    global island_boundaries, island_elite_indices, island_elite_count
    ref_pp_field = None
    ref_cm_field = None
    ref_fm_field = None
    ref_ft_field = None
    ref_ff_field = None
    exact_pp_best_gems_prefix = None
    grid_count_body_fever = None
    grid_count_body_normal = None
    grid_head_len = None
    grid_N_hn = None
    grid_N_hf = None
    grid_Sigma_hn = None
    grid_Sigma_hf = None
    grid_fever_masks_bits = None
    grid_frontier_count = None
    grid_frontier_offset = None
    grid_frontier_body_fever_pool = None
    grid_frontier_body_normal_pool = None
    grid_frontier_masks_bits_pool = None
    grid_sig0 = None
    grid_sig1 = None
    grid_gap = None
    grid_fever_activations = None
    song_timestamps = None
    fever_end_idx_song = None
    song_note_group_idx = None
    song_group_starts = None
    song_group_base_t_ms = None
    song_group_low_ms = None
    song_group_high_ms = None
    genome_base_stats = None
    population_indices = None
    population_next_indices = None
    ga_initial_populations = None
    ga_init_heuristic_topk = None
    item_stats = None
    base_fixed_stats = None
    ga_scores = None
    ga_rng_state = None
    ga_parent_a = None
    ga_parent_b = None
    ga_exact_eval_hash_used = None
    ga_exact_eval_hash_keys = None
    ga_exact_eval_hash_sort_keys = None
    ga_exact_eval_hash_sort_indices = None
    ga_exact_eval_rep_idx = None
    ga_exact_eval_unique_count = None
    ga_warmstart_lane_best_key = None
    ga_warmstart_lane_best_results = None
    slot_start = None
    slot_count = None
    island_boundaries = None
    island_elite_indices = None
    island_elite_count = None
    ga_global_best_score = None
    ga_global_best_genome = None
    ga_global_best_results = None
    ga_global_best_scan_key = None
    ga_global_best_packed = None
    ga_runs_payload_packed = None
    ga_fg_candidates_packed = None
    ga_fg_gear_name_rank = None
    ga_fg_mini_sig_id = None
    ga_fg_select_hash_used = None
    ga_fg_select_hash_keys = None
    ga_fg_select_stub_count = None
    ga_fg_select_stub_run = None
    ga_fg_select_stub_row = None
    ga_fg_select_stub_score = None
    ga_fg_select_stub_ids = None
    ga_fg_select_selected_mask = None
    ga_fg_selected_count = None
    ga_fg_selected_coords = None
    ga_fg_selected_payload_staging_256 = None
    ga_fg_selected_payload_staging_1024 = None
    ga_fg_selected_payload_staging_5000 = None
    genome_result_stats = None
    genome_result_stats_download_staging_256 = None
    genome_result_stats_download_staging_1024 = None
    chunk_best_key = None
    ga_eval_incumbent_score = None
    chunk_best_score = None
    chunk_best_idx = None
    chunk_best_results = None
    ftff_combo_ft = None
    ftff_combo_ff = None
    timing_response_combo_ft = None
    timing_response_combo_ff = None
    timing_response_genome_offset = None
    timing_response_genome_length = None
    MAX_GA_RUNS = int(DEFAULT_MAX_GA_RUNS)
    MAX_GA_RUN_GENOMES = int(DEFAULT_MAX_GA_RUN_GENOMES)
    # Restore-defaults-on-reset contract (docs/Implementation Records/
    # GPU_GA_BUFFER_CONFIG_RESET_RESTORE.md): clear the requested record so a stale
    # session size never silently re-applies after a hard_reset_taichi. The GA
    # recovery paths (genetic_pipeline.py) explicitly re-call configure_ga_run_buffers()
    # after a mid-run reset to re-size for the rest of the song -- fixing the
    # padded-transfer cost WITHOUT breaking the restore-defaults contract.
    _REQUESTED_MAX_GA_RUNS = None
    _REQUESTED_MAX_GA_RUN_GENOMES = None
    _sync_skyline_aliases()
    _fields_allocated = False
    _grid_fields_allocated = False
    _last_uploaded_grid_id = None
def _clamp_ga_runs(n: int) -> int:
    if n < 1:
        return 1
    if n > 8192:
        return 8192
    return n
def _clamp_ga_genomes(n: int) -> int:
    if n < 250:
        return 250
    if n > MAX_GENOMES:
        return MAX_GENOMES
    return n
def configure_ga_run_buffers(*, max_runs: int | None = None, max_genomes: int | None = None) -> None:
    """
    Configure GPU-native GA buffer sizes before fields are allocated.
    This reduces large padded CPUâ†”GPU transfers in GA multi-run mode by shrinking
    `ga_initial_populations` and `ga_runs_payload_packed` to the smallest required
    shapes for the current session.
    Callers MUST invoke this before the first `ensure_fields_allocated()`/kernel run.
    """
    global MAX_GA_RUNS, MAX_GA_RUN_GENOMES, _REQUESTED_MAX_GA_RUNS, _REQUESTED_MAX_GA_RUN_GENOMES
    # Record the requested sizing even if fields are already allocated, so a later
    # reset_fields_state() + re-allocation re-applies it (replaces the env bridge).
    if max_runs is not None:
        _REQUESTED_MAX_GA_RUNS = int(max_runs)
    if max_genomes is not None:
        _REQUESTED_MAX_GA_RUN_GENOMES = int(max_genomes)
    if _fields_allocated:
        return
    if max_runs is not None:
        MAX_GA_RUNS = _clamp_ga_runs(int(max_runs))
    if max_genomes is not None:
        MAX_GA_RUN_GENOMES = _clamp_ga_genomes(int(max_genomes))
    _sync_skyline_aliases()


def configure_skyline_run_buffers(*, max_runs: int | None = None, max_genomes: int | None = None) -> None:
    configure_ga_run_buffers(max_runs=max_runs, max_genomes=max_genomes)
def _apply_requested_ga_run_buffers() -> None:
    """
    Re-apply the last requested GA buffer sizing before the first field allocation.

    GA multi-run payloads otherwise allocate at the large defaults and incur big
    padded Vulkan `to_numpy()` transfers when fields are allocated (e.g., by the
    in-process GPU executor warmup) before the GA code's own
    `configure_ga_run_buffers()` call. The requested sizes are recorded in-process
    by `configure_ga_run_buffers()` (this replaces the former
    `GPU_NATIVE_GA_MAX_RUNS` / `GPU_NATIVE_GA_MAX_GENOMES` env bridge).
    """
    if _fields_allocated:
        return
    if _REQUESTED_MAX_GA_RUNS is None and _REQUESTED_MAX_GA_RUN_GENOMES is None:
        return
    configure_ga_run_buffers(
        max_runs=_REQUESTED_MAX_GA_RUNS,
        max_genomes=_REQUESTED_MAX_GA_RUN_GENOMES,
    )
def allocate_fields():
    """
    Allocate GPU fields. Must be called after ti.init().
    This allocates the baseline Taichi fields used by the solvers and GPU-native GA.
    """
    global ref_pp_field, ref_cm_field, ref_fm_field, ref_ft_field, ref_ff_field
    global exact_pp_best_gems_prefix
    global genome_base_stats
    global \
        population_indices, \
        population_next_indices, \
        ga_initial_populations, \
        ga_init_heuristic_topk, \
        item_stats, \
        base_fixed_stats
    global ga_scores, ga_rng_state, ga_parent_a, ga_parent_b
    global ga_exact_eval_hash_used, ga_exact_eval_hash_keys
    global ga_exact_eval_hash_sort_keys, ga_exact_eval_hash_sort_indices
    global ga_exact_eval_rep_idx, ga_exact_eval_unique_count
    global ga_warmstart_lane_best_key, ga_warmstart_lane_best_results
    global slot_start, slot_count
    global genome_result_stats
    global genome_result_stats_download_staging_256, genome_result_stats_download_staging_1024
    global chunk_best_key, chunk_best_score, chunk_best_idx, chunk_best_results
    global ga_eval_incumbent_score
    global ftff_combo_ft, ftff_combo_ff
    global timing_response_combo_ft, timing_response_combo_ff
    global timing_response_genome_offset, timing_response_genome_length
    global ga_global_best_score, ga_global_best_genome, ga_global_best_results, ga_global_best_scan_key
    global ga_global_best_packed
    global ga_runs_payload_packed
    global ga_fg_candidates_packed
    global ga_fg_gear_name_rank, ga_fg_mini_sig_id
    global ga_fg_select_hash_used, ga_fg_select_hash_keys
    global ga_fg_select_stub_count, ga_fg_select_stub_run, ga_fg_select_stub_row, ga_fg_select_stub_score
    global ga_fg_select_stub_ids
    global ga_fg_select_selected_mask, ga_fg_selected_count, ga_fg_selected_coords
    global ga_fg_selected_payload_staging_256, ga_fg_selected_payload_staging_1024, ga_fg_selected_payload_staging_5000
    global island_boundaries, island_elite_indices, island_elite_count
    global _fields_allocated
    if _fields_allocated:
        return
    ref_pp_field = ti.field(dtype=ti.f32, shape=161)
    ref_cm_field = ti.field(dtype=ti.f32, shape=161)
    ref_fm_field = ti.field(dtype=ti.f32, shape=161)
    ref_ft_field = ti.field(dtype=ti.f32, shape=161)
    ref_ff_field = ti.field(dtype=ti.f32, shape=161)
    exact_pp_best_gems_prefix = ti.field(dtype=ti.i16, shape=(16, GRID_SIZE, MAX_TOTAL_BUDGET + 1))
    genome_base_stats = ti.Vector.field(n=7, dtype=ti.i16, shape=MAX_GENOMES)
    population_indices = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, MAX_SLOTS))
    population_next_indices = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, MAX_SLOTS))
    ga_initial_populations = ti.field(dtype=ti.i32, shape=(MAX_GA_RUNS, MAX_GA_RUN_GENOMES, MAX_SLOTS))
    if GA_INIT_HEURISTIC_K > 0:
        ga_init_heuristic_topk = ti.field(dtype=ti.i32, shape=(MAX_SLOTS, GA_INIT_HEURISTIC_K))
    else:
        ga_init_heuristic_topk = ti.field(dtype=ti.i32, shape=(MAX_SLOTS, 1))
    item_stats = ti.field(dtype=ti.i32, shape=(MAX_ITEMS, ITEM_STAT_DIM))
    base_fixed_stats = ti.field(dtype=ti.i32, shape=ITEM_STAT_DIM)
    ga_scores = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    ga_rng_state = ti.field(dtype=ti.u32, shape=MAX_GENOMES)
    ga_parent_a = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    ga_parent_b = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    ga_exact_eval_hash_used = ti.field(dtype=ti.i32, shape=int(GA_EXACT_EVAL_HASH_SIZE))
    ga_exact_eval_hash_keys = ti.field(
        dtype=ti.i32,
        shape=(int(GA_EXACT_EVAL_HASH_SIZE), int(GA_EXACT_EVAL_HASH_KEY_COLS)),
    )
    ga_exact_eval_hash_sort_keys = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    ga_exact_eval_hash_sort_indices = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    ga_exact_eval_rep_idx = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    ga_exact_eval_unique_count = ti.field(dtype=ti.i32, shape=1)
    ga_warmstart_lane_best_key = ti.field(dtype=ti.u64, shape=(MAX_GENOMES, int(GA_FTFF_REDUCE_BLOCK_DIM)))
    ga_warmstart_lane_best_results = ti.field(
        dtype=ti.i32,
        shape=(MAX_GENOMES, int(GA_FTFF_REDUCE_BLOCK_DIM), 4),
    )
    slot_start = ti.field(dtype=ti.i32, shape=MAX_SLOTS)
    slot_count = ti.field(dtype=ti.i32, shape=MAX_SLOTS)
    genome_result_stats = ti.Vector.field(n=7, dtype=ti.i32, shape=MAX_GENOMES)
    genome_result_stats_download_staging_256 = ti.Vector.field(n=7, dtype=ti.i32, shape=256)
    genome_result_stats_download_staging_1024 = ti.Vector.field(n=7, dtype=ti.i32, shape=1024)
    chunk_best_key = ti.field(dtype=ti.u64, shape=MAX_GENOMES)
    ga_eval_incumbent_score = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    chunk_best_score = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    chunk_best_idx = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    ftff_combo_ft = ti.field(dtype=ti.i32, shape=MAX_FTFF_COMBOS)
    ftff_combo_ff = ti.field(dtype=ti.i32, shape=MAX_FTFF_COMBOS)
    timing_response_combo_ft = ti.field(dtype=ti.i32, shape=MAX_TIMING_RESPONSE_COMBOS)
    timing_response_combo_ff = ti.field(dtype=ti.i32, shape=MAX_TIMING_RESPONSE_COMBOS)
    timing_response_genome_offset = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    timing_response_genome_length = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    chunk_best_results = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, 4))
    ga_global_best_score = ti.field(dtype=ti.i32, shape=1)
    ga_global_best_genome = ti.field(dtype=ti.i32, shape=MAX_SLOTS)
    ga_global_best_results = ti.field(dtype=ti.i32, shape=7)  # [score, ft, ff, pp, cm, fm, ov]
    ga_global_best_scan_key = ti.field(dtype=ti.u64, shape=1)
    ga_global_best_packed = ti.field(dtype=ti.i32, shape=17)  # [score, genome_ids(9), results(7)]
    _payload_cols = 1 + MAX_SLOTS + 7
    ga_runs_payload_packed = ti.field(dtype=ti.i32, shape=(MAX_GA_RUNS, MAX_GA_RUN_GENOMES + 1, _payload_cols))
    ga_fg_candidates_packed = ti.field(
        dtype=ti.i32,
        shape=(MAX_SONG_SLOTS, MAX_GA_RUNS, int(GA_FG_CANDIDATES_PER_RUN) + 1, int(GA_FG_CANDIDATE_COLS)),
    )
    ga_fg_gear_name_rank = ti.field(dtype=ti.i32, shape=int(MAX_ITEMS))
    ga_fg_mini_sig_id = ti.field(dtype=ti.i32, shape=int(MAX_ITEMS))
    ga_fg_select_hash_used = ti.field(dtype=ti.i32, shape=int(GA_FG_SELECTED_HASH_SIZE))
    ga_fg_select_hash_keys = ti.field(dtype=ti.i32, shape=(int(GA_FG_SELECTED_HASH_SIZE), 9))
    ga_fg_select_stub_count = ti.field(dtype=ti.i32, shape=1)
    ga_fg_select_stub_run = ti.field(dtype=ti.i32, shape=int(GA_FG_SELECTED_STUBS_MAX))
    ga_fg_select_stub_row = ti.field(dtype=ti.i32, shape=int(GA_FG_SELECTED_STUBS_MAX))
    ga_fg_select_stub_score = ti.field(dtype=ti.i32, shape=int(GA_FG_SELECTED_STUBS_MAX))
    ga_fg_select_stub_ids = ti.field(dtype=ti.i32, shape=(int(GA_FG_SELECTED_STUBS_MAX), 9))
    ga_fg_select_selected_mask = ti.field(dtype=ti.i32, shape=int(GA_FG_SELECTED_STUBS_MAX))
    ga_fg_selected_count = ti.field(dtype=ti.i32, shape=1)
    ga_fg_selected_coords = ti.field(dtype=ti.i32, shape=(int(GA_FG_SELECTED_MAX), 2))
    ga_fg_selected_payload_staging_256 = ti.field(
        dtype=ti.i32,
        shape=(257, int(GA_FG_SELECTED_PAYLOAD_COLS)),
    )
    ga_fg_selected_payload_staging_1024 = ti.field(
        dtype=ti.i32,
        shape=(1025, int(GA_FG_SELECTED_PAYLOAD_COLS)),
    )
    ga_fg_selected_payload_staging_5000 = ti.field(
        dtype=ti.i32,
        shape=(int(GA_FG_SELECTED_MAX) + 1, int(GA_FG_SELECTED_PAYLOAD_COLS)),
    )
    MAX_ISLANDS = 16  # Maximum number of islands
    island_boundaries = ti.field(dtype=ti.i32, shape=MAX_ISLANDS + 1)  # [start0, start1, ..., end_last]
    island_elite_indices = ti.field(dtype=ti.i32, shape=MAX_GENOMES)  # Output: elite genome indices
    island_elite_count = ti.field(dtype=ti.i32, shape=1)  # Output: total elites found
    _sync_skyline_aliases()
    _fields_allocated = True
    logger.debug("[Taichi] Allocated GPU fields: %s genomes", MAX_GENOMES)
def allocate_grid_fields():
    """
    Allocate GPU fields for timeline grid. Must be called after ti.init().
    This allocates MAX_SONG_SLOTS Ã— 161Ã—161 timeline grids for batch coalescing.
    Each song slot can hold a different song's grid for parallel processing.
    """
    global grid_count_body_fever, grid_count_body_normal, grid_head_len
    global grid_N_hn, grid_N_hf, grid_Sigma_hn, grid_Sigma_hf
    global grid_fever_masks_bits
    global grid_frontier_count, grid_frontier_offset
    global grid_frontier_body_fever_pool, grid_frontier_body_normal_pool, grid_frontier_masks_bits_pool
    global grid_sig0, grid_sig1
    global grid_gap, grid_fever_activations
    global song_timestamps, fever_end_idx_song
    global song_note_group_idx, song_group_starts, song_group_base_t_ms, song_group_low_ms, song_group_high_ms
    global _grid_fields_allocated
    if _grid_fields_allocated:
        return
    grid_count_body_fever = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_count_body_normal = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_head_len = ti.field(dtype=ti.i8, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_N_hn = ti.field(dtype=ti.i16, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_N_hf = ti.field(dtype=ti.i16, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_Sigma_hn = ti.field(dtype=ti.i16, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_Sigma_hf = ti.field(dtype=ti.i16, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_fever_masks_bits = ti.field(dtype=ti.u32, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE, 4))
    grid_frontier_count = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_frontier_offset = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_frontier_body_fever_pool = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, MAX_TIMELINE_FRONTIER_SURFACES))
    grid_frontier_body_normal_pool = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, MAX_TIMELINE_FRONTIER_SURFACES))
    grid_frontier_masks_bits_pool = ti.field(dtype=ti.u32, shape=(MAX_SONG_SLOTS, MAX_TIMELINE_FRONTIER_SURFACES, 4))
    grid_sig0 = ti.field(dtype=ti.u64, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_sig1 = ti.field(dtype=ti.u64, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_gap = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_fever_activations = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    if song_timestamps is None:
        song_timestamps = ti.field(dtype=ti.f32, shape=MAX_SONG_NOTES)
    if fever_end_idx_song is None:
        fever_end_idx_song = ti.field(dtype=ti.i32, shape=(MAX_SONG_NOTES, GRID_SIZE))
    if song_note_group_idx is None:
        song_note_group_idx = ti.field(dtype=ti.i32, shape=MAX_SONG_NOTES)
    if song_group_starts is None:
        song_group_starts = ti.field(dtype=ti.i32, shape=MAX_SONG_NOTES)
    if song_group_base_t_ms is None:
        song_group_base_t_ms = ti.field(dtype=ti.i32, shape=MAX_SONG_NOTES)
    if song_group_low_ms is None:
        song_group_low_ms = ti.field(dtype=ti.i32, shape=MAX_SONG_NOTES)
    if song_group_high_ms is None:
        song_group_high_ms = ti.field(dtype=ti.i32, shape=MAX_SONG_NOTES)
    _grid_fields_allocated = True
    logger.debug(
        "[Taichi] Allocated grid fields: %s x %s x %s timeline grid slots",
        MAX_SONG_SLOTS,
        GRID_SIZE,
        GRID_SIZE,
    )
def bind_fields(kernels_module):
    """
    Bind live field objects to the kernels module.
    This must be called AFTER field allocation, so that kernels can access
    the actual ti.field objects rather than None placeholders.
    If kernels is a package (has kernels_helpers submodule), binds to kernels_helpers.
    Otherwise binds to the module directly.
    Args:
        kernels_module: The kernels module or package to bind fields to
    """
    try:
        from . import kernels
        target = kernels.kernels_helpers
    except (ImportError, AttributeError):
        target = kernels_module
    target.ref_pp_field = ref_pp_field
    target.ref_cm_field = ref_cm_field
    target.ref_fm_field = ref_fm_field
    target.ref_ft_field = ref_ft_field
    target.ref_ff_field = ref_ff_field
    target.exact_pp_best_gems_prefix = exact_pp_best_gems_prefix
    target.grid_count_body_fever = grid_count_body_fever
    target.grid_count_body_normal = grid_count_body_normal
    target.grid_head_len = grid_head_len
    target.grid_N_hn = grid_N_hn
    target.grid_N_hf = grid_N_hf
    target.grid_Sigma_hn = grid_Sigma_hn
    target.grid_Sigma_hf = grid_Sigma_hf
    target.grid_fever_masks_bits = grid_fever_masks_bits
    target.grid_frontier_count = grid_frontier_count
    target.grid_frontier_offset = grid_frontier_offset
    target.grid_frontier_body_fever_pool = grid_frontier_body_fever_pool
    target.grid_frontier_body_normal_pool = grid_frontier_body_normal_pool
    target.grid_frontier_masks_bits_pool = grid_frontier_masks_bits_pool
    target.grid_sig0 = grid_sig0
    target.grid_sig1 = grid_sig1
    target.grid_gap = grid_gap
    target.grid_fever_activations = grid_fever_activations
    target.song_timestamps = song_timestamps
    target.fever_end_idx_song = fever_end_idx_song
    target.song_note_group_idx = song_note_group_idx
    target.song_group_starts = song_group_starts
    target.song_group_base_t_ms = song_group_base_t_ms
    target.song_group_low_ms = song_group_low_ms
    target.song_group_high_ms = song_group_high_ms
    target.genome_base_stats = genome_base_stats
    target.population_indices = population_indices
    target.population_next_indices = population_next_indices
    target.ga_initial_populations = ga_initial_populations
    target.ga_init_heuristic_topk = ga_init_heuristic_topk
    target.item_stats = item_stats
    target.base_fixed_stats = base_fixed_stats
    target.ga_scores = ga_scores
    target.ga_rng_state = ga_rng_state
    target.ga_parent_a = ga_parent_a
    target.ga_parent_b = ga_parent_b
    target.ga_exact_eval_hash_used = ga_exact_eval_hash_used
    target.ga_exact_eval_hash_keys = ga_exact_eval_hash_keys
    target.ga_exact_eval_hash_sort_keys = ga_exact_eval_hash_sort_keys
    target.ga_exact_eval_hash_sort_indices = ga_exact_eval_hash_sort_indices
    target.ga_exact_eval_rep_idx = ga_exact_eval_rep_idx
    target.ga_exact_eval_unique_count = ga_exact_eval_unique_count
    target.ga_warmstart_lane_best_key = ga_warmstart_lane_best_key
    target.ga_warmstart_lane_best_results = ga_warmstart_lane_best_results
    target.slot_start = slot_start
    target.slot_count = slot_count
    target.genome_result_stats = genome_result_stats
    target.chunk_best_key = chunk_best_key
    target.ga_eval_incumbent_score = ga_eval_incumbent_score
    target.chunk_best_score = chunk_best_score
    target.chunk_best_idx = chunk_best_idx
    target.ftff_combo_ft = ftff_combo_ft
    target.ftff_combo_ff = ftff_combo_ff
    target.chunk_best_results = chunk_best_results
    target.ga_global_best_score = ga_global_best_score
    target.ga_global_best_genome = ga_global_best_genome
    target.ga_global_best_results = ga_global_best_results
    target.ga_global_best_scan_key = ga_global_best_scan_key
    target.ga_global_best_packed = ga_global_best_packed
    target.ga_runs_payload_packed = ga_runs_payload_packed
    target.ga_fg_candidates_packed = ga_fg_candidates_packed
    target.ga_fg_gear_name_rank = ga_fg_gear_name_rank
    target.ga_fg_mini_sig_id = ga_fg_mini_sig_id
    target.ga_fg_select_hash_used = ga_fg_select_hash_used
    target.ga_fg_select_hash_keys = ga_fg_select_hash_keys
    target.ga_fg_select_stub_count = ga_fg_select_stub_count
    target.ga_fg_select_stub_run = ga_fg_select_stub_run
    target.ga_fg_select_stub_row = ga_fg_select_stub_row
    target.ga_fg_select_stub_score = ga_fg_select_stub_score
    target.ga_fg_select_stub_ids = ga_fg_select_stub_ids
    target.ga_fg_select_selected_mask = ga_fg_select_selected_mask
    target.ga_fg_selected_count = ga_fg_selected_count
    target.ga_fg_selected_coords = ga_fg_selected_coords
    target.ga_fg_selected_payload_staging_256 = ga_fg_selected_payload_staging_256
    target.ga_fg_selected_payload_staging_1024 = ga_fg_selected_payload_staging_1024
    target.ga_fg_selected_payload_staging_5000 = ga_fg_selected_payload_staging_5000
    target.skyline_initial_populations = skyline_initial_populations
    target.skyline_init_heuristic_topk = skyline_init_heuristic_topk
    target.skyline_scores = skyline_scores
    target.skyline_rng_state = skyline_rng_state
    target.skyline_parent_a = skyline_parent_a
    target.skyline_parent_b = skyline_parent_b
    target.skyline_exact_eval_hash_used = skyline_exact_eval_hash_used
    target.skyline_exact_eval_hash_keys = skyline_exact_eval_hash_keys
    target.skyline_exact_eval_hash_sort_keys = skyline_exact_eval_hash_sort_keys
    target.skyline_exact_eval_hash_sort_indices = skyline_exact_eval_hash_sort_indices
    target.skyline_exact_eval_rep_idx = skyline_exact_eval_rep_idx
    target.skyline_exact_eval_unique_count = skyline_exact_eval_unique_count
    target.skyline_global_best_score = skyline_global_best_score
    target.skyline_global_best_genome = skyline_global_best_genome
    target.skyline_global_best_results = skyline_global_best_results
    target.skyline_global_best_scan_key = skyline_global_best_scan_key
    target.skyline_global_best_packed = skyline_global_best_packed
    target.skyline_runs_payload_packed = skyline_runs_payload_packed
    target.skyline_fg_candidates_packed = skyline_fg_candidates_packed
    target.skyline_fg_gear_name_rank = skyline_fg_gear_name_rank
    target.skyline_fg_mini_sig_id = skyline_fg_mini_sig_id
    target.skyline_fg_select_hash_used = skyline_fg_select_hash_used
    target.skyline_fg_select_hash_keys = skyline_fg_select_hash_keys
    target.skyline_fg_select_stub_count = skyline_fg_select_stub_count
    target.skyline_fg_select_stub_run = skyline_fg_select_stub_run
    target.skyline_fg_select_stub_row = skyline_fg_select_stub_row
    target.skyline_fg_select_stub_score = skyline_fg_select_stub_score
    target.skyline_fg_select_stub_ids = skyline_fg_select_stub_ids
    target.skyline_fg_select_selected_mask = skyline_fg_select_selected_mask
    target.skyline_fg_selected_count = skyline_fg_selected_count
    target.skyline_fg_selected_coords = skyline_fg_selected_coords
    target.skyline_fg_selected_payload_staging_256 = skyline_fg_selected_payload_staging_256
    target.skyline_fg_selected_payload_staging_1024 = skyline_fg_selected_payload_staging_1024
    target.skyline_fg_selected_payload_staging_5000 = skyline_fg_selected_payload_staging_5000
    target.timing_response_combo_ft = timing_response_combo_ft
    target.timing_response_combo_ff = timing_response_combo_ff
    target.timing_response_genome_offset = timing_response_genome_offset
    target.timing_response_genome_length = timing_response_genome_length
    target.island_boundaries = island_boundaries
    target.island_elite_indices = island_elite_indices
    target.island_elite_count = island_elite_count
def ensure_fields_allocated():
    """
    Ensure Taichi is initialized and fields are allocated.
    This is the main entry point for ensuring the GPU is ready.
    Initializes Taichi if needed, allocates fields, and binds them to kernels.
    """
    if not is_initialized():
        init_taichi()
    if not _fields_allocated:
        _apply_requested_ga_run_buffers()
        allocate_fields()
        global song_timestamps
        if song_timestamps is None:
            song_timestamps = ti.field(dtype=ti.f32, shape=MAX_SONG_NOTES)
        from . import kernels
        bind_fields(kernels)
def ensure_grid_fields_allocated():
    """
    Ensure grid fields are allocated for timeline lookups.
    Call this before uploading or using the timeline grid.
    """
    ensure_fields_allocated()  # Main fields must be allocated first
    if not _grid_fields_allocated:
        allocate_grid_fields()
        from . import kernels
        bind_fields(kernels)
