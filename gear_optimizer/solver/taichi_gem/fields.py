"""
Taichi Fields - GPU field declarations and allocation.

This module handles:
- All ti.Field declarations (reference tables, work items, genome data, results)
- Field allocation functions
- Grid fields for timeline lookups
- bind_fields() to inject live field objects into kernels module
"""

import logging
import sys

import taichi as ti

from gear_optimizer.core.parsing import env_flag, env_int

from .runtime import is_initialized, init_taichi

# Platform detection for Metal-specific fields
from gear_optimizer.core.parsing import env_get
IS_METAL = sys.platform == "darwin"
logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS
# ============================================================================

GRID_SIZE = 161  # Timeline grid dimension (161x161 = 26,521 entries per song)
MAX_HEAD_NOTES = 100  # Maximum notes in head section
MAX_GENOMES = max(4096, min(env_int("GPU_MAX_GENOMES", 8192), 32768))
"""Maximum active genomes per GPU dispatch.

The production target can experiment with larger batches when useful, but the
8192-row default is the recovered steady-state skyline profile on the target
GPU-first path. Keep a 4096 floor and clamp the env override so accidental
values do not turn field allocation into an OOM trap.
"""
MAX_SLOTS = 9  # 6 gear + 3 minis (GPU-native skyline representation)
MAX_ITEMS = 65536  # Upper bound for (type,Name)-deduped items per song (row 0 reserved)
ITEM_STAT_DIM = 10  # PP, CM, FM, FT, FF, Beat, Vibe, Rush, Flow, Chill
MAX_SONG_NOTES = 200000  # Maximum song length for GPU timeline computation
MAX_EVALS_PER_DISPATCH = max(
    4_194_304,
    min(env_int("SKYLINE_GPU_MAX_EVALS_PER_DISPATCH", 67_108_864), 67_108_864),
)  # Upper bound used for chunking (genomes * FT/FF combos)


def _clamp_song_slots(n: int) -> int:
    # Slot 0 is always reserved; keep at least one additional slot for prefetch/batching.
    if n < 2:
        return 2
    # Prevent accidental huge allocations (each slot is ~3MB of timeline grids).
    if n > 256:
        try:
            logger.warning("[GPU] GPU_SONG_SLOTS=%s too large; clamping to 256 to avoid VRAM OOM.", int(n))
        except Exception as e:
            logger.debug(f"fields:_clamp_song_slots: {e}")
        return 256
    return n


MAX_TIMELINE_FRONTIER_SURFACES = env_int("GPU_TIMELINE_FRONTIER_SURFACES", 262144)
MAX_TIMELINE_FRONTIER_SURFACES = max(1, min(int(MAX_TIMELINE_FRONTIER_SURFACES), 1_048_576))


# Concurrent song grid slots for batch coalescing / timeline caching.
# Override via env var `GPU_SONG_SLOTS` (set before process start).
MAX_SONG_SLOTS = _clamp_song_slots(env_int("GPU_SONG_SLOTS", 8))
MAX_TOTAL_BUDGET = 90  # Max supported total_budget for FT/FF combo tables
MAX_FTFF_COMBOS = (MAX_TOTAL_BUDGET + 1) * (MAX_TOTAL_BUDGET + 2) // 2  # 4186 when MAX_TOTAL_BUDGET=90
MAX_BP_PAIRS = 256  # Breakpoint kernel scan pairs

# Optional allocations: unpacked timeline masks are optional; bitpacked masks are the production path.
WRITE_UNPACKED_GRID_MASKS_DEFAULT = env_flag("GPU_TIMELINE_WRITE_UNPACKED_MASKS")

# FT/FF combo reduction sizing (Vulkan path).
# Used by the warmstart and combo-search reduction kernels.
SKYLINE_FTFF_REDUCE_BLOCK_DIM = env_int(
    "SKYLINE_FTFF_REDUCE_BLOCK_DIM", 256
)  # Must match kernels/skyline_eval/warmstart.py Vulkan block dim
SKYLINE_FTFF_REDUCE_BLOCK_DIM = max(32, min(int(SKYLINE_FTFF_REDUCE_BLOCK_DIM), 256))
SKYLINE_FTFF_REDUCE_BLOCK_DIM = (SKYLINE_FTFF_REDUCE_BLOCK_DIM // 32) * 32
if SKYLINE_FTFF_REDUCE_BLOCK_DIM <= 0:
    SKYLINE_FTFF_REDUCE_BLOCK_DIM = 32
SKYLINE_FTFF_REDUCE_WAVE_STRIDE = SKYLINE_FTFF_REDUCE_BLOCK_DIM // 32  # Works for wave32 and wave64 (uses lane//32)

# GPU-native skyline -> ForceGreats candidate table (compact GPU-resident buffer).
# Avoids downloading full `(runs, pop, payload_cols)` skyline run payloads back to CPU just to
# seed ForceGreats candidate selection. skyline packs a small per-run candidate table on GPU.
# Layout per row (int32):
#   [score, slot_ids(9), result_row(7), base_stats7(7)]
# Where base_stats7 is `[pp, cm, fm, p_val, s_val, ft_stat, ff_stat]` (same column order
# used by native FG solver GPU kernels via `genome_base_stats`).
SKYLINE_FG_CANDIDATES_PER_RUN = env_int("GPU_SKYLINE_FG_CANDIDATES_PER_RUN", 64)
SKYLINE_FG_CANDIDATES_PER_RUN = max(1, min(128, int(SKYLINE_FG_CANDIDATES_PER_RUN)))
SKYLINE_FG_CANDIDATE_COLS = 1 + MAX_SLOTS + 7 + 7

# GPU-side initial population generation (heuristic sampling)
SKYLINE_INIT_HEURISTIC_K = env_int("GPU_SKYLINE_INIT_HEURISTIC_K", 64)
SKYLINE_INIT_HEURISTIC_K = max(0, min(256, int(SKYLINE_INIT_HEURISTIC_K)))

# ============================================================================
# GPU FIELDS (Device-resident data)
# ============================================================================

# Reference lookup tables (161 entries each, index 0-160)
ref_pp_field: ti.Field = None
ref_cm_field: ti.Field = None
ref_fm_field: ti.Field = None
ref_ft_field: ti.Field = None  # Fever Time multipliers
ref_ff_field: ti.Field = None  # Fever Fill Rate multipliers

# Exact-solver helper tables (small, ref-derived).
# Prefix argmax for PP-vs-OV choice inside the bounded exact inner solver.
# Shape: (flags16, pp_base_idx161, max_pp_gems<=MAX_TOTAL_BUDGET+1) -> best_pp_gems.
exact_pp_best_gems_prefix: ti.Field = None  # (16, 161, MAX_TOTAL_BUDGET+1) i16

# Timeline grid with song slots (MAX_SONG_SLOTS, 161, 161)
# Slot 0 is default for single-song mode; slots 1..MAX_SONG_SLOTS-1 for batch mode
grid_count_body_fever: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161) i32
grid_count_body_normal: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161) i32
grid_head_len: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161) i32
grid_N_hn: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161) i32 - count of normal head notes
grid_N_hf: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161) i32 - count of fever head notes
grid_Sigma_hn: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161) i32 - sum(i+1) over normal head notes
grid_Sigma_hf: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161) i32 - sum(i+1) over fever head notes
grid_fever_masks: ti.Field = None  # (MAX_SONG_SLOTS, 161, 161, 100) i8 - head masks
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

