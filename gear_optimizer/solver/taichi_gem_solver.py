"""
Taichi-based GPU gem solver for Vulkan backend.

This module contains GPU-accelerated implementations of the Compute Layer
functions from scoring_core.py. Designed for AMD GPUs (RX 7900 XTX) via Vulkan.

Architecture:
- Reference arrays are loaded into ti.field() on GPU
- Batch kernel processes multiple FT/FF combinations in parallel
- Each GPU thread runs one complete greedy gem optimization
"""
import taichi as ti
import numpy as np
from math import floor

from ..core.constants import (
    TOTAL_ROWS,
    MAX_STAT_INDEX,
    GEM_SCALE_NORMAL,
    GEM_SCALE_FEVER,
    GEM_STAT_TO_ELEMENT_SCALE,
    ELEMENTAL_GEM_SCALE,
    TOTAL_GEM_BUDGET,
)
from ..core.math_utils import ti_floor_eps

# =============================================================================
# Module State
# =============================================================================
_initialized = False

# Reference array fields (loaded once per session)
ref_pp_field = None
ref_cm_field = None
ref_fm_field = None

# Batch fever mask field: [batch_idx, head_note_idx]
fever_mask_batch_field = None

# Constants
HEAD_LIMIT = 100
MAX_BATCH_SIZE = 65536  # Max work items for mega-batch (200 genomes × 300 timelines)

# Single fever mask for backwards compatibility
fever_mask_field = None


def init_taichi_vulkan():
    """
    Initialize Taichi with Vulkan backend for AMD GPUs.
    
    Should be called once at application startup.
    """
    global _initialized, ref_pp_field, ref_cm_field, ref_fm_field
    global fever_mask_field, fever_mask_batch_field
    
    if _initialized:
        return
    
    # Initialize Taichi with Vulkan (AMD-compatible)
    ti.init(arch=ti.vulkan, debug=False)
    
    # Allocate reference array fields
    grid_size = TOTAL_ROWS + 1  # 0-160 inclusive = 161
    ref_pp_field = ti.field(dtype=ti.f32, shape=(grid_size,))
    ref_cm_field = ti.field(dtype=ti.f32, shape=(grid_size,))
    ref_fm_field = ti.field(dtype=ti.f32, shape=(grid_size,))
    
    # Fever mask for head notes (max 100 notes) - single version
    fever_mask_field = ti.field(dtype=ti.i32, shape=(HEAD_LIMIT,))
    
    # Batch fever masks: [batch_idx][head_note_idx]
    fever_mask_batch_field = ti.field(dtype=ti.i32, shape=(MAX_BATCH_SIZE, HEAD_LIMIT))
    
    _initialized = True
    print("[Taichi] Vulkan backend initialized for GPU gem solver (batched)")


def load_ref_arrays(ref_arrays: dict):
    """
    Load reference arrays from CPU to GPU fields.
    
    Args:
        ref_arrays: Dict with "Perfect Points", "Combo Multiplier", "Fever Multiplier"
    """
    if not _initialized:
        init_taichi_vulkan()
    
    # Copy numpy arrays to Taichi fields
    ref_pp_field.from_numpy(ref_arrays["Perfect Points"].astype(np.float32))
    ref_cm_field.from_numpy(ref_arrays["Combo Multiplier"].astype(np.float32))
    ref_fm_field.from_numpy(ref_arrays["Fever Multiplier"].astype(np.float32))


def load_fever_mask(fever_mask_head: np.ndarray):
    """
    Load fever mask for head notes to GPU (single mask).
    
    Args:
        fever_mask_head: Boolean array (length <= 100) marking fever notes
    """
    if not _initialized:
        init_taichi_vulkan()
    
    # Pad to HEAD_LIMIT if shorter
    padded = np.zeros(HEAD_LIMIT, dtype=np.int32)
    n = min(len(fever_mask_head), HEAD_LIMIT)
    padded[:n] = fever_mask_head[:n].astype(np.int32)
    fever_mask_field.from_numpy(padded)


