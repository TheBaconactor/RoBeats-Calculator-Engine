"""
ForceGreats GPU Fields - declarations and allocation.

These fields are *separate* from the main gem solver fields in `taichi_gem.fields`.
We share the Taichi runtime (`taichi_gem.runtime`) and reuse the main gem solver
reference tables + base genome stats fields for scoring.
"""

from __future__ import annotations

import taichi as ti

from ..runtime import init_taichi_vulkan, is_initialized
from ..fields import MAX_GENOMES, MAX_SONG_SLOTS

# ============================================================================
# CONSTANTS
# ============================================================================

FG_MAX_SECTIONS = 16
FG_MAX_STAT = 160  # Maximum FT/FF stat index
FG_MAX_CONFIGS = 1048576
FG_MAX_FTFF = 1024
FG_MAX_SONG_NOTES = 200000  # safety cap for timestamps uploaded to GPU
FG_DOWNLOAD_TOPK_MAX = 256  # Max selected rows for reduced global_best download (keep + candidates)
# Batch download staging for executor-side payload bundles (avoid per-payload to_numpy()).
FG_DOWNLOAD_BATCH_MAX = 128
FG_PACKED_COLS = 11 + FG_MAX_SECTIONS
FG_SELECTED_PACKED_COLS = 12 + FG_MAX_SECTIONS

# Flattened parallelization: MAX_GENOMES * FG_MAX_FTFF threads
# Each thread processes ONE config at a time (chunked)
FG_MAX_FLAT_WORK_ITEMS = MAX_GENOMES * FG_MAX_FTFF  # 4096 * 256 = 1M work items max


# ============================================================================
# GPU FIELDS (device-resident)
# ============================================================================

# Song timestamps (GPU-resident; used by FG finder kernel)
song_timestamps: ti.Field | None = None  # (FG_MAX_SONG_NOTES,) f32
song_timestamps_great_candidate: ti.Field | None = None  # (FG_MAX_SONG_NOTES,) f32

# Precomputed fever-end indices for fast timeline simulation.
# Shape: (note_idx, ft_idx) -> end_note_idx (binary search result in song_timestamps).
fg_fever_end_idx_song: ti.Field | None = None  # (FG_MAX_SONG_NOTES, FG_MAX_STAT+1) i32
fg_fever_end_idx_great_candidate: ti.Field | None = None  # (FG_MAX_SONG_NOTES, FG_MAX_STAT+1) i32

# FG finder inputs (GPU-resident)
# Stores fill-penalty targets (fp) per section (not raw forced counts).
fg_forced_counts: ti.Field | None = None  # (FG_MAX_CONFIGS, FG_MAX_SECTIONS) i32
fg_pair_caps: ti.Field | None = None  # (FG_MAX_STAT+1, FG_MAX_STAT+1, FG_MAX_SECTIONS) i32
fg_ft_list: ti.Field | None = None  # (FG_MAX_FTFF,) i32
fg_ff_list: ti.Field | None = None  # (FG_MAX_FTFF,) i32
# Packed-task support: per-(ftff) config window (global cfg table slice).
fg_cfg_start_list: ti.Field | None = None  # (FG_MAX_FTFF,) i32
fg_cfg_len_list: ti.Field | None = None  # (FG_MAX_FTFF,) i32
# Total cfg window length (per-ftff). Used to build banded cfg ranges on GPU.
fg_cfg_total_len_list: ti.Field | None = None  # (FG_MAX_FTFF,) i32
# Scalar reduction scratch: max(cfg_total_len_list[:n_ftff]).
fg_cfg_total_len_max: ti.Field | None = None  # () i32
# Packed-task support: implicit config decode metadata.
# - cfg_base_list: base_cfg_offset for the full config window (global cfg index space)
# - cfg_mode_list: 0=read fg_forced_counts table, 1=implicit mixed-radix decode (counts_max_fp)
# - cfg_max_fp: per-(ftff, section) max FP value (for mixed-radix decode); only used when mode=1
fg_cfg_base_list: ti.Field | None = None  # (FG_MAX_FTFF,) i32
fg_cfg_mode_list: ti.Field | None = None  # (FG_MAX_FTFF,) i32
fg_cfg_max_fp: ti.Field | None = None  # (FG_MAX_FTFF, FG_MAX_SECTIONS) i32

