"""
ForceGreats GPU Fields - declarations and allocation.

These fields are *separate* from the main gem solver fields in `taichi_gem.fields`.
We share the Taichi runtime (`taichi_gem.runtime`) and reuse the main gem solver
reference tables + base genome stats fields for scoring.
"""

from __future__ import annotations

import taichi as ti

from ..runtime import init_taichi_vulkan, is_initialized
from ..fields import MAX_GENOMES

# ============================================================================
# CONSTANTS
# ============================================================================

FG_MAX_SECTIONS = 16
FG_MAX_STAT = 160  # Maximum FT/FF stat index
FG_MAX_CONFIGS = 1048576
FG_MAX_FTFF = 1024
FG_MAX_SONG_NOTES = 200000  # safety cap for timestamps uploaded to GPU

# Flattened parallelization: MAX_GENOMES * FG_MAX_FTFF threads
# Each thread processes ONE config at a time (chunked)
FG_MAX_FLAT_WORK_ITEMS = MAX_GENOMES * FG_MAX_FTFF  # 4096 * 256 = 1M work items max


# ============================================================================
# GPU FIELDS (device-resident)
# ============================================================================

# Song timestamps (GPU-resident; used by FG finder kernel)
song_timestamps: ti.Field | None = None  # (FG_MAX_SONG_NOTES,) f32
song_timestamps_great_candidate: ti.Field | None = None  # (FG_MAX_SONG_NOTES,) f32

# FG finder inputs (GPU-resident)
# Stores fill-penalty targets (fp) per section (not raw forced counts).
fg_forced_counts: ti.Field | None = None  # (FG_MAX_CONFIGS, FG_MAX_SECTIONS) i32
fg_pair_caps: ti.Field | None = None      # (FG_MAX_STAT+1, FG_MAX_STAT+1, FG_MAX_SECTIONS) i32
fg_ft_list: ti.Field | None = None        # (FG_MAX_FTFF,) i32
fg_ff_list: ti.Field | None = None        # (FG_MAX_FTFF,) i32

# FG finder outputs (per genome)
fg_best_final_score: ti.Field | None = None     # (MAX_GENOMES,) i32
fg_best_base_score: ti.Field | None = None      # (MAX_GENOMES,) i32
fg_best_cfg_idx: ti.Field | None = None         # (MAX_GENOMES,) i32
fg_best_ft: ti.Field | None = None              # (MAX_GENOMES,) i32
fg_best_ff: ti.Field | None = None              # (MAX_GENOMES,) i32
fg_best_g_pp: ti.Field | None = None            # (MAX_GENOMES,) i32
fg_best_g_cm: ti.Field | None = None            # (MAX_GENOMES,) i32
fg_best_g_fm: ti.Field | None = None            # (MAX_GENOMES,) i32
fg_best_g_ov: ti.Field | None = None            # (MAX_GENOMES,) i32
fg_best_score_penalty: ti.Field | None = None   # (MAX_GENOMES,) i32
fg_best_fill_penalty: ti.Field | None = None    # (MAX_GENOMES,) i32

# Packed results for efficient CPU download (all 11 fields in one transfer)
# Format: (MAX_GENOMES, 11) with columns: [final_score, base_score, cfg_idx, ft, ff, g_pp, g_cm, g_fm, g_ov, score_penalty, fill_penalty]
fg_best_packed: ti.Field | None = None          # (MAX_GENOMES, 11) i32

# NEW: Packed 64-bit field for atomic (score, cfg_idx) updates - fixes race condition
# Format: (score << 32) | (cfg_idx & 0xFFFFFFFF) - score in upper 32 bits for correct atomic_max ordering
fg_stage1_packed: ti.Field | None = None        # (MAX_GENOMES, FG_MAX_FTFF) i64

