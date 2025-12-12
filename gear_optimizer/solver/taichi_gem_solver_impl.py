"""
Legacy Taichi implementation module.

NOTE: The primary (maintained) gem-solver implementation lives in:
    gear_optimizer.solver.taichi_gem

This module is kept only to host the ForceGreatsFinder GPU implementation
while it is being migrated into the modular subpackage.

This module ports the CPU scoring_core.py functions to Taichi kernels:
- lookup_ref: O(1) reference table lookup
- calc_score_device: Score calculation with fever/normal notes
- optimize_core_device: Greedy gem allocation optimizer
- solve_batch_kernel: Main entry point - processes all work items in parallel

Architecture:
    Python (scoring.py) --> load_ref_arrays() --> GPU fields (device-resident)
                       --> optimize_gems_batch_gpu() --> solve_batch_kernel
                       <-- results (score, gem counts)
"""
import taichi as ti
import numpy as np

# Explicitly keep the public surface area minimal to reduce drift.
__all__ = ["solve_force_greats_finder_gpu"]

# ============================================================================
# TAICHI INITIALIZATION
# ============================================================================

_ti_initialized = False


def init_taichi_vulkan():
    """
    Initialize Taichi with Vulkan backend for AMD GPUs.
    
    Called once by gpu_scheduler.py on the GPU thread, or lazily on first use.
    Uses f32 precision for performance (sufficient for score accuracy).
    """
    global _ti_initialized
    if not _ti_initialized:
        # IMPORTANT: Delegate to the modular runtime so the whole codebase shares
        # one initialization path (avoids double-ti.init when both legacy + new
        # code paths are exercised in the same process).
        from .taichi_gem.runtime import init_taichi_vulkan as _init

        _init()
        _ti_initialized = True


# ============================================================================
# GPU FIELDS (Device-resident data)
# ============================================================================

# Reference lookup tables (161 entries each, index 0-160)
ref_pp_field: ti.Field = None
ref_cm_field: ti.Field = None
ref_fm_field: ti.Field = None
ref_ft_field: ti.Field = None  # Fever Time multipliers
ref_ff_field: ti.Field = None  # Fever Fill Rate multipliers

# Timeline grid (161x161 = 26,521 entries per song)
GRID_SIZE = 161
grid_count_body_fever: ti.Field = None   # (161, 161) i32
grid_count_body_normal: ti.Field = None  # (161, 161) i32
grid_head_len: ti.Field = None           # (161, 161) i32
grid_fever_masks: ti.Field = None        # (161, 161, 100) i8 - head masks
grid_fever_masks_bits: ti.Field = None   # (161, 161, 4) u32 - bitpacked head masks (128 bits covers 100 notes)

# MEGA-BATCH work items (max 524k work items for V2 parallel kernel)
MAX_WORK_ITEMS = 524288  # 512k - supports 500 genomes × ~800 FT/FF combinations
MAX_HEAD_NOTES = 100
MAX_GENOMES = 512  # Support up to 512 unique genomes per batch

# ============================================================================
# FORCE GREATs (FG) FINDER GPU CONFIG
# ============================================================================
FG_MAX_SECTIONS = 16
FG_MAX_CONFIGS = 8192
FG_MAX_FTFF = 256
FG_MAX_SONG_NOTES = 200000  # safety cap for timestamps uploaded to GPU

# Song timestamps (GPU-resident; used by FG finder kernel)
song_timestamps: ti.Field = None  # (FG_MAX_SONG_NOTES,) f32

# FG finder inputs (GPU-resident)
fg_forced_counts: ti.Field = None  # (FG_MAX_CONFIGS, FG_MAX_SECTIONS) i32
fg_ft_list: ti.Field = None        # (FG_MAX_FTFF,) i32
fg_ff_list: ti.Field = None        # (FG_MAX_FTFF,) i32

# FG finder outputs (per genome) - final reduction targets
fg_best_final_score: ti.Field = None     # i32
fg_best_base_score: ti.Field = None      # i32
fg_best_cfg_idx: ti.Field = None         # i32 (global cfg index)
fg_best_ft: ti.Field = None              # i32
fg_best_ff: ti.Field = None              # i32
fg_best_g_pp: ti.Field = None            # i32
fg_best_g_cm: ti.Field = None            # i32
fg_best_g_fm: ti.Field = None            # i32
fg_best_g_ov: ti.Field = None            # i32
fg_best_score_penalty: ti.Field = None   # i32
fg_best_fill_penalty: ti.Field = None    # i32 (diagnostic; already reflected in base_score via shifted timeline)

# FG finder intermediate outputs (per genome × ftff) - for two-stage reduction
# Stage 1: Each (genome, ftff) finds best across all cfg_idx (no atomics needed)
# Stage 2: Reduce across ftff to find best per genome
fg_stage1_final_score: ti.Field = None   # (MAX_GENOMES, FG_MAX_FTFF) i32
fg_stage1_base_score: ti.Field = None    # (MAX_GENOMES, FG_MAX_FTFF) i32
fg_stage1_cfg_idx: ti.Field = None       # (MAX_GENOMES, FG_MAX_FTFF) i32
fg_stage1_g_pp: ti.Field = None          # (MAX_GENOMES, FG_MAX_FTFF) i32
fg_stage1_g_cm: ti.Field = None          # (MAX_GENOMES, FG_MAX_FTFF) i32
fg_stage1_g_fm: ti.Field = None          # (MAX_GENOMES, FG_MAX_FTFF) i32
fg_stage1_g_ov: ti.Field = None          # (MAX_GENOMES, FG_MAX_FTFF) i32
fg_stage1_score_penalty: ti.Field = None # (MAX_GENOMES, FG_MAX_FTFF) i32
fg_stage1_fill_penalty: ti.Field = None  # (MAX_GENOMES, FG_MAX_FTFF) i32

fever_masks: ti.Field = None  # (MAX_WORK_ITEMS, MAX_HEAD_NOTES) - i8

# Per-work-item inputs
work_budgets: ti.Field = None
work_count_fever: ti.Field = None
work_count_normal: ti.Field = None
work_ft_gems: ti.Field = None
work_ff_gems: ti.Field = None
work_head_len: ti.Field = None
work_genome_id: ti.Field = None  # Maps work item -> genome index

# Per-genome base stats (lookup by genome_id in kernel)
genome_base_pp: ti.Field = None
genome_base_cm: ti.Field = None
genome_base_fm: ti.Field = None
genome_base_p_val: ti.Field = None
genome_base_s_val: ti.Field = None
genome_base_ft: ti.Field = None  # Base Fever Time stat (for FT/FF iteration)
genome_base_ff: ti.Field = None  # Base Fever Fill Rate stat

# Per-work-item outputs
result_scores: ti.Field = None
result_pp: ti.Field = None
result_cm: ti.Field = None
result_fm: ti.Field = None
result_ov: ti.Field = None
result_p_val: ti.Field = None
result_s_val: ti.Field = None

# Per-genome outputs (for FT/FF iteration kernel)
genome_result_scores: ti.Field = None
genome_result_ft: ti.Field = None
genome_result_ff: ti.Field = None
genome_result_pp: ti.Field = None
genome_result_cm: ti.Field = None
genome_result_fm: ti.Field = None
genome_result_ov: ti.Field = None

_fields_allocated = False
_grid_fields_allocated = False
_last_uploaded_grid_id = None  # Cache to skip redundant grid uploads

# ============================================================================
# NUMPY STAGING BUFFERS (avoid huge per-call allocations)
# ============================================================================
_BATCH_STAGING = None
_MEGA_STAGING = None


def _ensure_batch_staging():
    """
    Allocate and reuse large NumPy staging buffers used by optimize_gems_batch_gpu().

    These buffers are intentionally sized to MAX_WORK_ITEMS so we can upload to
    fixed-shape Taichi fields via from_numpy without reallocating/zeroing tens
    of MB every call.
    """
    global _BATCH_STAGING
    if _BATCH_STAGING is not None:
        return _BATCH_STAGING

    _BATCH_STAGING = {
        "budgets": np.zeros(MAX_WORK_ITEMS, dtype=np.int32),
        "count_fever": np.zeros(MAX_WORK_ITEMS, dtype=np.int32),
        "count_normal": np.zeros(MAX_WORK_ITEMS, dtype=np.int32),
        "ft_gems": np.zeros(MAX_WORK_ITEMS, dtype=np.int32),
        "ff_gems": np.zeros(MAX_WORK_ITEMS, dtype=np.int32),
        "head_len": np.zeros(MAX_WORK_ITEMS, dtype=np.int32),
        "genome_id": np.zeros(MAX_WORK_ITEMS, dtype=np.int32),
        "fever_masks": np.zeros((MAX_WORK_ITEMS, MAX_HEAD_NOTES), dtype=np.int8),
        "genome_pp": np.zeros(MAX_GENOMES, dtype=np.int32),
        "genome_cm": np.zeros(MAX_GENOMES, dtype=np.int32),
        "genome_fm": np.zeros(MAX_GENOMES, dtype=np.int32),
        "genome_p": np.zeros(MAX_GENOMES, dtype=np.int32),
        "genome_s": np.zeros(MAX_GENOMES, dtype=np.int32),
    }
    return _BATCH_STAGING


def _ensure_mega_staging():
    """
    Allocate and reuse large NumPy staging buffers used by mega_batch_solve_population().
    """
    global _MEGA_STAGING
    if _MEGA_STAGING is not None:
        return _MEGA_STAGING

    _MEGA_STAGING = {
        "budgets": np.zeros(MAX_WORK_ITEMS, dtype=np.int32),
        "count_fever": np.zeros(MAX_WORK_ITEMS, dtype=np.int32),
        "count_normal": np.zeros(MAX_WORK_ITEMS, dtype=np.int32),
        "ft_gems": np.zeros(MAX_WORK_ITEMS, dtype=np.int32),
        "ff_gems": np.zeros(MAX_WORK_ITEMS, dtype=np.int32),
        "head_len": np.zeros(MAX_WORK_ITEMS, dtype=np.int32),
        "genome_id": np.zeros(MAX_WORK_ITEMS, dtype=np.int32),
        "fever_masks": np.zeros((MAX_WORK_ITEMS, MAX_HEAD_NOTES), dtype=np.int8),
        "genome_pp": np.zeros(MAX_GENOMES, dtype=np.int32),
        "genome_cm": np.zeros(MAX_GENOMES, dtype=np.int32),
        "genome_fm": np.zeros(MAX_GENOMES, dtype=np.int32),
        "genome_p": np.zeros(MAX_GENOMES, dtype=np.int32),
        "genome_s": np.zeros(MAX_GENOMES, dtype=np.int32),
    }
    return _MEGA_STAGING


def _allocate_fields():
    """Allocate GPU fields. Must be called after ti.init()."""
    global ref_pp_field, ref_cm_field, ref_fm_field, ref_ft_field, ref_ff_field
    global song_timestamps
    global fg_forced_counts, fg_ft_list, fg_ff_list
    global fg_best_final_score, fg_best_base_score, fg_best_cfg_idx, fg_best_ft, fg_best_ff
    global fg_best_g_pp, fg_best_g_cm, fg_best_g_fm, fg_best_g_ov
    global fg_best_score_penalty, fg_best_fill_penalty
    global fg_stage1_final_score, fg_stage1_base_score, fg_stage1_cfg_idx
    global fg_stage1_g_pp, fg_stage1_g_cm, fg_stage1_g_fm, fg_stage1_g_ov
    global fg_stage1_score_penalty, fg_stage1_fill_penalty
    global fever_masks, work_budgets, work_count_fever, work_count_normal
    global work_ft_gems, work_ff_gems, work_head_len, work_genome_id
    global genome_base_pp, genome_base_cm, genome_base_fm, genome_base_p_val, genome_base_s_val
    global genome_base_ft, genome_base_ff
    global result_scores, result_pp, result_cm, result_fm, result_ov
    global result_p_val, result_s_val, _fields_allocated
    global genome_result_scores, genome_result_ft, genome_result_ff
    global genome_result_pp, genome_result_cm, genome_result_fm, genome_result_ov
    
    if _fields_allocated:
        return
    
    # Reference tables (f32 for performance)
    ref_pp_field = ti.field(dtype=ti.f32, shape=161)
    ref_cm_field = ti.field(dtype=ti.f32, shape=161)
    ref_fm_field = ti.field(dtype=ti.f32, shape=161)
    ref_ft_field = ti.field(dtype=ti.f32, shape=161)
    ref_ff_field = ti.field(dtype=ti.f32, shape=161)

    # Song timestamps for FG finder
    song_timestamps = ti.field(dtype=ti.f32, shape=FG_MAX_SONG_NOTES)

    # FG finder inputs
    fg_forced_counts = ti.field(dtype=ti.i32, shape=(FG_MAX_CONFIGS, FG_MAX_SECTIONS))
    fg_ft_list = ti.field(dtype=ti.i32, shape=FG_MAX_FTFF)
    fg_ff_list = ti.field(dtype=ti.i32, shape=FG_MAX_FTFF)

    # FG finder outputs (per genome)
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
    
    # FG Stage 1 intermediate fields (per genome × ftff) for two-stage reduction
    # Eliminates atomic_max contention by giving each (genome, ftff) its own slot
    fg_stage1_final_score = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_MAX_FTFF))
    fg_stage1_base_score = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_MAX_FTFF))
    fg_stage1_cfg_idx = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_MAX_FTFF))
    fg_stage1_g_pp = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_MAX_FTFF))
    fg_stage1_g_cm = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_MAX_FTFF))
    fg_stage1_g_fm = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_MAX_FTFF))
    fg_stage1_g_ov = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_MAX_FTFF))
    fg_stage1_score_penalty = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_MAX_FTFF))
    fg_stage1_fill_penalty = ti.field(dtype=ti.i32, shape=(MAX_GENOMES, FG_MAX_FTFF))
    
    # Work item inputs
    fever_masks = ti.field(dtype=ti.i8, shape=(MAX_WORK_ITEMS, MAX_HEAD_NOTES))
    work_budgets = ti.field(dtype=ti.i32, shape=MAX_WORK_ITEMS)
    work_count_fever = ti.field(dtype=ti.i32, shape=MAX_WORK_ITEMS)
    work_count_normal = ti.field(dtype=ti.i32, shape=MAX_WORK_ITEMS)
    work_ft_gems = ti.field(dtype=ti.i32, shape=MAX_WORK_ITEMS)
    work_ff_gems = ti.field(dtype=ti.i32, shape=MAX_WORK_ITEMS)
    work_head_len = ti.field(dtype=ti.i32, shape=MAX_WORK_ITEMS)
    work_genome_id = ti.field(dtype=ti.i32, shape=MAX_WORK_ITEMS)
    
    # Per-genome base stats (lookup by work_genome_id in kernel)
    genome_base_pp = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    genome_base_cm = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    genome_base_fm = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    genome_base_p_val = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    genome_base_s_val = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    genome_base_ft = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    genome_base_ff = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    
    # Per-work-item results
    result_scores = ti.field(dtype=ti.i32, shape=MAX_WORK_ITEMS)
    result_pp = ti.field(dtype=ti.i32, shape=MAX_WORK_ITEMS)
    result_cm = ti.field(dtype=ti.i32, shape=MAX_WORK_ITEMS)
    result_fm = ti.field(dtype=ti.i32, shape=MAX_WORK_ITEMS)
    result_ov = ti.field(dtype=ti.i32, shape=MAX_WORK_ITEMS)
    result_p_val = ti.field(dtype=ti.i32, shape=MAX_WORK_ITEMS)
    result_s_val = ti.field(dtype=ti.i32, shape=MAX_WORK_ITEMS)
    
    # Per-genome results (for FT/FF iteration kernel)
    genome_result_scores = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    genome_result_ft = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    genome_result_ff = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    genome_result_pp = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    genome_result_cm = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    genome_result_fm = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    genome_result_ov = ti.field(dtype=ti.i32, shape=MAX_GENOMES)
    
    _fields_allocated = True
    print(f"[Taichi] Allocated GPU fields: {MAX_WORK_ITEMS} work items, {MAX_HEAD_NOTES} head notes, {MAX_GENOMES} genomes")