# FG finder outputs (per genome)
fg_best_final_score: ti.Field | None = None  # (MAX_GENOMES,) i32
fg_best_base_score: ti.Field | None = None  # (MAX_GENOMES,) i32
fg_best_cfg_idx: ti.Field | None = None  # (MAX_GENOMES,) i32
fg_best_ft: ti.Field | None = None  # (MAX_GENOMES,) i32
fg_best_ff: ti.Field | None = None  # (MAX_GENOMES,) i32
fg_best_g_pp: ti.Field | None = None  # (MAX_GENOMES,) i32
fg_best_g_cm: ti.Field | None = None  # (MAX_GENOMES,) i32
fg_best_g_fm: ti.Field | None = None  # (MAX_GENOMES,) i32
fg_best_g_ov: ti.Field | None = None  # (MAX_GENOMES,) i32
fg_best_score_penalty: ti.Field | None = None  # (MAX_GENOMES,) i32
fg_best_fill_penalty: ti.Field | None = None  # (MAX_GENOMES,) i32
fg_best_cfg_counts: ti.Field | None = None  # (MAX_GENOMES, FG_MAX_SECTIONS) i32

# Packed results for efficient CPU download.
# Format: (MAX_GENOMES, 11 + FG_MAX_SECTIONS) with columns:
# [final_score, base_score, cfg_idx, ft, ff, g_pp, g_cm, g_fm, g_ov, score_penalty, fill_penalty, cfg_counts...]
fg_best_packed: ti.Field | None = None  # (MAX_GENOMES, FG_PACKED_COLS) i32

# NEW: Packed 64-bit field for atomic (score, cfg_idx) updates - fixes race condition
# Format: (score << 32) | (cfg_idx & 0xFFFFFFFF) - score in upper 32 bits for correct atomic_max ordering
fg_stage1_packed: ti.Field | None = None  # (MAX_GENOMES, FG_MAX_FTFF) i64

# FG finder intermediate outputs (per genome × ftff) - for two-stage reduction
fg_stage1_final_score: ti.Field | None = None  # (MAX_GENOMES, FG_MAX_FTFF) i32
fg_stage1_base_score: ti.Field | None = None  # (MAX_GENOMES, FG_MAX_FTFF) i32
fg_stage1_cfg_idx: ti.Field | None = None  # (MAX_GENOMES, FG_MAX_FTFF) i32
fg_stage1_g_pp: ti.Field | None = None  # (MAX_GENOMES, FG_MAX_FTFF) i32
fg_stage1_g_cm: ti.Field | None = None  # (MAX_GENOMES, FG_MAX_FTFF) i32
fg_stage1_g_fm: ti.Field | None = None  # (MAX_GENOMES, FG_MAX_FTFF) i32
fg_stage1_g_ov: ti.Field | None = None  # (MAX_GENOMES, FG_MAX_FTFF) i32
fg_stage1_score_penalty: ti.Field | None = None  # (MAX_GENOMES, FG_MAX_FTFF) i32
fg_stage1_fill_penalty: ti.Field | None = None  # (MAX_GENOMES, FG_MAX_FTFF) i32

# Flat work items for GPU-friendly parallelization
# Each item is (genome_id, ftff_id) - cfg is batched in chunks
fg_flat_work_genome: ti.Field | None = None  # (FG_MAX_FLAT_WORK_ITEMS,) i32
fg_flat_work_ftff: ti.Field | None = None  # (FG_MAX_FLAT_WORK_ITEMS,) i32