def load_fever_masks_batch(fever_masks: list, n_head_list: list):
    """
    Load batch of fever masks to GPU for parallel processing.
    
    Args:
        fever_masks: List of boolean arrays (each length <= 100)
        n_head_list: List of actual head lengths for each mask
        
    Returns:
        int: Number of masks loaded
    """
    if not _initialized:
        init_taichi_vulkan()
    
    batch_size = min(len(fever_masks), MAX_BATCH_SIZE)
    
    # Create numpy batch array
    batch_array = np.zeros((MAX_BATCH_SIZE, HEAD_LIMIT), dtype=np.int32)
    
    for i in range(batch_size):
        mask = fever_masks[i]
        n = min(len(mask), HEAD_LIMIT)
        batch_array[i, :n] = mask[:n].astype(np.int32)
    
    fever_mask_batch_field.from_numpy(batch_array)
    return batch_size


# =============================================================================
# Taichi Kernels - Core Functions
# =============================================================================

@ti.func
def lookup_reference_ti(value: ti.i32, ref_field: ti.template()) -> ti.f32:
    """
    GPU reference lookup - clamps index and returns value.
    """
    idx = value
    if idx > TOTAL_ROWS:
        idx = TOTAL_ROWS
    elif idx < 0:
        idx = 0
    return ref_field[idx]


@ti.func
def calc_score_batch_ti(
    base_value: ti.f32,
    combo_mul: ti.f32,
    fever_mul: ti.f32,
    batch_idx: ti.i32,
    n_head: ti.i32,
    count_body_fever: ti.i32,
    count_body_normal: ti.i32,
) -> ti.i32:
    """
    GPU score calculation using batch fever mask.
    
    Uses fever_mask_batch_field[batch_idx] for the fever mask.
    """
    combo_val_per_note = ti_floor_eps(base_value * combo_mul)
    fever_val_per_note = ti_floor_eps(base_value * combo_mul * fever_mul)
    
    body_score = (count_body_fever * fever_val_per_note) + (
        count_body_normal * combo_val_per_note
    )
    
    factor = (combo_mul - 1.0) * base_value / 100.0
    total_head = 0.0
    
    for i in range(n_head):
        current_ramp_val = base_value + ((i + 1) * factor)
        val = ti_floor_eps(current_ramp_val)  # Default: normal note
        if fever_mask_batch_field[batch_idx, i] != 0:
            val = ti_floor_eps(current_ramp_val * fever_mul)
        total_head += val
    
    return ti.cast(body_score + total_head, ti.i32)


@ti.func
def calc_score_ti(
    base_value: ti.f32,
    combo_mul: ti.f32,
    fever_mul: ti.f32,
    n_head: ti.i32,
    count_body_fever: ti.i32,
    count_body_normal: ti.i32,
) -> ti.i32:
    """
    GPU score calculation (single mask version for backwards compatibility).
    """
    combo_val_per_note = ti_floor_eps(base_value * combo_mul)
    fever_val_per_note = ti_floor_eps(base_value * combo_mul * fever_mul)
    
    body_score = (count_body_fever * fever_val_per_note) + (
        count_body_normal * combo_val_per_note
    )
    
    factor = (combo_mul - 1.0) * base_value / 100.0
    total_head = 0.0
    
    for i in range(n_head):
        current_ramp_val = base_value + ((i + 1) * factor)
        val = ti_floor_eps(current_ramp_val)
        if fever_mask_field[i] != 0:
            val = ti_floor_eps(current_ramp_val * fever_mul)
        total_head += val
    
    return ti.cast(body_score + total_head, ti.i32)