# ============================================================================
# @ti.func IMPLEMENTATIONS (Ported from scoring_core.py)
# ============================================================================

@ti.func
def lookup_ref_pp(value: ti.i32) -> ti.f32:
    """O(1) lookup from Perfect Points reference table. Clamps to [0, 160]."""
    idx = ti.max(0, ti.min(160, value))
    return ref_pp_field[idx]


@ti.func
def lookup_ref_cm(value: ti.i32) -> ti.f32:
    """O(1) lookup from Combo Multiplier reference table. Clamps to [0, 160]."""
    idx = ti.max(0, ti.min(160, value))
    return ref_cm_field[idx]


@ti.func
def lookup_ref_fm(value: ti.i32) -> ti.f32:
    """O(1) lookup from Fever Multiplier reference table. Clamps to [0, 160]."""
    idx = ti.max(0, ti.min(160, value))
    return ref_fm_field[idx]


@ti.func
def lookup_ref_ft(value: ti.i32) -> ti.f32:
    """O(1) lookup from Fever Time reference table. Clamps to [0, 160]."""
    idx = ti.max(0, ti.min(160, value))
    return ref_ft_field[idx]


@ti.func
def lookup_ref_ff(value: ti.i32) -> ti.f32:
    """O(1) lookup from Fever Fill Rate reference table. Clamps to [0, 160]."""
    idx = ti.max(0, ti.min(160, value))
    return ref_ff_field[idx]


@ti.func
def calc_score_device(
    base_value: ti.f32,  # Changed to f32 for performance
    combo_mul: ti.f32,
    fever_mul: ti.f32,
    work_idx: ti.i32,
    head_len: ti.i32,
    count_fever: ti.i32,
    count_normal: ti.i32,
) -> ti.i32:
    """
    GPU port of fast_calculate_score (scoring_core.py:48-96).
    
    Calculates total score by:
    1. Body score: simple multiply (all notes past head at full combo)
    2. Head score: ramped combo scaling for first head_len notes
    
    Args:
        base_value: (primary*2) + secondary + pp_factor
        combo_mul: Combo multiplier from lookup
        fever_mul: Fever multiplier from lookup
        work_idx: Index into fever_masks for this work item
        head_len: Number of notes in the head (<=100)
        count_fever: Fever notes in body
        count_normal: Normal notes in body
        
    Returns:
        Total score as int32
    """
    # Body score (notes 101+) - base_value is already f32
    combo_val = ti.floor(base_value * combo_mul)
    fever_val = ti.floor(base_value * combo_mul * fever_mul)
    
    body_score = (ti.cast(count_fever, ti.f32) * fever_val) + (ti.cast(count_normal, ti.f32) * combo_val)
    
    # Head score (notes 1-100) with ramped combo
    factor = (combo_mul - 1.0) * base_value / 100.0
    head_score = 0.0
    
    for i in range(head_len):
        ramp_val = base_value + (ti.cast(i + 1, ti.f32) * factor)
        if fever_masks[work_idx, i] != 0:
            head_score += ti.floor(ramp_val * fever_mul)
        else:
            head_score += ti.floor(ramp_val)
    
    return ti.cast(body_score + head_score, ti.i32)


@ti.func
def calc_score_bits(
    base_value: ti.f32,
    combo_mul: ti.f32,
    fever_mul: ti.f32,
    m0: ti.u32,
    m1: ti.u32,
    m2: ti.u32,
    m3: ti.u32,
    head_len: ti.i32,
    count_fever: ti.i32,
    count_normal: ti.i32,
) -> ti.i32:
    """
    Score calculation using bitpacked head fever masks (4x u32).
    Intended for FG finder kernel to avoid large head-mask uploads.
    """
    combo_val = ti.floor(base_value * combo_mul)
    fever_val = ti.floor(base_value * combo_mul * fever_mul)
    body_score = (ti.cast(count_fever, ti.f32) * fever_val) + (
        ti.cast(count_normal, ti.f32) * combo_val
    )

    factor = (combo_mul - 1.0) * base_value / 100.0
    head_score = 0.0

    for i in range(head_len):
        ramp_val = base_value + (ti.cast(i + 1, ti.f32) * factor)
        word = i >> 5
        bit = ti.cast(1, ti.u32) << ti.cast(i & 31, ti.u32)
        is_fever = False
        if word == 0:
            is_fever = (m0 & bit) != 0
        elif word == 1:
            is_fever = (m1 & bit) != 0
        elif word == 2:
            is_fever = (m2 & bit) != 0
        else:
            is_fever = (m3 & bit) != 0

        if is_fever:
            head_score += ti.floor(ramp_val * fever_mul)
        else:
            head_score += ti.floor(ramp_val)

    return ti.cast(body_score + head_score, ti.i32)


@ti.func
def _optimize_core_bits(
    budget: ti.i32,
    cur_pp: ti.i32,
    cur_cm: ti.i32,
    cur_fm: ti.i32,
    cur_p_val: ti.i32,
    cur_s_val: ti.i32,
    is_p_pp: ti.i32,
    is_s_pp: ti.i32,
    is_p_cm: ti.i32,
    is_s_cm: ti.i32,
    is_p_fm: ti.i32,
    is_s_fm: ti.i32,
    is_p_ov: ti.i32,
    is_s_ov: ti.i32,
    m0: ti.u32,
    m1: ti.u32,
    m2: ti.u32,
    m3: ti.u32,
    head_len: ti.i32,
    count_fever: ti.i32,
    count_normal: ti.i32,
) -> ti.types.vector(10, ti.i32):
    """
    Greedy gem allocation optimizer (bitmask head scoring).

    Returns vector:
      [score, pp, cm, fm, p_val, s_val, g_pp, g_cm, g_fm, g_ov]
    """
    GEM_SCALE_NORMAL: ti.i32 = 2
    GEM_SCALE_FEVER: ti.i32 = 3
    ELEMENTAL_GEM_SCALE: ti.i32 = 6
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160
    PP_TIE_LOOKAHEAD_MAX: ti.i32 = 8

    gems_pp: ti.i32 = 0
    gems_cm: ti.i32 = 0
    gems_fm: ti.i32 = 0
    gems_ov: ti.i32 = 0
    remaining: ti.i32 = budget

    pp: ti.i32 = cur_pp
    cm: ti.i32 = cur_cm
    fm: ti.i32 = cur_fm
    p_val: ti.i32 = cur_p_val
    s_val: ti.i32 = cur_s_val

    best_final_score: ti.i32 = 0

    while remaining > 0:
        fill_budget: ti.i32 = remaining - 1
        fill_bonus: ti.i32 = fill_budget * ELEMENTAL_GEM_SCALE if fill_budget > 0 else 0

        c_mul_cur: ti.f32 = lookup_ref_cm(cm)
        f_mul_cur: ti.f32 = lookup_ref_fm(fm)

        # OV wins exact ties by default
        t_p: ti.i32 = p_val + (ELEMENTAL_GEM_SCALE * is_p_ov) + (fill_bonus * is_p_ov)
        t_s: ti.i32 = s_val + (ELEMENTAL_GEM_SCALE * is_s_ov) + (fill_bonus * is_s_ov)
        pp_factor: ti.f32 = lookup_ref_pp(pp)
        base: ti.f32 = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
        best_score: ti.i32 = calc_score_bits(
            base, c_mul_cur, f_mul_cur, m0, m1, m2, m3, head_len, count_fever, count_normal
        )
        best_opt: ti.i32 = 3

        pp_score: ti.i32 = -1

        # PP gem
        if pp < MAX_STAT:
            t_pp: ti.i32 = pp + GEM_SCALE_NORMAL
            t_p = p_val + (GEM_STAT_TO_ELEMENT * is_p_pp) + (fill_bonus * is_p_ov)
            t_s = s_val + (GEM_STAT_TO_ELEMENT * is_s_pp) + (fill_bonus * is_s_ov)
            pp_factor = lookup_ref_pp(t_pp)
            base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
            pp_score = calc_score_bits(
                base, c_mul_cur, f_mul_cur, m0, m1, m2, m3, head_len, count_fever, count_normal
            )
            if pp_score > best_score:
                best_score = pp_score
                best_opt = 0

        # CM gem
        if cm < MAX_STAT:
            t_cm: ti.i32 = cm + GEM_SCALE_NORMAL
            t_p = p_val + (GEM_STAT_TO_ELEMENT * is_p_cm) + (fill_bonus * is_p_ov)
            t_s = s_val + (GEM_STAT_TO_ELEMENT * is_s_cm) + (fill_bonus * is_s_ov)
            pp_factor = lookup_ref_pp(pp)
            base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
            c_mul: ti.f32 = lookup_ref_cm(t_cm)
            score: ti.i32 = calc_score_bits(
                base, c_mul, f_mul_cur, m0, m1, m2, m3, head_len, count_fever, count_normal
            )
            if score > best_score:
                best_score = score
                best_opt = 1

        # FM gem
        if fm < MAX_STAT:
            t_fm: ti.i32 = fm + GEM_SCALE_FEVER
            t_p = p_val + (GEM_STAT_TO_ELEMENT * is_p_fm) + (fill_bonus * is_p_ov)
            t_s = s_val + (GEM_STAT_TO_ELEMENT * is_s_fm) + (fill_bonus * is_s_ov)
            pp_factor = lookup_ref_pp(pp)
            base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
            f_mul: ti.f32 = lookup_ref_fm(t_fm)
            score = calc_score_bits(
                base, c_mul_cur, f_mul, m0, m1, m2, m3, head_len, count_fever, count_normal
            )
            if score > best_score:
                best_score = score
                best_opt = 2

        # PP lookahead (optional)
        if best_opt == 3 and pp_score == best_score and remaining > 1:
            max_k: ti.i32 = remaining
            if max_k > PP_TIE_LOOKAHEAD_MAX:
                max_k = PP_TIE_LOOKAHEAD_MAX
            k: ti.i32 = 2
            while k <= max_k:
                fill_bonus_k: ti.i32 = (remaining - k) * ELEMENTAL_GEM_SCALE
                t_pp: ti.i32 = pp + (k * GEM_SCALE_NORMAL)
                t_p = p_val + (k * GEM_STAT_TO_ELEMENT * is_p_pp) + (fill_bonus_k * is_p_ov)
                t_s = s_val + (k * GEM_STAT_TO_ELEMENT * is_s_pp) + (fill_bonus_k * is_s_ov)
                pp_factor = lookup_ref_pp(t_pp)
                base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                score_k: ti.i32 = calc_score_bits(
                    base, c_mul_cur, f_mul_cur, m0, m1, m2, m3, head_len, count_fever, count_normal
                )
                if score_k > best_score:
                    best_opt = 0
                    break
                k += 1

        # Apply best option
        if best_opt == 0:
            pp += GEM_SCALE_NORMAL
            p_val += GEM_STAT_TO_ELEMENT * is_p_pp
            s_val += GEM_STAT_TO_ELEMENT * is_s_pp
            gems_pp += 1
        elif best_opt == 1:
            cm += GEM_SCALE_NORMAL
            p_val += GEM_STAT_TO_ELEMENT * is_p_cm
            s_val += GEM_STAT_TO_ELEMENT * is_s_cm
            gems_cm += 1
        elif best_opt == 2:
            fm += GEM_SCALE_FEVER
            p_val += GEM_STAT_TO_ELEMENT * is_p_fm
            s_val += GEM_STAT_TO_ELEMENT * is_s_fm
            gems_fm += 1
        else:
            p_val += ELEMENTAL_GEM_SCALE * is_p_ov
            s_val += ELEMENTAL_GEM_SCALE * is_s_ov
            gems_ov += 1

        remaining -= 1
        best_final_score = best_score

    return ti.Vector([
        best_final_score,
        pp, cm, fm,
        p_val, s_val,
        gems_pp, gems_cm, gems_fm, gems_ov,
    ])


@ti.func
def optimize_core_device(
    work_idx: ti.i32,
    budget: ti.i32,
    cur_pp: ti.i32,
    cur_cm: ti.i32,
    cur_fm: ti.i32,
    cur_p_val: ti.i32,
    cur_s_val: ti.i32,
    is_p_pp: ti.i32, is_s_pp: ti.i32,
    is_p_cm: ti.i32, is_s_cm: ti.i32,
    is_p_fm: ti.i32, is_s_fm: ti.i32,
    is_p_ov: ti.i32, is_s_ov: ti.i32,
    head_len: ti.i32,
    count_fever: ti.i32,
    count_normal: ti.i32,
) -> ti.i32:
    """
    GPU port of optimize_core_jit (scoring_core.py:99-278).
    
    Greedy gem allocation: at each iteration, evaluates 4 options:
    - PP gem (Perfect Points)
    - CM gem (Combo Multiplier)
    - FM gem (Fever Multiplier)
    - OV gem (Overflow/Elemental)
    
    Picks the option that maximizes score. Repeats until budget exhausted.
    
    Returns:
        Best final score after gem allocation
    """
    # Constants (matching constants.py)
    GEM_SCALE_NORMAL: ti.i32 = 2
    GEM_SCALE_FEVER: ti.i32 = 3
    ELEMENTAL_GEM_SCALE: ti.i32 = 6
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160
    
    gems_pp: ti.i32 = 0
    gems_cm: ti.i32 = 0
    gems_fm: ti.i32 = 0
    gems_ov: ti.i32 = 0
    remaining: ti.i32 = budget
    PP_TIE_LOOKAHEAD_MAX: ti.i32 = 8
    
    # Mutable state
    pp: ti.i32 = cur_pp
    cm: ti.i32 = cur_cm
    fm: ti.i32 = cur_fm
    p_val: ti.i32 = cur_p_val
    s_val: ti.i32 = cur_s_val
    
    best_final_score: ti.i32 = 0
    
    while remaining > 0:
        fill_budget: ti.i32 = remaining - 1
        fill_bonus: ti.i32 = fill_budget * ELEMENTAL_GEM_SCALE if fill_budget > 0 else 0

        # Precompute current multipliers (unchanged for PP/OV checks)
        c_mul_cur: ti.f32 = lookup_ref_cm(cm)
        f_mul_cur: ti.f32 = lookup_ref_fm(fm)

        # Start with OV as default so OV wins exact ties.
        t_p: ti.i32 = p_val + (ELEMENTAL_GEM_SCALE * is_p_ov) + (fill_bonus * is_p_ov)
        t_s: ti.i32 = s_val + (ELEMENTAL_GEM_SCALE * is_s_ov) + (fill_bonus * is_s_ov)
        pp_factor: ti.f32 = lookup_ref_pp(pp)
        base: ti.f32 = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
        best_score: ti.i32 = calc_score_device(base, c_mul_cur, f_mul_cur, work_idx, head_len, count_fever, count_normal)
        best_opt: ti.i32 = 3

        pp_score: ti.i32 = -1

        # Option 0: PP gem
        if pp < MAX_STAT:
            t_pp: ti.i32 = pp + GEM_SCALE_NORMAL
            t_p = p_val + (GEM_STAT_TO_ELEMENT * is_p_pp) + (fill_bonus * is_p_ov)
            t_s = s_val + (GEM_STAT_TO_ELEMENT * is_s_pp) + (fill_bonus * is_s_ov)
            pp_factor = lookup_ref_pp(t_pp)
            base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
            pp_score = calc_score_device(base, c_mul_cur, f_mul_cur, work_idx, head_len, count_fever, count_normal)
            if pp_score > best_score:
                best_score = pp_score
                best_opt = 0

        # Option 1: CM gem
        if cm < MAX_STAT:
            t_cm: ti.i32 = cm + GEM_SCALE_NORMAL
            t_p = p_val + (GEM_STAT_TO_ELEMENT * is_p_cm) + (fill_bonus * is_p_ov)
            t_s = s_val + (GEM_STAT_TO_ELEMENT * is_s_cm) + (fill_bonus * is_s_ov)
            pp_factor = lookup_ref_pp(pp)
            base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
            c_mul: ti.f32 = lookup_ref_cm(t_cm)
            score: ti.i32 = calc_score_device(base, c_mul, f_mul_cur, work_idx, head_len, count_fever, count_normal)
            if score > best_score:
                best_score = score
                best_opt = 1

        # Option 2: FM gem
        if fm < MAX_STAT:
            t_fm: ti.i32 = fm + GEM_SCALE_FEVER
            t_p = p_val + (GEM_STAT_TO_ELEMENT * is_p_fm) + (fill_bonus * is_p_ov)
            t_s = s_val + (GEM_STAT_TO_ELEMENT * is_s_fm) + (fill_bonus * is_s_ov)
            pp_factor = lookup_ref_pp(pp)
            base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
            f_mul: ti.f32 = lookup_ref_fm(t_fm)
            score = calc_score_device(base, c_mul_cur, f_mul, work_idx, head_len, count_fever, count_normal)
            if score > best_score:
                best_score = score
                best_opt = 2

        # PP lookahead: if OV wins a tie now, but a few PP gems would become a real
        # improvement soon, start investing in PP.
        if best_opt == 3 and pp_score == best_score and remaining > 1:
            max_k: ti.i32 = remaining
            if max_k > PP_TIE_LOOKAHEAD_MAX:
                max_k = PP_TIE_LOOKAHEAD_MAX
            k: ti.i32 = 2
            while k <= max_k:
                fill_bonus_k: ti.i32 = (remaining - k) * ELEMENTAL_GEM_SCALE
                t_pp: ti.i32 = pp + (k * GEM_SCALE_NORMAL)
                t_p = p_val + (k * GEM_STAT_TO_ELEMENT * is_p_pp) + (fill_bonus_k * is_p_ov)
                t_s = s_val + (k * GEM_STAT_TO_ELEMENT * is_s_pp) + (fill_bonus_k * is_s_ov)
                pp_factor = lookup_ref_pp(t_pp)
                base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                score_k: ti.i32 = calc_score_device(base, c_mul_cur, f_mul_cur, work_idx, head_len, count_fever, count_normal)
                if score_k > best_score:
                    best_opt = 0
                    break
                k += 1
        
        # Apply best option
        if best_opt == 0:
            pp += GEM_SCALE_NORMAL
            p_val += GEM_STAT_TO_ELEMENT * is_p_pp
            s_val += GEM_STAT_TO_ELEMENT * is_s_pp
            gems_pp += 1
        elif best_opt == 1:
            cm += GEM_SCALE_NORMAL
            p_val += GEM_STAT_TO_ELEMENT * is_p_cm
            s_val += GEM_STAT_TO_ELEMENT * is_s_cm
            gems_cm += 1
        elif best_opt == 2:
            fm += GEM_SCALE_FEVER
            p_val += GEM_STAT_TO_ELEMENT * is_p_fm
            s_val += GEM_STAT_TO_ELEMENT * is_s_fm
            gems_fm += 1
        else:
            p_val += ELEMENTAL_GEM_SCALE * is_p_ov
            s_val += ELEMENTAL_GEM_SCALE * is_s_ov
            gems_ov += 1
        
        remaining -= 1
        best_final_score = best_score
    
    # Store results in output fields
    result_pp[work_idx] = gems_pp
    result_cm[work_idx] = gems_cm
    result_fm[work_idx] = gems_fm
    result_ov[work_idx] = gems_ov
    result_p_val[work_idx] = p_val
    result_s_val[work_idx] = s_val
    
    return best_final_score


