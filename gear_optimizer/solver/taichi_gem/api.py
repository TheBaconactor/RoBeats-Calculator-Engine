"""
Taichi API - Python wrapper functions for GPU gem optimization.

This module provides the public Python API:
- load_ref_arrays: Upload reference lookup tables
- optimize_gems_gpu: Single-item optimization
- optimize_gems_batch_gpu: Batch optimization
- mega_batch_solve_population: Multi-genome batch solver
- solve_genomes_with_ftff: GPU-resident FT/FF iteration
- solve_genomes_parallel: Maximum parallelism solver
"""
from __future__ import annotations

import taichi as ti
import numpy as np

from .runtime import init_taichi_vulkan, is_initialized
from . import fields
from .fields import (
    GRID_SIZE,
    MAX_WORK_ITEMS,
    MAX_HEAD_NOTES,
    MAX_GENOMES,
    ensure_fields_allocated,
    ensure_grid_fields_allocated,
    is_fields_allocated,
    is_grid_fields_allocated,
    get_last_uploaded_grid_id,
    set_last_uploaded_grid_id,
)
from . import kernels


# ============================================================================
# REFERENCE LOADING STATE
# ============================================================================

_ref_loaded = False
_last_ref_arrays_id = None

# ============================================================================
# NUMPY STAGING BUFFERS (avoid huge per-call allocations / CPU zeroing)
# ============================================================================

_BATCH_STAGING = None
_MEGA_STAGING = None
_PARALLEL_STAGING = None


def _ensure_batch_staging():
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


def _ensure_parallel_staging():
    """
    Allocate and reuse staging buffers for solve_genomes_parallel().
    
    These buffers avoid per-call np.zeros() allocations which are expensive
    due to memory allocation + CPU zeroing overhead.
    """
    global _PARALLEL_STAGING
    if _PARALLEL_STAGING is not None:
        return _PARALLEL_STAGING
    _PARALLEL_STAGING = {
        # Per-genome stats (uploaded once per call)
        "genome_pp": np.zeros(MAX_GENOMES, dtype=np.int32),
        "genome_cm": np.zeros(MAX_GENOMES, dtype=np.int32),
        "genome_fm": np.zeros(MAX_GENOMES, dtype=np.int32),
        "genome_p_val": np.zeros(MAX_GENOMES, dtype=np.int32),
        "genome_s_val": np.zeros(MAX_GENOMES, dtype=np.int32),
        "genome_ft": np.zeros(MAX_GENOMES, dtype=np.int32),
        "genome_ff": np.zeros(MAX_GENOMES, dtype=np.int32),
        # Per-work-item buffers (reused per chunk)
        "work_genome_id": np.zeros(MAX_WORK_ITEMS, dtype=np.int32),
        "work_ft_gems": np.zeros(MAX_WORK_ITEMS, dtype=np.int32),
        "work_ff_gems": np.zeros(MAX_WORK_ITEMS, dtype=np.int32),
    }
    return _PARALLEL_STAGING


def is_refs_loaded() -> bool:
    """Check if reference arrays have been loaded."""
    return _ref_loaded


# ============================================================================
# INITIALIZATION HELPERS
# ============================================================================

def ensure_ready(ref_arrays=None, *, need_grid=False, timeline_grid=None):
    """
    Ensure Taichi and GPU fields are ready for use.
    
    This is the centralized initialization function that maintains
    the same order and semantics as the original scattered checks.
    
    Args:
        ref_arrays: Reference arrays to load (optional)
        need_grid: Whether grid fields are required
        timeline_grid: Timeline grid to upload (optional, requires need_grid=True)
    """
    # 1. Taichi initialization
    if not is_initialized():
        init_taichi_vulkan()
    
    # 2. Field allocation (includes bind_fields to kernels)
    if not is_fields_allocated():
        ensure_fields_allocated()
    
    # 3. Reference arrays - upload only when needed (or when ref source changes)
    # This preserves the old behavior where callers could load once and reuse.
    global _last_ref_arrays_id
    if ref_arrays is not None:
        rid = id(ref_arrays)
        if (not _ref_loaded) or (_last_ref_arrays_id != rid):
            load_ref_arrays(ref_arrays)
            _last_ref_arrays_id = rid
    
    # 4. Grid fields (only if needed)
    if need_grid:
        if not is_grid_fields_allocated():
            ensure_grid_fields_allocated()
        
        if timeline_grid is not None:
            _upload_timeline_grid(timeline_grid)