# Song data for GPU timeline computation
song_timestamps: ti.Field = None  # (MAX_SONG_NOTES,) f32
# Precomputed fever end indices per note/FT (binary-search-free timeline simulation)
fever_end_idx_song: ti.Field = None  # (MAX_SONG_NOTES, GRID_SIZE) i32

# Chord-grouped chart data for analytical timing-envelope ceiling computation.
# These are derived from chart timestamps + note types using the same chord grouping and
# per-note window semantics as the shared timing envelope.
song_note_group_idx: ti.Field = None  # (MAX_SONG_NOTES,) i32: note_idx -> group_idx
song_group_starts: ti.Field = None  # (MAX_SONG_NOTES,) i32: group_idx -> first note_idx
song_group_base_t_ms: ti.Field = None  # (MAX_SONG_NOTES,) i32: group_idx -> chart time in integer ms
song_group_low_ms: ti.Field = None  # (MAX_SONG_NOTES,) i32: group_idx -> min feasible carry (ms)
song_group_high_ms: ti.Field = None  # (MAX_SONG_NOTES,) i32: group_idx -> max feasible carry (ms)

# Breakpoint detection kernel inputs/outputs (bound into kernels_breakpoints)
bp_pair_ft: ti.Field = None  # (MAX_BP_PAIRS,) i32
bp_pair_ff: ti.Field = None  # (MAX_BP_PAIRS,) i32
bp_result_mask: ti.Field = None  # (16, 64) i32

# Per-genome base stats: [pp, cm, fm, p, s, ft, ff]
genome_base_stats: ti.Field = None

# GPU-native skyline fields
# These fields support GPU-side skyline operators. They are wired into the skyline kernels
# via bind_fields() and used by skyline_operations.py API calls.
population_indices: ti.Field = None  # (MAX_GENOMES, MAX_SLOTS) item_id per (genome,slot)
population_next_indices: ti.Field = None  # (MAX_GENOMES, MAX_SLOTS) next generation buffer
# Initial populations staged on GPU for multi-start runs (uploaded once per segment, then copied run-by-run).
skyline_initial_populations: ti.Field = None  # (MAX_SKYLINE_RUNS, MAX_SKYLINE_RUN_GENOMES, MAX_SLOTS) item_id per (run,genome,slot)
skyline_init_heuristic_topk: ti.Field = None  # (MAX_SLOTS, SKYLINE_INIT_HEURISTIC_K) item_id per (slot,k)
item_stats: ti.Field = None  # (MAX_ITEMS, ITEM_STAT_DIM) dense item stats table
base_fixed_stats: ti.Field = None  # (ITEM_STAT_DIM,) fixed base stats (added to all genomes)
skyline_scores: ti.Field = None  # (MAX_GENOMES,) int32 fitness scores (from evaluation)
skyline_rng_state: ti.Field = None  # (MAX_GENOMES,) uint32 RNG state per genome/thread
skyline_parent_a: ti.Field = None  # (MAX_GENOMES,) int32 selected parent index A
skyline_parent_b: ti.Field = None  # (MAX_GENOMES,) int32 selected parent index B
SKYLINE_EXACT_EVAL_HASH_KEY_COLS = MAX_SLOTS  # encoded gear/minis genome IDs
SKYLINE_EXACT_EVAL_HASH_SIZE = 16384  # Open-addressing table for exact duplicate-genome detection.
skyline_exact_eval_hash_used: ti.Field = None  # (HASH_SIZE,) i32 occupancy (0=empty, else rep_idx+1)
skyline_exact_eval_hash_keys: ti.Field = None  # (HASH_SIZE, KEY_COLS) i32 exact genome key (trailing cols reserved)
skyline_exact_eval_hash_sort_keys: ti.Field = None  # (MAX_GENOMES,) i32 hash keys for parallel sort grouping
skyline_exact_eval_hash_sort_indices: ti.Field = None  # (MAX_GENOMES,) i32 genome indices permuted with sort keys
skyline_exact_eval_rep_idx: ti.Field = None  # (MAX_GENOMES,) i32 representative genome index per row
skyline_exact_eval_unique_count: ti.Field = None  # (1,) i32 number of unique genome rows

# GPU-side global best tracking (avoids per-generation CPU downloads)
skyline_global_best_score: ti.Field = None  # (1,) i32 - best score across all generations
skyline_global_best_genome: ti.Field = None  # (MAX_SLOTS,) i32 - item IDs of best genome
skyline_global_best_results: ti.Field = None  # (7,) i32 - [score, ft, ff, pp, cm, fm, ov] for best genome
skyline_global_best_scan_key: ti.Field = None  # (1,) u64 - reduction key ((score+1)<<32)|inv_genome_idx
skyline_global_best_packed: ti.Field = None  # (17,) i32 - packed [score, genome_ids(9), results(7)] for single download
# Packed skyline download payload (reduce CPU<->GPU transfers): row 0 = global best, rows 1..n = per-genome snapshot.
skyline_run_payload_packed: ti.Field = None  # (MAX_GENOMES+1, 17) i32 - [score, slot_ids(9), result(7)]
# Download staging buffer for `skyline_run_payload_packed` (reduce padded Vulkan `to_numpy()` transfers).
skyline_run_payload_download_staging_256: ti.Field = None  # (<=257, 17) i32
# Multi-start skyline snapshot buffer (stores packed payload per run to avoid per-run downloads).
DEFAULT_MAX_SKYLINE_RUNS = 128  # Stores up to this many skyline runs before a flush/download.
DEFAULT_MAX_SKYLINE_RUN_GENOMES = 1024  # Must be >= SKYLINE_POPULATION_SIZE.
MAX_SKYLINE_RUNS = DEFAULT_MAX_SKYLINE_RUNS
MAX_SKYLINE_RUN_GENOMES = DEFAULT_MAX_SKYLINE_RUN_GENOMES
skyline_runs_payload_packed: ti.Field = None  # (MAX_SKYLINE_RUNS, MAX_SKYLINE_RUN_GENOMES+1, 17) i32
# Download staging buffers (smaller than `skyline_runs_payload_packed` to reduce padded Vulkan `to_numpy()` transfers).
SKYLINE_RUNS_PAYLOAD_DOWNLOAD_STAGING_MAX_GENOMES = 256  # Small staging buffer for compact run payload downloads.
skyline_runs_payload_download_staging_16: ti.Field = None  # (<=16, <=max_genomes+1, 17) i32
skyline_runs_payload_download_staging_64: ti.Field = None  # (<=64, <=max_genomes+1, 17) i32
skyline_runs_payload_download_staging_128: ti.Field = None  # (<=128, <=max_genomes+1, 17) i32

