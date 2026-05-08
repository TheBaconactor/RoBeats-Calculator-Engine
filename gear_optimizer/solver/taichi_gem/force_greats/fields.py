"""
ForceGreats GPU Fields - declarations and allocation.

These fields are *separate* from the main gem solver fields in `taichi_gem.fields`.
We share the Taichi runtime (`taichi_gem.runtime`) and reuse the main gem solver
reference tables + base genome stats fields for scoring.
"""

from __future__ import annotations
import logging

import numpy as np
import taichi as ti

from ..runtime import init_taichi, is_initialized
from ..fields import IS_METAL, MAX_GENOMES, MAX_SONG_SLOTS

# ============================================================================
# CONSTANTS
# ============================================================================

from gear_optimizer.core.parsing import env_get

logger = logging.getLogger(__name__)
FG_MAX_SECTIONS = 16
FG_MAX_STAT = 160  # Maximum FT/FF stat index
FG_MAX_CONFIGS = 1048576
_FG_MAX_FTFF_DEFAULT = 1024
try:
    _fg_max_ftff_env = int(env_get("FG_MAX_FTFF", _FG_MAX_FTFF_DEFAULT) or _FG_MAX_FTFF_DEFAULT)
except Exception as e:
    logger.debug(f"fields: {e}")
    _fg_max_ftff_env = _FG_MAX_FTFF_DEFAULT
# Clamp to a conservative range to avoid pathological allocations on low-memory GPUs.
_fg_max_ftff_env = max(256, min(int(_fg_max_ftff_env), 4096))
FG_MAX_FTFF = int(_fg_max_ftff_env)
FG_MAX_SONG_NOTES = 200000  # safety cap for timestamps uploaded to GPU
FG_DOWNLOAD_TOPK_MAX = 256  # Max selected rows for reduced global_best download (keep + candidates)
FG_SIGNATURE_FRONTIER_MAX = MAX_GENOMES  # Max signatures per FG frontier-selection batch
_FG_EXACT_DP_MAX_NOTES_DEFAULT = 128
try:
    _fg_exact_dp_max_notes_env = int(env_get("FG_EXACT_DP_MAX_NOTES", _FG_EXACT_DP_MAX_NOTES_DEFAULT) or 0)
except Exception as e:
    logger.debug(f"fields: {e}")
    _fg_exact_dp_max_notes_env = _FG_EXACT_DP_MAX_NOTES_DEFAULT
# Keep this small by default: exact DP state scales ~O(n^2) in the timing-aware carry model.
_fg_exact_dp_max_notes_env = max(32, min(int(_fg_exact_dp_max_notes_env), 512))
FG_EXACT_DP_MAX_NOTES = int(_fg_exact_dp_max_notes_env)


def _next_pow2(x: int) -> int:
    v = 1
    while v < int(x):
        v <<= 1
    return int(v)


_FG_EXACT_DP_SPARSE_MAX_STATES_DEFAULT = 4096
try:
    _fg_exact_dp_sparse_states_env = int(
        env_get("FG_EXACT_DP_SPARSE_MAX_STATES", _FG_EXACT_DP_SPARSE_MAX_STATES_DEFAULT)
        or _FG_EXACT_DP_SPARSE_MAX_STATES_DEFAULT
    )
except Exception as e:
    logger.debug(f"fields:_next_pow2: {e}")
    _fg_exact_dp_sparse_states_env = _FG_EXACT_DP_SPARSE_MAX_STATES_DEFAULT
_fg_exact_dp_sparse_states_env = max(256, min(int(_fg_exact_dp_sparse_states_env), 65536))
FG_EXACT_DP_SPARSE_MAX_STATES = int(_fg_exact_dp_sparse_states_env)

try:
    _fg_exact_dp_sparse_hash_env = int(env_get("FG_EXACT_DP_SPARSE_HASH_SIZE", "0") or "0")
except Exception as e:
    logger.debug(f"fields:_next_pow2: {e}")
    _fg_exact_dp_sparse_hash_env = 0
if int(_fg_exact_dp_sparse_hash_env) <= 0:
    _fg_exact_dp_sparse_hash_env = _next_pow2(int(FG_EXACT_DP_SPARSE_MAX_STATES) * 4)
else:
    _fg_exact_dp_sparse_hash_env = _next_pow2(int(_fg_exact_dp_sparse_hash_env))
_fg_exact_dp_sparse_hash_env = max(1024, min(int(_fg_exact_dp_sparse_hash_env), 262144))
FG_EXACT_DP_SPARSE_HASH_SIZE = int(_fg_exact_dp_sparse_hash_env)

try:
    _fg_exact_dp_batch_rows_env = int(env_get("FG_EXACT_DP_BATCH_MAX_ROWS", "128") or "128")
except Exception as e:
    logger.debug(f"fields:_next_pow2: {e}")
    _fg_exact_dp_batch_rows_env = 128
FG_EXACT_DP_BATCH_MAX_ROWS = max(1, min(int(_fg_exact_dp_batch_rows_env), 256))
FG_EXACT_DP_PREFIX_HEAD_LEN = 101

FG_EXACT_DP_FULL_PREFIX_LEN = FG_MAX_SONG_NOTES + 1
try:
    _fg_signature_frontier_batch_env = int(env_get("FG_SIGNATURE_FRONTIER_BATCH_MAX", "64") or "64")
except Exception as e:
    logger.debug(f"fields:_next_pow2: {e}")
    _fg_signature_frontier_batch_env = 64
FG_SIGNATURE_FRONTIER_BATCH_MAX = max(1, min(int(_fg_signature_frontier_batch_env), 128))
try:
    _fg_download_batch_env = int(env_get("FG_DOWNLOAD_BATCH_MAX", "128") or "128")
except Exception as e:
    logger.debug(f"fields:_next_pow2: {e}")
    _fg_download_batch_env = 128
FG_DOWNLOAD_BATCH_MAX = max(1, min(int(_fg_download_batch_env), 256))
FG_PACKED_COLS = 11 + FG_MAX_SECTIONS
FG_SELECTED_PACKED_COLS = 12 + FG_MAX_SECTIONS
_FG_SECTION_FORCED_CAPS_DEFAULT = (50, 30, 15, 10, 8, 6, 5, 4, 4, 4, 4, 4, 4, 4, 4, 4)

# Flattened parallelization: MAX_GENOMES * FG_MAX_FTFF threads
# Each thread processes ONE config at a time (chunked)
FG_MAX_FLAT_WORK_ITEMS = MAX_GENOMES * FG_MAX_FTFF  # MAX_GENOMES * FG_MAX_FTFF
FG_STAGE1_WAVE_SLOTS_MAX = 8  # max waves for FG_STAGE1_BLOCK_DIM<=256 (used by wave-staging kernels)
try:
    _fg_cfg_dedupe_work_items_env = int(env_get("FG_CFG_DEDUPE_WORK_ITEMS", "512") or "512")