# Global best fields for GPU-resident accumulation (persist across group calls)
# These track the best results found across all GPU calls within a single FG batch
# NOTE: These buffers are indexed by `song_slot` so multiple in-flight FG sessions can safely interleave
# (global-best state must not mix across songs when multi-request pipelining is enabled).
fg_global_best_final_score: ti.Field | None = None  # (MAX_SONG_SLOTS, MAX_GENOMES) i32
fg_global_best_base_score: ti.Field | None = None  # (MAX_SONG_SLOTS, MAX_GENOMES) i32
fg_global_best_cfg_idx: ti.Field | None = None  # (MAX_SONG_SLOTS, MAX_GENOMES) i32
fg_global_best_ft: ti.Field | None = None  # (MAX_SONG_SLOTS, MAX_GENOMES) i32
fg_global_best_ff: ti.Field | None = None  # (MAX_SONG_SLOTS, MAX_GENOMES) i32
fg_global_best_g_pp: ti.Field | None = None  # (MAX_SONG_SLOTS, MAX_GENOMES) i32
fg_global_best_g_cm: ti.Field | None = None  # (MAX_SONG_SLOTS, MAX_GENOMES) i32
fg_global_best_g_fm: ti.Field | None = None  # (MAX_SONG_SLOTS, MAX_GENOMES) i32
fg_global_best_g_ov: ti.Field | None = None  # (MAX_SONG_SLOTS, MAX_GENOMES) i32
fg_global_best_score_penalty: ti.Field | None = None  # (MAX_SONG_SLOTS, MAX_GENOMES) i32
fg_global_best_fill_penalty: ti.Field | None = None  # (MAX_SONG_SLOTS, MAX_GENOMES) i32
fg_global_best_cfg_counts: ti.Field | None = None  # (MAX_SONG_SLOTS, MAX_GENOMES, FG_MAX_SECTIONS) i32
# Scratch staging buffer for download (packed for a single song_slot).
fg_global_best_packed: ti.Field | None = None  # (MAX_GENOMES, FG_PACKED_COLS) i32

# Optional: reduce host downloads by selecting/packing only a small subset of global_best rows.
fg_input_base_score: ti.Field | None = None  # (MAX_GENOMES,) i32 (base score per genome for eligibility filter)
fg_keep_mask: ti.Field | None = None  # (MAX_GENOMES,) i32 (1=force include this genome in selected list)
fg_selected_count: ti.Field | None = None  # () i32 (number of selected rows)
fg_selected_indices: ti.Field | None = None  # (FG_DOWNLOAD_TOPK_MAX,) i32 (genome indices into global_best arrays)
fg_selected_packed: ti.Field | None = None  # (FG_DOWNLOAD_TOPK_MAX, 12 + FG_MAX_SECTIONS) i32 (idx + packed row)
fg_selected_packed_batch: ti.Field | None = (
    None  # (FG_DOWNLOAD_BATCH_MAX, FG_DOWNLOAD_TOPK_MAX, 12 + FG_MAX_SECTIONS) i32
)

# Warm-start hints for FG gem allocation (local search optimization)
# Stores: [pp_gems, cm_gems, fm_gems, ov_gems] from previous best allocation
fg_genome_hint_allocation: ti.Field | None = None  # (MAX_GENOMES, 4) i32


# ============================================================================
# ALLOCATION STATE
# ============================================================================

_fields_allocated = False


def is_fields_allocated() -> bool:
    return _fields_allocated