@ti.func
def run_greedy_optimization(
    batch_idx: ti.i32,
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
    n_head: ti.i32,
    count_body_fever: ti.i32,
    count_body_normal: ti.i32,
) -> ti.types.vector(10, ti.i32):
    """
    Greedy gem optimization for a single batch element.
    
    Returns vector: [score, pp, cm, fm, p_val, s_val, gems_pp, gems_cm, gems_fm, gems_ov]
    """
    pp = cur_pp
    cm = cur_cm
    fm = cur_fm
    p_val = cur_p_val
    s_val = cur_s_val
    gems_pp = 0
    gems_cm = 0
    gems_fm = 0
    gems_ov = 0
    remaining = budget
    
    while remaining > 0:
        best_score = ti.cast(-1, ti.f32)
        best_opt_idx = -1
        fill_budget = remaining - 1
        fill_bonus = fill_budget * ELEMENTAL_GEM_SCALE if fill_budget > 0 else 0
        
        # Option 0: PP gem
        if pp < MAX_STAT_INDEX:
            t_pp = pp + GEM_SCALE_NORMAL
            t_p = p_val + (GEM_STAT_TO_ELEMENT_SCALE * is_p_pp) + (fill_bonus * is_p_ov)
            t_s = s_val + (GEM_STAT_TO_ELEMENT_SCALE * is_s_pp) + (fill_bonus * is_s_ov)
            pp_factor = lookup_reference_ti(t_pp, ref_pp_field)
            base = (t_p * 2.0) + t_s + pp_factor
            c_mul = lookup_reference_ti(cm, ref_cm_field)
            f_mul = lookup_reference_ti(fm, ref_fm_field)
            score = ti.cast(calc_score_batch_ti(base, c_mul, f_mul, batch_idx, n_head, count_body_fever, count_body_normal), ti.f32)
            if score >= best_score:
                best_score = score
                best_opt_idx = 0
        
        # Option 1: CM gem
        if cm < MAX_STAT_INDEX:
            t_cm = cm + GEM_SCALE_NORMAL
            t_p = p_val + (GEM_STAT_TO_ELEMENT_SCALE * is_p_cm) + (fill_bonus * is_p_ov)
            t_s = s_val + (GEM_STAT_TO_ELEMENT_SCALE * is_s_cm) + (fill_bonus * is_s_ov)
            pp_factor = lookup_reference_ti(pp, ref_pp_field)
            base = (t_p * 2.0) + t_s + pp_factor
            c_mul = lookup_reference_ti(t_cm, ref_cm_field)
            f_mul = lookup_reference_ti(fm, ref_fm_field)
            score = ti.cast(calc_score_batch_ti(base, c_mul, f_mul, batch_idx, n_head, count_body_fever, count_body_normal), ti.f32)
            if score > best_score:
                best_score = score
                best_opt_idx = 1
        
        # Option 2: FM gem
        if fm < MAX_STAT_INDEX:
            t_fm = fm + GEM_SCALE_FEVER
            t_p = p_val + (GEM_STAT_TO_ELEMENT_SCALE * is_p_fm) + (fill_bonus * is_p_ov)
            t_s = s_val + (GEM_STAT_TO_ELEMENT_SCALE * is_s_fm) + (fill_bonus * is_s_ov)
            pp_factor = lookup_reference_ti(pp, ref_pp_field)
            base = (t_p * 2.0) + t_s + pp_factor
            c_mul = lookup_reference_ti(cm, ref_cm_field)
            f_mul = lookup_reference_ti(t_fm, ref_fm_field)
            score = ti.cast(calc_score_batch_ti(base, c_mul, f_mul, batch_idx, n_head, count_body_fever, count_body_normal), ti.f32)
            if score > best_score:
                best_score = score
                best_opt_idx = 2
        
        # Option 3: Overflow (elemental gem)
        t_p = p_val + (ELEMENTAL_GEM_SCALE * is_p_ov) + (fill_bonus * is_p_ov)
        t_s = s_val + (ELEMENTAL_GEM_SCALE * is_s_ov) + (fill_bonus * is_s_ov)
        pp_factor = lookup_reference_ti(pp, ref_pp_field)
        base = (t_p * 2.0) + t_s + pp_factor
        c_mul = lookup_reference_ti(cm, ref_cm_field)
        f_mul = lookup_reference_ti(fm, ref_fm_field)
        score = ti.cast(calc_score_batch_ti(base, c_mul, f_mul, batch_idx, n_head, count_body_fever, count_body_normal), ti.f32)
        if score >= best_score:
            best_score = score
            best_opt_idx = 3
        
        # Apply best option
        if best_opt_idx == 0:
            pp += GEM_SCALE_NORMAL
            p_val += GEM_STAT_TO_ELEMENT_SCALE * is_p_pp
            s_val += GEM_STAT_TO_ELEMENT_SCALE * is_s_pp
            gems_pp += 1
        elif best_opt_idx == 1:
            cm += GEM_SCALE_NORMAL
            p_val += GEM_STAT_TO_ELEMENT_SCALE * is_p_cm
            s_val += GEM_STAT_TO_ELEMENT_SCALE * is_s_cm
            gems_cm += 1
        elif best_opt_idx == 2:
            fm += GEM_SCALE_FEVER
            p_val += GEM_STAT_TO_ELEMENT_SCALE * is_p_fm
            s_val += GEM_STAT_TO_ELEMENT_SCALE * is_s_fm
            gems_fm += 1
        else:
            p_val += ELEMENTAL_GEM_SCALE * is_p_ov
            s_val += ELEMENTAL_GEM_SCALE * is_s_ov
            gems_ov += 1
        
        remaining -= 1
    
    # Calculate final score
    pp_factor = lookup_reference_ti(pp, ref_pp_field)
    base = (p_val * 2.0) + s_val + pp_factor
    c_mul = lookup_reference_ti(cm, ref_cm_field)
    f_mul = lookup_reference_ti(fm, ref_fm_field)
    final_score = calc_score_batch_ti(base, c_mul, f_mul, batch_idx, n_head, count_body_fever, count_body_normal)
    
    return ti.Vector([final_score, pp, cm, fm, p_val, s_val, gems_pp, gems_cm, gems_fm, gems_ov], dt=ti.i32)