# Compact skyline -> FG candidate table (GPU-resident), plus a single-slot download staging field.
skyline_fg_candidates_packed: ti.Field = (
    None  # (MAX_SONG_SLOTS, MAX_SKYLINE_RUNS, SKYLINE_FG_CANDIDATES_PER_RUN+1, SKYLINE_FG_CANDIDATE_COLS) i32
)
skyline_fg_candidates_download_staging: ti.Field = (
    None  # (MAX_SKYLINE_RUNS, SKYLINE_FG_CANDIDATES_PER_RUN+1, SKYLINE_FG_CANDIDATE_COLS) i32
)

# GPU-side skyline->FG candidate selection outputs (avoid downloading full candidate tables).
# Selected payload row layout (int32), used for bounded CPU downloads:
# - Header row 0: [selected_count, best_score, best_ids(9), best_results(7), best_run_idx, ...]
# - Rows 1..N:    [run_idx, row_idx, score, slot_ids(9), result_row(7), base_stats7(7)]
SKYLINE_FG_SELECTED_PAYLOAD_COLS = 2 + (1 + MAX_SLOTS + 7 + 7)  # (run,row) + packed candidate row (24)
SKYLINE_FG_SELECTED_MAX = 5000  # Must cover clamp in `read_fg_candidate_limit` (<=5000).
SKYLINE_FG_SELECTED_HASH_SIZE = 65536  # Open-addressing table for dedupe (power of two).
SKYLINE_FG_SELECTED_STUBS_MAX = 20000  # Upper bound on unique stubs we support in GPU selection.

skyline_fg_select_hash_used: ti.Field = None  # (HASH_SIZE,) i32 occupancy
skyline_fg_select_hash_keys: ti.Field = None  # (HASH_SIZE, 9) i32
skyline_fg_select_stub_count: ti.Field = None  # (1,) i32
skyline_fg_select_stub_run: ti.Field = None  # (STUBS_MAX,) i32
skyline_fg_select_stub_row: ti.Field = None  # (STUBS_MAX,) i32
skyline_fg_select_stub_score: ti.Field = None  # (STUBS_MAX,) i32
skyline_fg_select_stub_fg_proxy: ti.Field = None  # (STUBS_MAX,) i64
skyline_fg_select_stub_center_ft: ti.Field = None  # (STUBS_MAX,) i32
skyline_fg_select_stub_center_ff: ti.Field = None  # (STUBS_MAX,) i32
skyline_fg_select_stub_ids: ti.Field = None  # (STUBS_MAX, 9) i32
skyline_fg_select_selected_mask: ti.Field = None  # (STUBS_MAX,) i32
skyline_fg_selected_count: ti.Field = None  # (1,) i32
skyline_fg_selected_coords: ti.Field = None  # (SKYLINE_FG_SELECTED_MAX, 2) i32
skyline_fg_selected_payload_staging_256: ti.Field = None  # (257, SKYLINE_FG_SELECTED_PAYLOAD_COLS) i32
skyline_fg_selected_payload_staging_1024: ti.Field = None  # (1025, SKYLINE_FG_SELECTED_PAYLOAD_COLS) i32
skyline_fg_selected_payload_staging_5000: ti.Field = None  # (5001, SKYLINE_FG_SELECTED_PAYLOAD_COLS) i32

# GPU-side island elitism (avoids per-generation score downloads)
MAX_ISLANDS = 16  # Maximum number of islands
island_boundaries: ti.Field = None  # (MAX_ISLANDS+1,) i32 - island start indices + end sentinel
island_elite_indices: ti.Field = None  # (MAX_GENOMES,) i32 - output: elite genome indices
island_elite_count: ti.Field = None  # (1,) i32 - output: total elites found

# Slot pools for GPU mutation - contiguous ID ranges per slot
# Allows O(1) mutation: new_id = slot_start[s] + (rand % slot_count[s])
slot_start: ti.Field = None  # (MAX_SLOTS,) int32 - first valid item_id for slot
slot_count: ti.Field = None  # (MAX_SLOTS,) int32 - number of items in slot pool

# Per-genome outputs (for FT/FF iteration kernels)
genome_result_stats: ti.Field = None  # Vector field [score, ft, ff, pp, cm, fm, ov]
# Download staging for FTFF `genome_result_stats` (bounded Vulkan `to_numpy()` transfers).
# Larger workloads can use the 1024 staging buffer; the 256 buffer keeps smaller downloads light.
genome_result_stats_download_staging_256: ti.Field = None  # (256,) vec7 i32
genome_result_stats_download_staging_1024: ti.Field = None  # (1024,) vec7 i32
chunk_best_key: ti.Field = None  # (MAX_GENOMES,) u64 packed key for safe per-chunk reduction
ftff_combo_ft: ti.Field = None  # (MAX_FTFF_COMBOS,) i32 FT gems per combo
ftff_combo_ff: ti.Field = None  # (MAX_FTFF_COMBOS,) i32 FF gems per combo

# Metal-specific 32-bit fields (used instead of u64 atomics on macOS)
chunk_best_score: ti.Field = None  # (MAX_GENOMES,) i32 best score per genome (Metal)
chunk_best_idx: ti.Field = None  # (MAX_GENOMES,) i32 winning combo index (Metal)

# Cached evaluation results per genome (eliminates redundant exact-bound calls)
chunk_best_results: ti.Field = None  # (MAX_GENOMES, 4) i32 - [pp, cm, fm, ov] from winning combo

# ============================================================================
# ALLOCATION STATE
# ============================================================================