def reset_fields_state() -> None:
    """Reset module-level allocation state after `ti.reset()`."""
    global _fields_allocated
    global song_timestamps, song_timestamps_great_candidate
    global fg_fever_end_idx_song, fg_fever_end_idx_great_candidate
    global \
        fg_forced_counts, \
        fg_pair_caps, \
        fg_ft_list, \
        fg_ff_list, \
        fg_cfg_start_list, \
        fg_cfg_len_list, \
        fg_cfg_total_len_list
    global fg_cfg_total_len_list
    global fg_cfg_base_list, fg_cfg_mode_list, fg_cfg_max_fp
    global fg_best_final_score, fg_best_base_score, fg_best_cfg_idx
    global fg_best_ft, fg_best_ff, fg_best_g_pp, fg_best_g_cm, fg_best_g_fm, fg_best_g_ov
    global fg_best_score_penalty, fg_best_fill_penalty, fg_best_cfg_counts, fg_best_packed
    global fg_stage1_packed
    global fg_stage1_final_score, fg_stage1_base_score, fg_stage1_cfg_idx
    global fg_stage1_g_pp, fg_stage1_g_cm, fg_stage1_g_fm, fg_stage1_g_ov
    global fg_stage1_score_penalty, fg_stage1_fill_penalty
    global fg_flat_work_genome, fg_flat_work_ftff

    song_timestamps = None
    song_timestamps_great_candidate = None
    fg_fever_end_idx_song = None
    fg_fever_end_idx_great_candidate = None
    fg_forced_counts = None
    fg_pair_caps = None
    fg_ft_list = None
    fg_ff_list = None
    fg_cfg_start_list = None
    fg_cfg_len_list = None
    fg_cfg_total_len_list = None
    fg_cfg_base_list = None
    fg_cfg_mode_list = None
    fg_cfg_max_fp = None

    fg_best_final_score = None
    fg_best_base_score = None
    fg_best_cfg_idx = None
    fg_best_ft = None
    fg_best_ff = None
    fg_best_g_pp = None
    fg_best_g_cm = None
    fg_best_g_fm = None
    fg_best_g_ov = None
    fg_best_score_penalty = None
    fg_best_fill_penalty = None
    fg_best_cfg_counts = None
    fg_best_packed = None

    fg_stage1_packed = None
    fg_stage1_final_score = None
    fg_stage1_base_score = None
    fg_stage1_cfg_idx = None
    fg_stage1_g_pp = None
    fg_stage1_g_cm = None
    fg_stage1_g_fm = None
    fg_stage1_g_ov = None
    fg_stage1_score_penalty = None
    fg_stage1_fill_penalty = None

    fg_flat_work_genome = None
    fg_flat_work_ftff = None

    # Global best fields
    global fg_global_best_final_score, fg_global_best_base_score, fg_global_best_cfg_idx
    global fg_global_best_ft, fg_global_best_ff
    global fg_global_best_g_pp, fg_global_best_g_cm, fg_global_best_g_fm, fg_global_best_g_ov
    global fg_global_best_score_penalty, fg_global_best_fill_penalty, fg_global_best_cfg_counts, fg_global_best_packed
    global \
        fg_input_base_score, \
        fg_keep_mask, \
        fg_selected_count, \
        fg_selected_indices, \
        fg_selected_packed, \
        fg_selected_packed_batch
    global fg_genome_hint_allocation
    fg_global_best_final_score = None
    fg_global_best_base_score = None
    fg_global_best_cfg_idx = None
    fg_global_best_ft = None
    fg_global_best_ff = None
    fg_global_best_g_pp = None
    fg_global_best_g_cm = None
    fg_global_best_g_fm = None
    fg_global_best_g_ov = None
    fg_global_best_score_penalty = None
    fg_global_best_fill_penalty = None
    fg_global_best_cfg_counts = None
    fg_global_best_packed = None

    fg_input_base_score = None
    fg_keep_mask = None
    fg_selected_count = None
    fg_selected_indices = None
    fg_selected_packed = None
    fg_selected_packed_batch = None
    fg_genome_hint_allocation = None

    _fields_allocated = False