except Exception as e:
    logger.debug(f"fields:_next_pow2: {e}")
    _fg_cfg_dedupe_work_items_env = 512
FG_CFG_DEDUPE_WORK_ITEMS = max(128, min(int(_fg_cfg_dedupe_work_items_env), 2048))
try:
    _fg_cfg_dedupe_max_reps_env = int(env_get("FG_CFG_DEDUPE_MAX_REPS", "512") or "512")
except Exception as e:
    logger.debug(f"fields:_next_pow2: {e}")
    _fg_cfg_dedupe_max_reps_env = 512
FG_CFG_DEDUPE_MAX_REPS = max(512, min(int(_fg_cfg_dedupe_max_reps_env), 8192))
FG_CFG_DEDUPE_SIG_WORDS = 11


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
fg_section_forced_caps: ti.Field | None = None  # (FG_MAX_SECTIONS,) i32
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

# GPU-side config signature dedupe scratch. Shape is intentionally bounded and
# processed in work-item chunks, so production keeps implicit configs on-device.
fg_cfg_dedupe_hash: ti.Field | None = None  # (FG_CFG_DEDUPE_WORK_ITEMS, FG_CFG_DEDUPE_MAX_REPS) u64
fg_cfg_dedupe_sig: ti.Field | None = None  # vector[FG_CFG_DEDUPE_SIG_WORDS] per representative
fg_cfg_dedupe_rep_cfg_idx: ti.Field | None = None  # original global cfg_idx per representative
fg_cfg_dedupe_rep_count: ti.Field | None = None  # representatives per local work item
fg_cfg_dedupe_active: ti.Field | None = None  # 1=use representatives, 0=fallback to full configs

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
# Vulkan block-per-owner staging (no shared memory): per-work-item best packed key per wave slot.
fg_stage1_wave_best: ti.Field | None = None  # (FG_MAX_FLAT_WORK_ITEMS, FG_STAGE1_WAVE_SLOTS_MAX) u64

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
# NOTE: These buffers are indexed by `song_slot` so multiple in-flight FG sessions can safely overlap
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
# Download staging buffers (reduce padded Vulkan `to_numpy()` transfers).
fg_selected_packed_batch_download_staging_1: ti.Field | None = None
fg_selected_packed_batch_download_staging_8: ti.Field | None = None
fg_selected_packed_batch_download_staging_32: ti.Field | None = None
fg_selected_packed_batch_download_staging_128: ti.Field | None = None
# Download staging buffers for `fg_best_packed` (reduce padded Vulkan `to_numpy()` transfers).
fg_best_packed_download_staging_256: ti.Field | None = None
fg_best_packed_download_staging_1024: ti.Field | None = None
# Download staging buffers for `fg_global_best_packed` (reduce padded Vulkan `to_numpy()` transfers).
fg_global_best_packed_download_staging_256: ti.Field | None = None
fg_global_best_packed_download_staging_1024: ti.Field | None = None

# GPU-side FG frontier selection metadata and outputs.
fg_frontier_base_score: ti.Field | None = None  # (FG_SIGNATURE_FRONTIER_MAX,) i32
fg_frontier_proxy_score: ti.Field | None = None  # (FG_SIGNATURE_FRONTIER_MAX,) i32
fg_frontier_priority: ti.Field | None = None  # (FG_SIGNATURE_FRONTIER_MAX,) i32
fg_frontier_force_keep: ti.Field | None = None  # (FG_SIGNATURE_FRONTIER_MAX,) i32
fg_frontier_center_bucket_ft: ti.Field | None = None  # (FG_SIGNATURE_FRONTIER_MAX,) i32
fg_frontier_center_bucket_ff: ti.Field | None = None  # (FG_SIGNATURE_FRONTIER_MAX,) i32
fg_frontier_timing_bucket: ti.Field | None = None  # (FG_SIGNATURE_FRONTIER_MAX,) i32
fg_frontier_selected_count: ti.Field | None = None  # () i32
fg_frontier_selected_indices: ti.Field | None = None  # (FG_SIGNATURE_FRONTIER_MAX,) i32
fg_frontier_base_order: ti.Field | None = None  # (FG_SIGNATURE_FRONTIER_MAX,) i32
fg_frontier_fg_order: ti.Field | None = None  # (FG_SIGNATURE_FRONTIER_MAX,) i32
fg_frontier_selected_count_batch: ti.Field | None = None  # (FG_SIGNATURE_FRONTIER_BATCH_MAX,) i32
fg_frontier_selected_indices_batch: ti.Field | None = (
    None  # (FG_SIGNATURE_FRONTIER_BATCH_MAX, FG_SIGNATURE_FRONTIER_MAX) i32
)

# Warm-start hints for FG gem allocation (local search optimization)
# Stores: [pp_gems, cm_gems, fm_gems, ov_gems] from previous best allocation
fg_genome_hint_allocation: ti.Field | None = None  # (MAX_GENOMES, 4) i32

# Exact FG DP (reference / research-only): small scratch buffers.
fg_exact_dp_w_prefix: ti.Field | None = None  # (FG_EXACT_DP_MAX_NOTES+1,) i64
fg_exact_dp_c_prefix: ti.Field | None = None  # (FG_EXACT_DP_MAX_NOTES+1,) i64
fg_exact_dp_dp: ti.Field | None = None  # (FG_EXACT_DP_MAX_NOTES+1, FG_EXACT_DP_MAX_NOTES+1) i64
fg_exact_dp_best_delta: ti.Field | None = None  # () i64
fg_exact_dp_counts: ti.Field | None = None  # (FG_MAX_SECTIONS,) i32