# =============================================================================
# Batched Parallel Kernel
# =============================================================================

@ti.kernel
def optimize_gems_batch_kernel(
    batch_size: ti.i32,
    # Per-batch inputs (arrays)
    budgets: ti.types.ndarray(),
    n_heads: ti.types.ndarray(),
    body_fevers: ti.types.ndarray(),
    body_normals: ti.types.ndarray(),
    ft_gems: ti.types.ndarray(),    # FT gems per batch to calc p_val
    ff_gems: ti.types.ndarray(),    # FF gems per batch to calc s_val
    # Shared inputs (same for all batches)
    cur_pp: ti.i32,
    cur_cm: ti.i32,
    cur_fm: ti.i32,
    base_p_val: ti.i32,  # Base primary color val (before FT/FF gems)
    base_s_val: ti.i32,  # Base secondary color val (before FT/FF gems)
    # Color contribution flags for FT/FF
    is_p_ft: ti.i32,  # Does FT gem contribute to primary? (Beat)
    is_s_ft: ti.i32,  # Does FT gem contribute to secondary? (Beat)
    is_p_ff: ti.i32,  # Does FF gem contribute to primary? (Vibe)
    is_s_ff: ti.i32,  # Does FF gem contribute to secondary? (Vibe)
    # Existing flags
    is_p_pp: ti.i32,
    is_s_pp: ti.i32,
    is_p_cm: ti.i32,
    is_s_cm: ti.i32,
    is_p_fm: ti.i32,
    is_s_fm: ti.i32,
    is_p_ov: ti.i32,
    is_s_ov: ti.i32,
    # Output: [batch_idx, 10 values]
    results: ti.types.ndarray(),
):
    """
    Batched parallel gem optimization - GPU-resident.
    
    Each GPU thread processes one FT/FF combination independently.
    cur_p_val/cur_s_val computed per-batch on GPU based on FT/FF gems.
    
    Results layout per batch: [score, pp, cm, fm, p_val, s_val, gems_pp, gems_cm, gems_fm, gems_ov]
    """
    for i in range(batch_size):
        # Compute per-batch p_val/s_val from FT/FF gems
        ft = ft_gems[i]
        ff = ff_gems[i]
        cur_p_val = base_p_val + (ft * GEM_STAT_TO_ELEMENT_SCALE * is_p_ft) + (ff * GEM_STAT_TO_ELEMENT_SCALE * is_p_ff)
        cur_s_val = base_s_val + (ft * GEM_STAT_TO_ELEMENT_SCALE * is_s_ft) + (ff * GEM_STAT_TO_ELEMENT_SCALE * is_s_ff)
        
        result = run_greedy_optimization(
            i,
            budgets[i],
            cur_pp,
            cur_cm,
            cur_fm,
            cur_p_val,
            cur_s_val,
            is_p_pp,
            is_s_pp,
            is_p_cm,
            is_s_cm,
            is_p_fm,
            is_s_fm,
            is_p_ov,
            is_s_ov,
            n_heads[i],
            body_fevers[i],
            body_normals[i],
        )
        for j in ti.static(range(10)):
            results[i, j] = result[j]


# =============================================================================
# Single-item Kernel (backwards compatibility)
# =============================================================================