_fields_allocated = False
_grid_fields_allocated = False


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
    global MAX_SKYLINE_RUNS, MAX_SKYLINE_RUN_GENOMES

    global ref_pp_field, ref_cm_field, ref_fm_field, ref_ft_field, ref_ff_field
    global exact_pp_best_gems_prefix
    global grid_count_body_fever, grid_count_body_normal, grid_head_len
    global grid_N_hn, grid_N_hf, grid_Sigma_hn, grid_Sigma_hf
    global grid_fever_masks, grid_fever_masks_bits
    global grid_frontier_count, grid_frontier_offset
    global grid_frontier_body_fever_pool, grid_frontier_body_normal_pool, grid_frontier_masks_bits_pool
    global grid_sig0, grid_sig1
    global grid_gap, grid_fever_activations
    global song_timestamps, fever_end_idx_song
    global song_note_group_idx, song_group_starts, song_group_base_t_ms, song_group_low_ms, song_group_high_ms
    global bp_pair_ft, bp_pair_ff, bp_result_mask
    global genome_base_stats
    global population_indices, population_next_indices, skyline_initial_populations, skyline_init_heuristic_topk
    global item_stats, base_fixed_stats
    global skyline_scores, skyline_rng_state, skyline_parent_a, skyline_parent_b
    global skyline_exact_eval_hash_used, skyline_exact_eval_hash_keys
    global skyline_exact_eval_hash_sort_keys, skyline_exact_eval_hash_sort_indices
    global skyline_exact_eval_rep_idx, skyline_exact_eval_unique_count
    global slot_start, slot_count
    global genome_result_stats
    global genome_result_stats_download_staging_256, genome_result_stats_download_staging_1024
    global chunk_best_key, chunk_best_score, chunk_best_idx, chunk_best_results
    global ftff_combo_ft, ftff_combo_ff
    global skyline_global_best_score, skyline_global_best_genome, skyline_global_best_results, skyline_global_best_scan_key
    global skyline_global_best_packed
    global skyline_runs_payload_packed
    global skyline_run_payload_packed
    global skyline_run_payload_download_staging_256
    global \
        skyline_runs_payload_download_staging_16, \
        skyline_runs_payload_download_staging_64, \
        skyline_runs_payload_download_staging_128
    global skyline_fg_candidates_packed, skyline_fg_candidates_download_staging
    global skyline_fg_select_hash_used, skyline_fg_select_hash_keys
    global skyline_fg_select_stub_count, skyline_fg_select_stub_run, skyline_fg_select_stub_row, skyline_fg_select_stub_score
    global skyline_fg_select_stub_fg_proxy, skyline_fg_select_stub_center_ft, skyline_fg_select_stub_center_ff, skyline_fg_select_stub_ids
    global skyline_fg_select_selected_mask, skyline_fg_selected_count, skyline_fg_selected_coords
    global skyline_fg_selected_payload_staging_256, skyline_fg_selected_payload_staging_1024, skyline_fg_selected_payload_staging_5000
    global island_boundaries, island_elite_indices, island_elite_count

    # Main refs
    ref_pp_field = None
    ref_cm_field = None
    ref_fm_field = None
    ref_ft_field = None
    ref_ff_field = None
    exact_pp_best_gems_prefix = None

    # Grid fields
    grid_count_body_fever = None
    grid_count_body_normal = None
    grid_head_len = None
    grid_N_hn = None
    grid_N_hf = None
    grid_Sigma_hn = None
    grid_Sigma_hf = None
    grid_fever_masks = None
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

    # Song timeline
    song_timestamps = None
    fever_end_idx_song = None
    song_note_group_idx = None
    song_group_starts = None
    song_group_base_t_ms = None
    song_group_low_ms = None
    song_group_high_ms = None

    # Breakpoint detection
    bp_pair_ft = None
    bp_pair_ff = None
    bp_result_mask = None

    # Genome base
    genome_base_stats = None

    # skyline fields
    population_indices = None
    population_next_indices = None
    skyline_initial_populations = None
    item_stats = None
    base_fixed_stats = None
    skyline_scores = None
    skyline_rng_state = None
    skyline_parent_a = None
    skyline_parent_b = None
    skyline_exact_eval_hash_used = None
    skyline_exact_eval_hash_keys = None
    skyline_exact_eval_hash_sort_keys = None
    skyline_exact_eval_hash_sort_indices = None
    skyline_exact_eval_rep_idx = None
    skyline_exact_eval_unique_count = None
    slot_start = None
    slot_count = None
    island_boundaries = None
    island_elite_indices = None
    island_elite_count = None
    skyline_global_best_score = None
    skyline_global_best_genome = None
    skyline_global_best_results = None
    skyline_global_best_scan_key = None
    skyline_global_best_packed = None
    skyline_runs_payload_packed = None
    skyline_run_payload_packed = None
    skyline_run_payload_download_staging_256 = None
    skyline_runs_payload_download_staging_16 = None
    skyline_runs_payload_download_staging_64 = None
    skyline_runs_payload_download_staging_128 = None
    skyline_fg_candidates_packed = None
    skyline_fg_candidates_download_staging = None
    skyline_fg_select_hash_used = None
    skyline_fg_select_hash_keys = None
    skyline_fg_select_stub_count = None
    skyline_fg_select_stub_run = None
    skyline_fg_select_stub_row = None
    skyline_fg_select_stub_score = None
    skyline_fg_select_stub_fg_proxy = None
    skyline_fg_select_stub_center_ft = None
    skyline_fg_select_stub_center_ff = None
    skyline_fg_select_stub_ids = None
    skyline_fg_select_selected_mask = None
    skyline_fg_selected_count = None
    skyline_fg_selected_coords = None
    skyline_fg_selected_payload_staging_256 = None
    skyline_fg_selected_payload_staging_1024 = None
    skyline_fg_selected_payload_staging_5000 = None
    genome_result_stats = None
    genome_result_stats_download_staging_256 = None
    genome_result_stats_download_staging_1024 = None
    chunk_best_key = None
    chunk_best_score = None
    chunk_best_idx = None
    chunk_best_results = None
    ftff_combo_ft = None
    ftff_combo_ff = None

    # Restore configurable skyline buffer shapes so future sessions/modules do not inherit
    # the previous caller's reduced multi-run sizing after a hard reset.
    MAX_SKYLINE_RUNS = int(DEFAULT_MAX_SKYLINE_RUNS)
    MAX_SKYLINE_RUN_GENOMES = int(DEFAULT_MAX_SKYLINE_RUN_GENOMES)

    _fields_allocated = False
    _grid_fields_allocated = False
    _last_uploaded_grid_id = None


# ============================================================================
# FIELD ALLOCATION
# ============================================================================


def _clamp_skyline_runs(n: int) -> int:
    if n < 1:
        return 1
    # Prevent accidental huge allocations.
    if n > 8192:
        return 8192
    return n


def _clamp_SKYLINE_genomes(n: int) -> int:
    # Must be >= SKYLINE_POPULATION_SIZE for GPU-native GA.
    if n < 250:
        return 250
    if n > MAX_GENOMES:
        return MAX_GENOMES
    return n


def configure_skyline_run_buffers(*, max_runs: int | None = None, max_genomes: int | None = None) -> None:
    """
    Configure GPU-native skyline buffer sizes before fields are allocated.

    This reduces large padded CPUâ†”GPU transfers in skyline multi-run mode by shrinking
    `skyline_initial_populations` and `skyline_runs_payload_packed` to the smallest required
    shapes for the current session.

    Callers MUST invoke this before the first `ensure_fields_allocated()`/kernel run.
    """
    global MAX_SKYLINE_RUNS, MAX_SKYLINE_RUN_GENOMES

    if _fields_allocated:
        return

    if max_runs is not None:
        MAX_SKYLINE_RUNS = _clamp_skyline_runs(int(max_runs))
    if max_genomes is not None:
        MAX_SKYLINE_RUN_GENOMES = _clamp_SKYLINE_genomes(int(max_genomes))