# ============================================================================
# REFERENCE ARRAY LOADING
# ============================================================================

def load_ref_arrays(ref_arrays: dict):
    """
    Upload reference arrays to GPU fields.
    
    Must be called once before using optimize_gems_batch_gpu().
    Typically called when switching songs or on first use.
    
    Args:
        ref_arrays: Dict with keys "Perfect Points", "Combo Multiplier", "Fever Multiplier"
                    Each value is a NumPy array of shape (161,)
                    
    Optional keys:
        - "Fever Time": Optional FT reference array (161,)
        - "Fever Fill Rate": Optional FF reference array (161,)
    """
    global _ref_loaded
    
    ensure_fields_allocated()
    
    # Validate required keys and shapes early (clear errors)
    required = ("Perfect Points", "Combo Multiplier", "Fever Multiplier")
    for k in required:
        if k not in ref_arrays:
            raise KeyError(f"ref_arrays missing required key {k!r}")
        arr = np.asarray(ref_arrays[k])
        if arr.ndim != 1 or arr.shape[0] != GRID_SIZE:
            raise ValueError(f"ref_arrays[{k!r}] must be shape ({GRID_SIZE},), got {arr.shape}")
    
    fields.ref_pp_field.from_numpy(ref_arrays["Perfect Points"].astype(np.float32))
    fields.ref_cm_field.from_numpy(ref_arrays["Combo Multiplier"].astype(np.float32))
    fields.ref_fm_field.from_numpy(ref_arrays["Fever Multiplier"].astype(np.float32))
    
    # Optional FT/FF uploads
    if "Fever Time" in ref_arrays:
        arr = np.asarray(ref_arrays["Fever Time"])
        if arr.ndim != 1 or arr.shape[0] != GRID_SIZE:
            raise ValueError(f"ref_arrays['Fever Time'] must be shape ({GRID_SIZE},), got {arr.shape}")
        fields.ref_ft_field.from_numpy(ref_arrays["Fever Time"].astype(np.float32))
    if "Fever Fill Rate" in ref_arrays:
        arr = np.asarray(ref_arrays["Fever Fill Rate"])
        if arr.ndim != 1 or arr.shape[0] != GRID_SIZE:
            raise ValueError(f"ref_arrays['Fever Fill Rate'] must be shape ({GRID_SIZE},), got {arr.shape}")
        fields.ref_ff_field.from_numpy(ref_arrays["Fever Fill Rate"].astype(np.float32))
    
    _ref_loaded = True


# ============================================================================
# SINGLE-ITEM OPTIMIZATION
# ============================================================================

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