# FG finder intermediate outputs (per genome × ftff) - for two-stage reduction
fg_stage1_final_score: ti.Field | None = None   # (MAX_GENOMES, FG_MAX_FTFF) i32
fg_stage1_base_score: ti.Field | None = None    # (MAX_GENOMES, FG_MAX_FTFF) i32
fg_stage1_cfg_idx: ti.Field | None = None       # (MAX_GENOMES, FG_MAX_FTFF) i32
fg_stage1_g_pp: ti.Field | None = None          # (MAX_GENOMES, FG_MAX_FTFF) i32
fg_stage1_g_cm: ti.Field | None = None          # (MAX_GENOMES, FG_MAX_FTFF) i32
fg_stage1_g_fm: ti.Field | None = None          # (MAX_GENOMES, FG_MAX_FTFF) i32
fg_stage1_g_ov: ti.Field | None = None          # (MAX_GENOMES, FG_MAX_FTFF) i32
fg_stage1_score_penalty: ti.Field | None = None # (MAX_GENOMES, FG_MAX_FTFF) i32
fg_stage1_fill_penalty: ti.Field | None = None  # (MAX_GENOMES, FG_MAX_FTFF) i32

# Flat work items for GPU-friendly parallelization
# Each item is (genome_id, ftff_id) - cfg is batched in chunks
fg_flat_work_genome: ti.Field | None = None     # (FG_MAX_FLAT_WORK_ITEMS,) i32
fg_flat_work_ftff: ti.Field | None = None       # (FG_MAX_FLAT_WORK_ITEMS,) i32

# Global best fields for GPU-resident accumulation (persist across group calls)
# These track the best results found across all GPU calls within a single FG batch
fg_global_best_final_score: ti.Field | None = None     # (MAX_GENOMES,) i32
fg_global_best_base_score: ti.Field | None = None      # (MAX_GENOMES,) i32
fg_global_best_cfg_idx: ti.Field | None = None         # (MAX_GENOMES,) i32
fg_global_best_ft: ti.Field | None = None              # (MAX_GENOMES,) i32
fg_global_best_ff: ti.Field | None = None              # (MAX_GENOMES,) i32
fg_global_best_g_pp: ti.Field | None = None            # (MAX_GENOMES,) i32
fg_global_best_g_cm: ti.Field | None = None            # (MAX_GENOMES,) i32
fg_global_best_g_fm: ti.Field | None = None            # (MAX_GENOMES,) i32
fg_global_best_g_ov: ti.Field | None = None            # (MAX_GENOMES,) i32
fg_global_best_score_penalty: ti.Field | None = None   # (MAX_GENOMES,) i32
fg_global_best_fill_penalty: ti.Field | None = None    # (MAX_GENOMES,) i32
fg_global_best_packed: ti.Field | None = None          # (MAX_GENOMES, 11) i32

# Warm-start hints for FG gem allocation (local search optimization)
# Stores: [pp_gems, cm_gems, fm_gems, ov_gems] from previous best allocation
fg_genome_hint_allocation: ti.Field | None = None      # (MAX_GENOMES, 4) i32


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
    global fg_forced_counts, fg_pair_caps, fg_ft_list, fg_ff_list
    global fg_best_final_score, fg_best_base_score, fg_best_cfg_idx
    global fg_best_ft, fg_best_ff, fg_best_g_pp, fg_best_g_cm, fg_best_g_fm, fg_best_g_ov
    global fg_best_score_penalty, fg_best_fill_penalty, fg_best_packed
    global fg_stage1_packed
    global fg_stage1_final_score, fg_stage1_base_score, fg_stage1_cfg_idx
    global fg_stage1_g_pp, fg_stage1_g_cm, fg_stage1_g_fm, fg_stage1_g_ov
    global fg_stage1_score_penalty, fg_stage1_fill_penalty
    global fg_flat_work_genome, fg_flat_work_ftff

    song_timestamps = None
    song_timestamps_great_candidate = None
    fg_forced_counts = None
    fg_pair_caps = None
    fg_ft_list = None
    fg_ff_list = None

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
    global fg_global_best_score_penalty, fg_global_best_fill_penalty, fg_global_best_packed
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
    fg_global_best_packed = None
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
    kernels_module.fg_forced_counts = fg_forced_counts
    kernels_module.fg_pair_caps = fg_pair_caps
    kernels_module.fg_ft_list = fg_ft_list
    kernels_module.fg_ff_list = fg_ff_list

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
    kernels_module.fg_global_best_packed = fg_global_best_packed
    kernels_module.fg_genome_hint_allocation = fg_genome_hint_allocation