@ti.kernel
def optimize_gems_kernel(
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
    n_head: ti.i32,
    count_body_fever: ti.i32,
    count_body_normal: ti.i32,
    result: ti.types.ndarray(),
):
    """
    Single gem optimization (backwards compatibility).
    """
    pp = cur_pp
    cm = cur_cm
    fm = cur_fm
    p_val = cur_p_val
    s_val = cur_s_val
    gems_pp = 0
    gems_cm = 0
    gems_fm = 0
    gems_ov = 0
    remaining = budget
    
    while remaining > 0:
        best_score = ti.cast(-1, ti.f32)
        best_opt_idx = -1
        fill_budget = remaining - 1
        fill_bonus = fill_budget * ELEMENTAL_GEM_SCALE if fill_budget > 0 else 0
        
        # Option 0: PP gem
        if pp < MAX_STAT_INDEX:
            t_pp = pp + GEM_SCALE_NORMAL
            t_p = p_val + (GEM_STAT_TO_ELEMENT_SCALE * is_p_pp) + (fill_bonus * is_p_ov)
            t_s = s_val + (GEM_STAT_TO_ELEMENT_SCALE * is_s_pp) + (fill_bonus * is_s_ov)
            pp_factor = lookup_reference_ti(t_pp, ref_pp_field)
            base = (t_p * 2.0) + t_s + pp_factor
            c_mul = lookup_reference_ti(cm, ref_cm_field)
            f_mul = lookup_reference_ti(fm, ref_fm_field)
            score = ti.cast(calc_score_ti(base, c_mul, f_mul, n_head, count_body_fever, count_body_normal), ti.f32)
            if score >= best_score:
                best_score = score
                best_opt_idx = 0
        
        # Option 1: CM gem
        if cm < MAX_STAT_INDEX:
            t_cm = cm + GEM_SCALE_NORMAL
            t_p = p_val + (GEM_STAT_TO_ELEMENT_SCALE * is_p_cm) + (fill_bonus * is_p_ov)
            t_s = s_val + (GEM_STAT_TO_ELEMENT_SCALE * is_s_cm) + (fill_bonus * is_s_ov)
            pp_factor = lookup_reference_ti(pp, ref_pp_field)
            base = (t_p * 2.0) + t_s + pp_factor
            c_mul = lookup_reference_ti(t_cm, ref_cm_field)
            f_mul = lookup_reference_ti(fm, ref_fm_field)
            score = ti.cast(calc_score_ti(base, c_mul, f_mul, n_head, count_body_fever, count_body_normal), ti.f32)
            if score > best_score:
                best_score = score
                best_opt_idx = 1
        
        # Option 2: FM gem
        if fm < MAX_STAT_INDEX:
            t_fm = fm + GEM_SCALE_FEVER
            t_p = p_val + (GEM_STAT_TO_ELEMENT_SCALE * is_p_fm) + (fill_bonus * is_p_ov)
            t_s = s_val + (GEM_STAT_TO_ELEMENT_SCALE * is_s_fm) + (fill_bonus * is_s_ov)
            pp_factor = lookup_reference_ti(pp, ref_pp_field)
            base = (t_p * 2.0) + t_s + pp_factor
            c_mul = lookup_reference_ti(cm, ref_cm_field)
            f_mul = lookup_reference_ti(t_fm, ref_fm_field)
            score = ti.cast(calc_score_ti(base, c_mul, f_mul, n_head, count_body_fever, count_body_normal), ti.f32)
            if score > best_score:
                best_score = score
                best_opt_idx = 2
        
        # Option 3: Overflow
        t_p = p_val + (ELEMENTAL_GEM_SCALE * is_p_ov) + (fill_bonus * is_p_ov)
        t_s = s_val + (ELEMENTAL_GEM_SCALE * is_s_ov) + (fill_bonus * is_s_ov)
        pp_factor = lookup_reference_ti(pp, ref_pp_field)
        base = (t_p * 2.0) + t_s + pp_factor
        c_mul = lookup_reference_ti(cm, ref_cm_field)
        f_mul = lookup_reference_ti(fm, ref_fm_field)
        score = ti.cast(calc_score_ti(base, c_mul, f_mul, n_head, count_body_fever, count_body_normal), ti.f32)
        if score >= best_score:
            best_score = score
            best_opt_idx = 3
        
        # Apply best option
        if best_opt_idx == 0:
            pp += GEM_SCALE_NORMAL
            p_val += GEM_STAT_TO_ELEMENT_SCALE * is_p_pp
            s_val += GEM_STAT_TO_ELEMENT_SCALE * is_s_pp
            gems_pp += 1
        elif best_opt_idx == 1:
            cm += GEM_SCALE_NORMAL
            p_val += GEM_STAT_TO_ELEMENT_SCALE * is_p_cm
            s_val += GEM_STAT_TO_ELEMENT_SCALE * is_s_cm
            gems_cm += 1
        elif best_opt_idx == 2:
            fm += GEM_SCALE_FEVER
            p_val += GEM_STAT_TO_ELEMENT_SCALE * is_p_fm
            s_val += GEM_STAT_TO_ELEMENT_SCALE * is_s_fm
            gems_fm += 1
        else:
            p_val += ELEMENTAL_GEM_SCALE * is_p_ov
            s_val += ELEMENTAL_GEM_SCALE * is_s_ov
            gems_ov += 1
        
        remaining -= 1
    
    # Write results
    result[0] = pp
    result[1] = cm
    result[2] = fm
    result[3] = p_val
    result[4] = s_val
    result[5] = gems_pp
    result[6] = gems_cm
    result[7] = gems_fm
    result[8] = gems_ov