def bind_fields(kernels_module) -> None:
    """
    Bind live field objects into the kernels module placeholders.

    We mirror the pattern used by `taichi_gem.fields.bind_fields` to avoid
    importing/initializing Taichi fields at module import time.
    """
    kernels_module.song_timestamps = song_timestamps
    kernels_module.song_timestamps_great_candidate = song_timestamps_great_candidate
    kernels_module.fg_fever_end_idx_song = fg_fever_end_idx_song
    kernels_module.fg_fever_end_idx_great_candidate = fg_fever_end_idx_great_candidate
    kernels_module.fg_forced_counts = fg_forced_counts
    kernels_module.fg_pair_caps = fg_pair_caps
    kernels_module.fg_ft_list = fg_ft_list
    kernels_module.fg_ff_list = fg_ff_list
    kernels_module.fg_cfg_start_list = fg_cfg_start_list
    kernels_module.fg_cfg_len_list = fg_cfg_len_list
    kernels_module.fg_cfg_total_len_list = fg_cfg_total_len_list
    kernels_module.fg_cfg_total_len_max = fg_cfg_total_len_max
    kernels_module.fg_cfg_base_list = fg_cfg_base_list
    kernels_module.fg_cfg_mode_list = fg_cfg_mode_list
    kernels_module.fg_cfg_max_fp = fg_cfg_max_fp

    kernels_module.fg_best_final_score = fg_best_final_score
    kernels_module.fg_best_base_score = fg_best_base_score
    kernels_module.fg_best_cfg_idx = fg_best_cfg_idx
    kernels_module.fg_best_ft = fg_best_ft
    kernels_module.fg_best_ff = fg_best_ff
    kernels_module.fg_best_g_pp = fg_best_g_pp
    kernels_module.fg_best_g_cm = fg_best_g_cm
    kernels_module.fg_best_g_fm = fg_best_g_fm
    kernels_module.fg_best_g_ov = fg_best_g_ov
    kernels_module.fg_best_score_penalty = fg_best_score_penalty
    kernels_module.fg_best_fill_penalty = fg_best_fill_penalty
    kernels_module.fg_best_cfg_counts = fg_best_cfg_counts
    kernels_module.fg_best_packed = fg_best_packed

    kernels_module.fg_stage1_final_score = fg_stage1_final_score
    kernels_module.fg_stage1_base_score = fg_stage1_base_score
    kernels_module.fg_stage1_cfg_idx = fg_stage1_cfg_idx
    kernels_module.fg_stage1_g_pp = fg_stage1_g_pp
    kernels_module.fg_stage1_g_cm = fg_stage1_g_cm
    kernels_module.fg_stage1_g_fm = fg_stage1_g_fm
    kernels_module.fg_stage1_g_ov = fg_stage1_g_ov
    kernels_module.fg_stage1_score_penalty = fg_stage1_score_penalty
    kernels_module.fg_stage1_fill_penalty = fg_stage1_fill_penalty
    kernels_module.fg_stage1_packed = fg_stage1_packed

    # Flat work items
    kernels_module.fg_flat_work_genome = fg_flat_work_genome
    kernels_module.fg_flat_work_ftff = fg_flat_work_ftff

    # Global best fields
    kernels_module.fg_global_best_final_score = fg_global_best_final_score
    kernels_module.fg_global_best_base_score = fg_global_best_base_score
    kernels_module.fg_global_best_cfg_idx = fg_global_best_cfg_idx
    kernels_module.fg_global_best_ft = fg_global_best_ft
    kernels_module.fg_global_best_ff = fg_global_best_ff
    kernels_module.fg_global_best_g_pp = fg_global_best_g_pp
    kernels_module.fg_global_best_g_cm = fg_global_best_g_cm
    kernels_module.fg_global_best_g_fm = fg_global_best_g_fm
    kernels_module.fg_global_best_g_ov = fg_global_best_g_ov
    kernels_module.fg_global_best_score_penalty = fg_global_best_score_penalty
    kernels_module.fg_global_best_fill_penalty = fg_global_best_fill_penalty
    kernels_module.fg_global_best_cfg_counts = fg_global_best_cfg_counts
    kernels_module.fg_global_best_packed = fg_global_best_packed

    kernels_module.fg_input_base_score = fg_input_base_score
    kernels_module.fg_keep_mask = fg_keep_mask
    kernels_module.fg_selected_count = fg_selected_count
    kernels_module.fg_selected_indices = fg_selected_indices
    kernels_module.fg_selected_packed = fg_selected_packed
    kernels_module.fg_selected_packed_batch = fg_selected_packed_batch
    kernels_module.fg_genome_hint_allocation = fg_genome_hint_allocation