# ============================================================================
# @ti.kernel ENTRY POINTS
# ============================================================================

@ti.kernel
def solve_batch_kernel(
    n_items: ti.i32,
    is_p_ft: ti.i32, is_s_ft: ti.i32,
    is_p_ff: ti.i32, is_s_ff: ti.i32,
    is_p_pp: ti.i32, is_s_pp: ti.i32,
    is_p_cm: ti.i32, is_s_cm: ti.i32,
    is_p_fm: ti.i32, is_s_fm: ti.i32,
    is_p_ov: ti.i32, is_s_ov: ti.i32,
):
    """
    Main kernel - processes all work items in parallel.
    
    Each work item represents one (FT_gems, FF_gems) timeline combination
    for one genome. The kernel parallelizes across all work items.
    
    Per-genome base stats are looked up from genome_base_* fields using
    work_genome_id mapping (fixes per-genome stats bug).
    
    Args:
        n_items: Number of work items to process
        is_*: Boolean flags (0/1) for color contributions
    """
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    
    for i in range(n_items):
        budget: ti.i32 = work_budgets[i]
        count_fever: ti.i32 = work_count_fever[i]
        count_normal: ti.i32 = work_count_normal[i]
        ft_gems: ti.i32 = work_ft_gems[i]
        ff_gems: ti.i32 = work_ff_gems[i]
        head_len: ti.i32 = work_head_len[i]
        
        # Look up per-genome base stats (fixes the per-genome stats bug!)
        genome_id: ti.i32 = work_genome_id[i]
        base_pp: ti.i32 = genome_base_pp[genome_id]
        base_cm: ti.i32 = genome_base_cm[genome_id]
        base_fm: ti.i32 = genome_base_fm[genome_id]
        base_p_val: ti.i32 = genome_base_p_val[genome_id]
        base_s_val: ti.i32 = genome_base_s_val[genome_id]
        
        # Adjust base p/s values for FT/FF gem contributions to elemental stats
        # FT gems add to Beat (is_p_ft/is_s_ft tells us if Beat is primary/secondary)
        # FF gems add to Vibe (is_p_ff/is_s_ff tells us if Vibe is primary/secondary)
        p_val: ti.i32 = base_p_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff_gems * GEM_STAT_TO_ELEMENT * is_p_ff)
        s_val: ti.i32 = base_s_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff_gems * GEM_STAT_TO_ELEMENT * is_s_ff)
        
        score: ti.i32 = optimize_core_device(
            i, budget,
            base_pp, base_cm, base_fm,
            p_val, s_val,
            is_p_pp, is_s_pp,
            is_p_cm, is_s_cm,
            is_p_fm, is_s_fm,
            is_p_ov, is_s_ov,
            head_len, count_fever, count_normal,
        )
        result_scores[i] = score


def _allocate_grid_fields():
    """Allocate GPU fields for timeline grid. Must be called after ti.init()."""
    global grid_count_body_fever, grid_count_body_normal, grid_head_len, grid_fever_masks, grid_fever_masks_bits
    global _grid_fields_allocated
    
    if _grid_fields_allocated:
        return
    
    # Timeline grid (161x161 = 26,521 entries)
    grid_count_body_fever = ti.field(dtype=ti.i32, shape=(GRID_SIZE, GRID_SIZE))
    grid_count_body_normal = ti.field(dtype=ti.i32, shape=(GRID_SIZE, GRID_SIZE))
    grid_head_len = ti.field(dtype=ti.i32, shape=(GRID_SIZE, GRID_SIZE))
    grid_fever_masks = ti.field(dtype=ti.i8, shape=(GRID_SIZE, GRID_SIZE, MAX_HEAD_NOTES))
    grid_fever_masks_bits = ti.field(dtype=ti.u32, shape=(GRID_SIZE, GRID_SIZE, 4))
    
    _grid_fields_allocated = True
    print(f"[Taichi] Allocated grid fields: {GRID_SIZE}x{GRID_SIZE} timeline grid")


@ti.kernel
def solve_genomes_with_ftff_kernel(
    n_genomes: ti.i32,
    total_budget: ti.i32,
    gem_scale_fever: ti.i32,
    is_p_ft: ti.i32, is_s_ft: ti.i32,
    is_p_ff: ti.i32, is_s_ff: ti.i32,
    is_p_pp: ti.i32, is_s_pp: ti.i32,
    is_p_cm: ti.i32, is_s_cm: ti.i32,
    is_p_fm: ti.i32, is_s_fm: ti.i32,
    is_p_ov: ti.i32, is_s_ov: ti.i32,
):
    """
    New kernel that iterates FT/FF combinations INSIDE the GPU thread.
    
    Each thread handles one genome and iterates through all valid FT/FF
    combinations, using the preloaded timeline grid for O(1) lookups.
    
    This eliminates ~400k work item transfers per generation.
    
    Args:
        n_genomes: Number of genomes to process
        total_budget: Total gem budget (typically 90)
        gem_scale_fever: Gems per fever stat point (typically 3)
        is_*: Color contribution flags (0/1)
    """
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160
    
    for genome_idx in range(n_genomes):
        # Load genome base stats
        base_pp: ti.i32 = genome_base_pp[genome_idx]
        base_cm: ti.i32 = genome_base_cm[genome_idx]
        base_fm: ti.i32 = genome_base_fm[genome_idx]
        base_p_val: ti.i32 = genome_base_p_val[genome_idx]
        base_s_val: ti.i32 = genome_base_s_val[genome_idx]
        base_ft_stat: ti.i32 = genome_base_ft[genome_idx]
        base_ff_stat: ti.i32 = genome_base_ff[genome_idx]
        
        # Compute max FT/FF gems based on stat headroom
        remaining_ft = MAX_STAT - base_ft_stat
        remaining_ff = MAX_STAT - base_ff_stat
        max_ft_gems: ti.i32 = remaining_ft // gem_scale_fever if remaining_ft > 0 else 0
        max_ff_gems: ti.i32 = remaining_ff // gem_scale_fever if remaining_ff > 0 else 0
        
        # Track best result across all FT/FF combinations
        best_score: ti.i32 = -1
        best_ft: ti.i32 = 0
        best_ff: ti.i32 = 0
        best_g_pp: ti.i32 = 0
        best_g_cm: ti.i32 = 0
        best_g_fm: ti.i32 = 0
        best_g_ov: ti.i32 = 0
        
        # Iterate all valid FT/FF combinations
        for ft in range(ti.min(total_budget, max_ft_gems) + 1):
            remaining_for_ff: ti.i32 = total_budget - ft
            
            for ff in range(ti.min(remaining_for_ff, max_ff_gems) + 1):
                # Compute stat indices for grid lookup
                ft_stat_val: ti.i32 = base_ft_stat + (ft * gem_scale_fever)
                ff_stat_val: ti.i32 = base_ff_stat + (ff * gem_scale_fever)
                ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
                ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))
                
                # O(1) lookup from grid
                count_fever: ti.i32 = grid_count_body_fever[ft_idx, ff_idx]
                count_normal: ti.i32 = grid_count_body_normal[ft_idx, ff_idx]
                head_len: ti.i32 = grid_head_len[ft_idx, ff_idx]
                
                # Budget remaining for PP/CM/FM/OV gems
                budget: ti.i32 = total_budget - ft - ff
                
                # Adjust p/s values for FT/FF gem contributions
                p_val: ti.i32 = base_p_val + (ft * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff * GEM_STAT_TO_ELEMENT * is_p_ff)
                s_val: ti.i32 = base_s_val + (ft * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff * GEM_STAT_TO_ELEMENT * is_s_ff)
                
                # Run greedy gem allocation (inlined optimize_core_device variant)
                # We can't call optimize_core_device because it stores to work_item arrays
                gems_pp: ti.i32 = 0
                gems_cm: ti.i32 = 0
                gems_fm: ti.i32 = 0
                gems_ov: ti.i32 = 0
                cur_pp: ti.i32 = base_pp
                cur_cm: ti.i32 = base_cm
                cur_fm: ti.i32 = base_fm
                cur_p: ti.i32 = p_val
                cur_s: ti.i32 = s_val
                cur_remaining: ti.i32 = budget
                local_best_score: ti.i32 = 0
                PP_TIE_LOOKAHEAD_MAX: ti.i32 = 8
                
                GEM_SCALE_NORMAL: ti.i32 = 2
                GEM_SCALE_FEVER_LOCAL: ti.i32 = 3
                ELEMENTAL_GEM_SCALE: ti.i32 = 6
                
                while cur_remaining > 0:
                    fill_budget: ti.i32 = cur_remaining - 1
                    fill_bonus: ti.i32 = fill_budget * ELEMENTAL_GEM_SCALE if fill_budget > 0 else 0

                    # Precompute current multipliers (unchanged for PP/OV checks)
                    c_mul_cur: ti.f32 = lookup_ref_cm(cur_cm)
                    f_mul_cur: ti.f32 = lookup_ref_fm(cur_fm)

                    # Start with OV as default so OV wins exact ties.
                    t_p: ti.i32 = cur_p + (ELEMENTAL_GEM_SCALE * is_p_ov) + (fill_bonus * is_p_ov)
                    t_s: ti.i32 = cur_s + (ELEMENTAL_GEM_SCALE * is_s_ov) + (fill_bonus * is_s_ov)
                    pp_factor: ti.f32 = lookup_ref_pp(cur_pp)
                    base_val: ti.f32 = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                    best_opt_score: ti.i32 = calc_score_with_grid(base_val, c_mul_cur, f_mul_cur, ft_idx, ff_idx, head_len, count_fever, count_normal)
                    best_opt: ti.i32 = 3

                    pp_score: ti.i32 = -1

                    # Option 0: PP gem
                    if cur_pp < MAX_STAT:
                        t_pp: ti.i32 = cur_pp + GEM_SCALE_NORMAL
                        t_p = cur_p + (GEM_STAT_TO_ELEMENT * is_p_pp) + (fill_bonus * is_p_ov)
                        t_s = cur_s + (GEM_STAT_TO_ELEMENT * is_s_pp) + (fill_bonus * is_s_ov)
                        pp_factor = lookup_ref_pp(t_pp)
                        base_val = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                        pp_score = calc_score_with_grid(base_val, c_mul_cur, f_mul_cur, ft_idx, ff_idx, head_len, count_fever, count_normal)
                        if pp_score > best_opt_score:
                            best_opt_score = pp_score
                            best_opt = 0

                    # Option 1: CM gem
                    if cur_cm < MAX_STAT:
                        t_cm: ti.i32 = cur_cm + GEM_SCALE_NORMAL
                        t_p = cur_p + (GEM_STAT_TO_ELEMENT * is_p_cm) + (fill_bonus * is_p_ov)
                        t_s = cur_s + (GEM_STAT_TO_ELEMENT * is_s_cm) + (fill_bonus * is_s_ov)
                        pp_factor = lookup_ref_pp(cur_pp)
                        base_val = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                        c_mul: ti.f32 = lookup_ref_cm(t_cm)
                        score: ti.i32 = calc_score_with_grid(base_val, c_mul, f_mul_cur, ft_idx, ff_idx, head_len, count_fever, count_normal)
                        if score > best_opt_score:
                            best_opt_score = score
                            best_opt = 1

                    # Option 2: FM gem
                    if cur_fm < MAX_STAT:
                        t_fm: ti.i32 = cur_fm + GEM_SCALE_FEVER_LOCAL
                        t_p = cur_p + (GEM_STAT_TO_ELEMENT * is_p_fm) + (fill_bonus * is_p_ov)
                        t_s = cur_s + (GEM_STAT_TO_ELEMENT * is_s_fm) + (fill_bonus * is_s_ov)
                        pp_factor = lookup_ref_pp(cur_pp)
                        base_val = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                        f_mul: ti.f32 = lookup_ref_fm(t_fm)
                        score = calc_score_with_grid(base_val, c_mul_cur, f_mul, ft_idx, ff_idx, head_len, count_fever, count_normal)
                        if score > best_opt_score:
                            best_opt_score = score
                            best_opt = 2

                    # PP lookahead: if OV wins a tie now, but a few PP gems would become a real
                    # improvement soon, start investing in PP.
                    if best_opt == 3 and pp_score == best_opt_score and cur_remaining > 1:
                        max_k: ti.i32 = cur_remaining
                        if max_k > PP_TIE_LOOKAHEAD_MAX:
                            max_k = PP_TIE_LOOKAHEAD_MAX
                        k: ti.i32 = 2
                        while k <= max_k:
                            fill_bonus_k: ti.i32 = (cur_remaining - k) * ELEMENTAL_GEM_SCALE
                            t_pp: ti.i32 = cur_pp + (k * GEM_SCALE_NORMAL)
                            t_p = cur_p + (k * GEM_STAT_TO_ELEMENT * is_p_pp) + (fill_bonus_k * is_p_ov)
                            t_s = cur_s + (k * GEM_STAT_TO_ELEMENT * is_s_pp) + (fill_bonus_k * is_s_ov)
                            pp_factor = lookup_ref_pp(t_pp)
                            base_val = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                            score_k: ti.i32 = calc_score_with_grid(base_val, c_mul_cur, f_mul_cur, ft_idx, ff_idx, head_len, count_fever, count_normal)
                            if score_k > best_opt_score:
                                best_opt = 0
                                break
                            k += 1
                    
                    # Apply best option
                    if best_opt == 0:
                        cur_pp += GEM_SCALE_NORMAL
                        cur_p += GEM_STAT_TO_ELEMENT * is_p_pp
                        cur_s += GEM_STAT_TO_ELEMENT * is_s_pp
                        gems_pp += 1
                    elif best_opt == 1:
                        cur_cm += GEM_SCALE_NORMAL
                        cur_p += GEM_STAT_TO_ELEMENT * is_p_cm
                        cur_s += GEM_STAT_TO_ELEMENT * is_s_cm
                        gems_cm += 1
                    elif best_opt == 2:
                        cur_fm += GEM_SCALE_FEVER_LOCAL
                        cur_p += GEM_STAT_TO_ELEMENT * is_p_fm
                        cur_s += GEM_STAT_TO_ELEMENT * is_s_fm
                        gems_fm += 1
                    else:
                        cur_p += ELEMENTAL_GEM_SCALE * is_p_ov
                        cur_s += ELEMENTAL_GEM_SCALE * is_s_ov
                        gems_ov += 1
                    
                    cur_remaining -= 1
                    local_best_score = best_opt_score
                
                # Check if this FT/FF combo is better
                if local_best_score > best_score:
                    best_score = local_best_score
                    best_ft = ft
                    best_ff = ff
                    best_g_pp = gems_pp
                    best_g_cm = gems_cm
                    best_g_fm = gems_fm
                    best_g_ov = gems_ov
        
        # Store best result for this genome
        genome_result_scores[genome_idx] = best_score
        genome_result_ft[genome_idx] = best_ft
        genome_result_ff[genome_idx] = best_ff
        genome_result_pp[genome_idx] = best_g_pp
        genome_result_cm[genome_idx] = best_g_cm
        genome_result_fm[genome_idx] = best_g_fm
        genome_result_ov[genome_idx] = best_g_ov