# Exact FG DP (sparse, full charts): scratch buffers.
fg_exact_dp_full_w_prefix: ti.Field | None = None  # (FG_EXACT_DP_FULL_PREFIX_LEN,) i64
fg_exact_dp_full_c_prefix: ti.Field | None = None  # (FG_EXACT_DP_FULL_PREFIX_LEN,) i64
fg_exact_dp_sparse_hash_keys: ti.Field | None = None  # (FG_EXACT_DP_SPARSE_HASH_SIZE,) i64
fg_exact_dp_sparse_hash_vals: ti.Field | None = None  # (FG_EXACT_DP_SPARSE_HASH_SIZE,) i32
fg_exact_dp_sparse_state_i: ti.Field | None = None  # (FG_EXACT_DP_SPARSE_MAX_STATES,) i32
fg_exact_dp_sparse_state_first: ti.Field | None = None  # (FG_EXACT_DP_SPARSE_MAX_STATES,) i32
fg_exact_dp_sparse_state_carry: ti.Field | None = None  # (FG_EXACT_DP_SPARSE_MAX_STATES,) i32
fg_exact_dp_sparse_dp: ti.Field | None = None  # (FG_EXACT_DP_SPARSE_MAX_STATES,) i64
fg_exact_dp_sparse_policy_p: ti.Field | None = None  # (FG_EXACT_DP_SPARSE_MAX_STATES,) i32
fg_exact_dp_sparse_policy_k: ti.Field | None = None  # (FG_EXACT_DP_SPARSE_MAX_STATES,) i32
fg_exact_dp_sparse_order: ti.Field | None = None  # (FG_EXACT_DP_SPARSE_MAX_STATES,) i32
fg_exact_dp_sparse_state_count: ti.Field | None = None  # () i32
fg_exact_dp_sparse_best_delta: ti.Field | None = None  # () i64
fg_exact_dp_sparse_counts: ti.Field | None = None  # (FG_MAX_SECTIONS,) i32
fg_exact_dp_sparse_states: ti.Field | None = None  # () i32
fg_exact_dp_sparse_transitions: ti.Field | None = None  # () i32
fg_exact_dp_sparse_overflow: ti.Field | None = None  # () i32