def allocate_fields() -> None:
    """Allocate ForceGreats GPU fields. Must be called after ti.init()."""
    global song_timestamps, song_timestamps_great_candidate
    global fg_fever_end_idx_song, fg_fever_end_idx_great_candidate
    global \
        fg_forced_counts, \
        fg_pair_caps, \
        fg_ft_list, \
        fg_ff_list, \
        fg_cfg_start_list, \
        fg_cfg_len_list, \
        fg_cfg_total_len_list
    global fg_cfg_base_list, fg_cfg_mode_list, fg_cfg_max_fp
    global fg_cfg_total_len_max
    global fg_best_final_score, fg_best_base_score, fg_best_cfg_idx, fg_best_ft, fg_best_ff
    global fg_best_g_pp, fg_best_g_cm, fg_best_g_fm, fg_best_g_ov
    global fg_best_score_penalty, fg_best_fill_penalty, fg_best_cfg_counts, fg_best_packed
    global fg_stage1_final_score, fg_stage1_base_score, fg_stage1_cfg_idx
    global fg_stage1_g_pp, fg_stage1_g_cm, fg_stage1_g_fm, fg_stage1_g_ov
    global fg_stage1_score_penalty, fg_stage1_fill_penalty
    global fg_stage1_packed
    global fg_flat_work_genome, fg_flat_work_ftff
    global _fields_allocated

    if _fields_allocated:
        return

    song_timestamps = ti.field(dtype=ti.f32, shape=FG_MAX_SONG_NOTES)
    song_timestamps_great_candidate = ti.field(dtype=ti.f32, shape=FG_MAX_SONG_NOTES)
    fg_fever_end_idx_song = ti.field(dtype=ti.i32, shape=(FG_MAX_SONG_NOTES, FG_MAX_STAT + 1))
    fg_fever_end_idx_great_candidate = ti.field(dtype=ti.i32, shape=(FG_MAX_SONG_NOTES, FG_MAX_STAT + 1))

    fg_forced_counts = ti.field(dtype=ti.i32, shape=(FG_MAX_CONFIGS, FG_MAX_SECTIONS))
    fg_pair_caps = ti.field(dtype=ti.i32, shape=(FG_MAX_STAT + 1, FG_MAX_STAT + 1, FG_MAX_SECTIONS))
    fg_ft_list = ti.field(dtype=ti.i32, shape=FG_MAX_FTFF)
    fg_ff_list = ti.field(dtype=ti.i32, shape=FG_MAX_FTFF)
    fg_cfg_start_list = ti.field(dtype=ti.i32, shape=FG_MAX_FTFF)
    fg_cfg_len_list = ti.field(dtype=ti.i32, shape=FG_MAX_FTFF)
    fg_cfg_total_len_list = ti.field(dtype=ti.i32, shape=FG_MAX_FTFF)
    fg_cfg_total_len_max = ti.field(dtype=ti.i32, shape=())
    fg_cfg_base_list = ti.field(dtype=ti.i32, shape=FG_MAX_FTFF)
    fg_cfg_mode_list = ti.field(dtype=ti.i32, shape=FG_MAX_FTFF)
    fg_cfg_max_fp = ti.field(dtype=ti.i32, shape=(FG_MAX_FTFF, FG_MAX_SECTIONS))

    fg_best_final_score = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    fg_best_base_score = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    fg_best_cfg_idx = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    fg_best_ft = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    fg_best_ff = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    fg_best_g_pp = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    fg_best_g_cm = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    fg_best_g_fm = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    fg_best_g_ov = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    fg_best_score_penalty = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    fg_best_fill_penalty = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    fg_best_cfg_counts = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_MAX_SECTIONS))
    fg_best_packed = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_PACKED_COLS))

    fg_stage1_final_score = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_MAX_FTFF))
    fg_stage1_base_score = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_MAX_FTFF))
    fg_stage1_cfg_idx = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_MAX_FTFF))
    fg_stage1_g_pp = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_MAX_FTFF))
    fg_stage1_g_cm = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_MAX_FTFF))
    fg_stage1_g_fm = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_MAX_FTFF))
    fg_stage1_g_ov = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_MAX_FTFF))
    fg_stage1_score_penalty = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_MAX_FTFF))
    fg_stage1_fill_penalty = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_MAX_FTFF))

    # Packed 64-bit field for atomic (score, cfg_idx) updates
    fg_stage1_packed = ti.field(dtype=ti.i64, shape=(MAX_GENOMES, FG_MAX_FTFF))

    # Flat work item indices (GPU-friendly)
    fg_flat_work_genome = ti.field(dtype=ti.i32, shape=FG_MAX_FLAT_WORK_ITEMS)
    fg_flat_work_ftff = ti.field(dtype=ti.i32, shape=FG_MAX_FLAT_WORK_ITEMS)

    # Global best fields (persistent across group calls)
    global fg_global_best_final_score, fg_global_best_base_score, fg_global_best_cfg_idx
    global fg_global_best_ft, fg_global_best_ff
    global fg_global_best_g_pp, fg_global_best_g_cm, fg_global_best_g_fm, fg_global_best_g_ov
    global fg_global_best_score_penalty, fg_global_best_fill_penalty, fg_global_best_cfg_counts, fg_global_best_packed
    global \
        fg_input_base_score, \
        fg_keep_mask, \
        fg_selected_count, \
        fg_selected_indices, \
        fg_selected_packed, \
        fg_selected_packed_batch
    fg_global_best_final_score = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, MAX_GENOMES))
    fg_global_best_base_score = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, MAX_GENOMES))
    fg_global_best_cfg_idx = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, MAX_GENOMES))
    fg_global_best_ft = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, MAX_GENOMES))
    fg_global_best_ff = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, MAX_GENOMES))
    fg_global_best_g_pp = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, MAX_GENOMES))
    fg_global_best_g_cm = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, MAX_GENOMES))
    fg_global_best_g_fm = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, MAX_GENOMES))
    fg_global_best_g_ov = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, MAX_GENOMES))
    fg_global_best_score_penalty = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, MAX_GENOMES))
    fg_global_best_fill_penalty = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, MAX_GENOMES))
    fg_global_best_cfg_counts = ti.field(dtype=ti.i32, shape=(MAX_SONG_SLOTS, MAX_GENOMES, FG_MAX_SECTIONS))
    fg_global_best_packed = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_PACKED_COLS))

    fg_input_base_score = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    fg_keep_mask = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    fg_selected_count = ti.field(dtype=ti.i32, shape=())
    fg_selected_indices = ti.field(dtype=ti.i32, shape=FG_DOWNLOAD_TOPK_MAX)
    fg_selected_packed = ti.field(dtype=ti.i32, shape=(FG_DOWNLOAD_TOPK_MAX, FG_SELECTED_PACKED_COLS))
    fg_selected_packed_batch = ti.field(
        dtype=ti.i32,
        shape=(FG_DOWNLOAD_BATCH_MAX, FG_DOWNLOAD_TOPK_MAX, FG_SELECTED_PACKED_COLS),
    )

    # Warm-start hints for FG gem allocation
    global fg_genome_hint_allocation
    fg_genome_hint_allocation = ti.Vector.field(n=4, dtype=ti.i32, shape=MAX_GENOMES)

    _fields_allocated = True