# =============================================================================
# Python Interface
# =============================================================================

def optimize_gems_gpu(
    budget: int,
    cur_pp: int,
    cur_cm: int,
    cur_fm: int,
    cur_p_val: int,
    cur_s_val: int,
    is_p_pp: int,
    is_s_pp: int,
    is_p_cm: int,
    is_s_cm: int,
    is_p_fm: int,
    is_s_fm: int,
    is_p_ov: int,
    is_s_ov: int,
    fever_mask_head: np.ndarray,
    count_body_fever: int,
    count_body_normal: int,
    ref_arrays: dict,
) -> tuple:
    """
    Python wrapper for GPU gem optimization (single item).
    
    Matches the interface of optimize_core_jit from scoring_core.py.
    """
    if not _initialized:
        init_taichi_vulkan()
    
    load_ref_arrays(ref_arrays)
    load_fever_mask(fever_mask_head)
    
    n_head = min(len(fever_mask_head), HEAD_LIMIT)
    result = np.zeros(9, dtype=np.int32)
    
    optimize_gems_kernel(
        budget,
        cur_pp, cur_cm, cur_fm,
        cur_p_val, cur_s_val,
        is_p_pp, is_s_pp,
        is_p_cm, is_s_cm,
        is_p_fm, is_s_fm,
        is_p_ov, is_s_ov,
        n_head,
        count_body_fever,
        count_body_normal,
        result,
    )
    
    return tuple(result)