# ============================================================================
# FORCE GREATs (FG) FINDER - FULL GPU PATH
# ============================================================================

@ti.func
def _searchsorted_left_timestamps(
    n_notes: ti.i32,
    x: ti.f32,
    lo: ti.i32,
) -> ti.i32:
    """
    searchsorted(side='left') for the global song_timestamps field.
    Returns the first index i in [lo, n_notes] with song_timestamps[i] >= x.
    """
    l = lo
    r = n_notes
    while l < r:
        mid = (l + r) >> 1
        if song_timestamps[mid] < x:
            l = mid + 1
        else:
            r = mid
    return l


@ti.kernel
def fg_reset_best_kernel(n_genomes: ti.i32):
    for i in range(n_genomes):
        fg_best_final_score[i] = -1
        fg_best_base_score[i] = 0
        fg_best_cfg_idx[i] = -1
        fg_best_ft[i] = 0
        fg_best_ff[i] = 0
        fg_best_g_pp[i] = 0
        fg_best_g_cm[i] = 0
        fg_best_g_fm[i] = 0
        fg_best_g_ov[i] = 0
        fg_best_score_penalty[i] = 0
        fg_best_fill_penalty[i] = 0


@ti.kernel
def solve_force_greats_finder_kernel(
    n_genomes: ti.i32,
    total_notes: ti.i32,
    long_notes: ti.i32,
    last_note_time: ti.f32,
    total_budget: ti.i32,
    gem_scale_fever: ti.i32,
    n_cfg: ti.i32,
    n_sections: ti.i32,
    n_ftff: ti.i32,
    cfg_offset: ti.i32,
    is_p_ft: ti.i32, is_s_ft: ti.i32,
    is_p_ff: ti.i32, is_s_ff: ti.i32,
    is_p_pp: ti.i32, is_s_pp: ti.i32,
    is_p_cm: ti.i32, is_s_cm: ti.i32,
    is_p_fm: ti.i32, is_s_fm: ti.i32,
    is_p_ov: ti.i32, is_s_ov: ti.i32,
):
    """
    Full GPU ForceGreatsFinder:
    - Builds FG timeline (head mask bits + body counts)
    - Runs greedy gem optimizer
    - Computes fill+score penalties (including ramp up to 100 notes)
    - Reduces to best candidate per genome
    """
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    ELEMENTAL_GEM_SCALE: ti.i32 = 6
    MAX_STAT: ti.i32 = 160

    head_len: ti.i32 = ti.min(total_notes, 100)

    non_fever_cas: ti.f32 = ti.max(0.0, (ti.cast(total_notes - long_notes, ti.f32) * 0.333))
    fever_time_cas: ti.f32 = last_note_time * 0.15 + 0.15

    for g, cfg_idx, ftff_idx in ti.ndrange(n_genomes, n_cfg, n_ftff):
        ft_gems: ti.i32 = fg_ft_list[ftff_idx]
        ff_gems: ti.i32 = fg_ff_list[ftff_idx]
        if ft_gems + ff_gems > total_budget:
            continue

        # Load genome base stats
        base_pp: ti.i32 = genome_base_pp[g]
        base_cm: ti.i32 = genome_base_cm[g]
        base_fm: ti.i32 = genome_base_fm[g]
        base_p_val: ti.i32 = genome_base_p_val[g]
        base_s_val: ti.i32 = genome_base_s_val[g]
        base_ft_stat: ti.i32 = genome_base_ft[g]
        base_ff_stat: ti.i32 = genome_base_ff[g]

        # Fever multipliers for this FT/FF (clamp to stat index)
        ft_stat_val: ti.i32 = base_ft_stat + (ft_gems * gem_scale_fever)
        ff_stat_val: ti.i32 = base_ff_stat + (ff_gems * gem_scale_fever)
        ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
        ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))
        ft_factor: ti.f32 = lookup_ref_ft(ft_idx)
        ff_factor: ti.f32 = lookup_ref_ff(ff_idx)

        # Fever parameters
        non_fever_base: ti.i32 = ti.cast(ti.ceil(non_fever_cas * ff_factor), ti.i32)
        non_fever_great_to_fill: ti.i32 = ti.cast(
            ti.ceil(ti.max(1.0, non_fever_cas * ff_factor * 2.0)),
            ti.i32,
        )
        real_fever_time: ti.f32 = fever_time_cas * ft_factor

        # Timeline simulation -> head mask bits + body fever count
        m0 = ti.cast(0, ti.u32)
        m1 = ti.cast(0, ti.u32)
        m2 = ti.cast(0, ti.u32)
        m3 = ti.cast(0, ti.u32)
        body_fever: ti.i32 = 0

        # Store section info only for configured sections
        start_idx = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
        forced_applied = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
        fill_notes = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
        skip_wasted = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)

        current_idx: ti.i32 = 0
        sec: ti.i32 = 0
        while current_idx < total_notes:
            # Non-fever section
            base_notes: ti.i32 = non_fever_base - 1 if sec == 0 else non_fever_base
            if base_notes < 0:
                base_notes = 0

            forced_val: ti.i32 = 0
            if sec < n_sections:
                forced_val = fg_forced_counts[cfg_idx, sec]
                if forced_val < 0:
                    forced_val = 0
                forced_val = ti.min(forced_val, non_fever_base)

            fp: ti.i32 = 0
            if forced_val > 0:
                fp = ti.cast(
                    ti.ceil(
                        ti.max(
                            0.0,
                            (ti.cast(non_fever_base * forced_val, ti.f32) / ti.cast(non_fever_great_to_fill, ti.f32)),
                        )
                    ),
                    ti.i32,
                )

            notes_to_fill: ti.i32 = base_notes + fp
            section_start: ti.i32 = current_idx
            end_normal: ti.i32 = ti.min(total_notes, section_start + notes_to_fill)
            actual_notes: ti.i32 = ti.max(0, end_normal - section_start)
            forced_app: ti.i32 = ti.min(forced_val, actual_notes)

            if sec < n_sections and sec < FG_MAX_SECTIONS:
                start_idx[sec] = section_start
                forced_applied[sec] = forced_app
                fill_notes[sec] = fp
                skip_wasted[sec] = 1 if sec == 0 else 0

            current_idx = end_normal
            if current_idx >= total_notes:
                break

            # Fever section
            start_time: ti.f32 = song_timestamps[current_idx]
            end_time: ti.f32 = start_time + real_fever_time
            fever_end_idx: ti.i32 = _searchsorted_left_timestamps(total_notes, end_time, current_idx)
            if fever_end_idx <= current_idx:
                fever_end_idx = ti.min(total_notes, current_idx + 1)

            # Mark head fever notes (bitset)
            if current_idx < head_len:
                head_end = ti.min(head_len, fever_end_idx)
                for i in range(current_idx, head_end):
                    word = i >> 5
                    bit = ti.cast(1, ti.u32) << ti.cast(i & 31, ti.u32)
                    if word == 0:
                        m0 |= bit
                    elif word == 1:
                        m1 |= bit
                    elif word == 2:
                        m2 |= bit
                    else:
                        m3 |= bit

            # Count body fever notes
            if fever_end_idx > head_len:
                body_start = head_len if current_idx < head_len else current_idx
                if fever_end_idx > body_start:
                    body_fever += (fever_end_idx - body_start)

            current_idx = fever_end_idx
            sec += 1

        body_len = ti.max(total_notes - head_len, 0)
        body_normal: ti.i32 = ti.max(body_len - body_fever, 0)

        # Run greedy gem optimizer with remaining budget
        budget: ti.i32 = total_budget - ft_gems - ff_gems
        if budget < 0:
            continue

        # Apply FT/FF elemental contributions to p/s values
        p_val: ti.i32 = base_p_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff_gems * GEM_STAT_TO_ELEMENT * is_p_ff)
        s_val: ti.i32 = base_s_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff_gems * GEM_STAT_TO_ELEMENT * is_s_ff)

        opt = _optimize_core_bits(
            budget,
            base_pp, base_cm, base_fm,
            p_val, s_val,
            is_p_pp, is_s_pp,
            is_p_cm, is_s_cm,
            is_p_fm, is_s_fm,
            is_p_ov, is_s_ov,
            m0, m1, m2, m3,
            head_len,
            body_fever, body_normal,
        )

        base_score: ti.i32 = opt[0]
        final_pp: ti.i32 = opt[1]
        final_cm: ti.i32 = opt[2]
        final_fm: ti.i32 = opt[3]
        final_p_val: ti.i32 = opt[4]
        final_s_val: ti.i32 = opt[5]
        gems_pp: ti.i32 = opt[6]
        gems_cm: ti.i32 = opt[7]
        gems_fm: ti.i32 = opt[8]
        gems_ov: ti.i32 = opt[9]

        # Penalty math
        pp_factor: ti.f32 = lookup_ref_pp(final_pp)
        combo_mul: ti.f32 = lookup_ref_cm(final_cm)
        combo_span: ti.f32 = combo_mul - 1.0

        base_value: ti.f32 = ti.cast((final_p_val * 2) + final_s_val, ti.f32) + pp_factor
        combo_value: ti.i32 = ti.cast(ti.floor(base_value * combo_mul), ti.i32)

        great_penalty_base: ti.i32 = ti.cast(
            ti.floor((ti.cast((final_p_val * 2) + final_s_val, ti.f32) * (2.0 / 3.0)) + 150.0),
            ti.i32,
        )
        great_combo_value: ti.i32 = ti.cast(ti.floor(ti.cast(great_penalty_base, ti.f32) * combo_mul), ti.i32)
        body_penalty: ti.i32 = ti.max(0, combo_value - great_combo_value)

        score_penalty_total: ti.i32 = 0
        fill_penalty_total: ti.i32 = 0

        for s in range(ti.min(n_sections, FG_MAX_SECTIONS)):
            fp_notes: ti.i32 = fill_notes[s]
            fill_penalty_total += fp_notes * combo_value

            forced_n: ti.i32 = forced_applied[s]
            if forced_n > 0:
                start = start_idx[s] + (1 if skip_wasted[s] != 0 else 0)
                if start > total_notes:
                    start = total_notes
                for k in range(forced_n):
                    note_idx = start + k
                    if note_idx < 100:
                        scaling: ti.f32 = 1.0 + combo_span * (ti.cast(note_idx + 1, ti.f32) / 100.0)
                        perfect_val: ti.i32 = ti.cast(ti.floor(base_value * scaling), ti.i32)
                        great_val: ti.i32 = ti.cast(ti.floor(ti.cast(great_penalty_base, ti.f32) * scaling), ti.i32)
                        pen: ti.i32 = ti.max(0, perfect_val - great_val)
                        score_penalty_total += pen
                    else:
                        score_penalty_total += body_penalty

        final_score: ti.i32 = base_score - score_penalty_total
        if final_score < 0:
            final_score = 0

        old = ti.atomic_max(fg_best_final_score[g], final_score)
        if final_score > old:
            fg_best_base_score[g] = base_score
            fg_best_cfg_idx[g] = cfg_offset + cfg_idx
            fg_best_ft[g] = ft_gems
            fg_best_ff[g] = ff_gems
            fg_best_g_pp[g] = gems_pp
            fg_best_g_cm[g] = gems_cm
            fg_best_g_fm[g] = gems_fm
            fg_best_g_ov[g] = gems_ov
            fg_best_score_penalty[g] = score_penalty_total
            fg_best_fill_penalty[g] = fill_penalty_total


# ============================================================================
# TWO-STAGE REDUCTION KERNELS (FG Finder optimization)
# Eliminates atomic_max contention by splitting reduction into two phases:
#   Stage 1: Find best cfg per (genome, ftff) - sequential cfg loop, no atomics
#   Stage 2: Reduce ftff to find best per genome - parallel across genomes
# ============================================================================

@ti.kernel
def fg_stage1_init_kernel(n_genomes: ti.i32, n_ftff: ti.i32):
    """Initialize Stage 1 fields before reduction (supports cfg-chunk accumulation)."""
    for g, f in ti.ndrange(n_genomes, n_ftff):
        fg_stage1_final_score[g, f] = -1
        fg_stage1_base_score[g, f] = 0
        fg_stage1_cfg_idx[g, f] = -1
        fg_stage1_g_pp[g, f] = 0
        fg_stage1_g_cm[g, f] = 0
        fg_stage1_g_fm[g, f] = 0
        fg_stage1_g_ov[g, f] = 0
        fg_stage1_score_penalty[g, f] = 0
        fg_stage1_fill_penalty[g, f] = 0