# ============================================================================
# BATCH OPTIMIZATION
# ============================================================================

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
    
    ensure_ready(ref_arrays)
    
    # ========================================================================
    # DYNAMIC GENOME MAPPING (Fix for Batch Coalescing)
    # ========================================================================
    # Identify unique (base_p, base_s) pairs to support merged batches
    
    unique_stats_map = {}  # (p, s) -> genome_id
    next_genome_id = 0
    
    staging = _ensure_batch_staging()
    budgets_np = staging["budgets"]
    count_fever_np = staging["count_fever"]
    count_normal_np = staging["count_normal"]
    ft_gems_np = staging["ft_gems"]
    ff_gems_np = staging["ff_gems"]
    head_len_np = staging["head_len"]
    genome_id_np = staging["genome_id"]
    fever_masks_np = staging["fever_masks"]

    # Clear only the active prefix. (Avoid full zeroing of MAX_WORK_ITEMS each call.)
    budgets_np[:n] = 0
    count_fever_np[:n] = 0
    count_normal_np[:n] = 0
    ft_gems_np[:n] = 0
    ff_gems_np[:n] = 0
    head_len_np[:n] = 0
    genome_id_np[:n] = 0
    fever_masks_np[:n, :] = 0
    
    for i, item in enumerate(batch_input):
        budgets_np[i] = item["budget"]
        count_fever_np[i] = item["count_body_fever"]
        count_normal_np[i] = item["count_body_normal"]
        ft_gems_np[i] = item.get("ft_gems", 0)
        ff_gems_np[i] = item.get("ff_gems", 0)
        
        mask = item.get("fever_mask_head")
        if mask is not None:
            hl = min(len(mask), MAX_HEAD_NOTES)
            head_len_np[i] = hl
            fever_masks_np[i, :hl] = mask[:hl].astype(np.int8)
            
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
        raise RuntimeError(f"Too many unique base stat combinations in batch ({next_genome_id} > {MAX_GENOMES})")
        
    # Upload per-genome stats
    genome_pp_np = staging["genome_pp"]
    genome_cm_np = staging["genome_cm"]
    genome_fm_np = staging["genome_fm"]
    genome_p_np = staging["genome_p"]
    genome_s_np = staging["genome_s"]

    genome_pp_np[:] = 0
    genome_cm_np[:] = 0
    genome_fm_np[:] = 0
    genome_p_np[:] = 0
    genome_s_np[:] = 0
    
    for (p, s), gid in unique_stats_map.items():
        genome_pp_np[gid] = cur_pp
        genome_cm_np[gid] = cur_cm
        genome_fm_np[gid] = cur_fm
        genome_p_np[gid] = p
        genome_s_np[gid] = s
        
    fields.genome_base_pp.from_numpy(genome_pp_np)
    fields.genome_base_cm.from_numpy(genome_cm_np)
    fields.genome_base_fm.from_numpy(genome_fm_np)
    fields.genome_base_p_val.from_numpy(genome_p_np)
    fields.genome_base_s_val.from_numpy(genome_s_np)
    
    # BULK transfer
    fields.work_budgets.from_numpy(budgets_np)
    fields.work_count_fever.from_numpy(count_fever_np)
    fields.work_count_normal.from_numpy(count_normal_np)
    fields.work_ft_gems.from_numpy(ft_gems_np)
    fields.work_ff_gems.from_numpy(ff_gems_np)
    fields.work_head_len.from_numpy(head_len_np)
    fields.work_genome_id.from_numpy(genome_id_np)
    fields.fever_masks.from_numpy(fever_masks_np)
    
    # Launch kernel
    kernels.solve_batch_kernel(
        n,
        is_p_ft, is_s_ft, is_p_ff, is_s_ff,
        is_p_pp, is_s_pp, is_p_cm, is_s_cm,
        is_p_fm, is_s_fm, is_p_ov, is_s_ov,
    )
    
    ti.sync()
    
    # Download results
    scores_np = fields.result_scores.to_numpy()[:n]
    pp_np = fields.result_pp.to_numpy()[:n]
    cm_np = fields.result_cm.to_numpy()[:n]
    fm_np = fields.result_fm.to_numpy()[:n]
    ov_np = fields.result_ov.to_numpy()[:n]
    p_val_np = fields.result_p_val.to_numpy()[:n]
    s_val_np = fields.result_s_val.to_numpy()[:n]
    
    results = [
        (int(scores_np[i]), int(pp_np[i]), int(cm_np[i]), int(fm_np[i]),
         int(p_val_np[i]), int(s_val_np[i]),
         int(pp_np[i]), int(cm_np[i]), int(fm_np[i]), int(ov_np[i]))
        for i in range(n)
    ]
    
    return results


# ============================================================================
# MEGA-BATCH POPULATION SOLVER
# ============================================================================