def _maybe_configure_skyline_run_buffers_from_env() -> None:
    """
    Best-effort skyline buffer sizing before the first field allocation.

    This is primarily to avoid large padded Vulkan `to_numpy()` transfers for
    GPU-native skyline multi-run payloads when Taichi fields are allocated early
    (e.g., by the GPU executor) before the skyline code can call `configure_skyline_run_buffers()`.
    """
    if _fields_allocated:
        return

    raw_runs = str(env_get("SKYLINE_GPU_MAX_RUNS", "") or "").strip()
    raw_genomes = str(env_get("SKYLINE_GPU_MAX_GENOMES", "") or "").strip()
    if not raw_runs and not raw_genomes:
        return

    max_runs = None
    max_genomes = None
    if raw_runs:
        try:
            max_runs = int(raw_runs)
        except Exception as e:
            logger.debug(f"fields:_maybe_configure_skyline_run_buffers_from_env: {e}")
            max_runs = None
    if raw_genomes:
        try:
            max_genomes = int(raw_genomes)
        except Exception as e:
            logger.debug(f"fields:_maybe_configure_skyline_run_buffers_from_env: {e}")
            max_genomes = None

    if max_runs is None and max_genomes is None:
        return
    configure_skyline_run_buffers(max_runs=max_runs, max_genomes=max_genomes)