def optimize_gems_batch_gpu(
    timeline_data: list,
    cur_pp: int,
    cur_cm: int,
    cur_fm: int,
    base_p_val: int,
    base_s_val: int,
    # Color flags for FT/FF gems
    is_p_ft: int,
    is_s_ft: int,
    is_p_ff: int,
    is_s_ff: int,
    # Existing flags
    is_p_pp: int,
    is_s_pp: int,
    is_p_cm: int,
    is_s_cm: int,
    is_p_fm: int,
    is_s_fm: int,
    is_p_ov: int,
    is_s_ov: int,
    ref_arrays: dict,
) -> list:
    """
    Batched GPU gem optimization - GPU-resident processing.
    
    Processes multiple FT/FF combinations in parallel with a SINGLE kernel launch.
    cur_p_val/cur_s_val computed on GPU from FT/FF gems - no CPU interaction.
    
    Args:
        timeline_data: List of dicts with budget, fever_mask_head, counts, ft_gems, ff_gems
        cur_pp, cur_cm, cur_fm: Base stats
        base_p_val, base_s_val: Base color values (before FT/FF gems)
        is_p_ft, is_s_ft: Does FT (Beat) contribute to primary/secondary?
        is_p_ff, is_s_ff: Does FF (Vibe) contribute to primary/secondary?
        is_p_pp, etc.: Standard gem contribution flags
        ref_arrays: Reference lookup arrays
        
    Returns:
        list of tuples: [(score, pp, cm, fm, p_val, s_val, gems_pp, gems_cm, gems_fm, gems_ov), ...]
    """
    if not _initialized:
        init_taichi_vulkan()
    
    batch_size = len(timeline_data)
    if batch_size == 0:
        return []
    
    if batch_size > MAX_BATCH_SIZE:
        # Process in chunks (rare for typical FT/FF combinations)
        results = []
        for i in range(0, batch_size, MAX_BATCH_SIZE):
            chunk = timeline_data[i:i + MAX_BATCH_SIZE]
            results.extend(optimize_gems_batch_gpu(
                chunk, cur_pp, cur_cm, cur_fm, base_p_val, base_s_val,
                is_p_ft, is_s_ft, is_p_ff, is_s_ff,
                is_p_pp, is_s_pp, is_p_cm, is_s_cm, is_p_fm, is_s_fm,
                is_p_ov, is_s_ov, ref_arrays
            ))
        return results
    
    # Load reference arrays ONCE
    load_ref_arrays(ref_arrays)
    
    # Prepare batch input arrays - all data sent to GPU in one transfer
    fever_masks = [t["fever_mask_head"] for t in timeline_data]
    n_heads = [min(len(t["fever_mask_head"]), HEAD_LIMIT) for t in timeline_data]
    load_fever_masks_batch(fever_masks, n_heads)
    
    budgets = np.array([t["budget"] for t in timeline_data], dtype=np.int32)
    n_heads_arr = np.array(n_heads, dtype=np.int32)
    body_fevers = np.array([t["count_body_fever"] for t in timeline_data], dtype=np.int32)
    body_normals = np.array([t["count_body_normal"] for t in timeline_data], dtype=np.int32)
    ft_gems_arr = np.array([t.get("ft_gems", 0) for t in timeline_data], dtype=np.int32)
    ff_gems_arr = np.array([t.get("ff_gems", 0) for t in timeline_data], dtype=np.int32)
    
    # Output array: [batch_size, 10]
    results = np.zeros((batch_size, 10), dtype=np.int32)
    
    # SINGLE GPU kernel launch - all computation on GPU
    optimize_gems_batch_kernel(
        batch_size,
        budgets,
        n_heads_arr,
        body_fevers,
        body_normals,
        ft_gems_arr,
        ff_gems_arr,
        cur_pp, cur_cm, cur_fm,
        base_p_val, base_s_val,
        is_p_ft, is_s_ft, is_p_ff, is_s_ff,
        is_p_pp, is_s_pp,
        is_p_cm, is_s_cm,
        is_p_fm, is_s_fm,
        is_p_ov, is_s_ov,
        results,
    )
    
    # Convert to list of tuples (only CPU work: simple iteration)
    return [tuple(results[i]) for i in range(batch_size)]


def calc_score_gpu(
    base_value: float,
    combo_mul: float,
    fever_mul: float,
    fever_mask_head: np.ndarray,
    count_body_fever: int,
    count_body_normal: int,
) -> int:
    """
    Standalone GPU score calculation.
    """
    if not _initialized:
        init_taichi_vulkan()
    
    load_fever_mask(fever_mask_head)
    n_head = min(len(fever_mask_head), HEAD_LIMIT)
    
    @ti.kernel
    def _calc_score_wrapper(
        base_value: ti.f32,
        combo_mul: ti.f32,
        fever_mul: ti.f32,
        n_head: ti.i32,
        count_body_fever: ti.i32,
        count_body_normal: ti.i32,
        out: ti.types.ndarray(),
    ):
        out[0] = calc_score_ti(base_value, combo_mul, fever_mul, n_head, count_body_fever, count_body_normal)
    
    out = np.zeros(1, dtype=np.int32)
    _calc_score_wrapper(
        float(base_value),
        float(combo_mul),
        float(fever_mul),
        n_head,
        count_body_fever,
        count_body_normal,
        out,
    )
    return int(out[0])


# =============================================================================
# Population-Level Mega-Batch Solver
# =============================================================================