@ti.kernel
def fg_stage1_kernel(
    n_genomes: ti.i32,
    total_notes: ti.i32,
    long_notes: ti.i32,
    last_note_time: ti.f32,
    total_budget: ti.i32,
    gem_scale_fever: ti.i32,
    n_cfg: ti.i32,
    n_sections: ti.i32,
    n_ftff: ti.i32,
    cfg_offset: ti.i32,
    is_p_ft: ti.i32, is_s_ft: ti.i32,
    is_p_ff: ti.i32, is_s_ff: ti.i32,
    is_p_pp: ti.i32, is_s_pp: ti.i32,
    is_p_cm: ti.i32, is_s_cm: ti.i32,
    is_p_fm: ti.i32, is_s_fm: ti.i32,
    is_p_ov: ti.i32, is_s_ov: ti.i32,
):
    """
    Stage 1: Find best cfg for each (genome, ftff) pair.
    
    Parallelizes over (genome, ftff), loops cfg sequentially inside.
    NO ATOMICS - each (g, f) pair has its own output slot.
    """
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    ELEMENTAL_GEM_SCALE: ti.i32 = 6
    MAX_STAT: ti.i32 = 160

    head_len: ti.i32 = ti.min(total_notes, 100)

    non_fever_cas: ti.f32 = ti.max(0.0, (ti.cast(total_notes - long_notes, ti.f32) * 0.333))
    fever_time_cas: ti.f32 = last_note_time * 0.15 + 0.15

    for g, ftff_idx in ti.ndrange(n_genomes, n_ftff):
        ft_gems: ti.i32 = fg_ft_list[ftff_idx]
        ff_gems: ti.i32 = fg_ff_list[ftff_idx]
        if ft_gems + ff_gems > total_budget:
            continue

        # Load genome base stats (hoisted out of cfg loop)
        base_pp: ti.i32 = genome_base_pp[g]
        base_cm: ti.i32 = genome_base_cm[g]
        base_fm: ti.i32 = genome_base_fm[g]
        base_p_val: ti.i32 = genome_base_p_val[g]
        base_s_val: ti.i32 = genome_base_s_val[g]
        base_ft_stat: ti.i32 = genome_base_ft[g]
        base_ff_stat: ti.i32 = genome_base_ff[g]

        # Fever multipliers for this FT/FF (hoisted)
        ft_stat_val: ti.i32 = base_ft_stat + (ft_gems * gem_scale_fever)
        ff_stat_val: ti.i32 = base_ff_stat + (ff_gems * gem_scale_fever)
        ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
        ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))
        ft_factor: ti.f32 = lookup_ref_ft(ft_idx)
        ff_factor: ti.f32 = lookup_ref_ff(ff_idx)

        non_fever_base: ti.i32 = ti.cast(ti.ceil(non_fever_cas * ff_factor), ti.i32)
        non_fever_great_to_fill: ti.i32 = ti.cast(
            ti.ceil(ti.max(1.0, non_fever_cas * ff_factor * 2.0)),
            ti.i32,
        )
        real_fever_time: ti.f32 = fever_time_cas * ft_factor

        # Track best across all cfg for this (genome, ftff).
        # IMPORTANT: This kernel may be called multiple times (cfg-chunked uploads),
        # so we must accumulate across calls instead of overwriting prior chunk results.
        best_final: ti.i32 = fg_stage1_final_score[g, ftff_idx]
        best_base: ti.i32 = 0
        best_cfg: ti.i32 = 0
        best_pp: ti.i32 = 0
        best_cm: ti.i32 = 0
        best_fm: ti.i32 = 0
        best_ov: ti.i32 = 0
        best_sp: ti.i32 = 0
        best_fp: ti.i32 = 0
        if best_final >= 0:
            best_base = fg_stage1_base_score[g, ftff_idx]
            best_cfg = fg_stage1_cfg_idx[g, ftff_idx]
            best_pp = fg_stage1_g_pp[g, ftff_idx]
            best_cm = fg_stage1_g_cm[g, ftff_idx]
            best_fm = fg_stage1_g_fm[g, ftff_idx]
            best_ov = fg_stage1_g_ov[g, ftff_idx]
            best_sp = fg_stage1_score_penalty[g, ftff_idx]
            best_fp = fg_stage1_fill_penalty[g, ftff_idx]

        # Sequential loop over configs (no atomics needed!)
        for cfg_idx in range(n_cfg):
            # Timeline simulation -> head mask bits + body fever count
            m0 = ti.cast(0, ti.u32)
            m1 = ti.cast(0, ti.u32)
            m2 = ti.cast(0, ti.u32)
            m3 = ti.cast(0, ti.u32)
            body_fever: ti.i32 = 0

            start_idx = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
            forced_applied = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
            fill_notes = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
            skip_wasted = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)

            current_idx: ti.i32 = 0
            sec: ti.i32 = 0
            while current_idx < total_notes:
                base_notes_s: ti.i32 = non_fever_base - 1 if sec == 0 else non_fever_base
                if base_notes_s < 0:
                    base_notes_s = 0

                forced_val: ti.i32 = 0
                if sec < n_sections:
                    forced_val = fg_forced_counts[cfg_idx, sec]
                    if forced_val < 0:
                        forced_val = 0
                    forced_val = ti.min(forced_val, non_fever_base)

                fp_calc: ti.i32 = 0
                if forced_val > 0:
                    fp_calc = ti.cast(
                        ti.ceil(
                            ti.max(
                                0.0,
                                (ti.cast(non_fever_base * forced_val, ti.f32) / ti.cast(non_fever_great_to_fill, ti.f32)),
                            )
                        ),
                        ti.i32,
                    )

                notes_to_fill: ti.i32 = base_notes_s + fp_calc
                section_start: ti.i32 = current_idx
                end_normal: ti.i32 = ti.min(total_notes, section_start + notes_to_fill)
                actual_notes: ti.i32 = ti.max(0, end_normal - section_start)
                forced_app: ti.i32 = ti.min(forced_val, actual_notes)

                if sec < n_sections and sec < FG_MAX_SECTIONS:
                    start_idx[sec] = section_start
                    forced_applied[sec] = forced_app
                    fill_notes[sec] = fp_calc
                    skip_wasted[sec] = 1 if sec == 0 else 0

                current_idx = end_normal
                if current_idx >= total_notes:
                    break

                # Fever section
                start_time: ti.f32 = song_timestamps[current_idx]
                end_time: ti.f32 = start_time + real_fever_time
                fever_end_idx: ti.i32 = _searchsorted_left_timestamps(total_notes, end_time, current_idx)
                if fever_end_idx <= current_idx:
                    fever_end_idx = ti.min(total_notes, current_idx + 1)

                if current_idx < head_len:
                    head_end = ti.min(head_len, fever_end_idx)
                    for i in range(current_idx, head_end):
                        word = i >> 5
                        bit = ti.cast(1, ti.u32) << ti.cast(i & 31, ti.u32)
                        if word == 0:
                            m0 |= bit
                        elif word == 1:
                            m1 |= bit
                        elif word == 2:
                            m2 |= bit
                        else:
                            m3 |= bit

                if fever_end_idx > head_len:
                    body_start = head_len if current_idx < head_len else current_idx
                    if fever_end_idx > body_start:
                        body_fever += (fever_end_idx - body_start)

                current_idx = fever_end_idx
                sec += 1

            body_len = ti.max(total_notes - head_len, 0)
            body_normal: ti.i32 = ti.max(body_len - body_fever, 0)

            budget: ti.i32 = total_budget - ft_gems - ff_gems
            if budget < 0:
                continue

            p_val: ti.i32 = base_p_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff_gems * GEM_STAT_TO_ELEMENT * is_p_ff)
            s_val: ti.i32 = base_s_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff_gems * GEM_STAT_TO_ELEMENT * is_s_ff)

            opt = _optimize_core_bits(
                budget,
                base_pp, base_cm, base_fm,
                p_val, s_val,
                is_p_pp, is_s_pp,
                is_p_cm, is_s_cm,
                is_p_fm, is_s_fm,
                is_p_ov, is_s_ov,
                m0, m1, m2, m3,
                head_len,
                body_fever, body_normal,
            )

            base_score: ti.i32 = opt[0]
            final_pp: ti.i32 = opt[1]
            final_cm: ti.i32 = opt[2]
            final_fm: ti.i32 = opt[3]
            final_p_val: ti.i32 = opt[4]
            final_s_val: ti.i32 = opt[5]
            gems_pp: ti.i32 = opt[6]
            gems_cm: ti.i32 = opt[7]
            gems_fm: ti.i32 = opt[8]
            gems_ov: ti.i32 = opt[9]

            # Penalty math
            pp_factor: ti.f32 = lookup_ref_pp(final_pp)
            combo_mul: ti.f32 = lookup_ref_cm(final_cm)
            combo_span: ti.f32 = combo_mul - 1.0

            base_value: ti.f32 = ti.cast((final_p_val * 2) + final_s_val, ti.f32) + pp_factor
            combo_value: ti.i32 = ti.cast(ti.floor(base_value * combo_mul), ti.i32)

            great_penalty_base: ti.i32 = ti.cast(
                ti.floor((ti.cast((final_p_val * 2) + final_s_val, ti.f32) * (2.0 / 3.0)) + 150.0),
                ti.i32,
            )
            great_combo_value: ti.i32 = ti.cast(ti.floor(ti.cast(great_penalty_base, ti.f32) * combo_mul), ti.i32)
            body_penalty: ti.i32 = ti.max(0, combo_value - great_combo_value)

            score_penalty_total: ti.i32 = 0
            fill_penalty_total: ti.i32 = 0

            for s in range(ti.min(n_sections, FG_MAX_SECTIONS)):
                fp_notes: ti.i32 = fill_notes[s]
                fill_penalty_total += fp_notes * combo_value

                forced_n: ti.i32 = forced_applied[s]
                if forced_n > 0:
                    start = start_idx[s] + (1 if skip_wasted[s] != 0 else 0)
                    if start > total_notes:
                        start = total_notes
                    for k in range(forced_n):
                        note_idx = start + k
                        if note_idx < 100:
                            scaling: ti.f32 = 1.0 + combo_span * (ti.cast(note_idx + 1, ti.f32) / 100.0)
                            perfect_val: ti.i32 = ti.cast(ti.floor(base_value * scaling), ti.i32)
                            great_val: ti.i32 = ti.cast(ti.floor(ti.cast(great_penalty_base, ti.f32) * scaling), ti.i32)
                            pen: ti.i32 = ti.max(0, perfect_val - great_val)
                            score_penalty_total += pen
                        else:
                            score_penalty_total += body_penalty

            final_score: ti.i32 = base_score - score_penalty_total
            if final_score < 0:
                final_score = 0

            # Update best for this (genome, ftff) - NO ATOMICS!
            if final_score > best_final:
                best_final = final_score
                best_base = base_score
                best_cfg = cfg_offset + cfg_idx
                best_pp = gems_pp
                best_cm = gems_cm
                best_fm = gems_fm
                best_ov = gems_ov
                best_sp = score_penalty_total
                best_fp = fill_penalty_total

        # Store best for this (genome, ftff) pair
        fg_stage1_final_score[g, ftff_idx] = best_final
        fg_stage1_base_score[g, ftff_idx] = best_base
        fg_stage1_cfg_idx[g, ftff_idx] = best_cfg
        fg_stage1_g_pp[g, ftff_idx] = best_pp
        fg_stage1_g_cm[g, ftff_idx] = best_cm
        fg_stage1_g_fm[g, ftff_idx] = best_fm
        fg_stage1_g_ov[g, ftff_idx] = best_ov
        fg_stage1_score_penalty[g, ftff_idx] = best_sp
        fg_stage1_fill_penalty[g, ftff_idx] = best_fp


@ti.kernel
def fg_stage2_kernel(n_genomes: ti.i32, n_ftff: ti.i32):
    """
    Stage 2: Reduce across ftff to find best per genome.
    
    Each thread handles one genome, loops over ftff sequentially.
    Much smaller workload (genomes × ftff) vs (genomes × cfg × ftff).
    """
    for g in range(n_genomes):
        best_final: ti.i32 = -1
        best_ftff: ti.i32 = 0
        
        # Find best ftff for this genome
        for f in range(n_ftff):
            score = fg_stage1_final_score[g, f]
            if score > best_final:
                best_final = score
                best_ftff = f
        
        # Copy best to output fields
        if best_final >= 0:
            fg_best_final_score[g] = best_final
            fg_best_base_score[g] = fg_stage1_base_score[g, best_ftff]
            fg_best_cfg_idx[g] = fg_stage1_cfg_idx[g, best_ftff]
            fg_best_ft[g] = fg_ft_list[best_ftff]
            fg_best_ff[g] = fg_ff_list[best_ftff]
            fg_best_g_pp[g] = fg_stage1_g_pp[g, best_ftff]
            fg_best_g_cm[g] = fg_stage1_g_cm[g, best_ftff]
            fg_best_g_fm[g] = fg_stage1_g_fm[g, best_ftff]
            fg_best_g_ov[g] = fg_stage1_g_ov[g, best_ftff]
            fg_best_score_penalty[g] = fg_stage1_score_penalty[g, best_ftff]
            fg_best_fill_penalty[g] = fg_stage1_fill_penalty[g, best_ftff]


@ti.func
def calc_score_with_grid(
    base_value: ti.f32,
    combo_mul: ti.f32,
    fever_mul: ti.f32,
    ft_idx: ti.i32,
    ff_idx: ti.i32,
    head_len: ti.i32,
    count_fever: ti.i32,
    count_normal: ti.i32,
) -> ti.i32:
    """
    Score calculation using grid-stored fever masks.
    Reads fever mask from grid_fever_masks[ft_idx, ff_idx, :].
    """
    # Body score (notes 101+)
    combo_val = ti.floor(base_value * combo_mul)
    fever_val = ti.floor(base_value * combo_mul * fever_mul)
    body_score = (ti.cast(count_fever, ti.f32) * fever_val) + (ti.cast(count_normal, ti.f32) * combo_val)
    
    # Head score (notes 1-100) with ramped combo
    factor = (combo_mul - 1.0) * base_value / 100.0
    head_score = 0.0
    
    for i in range(head_len):
        ramp_val = base_value + (ti.cast(i + 1, ti.f32) * factor)
        if grid_fever_masks[ft_idx, ff_idx, i] != 0:
            head_score += ti.floor(ramp_val * fever_mul)
        else:
            head_score += ti.floor(ramp_val)
    
    return ti.cast(body_score + head_score, ti.i32)


@ti.func
def calc_score_with_grid_bits(
    base_value: ti.f32,
    combo_mul: ti.f32,
    fever_mul: ti.f32,
    m0: ti.u32,
    m1: ti.u32,
    m2: ti.u32,
    m3: ti.u32,
    head_len: ti.i32,
    count_fever: ti.i32,
    count_normal: ti.i32,
) -> ti.i32:
    """
    Score calculation using bitpacked head fever masks.

    m0..m3 are 4x u32 words (128 bits total), covering the first 100 notes.
    """
    combo_val = ti.floor(base_value * combo_mul)
    fever_val = ti.floor(base_value * combo_mul * fever_mul)
    body_score = (ti.cast(count_fever, ti.f32) * fever_val) + (
        ti.cast(count_normal, ti.f32) * combo_val
    )

    factor = (combo_mul - 1.0) * base_value / 100.0
    head_score = 0.0

    for i in range(head_len):
        ramp_val = base_value + (ti.cast(i + 1, ti.f32) * factor)
        word = i >> 5  # i // 32
        bit = ti.cast(1, ti.u32) << ti.cast(i & 31, ti.u32)
        is_fever = False
        if word == 0:
            is_fever = (m0 & bit) != 0
        elif word == 1:
            is_fever = (m1 & bit) != 0
        elif word == 2:
            is_fever = (m2 & bit) != 0
        else:
            is_fever = (m3 & bit) != 0

        if is_fever:
            head_score += ti.floor(ramp_val * fever_mul)
        else:
            head_score += ti.floor(ramp_val)

    return ti.cast(body_score + head_score, ti.i32)


# Work item fields for parallel FT/FF kernel (reuse existing result fields at genome level)
# We'll use a 2D parallelization: n_genomes × n_ftff_combos