# Batched sparse exact-DP buffers. These keep independent fixed-stat rows in one
# owner turn so exact-DP refinement uses GPU lane parallelism instead of one
# serialized tiny kernel per retained FG variant.
fg_exact_dp_batch_raw_fill: ti.Field | None = None  # (FG_EXACT_DP_BATCH_MAX_ROWS,) f32
fg_exact_dp_batch_non_fever_base: ti.Field | None = None  # (FG_EXACT_DP_BATCH_MAX_ROWS,) i32
fg_exact_dp_batch_ft_idx: ti.Field | None = None  # (FG_EXACT_DP_BATCH_MAX_ROWS,) i32
fg_exact_dp_batch_w_head_prefix: ti.Field | None = None  # (rows, 101) i64
fg_exact_dp_batch_c_head_prefix: ti.Field | None = None  # (rows, 101) i64
fg_exact_dp_batch_w_body: ti.Field | None = None  # (rows,) i64
fg_exact_dp_batch_c_body: ti.Field | None = None  # (rows,) i64
fg_exact_dp_batch_hash_keys: ti.Field | None = None  # (rows, hash) i64
fg_exact_dp_batch_hash_vals: ti.Field | None = None  # (rows, hash) i32
fg_exact_dp_batch_state_i: ti.Field | None = None  # (rows, states) i32
fg_exact_dp_batch_state_first: ti.Field | None = None  # (rows, states) i32
fg_exact_dp_batch_state_carry: ti.Field | None = None  # (rows, states) i32
fg_exact_dp_batch_dp: ti.Field | None = None  # (rows, states) i64
fg_exact_dp_batch_policy_p: ti.Field | None = None  # (rows, states) i32
fg_exact_dp_batch_policy_k: ti.Field | None = None  # (rows, states) i32
fg_exact_dp_batch_order: ti.Field | None = None  # (rows, states) i32
fg_exact_dp_batch_state_count: ti.Field | None = None  # (rows,) i32
fg_exact_dp_batch_best_delta: ti.Field | None = None  # (rows,) i64
fg_exact_dp_batch_counts: ti.Field | None = None  # (rows, FG_MAX_SECTIONS) i32
fg_exact_dp_batch_states: ti.Field | None = None  # (rows,) i32
fg_exact_dp_batch_transitions: ti.Field | None = None  # (rows,) i32
fg_exact_dp_batch_overflow: ti.Field | None = None  # (rows,) i32


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
        fg_section_forced_caps, \
        fg_pair_caps, \
        fg_ft_list, \
        fg_ff_list, \
        fg_cfg_start_list, \
        fg_cfg_len_list, \
        fg_cfg_total_len_list
    global fg_cfg_base_list, fg_cfg_mode_list, fg_cfg_max_fp
    global fg_cfg_dedupe_hash, fg_cfg_dedupe_sig, fg_cfg_dedupe_rep_cfg_idx
    global fg_cfg_dedupe_rep_count, fg_cfg_dedupe_active
    global fg_best_final_score, fg_best_base_score, fg_best_cfg_idx
    global fg_best_ft, fg_best_ff, fg_best_g_pp, fg_best_g_cm, fg_best_g_fm, fg_best_g_ov
    global fg_best_score_penalty, fg_best_fill_penalty, fg_best_cfg_counts, fg_best_packed
    global fg_best_packed_download_staging_256, fg_best_packed_download_staging_1024
    global fg_global_best_packed_download_staging_256, fg_global_best_packed_download_staging_1024
    global fg_stage1_packed, fg_stage1_wave_best
    global fg_stage1_final_score, fg_stage1_base_score, fg_stage1_cfg_idx
    global fg_stage1_g_pp, fg_stage1_g_cm, fg_stage1_g_fm, fg_stage1_g_ov
    global fg_stage1_score_penalty, fg_stage1_fill_penalty
    global fg_flat_work_genome, fg_flat_work_ftff
    global fg_exact_dp_w_prefix, fg_exact_dp_c_prefix, fg_exact_dp_dp
    global fg_exact_dp_best_delta, fg_exact_dp_counts
    global fg_exact_dp_full_w_prefix, fg_exact_dp_full_c_prefix
    global fg_exact_dp_sparse_hash_keys, fg_exact_dp_sparse_hash_vals
    global fg_exact_dp_sparse_state_i, fg_exact_dp_sparse_state_first, fg_exact_dp_sparse_state_carry
    global fg_exact_dp_sparse_dp, fg_exact_dp_sparse_policy_p, fg_exact_dp_sparse_policy_k
    global fg_exact_dp_sparse_order, fg_exact_dp_sparse_state_count
    global fg_exact_dp_sparse_best_delta, fg_exact_dp_sparse_counts
    global fg_exact_dp_sparse_states, fg_exact_dp_sparse_transitions, fg_exact_dp_sparse_overflow
    global fg_exact_dp_batch_raw_fill, fg_exact_dp_batch_non_fever_base, fg_exact_dp_batch_ft_idx
    global fg_exact_dp_batch_w_head_prefix, fg_exact_dp_batch_c_head_prefix
    global fg_exact_dp_batch_w_body, fg_exact_dp_batch_c_body
    global fg_exact_dp_batch_hash_keys, fg_exact_dp_batch_hash_vals
    global fg_exact_dp_batch_state_i, fg_exact_dp_batch_state_first, fg_exact_dp_batch_state_carry
    global fg_exact_dp_batch_dp, fg_exact_dp_batch_policy_p, fg_exact_dp_batch_policy_k
    global fg_exact_dp_batch_order, fg_exact_dp_batch_state_count
    global fg_exact_dp_batch_best_delta, fg_exact_dp_batch_counts
    global fg_exact_dp_batch_states, fg_exact_dp_batch_transitions, fg_exact_dp_batch_overflow
    global fg_exact_dp_batch_raw_fill, fg_exact_dp_batch_non_fever_base, fg_exact_dp_batch_ft_idx
    global fg_exact_dp_batch_w_head_prefix, fg_exact_dp_batch_c_head_prefix
    global fg_exact_dp_batch_w_body, fg_exact_dp_batch_c_body
    global fg_exact_dp_batch_hash_keys, fg_exact_dp_batch_hash_vals
    global fg_exact_dp_batch_state_i, fg_exact_dp_batch_state_first, fg_exact_dp_batch_state_carry
    global fg_exact_dp_batch_dp, fg_exact_dp_batch_policy_p, fg_exact_dp_batch_policy_k
    global fg_exact_dp_batch_order, fg_exact_dp_batch_state_count
    global fg_exact_dp_batch_best_delta, fg_exact_dp_batch_counts
    global fg_exact_dp_batch_states, fg_exact_dp_batch_transitions, fg_exact_dp_batch_overflow

    song_timestamps = None
    song_timestamps_great_candidate = None
    fg_fever_end_idx_song = None
    fg_fever_end_idx_great_candidate = None
    fg_forced_counts = None
    fg_section_forced_caps = None
    fg_pair_caps = None
    fg_ft_list = None
    fg_ff_list = None
    fg_cfg_start_list = None
    fg_cfg_len_list = None
    fg_cfg_total_len_list = None
    fg_cfg_base_list = None
    fg_cfg_mode_list = None
    fg_cfg_max_fp = None
    fg_cfg_dedupe_hash = None
    fg_cfg_dedupe_sig = None
    fg_cfg_dedupe_rep_cfg_idx = None
    fg_cfg_dedupe_rep_count = None
    fg_cfg_dedupe_active = None

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
    fg_best_packed_download_staging_256 = None
    fg_best_packed_download_staging_1024 = None
    fg_global_best_packed_download_staging_256 = None
    fg_global_best_packed_download_staging_1024 = None

    fg_stage1_packed = None
    fg_stage1_wave_best = None
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
        fg_selected_packed_batch, \
        fg_selected_packed_batch_download_staging_1, \
        fg_selected_packed_batch_download_staging_8, \
        fg_selected_packed_batch_download_staging_32, \
        fg_selected_packed_batch_download_staging_128
    global \
        fg_frontier_base_score, \
        fg_frontier_proxy_score, \
        fg_frontier_priority, \
        fg_frontier_force_keep, \
        fg_frontier_center_bucket_ft, \
        fg_frontier_center_bucket_ff, \
        fg_frontier_timing_bucket, \
        fg_frontier_selected_count, \
        fg_frontier_selected_indices, \
        fg_frontier_base_order, \
        fg_frontier_fg_order, \
        fg_frontier_selected_count_batch, \
        fg_frontier_selected_indices_batch
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
    fg_selected_packed_batch_download_staging_1 = None
    fg_selected_packed_batch_download_staging_8 = None
    fg_selected_packed_batch_download_staging_32 = None
    fg_selected_packed_batch_download_staging_128 = None
    fg_frontier_base_score = None
    fg_frontier_proxy_score = None
    fg_frontier_priority = None
    fg_frontier_force_keep = None
    fg_frontier_center_bucket_ft = None
    fg_frontier_center_bucket_ff = None
    fg_frontier_timing_bucket = None
    fg_frontier_selected_count = None
    fg_frontier_selected_indices = None
    fg_frontier_base_order = None
    fg_frontier_fg_order = None
    fg_frontier_selected_count_batch = None
    fg_frontier_selected_indices_batch = None
    fg_genome_hint_allocation = None

    fg_exact_dp_w_prefix = None
    fg_exact_dp_c_prefix = None
    fg_exact_dp_dp = None
    fg_exact_dp_best_delta = None
    fg_exact_dp_counts = None

    fg_exact_dp_full_w_prefix = None
    fg_exact_dp_full_c_prefix = None
    fg_exact_dp_sparse_hash_keys = None
    fg_exact_dp_sparse_hash_vals = None
    fg_exact_dp_sparse_state_i = None
    fg_exact_dp_sparse_state_first = None
    fg_exact_dp_sparse_state_carry = None
    fg_exact_dp_sparse_dp = None
    fg_exact_dp_sparse_policy_p = None
    fg_exact_dp_sparse_policy_k = None
    fg_exact_dp_sparse_order = None
    fg_exact_dp_sparse_state_count = None
    fg_exact_dp_sparse_best_delta = None
    fg_exact_dp_sparse_counts = None
    fg_exact_dp_sparse_states = None
    fg_exact_dp_sparse_transitions = None
    fg_exact_dp_sparse_overflow = None
    fg_exact_dp_batch_raw_fill = None
    fg_exact_dp_batch_non_fever_base = None
    fg_exact_dp_batch_ft_idx = None
    fg_exact_dp_batch_w_head_prefix = None
    fg_exact_dp_batch_c_head_prefix = None
    fg_exact_dp_batch_w_body = None
    fg_exact_dp_batch_c_body = None
    fg_exact_dp_batch_hash_keys = None
    fg_exact_dp_batch_hash_vals = None
    fg_exact_dp_batch_state_i = None
    fg_exact_dp_batch_state_first = None
    fg_exact_dp_batch_state_carry = None
    fg_exact_dp_batch_dp = None
    fg_exact_dp_batch_policy_p = None
    fg_exact_dp_batch_policy_k = None
    fg_exact_dp_batch_order = None
    fg_exact_dp_batch_state_count = None
    fg_exact_dp_batch_best_delta = None
    fg_exact_dp_batch_counts = None
    fg_exact_dp_batch_states = None
    fg_exact_dp_batch_transitions = None
    fg_exact_dp_batch_overflow = None

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
    kernels_module.fg_section_forced_caps = fg_section_forced_caps
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
    kernels_module.fg_cfg_dedupe_hash = fg_cfg_dedupe_hash
    kernels_module.fg_cfg_dedupe_sig = fg_cfg_dedupe_sig
    kernels_module.fg_cfg_dedupe_rep_cfg_idx = fg_cfg_dedupe_rep_cfg_idx
    kernels_module.fg_cfg_dedupe_rep_count = fg_cfg_dedupe_rep_count
    kernels_module.fg_cfg_dedupe_active = fg_cfg_dedupe_active

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
    kernels_module.fg_stage1_wave_best = fg_stage1_wave_best
    kernels_module.FG_STAGE1_HAS_AUX_FIELDS = fg_stage1_final_score is not None
    kernels_module.FG_STAGE1_HAS_CFG_IDX_FIELD = fg_stage1_cfg_idx is not None

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
    kernels_module.fg_frontier_base_score = fg_frontier_base_score
    kernels_module.fg_frontier_proxy_score = fg_frontier_proxy_score
    kernels_module.fg_frontier_priority = fg_frontier_priority
    kernels_module.fg_frontier_force_keep = fg_frontier_force_keep
    kernels_module.fg_frontier_center_bucket_ft = fg_frontier_center_bucket_ft
    kernels_module.fg_frontier_center_bucket_ff = fg_frontier_center_bucket_ff
    kernels_module.fg_frontier_timing_bucket = fg_frontier_timing_bucket
    kernels_module.fg_frontier_selected_count = fg_frontier_selected_count
    kernels_module.fg_frontier_selected_indices = fg_frontier_selected_indices
    kernels_module.fg_frontier_base_order = fg_frontier_base_order
    kernels_module.fg_frontier_fg_order = fg_frontier_fg_order
    kernels_module.fg_frontier_selected_count_batch = fg_frontier_selected_count_batch
    kernels_module.fg_frontier_selected_indices_batch = fg_frontier_selected_indices_batch
    kernels_module.fg_genome_hint_allocation = fg_genome_hint_allocation

    # Exact FG DP (reference / research-only)
    kernels_module.fg_exact_dp_w_prefix = fg_exact_dp_w_prefix
    kernels_module.fg_exact_dp_c_prefix = fg_exact_dp_c_prefix
    kernels_module.fg_exact_dp_dp = fg_exact_dp_dp
    kernels_module.fg_exact_dp_best_delta = fg_exact_dp_best_delta
    kernels_module.fg_exact_dp_counts = fg_exact_dp_counts

    kernels_module.fg_exact_dp_full_w_prefix = fg_exact_dp_full_w_prefix
    kernels_module.fg_exact_dp_full_c_prefix = fg_exact_dp_full_c_prefix
    kernels_module.fg_exact_dp_sparse_hash_keys = fg_exact_dp_sparse_hash_keys
    kernels_module.fg_exact_dp_sparse_hash_vals = fg_exact_dp_sparse_hash_vals
    kernels_module.fg_exact_dp_sparse_state_i = fg_exact_dp_sparse_state_i
    kernels_module.fg_exact_dp_sparse_state_first = fg_exact_dp_sparse_state_first
    kernels_module.fg_exact_dp_sparse_state_carry = fg_exact_dp_sparse_state_carry
    kernels_module.fg_exact_dp_sparse_dp = fg_exact_dp_sparse_dp
    kernels_module.fg_exact_dp_sparse_policy_p = fg_exact_dp_sparse_policy_p
    kernels_module.fg_exact_dp_sparse_policy_k = fg_exact_dp_sparse_policy_k
    kernels_module.fg_exact_dp_sparse_order = fg_exact_dp_sparse_order
    kernels_module.fg_exact_dp_sparse_state_count = fg_exact_dp_sparse_state_count
    kernels_module.fg_exact_dp_sparse_best_delta = fg_exact_dp_sparse_best_delta
    kernels_module.fg_exact_dp_sparse_counts = fg_exact_dp_sparse_counts
    kernels_module.fg_exact_dp_sparse_states = fg_exact_dp_sparse_states
    kernels_module.fg_exact_dp_sparse_transitions = fg_exact_dp_sparse_transitions
    kernels_module.fg_exact_dp_sparse_overflow = fg_exact_dp_sparse_overflow
    kernels_module.fg_exact_dp_batch_raw_fill = fg_exact_dp_batch_raw_fill
    kernels_module.fg_exact_dp_batch_non_fever_base = fg_exact_dp_batch_non_fever_base
    kernels_module.fg_exact_dp_batch_ft_idx = fg_exact_dp_batch_ft_idx
    kernels_module.fg_exact_dp_batch_w_head_prefix = fg_exact_dp_batch_w_head_prefix
    kernels_module.fg_exact_dp_batch_c_head_prefix = fg_exact_dp_batch_c_head_prefix
    kernels_module.fg_exact_dp_batch_w_body = fg_exact_dp_batch_w_body
    kernels_module.fg_exact_dp_batch_c_body = fg_exact_dp_batch_c_body
    kernels_module.fg_exact_dp_batch_hash_keys = fg_exact_dp_batch_hash_keys
    kernels_module.fg_exact_dp_batch_hash_vals = fg_exact_dp_batch_hash_vals
    kernels_module.fg_exact_dp_batch_state_i = fg_exact_dp_batch_state_i
    kernels_module.fg_exact_dp_batch_state_first = fg_exact_dp_batch_state_first
    kernels_module.fg_exact_dp_batch_state_carry = fg_exact_dp_batch_state_carry
    kernels_module.fg_exact_dp_batch_dp = fg_exact_dp_batch_dp
    kernels_module.fg_exact_dp_batch_policy_p = fg_exact_dp_batch_policy_p
    kernels_module.fg_exact_dp_batch_policy_k = fg_exact_dp_batch_policy_k
    kernels_module.fg_exact_dp_batch_order = fg_exact_dp_batch_order
    kernels_module.fg_exact_dp_batch_state_count = fg_exact_dp_batch_state_count
    kernels_module.fg_exact_dp_batch_best_delta = fg_exact_dp_batch_best_delta
    kernels_module.fg_exact_dp_batch_counts = fg_exact_dp_batch_counts
    kernels_module.fg_exact_dp_batch_states = fg_exact_dp_batch_states
    kernels_module.fg_exact_dp_batch_transitions = fg_exact_dp_batch_transitions
    kernels_module.fg_exact_dp_batch_overflow = fg_exact_dp_batch_overflow