def allocate_fields():
    """
    Allocate GPU fields. Must be called after ti.init().

    This allocates the baseline Taichi fields used by the solvers and GPU-native GA.
    """
    global ref_pp_field, ref_cm_field, ref_fm_field, ref_ft_field, ref_ff_field
    global exact_pp_best_gems_prefix
    global bp_pair_ft, bp_pair_ff, bp_result_mask
    global genome_base_stats
    global \
        population_indices, \
        population_next_indices, \
        skyline_initial_populations, \
        skyline_init_heuristic_topk, \
        item_stats, \
        base_fixed_stats
    global skyline_scores, skyline_rng_state, skyline_parent_a, skyline_parent_b
    global skyline_exact_eval_hash_used, skyline_exact_eval_hash_keys
    global skyline_exact_eval_hash_sort_keys, skyline_exact_eval_hash_sort_indices
    global skyline_exact_eval_rep_idx, skyline_exact_eval_unique_count
    global slot_start, slot_count
    global genome_result_stats
    global genome_result_stats_download_staging_256, genome_result_stats_download_staging_1024
    global chunk_best_key, chunk_best_score, chunk_best_idx, chunk_best_results
    global ftff_combo_ft, ftff_combo_ff
    global skyline_global_best_score, skyline_global_best_genome, skyline_global_best_results, skyline_global_best_scan_key
    global skyline_global_best_packed
    global skyline_runs_payload_packed
    global skyline_run_payload_packed
    global skyline_run_payload_download_staging_256
    global \
        skyline_runs_payload_download_staging_16, \
        skyline_runs_payload_download_staging_64, \
        skyline_runs_payload_download_staging_128
    global skyline_fg_candidates_packed, skyline_fg_candidates_download_staging
    global skyline_fg_select_hash_used, skyline_fg_select_hash_keys
    global skyline_fg_select_stub_count, skyline_fg_select_stub_run, skyline_fg_select_stub_row, skyline_fg_select_stub_score
    global skyline_fg_select_stub_fg_proxy, skyline_fg_select_stub_center_ft, skyline_fg_select_stub_center_ff, skyline_fg_select_stub_ids
    global skyline_fg_select_selected_mask, skyline_fg_selected_count, skyline_fg_selected_coords
    global skyline_fg_selected_payload_staging_256, skyline_fg_selected_payload_staging_1024, skyline_fg_selected_payload_staging_5000
    global island_boundaries, island_elite_indices, island_elite_count
    global _fields_allocated

    if _fields_allocated:
        return

    # Reference tables (f32 for performance)
    ref_pp_field = ti.field(dtype=ti.f32, shape=161)
    ref_cm_field = ti.field(dtype=ti.f32, shape=161)
    ref_fm_field = ti.field(dtype=ti.f32, shape=161)
    ref_ft_field = ti.field(dtype=ti.f32, shape=161)
    ref_ff_field = ti.field(dtype=ti.f32, shape=161)
    exact_pp_best_gems_prefix = ti.field(dtype=ti.i16, shape=(16, GRID_SIZE, MAX_TOTAL_BUDGET + 1))

    # Breakpoint detection kernel inputs/outputs (small, always-on)
    bp_pair_ft = ti.field(dtype=ti.i32, shape=MAX_BP_PAIRS)
    bp_pair_ff = ti.field(dtype=ti.i32, shape=MAX_BP_PAIRS)
    bp_result_mask = ti.field(dtype=ti.i32, shape=(16, 64))

    # Per-genome base stats
    # [pp, cm, fm, p_val, s_val, ft, ff]
    genome_base_stats = ti.Vector.field(n=7, dtype=ti.i16, shape=MAX_GENOMES)

    # GPU-native skyline / stat aggregation (Phase 3/4)
    population_indices = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, MAX_SLOTS))
    population_next_indices = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, MAX_SLOTS))
    skyline_initial_populations = ti.field(dtype=ti.i32, shape=(MAX_SKYLINE_RUNS, MAX_SKYLINE_RUN_GENOMES, MAX_SLOTS))
    if SKYLINE_INIT_HEURISTIC_K > 0:
        skyline_init_heuristic_topk = ti.field(dtype=ti.i32, shape=(MAX_SLOTS, SKYLINE_INIT_HEURISTIC_K))
    else:
        skyline_init_heuristic_topk = ti.field(dtype=ti.i32, shape=(MAX_SLOTS, 1))
    item_stats = ti.field(dtype=ti.i32, shape=(MAX_ITEMS, ITEM_STAT_DIM))
    base_fixed_stats = ti.field(dtype=ti.i32, shape=ITEM_STAT_DIM)
    skyline_scores = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    skyline_rng_state = ti.field(dtype=ti.u32, shape=MAX_GENOMES)
    skyline_parent_a = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    skyline_parent_b = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    skyline_exact_eval_hash_used = ti.field(dtype=ti.i32, shape=int(SKYLINE_EXACT_EVAL_HASH_SIZE))
    skyline_exact_eval_hash_keys = ti.field(
        dtype=ti.i32,
        shape=(int(SKYLINE_EXACT_EVAL_HASH_SIZE), int(SKYLINE_EXACT_EVAL_HASH_KEY_COLS)),
    )
    skyline_exact_eval_hash_sort_keys = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    skyline_exact_eval_hash_sort_indices = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    skyline_exact_eval_rep_idx = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    skyline_exact_eval_unique_count = ti.field(dtype=ti.i32, shape=1)

    # Slot pools for GPU mutation
    slot_start = ti.field(dtype=ti.i32, shape=MAX_SLOTS)
    slot_count = ti.field(dtype=ti.i32, shape=MAX_SLOTS)

    # Per-genome results (for FT/FF iteration kernel)
    # [score, ft, ff, pp, cm, fm, ov]
    genome_result_stats = ti.Vector.field(n=7, dtype=ti.i32, shape=MAX_GENOMES)
    # Bounded download staging buffers (reduce padded Vulkan `to_numpy()` transfers).
    genome_result_stats_download_staging_256 = ti.Vector.field(n=7, dtype=ti.i32, shape=256)
    genome_result_stats_download_staging_1024 = ti.Vector.field(n=7, dtype=ti.i32, shape=1024)
    # Per-genome reduction key: ((score + 1) << 32) | combo_idx
    # NOTE: u64 atomics are not supported on Metal, so we use separate 32-bit fields on macOS.
    if not IS_METAL:
        chunk_best_key = ti.field(dtype=ti.u64, shape=MAX_GENOMES)
    else:
        chunk_best_score = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
        chunk_best_idx = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    # FT/FF combo tables for GPU-parallel evaluation (indexed by combo_id)
    ftff_combo_ft = ti.field(dtype=ti.i32, shape=MAX_FTFF_COMBOS)
    ftff_combo_ff = ti.field(dtype=ti.i32, shape=MAX_FTFF_COMBOS)
    # Cached evaluation results per genome [pp, cm, fm, ov] - avoids redundant scoring
    chunk_best_results = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, 4))

    # GPU-side global best tracking (avoids per-generation CPU downloads)
    skyline_global_best_score = ti.field(dtype=ti.i32, shape=1)
    skyline_global_best_genome = ti.field(dtype=ti.i32, shape=MAX_SLOTS)
    skyline_global_best_results = ti.field(dtype=ti.i32, shape=7)  # [score, ft, ff, pp, cm, fm, ov]
    skyline_global_best_scan_key = ti.field(dtype=ti.u64, shape=1)
    skyline_global_best_packed = ti.field(dtype=ti.i32, shape=17)  # [score, genome_ids(9), results(7)]
    _payload_cols = 1 + MAX_SLOTS + 7
    skyline_run_payload_packed = ti.field(dtype=ti.i32, shape=(MAX_GENOMES + 1, _payload_cols))
    _run_staging_genomes = min(int(MAX_GENOMES), int(SKYLINE_RUNS_PAYLOAD_DOWNLOAD_STAGING_MAX_GENOMES))
    skyline_run_payload_download_staging_256 = ti.field(dtype=ti.i32, shape=(_run_staging_genomes + 1, _payload_cols))
    skyline_runs_payload_packed = ti.field(dtype=ti.i32, shape=(MAX_SKYLINE_RUNS, MAX_SKYLINE_RUN_GENOMES + 1, _payload_cols))
    # NOTE: these staging buffers are intentionally smaller than skyline_runs_payload_packed so we can
    # download only the populated slice for typical skyline workloads.
    _staging_genomes = min(int(MAX_SKYLINE_RUN_GENOMES), int(SKYLINE_RUNS_PAYLOAD_DOWNLOAD_STAGING_MAX_GENOMES))
    skyline_runs_payload_download_staging_16 = ti.field(
        dtype=ti.i32,
        shape=(min(int(MAX_SKYLINE_RUNS), 16), _staging_genomes + 1, _payload_cols),
    )
    skyline_runs_payload_download_staging_64 = ti.field(
        dtype=ti.i32,
        shape=(min(int(MAX_SKYLINE_RUNS), 64), _staging_genomes + 1, _payload_cols),
    )
    skyline_runs_payload_download_staging_128 = ti.field(
        dtype=ti.i32,
        shape=(min(int(MAX_SKYLINE_RUNS), 128), _staging_genomes + 1, _payload_cols),
    )

    # Compact skyline -> FG candidate table (one per song slot) + single-slot download staging.
    skyline_fg_candidates_packed = ti.field(
        dtype=ti.i32,
        shape=(MAX_SONG_SLOTS, MAX_SKYLINE_RUNS, int(SKYLINE_FG_CANDIDATES_PER_RUN) + 1, int(SKYLINE_FG_CANDIDATE_COLS)),
    )
    skyline_fg_candidates_download_staging = ti.field(
        dtype=ti.i32,
        shape=(MAX_SKYLINE_RUNS, int(SKYLINE_FG_CANDIDATES_PER_RUN) + 1, int(SKYLINE_FG_CANDIDATE_COLS)),
    )

    # GPU-side skyline->FG candidate selection buffers (bounded CPU downloads).
    skyline_fg_select_hash_used = ti.field(dtype=ti.i32, shape=int(SKYLINE_FG_SELECTED_HASH_SIZE))
    skyline_fg_select_hash_keys = ti.field(dtype=ti.i32, shape=(int(SKYLINE_FG_SELECTED_HASH_SIZE), 9))
    skyline_fg_select_stub_count = ti.field(dtype=ti.i32, shape=1)
    skyline_fg_select_stub_run = ti.field(dtype=ti.i32, shape=int(SKYLINE_FG_SELECTED_STUBS_MAX))
    skyline_fg_select_stub_row = ti.field(dtype=ti.i32, shape=int(SKYLINE_FG_SELECTED_STUBS_MAX))
    skyline_fg_select_stub_score = ti.field(dtype=ti.i32, shape=int(SKYLINE_FG_SELECTED_STUBS_MAX))
    skyline_fg_select_stub_fg_proxy = ti.field(dtype=ti.i64, shape=int(SKYLINE_FG_SELECTED_STUBS_MAX))
    skyline_fg_select_stub_center_ft = ti.field(dtype=ti.i32, shape=int(SKYLINE_FG_SELECTED_STUBS_MAX))
    skyline_fg_select_stub_center_ff = ti.field(dtype=ti.i32, shape=int(SKYLINE_FG_SELECTED_STUBS_MAX))
    skyline_fg_select_stub_ids = ti.field(dtype=ti.i32, shape=(int(SKYLINE_FG_SELECTED_STUBS_MAX), 9))
    skyline_fg_select_selected_mask = ti.field(dtype=ti.i32, shape=int(SKYLINE_FG_SELECTED_STUBS_MAX))
    skyline_fg_selected_count = ti.field(dtype=ti.i32, shape=1)
    skyline_fg_selected_coords = ti.field(dtype=ti.i32, shape=(int(SKYLINE_FG_SELECTED_MAX), 2))

    skyline_fg_selected_payload_staging_256 = ti.field(
        dtype=ti.i32,
        shape=(257, int(SKYLINE_FG_SELECTED_PAYLOAD_COLS)),
    )
    skyline_fg_selected_payload_staging_1024 = ti.field(
        dtype=ti.i32,
        shape=(1025, int(SKYLINE_FG_SELECTED_PAYLOAD_COLS)),
    )
    skyline_fg_selected_payload_staging_5000 = ti.field(
        dtype=ti.i32,
        shape=(int(SKYLINE_FG_SELECTED_MAX) + 1, int(SKYLINE_FG_SELECTED_PAYLOAD_COLS)),
    )

    # GPU-side island elitism (avoids per-generation score downloads)
    # Islands are contiguous ranges in the population
    MAX_ISLANDS = 16  # Maximum number of islands
    island_boundaries = ti.field(dtype=ti.i32, shape=MAX_ISLANDS + 1)  # [start0, start1, ..., end_last]
    island_elite_indices = ti.field(dtype=ti.i32, shape=MAX_GENOMES)  # Output: elite genome indices
    island_elite_count = ti.field(dtype=ti.i32, shape=1)  # Output: total elites found

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
    global grid_fever_masks, grid_fever_masks_bits
    global grid_frontier_count, grid_frontier_offset
    global grid_frontier_body_fever_pool, grid_frontier_body_normal_pool, grid_frontier_masks_bits_pool
    global grid_sig0, grid_sig1
    global grid_gap, grid_fever_activations
    global song_timestamps, fever_end_idx_song
    global song_note_group_idx, song_group_starts, song_group_base_t_ms, song_group_low_ms, song_group_high_ms
    global _grid_fields_allocated

    if _grid_fields_allocated:
        return

    # Timeline grid with song slots (MAX_SONG_SLOTS Ã— 161Ã—161)
    # Slot 0 is default for single-song mode; slots 0-7 for batch mode
    grid_count_body_fever = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_count_body_normal = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_head_len = ti.field(dtype=ti.i8, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_N_hn = ti.field(dtype=ti.i16, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_N_hf = ti.field(dtype=ti.i16, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_Sigma_hn = ti.field(dtype=ti.i16, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_Sigma_hf = ti.field(dtype=ti.i16, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    if WRITE_UNPACKED_GRID_MASKS_DEFAULT:
        # Unpacked masks are historical/debug-only; keep them minimal to avoid VRAM blowups.
        # We only allocate slot 0 (shape[0]=1). Multi-slot code must use bitpacked masks.
        grid_fever_masks = ti.field(dtype=ti.i8, shape=(1, GRID_SIZE, GRID_SIZE, MAX_HEAD_NOTES))
    else:
        grid_fever_masks = None
    grid_fever_masks_bits = ti.field(dtype=ti.u32, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE, 4))
    grid_frontier_count = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_frontier_offset = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_frontier_body_fever_pool = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, MAX_TIMELINE_FRONTIER_SURFACES))
    grid_frontier_body_normal_pool = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, MAX_TIMELINE_FRONTIER_SURFACES))
    grid_frontier_masks_bits_pool = ti.field(dtype=ti.u32, shape=(MAX_SONG_SLOTS, MAX_TIMELINE_FRONTIER_SURFACES, 4))
    grid_sig0 = ti.field(dtype=ti.u64, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    grid_sig1 = ti.field(dtype=ti.u64, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    # Gap to song end: total_notes - last_fever_end_idx (positive = opportunity, negative = overshoot)
    grid_gap = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))
    # Fever activations count per (FT, FF) - sections beyond this have no fever
    grid_fever_activations = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE))

    # Song timestamps for GPU timeline computation (may already be allocated by
    # ensure_fields_allocated for non-grid kernels).
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