def mega_batch_solve_population(
    work_items: list,
    genome_ids: np.ndarray,
    genome_stats: dict,  # {genome_idx: (base_pp, base_cm, base_fm, base_p_val, base_s_val)}
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
    
    ensure_ready(ref_arrays)
    
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
    
    staging = _ensure_mega_staging()

    # ========================================================================
    # UPLOAD PER-GENOME STATS
    # ========================================================================
    genome_pp_np = staging["genome_pp"]
    genome_cm_np = staging["genome_cm"]
    genome_fm_np = staging["genome_fm"]
    genome_p_np = staging["genome_p"]
    genome_s_np = staging["genome_s"]

    genome_pp_np[:] = 0
    genome_cm_np[:] = 0
    genome_fm_np[:] = 0
    genome_p_np[:] = 0
    genome_s_np[:] = 0
    
    for gid, (base_pp, base_cm, base_fm, base_p, base_s) in genome_stats.items():
        genome_pp_np[gid] = base_pp
        genome_cm_np[gid] = base_cm
        genome_fm_np[gid] = base_fm
        genome_p_np[gid] = base_p
        genome_s_np[gid] = base_s
    
    fields.genome_base_pp.from_numpy(genome_pp_np)
    fields.genome_base_cm.from_numpy(genome_cm_np)
    fields.genome_base_fm.from_numpy(genome_fm_np)
    fields.genome_base_p_val.from_numpy(genome_p_np)
    fields.genome_base_s_val.from_numpy(genome_s_np)
    
    # ========================================================================
    # UPLOAD WORK ITEMS WITH GENOME IDS
    # ========================================================================
    budgets_np = staging["budgets"]
    count_fever_np = staging["count_fever"]
    count_normal_np = staging["count_normal"]
    ft_gems_np = staging["ft_gems"]
    ff_gems_np = staging["ff_gems"]
    head_len_np = staging["head_len"]
    genome_id_np = staging["genome_id"]
    fever_masks_np = staging["fever_masks"]

    budgets_np[:n] = 0
    count_fever_np[:n] = 0
    count_normal_np[:n] = 0
    ft_gems_np[:n] = 0
    ff_gems_np[:n] = 0
    head_len_np[:n] = 0
    genome_id_np[:n] = 0
    fever_masks_np[:n, :] = 0
    
    for i, item in enumerate(work_items):
        budgets_np[i] = item["budget"]
        count_fever_np[i] = item["count_body_fever"]
        count_normal_np[i] = item["count_body_normal"]
        ft_gems_np[i] = item.get("ft_gems", 0)
        ff_gems_np[i] = item.get("ff_gems", 0)
        genome_id_np[i] = genome_ids[i]
        
        mask = item.get("fever_mask_head")
        if mask is not None:
            head_len = min(len(mask), MAX_HEAD_NOTES)
            head_len_np[i] = head_len
            fever_masks_np[i, :head_len] = mask[:head_len].astype(np.int8)
    
    fields.work_budgets.from_numpy(budgets_np)
    fields.work_count_fever.from_numpy(count_fever_np)
    fields.work_count_normal.from_numpy(count_normal_np)
    fields.work_ft_gems.from_numpy(ft_gems_np)
    fields.work_ff_gems.from_numpy(ff_gems_np)
    fields.work_head_len.from_numpy(head_len_np)
    fields.work_genome_id.from_numpy(genome_id_np)
    fields.fever_masks.from_numpy(fever_masks_np)
    
    # Launch kernel (uses genome lookup for base stats)
    kernels.solve_batch_kernel(
        n,
        is_p_ft, is_s_ft, is_p_ff, is_s_ff,
        is_p_pp, is_s_pp, is_p_cm, is_s_cm,
        is_p_fm, is_s_fm, is_p_ov, is_s_ov,
    )
    
    ti.sync()
    
    # Download results
    scores_np = fields.result_scores.to_numpy()[:n]
    pp_np = fields.result_pp.to_numpy()[:n]
    cm_np = fields.result_cm.to_numpy()[:n]
    fm_np = fields.result_fm.to_numpy()[:n]
    ov_np = fields.result_ov.to_numpy()[:n]
    p_val_np = fields.result_p_val.to_numpy()[:n]
    s_val_np = fields.result_s_val.to_numpy()[:n]
    
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


# ============================================================================
# GRID UPLOAD HELPERS
# ============================================================================

_grid_uploaded = False


def _upload_timeline_grid(timeline_grid):
    """Upload timeline grid to GPU fields (with caching)."""
    global _grid_uploaded
    
    # Skip if same grid already uploaded (major optimization!)
    grid_id = id(timeline_grid)
    if _grid_uploaded and get_last_uploaded_grid_id() == grid_id:
        return
    
    # Ensure all timelines are computed
    timeline_grid.precompute_all()
    
    # Import fields module
    from . import fields
    
    # Get grid data
    grid_size = timeline_grid.GRID_SIZE
    
    # Allocate numpy arrays
    cbf_np = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.int32)
    cbn_np = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.int32)
    hl_np = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.int32)
    masks_np = np.zeros((GRID_SIZE, GRID_SIZE, MAX_HEAD_NOTES), dtype=np.int8)
    masks_bits_np = np.zeros((GRID_SIZE, GRID_SIZE, 4), dtype=np.uint32)
    
    # Fill from grid (+ bitpack head mask)
    for ft_idx in range(grid_size):
        for ff_idx in range(grid_size):
            timeline = timeline_grid._timeline_grid[ft_idx][ff_idx]
            if timeline is not None:
                fever_mask_head, count_fever, count_normal, _ = timeline
                cbf_np[ft_idx, ff_idx] = count_fever
                cbn_np[ft_idx, ff_idx] = count_normal
                head_len = min(len(fever_mask_head), MAX_HEAD_NOTES)
                hl_np[ft_idx, ff_idx] = head_len
                masks_np[ft_idx, ff_idx, :head_len] = fever_mask_head[:head_len].astype(np.int8)

                # Pack bits (bit i = head note i fever)
                w0 = np.uint32(0)
                w1 = np.uint32(0)
                w2 = np.uint32(0)
                w3 = np.uint32(0)
                for i in range(head_len):
                    if fever_mask_head[i]:
                        bit = np.uint32(1) << np.uint32(i & 31)
                        if i < 32:
                            w0 |= bit
                        elif i < 64:
                            w1 |= bit
                        elif i < 96:
                            w2 |= bit
                        else:
                            w3 |= bit
                masks_bits_np[ft_idx, ff_idx, 0] = w0
                masks_bits_np[ft_idx, ff_idx, 1] = w1
                masks_bits_np[ft_idx, ff_idx, 2] = w2
                masks_bits_np[ft_idx, ff_idx, 3] = w3
    
    # Upload to GPU
    fields.grid_count_body_fever.from_numpy(cbf_np)
    fields.grid_count_body_normal.from_numpy(cbn_np)
    fields.grid_head_len.from_numpy(hl_np)
    fields.grid_fever_masks.from_numpy(masks_np)
    fields.grid_fever_masks_bits.from_numpy(masks_bits_np)
    
    _grid_uploaded = True
    set_last_uploaded_grid_id(grid_id)