def allocate_fields() -> None:
    """Allocate ForceGreats GPU fields. Must be called after ti.init()."""
    global song_timestamps, song_timestamps_great_candidate
    global fg_fever_end_idx_song, fg_fever_end_idx_great_candidate
    global \
        fg_forced_counts, \
        fg_section_forced_caps, \
        fg_pair_caps, \
        fg_ft_list, \
        fg_ff_list, \
        fg_cfg_start_list, \
        fg_cfg_len_list, \
        fg_cfg_total_len_list
    global fg_cfg_base_list, fg_cfg_mode_list, fg_cfg_max_fp
    global fg_cfg_total_len_max
    global fg_cfg_dedupe_hash, fg_cfg_dedupe_sig, fg_cfg_dedupe_rep_cfg_idx
    global fg_cfg_dedupe_rep_count, fg_cfg_dedupe_active
    global fg_best_final_score, fg_best_base_score, fg_best_cfg_idx, fg_best_ft, fg_best_ff
    global fg_best_g_pp, fg_best_g_cm, fg_best_g_fm, fg_best_g_ov
    global fg_best_score_penalty, fg_best_fill_penalty, fg_best_cfg_counts, fg_best_packed
    global fg_best_packed_download_staging_256, fg_best_packed_download_staging_1024
    global fg_stage1_final_score, fg_stage1_base_score, fg_stage1_cfg_idx
    global fg_stage1_g_pp, fg_stage1_g_cm, fg_stage1_g_fm, fg_stage1_g_ov
    global fg_stage1_score_penalty, fg_stage1_fill_penalty
    global fg_stage1_packed, fg_stage1_wave_best
    global fg_flat_work_genome, fg_flat_work_ftff
    global fg_exact_dp_w_prefix, fg_exact_dp_c_prefix, fg_exact_dp_dp
    global fg_exact_dp_best_delta, fg_exact_dp_counts
    global fg_exact_dp_full_w_prefix, fg_exact_dp_full_c_prefix
    global fg_exact_dp_sparse_hash_keys, fg_exact_dp_sparse_hash_vals
    global fg_exact_dp_sparse_state_i, fg_exact_dp_sparse_state_first, fg_exact_dp_sparse_state_carry
    global fg_exact_dp_sparse_dp, fg_exact_dp_sparse_policy_p, fg_exact_dp_sparse_policy_k
    global fg_exact_dp_sparse_order, fg_exact_dp_sparse_state_count
    global fg_exact_dp_sparse_best_delta, fg_exact_dp_sparse_counts
    global fg_exact_dp_sparse_states, fg_exact_dp_sparse_transitions, fg_exact_dp_sparse_overflow
    global fg_exact_dp_batch_raw_fill, fg_exact_dp_batch_non_fever_base, fg_exact_dp_batch_ft_idx
    global fg_exact_dp_batch_w_head_prefix, fg_exact_dp_batch_c_head_prefix
    global fg_exact_dp_batch_w_body, fg_exact_dp_batch_c_body
    global fg_exact_dp_batch_hash_keys, fg_exact_dp_batch_hash_vals
    global fg_exact_dp_batch_state_i, fg_exact_dp_batch_state_first, fg_exact_dp_batch_state_carry
    global fg_exact_dp_batch_dp, fg_exact_dp_batch_policy_p, fg_exact_dp_batch_policy_k
    global fg_exact_dp_batch_order, fg_exact_dp_batch_state_count
    global fg_exact_dp_batch_best_delta, fg_exact_dp_batch_counts
    global fg_exact_dp_batch_states, fg_exact_dp_batch_transitions, fg_exact_dp_batch_overflow
    global fg_global_best_packed_download_staging_256, fg_global_best_packed_download_staging_1024
    global \
        fg_frontier_base_score, \
        fg_frontier_proxy_score, \
        fg_frontier_priority, \
        fg_frontier_force_keep, \
        fg_frontier_center_bucket_ft, \
        fg_frontier_center_bucket_ff, \
        fg_frontier_timing_bucket, \
        fg_frontier_selected_count, \
        fg_frontier_selected_indices, \
        fg_frontier_base_order, \
        fg_frontier_fg_order, \
        fg_frontier_selected_count_batch, \
        fg_frontier_selected_indices_batch
    global _fields_allocated

    if _fields_allocated:
        return

    song_timestamps = ti.field(dtype=ti.f32, shape=FG_MAX_SONG_NOTES)
    song_timestamps_great_candidate = ti.field(dtype=ti.f32, shape=FG_MAX_SONG_NOTES)
    fg_fever_end_idx_song = ti.field(dtype=ti.i32, shape=(FG_MAX_SONG_NOTES, FG_MAX_STAT + 1))
    fg_fever_end_idx_great_candidate = ti.field(dtype=ti.i32, shape=(FG_MAX_SONG_NOTES, FG_MAX_STAT + 1))

    fg_forced_counts = ti.field(dtype=ti.i32, shape=(FG_MAX_CONFIGS, FG_MAX_SECTIONS))
    fg_section_forced_caps = ti.field(dtype=ti.i32, shape=FG_MAX_SECTIONS)
    caps_np = np.zeros((FG_MAX_SECTIONS,), dtype=np.int32)
    caps_np[: len(_FG_SECTION_FORCED_CAPS_DEFAULT)] = np.asarray(_FG_SECTION_FORCED_CAPS_DEFAULT, dtype=np.int32)
    fg_section_forced_caps.from_numpy(caps_np)
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
    fg_cfg_dedupe_hash = ti.field(dtype=ti.u64, shape=(FG_CFG_DEDUPE_WORK_ITEMS, FG_CFG_DEDUPE_MAX_REPS))
    fg_cfg_dedupe_sig = ti.Vector.field(
        n=FG_CFG_DEDUPE_SIG_WORDS,
        dtype=ti.i32,
        shape=(FG_CFG_DEDUPE_WORK_ITEMS, FG_CFG_DEDUPE_MAX_REPS),
    )
    fg_cfg_dedupe_rep_cfg_idx = ti.field(dtype=ti.i32, shape=(FG_CFG_DEDUPE_WORK_ITEMS, FG_CFG_DEDUPE_MAX_REPS))
    fg_cfg_dedupe_rep_count = ti.field(dtype=ti.i32, shape=FG_CFG_DEDUPE_WORK_ITEMS)
    fg_cfg_dedupe_active = ti.field(dtype=ti.i32, shape=FG_CFG_DEDUPE_WORK_ITEMS)

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
    fg_best_packed_download_staging_256 = ti.field(dtype=ti.i32, shape=(256, FG_PACKED_COLS))
    fg_best_packed_download_staging_1024 = (
        ti.field(dtype=ti.i32, shape=(1024, FG_PACKED_COLS)) if int(MAX_GENOMES) >= 1024 else None
    )

    if IS_METAL:
        fg_stage1_final_score = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_MAX_FTFF))
        fg_stage1_base_score = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_MAX_FTFF))
        fg_stage1_cfg_idx = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_MAX_FTFF))
        fg_stage1_g_pp = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_MAX_FTFF))
        fg_stage1_g_cm = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_MAX_FTFF))
        fg_stage1_g_fm = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_MAX_FTFF))
        fg_stage1_g_ov = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_MAX_FTFF))
        fg_stage1_score_penalty = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_MAX_FTFF))
        fg_stage1_fill_penalty = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_MAX_FTFF))
    else:
        # Vulkan path writes/reads packed stage-1 winners only.
        # Keep cfg_idx because downstream result packing reads decoded tie-break metadata.
        fg_stage1_final_score = None
        fg_stage1_base_score = None
        fg_stage1_cfg_idx = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_MAX_FTFF))
        fg_stage1_g_pp = None
        fg_stage1_g_cm = None
        fg_stage1_g_fm = None
        fg_stage1_g_ov = None
        fg_stage1_score_penalty = None
        fg_stage1_fill_penalty = None

    # Packed 64-bit field for atomic (score, cfg_idx) updates
    fg_stage1_packed = ti.field(dtype=ti.i64, shape=(MAX_GENOMES, FG_MAX_FTFF))
    fg_stage1_wave_best = ti.field(dtype=ti.u64, shape=(FG_MAX_FLAT_WORK_ITEMS, FG_STAGE1_WAVE_SLOTS_MAX))

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
        fg_selected_packed_batch, \
        fg_selected_packed_batch_download_staging_1, \
        fg_selected_packed_batch_download_staging_8, \
        fg_selected_packed_batch_download_staging_32, \
        fg_selected_packed_batch_download_staging_128
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
    fg_global_best_packed_download_staging_256 = ti.field(dtype=ti.i32, shape=(256, FG_PACKED_COLS))
    fg_global_best_packed_download_staging_1024 = (
        ti.field(dtype=ti.i32, shape=(1024, FG_PACKED_COLS)) if int(MAX_GENOMES) >= 1024 else None
    )

    fg_input_base_score = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    fg_keep_mask = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    fg_selected_count = ti.field(dtype=ti.i32, shape=())
    fg_selected_indices = ti.field(dtype=ti.i32, shape=FG_DOWNLOAD_TOPK_MAX)
    fg_selected_packed = ti.field(dtype=ti.i32, shape=(FG_DOWNLOAD_TOPK_MAX, FG_SELECTED_PACKED_COLS))
    fg_selected_packed_batch = ti.field(
        dtype=ti.i32,
        shape=(FG_DOWNLOAD_BATCH_MAX, FG_DOWNLOAD_TOPK_MAX, FG_SELECTED_PACKED_COLS),
    )
    # Download staging tiers (allocate only the tiers we can actually use).
    fg_selected_packed_batch_download_staging_1 = ti.field(
        dtype=ti.i32,
        shape=(1, FG_DOWNLOAD_TOPK_MAX, FG_SELECTED_PACKED_COLS),
    )
    fg_selected_packed_batch_download_staging_8 = (
        ti.field(
            dtype=ti.i32,
            shape=(8, FG_DOWNLOAD_TOPK_MAX, FG_SELECTED_PACKED_COLS),
        )
        if FG_DOWNLOAD_BATCH_MAX >= 8
        else None
    )
    fg_selected_packed_batch_download_staging_32 = (
        ti.field(
            dtype=ti.i32,
            shape=(32, FG_DOWNLOAD_TOPK_MAX, FG_SELECTED_PACKED_COLS),
        )
        if FG_DOWNLOAD_BATCH_MAX >= 32
        else None
    )
    fg_selected_packed_batch_download_staging_128 = (
        ti.field(
            dtype=ti.i32,
            shape=(128, FG_DOWNLOAD_TOPK_MAX, FG_SELECTED_PACKED_COLS),
        )
        if FG_DOWNLOAD_BATCH_MAX >= 128
        else None
    )

    fg_frontier_base_score = ti.field(dtype=ti.i32, shape=FG_SIGNATURE_FRONTIER_MAX)
    fg_frontier_proxy_score = ti.field(dtype=ti.i32, shape=FG_SIGNATURE_FRONTIER_MAX)
    fg_frontier_priority = ti.field(dtype=ti.i32, shape=FG_SIGNATURE_FRONTIER_MAX)
    fg_frontier_force_keep = ti.field(dtype=ti.i32, shape=FG_SIGNATURE_FRONTIER_MAX)
    fg_frontier_center_bucket_ft = ti.field(dtype=ti.i32, shape=FG_SIGNATURE_FRONTIER_MAX)
    fg_frontier_center_bucket_ff = ti.field(dtype=ti.i32, shape=FG_SIGNATURE_FRONTIER_MAX)
    fg_frontier_timing_bucket = ti.field(dtype=ti.i32, shape=FG_SIGNATURE_FRONTIER_MAX)
    fg_frontier_selected_count = ti.field(dtype=ti.i32, shape=())
    fg_frontier_selected_indices = ti.field(dtype=ti.i32, shape=FG_SIGNATURE_FRONTIER_MAX)
    fg_frontier_base_order = ti.field(dtype=ti.i32, shape=FG_SIGNATURE_FRONTIER_MAX)
    fg_frontier_fg_order = ti.field(dtype=ti.i32, shape=FG_SIGNATURE_FRONTIER_MAX)
    fg_frontier_selected_count_batch = ti.field(dtype=ti.i32, shape=FG_SIGNATURE_FRONTIER_BATCH_MAX)
    fg_frontier_selected_indices_batch = ti.field(
        dtype=ti.i32,
        shape=(FG_SIGNATURE_FRONTIER_BATCH_MAX, FG_SIGNATURE_FRONTIER_MAX),
    )

    # Warm-start hints for FG gem allocation
    global fg_genome_hint_allocation
    fg_genome_hint_allocation = ti.Vector.field(n=4, dtype=ti.i32, shape=MAX_GENOMES)

    # Exact FG DP (reference / research-only)
    fg_exact_dp_w_prefix = ti.field(dtype=ti.i64, shape=(FG_EXACT_DP_MAX_NOTES + 1))
    fg_exact_dp_c_prefix = ti.field(dtype=ti.i64, shape=(FG_EXACT_DP_MAX_NOTES + 1))
    fg_exact_dp_dp = ti.field(dtype=ti.i64, shape=(FG_EXACT_DP_MAX_NOTES + 1, FG_EXACT_DP_MAX_NOTES + 1))
    fg_exact_dp_best_delta = ti.field(dtype=ti.i64, shape=())
    fg_exact_dp_counts = ti.field(dtype=ti.i32, shape=(FG_MAX_SECTIONS,))

    fg_exact_dp_full_w_prefix = ti.field(dtype=ti.i64, shape=(FG_EXACT_DP_FULL_PREFIX_LEN,))
    fg_exact_dp_full_c_prefix = ti.field(dtype=ti.i64, shape=(FG_EXACT_DP_FULL_PREFIX_LEN,))
    fg_exact_dp_sparse_hash_keys = ti.field(dtype=ti.i64, shape=(FG_EXACT_DP_SPARSE_HASH_SIZE,))
    fg_exact_dp_sparse_hash_vals = ti.field(dtype=ti.i32, shape=(FG_EXACT_DP_SPARSE_HASH_SIZE,))
    fg_exact_dp_sparse_state_i = ti.field(dtype=ti.i32, shape=(FG_EXACT_DP_SPARSE_MAX_STATES,))
    fg_exact_dp_sparse_state_first = ti.field(dtype=ti.i32, shape=(FG_EXACT_DP_SPARSE_MAX_STATES,))
    fg_exact_dp_sparse_state_carry = ti.field(dtype=ti.i32, shape=(FG_EXACT_DP_SPARSE_MAX_STATES,))
    fg_exact_dp_sparse_dp = ti.field(dtype=ti.i64, shape=(FG_EXACT_DP_SPARSE_MAX_STATES,))
    fg_exact_dp_sparse_policy_p = ti.field(dtype=ti.i32, shape=(FG_EXACT_DP_SPARSE_MAX_STATES,))
    fg_exact_dp_sparse_policy_k = ti.field(dtype=ti.i32, shape=(FG_EXACT_DP_SPARSE_MAX_STATES,))
    fg_exact_dp_sparse_order = ti.field(dtype=ti.i32, shape=(FG_EXACT_DP_SPARSE_MAX_STATES,))
    fg_exact_dp_sparse_state_count = ti.field(dtype=ti.i32, shape=())
    fg_exact_dp_sparse_best_delta = ti.field(dtype=ti.i64, shape=())
    fg_exact_dp_sparse_counts = ti.field(dtype=ti.i32, shape=(FG_MAX_SECTIONS,))
    fg_exact_dp_sparse_states = ti.field(dtype=ti.i32, shape=())
    fg_exact_dp_sparse_transitions = ti.field(dtype=ti.i32, shape=())
    fg_exact_dp_sparse_overflow = ti.field(dtype=ti.i32, shape=())

    batch_shape = (FG_EXACT_DP_BATCH_MAX_ROWS,)
    batch_state_shape = (FG_EXACT_DP_BATCH_MAX_ROWS, FG_EXACT_DP_SPARSE_MAX_STATES)
    batch_hash_shape = (FG_EXACT_DP_BATCH_MAX_ROWS, FG_EXACT_DP_SPARSE_HASH_SIZE)
    fg_exact_dp_batch_raw_fill = ti.field(dtype=ti.f32, shape=batch_shape)
    fg_exact_dp_batch_non_fever_base = ti.field(dtype=ti.i32, shape=batch_shape)
    fg_exact_dp_batch_ft_idx = ti.field(dtype=ti.i32, shape=batch_shape)
    fg_exact_dp_batch_w_head_prefix = ti.field(
        dtype=ti.i64,
        shape=(FG_EXACT_DP_BATCH_MAX_ROWS, FG_EXACT_DP_PREFIX_HEAD_LEN),
    )
    fg_exact_dp_batch_c_head_prefix = ti.field(
        dtype=ti.i64,
        shape=(FG_EXACT_DP_BATCH_MAX_ROWS, FG_EXACT_DP_PREFIX_HEAD_LEN),
    )
    fg_exact_dp_batch_w_body = ti.field(dtype=ti.i64, shape=batch_shape)
    fg_exact_dp_batch_c_body = ti.field(dtype=ti.i64, shape=batch_shape)
    fg_exact_dp_batch_hash_keys = ti.field(dtype=ti.i64, shape=batch_hash_shape)
    fg_exact_dp_batch_hash_vals = ti.field(dtype=ti.i32, shape=batch_hash_shape)
    fg_exact_dp_batch_state_i = ti.field(dtype=ti.i32, shape=batch_state_shape)
    fg_exact_dp_batch_state_first = ti.field(dtype=ti.i32, shape=batch_state_shape)
    fg_exact_dp_batch_state_carry = ti.field(dtype=ti.i32, shape=batch_state_shape)
    fg_exact_dp_batch_dp = ti.field(dtype=ti.i64, shape=batch_state_shape)
    fg_exact_dp_batch_policy_p = ti.field(dtype=ti.i32, shape=batch_state_shape)
    fg_exact_dp_batch_policy_k = ti.field(dtype=ti.i32, shape=batch_state_shape)
    fg_exact_dp_batch_order = ti.field(dtype=ti.i32, shape=batch_state_shape)
    fg_exact_dp_batch_state_count = ti.field(dtype=ti.i32, shape=batch_shape)
    fg_exact_dp_batch_best_delta = ti.field(dtype=ti.i64, shape=batch_shape)
    fg_exact_dp_batch_counts = ti.field(dtype=ti.i32, shape=(FG_EXACT_DP_BATCH_MAX_ROWS, FG_MAX_SECTIONS))
    fg_exact_dp_batch_states = ti.field(dtype=ti.i32, shape=batch_shape)
    fg_exact_dp_batch_transitions = ti.field(dtype=ti.i32, shape=batch_shape)
    fg_exact_dp_batch_overflow = ti.field(dtype=ti.i32, shape=batch_shape)

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
        init_taichi()

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
    if IS_METAL:
        fg_kernels.fg_stage1_init_kernel(n_genomes, n_ftff)
    else:
        # Vulkan runtime uses the minimal packed-only init; precompile it.
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
            1,  # is_first_chunk
        )
    else:
        # Warm Stage-1 (Vulkan): wave-staged block-per-owner kernels (atomic-free).
        n_work_items = n_genomes * n_ftff
        fg_kernels.fg_build_flat_work_kernel(n_genomes, n_ftff)
        fg_kernels.fg_stage1_clear_wave_best_kernel(n_work_items)
        fg_kernels.fg_stage1_waves_kernel(
            bool(getattr(fg_kernels, "FG_STAGE1_SMALL_SECTIONS_FASTPATH", False) and int(n_sections) <= 4),
            0,  # work_offset
            0,  # use_cfg_dedupe
            0,  # cfg_dedupe_slots
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
            0,  # color flags (12x)
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
            0,  # song_slot
            0,  # pair_caps_from_timeline
        )
        fg_kernels.fg_stage1_reduce_waves_kernel(0, n_work_items, 1)

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
    try:
        fg_kernels.fg_copy_selected_packed_batch_to_download_staging_kernel(
            fg_selected_packed_batch_download_staging_1,
            1,
        )
    except Exception as e:
        logger.debug(f"fields:warmup_kernels: {e}")
    try:
        fg_kernels.fg_copy_best_packed_to_download_staging_kernel(
            fg_best_packed_download_staging_256,
            1,
        )
    except Exception as e:
        logger.debug(f"fields:warmup_kernels: {e}")
    try:
        fg_kernels.fg_copy_global_best_packed_to_download_staging_kernel(
            fg_global_best_packed_download_staging_256,
            1,
        )
    except Exception as e:
        logger.debug(f"fields:warmup_kernels: {e}")

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
    except Exception as e:
        logger.debug(f"fields:ensure_ready_with_warmup: {e}")
    ensure_fields_allocated()
    warmup_kernels()