def ensure_fields_allocated() -> None:
    """Ensure ForceGreats fields are allocated and bound to kernels."""
    # ForceGreatsFinder kernels reuse core scoring helpers in `taichi_gem.kernels_helpers`,
    # which depend on the main gem solver fields being allocated and bound.
    # In calculate-only runs (MetaFinder disabled), the app may reach FG init before
    # the main gem fields are initialized; ensure they exist first.
    from .. import fields as gem_fields

    gem_fields.ensure_fields_allocated()

    if not is_initialized():
        init_taichi_vulkan()

    if not _fields_allocated:
        allocate_fields()

    # Bind fields into kernel placeholders
    from . import kernels as _kernels

    bind_fields(_kernels)


# ============================================================================
# KERNEL WARMUP (JIT pre-compilation)
# ============================================================================

_kernels_warmed = False


def warmup_kernels() -> None:
    """
    Pre-compile FG kernels to eliminate first-call JIT overhead (~150ms).

    Call this once during initialization (after ensure_fields_allocated).
    The warmup runs minimal workloads just to trigger Taichi JIT compilation.
    """
    global _kernels_warmed

    if _kernels_warmed:
        return

    import taichi as ti
    from . import kernels as fg_kernels
    from ..fields import IS_METAL

    # Minimal warmup parameters
    n_genomes = 1
    n_ftff = 1
    n_work_items = 1
    n_cfg = 1
    cfg_offset = 0
    total_notes = 10
    long_notes = 0
    last_note_time = 10.0
    total_budget = 90
    gem_scale_fever = 3
    n_sections = 2

    # Warmup reset kernel
    fg_kernels.fg_reset_best_kernel(n_genomes)

    # Warmup stage1 init kernel
    fg_kernels.fg_stage1_init_kernel(n_genomes, n_ftff)
    # Vulkan runtime uses the minimal packed-only init; precompile it too.
    if not IS_METAL:
        fg_kernels.fg_stage1_init_packed_kernel(n_genomes, n_ftff)
        fg_kernels.fg_reduce_cfg_total_len_max_kernel(n_ftff)

    # Warmup precomputed fever-end tables (used by Stage 1 kernels)
    fg_kernels.fg_precompute_fever_end_idx_tables_kernel(total_notes, float(last_note_time))

    # Warmup Stage 1 (the heavy one).
    # Note: kernels read forced-count targets from `fg_forced_counts` (a GPU field). We don't need
    # to populate it here; warmup outputs are discarded and the field is allocated/zeroed by Taichi.
    if IS_METAL:
        fg_kernels.fg_stage1_kernel(
            n_genomes,
            total_notes,
            long_notes,
            last_note_time,
            total_budget,
            gem_scale_fever,
            n_cfg,
            n_sections,
            n_ftff,
            cfg_offset,
            0,  # cfg_read_offset
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,  # color flags
            0,  # song_slot
            0,  # pair_caps_from_timeline
        )
    else:
        # Warm both Stage-1 flat variants to avoid first-call JIT when section counts differ.
        fg_kernels.fg_stage1_flat_kernel_small3(
            n_work_items,
            n_cfg,
            cfg_offset,
            0,  # cfg_read_offset
            total_notes,
            long_notes,
            last_note_time,
            total_budget,
            gem_scale_fever,
            n_sections,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,  # color flags
            0,  # song_slot
            0,  # pair_caps_from_timeline
        )
        fg_kernels.fg_stage1_flat_kernel(
            n_work_items,
            n_cfg,
            cfg_offset,
            0,  # cfg_read_offset
            total_notes,
            long_notes,
            last_note_time,
            total_budget,
            gem_scale_fever,
            n_sections,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,  # color flags
            0,  # song_slot
            0,  # pair_caps_from_timeline
        )

    # Warmup Stage-2 recompute kernels (used by runtime to avoid Stage-1 aux races).
    fg_kernels.fg_stage2_recompute_kernel(
        n_genomes,
        n_ftff,
        total_notes,
        long_notes,
        float(last_note_time),
        total_budget,
        gem_scale_fever,
        n_sections,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,  # color flags
        0,  # song_slot
        0,  # pair_caps_from_timeline
    )

    # Warmup global best kernels (new for GPU-resident accumulation)
    fg_kernels.fg_reset_global_best_kernel(0, n_genomes)
    fg_kernels.fg_stage2_recompute_and_update_global_best_kernel(
        n_genomes,
        n_ftff,
        total_notes,
        long_notes,
        float(last_note_time),
        total_budget,
        gem_scale_fever,
        n_sections,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,  # color flags
        0,  # song_slot
        0,  # pair_caps_from_timeline
    )
    fg_kernels.fg_update_global_best_kernel(0, n_genomes)

    # Warmup packing kernels (avoid first-download JIT hiccup)
    fg_kernels.fg_pack_results_kernel(n_genomes)
    fg_kernels.fg_pack_global_best_kernel(0, n_genomes)
    fg_kernels.fg_select_global_best_topk_kernel(0, n_genomes, 1)
    fg_kernels.fg_pack_selected_global_best_kernel(0, 1)
    fg_kernels.fg_pack_selected_global_best_batch_kernel(0, 1, 0)

    # Sync to ensure JIT is complete
    ti.sync()

    _kernels_warmed = True


def ensure_ready_with_warmup() -> None:
    """
    Ensure FG fields are allocated AND kernels are pre-warmed.

    This is the preferred initialization entry point for FG processing
    to avoid first-call JIT latency.
    """
    # FG Stage 1 kernels can reference shared `taichi_gem.kernels_helpers` grid fields
    # (e.g., timeline-derived pair caps), so ensure the base gem fields are allocated/bound first.
    try:
        from .. import api as gem_api

        gem_api.ensure_ready()
    except Exception:
        pass
    ensure_fields_allocated()
    warmup_kernels()