@ti.kernel
def solve_ftff_parallel_kernel(
    n_work_items: ti.i32,
    total_budget: ti.i32,
    gem_scale_fever: ti.i32,
    is_p_ft: ti.i32, is_s_ft: ti.i32,
    is_p_ff: ti.i32, is_s_ff: ti.i32,
    is_p_pp: ti.i32, is_s_pp: ti.i32,
    is_p_cm: ti.i32, is_s_cm: ti.i32,
    is_p_fm: ti.i32, is_s_fm: ti.i32,
    is_p_ov: ti.i32, is_s_ov: ti.i32,
):
    """
    V2 kernel: Parallelize across (genome, ft, ff) combinations.
    
    Each thread handles ONE (genome, ft, ff) combination.
    This gives 500 genomes × ~800 combos = 400k parallel threads.
    
    Uses work_* fields for input (genome_id, ft, ff) and result_* for output.
    Reduction to find best per genome is done on CPU after kernel.
    """
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160
    GEM_SCALE_NORMAL: ti.i32 = 2
    ELEMENTAL_GEM_SCALE: ti.i32 = 6
    
    for i in range(n_work_items):
        genome_idx: ti.i32 = work_genome_id[i]
        ft: ti.i32 = work_ft_gems[i]
        ff: ti.i32 = work_ff_gems[i]
        
        # Load genome base stats
        base_pp: ti.i32 = genome_base_pp[genome_idx]
        base_cm: ti.i32 = genome_base_cm[genome_idx]
        base_fm: ti.i32 = genome_base_fm[genome_idx]
        base_p_val: ti.i32 = genome_base_p_val[genome_idx]
        base_s_val: ti.i32 = genome_base_s_val[genome_idx]
        base_ft_stat: ti.i32 = genome_base_ft[genome_idx]
        base_ff_stat: ti.i32 = genome_base_ff[genome_idx]
        
        # Compute stat indices for grid lookup
        ft_stat_val: ti.i32 = base_ft_stat + (ft * gem_scale_fever)
        ff_stat_val: ti.i32 = base_ff_stat + (ff * gem_scale_fever)
        ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
        ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))
        
        # O(1) lookup from grid
        count_fever: ti.i32 = grid_count_body_fever[ft_idx, ff_idx]
        count_normal: ti.i32 = grid_count_body_normal[ft_idx, ff_idx]
        head_len: ti.i32 = grid_head_len[ft_idx, ff_idx]
        
        # Budget remaining for PP/CM/FM/OV gems
        budget: ti.i32 = total_budget - ft - ff
        
        # Adjust p/s values for FT/FF gem contributions
        p_val: ti.i32 = base_p_val + (ft * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff * GEM_STAT_TO_ELEMENT * is_p_ff)
        s_val: ti.i32 = base_s_val + (ft * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff * GEM_STAT_TO_ELEMENT * is_s_ff)
        
        # Run greedy gem allocation
        gems_pp: ti.i32 = 0
        gems_cm: ti.i32 = 0
        gems_fm: ti.i32 = 0
        gems_ov: ti.i32 = 0
        cur_pp: ti.i32 = base_pp
        cur_cm: ti.i32 = base_cm
        cur_fm: ti.i32 = base_fm
        cur_p: ti.i32 = p_val
        cur_s: ti.i32 = s_val
        cur_remaining: ti.i32 = budget
        final_score: ti.i32 = 0
        
        while cur_remaining > 0:
            PP_TIE_LOOKAHEAD_MAX: ti.i32 = 8
            fill_budget: ti.i32 = cur_remaining - 1
            fill_bonus: ti.i32 = fill_budget * ELEMENTAL_GEM_SCALE if fill_budget > 0 else 0

            # Precompute current multipliers (unchanged for PP/OV checks)
            c_mul_cur: ti.f32 = lookup_ref_cm(cur_cm)
            f_mul_cur: ti.f32 = lookup_ref_fm(cur_fm)

            # Start with OV as default so OV wins exact ties.
            t_p: ti.i32 = cur_p + (ELEMENTAL_GEM_SCALE * is_p_ov) + (fill_bonus * is_p_ov)
            t_s: ti.i32 = cur_s + (ELEMENTAL_GEM_SCALE * is_s_ov) + (fill_bonus * is_s_ov)
            pp_factor: ti.f32 = lookup_ref_pp(cur_pp)
            base_val: ti.f32 = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
            best_opt_score: ti.i32 = calc_score_with_grid(base_val, c_mul_cur, f_mul_cur, ft_idx, ff_idx, head_len, count_fever, count_normal)
            best_opt: ti.i32 = 3

            pp_score: ti.i32 = -1

            # Option 0: PP gem
            if cur_pp < MAX_STAT:
                t_pp: ti.i32 = cur_pp + GEM_SCALE_NORMAL
                t_p = cur_p + (GEM_STAT_TO_ELEMENT * is_p_pp) + (fill_bonus * is_p_ov)
                t_s = cur_s + (GEM_STAT_TO_ELEMENT * is_s_pp) + (fill_bonus * is_s_ov)
                pp_factor = lookup_ref_pp(t_pp)
                base_val = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                pp_score = calc_score_with_grid(base_val, c_mul_cur, f_mul_cur, ft_idx, ff_idx, head_len, count_fever, count_normal)
                if pp_score > best_opt_score:
                    best_opt_score = pp_score
                    best_opt = 0

            # Option 1: CM gem
            if cur_cm < MAX_STAT:
                t_cm: ti.i32 = cur_cm + GEM_SCALE_NORMAL
                t_p = cur_p + (GEM_STAT_TO_ELEMENT * is_p_cm) + (fill_bonus * is_p_ov)
                t_s = cur_s + (GEM_STAT_TO_ELEMENT * is_s_cm) + (fill_bonus * is_s_ov)
                pp_factor = lookup_ref_pp(cur_pp)
                base_val = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                c_mul: ti.f32 = lookup_ref_cm(t_cm)
                score: ti.i32 = calc_score_with_grid(base_val, c_mul, f_mul_cur, ft_idx, ff_idx, head_len, count_fever, count_normal)
                if score > best_opt_score:
                    best_opt_score = score
                    best_opt = 1

            # Option 2: FM gem
            if cur_fm < MAX_STAT:
                t_fm: ti.i32 = cur_fm + gem_scale_fever
                t_p = cur_p + (GEM_STAT_TO_ELEMENT * is_p_fm) + (fill_bonus * is_p_ov)
                t_s = cur_s + (GEM_STAT_TO_ELEMENT * is_s_fm) + (fill_bonus * is_s_ov)
                pp_factor = lookup_ref_pp(cur_pp)
                base_val = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                f_mul: ti.f32 = lookup_ref_fm(t_fm)
                score = calc_score_with_grid(base_val, c_mul_cur, f_mul, ft_idx, ff_idx, head_len, count_fever, count_normal)
                if score > best_opt_score:
                    best_opt_score = score
                    best_opt = 2

            # PP lookahead: if OV wins a tie now, but a few PP gems would become a real
            # improvement soon, start investing in PP.
            if best_opt == 3 and pp_score == best_opt_score and cur_remaining > 1:
                max_k: ti.i32 = cur_remaining
                if max_k > PP_TIE_LOOKAHEAD_MAX:
                    max_k = PP_TIE_LOOKAHEAD_MAX
                k: ti.i32 = 2
                while k <= max_k:
                    fill_bonus_k: ti.i32 = (cur_remaining - k) * ELEMENTAL_GEM_SCALE
                    t_pp: ti.i32 = cur_pp + (k * GEM_SCALE_NORMAL)
                    t_p = cur_p + (k * GEM_STAT_TO_ELEMENT * is_p_pp) + (fill_bonus_k * is_p_ov)
                    t_s = cur_s + (k * GEM_STAT_TO_ELEMENT * is_s_pp) + (fill_bonus_k * is_s_ov)
                    pp_factor = lookup_ref_pp(t_pp)
                    base_val = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                    score_k: ti.i32 = calc_score_with_grid(base_val, c_mul_cur, f_mul_cur, ft_idx, ff_idx, head_len, count_fever, count_normal)
                    if score_k > best_opt_score:
                        best_opt = 0
                        break
                    k += 1
            
            # Apply best option
            if best_opt == 0:
                cur_pp += GEM_SCALE_NORMAL
                cur_p += GEM_STAT_TO_ELEMENT * is_p_pp
                cur_s += GEM_STAT_TO_ELEMENT * is_s_pp
                gems_pp += 1
            elif best_opt == 1:
                cur_cm += GEM_SCALE_NORMAL
                cur_p += GEM_STAT_TO_ELEMENT * is_p_cm
                cur_s += GEM_STAT_TO_ELEMENT * is_s_cm
                gems_cm += 1
            elif best_opt == 2:
                cur_fm += gem_scale_fever
                cur_p += GEM_STAT_TO_ELEMENT * is_p_fm
                cur_s += GEM_STAT_TO_ELEMENT * is_s_fm
                gems_fm += 1
            else:
                cur_p += ELEMENTAL_GEM_SCALE * is_p_ov
                cur_s += ELEMENTAL_GEM_SCALE * is_s_ov
                gems_ov += 1
            
            cur_remaining -= 1
            final_score = best_opt_score
        
        # Store result for this work item (reduction done on CPU)
        result_scores[i] = final_score
        result_pp[i] = gems_pp
        result_cm[i] = gems_cm
        result_fm[i] = gems_fm
        result_ov[i] = gems_ov


# ============================================================================
# PYTHON WRAPPER API
# ============================================================================

_ref_loaded = False


def load_ref_arrays(ref_arrays: dict):
    """
    Upload reference arrays to GPU fields.
    
    Must be called once before using optimize_gems_batch_gpu().
    Typically called when switching songs or on first use.
    
    Args:
        ref_arrays: Dict with keys "Perfect Points", "Combo Multiplier", "Fever Multiplier"
                    Each value is a NumPy array of shape (161,)
    """
    global _ref_loaded
    
    if not _ti_initialized:
        init_taichi_vulkan()
    
    if not _fields_allocated:
        _allocate_fields()
    
    ref_pp_field.from_numpy(ref_arrays["Perfect Points"].astype(np.float32))
    ref_cm_field.from_numpy(ref_arrays["Combo Multiplier"].astype(np.float32))
    ref_fm_field.from_numpy(ref_arrays["Fever Multiplier"].astype(np.float32))

    # Optional FT/FF arrays (required for full FG finder GPU port)
    if "Fever Time" in ref_arrays:
        ref_ft_field.from_numpy(ref_arrays["Fever Time"].astype(np.float32))
    if "Fever Fill Rate" in ref_arrays:
        ref_ff_field.from_numpy(ref_arrays["Fever Fill Rate"].astype(np.float32))
    
    _ref_loaded = True


def optimize_gems_gpu(
    budget: int,
    fever_mask_head: np.ndarray,
    count_body_fever: int,
    count_body_normal: int,
    cur_pp: int, cur_cm: int, cur_fm: int,
    cur_p_val: int, cur_s_val: int,
    is_p_pp: int, is_s_pp: int,
    is_p_cm: int, is_s_cm: int,
    is_p_fm: int, is_s_fm: int,
    is_p_ov: int, is_s_ov: int,
    ref_arrays: dict,
):
    """
    Single-item GPU gem optimization (for compatibility with existing code).
    
    Wraps the batch API for single-item use.
    """
    batch_input = [{
        "budget": budget,
        "fever_mask_head": fever_mask_head,
        "count_body_fever": count_body_fever,
        "count_body_normal": count_body_normal,
        "ft_gems": 0,
        "ff_gems": 0,
    }]
    
    results = optimize_gems_batch_gpu(
        batch_input,
        cur_pp, cur_cm, cur_fm,
        base_p_val=cur_p_val,
        base_s_val=cur_s_val,
        is_p_ft=0, is_s_ft=0,
        is_p_ff=0, is_s_ff=0,
        is_p_pp=is_p_pp, is_s_pp=is_s_pp,
        is_p_cm=is_p_cm, is_s_cm=is_s_cm,
        is_p_fm=is_p_fm, is_s_fm=is_s_fm,
        is_p_ov=is_p_ov, is_s_ov=is_s_ov,
        ref_arrays=ref_arrays,
    )
    
    return results[0] if results else None


def optimize_gems_batch_gpu(
    batch_input: list,
    cur_pp: int, cur_cm: int, cur_fm: int,
    base_p_val: int, base_s_val: int,
    is_p_ft: int, is_s_ft: int,
    is_p_ff: int, is_s_ff: int,
    is_p_pp: int, is_s_pp: int,
    is_p_cm: int, is_s_cm: int,
    is_p_fm: int, is_s_fm: int,
    is_p_ov: int, is_s_ov: int,
    ref_arrays: dict,
) -> list:
    """
    Batch GPU gem optimization - main entry point.
    
    Processes multiple work items in a single kernel launch.
    Automatically handles per-item base stat overrides (for batch coalescing)
    by mapping unique base stat combinations to temporary genome IDs.
    
    Args:
        batch_input: List of dicts. Optional keys "_base_p_val", "_base_s_val"
                     override the function arguments for that specific item.
    """
    global _ref_loaded
    
    n = len(batch_input)
    if n == 0:
        return []
    
    # Handle large batches by chunking
    if n > MAX_WORK_ITEMS:
        all_results = []
        for chunk_start in range(0, n, MAX_WORK_ITEMS):
            chunk_end = min(chunk_start + MAX_WORK_ITEMS, n)
            chunk = batch_input[chunk_start:chunk_end]
            chunk_results = optimize_gems_batch_gpu(
                chunk, cur_pp, cur_cm, cur_fm,
                base_p_val, base_s_val,
                is_p_ft, is_s_ft, is_p_ff, is_s_ff,
                is_p_pp, is_s_pp, is_p_cm, is_s_cm,
                is_p_fm, is_s_fm, is_p_ov, is_s_ov,
                ref_arrays,
            )
            all_results.extend(chunk_results)
        return all_results
    
    if not _ti_initialized:
        init_taichi_vulkan()
    
    if not _fields_allocated:
        _allocate_fields()
    
    if not _ref_loaded:
        load_ref_arrays(ref_arrays)
    
    # ========================================================================
    # DYNAMIC GENOME MAPPING (Fix for Batch Coalescing)
    # ========================================================================
    # Identify unique (base_p, base_s) pairs to support merged batches
    
    unique_stats_map = {}  # (p, s) -> genome_id
    next_genome_id = 0
    
    # Default stats
    default_stats = (base_p_val, base_s_val)
    
    # Reuse large staging buffers to avoid huge per-call allocations/zeroing.
    staging = _ensure_batch_staging()
    budgets_np = staging["budgets"]
    count_fever_np = staging["count_fever"]
    count_normal_np = staging["count_normal"]
    ft_gems_np = staging["ft_gems"]
    ff_gems_np = staging["ff_gems"]
    head_len_np = staging["head_len"]
    genome_id_np = staging["genome_id"]
    fever_masks_np = staging["fever_masks"]
    
    # IMPORTANT: head_len is conditionally set below; ensure we reset it for used rows.
    # (Without this, reused buffers could leak stale head_len for mask-less rows.)
    for i, item in enumerate(batch_input):
        budgets_np[i] = item["budget"]
        count_fever_np[i] = item["count_body_fever"]
        count_normal_np[i] = item["count_body_normal"]
        ft_gems_np[i] = item.get("ft_gems", 0)
        ff_gems_np[i] = item.get("ff_gems", 0)
        head_len_np[i] = 0
        
        mask = item.get("fever_mask_head")
        if mask is not None:
            hl = min(len(mask), MAX_HEAD_NOTES)
            head_len_np[i] = hl
            # Avoid per-item astype allocations: NumPy will cast on assignment.
            fever_masks_np[i, :hl] = mask[:hl]
            
        # Check for overrides
        p = item.get("_base_p_val", base_p_val)
        s = item.get("_base_s_val", base_s_val)
        stats_key = (p, s)
        
        if stats_key not in unique_stats_map:
            unique_stats_map[stats_key] = next_genome_id
            next_genome_id += 1
            
        genome_id_np[i] = unique_stats_map[stats_key]
    
    # Ensure we don't exceed max genomes (unlikely for reasonable batches)
    if next_genome_id > MAX_GENOMES:
        # Fallback: Process sequentially or raise error. 
        # For now, just error as 512 distinct stat combos in one batch is extreme.
        raise RuntimeError(f"Too many unique base stat combinations in batch ({next_genome_id} > {MAX_GENOMES})")
        
    # Upload per-genome stats
    genome_pp_np = staging["genome_pp"]
    genome_cm_np = staging["genome_cm"]
    genome_fm_np = staging["genome_fm"]
    genome_p_np = staging["genome_p"]
    genome_s_np = staging["genome_s"]
    
    # Fill standard stats for all used genomes
    # Note: pp/cm/fm are still constant for the whole batch based on function args
    # If they needed to vary, we'd need them in the unique key too.
    for (p, s), gid in unique_stats_map.items():
        genome_pp_np[gid] = cur_pp
        genome_cm_np[gid] = cur_cm
        genome_fm_np[gid] = cur_fm
        genome_p_np[gid] = p
        genome_s_np[gid] = s
        
    genome_base_pp.from_numpy(genome_pp_np)
    genome_base_cm.from_numpy(genome_cm_np)
    genome_base_fm.from_numpy(genome_fm_np)
    genome_base_p_val.from_numpy(genome_p_np)
    genome_base_s_val.from_numpy(genome_s_np)
    
    # BULK transfer
    work_budgets.from_numpy(budgets_np)
    work_count_fever.from_numpy(count_fever_np)
    work_count_normal.from_numpy(count_normal_np)
    work_ft_gems.from_numpy(ft_gems_np)
    work_ff_gems.from_numpy(ff_gems_np)
    work_head_len.from_numpy(head_len_np)
    work_genome_id.from_numpy(genome_id_np)
    fever_masks.from_numpy(fever_masks_np)
    
    # Launch kernel
    solve_batch_kernel(
        n,
        is_p_ft, is_s_ft, is_p_ff, is_s_ff,
        is_p_pp, is_s_pp, is_p_cm, is_s_cm,
        is_p_fm, is_s_fm, is_p_ov, is_s_ov,
    )
    
    ti.sync()
    
    # Download results
    scores_np = result_scores.to_numpy()[:n]
    pp_np = result_pp.to_numpy()[:n]
    cm_np = result_cm.to_numpy()[:n]
    fm_np = result_fm.to_numpy()[:n]
    ov_np = result_ov.to_numpy()[:n]
    p_val_np = result_p_val.to_numpy()[:n]
    s_val_np = result_s_val.to_numpy()[:n]
    
    results = [
        (int(scores_np[i]), int(pp_np[i]), int(cm_np[i]), int(fm_np[i]),
         int(p_val_np[i]), int(s_val_np[i]),
         int(pp_np[i]), int(cm_np[i]), int(fm_np[i]), int(ov_np[i]))
        for i in range(n)
    ]
    
    return results