def allocate_fields() -> None:
    """Allocate ForceGreats GPU fields. Must be called after ti.init()."""
    global song_timestamps, song_timestamps_great_candidate
    global fg_forced_counts, fg_pair_caps, fg_ft_list, fg_ff_list
    global fg_best_final_score, fg_best_base_score, fg_best_cfg_idx, fg_best_ft, fg_best_ff
    global fg_best_g_pp, fg_best_g_cm, fg_best_g_fm, fg_best_g_ov
    global fg_best_score_penalty, fg_best_fill_penalty, fg_best_packed
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

    fg_forced_counts = ti.field(dtype=ti.i32, shape=(FG_MAX_CONFIGS, FG_MAX_SECTIONS))
    fg_pair_caps = ti.field(dtype=ti.i32, shape=(FG_MAX_STAT + 1, FG_MAX_STAT + 1, FG_MAX_SECTIONS))
    fg_ft_list = ti.field(dtype=ti.i32, shape=FG_MAX_FTFF)
    fg_ff_list = ti.field(dtype=ti.i32, shape=FG_MAX_FTFF)

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
    fg_best_packed = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, 11))

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
    global fg_global_best_score_penalty, fg_global_best_fill_penalty, fg_global_best_packed
    fg_global_best_final_score = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    fg_global_best_base_score = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    fg_global_best_cfg_idx = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    fg_global_best_ft = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    fg_global_best_ff = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    fg_global_best_g_pp = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    fg_global_best_g_cm = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    fg_global_best_g_fm = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    fg_global_best_g_ov = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    fg_global_best_score_penalty = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    fg_global_best_fill_penalty = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    fg_global_best_packed = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, 11))

    # Warm-start hints for FG gem allocation
    global fg_genome_hint_allocation
    fg_genome_hint_allocation = ti.Vector.field(n=4, dtype=ti.i32, shape=MAX_GENOMES)

    _fields_allocated = True


def ensure_fields_allocated() -> None:
    """Ensure ForceGreats fields are allocated and bound to kernels."""
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
    
    # Warmup FLAT stage1 kernel (the heavy one)
    # Check if we are on Metal to decide which kernel to warm up
    from ..fields import IS_METAL
    
    if IS_METAL:
        fg_kernels.fg_stage1_kernel(
            n_genomes,
            total_notes, long_notes, last_note_time,
            total_budget, gem_scale_fever, n_cfg, n_sections, n_ftff,
            cfg_offset,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 # color flags
        )
    else:
        fg_kernels.fg_stage1_flat_kernel(
            n_work_items, n_cfg, cfg_offset,
            total_notes, long_notes, last_note_time,
            total_budget, gem_scale_fever, n_sections,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0  # color flags
        )
    
    # Warmup stage2 reduction kernel
    fg_kernels.fg_stage2_kernel(n_genomes, n_ftff)
    
    # Warmup global best kernels (new for GPU-resident accumulation)
    fg_kernels.fg_reset_global_best_kernel(n_genomes)
    fg_kernels.fg_update_global_best_kernel(n_genomes)

    # Warmup packing kernels (avoid first-download JIT hiccup)
    fg_kernels.fg_pack_results_kernel(n_genomes)
    fg_kernels.fg_pack_global_best_kernel(n_genomes)
    
    # Sync to ensure JIT is complete
    ti.sync()
    
    _kernels_warmed = True


def ensure_ready_with_warmup() -> None:
    """
    Ensure FG fields are allocated AND kernels are pre-warmed.
    
    This is the preferred initialization entry point for FG processing
    to avoid first-call JIT latency.
    """
    ensure_fields_allocated()
    warmup_kernels()