# ============================================================================
# FT/FF ITERATION SOLVERS
# ============================================================================

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
    Solve gem allocation for multiple genomes with GPU-resident FT/FF iteration.
    
    Uploads the timeline grid ONCE, then processes all genomes in a single
    kernel launch that iterates FT/FF combinations on-GPU.
    
    ~100x faster than the old approach which transferred 400k work items.
    
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
    ensure_ready(ref_arrays, need_grid=True, timeline_grid=timeline_grid)
    
    # Import fields module
    from . import fields
    
    n_genomes = len(genome_stats_list)
    if n_genomes == 0:
        return []
    
    if n_genomes > MAX_GENOMES:
        raise ValueError(f"Too many genomes: {n_genomes} > {MAX_GENOMES}")
    
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
    
    fields.genome_base_pp.from_numpy(pp_np)
    fields.genome_base_cm.from_numpy(cm_np)
    fields.genome_base_fm.from_numpy(fm_np)
    fields.genome_base_p_val.from_numpy(p_val_np)
    fields.genome_base_s_val.from_numpy(s_val_np)
    fields.genome_base_ft.from_numpy(ft_np)
    fields.genome_base_ff.from_numpy(ff_np)
    
    # Launch kernel
    kernels.solve_genomes_with_ftff_kernel(
        n_genomes,
        total_budget,
        gem_scale_fever,
        is_p_ft, is_s_ft, is_p_ff, is_s_ff,
        is_p_pp, is_s_pp, is_p_cm, is_s_cm,
        is_p_fm, is_s_fm, is_p_ov, is_s_ov,
    )
    
    ti.sync()
    
    # Download results
    scores_np = fields.genome_result_scores.to_numpy()[:n_genomes]
    ft_out_np = fields.genome_result_ft.to_numpy()[:n_genomes]
    ff_out_np = fields.genome_result_ff.to_numpy()[:n_genomes]
    pp_out_np = fields.genome_result_pp.to_numpy()[:n_genomes]
    cm_out_np = fields.genome_result_cm.to_numpy()[:n_genomes]
    fm_out_np = fields.genome_result_fm.to_numpy()[:n_genomes]
    ov_out_np = fields.genome_result_ov.to_numpy()[:n_genomes]
    
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
    Combines the parallelism of the old approach with the low transfer
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
    ensure_ready(ref_arrays, need_grid=True, timeline_grid=timeline_grid)
    
    # Import fields module
    from . import fields
    
    n_genomes = len(genome_stats_list)
    if n_genomes == 0:
        return []
    
    if n_genomes > MAX_GENOMES:
        raise ValueError(f"Too many genomes: {n_genomes} > {MAX_GENOMES}")
    
    # Get reusable staging buffers (avoid per-call allocations)
    staging = _ensure_parallel_staging()
    pp_np = staging["genome_pp"]
    cm_np = staging["genome_cm"]
    fm_np = staging["genome_fm"]
    p_val_np = staging["genome_p_val"]
    s_val_np = staging["genome_s_val"]
    ft_np = staging["genome_ft"]
    ff_np = staging["genome_ff"]
    
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
    
    fields.genome_base_pp.from_numpy(pp_np)
    fields.genome_base_cm.from_numpy(cm_np)
    fields.genome_base_fm.from_numpy(fm_np)
    fields.genome_base_p_val.from_numpy(p_val_np)
    fields.genome_base_s_val.from_numpy(s_val_np)
    fields.genome_base_ft.from_numpy(ft_np)
    fields.genome_base_ff.from_numpy(ff_np)
    
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
    
    # Process in chunks if exceeds MAX_WORK_ITEMS
    chunk_size = MAX_WORK_ITEMS
    num_chunks = (n_work + chunk_size - 1) // chunk_size
    
    # Initialize genome results ONCE before any chunks
    kernels.init_genome_results_kernel(n_genomes)
    
    # Get reusable work item buffers
    genome_id_np = staging["work_genome_id"]
    ft_gems_np = staging["work_ft_gems"]
    ff_gems_np = staging["work_ff_gems"]
    
    for chunk_idx in range(num_chunks):
        start = chunk_idx * chunk_size
        end = min(start + chunk_size, n_work)
        chunk_n = end - start
        
        # Copy work items into reusable buffers (no allocation needed)
        genome_id_np[:chunk_n] = work_genome[start:end]
        ft_gems_np[:chunk_n] = work_ft[start:end]
        ff_gems_np[:chunk_n] = work_ff[start:end]
        
        fields.work_genome_id.from_numpy(genome_id_np)
        fields.work_ft_gems.from_numpy(ft_gems_np)
        fields.work_ff_gems.from_numpy(ff_gems_np)
        
        # Launch solve kernel
        kernels.solve_ftff_parallel_kernel(
            chunk_n,
            total_budget,
            gem_scale_fever,
            is_p_ft, is_s_ft, is_p_ff, is_s_ff,
            is_p_pp, is_s_pp, is_p_cm, is_s_cm,
            is_p_fm, is_s_fm, is_p_ov, is_s_ov,
        )
        
        # GPU-side reduction: accumulate best into genome_result_* fields
        kernels.reduce_chunk_to_genomes_kernel(chunk_n)
    
    ti.sync()
    
    # Download only O(n_genomes) results (not O(n_work_items)!)
    scores_np = fields.genome_result_scores.to_numpy()[:n_genomes]
    ft_np = fields.genome_result_ft.to_numpy()[:n_genomes]
    ff_np = fields.genome_result_ff.to_numpy()[:n_genomes]
    pp_np = fields.genome_result_pp.to_numpy()[:n_genomes]
    cm_np = fields.genome_result_cm.to_numpy()[:n_genomes]
    fm_np = fields.genome_result_fm.to_numpy()[:n_genomes]
    ov_np = fields.genome_result_ov.to_numpy()[:n_genomes]
    
    # Build results in order
    results = []
    for i in range(n_genomes):
        results.append((
            int(scores_np[i]),
            int(ft_np[i]),
            int(ff_np[i]),
            int(pp_np[i]),
            int(cm_np[i]),
            int(fm_np[i]),
            int(ov_np[i]),
        ))
    
    return results