def ensure_grid_unpacked_masks_allocated() -> None:
    """
    Allocate unpacked timeline masks on demand.

    Production kernels use `grid_fever_masks_bits`. Unpacked masks are only for
    optional debug/inspection paths and are disabled by default to save VRAM.
    """
    global grid_fever_masks

    ensure_grid_fields_allocated()
    if grid_fever_masks is not None:
        return

    # Unpacked masks are historical/debug-only; keep them minimal to avoid VRAM blowups.
    # We only allocate slot 0 (shape[0]=1). Multi-slot code must use bitpacked masks.
    grid_fever_masks = ti.field(dtype=ti.i8, shape=(1, GRID_SIZE, GRID_SIZE, MAX_HEAD_NOTES))
    from . import kernels

    bind_fields(kernels)
    logger.debug(
        "[Taichi] Allocated unpacked timeline masks: 1 x %s x %s x %s",
        GRID_SIZE,
        GRID_SIZE,
        MAX_HEAD_NOTES,
    )


# ============================================================================
# FIELD BINDING (for kernels module)
# ============================================================================


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
    # Try to bind to kernels_helpers submodule if it exists (package structure)
    # Otherwise bind to the module directly (monolithic kernels.py)
    try:
        from . import kernels

        target = kernels.kernels_helpers
    except (ImportError, AttributeError):
        target = kernels_module

    # Reference tables
    target.ref_pp_field = ref_pp_field
    target.ref_cm_field = ref_cm_field
    target.ref_fm_field = ref_fm_field
    target.ref_ft_field = ref_ft_field
    target.ref_ff_field = ref_ff_field
    target.exact_pp_best_gems_prefix = exact_pp_best_gems_prefix

    # Grid fields
    target.grid_count_body_fever = grid_count_body_fever
    target.grid_count_body_normal = grid_count_body_normal
    target.grid_head_len = grid_head_len
    target.grid_N_hn = grid_N_hn
    target.grid_N_hf = grid_N_hf
    target.grid_Sigma_hn = grid_Sigma_hn
    target.grid_Sigma_hf = grid_Sigma_hf
    target.grid_fever_masks = grid_fever_masks
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

    # Song data for timeline
    target.song_timestamps = song_timestamps
    target.fever_end_idx_song = fever_end_idx_song
    target.song_note_group_idx = song_note_group_idx
    target.song_group_starts = song_group_starts
    target.song_group_base_t_ms = song_group_base_t_ms
    target.song_group_low_ms = song_group_low_ms
    target.song_group_high_ms = song_group_high_ms

    # Genome base stats
    target.genome_base_stats = genome_base_stats

    # GPU-native skyline / stat aggregation
    target.population_indices = population_indices
    target.population_next_indices = population_next_indices
    target.skyline_initial_populations = skyline_initial_populations
    target.skyline_init_heuristic_topk = skyline_init_heuristic_topk
    target.item_stats = item_stats
    target.base_fixed_stats = base_fixed_stats
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
    target.slot_start = slot_start
    target.slot_count = slot_count

    # Genome results
    target.genome_result_stats = genome_result_stats
    if not IS_METAL:
        target.chunk_best_key = chunk_best_key
    else:
        target.chunk_best_score = chunk_best_score
        target.chunk_best_idx = chunk_best_idx
    target.ftff_combo_ft = ftff_combo_ft
    target.ftff_combo_ff = ftff_combo_ff
    target.chunk_best_results = chunk_best_results

    # GPU-side global best tracking
    target.skyline_global_best_score = skyline_global_best_score
    target.skyline_global_best_genome = skyline_global_best_genome
    target.skyline_global_best_results = skyline_global_best_results
    target.skyline_global_best_scan_key = skyline_global_best_scan_key
    target.skyline_global_best_packed = skyline_global_best_packed
    target.skyline_runs_payload_packed = skyline_runs_payload_packed
    target.skyline_run_payload_packed = skyline_run_payload_packed
    target.skyline_fg_candidates_packed = skyline_fg_candidates_packed
    target.skyline_fg_candidates_download_staging = skyline_fg_candidates_download_staging
    target.skyline_fg_select_hash_used = skyline_fg_select_hash_used
    target.skyline_fg_select_hash_keys = skyline_fg_select_hash_keys
    target.skyline_fg_select_stub_count = skyline_fg_select_stub_count
    target.skyline_fg_select_stub_run = skyline_fg_select_stub_run
    target.skyline_fg_select_stub_row = skyline_fg_select_stub_row
    target.skyline_fg_select_stub_score = skyline_fg_select_stub_score
    target.skyline_fg_select_stub_fg_proxy = skyline_fg_select_stub_fg_proxy
    target.skyline_fg_select_stub_center_ft = skyline_fg_select_stub_center_ft
    target.skyline_fg_select_stub_center_ff = skyline_fg_select_stub_center_ff
    target.skyline_fg_select_stub_ids = skyline_fg_select_stub_ids
    target.skyline_fg_select_selected_mask = skyline_fg_select_selected_mask
    target.skyline_fg_selected_count = skyline_fg_selected_count
    target.skyline_fg_selected_coords = skyline_fg_selected_coords
    target.skyline_fg_selected_payload_staging_256 = skyline_fg_selected_payload_staging_256
    target.skyline_fg_selected_payload_staging_1024 = skyline_fg_selected_payload_staging_1024
    target.skyline_fg_selected_payload_staging_5000 = skyline_fg_selected_payload_staging_5000

    # GPU-side island elitism
    target.island_boundaries = island_boundaries
    target.island_elite_indices = island_elite_indices
    target.island_elite_count = island_elite_count

    # Bind breakpoint-detection fields to kernels_breakpoints (separate module)
    try:
        from .kernels import kernels_breakpoints

        kernels_breakpoints.bp_pair_ft = bp_pair_ft
        kernels_breakpoints.bp_pair_ff = bp_pair_ff
        kernels_breakpoints.bp_result_mask = bp_result_mask
    except Exception as e:
        # Keep binding best-effort; breakpoint kernels aren't always imported.
        logger.debug(f"fields:bind_fields: {e}")