def mega_batch_solve_population(
    work_items: list,
    genome_ids: np.ndarray,
    cur_pp: int,
    cur_cm: int,
    cur_fm: int,
    base_p_val: int,
    base_s_val: int,
    is_p_ft: int, is_s_ft: int,
    is_p_ff: int, is_s_ff: int,
    is_p_pp: int, is_s_pp: int,
    is_p_cm: int, is_s_cm: int,
    is_p_fm: int, is_s_fm: int,
    is_p_ov: int, is_s_ov: int,
    ref_arrays: dict,
) -> dict:
    """
    Solve gem optimization for an entire population in ONE kernel launch.
    
    This is the mega-batch version that processes ALL timelines from ALL genomes
    in a single GPU kernel call, eliminating per-genome launch overhead.
    
    Args:
        work_items: List of dicts, each containing:
            - budget: Remaining gem budget
            - fever_mask_head: np.array of head fever mask
            - count_body_fever: int
            - count_body_normal: int
            - ft_gems: FT gems allocated
            - ff_gems: FF gems allocated
        genome_ids: np.ndarray mapping work_item index -> genome index
        cur_pp/cur_cm/cur_fm: Base PP/CM/FM stats
        base_p_val/base_s_val: Base primary/secondary color values
        is_p_*/is_s_*: Color contribution flags
        ref_arrays: Reference lookup arrays
        
    Returns:
        dict: genome_id -> best result tuple (score, pp, cm, fm, p_val, s_val, 
              gems_pp, gems_cm, gems_fm, gems_ov)
    """
    if not _initialized:
        init_taichi_vulkan()
        load_ref_arrays(ref_arrays)
    
    batch_size = len(work_items)
    if batch_size == 0:
        return {}
    
    # Clamp batch size to avoid memory issues
    effective_batch = min(batch_size, MAX_BATCH_SIZE)
    if batch_size > MAX_BATCH_SIZE:
        # Process in chunks if too large
        all_results = {}
        for chunk_start in range(0, batch_size, MAX_BATCH_SIZE):
            chunk_end = min(chunk_start + MAX_BATCH_SIZE, batch_size)
            chunk_items = work_items[chunk_start:chunk_end]
            chunk_ids = genome_ids[chunk_start:chunk_end]
            chunk_result = mega_batch_solve_population(
                chunk_items, chunk_ids,
                cur_pp, cur_cm, cur_fm,
                base_p_val, base_s_val,
                is_p_ft, is_s_ft, is_p_ff, is_s_ff,
                is_p_pp, is_s_pp, is_p_cm, is_s_cm,
                is_p_fm, is_s_fm, is_p_ov, is_s_ov,
                ref_arrays,
            )
            for gid, result in chunk_result.items():
                if gid not in all_results or result[0] > all_results[gid][0]:
                    all_results[gid] = result
        return all_results
    
    # VECTORIZED: Build all arrays using NumPy operations
    budgets = np.array([item["budget"] for item in work_items], dtype=np.int32)
    body_fevers = np.array([item["count_body_fever"] for item in work_items], dtype=np.int32)
    body_normals = np.array([item["count_body_normal"] for item in work_items], dtype=np.int32)
    ft_gems_arr = np.array([item["ft_gems"] for item in work_items], dtype=np.int32)
    ff_gems_arr = np.array([item["ff_gems"] for item in work_items], dtype=np.int32)
    
    # VECTORIZED: Build fever mask array using NumPy
    fever_masks_np = np.zeros((batch_size, HEAD_LIMIT), dtype=np.int32)
    n_heads_arr = np.zeros(batch_size, dtype=np.int32)
    
    for i, item in enumerate(work_items):
        mask_head = item["fever_mask_head"]
        n_head = min(len(mask_head), HEAD_LIMIT)
        n_heads_arr[i] = n_head
        # Vectorized copy using NumPy slicing
        fever_masks_np[i, :n_head] = mask_head[:n_head].astype(np.int32)
    
    # Pad to match Taichi field shape (from_numpy requires exact match)
    padded_masks = np.zeros((MAX_BATCH_SIZE, HEAD_LIMIT), dtype=np.int32)
    padded_masks[:batch_size, :] = fever_masks_np
    
    # Bulk copy fever masks to Taichi field using from_numpy
    fever_mask_batch_field.from_numpy(padded_masks)
    
    # Allocate results array
    results = np.zeros((batch_size, 10), dtype=np.int32)
    
    # SINGLE kernel launch for ALL work items
    optimize_gems_batch_kernel(
        batch_size,
        budgets,
        n_heads_arr,
        body_fevers,
        body_normals,
        ft_gems_arr,
        ff_gems_arr,
        cur_pp, cur_cm, cur_fm,
        base_p_val, base_s_val,
        is_p_ft, is_s_ft, is_p_ff, is_s_ff,
        is_p_pp, is_s_pp,
        is_p_cm, is_s_cm,
        is_p_fm, is_s_fm,
        is_p_ov, is_s_ov,
        results,
    )
    
    # VECTORIZED: Reduce results using NumPy
    best_per_genome = {}
    unique_genome_ids = np.unique(genome_ids)
    for gid in unique_genome_ids:
        mask = genome_ids == gid
        genome_results = results[mask]
        best_idx = np.argmax(genome_results[:, 0])
        best_per_genome[int(gid)] = tuple(genome_results[best_idx])
    
    return best_per_genome