#
# ============================================================================
# LEGACY GEM-SOLVER ENTRY POINTS (EXPLICITLY DISABLED)
# ============================================================================
#
# This module intentionally hosts ONLY the ForceGreatsFinder GPU implementation
# (see solve_force_greats_finder_gpu). The maintained gem-solver lives in:
#   gear_optimizer.solver.taichi_gem
#
# Historically, this file also contained the gem solver implementation. To avoid
# drift and accidental imports from the legacy path, we keep those names as
# hard-fail stubs.
#

def _legacy_entrypoint(*_args, **_kwargs):
    raise RuntimeError(
        "Legacy module: only solve_force_greats_finder_gpu is supported here. "
        "Use gear_optimizer.solver.taichi_gem_solver (facade) / "
        "gear_optimizer.solver.taichi_gem.api for gem optimization."
    )


# Old/public names that should not be used from this legacy module.
optimize_gems_gpu = _legacy_entrypoint
optimize_gems_batch_gpu = _legacy_entrypoint
mega_batch_solve_population = _legacy_entrypoint
solve_genomes_with_ftff = _legacy_entrypoint
solve_genomes_parallel = _legacy_entrypoint

def mega_batch_solve_population(
    work_items: list,
    genome_ids: np.ndarray,
    genome_stats: dict,  # NEW: {genome_idx: (base_pp, base_cm, base_fm, base_p_val, base_s_val)}
    is_p_ft: int, is_s_ft: int,
    is_p_ff: int, is_s_ff: int,
    is_p_pp: int, is_s_pp: int,
    is_p_cm: int, is_s_cm: int,
    is_p_fm: int, is_s_fm: int,
    is_p_ov: int, is_s_ov: int,
    ref_arrays: dict,
) -> dict:
    """
    MEGA-BATCH solver - processes all work items from ALL genomes in one kernel.
    
    This is the highest-performance path: flatten all timelines from all genomes,
    launch one kernel, then reduce to find best score per genome.
    
    FIXED: Now accepts per-genome stats instead of shared stats.
    
    Args:
        work_items: Flattened list of all work items from all genomes
        genome_ids: np.ndarray mapping work_item index -> genome index
        genome_stats: Dict mapping genome_idx -> (base_pp, base_cm, base_fm, base_p_val, base_s_val)
        is_*: Color contribution flags (0/1)
        ref_arrays: Reference lookup tables
        
    Returns:
        dict: {genome_idx: (score, pp, cm, fm, p_val, s_val, g_pp, g_cm, g_fm, g_ov)}
    """
    global _ref_loaded
    
    n = len(work_items)
    if n == 0:
        return {}
    
    n_genomes = len(genome_stats)
    if n_genomes > MAX_GENOMES:
        raise ValueError(f"Number of genomes {n_genomes} exceeds maximum {MAX_GENOMES}")
    
    # Ensure Taichi is initialized
    if not _ti_initialized:
        init_taichi_vulkan()
    
    if not _fields_allocated:
        _allocate_fields()
    
    if not _ref_loaded:
        load_ref_arrays(ref_arrays)
    
    # Handle large batches by chunking
    if n > MAX_WORK_ITEMS:
        all_results = {}
        for chunk_start in range(0, n, MAX_WORK_ITEMS):
            chunk_end = min(chunk_start + MAX_WORK_ITEMS, n)
            chunk_items = work_items[chunk_start:chunk_end]
            chunk_genome_ids = genome_ids[chunk_start:chunk_end]
            chunk_results = mega_batch_solve_population(
                chunk_items, chunk_genome_ids, genome_stats,
                is_p_ft, is_s_ft, is_p_ff, is_s_ff,
                is_p_pp, is_s_pp, is_p_cm, is_s_cm,
                is_p_fm, is_s_fm, is_p_ov, is_s_ov,
                ref_arrays,
            )
            # Merge results (keep best per genome)
            for gid, result in chunk_results.items():
                if gid not in all_results or result[0] > all_results[gid][0]:
                    all_results[gid] = result
        return all_results
    
    # ========================================================================
    # UPLOAD PER-GENOME STATS (fixes the per-genome stats bug!)
    # ========================================================================
    
    genome_pp_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    genome_cm_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    genome_fm_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    genome_p_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    genome_s_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    
    for gid, (base_pp, base_cm, base_fm, base_p, base_s) in genome_stats.items():
        genome_pp_np[gid] = base_pp
        genome_cm_np[gid] = base_cm
        genome_fm_np[gid] = base_fm
        genome_p_np[gid] = base_p
        genome_s_np[gid] = base_s
    
    genome_base_pp.from_numpy(genome_pp_np)
    genome_base_cm.from_numpy(genome_cm_np)
    genome_base_fm.from_numpy(genome_fm_np)
    genome_base_p_val.from_numpy(genome_p_np)
    genome_base_s_val.from_numpy(genome_s_np)
    
    # ========================================================================
    # UPLOAD WORK ITEMS WITH GENOME IDS
    # ========================================================================
    
    staging = _ensure_mega_staging()
    budgets_np = staging["budgets"]
    count_fever_np = staging["count_fever"]
    count_normal_np = staging["count_normal"]
    ft_gems_np = staging["ft_gems"]
    ff_gems_np = staging["ff_gems"]
    head_len_np = staging["head_len"]
    genome_id_np = staging["genome_id"]
    fever_masks_np = staging["fever_masks"]
    
    for i, item in enumerate(work_items):
        budgets_np[i] = item["budget"]
        count_fever_np[i] = item["count_body_fever"]
        count_normal_np[i] = item["count_body_normal"]
        ft_gems_np[i] = item.get("ft_gems", 0)
        ff_gems_np[i] = item.get("ff_gems", 0)
        genome_id_np[i] = genome_ids[i]
        
        head_len_np[i] = 0
        mask = item.get("fever_mask_head")
        if mask is not None:
            head_len = min(len(mask), MAX_HEAD_NOTES)
            head_len_np[i] = head_len
            # Avoid per-item astype allocations: NumPy will cast on assignment.
            fever_masks_np[i, :head_len] = mask[:head_len]
    
    work_budgets.from_numpy(budgets_np)
    work_count_fever.from_numpy(count_fever_np)
    work_count_normal.from_numpy(count_normal_np)
    work_ft_gems.from_numpy(ft_gems_np)
    work_ff_gems.from_numpy(ff_gems_np)
    work_head_len.from_numpy(head_len_np)
    work_genome_id.from_numpy(genome_id_np)
    fever_masks.from_numpy(fever_masks_np)
    
    # Launch kernel (uses genome lookup for base stats)
    solve_batch_kernel(
        n,
        is_p_ft, is_s_ft, is_p_ff, is_s_ff,
        is_p_pp, is_s_pp, is_p_cm, is_s_cm,
        is_p_fm, is_s_fm, is_p_ov, is_s_ov,
    )
    
    ti.sync()
    
    # Download results
    scores_np = result_scores.to_numpy()[:n]
    pp_np = result_pp.to_numpy()[:n]
    cm_np = result_cm.to_numpy()[:n]
    fm_np = result_fm.to_numpy()[:n]
    ov_np = result_ov.to_numpy()[:n]
    p_val_np = result_p_val.to_numpy()[:n]
    s_val_np = result_s_val.to_numpy()[:n]
    
    # Reduce: find best score per genome
    best_per_genome = {}
    
    for i in range(n):
        genome_idx = int(genome_ids[i])
        score = int(scores_np[i])
        
        if genome_idx not in best_per_genome or score > best_per_genome[genome_idx][0]:
            best_per_genome[genome_idx] = (
                score,
                int(pp_np[i]), int(cm_np[i]), int(fm_np[i]),
                int(p_val_np[i]), int(s_val_np[i]),
                int(pp_np[i]), int(cm_np[i]), int(fm_np[i]), int(ov_np[i]),
                int(ft_gems_np[i]), int(ff_gems_np[i])  # Added FT/FF specific to this result
            )
    
    return best_per_genome


def solve_genomes_with_ftff(
    genome_stats_list: list,
    timeline_grid,
    is_p_ft: int, is_s_ft: int,
    is_p_ff: int, is_s_ff: int,
    is_p_pp: int, is_s_pp: int,
    is_p_cm: int, is_s_cm: int,
    is_p_fm: int, is_s_fm: int,
    is_p_ov: int, is_s_ov: int,
    ref_arrays: dict,
    total_budget: int = 90,
    gem_scale_fever: int = 3,
) -> list:
    """
    NEW: Solve gem allocation for multiple genomes with GPU-resident FT/FF iteration.
    
    This function uploads the timeline grid ONCE, then processes all genomes
    in a single kernel launch that iterates FT/FF combinations on-GPU.
    
    This is ~100x faster than the old approach which transferred 400k work items.
    
    Args:
        genome_stats_list: List of dicts, each with keys:
            - base_pp, base_cm, base_fm, base_p_val, base_s_val
            - base_ft_stat, base_ff_stat
        timeline_grid: SongTimelineGrid object (must have precompute_all() called)
        is_*: Color contribution flags (0/1)
        ref_arrays: Reference lookup arrays
        total_budget: Total gem budget (default 90)
        gem_scale_fever: Stat points per fever gem (default 3)
        
    Returns:
        List of result tuples: (score, ft, ff, pp, cm, fm, ov) per genome
    """
    if not _ti_initialized:
        init_taichi_vulkan()
    
    if not _fields_allocated:
        _allocate_fields()
    
    if not _grid_fields_allocated:
        _allocate_grid_fields()
    
    # Upload reference arrays if needed
    global _ref_loaded
    if not _ref_loaded:
        load_ref_arrays(ref_arrays)
    
    n_genomes = len(genome_stats_list)
    if n_genomes == 0:
        return []
    
    if n_genomes > MAX_GENOMES:
        raise ValueError(f"Too many genomes: {n_genomes} > {MAX_GENOMES}")
    
    # Upload timeline grid to GPU (once per song)
    _upload_timeline_grid(timeline_grid)
    
    # Upload per-genome stats
    pp_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    cm_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    fm_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    p_val_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    s_val_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    ft_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    ff_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    
    for i, stats in enumerate(genome_stats_list):
        pp_np[i] = stats["base_pp"]
        cm_np[i] = stats["base_cm"]
        fm_np[i] = stats["base_fm"]
        p_val_np[i] = stats["base_p_val"]
        s_val_np[i] = stats["base_s_val"]
        ft_np[i] = stats["base_ft_stat"]
        ff_np[i] = stats["base_ff_stat"]
    
    genome_base_pp.from_numpy(pp_np)
    genome_base_cm.from_numpy(cm_np)
    genome_base_fm.from_numpy(fm_np)
    genome_base_p_val.from_numpy(p_val_np)
    genome_base_s_val.from_numpy(s_val_np)
    genome_base_ft.from_numpy(ft_np)
    genome_base_ff.from_numpy(ff_np)
    
    # Launch kernel
    solve_genomes_with_ftff_kernel(
        n_genomes,
        total_budget,
        gem_scale_fever,
        is_p_ft, is_s_ft, is_p_ff, is_s_ff,
        is_p_pp, is_s_pp, is_p_cm, is_s_cm,
        is_p_fm, is_s_fm, is_p_ov, is_s_ov,
    )
    
    ti.sync()
    
    # Download results
    scores_np = genome_result_scores.to_numpy()[:n_genomes]
    ft_out_np = genome_result_ft.to_numpy()[:n_genomes]
    ff_out_np = genome_result_ff.to_numpy()[:n_genomes]
    pp_out_np = genome_result_pp.to_numpy()[:n_genomes]
    cm_out_np = genome_result_cm.to_numpy()[:n_genomes]
    fm_out_np = genome_result_fm.to_numpy()[:n_genomes]
    ov_out_np = genome_result_ov.to_numpy()[:n_genomes]
    
    results = []
    for i in range(n_genomes):
        results.append((
            int(scores_np[i]),
            int(ft_out_np[i]),
            int(ff_out_np[i]),
            int(pp_out_np[i]),
            int(cm_out_np[i]),
            int(fm_out_np[i]),
            int(ov_out_np[i]),
        ))
    
    return results


_grid_uploaded = False


def _upload_timeline_grid(timeline_grid):
    """Upload timeline grid to GPU fields (with caching)."""
    global _grid_uploaded, _last_uploaded_grid_id
    
    # Skip if same grid already uploaded (major optimization!)
    grid_id = id(timeline_grid)
    if _grid_uploaded and _last_uploaded_grid_id == grid_id:
        return
    
    # Ensure all timelines are computed
    timeline_grid.precompute_all()
    
    # Get grid data
    grid_size = timeline_grid.GRID_SIZE
    
    # Allocate numpy arrays
    cbf_np = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.int32)
    cbn_np = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.int32)
    hl_np = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.int32)
    masks_np = np.zeros((GRID_SIZE, GRID_SIZE, MAX_HEAD_NOTES), dtype=np.int8)
    masks_bits_np = np.zeros((GRID_SIZE, GRID_SIZE, 4), dtype=np.uint32)
    
    # Fill from grid
    for ft_idx in range(grid_size):
        for ff_idx in range(grid_size):
            timeline = timeline_grid._timeline_grid[ft_idx][ff_idx]
            if timeline is not None:
                fever_mask_head, count_fever, count_normal, _ = timeline
                cbf_np[ft_idx, ff_idx] = count_fever
                cbn_np[ft_idx, ff_idx] = count_normal
                head_len = min(len(fever_mask_head), MAX_HEAD_NOTES)
                hl_np[ft_idx, ff_idx] = head_len
                head_slice = fever_mask_head[:head_len]
                masks_np[ft_idx, ff_idx, :head_len] = head_slice.astype(np.int8)

                # Pack head_slice into 4x u32 bitset (covers up to 128 bits; we need 100)
                w0 = np.uint32(0)
                w1 = np.uint32(0)
                w2 = np.uint32(0)
                w3 = np.uint32(0)
                for i in range(head_len):
                    if head_slice[i]:
                        bit = np.uint32(1) << np.uint32(i & 31)
                        word = i >> 5
                        if word == 0:
                            w0 |= bit
                        elif word == 1:
                            w1 |= bit
                        elif word == 2:
                            w2 |= bit
                        else:
                            w3 |= bit
                masks_bits_np[ft_idx, ff_idx, 0] = w0
                masks_bits_np[ft_idx, ff_idx, 1] = w1
                masks_bits_np[ft_idx, ff_idx, 2] = w2
                masks_bits_np[ft_idx, ff_idx, 3] = w3
    
    # Upload to GPU
    grid_count_body_fever.from_numpy(cbf_np)
    grid_count_body_normal.from_numpy(cbn_np)
    grid_head_len.from_numpy(hl_np)
    grid_fever_masks.from_numpy(masks_np)
    grid_fever_masks_bits.from_numpy(masks_bits_np)
    
    _grid_uploaded = True
    _last_uploaded_grid_id = grid_id