def ensure_fields_allocated():
    """
    Ensure Taichi is initialized and fields are allocated.

    This is the main entry point for ensuring the GPU is ready.
    Initializes Taichi if needed, allocates fields, and binds them to kernels.
    """
    if not is_initialized():
        init_taichi()

    if not _fields_allocated:
        _maybe_configure_skyline_run_buffers_from_env()
        allocate_fields()

        # Some kernels/tests rely on `song_timestamps` without needing the full
        # timeline grid fields. Allocate it eagerly once Taichi is initialized.
        global song_timestamps
        if song_timestamps is None:
            song_timestamps = ti.field(dtype=ti.f32, shape=MAX_SONG_NOTES)

        # Import kernels here to avoid circular import at module load time
        from . import kernels

        bind_fields(kernels)

        # Bind Metal-specific NON-GRID fields if on macOS
        # Grid fields are bound later in ensure_grid_fields_allocated()
        if IS_METAL:
            from . import kernels_metal

            kernels_metal.chunk_best_score = chunk_best_score
            kernels_metal.chunk_best_idx = chunk_best_idx
            # Bind shared non-grid fields needed by Metal kernels
            kernels_metal.genome_result_stats = genome_result_stats
            kernels_metal.genome_base_stats = genome_base_stats
            kernels_metal.skyline_scores = skyline_scores
            kernels_metal.population_indices = population_indices
            kernels_metal.skyline_exact_eval_rep_idx = skyline_exact_eval_rep_idx
            kernels_metal.ftff_combo_ft = ftff_combo_ft
            kernels_metal.ftff_combo_ff = ftff_combo_ff
            kernels_metal.skyline_global_best_score = skyline_global_best_score
            kernels_metal.skyline_global_best_genome = skyline_global_best_genome
            kernels_metal.skyline_global_best_results = skyline_global_best_results


def ensure_grid_fields_allocated():
    """
    Ensure grid fields are allocated for timeline lookups.

    Call this before uploading or using the timeline grid.
    """
    ensure_fields_allocated()  # Main fields must be allocated first

    if not _grid_fields_allocated:
        allocate_grid_fields()
        # Re-bind to include grid fields
        from . import kernels

        bind_fields(kernels)

        # Bind Metal-specific GRID fields if on macOS
        if IS_METAL:
            from . import kernels_metal

            kernels_metal.grid_count_body_fever = grid_count_body_fever
            kernels_metal.grid_count_body_normal = grid_count_body_normal
            kernels_metal.grid_head_len = grid_head_len
            kernels_metal.grid_N_hn = grid_N_hn
            kernels_metal.grid_N_hf = grid_N_hf
            kernels_metal.grid_Sigma_hn = grid_Sigma_hn
            kernels_metal.grid_Sigma_hf = grid_Sigma_hf
            kernels_metal.grid_fever_masks_bits = grid_fever_masks_bits
            kernels_metal.grid_frontier_count = grid_frontier_count
            kernels_metal.grid_frontier_offset = grid_frontier_offset
            kernels_metal.grid_frontier_body_fever_pool = grid_frontier_body_fever_pool
            kernels_metal.grid_frontier_body_normal_pool = grid_frontier_body_normal_pool
            kernels_metal.grid_frontier_masks_bits_pool = grid_frontier_masks_bits_pool
            kernels_metal.grid_sig0 = grid_sig0
            kernels_metal.grid_sig1 = grid_sig1
            kernels_metal.grid_gap = grid_gap
            kernels_metal.grid_fever_activations = grid_fever_activations

            # Now that ALL fields are bound, apply Metal kernel patches
            from .kernel_loader import apply_metal_patches

            apply_metal_patches()