def aggregate_population_stats_gpu(
    population_indices_np: np.ndarray,
    item_stats_np: np.ndarray,
    base_fixed_stats_np: np.ndarray,
    *,
    n_slots: int = 9,
) -> None:
    """
    Upload population/item stats to GPU and aggregate per-genome base stats.

    This fills fields.genome_base_pp/cm/fm/ft/ff plus element stats are kept on
    GPU implicitly (callers can derive p/s values on host if desired).

    NOTE: This function does NOT compute genome_base_p_val/genome_base_s_val
    because that depends on song primary/secondary colors.
    """
    ensure_ready()

    n_genomes = int(population_indices_np.shape[0])
    if n_genomes <= 0:
        return
    if n_genomes > fields.MAX_GENOMES:
        raise ValueError(f"Too many genomes: {n_genomes} > {fields.MAX_GENOMES}")

    if int(n_slots) > fields.MAX_SLOTS:
        raise ValueError(f"Too many slots: {n_slots} > {fields.MAX_SLOTS}")

    # Upload population indices (pad to MAX_GENOMES/MAX_SLOTS)
    pop_buf = np.zeros((fields.MAX_GENOMES, fields.MAX_SLOTS), dtype=np.int32)
    pop_buf[:n_genomes, : int(n_slots)] = np.asarray(population_indices_np[:, : int(n_slots)], dtype=np.int32)
    fields.population_indices.from_numpy(pop_buf)

    # Upload item stats (pad to MAX_ITEMS)
    item_buf = np.zeros((fields.MAX_ITEMS, fields.ITEM_STAT_DIM), dtype=np.int32)
    n_items = min(int(item_stats_np.shape[0]), fields.MAX_ITEMS)
    item_buf[:n_items, :] = np.asarray(item_stats_np[:n_items, : fields.ITEM_STAT_DIM], dtype=np.int32)
    fields.item_stats.from_numpy(item_buf)

    # Upload fixed base stats (length ITEM_STAT_DIM)
    base_buf = np.zeros((fields.ITEM_STAT_DIM,), dtype=np.int32)
    base_buf[: fields.ITEM_STAT_DIM] = np.asarray(base_fixed_stats_np[: fields.ITEM_STAT_DIM], dtype=np.int32)
    fields.base_fixed_stats.from_numpy(base_buf)

    kernels.aggregate_population_stats_kernel(n_genomes, int(n_slots))
    ti.sync()