# ============================================================================
# FORCE GREATs FINDER - PYTHON WRAPPER
# ============================================================================

_fg_last_song_key = None
_fg_song_upload_buf = None
_fg_forced_upload_buf = None
_fg_ftff_upload_buf = None


def _fg_upload_song_timestamps(timestamps_np: np.ndarray):
    """Upload song timestamps to GPU (cached by (len, first, last))."""
    global _fg_last_song_key, _fg_song_upload_buf
    n = int(len(timestamps_np))
    if n <= 0:
        return 0
    if n > FG_MAX_SONG_NOTES:
        raise ValueError(f"Song too long for FG GPU timestamps: {n} > {FG_MAX_SONG_NOTES}")

    key = (n, float(timestamps_np[0]), float(timestamps_np[-1]))
    if _fg_last_song_key == key:
        return n

    if _fg_song_upload_buf is None:
        _fg_song_upload_buf = np.zeros((FG_MAX_SONG_NOTES,), dtype=np.float32)
    buf = _fg_song_upload_buf
    buf[:n] = np.asarray(timestamps_np, dtype=np.float32)
    if n < FG_MAX_SONG_NOTES:
        buf[n:] = 0.0
    song_timestamps.from_numpy(buf)
    _fg_last_song_key = key
    return n


def solve_force_greats_finder_gpu(
    genome_stats_list: list,
    timestamps_np: np.ndarray,
    long_notes: int,
    last_note_time: float,
    fg_configs: list,
    ftff_pairs: list,
    *,
    n_sections: int,
    is_p_ft: int, is_s_ft: int,
    is_p_ff: int, is_s_ff: int,
    is_p_pp: int, is_s_pp: int,
    is_p_cm: int, is_s_cm: int,
    is_p_fm: int, is_s_fm: int,
    is_p_ov: int, is_s_ov: int,
    ref_arrays: dict,
    total_budget: int = 90,
    gem_scale_fever: int = 3,
    cfg_chunk: int = 2048,
) -> list:
    """
    Full GPU ForceGreatsFinder (tolerant mode).

    Returns list aligned with genome_stats_list:
      dict with keys: base_score, final_score, cfg_idx, ft, ff, gems_pp/cm/fm/ov, score_penalty, fill_penalty
    """
    if not genome_stats_list:
        return []

    if not _ti_initialized:
        init_taichi_vulkan()
    if not _fields_allocated:
        _allocate_fields()
    if not _ref_loaded:
        load_ref_arrays(ref_arrays)

    if "Fever Time" not in ref_arrays or "Fever Fill Rate" not in ref_arrays:
        raise KeyError("FG finder GPU requires ref_arrays to include 'Fever Time' and 'Fever Fill Rate'")

    n_genomes = len(genome_stats_list)
    if n_genomes > MAX_GENOMES:
        raise ValueError(f"Too many genomes for FG finder: {n_genomes} > {MAX_GENOMES}")

    total_notes = _fg_upload_song_timestamps(timestamps_np)
    if total_notes <= 0:
        return []

    # Upload per-genome stats
    pp_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    cm_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    fm_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    p_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    s_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    ft_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    ff_np = np.zeros(MAX_GENOMES, dtype=np.int32)

    for i, st in enumerate(genome_stats_list):
        pp_np[i] = int(st.get("base_pp", 0))
        cm_np[i] = int(st.get("base_cm", 0))
        fm_np[i] = int(st.get("base_fm", 0))
        p_np[i] = int(st.get("base_p_val", 0))
        s_np[i] = int(st.get("base_s_val", 0))
        ft_np[i] = int(st.get("base_ft_stat", 0))
        ff_np[i] = int(st.get("base_ff_stat", 0))

    genome_base_pp.from_numpy(pp_np)
    genome_base_cm.from_numpy(cm_np)
    genome_base_fm.from_numpy(fm_np)
    genome_base_p_val.from_numpy(p_np)
    genome_base_s_val.from_numpy(s_np)
    genome_base_ft.from_numpy(ft_np)
    genome_base_ff.from_numpy(ff_np)

    # Upload FT/FF list (small)
    n_ftff = len(ftff_pairs)
    if n_ftff <= 0:
        return []
    if n_ftff > FG_MAX_FTFF:
        raise ValueError(f"Too many FT/FF pairs: {n_ftff} > {FG_MAX_FTFF}")
    global _fg_ftff_upload_buf
    if _fg_ftff_upload_buf is None:
        _fg_ftff_upload_buf = {
            "ft": np.zeros((FG_MAX_FTFF,), dtype=np.int32),
            "ff": np.zeros((FG_MAX_FTFF,), dtype=np.int32),
        }
    ft_buf = _fg_ftff_upload_buf["ft"]
    ff_buf = _fg_ftff_upload_buf["ff"]
    ft_buf[:n_ftff] = 0
    ff_buf[:n_ftff] = 0
    for i, (ftg, ffg) in enumerate(ftff_pairs):
        ft_buf[i] = int(ftg)
        ff_buf[i] = int(ffg)
    fg_ft_list.from_numpy(ft_buf)
    fg_ff_list.from_numpy(ff_buf)

    # Reset best outputs
    fg_reset_best_kernel(n_genomes)

    # Upload configs in chunks and run kernel
    n_cfg_total = len(fg_configs)
    if n_cfg_total <= 0:
        return []
    if n_sections <= 0:
        n_sections = 1
    if n_sections > FG_MAX_SECTIONS:
        raise ValueError(f"Too many FG sections: {n_sections} > {FG_MAX_SECTIONS}")
    global _fg_forced_upload_buf
    if _fg_forced_upload_buf is None:
        _fg_forced_upload_buf = np.zeros((FG_MAX_CONFIGS, FG_MAX_SECTIONS), dtype=np.int32)

    cfg_chunk = int(cfg_chunk) if int(cfg_chunk) > 0 else FG_MAX_CONFIGS
    cfg_chunk = min(cfg_chunk, FG_MAX_CONFIGS)


    # Initialize Stage 1 intermediate fields before processing chunks
    fg_stage1_init_kernel(n_genomes, n_ftff)
    ti.sync()

    for cfg_offset in range(0, n_cfg_total, cfg_chunk):
        chunk = fg_configs[cfg_offset:cfg_offset + cfg_chunk]
        n_cfg = len(chunk)
        # Fill forced counts staging
        buf = _fg_forced_upload_buf
        buf[:n_cfg, :n_sections] = 0
        for i, cfg in enumerate(chunk):
            for s in range(min(n_sections, len(cfg))):
                buf[i, s] = int(cfg[s])
        # Zero remainder of section columns for these rows
        if n_sections < FG_MAX_SECTIONS:
            buf[:n_cfg, n_sections:] = 0
        # Upload full buffer (fixed shape field)
        fg_forced_counts.from_numpy(buf)

        # Use TWO-STAGE REDUCTION instead of atomic kernel
        # Stage 1: Find best cfg per (genome, ftff) - sequential cfg loop, no atomics
        fg_stage1_kernel(
            n_genomes,
            int(total_notes),
            int(long_notes),
            float(last_note_time),
            int(total_budget),
            int(gem_scale_fever),
            int(n_cfg),
            int(n_sections),
            int(n_ftff),
            int(cfg_offset),
            int(is_p_ft), int(is_s_ft),
            int(is_p_ff), int(is_s_ff),
            int(is_p_pp), int(is_s_pp),
            int(is_p_cm), int(is_s_cm),
            int(is_p_fm), int(is_s_fm),
            int(is_p_ov), int(is_s_ov),
        )
        ti.sync()

    # Stage 2: Reduce across ftff to find best per genome
    fg_stage2_kernel(n_genomes, n_ftff)
    ti.sync()


    # Download results
    out_final = fg_best_final_score.to_numpy()[:n_genomes]
    out_base = fg_best_base_score.to_numpy()[:n_genomes]
    out_cfg = fg_best_cfg_idx.to_numpy()[:n_genomes]
    out_ft = fg_best_ft.to_numpy()[:n_genomes]
    out_ff = fg_best_ff.to_numpy()[:n_genomes]
    out_gpp = fg_best_g_pp.to_numpy()[:n_genomes]
    out_gcm = fg_best_g_cm.to_numpy()[:n_genomes]
    out_gfm = fg_best_g_fm.to_numpy()[:n_genomes]
    out_gov = fg_best_g_ov.to_numpy()[:n_genomes]
    out_sp = fg_best_score_penalty.to_numpy()[:n_genomes]
    out_fp = fg_best_fill_penalty.to_numpy()[:n_genomes]

    results = []
    for i in range(n_genomes):
        results.append({
            "final_score": int(out_final[i]),
            "base_score": int(out_base[i]),
            "cfg_idx": int(out_cfg[i]),
            "FT": int(out_ft[i]),
            "FF": int(out_ff[i]),
            "gem_counts": {
                "Perfect Points": int(out_gpp[i]),
                "Combo Multiplier": int(out_gcm[i]),
                "Fever Multiplier": int(out_gfm[i]),
                "Element Overflow": int(out_gov[i]),
            },
            "score_penalty": int(out_sp[i]),
            "fill_penalty": int(out_fp[i]),
        })
    return results


def solve_genomes_parallel(
    genome_stats_list: list,
    timeline_grid,
    is_p_ft: int, is_s_ft: int,
    is_p_ff: int, is_s_ff: int,
    is_p_pp: int, is_s_pp: int,
    is_p_cm: int, is_s_cm: int,
    is_p_fm: int, is_s_fm: int,
    is_p_ov: int, is_s_ov: int,
    ref_arrays: dict,
    total_budget: int = 90,
    gem_scale_fever: int = 3,
) -> list:
    """
    V2: Solve gem allocation with MAXIMUM parallelism.
    
    Parallelizes across (genome, ft, ff) combinations = ~400k threads.
    This combines the parallelism of the old approach with the low transfer
    overhead of the new approach.
    
    Args:
        genome_stats_list: List of dicts with base stats per genome
        timeline_grid: SongTimelineGrid (precompute_all will be called)
        is_*: Color contribution flags (0/1)
        ref_arrays: Reference lookup arrays
        total_budget: Gem budget (default 90)
        gem_scale_fever: Stats per fever gem (default 3)
        
    Returns:
        List of (score, ft, ff, pp, cm, fm, ov) tuples per genome
    """
    if not _ti_initialized:
        init_taichi_vulkan()
    
    if not _fields_allocated:
        _allocate_fields()
    
    if not _grid_fields_allocated:
        _allocate_grid_fields()
    
    global _ref_loaded
    if not _ref_loaded:
        load_ref_arrays(ref_arrays)
    
    n_genomes = len(genome_stats_list)
    if n_genomes == 0:
        return []
    
    if n_genomes > MAX_GENOMES:
        raise ValueError(f"Too many genomes: {n_genomes} > {MAX_GENOMES}")
    
    # Upload timeline grid
    _upload_timeline_grid(timeline_grid)
    
    # Upload per-genome stats
    pp_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    cm_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    fm_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    p_val_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    s_val_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    ft_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    ff_np = np.zeros(MAX_GENOMES, dtype=np.int32)
    
    # Also track max allowed FT/FF per genome for work item generation
    max_ft_list = []
    max_ff_list = []
    
    for i, stats in enumerate(genome_stats_list):
        pp_np[i] = stats["base_pp"]
        cm_np[i] = stats["base_cm"]
        fm_np[i] = stats["base_fm"]
        p_val_np[i] = stats["base_p_val"]
        s_val_np[i] = stats["base_s_val"]
        ft_np[i] = stats["base_ft_stat"]
        ff_np[i] = stats["base_ff_stat"]
        
        # Compute max FT/FF gems
        remaining_ft = 160 - stats["base_ft_stat"]
        remaining_ff = 160 - stats["base_ff_stat"]
        max_ft = remaining_ft // gem_scale_fever if remaining_ft > 0 else 0
        max_ff = remaining_ff // gem_scale_fever if remaining_ff > 0 else 0
        max_ft_list.append(min(total_budget, max_ft))
        max_ff_list.append(min(total_budget, max_ff))
    
    genome_base_pp.from_numpy(pp_np)
    genome_base_cm.from_numpy(cm_np)
    genome_base_fm.from_numpy(fm_np)
    genome_base_p_val.from_numpy(p_val_np)
    genome_base_s_val.from_numpy(s_val_np)
    genome_base_ft.from_numpy(ft_np)
    genome_base_ff.from_numpy(ff_np)
    
    # Generate work items: (genome_id, ft, ff) for all valid combinations
    work_genome = []
    work_ft = []
    work_ff = []
    
    for genome_idx in range(n_genomes):
        max_ft = max_ft_list[genome_idx]
        max_ff = max_ff_list[genome_idx]
        
        for ft in range(max_ft + 1):
            remaining = total_budget - ft
            for ff in range(min(remaining, max_ff) + 1):
                work_genome.append(genome_idx)
                work_ft.append(ft)
                work_ff.append(ff)
    
    n_work = len(work_genome)
    
    if n_work == 0:
        return [(0, 0, 0, 0, 0, 0, 0) for _ in range(n_genomes)]
    
    # Track best results per genome across all chunks
    best_per_genome = {}
    
    # Process in chunks if exceeds MAX_WORK_ITEMS
    chunk_size = MAX_WORK_ITEMS
    num_chunks = (n_work + chunk_size - 1) // chunk_size
    
    for chunk_idx in range(num_chunks):
        start = chunk_idx * chunk_size
        end = min(start + chunk_size, n_work)
        chunk_n = end - start
        
        # Upload work items for this chunk
        genome_id_np = np.zeros(MAX_WORK_ITEMS, dtype=np.int32)
        ft_gems_np = np.zeros(MAX_WORK_ITEMS, dtype=np.int32)
        ff_gems_np = np.zeros(MAX_WORK_ITEMS, dtype=np.int32)
        
        genome_id_np[:chunk_n] = work_genome[start:end]
        ft_gems_np[:chunk_n] = work_ft[start:end]
        ff_gems_np[:chunk_n] = work_ff[start:end]
        
        work_genome_id.from_numpy(genome_id_np)
        work_ft_gems.from_numpy(ft_gems_np)
        work_ff_gems.from_numpy(ff_gems_np)
        
        # Launch kernel
        solve_ftff_parallel_kernel(
            chunk_n,
            total_budget,
            gem_scale_fever,
            is_p_ft, is_s_ft, is_p_ff, is_s_ff,
            is_p_pp, is_s_pp, is_p_cm, is_s_cm,
            is_p_fm, is_s_fm, is_p_ov, is_s_ov,
        )
        
        ti.sync()
        
        # Download results for this chunk
        scores_np = result_scores.to_numpy()[:chunk_n]
        pp_out = result_pp.to_numpy()[:chunk_n]
        cm_out = result_cm.to_numpy()[:chunk_n]
        fm_out = result_fm.to_numpy()[:chunk_n]
        ov_out = result_ov.to_numpy()[:chunk_n]
        
        # Reduce: find best score per genome (merge with global best)
        for i in range(chunk_n):
            gid = work_genome[start + i]
            score = int(scores_np[i])
            
            if gid not in best_per_genome or score > best_per_genome[gid][0]:
                best_per_genome[gid] = (
                    score,
                    work_ft[start + i],
                    work_ff[start + i],
                    int(pp_out[i]),
                    int(cm_out[i]),
                    int(fm_out[i]),
                    int(ov_out[i]),
                )
    
    # Return in order
    results = []
    for i in range(n_genomes):
        if i in best_per_genome:
            results.append(best_per_genome[i])
        else:
            results.append((0, 0, 0, 0, 0, 0, 0))
    
    return results