def ga_upload_population_indices(population_indices_np: np.ndarray, *, n_slots: int = 9) -> int:
    """
    Upload integer population to the GPU resident `fields.population_indices`.
    Returns n_genomes uploaded.
    """
    ensure_ready()
    n_genomes = int(population_indices_np.shape[0])
    if n_genomes <= 0:
        return 0
    if n_genomes > fields.MAX_GENOMES:
        raise ValueError(f"Too many genomes: {n_genomes} > {fields.MAX_GENOMES}")
    if int(n_slots) > fields.MAX_SLOTS:
        raise ValueError(f"Too many slots: {n_slots} > {fields.MAX_SLOTS}")

    pop_buf = np.zeros((fields.MAX_GENOMES, fields.MAX_SLOTS), dtype=np.int32)
    pop_buf[:n_genomes, : int(n_slots)] = np.asarray(population_indices_np[:, : int(n_slots)], dtype=np.int32)
    fields.population_indices.from_numpy(pop_buf)
    return n_genomes


def ga_seed_rng(n_genomes: int, seed: int = 12345) -> None:
    """Seed per-genome RNG state for GPU GA operators."""
    ensure_ready()
    kernels.ga_seed_rng_kernel(int(n_genomes), np.uint32(seed))
    ti.sync()


def ga_set_scores(scores_np: np.ndarray, *, n_genomes: int | None = None) -> int:
    """Upload fitness scores to GPU (fields.ga_scores). Returns n_genomes used."""
    ensure_ready()
    if n_genomes is None:
        n_genomes = int(scores_np.shape[0])
    n_genomes = int(n_genomes)
    if n_genomes <= 0:
        return 0
    if n_genomes > fields.MAX_GENOMES:
        raise ValueError(f"Too many genomes: {n_genomes} > {fields.MAX_GENOMES}")
    buf = np.zeros((fields.MAX_GENOMES,), dtype=np.int32)
    buf[:n_genomes] = np.asarray(scores_np[:n_genomes], dtype=np.int32)
    fields.ga_scores.from_numpy(buf)
    return n_genomes


def ga_next_generation(
    *,
    n_genomes: int,
    n_slots: int = 9,
    mutation_rate: float = 0.02,
    tournament_k: int = 3,
    elite_count: int = 2,
) -> None:
    """
    Run one GPU-side GA operator step on resident population:
      selection -> crossover+mutation -> swap buffers.
    """
    ensure_ready()
    n_genomes = int(n_genomes)
    n_slots = int(n_slots)
    elite_count = int(elite_count)
    tournament_k = int(tournament_k)
    if n_genomes <= 0:
        return
    if n_slots <= 0 or n_slots > fields.MAX_SLOTS:
        raise ValueError(f"Invalid n_slots: {n_slots}")
    if elite_count < 0:
        elite_count = 0
    if elite_count > n_genomes:
        elite_count = n_genomes
    if tournament_k < 1:
        tournament_k = 1

    # Convert probability to uint32 threshold.
    mr = float(mutation_rate)
    if mr <= 0.0:
        mr_fp = np.uint32(0)
    elif mr >= 1.0:
        mr_fp = np.uint32(0xFFFFFFFF)
    else:
        mr_fp = np.uint32(int(mr * 4294967295.0))

    kernels.ga_select_parents_tournament_kernel(n_genomes, tournament_k)
    kernels.ga_crossover_mutate_kernel(n_genomes, n_slots, mr_fp, elite_count)
    kernels.ga_swap_populations_kernel(n_genomes, n_slots)
    ti.sync()


def ga_download_population_indices(*, n_genomes: int, n_slots: int = 9) -> np.ndarray:
    """Download the current resident population indices (for testing / debugging)."""
    ensure_ready()
    n_genomes = int(n_genomes)
    n_slots = int(n_slots)
    out = fields.population_indices.to_numpy()
    return np.asarray(out[:n_genomes, :n_slots], dtype=np.int32)