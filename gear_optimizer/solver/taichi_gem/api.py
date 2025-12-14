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

import os
import time
import hashlib
import taichi as ti
import numpy as np

from ..gpu_profiler import get_gpu_profiler
_profiler = get_gpu_profiler()

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
from .kernel_loader import get_kernels

# Get appropriate kernels for current platform (Metal-safe on macOS)
kernels = get_kernels()


# ============================================================================
# REFERENCE LOADING STATE
# ============================================================================

_ref_loaded = False
_last_ref_arrays_sig = None


def _ref_arrays_sig(ref_arrays: dict) -> bytes:
    """
    Stable content signature for ref arrays.

    We avoid caching by `id(ref_arrays)` because in parallel/IPC mode each request
    arrives as a distinct Python object despite having identical contents.
    """
    h = hashlib.blake2b(digest_size=16)
    for key in ("Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Fill Rate", "Fever Time"):
        if key not in ref_arrays:
            # Preserve old behavior: some call sites may omit optional FT/FF.
            h.update(b"\x00")
            continue
        arr = np.asarray(ref_arrays[key])
        h.update(str(arr.dtype).encode("utf-8"))
        h.update(arr.shape[0].to_bytes(4, "little", signed=False))
        h.update(arr.tobytes(order="C"))
    return h.digest()

# ============================================================================
# NUMPY STAGING BUFFERS (avoid huge per-call allocations / CPU zeroing)
# ============================================================================

_BATCH_STAGING = None
_MEGA_STAGING = None
_PARALLEL_STAGING = None
_SONG_FLAGS_HOST = None

# Cache for genome_base_stats uploads to avoid redundant from_numpy calls
# Stores (n_genomes, hash_bytes) of last uploaded stats
_GENOME_STATS_CACHE = None
_FTFF_COMBO_CACHE = {"budget": None, "n_combos": 0}


def _ensure_song_flags_host():
    global _SONG_FLAGS_HOST
    if _SONG_FLAGS_HOST is not None:
        return _SONG_FLAGS_HOST
    _SONG_FLAGS_HOST = np.zeros((fields.MAX_SONG_SLOTS, 12), dtype=np.int32)
    return _SONG_FLAGS_HOST


def _upload_song_flags(slot_to_flags: dict[int, tuple[int, ...]]) -> None:
    """
    Upload per-slot song flags used by `solve_ftff_parallel_kernel`.

    slot_to_flags entries must be 12-int tuples in this order:
      [is_p_ft, is_s_ft, is_p_ff, is_s_ff, is_p_pp, is_s_pp,
       is_p_cm, is_s_cm, is_p_fm, is_s_fm, is_p_ov, is_s_ov]
    """
    host = _ensure_song_flags_host()
    for slot, flags12 in slot_to_flags.items():
        if len(flags12) != 12:
            raise ValueError(f"song_flags for slot {slot} must be 12 ints, got {len(flags12)}")
        host[int(slot), :] = np.asarray(flags12, dtype=np.int32)
    fields.song_flags.from_numpy(host)


def _ensure_ftff_combo_tables(total_budget: int) -> int:
    """
    Ensure the FT/FF combo lookup tables are resident on GPU.

    The tables enumerate all (ft, ff) integer pairs such that:
      0 <= ft <= total_budget
      0 <= ff <= total_budget - ft

    Returns:
        n_combos: Number of valid combos for this budget.
    """
    ensure_ready()
    total_budget = int(total_budget)
    if total_budget < 0:
        total_budget = 0
    if total_budget > fields.MAX_TOTAL_BUDGET:
        raise ValueError(
            f"total_budget={total_budget} exceeds fields.MAX_TOTAL_BUDGET={fields.MAX_TOTAL_BUDGET}"
        )

    cached_budget = _FTFF_COMBO_CACHE.get("budget")
    if cached_budget == total_budget:
        return int(_FTFF_COMBO_CACHE.get("n_combos") or 0)

    ft = np.zeros((fields.MAX_FTFF_COMBOS,), dtype=np.int32)
    ff = np.zeros((fields.MAX_FTFF_COMBOS,), dtype=np.int32)

    idx = 0
    for ft_gems in range(total_budget + 1):
        for ff_gems in range(total_budget - ft_gems + 1):
            ft[idx] = ft_gems
            ff[idx] = ff_gems
            idx += 1

    n_combos = idx
    fields.ftff_combo_ft.from_numpy(ft)
    fields.ftff_combo_ff.from_numpy(ff)
    _FTFF_COMBO_CACHE["budget"] = total_budget
    _FTFF_COMBO_CACHE["n_combos"] = n_combos
    return n_combos


# ============================================================================
# SYNC POLICY
# ============================================================================
#
# Taichi kernels are ordered on the device; explicit ti.sync() is only required
# when the CPU needs results/timing *right now*. Excess sync points can dominate
# runtime (CPU stalls waiting for GPU).
#
# - GPU_SYNC_FOR_TIMING=1: allow extra syncs to measure kernel wall time
# - GPU_FORCE_SYNC=1: force all optional sync points on (debug)
_SYNC_FOR_TIMING = os.environ.get("GPU_SYNC_FOR_TIMING", "0") == "1"
_FORCE_SYNC = os.environ.get("GPU_FORCE_SYNC", "0") == "1"


def _maybe_sync(*, for_timing: bool = False) -> None:
    """Sync only when explicitly requested (timing/debug)."""
    if _FORCE_SYNC or (for_timing and _SYNC_FOR_TIMING):
        ti.sync()


def _ensure_batch_staging():
    global _BATCH_STAGING
    if _BATCH_STAGING is not None:
        return _BATCH_STAGING
    _BATCH_STAGING = {
        # [budget, count_fever, count_normal, ft_gems, ff_gems, head_len, genome_id, song_slot]
        "work_items": np.zeros((MAX_WORK_ITEMS, 8), dtype=np.int32),
        "fever_masks": np.zeros((MAX_WORK_ITEMS, MAX_HEAD_NOTES), dtype=np.int8),
        # [pp, cm, fm, p_val, s_val, ft, ff]
        "genome_base_stats": np.zeros((MAX_GENOMES, 7), dtype=np.int32),
    }
    return _BATCH_STAGING


def _ensure_mega_staging():
    global _MEGA_STAGING
    if _MEGA_STAGING is not None:
        return _MEGA_STAGING
    _MEGA_STAGING = {
        # [budget, count_fever, count_normal, ft_gems, ff_gems, head_len, genome_id, song_slot]
        "work_items": np.zeros((MAX_WORK_ITEMS, 8), dtype=np.int32),
        "fever_masks": np.zeros((MAX_WORK_ITEMS, MAX_HEAD_NOTES), dtype=np.int8),
        # [pp, cm, fm, p_val, s_val, ft, ff]
        "genome_base_stats": np.zeros((MAX_GENOMES, 7), dtype=np.int32),
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
        # [pp, cm, fm, p_val, s_val, ft, ff]
        "genome_base_stats": np.zeros((MAX_GENOMES, 7), dtype=np.int32),
        
        # Per-work-item buffers (reused per chunk)
        # [budget, count_fever, count_normal, ft_gems, ff_gems, head_len, genome_id, song_slot]
        "work_items": np.zeros((MAX_WORK_ITEMS, 8), dtype=np.int32),
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
    global _last_ref_arrays_sig
    if ref_arrays is not None:
        sig = _ref_arrays_sig(ref_arrays)
        if (not _ref_loaded) or (_last_ref_arrays_sig != sig):
            load_ref_arrays(ref_arrays)
            _last_ref_arrays_sig = sig
    
    # 4. Grid fields - ALWAYS allocate because Taichi JIT traces both branches
    #    of _calc_score_selector regardless of runtime `mode` value, so accessing
    #    `grid_fever_masks_bits` during compilation fails if the field is None.
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
    work_items_np = staging["work_items"]
    fever_masks_np = staging["fever_masks"]

    # Clear only the active prefix. (Avoid full zeroing of MAX_WORK_ITEMS each call.)
    work_items_np[:n, :] = 0
    fever_masks_np[:n, :] = 0
    
    for i, item in enumerate(batch_input):
        # [budget, count_fever, count_normal, ft_gems, ff_gems, head_len, genome_id]
        work_items_np[i, 0] = item["budget"]
        work_items_np[i, 1] = item["count_body_fever"]
        work_items_np[i, 2] = item["count_body_normal"]
        work_items_np[i, 3] = item.get("ft_gems", 0)
        work_items_np[i, 4] = item.get("ff_gems", 0)
        
        mask = item.get("fever_mask_head")
        if mask is not None:
            hl = min(len(mask), MAX_HEAD_NOTES)
            work_items_np[i, 5] = hl
            fever_masks_np[i, :hl] = mask[:hl].astype(np.int8)
            
        # Check for overrides
        p = item.get("_base_p_val", base_p_val)
        s = item.get("_base_s_val", base_s_val)
        stats_key = (p, s)
        
        if stats_key not in unique_stats_map:
            unique_stats_map[stats_key] = next_genome_id
            next_genome_id += 1
            
        work_items_np[i, 6] = unique_stats_map[stats_key]
    
    # Ensure we don't exceed max genomes (unlikely for reasonable batches)
    if next_genome_id > MAX_GENOMES:
        raise RuntimeError(f"Too many unique base stat combinations in batch ({next_genome_id} > {MAX_GENOMES})")
        
    # Upload per-genome stats
    genome_stats_np = staging["genome_base_stats"]
    genome_stats_np[:] = 0
    
    # [pp, cm, fm, p_val, s_val, ft, ff]
    # In this legacy mode, we assume constant pp/cm/fm/ft/ff for the whole batch
    # (except p/s which can vary per item).
    # FT/FF stats are not used in solve_batch_kernel (passed as 0 usually), 
    # but we should fill them to avoid garbage.
    
    for (p, s), gid in unique_stats_map.items():
        genome_stats_np[gid, 0] = cur_pp
        genome_stats_np[gid, 1] = cur_cm
        genome_stats_np[gid, 2] = cur_fm
        genome_stats_np[gid, 3] = p
        genome_stats_np[gid, 4] = s
        genome_stats_np[gid, 5] = 0 # Dummy FT stat
        genome_stats_np[gid, 6] = 0 # Dummy FF stat
        
    fields.genome_base_stats.from_numpy(genome_stats_np)
    
    # BULK transfer
    fields.work_items.from_numpy(work_items_np)
    fields.fever_masks.from_numpy(fever_masks_np)
    
    # Launch kernel
    kernels.solve_batch_kernel(
        n,
        is_p_ft, is_s_ft, is_p_ff, is_s_ff,
        is_p_pp, is_s_pp, is_p_cm, is_s_cm,
        is_p_fm, is_s_fm, is_p_ov, is_s_ov,
    )
    # NOTE: ti.sync() removed - to_numpy() internally syncs
    
    # Download results
    # [score, pp, cm, fm, ov, p_val, s_val]
    results_np = fields.result_stats.to_numpy()[:n]
    
    results = [
        (int(row[0]), int(row[1]), int(row[2]), int(row[3]),
         int(row[5]), int(row[6]), # p_val, s_val
         int(row[1]), int(row[2]), int(row[3]), int(row[4])) # repeats for generic tuple format
        for row in results_np
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
    staging = _ensure_mega_staging()
    
    # ========================================================================
    # UPLOAD PER-GENOME STATS
    # ========================================================================
    genome_stats_np = staging["genome_base_stats"]
    genome_stats_np[:] = 0

    for gid, (base_pp, base_cm, base_fm, base_p, base_s) in genome_stats.items():
        genome_stats_np[gid, 0] = base_pp
        genome_stats_np[gid, 1] = base_cm
        genome_stats_np[gid, 2] = base_fm
        genome_stats_np[gid, 3] = base_p
        genome_stats_np[gid, 4] = base_s
        genome_stats_np[gid, 5] = 0 # Dummy FT
        genome_stats_np[gid, 6] = 0 # Dummy FF
    
    fields.genome_base_stats.from_numpy(genome_stats_np)
    
    # ========================================================================
    # UPLOAD WORK ITEMS WITH GENOME IDS
    # ========================================================================
    work_items_np = staging["work_items"]
    fever_masks_np = staging["fever_masks"]
    
    work_items_np[:n, :] = 0
    fever_masks_np[:n, :] = 0
    
    for i, item in enumerate(work_items):
        work_items_np[i, 0] = item["budget"]
        work_items_np[i, 1] = item["count_body_fever"]
        work_items_np[i, 2] = item["count_body_normal"]
        work_items_np[i, 3] = item.get("ft_gems", 0)
        work_items_np[i, 4] = item.get("ff_gems", 0)
        work_items_np[i, 6] = genome_ids[i]
        
        mask = item.get("fever_mask_head")
        if mask is not None:
            head_len = min(len(mask), MAX_HEAD_NOTES)
            work_items_np[i, 5] = head_len
            fever_masks_np[i, :head_len] = mask[:head_len].astype(np.int8)
    
    fields.work_items.from_numpy(work_items_np)
    fields.fever_masks.from_numpy(fever_masks_np)
    
    # Launch kernel (uses genome lookup for base stats)
    kernels.solve_batch_kernel(
        n,
        is_p_ft, is_s_ft, is_p_ff, is_s_ff,
        is_p_pp, is_s_pp, is_p_cm, is_s_cm,
        is_p_fm, is_s_fm, is_p_ov, is_s_ov,
    )
    # NOTE: ti.sync() removed - to_numpy() internally syncs
    
    # Download results
    # [score, pp, cm, fm, ov, p_val, s_val]
    results_np = fields.result_stats.to_numpy()[:n]
    
    # Reduce: find best score per genome
    best_per_genome = {}
    
    # Need access to ft_gems/ff_gems for result tuple, which are in input work_items
    
    for i in range(n):
        genome_idx = int(genome_ids[i])
        row = results_np[i]
        score = int(row[0])
        
        if genome_idx not in best_per_genome or score > best_per_genome[genome_idx][0]:
            ft_in = work_items_np[i, 3]
            ff_in = work_items_np[i, 4]
            
            best_per_genome[genome_idx] = (
                score,
                int(row[1]), int(row[2]), int(row[3]),
                int(row[5]), int(row[6]), # p, s
                int(row[1]), int(row[2]), int(row[3]), int(row[4]), # g_pp, g_cm, g_fm, g_ov
                int(ft_in), int(ff_in)  # Added FT/FF specific to this result
            )
    
    return best_per_genome

# ============================================================================
# GPU TIMELINE PRECOMPUTATION (eliminates Numba typeof overhead)
# ============================================================================

_gpu_timeline_song_id_by_slot = [None] * fields.MAX_SONG_SLOTS  # Track last song per slot


def precompute_timeline_gpu(calc_song: dict, ref_arrays: dict, song_slot: int = 0) -> None:
    """
    Precompute all 161×161 fever timeline entries on GPU.
    
    This replaces the CPU Numba path (calculate_fever_timeline_indices) which
    had 28.7s typeof() overhead from 20M calls.
    
    GPU computes all 26,521 timelines in parallel in ~100ms.
    
    Args:
        calc_song: Song calculation context with timestamps/metadata
        ref_arrays: Reference lookup arrays (must include Fever Time/Fill Rate)
        song_slot: Grid slot to write to (0-7, default 0 for single-song mode)
        
    After calling this, the grid fields for song_slot are populated:
    - grid_count_body_fever[song_slot, ft, ff]
    - grid_count_body_normal[song_slot, ft, ff]
    - grid_head_len[song_slot, ft, ff]
    - grid_fever_masks[song_slot, ft, ff, :]
    - grid_fever_masks_bits[song_slot, ft, ff, :]
    """
    global _gpu_timeline_song_id_by_slot
    
    # Check if we already computed for this song
    meta = calc_song.get("metadata", {}) or {}
    song_data = calc_song.get("song_data", {}) or {}
    timestamps = song_data.get("timestamps", ())
    song_key = (
        str(meta.get("Song Name", "")),
        int(len(timestamps)),
        float(meta.get("Last Note Time", 0) or 0),
        int(meta.get("Long Notes", 0) or 0),
    )
    song_slot = int(song_slot)
    if song_slot < 0 or song_slot >= fields.MAX_SONG_SLOTS:
        raise ValueError(f"song_slot out of range: {song_slot}")

    if _gpu_timeline_song_id_by_slot[song_slot] == song_key:
        return  # Already computed
    
    # Ensure GPU is ready with refs and grid fields
    ensure_ready(ref_arrays, need_grid=True)
    
    # Upload song timestamps
    timestamps = np.asarray(calc_song["song_data"]["timestamps"], dtype=np.float32)
    total_notes = len(timestamps)
    
    # Pad to MAX_SONG_NOTES if needed
    if total_notes > fields.MAX_SONG_NOTES:
        raise ValueError(f"Song has {total_notes} notes, max is {fields.MAX_SONG_NOTES}")
    
    # Create padded array
    ts_padded = np.zeros(fields.MAX_SONG_NOTES, dtype=np.float32)
    ts_padded[:total_notes] = timestamps
    fields.song_timestamps.from_numpy(ts_padded)
    
    # Extract song metadata
    long_notes = int(calc_song["metadata"].get("Long Notes", 0))
    last_note_time = float(calc_song["metadata"].get("Last Note Time", 0))
    
    # Sync before timing
    _maybe_sync(for_timing=True)
    _t0 = time.perf_counter()
    
    # Launch GPU kernel to compute all 161×161 timelines for this song slot
    kernels.compute_timeline_grid_kernel(
        total_notes,
        long_notes,
        last_note_time,
        song_slot,  # Grid slot for batch coalescing
    )
    
    _maybe_sync(for_timing=True)
    _t1 = time.perf_counter()
    
    _gpu_timeline_song_id_by_slot[song_slot] = song_key
    
    if _SYNC_FOR_TIMING or _FORCE_SYNC:
        print(f"[GPU Timeline] Computed 161×161 grid in {(_t1 - _t0) * 1000:.1f}ms")


# ============================================================================
# GRID UPLOAD HELPERS
# ============================================================================

_grid_uploaded = False


def _upload_timeline_grid(timeline_grid):
    """Upload timeline grid to GPU fields (with caching)."""
    global _grid_uploaded
    
    # Skip if same grid already uploaded (major optimization!)
    # NOTE: In parallel mode the timeline grid is pickled across processes; `id()`
    # changes on every request, which defeats caching and can force repeated
    # 161x161 precompute + upload. Prefer a stable key when available.
    grid_id = getattr(timeline_grid, "cache_key", None) or id(timeline_grid)
    cached_id = get_last_uploaded_grid_id()
    if _grid_uploaded and cached_id == grid_id:
        return
    
    # Ensure all timelines are computed
    timeline_grid.precompute_all()
    
    # Import fields module
    from . import fields
    
    # Get grid data
    grid_size = timeline_grid.GRID_SIZE
    
    # OPTIMIZED: Extract all grid data using precomputed cache
    # This avoids 2.6M Python loop iterations!
    _t_extract = time.perf_counter()
    
    # Allocate 3D arrays matching slotted grid fields (slot 0 for CPU upload path)
    from .fields import MAX_SONG_SLOTS
    cbf_np = np.zeros((MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE), dtype=np.int32)
    cbn_np = np.zeros((MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE), dtype=np.int32)
    hl_np = np.zeros((MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE), dtype=np.int32)
    masks_np = np.zeros((MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE, MAX_HEAD_NOTES), dtype=np.int8)
    masks_bits_np = np.zeros((MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE, 4), dtype=np.uint32)
    
    # Fill slot 0 with timeline data
    song_slot = 0
    
    # Vectorized extraction: iterate once, extract directly into slot 0
    for ft_idx in range(grid_size):
        row = timeline_grid._timeline_grid[ft_idx]
        for ff_idx in range(grid_size):
            timeline = row[ff_idx]
            if timeline is not None:
                fever_mask_head, count_fever, count_normal, _ = timeline
                cbf_np[song_slot, ft_idx, ff_idx] = count_fever
                cbn_np[song_slot, ft_idx, ff_idx] = count_normal
                head_len = min(len(fever_mask_head), MAX_HEAD_NOTES)
                hl_np[song_slot, ft_idx, ff_idx] = head_len
                masks_np[song_slot, ft_idx, ff_idx, :head_len] = fever_mask_head[:head_len].astype(np.int8)
                
                # OPTIMIZED: Vectorized bit packing using NumPy
                # Convert bool array to bit positions, then pack
                if head_len > 0:
                    fever_bits = np.nonzero(fever_mask_head[:head_len])[0]
                    for bit_pos in fever_bits:
                        word_idx = bit_pos >> 5  # bit_pos // 32
                        bit_in_word = bit_pos & 31  # bit_pos % 32
                        masks_bits_np[song_slot, ft_idx, ff_idx, word_idx] |= np.uint32(1) << bit_in_word
    
    _profiler.record_upload(time.perf_counter() - _t_extract)
    
    # Upload to GPU
    _t_gpu_upload = time.perf_counter()
    fields.grid_count_body_fever.from_numpy(cbf_np)
    fields.grid_count_body_normal.from_numpy(cbn_np)
    fields.grid_head_len.from_numpy(hl_np)
    fields.grid_fever_masks.from_numpy(masks_np)
    fields.grid_fever_masks_bits.from_numpy(masks_bits_np)
    _profiler.record_upload(time.perf_counter() - _t_gpu_upload)

    
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
    ensure_ready(ref_arrays, need_grid=True)
    if isinstance(timeline_grid, dict) and "metadata" in timeline_grid and "song_data" in timeline_grid:
        precompute_timeline_gpu(timeline_grid, ref_arrays, song_slot=0)
    else:
        _upload_timeline_grid(timeline_grid)

    _upload_song_flags({
        0: (
            int(is_p_ft), int(is_s_ft), int(is_p_ff), int(is_s_ff),
            int(is_p_pp), int(is_s_pp), int(is_p_cm), int(is_s_cm),
            int(is_p_fm), int(is_s_fm), int(is_p_ov), int(is_s_ov),
        )
    })
    
    # Import fields module
    from . import fields
    
    n_genomes = len(genome_stats_list)
    if n_genomes == 0:
        return []
    
    if n_genomes > MAX_GENOMES:
        raise ValueError(f"Too many genomes: {n_genomes} > {MAX_GENOMES}")
    
    # Upload per-genome stats
    # [pp, cm, fm, p_val, s_val, ft, ff]
    stats_buf = np.zeros((n_genomes, 7), dtype=np.int32)
    
    for i, stats in enumerate(genome_stats_list):
        stats_buf[i, 0] = stats["base_pp"]
        stats_buf[i, 1] = stats["base_cm"]
        stats_buf[i, 2] = stats["base_fm"]
        stats_buf[i, 3] = stats["base_p_val"]
        stats_buf[i, 4] = stats["base_s_val"]
        stats_buf[i, 5] = stats["base_ft_stat"]
        stats_buf[i, 6] = stats["base_ff_stat"]
    
    fields.genome_base_stats.from_numpy(stats_buf)
    
    # Launch kernel
    kernels.solve_genomes_with_ftff_kernel(
        n_genomes,
        total_budget,
        gem_scale_fever,
        is_p_ft, is_s_ft, is_p_ff, is_s_ff,
        is_p_pp, is_s_pp, is_p_cm, is_s_cm,
        is_p_fm, is_s_fm, is_p_ov, is_s_ov,
        0,  # song_slot=0 for single-song mode
    )

    # NOTE: ti.sync() removed - to_numpy() internally syncs
    
    # Download results
    # [score, ft, ff, pp, cm, fm, ov]
    results_np = fields.genome_result_stats.to_numpy()[:n_genomes]
    
    results = []
    for i in range(n_genomes):
        row = results_np[i]
        results.append((
            int(row[0]), # score
            int(row[1]), # ft
            int(row[2]), # ff
            int(row[3]), # pp
            int(row[4]), # cm
            int(row[5]), # fm
            int(row[6]), # ov
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
    song_slot: int = 0,
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
        song_slot: Grid slot for batch coalescing (0-7, default 0)
        
    Returns:
        List of (score, ft, ff, pp, cm, fm, ov) tuples per genome
    """

    # Ensure grid fields are available; timeline data must be available in `song_slot`.
    ensure_ready(ref_arrays, need_grid=True)

    # If we were given a lightweight calc_song dict, compute the 161×161 grid on GPU
    # directly into this song slot (avoids pickling CPU timeline objects in parallel mode).
    if isinstance(timeline_grid, dict) and "metadata" in timeline_grid and "song_data" in timeline_grid:
        precompute_timeline_gpu(timeline_grid, ref_arrays, song_slot=song_slot)
    else:
        # CPU upload path (slot 0 only today).
        if int(song_slot) != 0:
            raise ValueError("SongTimelineGrid upload supports song_slot=0 only; use calc_song dict for multi-slot batching")
        _upload_timeline_grid(timeline_grid)

    # Upload per-slot flags used by the kernel.
    _upload_song_flags({
        int(song_slot): (
            int(is_p_ft), int(is_s_ft), int(is_p_ff), int(is_s_ff),
            int(is_p_pp), int(is_s_pp), int(is_p_cm), int(is_s_cm),
            int(is_p_fm), int(is_s_fm), int(is_p_ov), int(is_s_ov),
        )
    })
    
    # Import fields module
    from . import fields
    
    n_genomes = len(genome_stats_list)
    if n_genomes == 0:
        return []
    
    if n_genomes > MAX_GENOMES:
        raise ValueError(f"Too many genomes: {n_genomes} > {MAX_GENOMES}")
    
    # Get reusable staging buffers (avoid per-call allocations)
    staging = _ensure_parallel_staging()
    genome_stats_np = staging["genome_base_stats"]
    
    # Also track max allowed FT/FF per genome for work item generation
    max_ft_list = []
    max_ff_list = []
    
    for i, stats in enumerate(genome_stats_list):
        # [pp, cm, fm, p_val, s_val, ft, ff]
        genome_stats_np[i, 0] = stats["base_pp"]
        genome_stats_np[i, 1] = stats["base_cm"]
        genome_stats_np[i, 2] = stats["base_fm"]
        genome_stats_np[i, 3] = stats["base_p_val"]
        genome_stats_np[i, 4] = stats["base_s_val"]
        genome_stats_np[i, 5] = stats["base_ft_stat"]
        genome_stats_np[i, 6] = stats["base_ff_stat"]
        
        # Compute max FT/FF gems
        remaining_ft = 160 - stats["base_ft_stat"]
        remaining_ff = 160 - stats["base_ff_stat"]
        max_ft = remaining_ft // gem_scale_fever if remaining_ft > 0 else 0
        max_ff = remaining_ff // gem_scale_fever if remaining_ff > 0 else 0
        max_ft_list.append(min(total_budget, max_ft))
        max_ff_list.append(min(total_budget, max_ff))
    
    # OPTIMIZATION: Skip upload if genome stats unchanged (saves ~1-2s per run)
    # Hash only the portion of the buffer that's actually used
    global _GENOME_STATS_CACHE
    stats_slice = genome_stats_np[:n_genomes].tobytes()
    stats_hash = hash(stats_slice)
    cache_key = (n_genomes, stats_hash)
    
    if _GENOME_STATS_CACHE != cache_key:
        fields.genome_base_stats.from_numpy(genome_stats_np)
        _GENOME_STATS_CACHE = cache_key
    
    # Generate work items: (genome_id, ft, ff) for all valid combinations
    # Avoid huge Python list append overhead by precomputing size and filling arrays.
    n_work = 0
    for genome_idx in range(n_genomes):
        max_ft = int(max_ft_list[genome_idx])
        max_ff = int(max_ff_list[genome_idx])
        for ft in range(max_ft + 1):
            remaining = total_budget - ft
            n_work += (min(remaining, max_ff) + 1)

    work_genome = np.empty((n_work,), dtype=np.int32)
    work_ft = np.empty((n_work,), dtype=np.int32)
    work_ff = np.empty((n_work,), dtype=np.int32)
    work_budgets = np.empty((n_work,), dtype=np.int32) # Need budget per item

    pos = 0
    for genome_idx in range(n_genomes):
        max_ft = int(max_ft_list[genome_idx])
        max_ff = int(max_ff_list[genome_idx])
        for ft in range(max_ft + 1):
            remaining = total_budget - ft
            ff_max = min(remaining, max_ff)
            cnt = ff_max + 1
            work_genome[pos : pos + cnt] = genome_idx
            work_ft[pos : pos + cnt] = ft
            work_ff[pos : pos + cnt] = np.arange(cnt, dtype=np.int32)
            # Budget calculation happens in kernel anyway based on ft/ff, but we pass it for consistency
            # Actually kernel calculates budget = total_budget - ft - ff
            # But the vector format expects budget at index 0.
            # Let's precalculate it or pass total_budget to kernel?
            # The vector format for work_items is:
            # [budget, count_fever, count_normal, ft_gems, ff_gems, head_len, genome_id]
            # Wait, solve_ftff_parallel_kernel in kernels.py calculates budget itself:
            # budget = total_budget - ft - ff
            # But it READS budget from item[0].
            # So we MUST prefill item[0].
            
            # Vectorized budget fill:
            # budget = total - ft - ff
            # ff ranges from 0 to ff_max
            # budget ranges from (total-ft) down to (total-ft-ff_max)
            current_budget_base = total_budget - ft
            work_budgets[pos : pos + cnt] = current_budget_base - np.arange(cnt, dtype=np.int32)
            
            pos += cnt

    # Safety: ensure we filled exactly what we allocated
    if pos != n_work:
        raise RuntimeError(f"Internal error: filled work items {pos} != allocated {n_work}")
    
    if n_work == 0:
        return [(0, 0, 0, 0, 0, 0, 0) for _ in range(n_genomes)]
    
    # Process in chunks if exceeds MAX_WORK_ITEMS
    chunk_size = MAX_WORK_ITEMS
    num_chunks = (n_work + chunk_size - 1) // chunk_size
    
    # Initialize genome results ONCE before any chunks
    kernels.init_genome_results_kernel(n_genomes)
    
    # Get reusable work item buffers
    work_items_np = staging["work_items"]
    
    for chunk_idx in range(num_chunks):
        start = chunk_idx * chunk_size
        end = min(start + chunk_size, n_work)
        chunk_n = end - start
        
        # Copy work items into reusable buffers (no allocation needed)
        # [budget, count_fever, count_normal, ft_gems, ff_gems, head_len, genome_id]
        
        # We need to fill all 7 channels.
        # Channels 1 (count_fever), 2 (count_normal), 5 (head_len) are filled by kernel (from grid lookup).
        # We can leave them as 0 or whatever.
        # But wait, solve_ftff_parallel_kernel READS them from grid, it ignores input values for these?
        # Let's check kernel:
        # count_fever = grid_count_body_fever[ft_idx, ff_idx]
        # YES, kernel overwrites local variables from grid lookup. so input doesn't matter.
        
        # So we just need to pack budget, ft, ff, genome_id.
        
        # Flattened packing
        # Reset buffer for cleanliness (optional but safer)
        # work_items_np[:chunk_n, :] = 0 
        
        work_items_np[:chunk_n, 0] = work_budgets[start:end]      # budget
        work_items_np[:chunk_n, 3] = work_ft[start:end]           # ft_gems
        work_items_np[:chunk_n, 4] = work_ff[start:end]           # ff_gems
        work_items_np[:chunk_n, 6] = work_genome[start:end]       # genome_id
        work_items_np[:chunk_n, 7] = song_slot                     # song_slot (batch coalescing)


        
        # OPTIMIZATION: Upload only when profiling disabled to reduce overhead
        if _profiler.enabled:
            _t_upload = time.perf_counter()
            fields.work_items.from_numpy(work_items_np)
            _profiler.record_upload(time.perf_counter() - _t_upload)
            _t_kernel = time.perf_counter()
        else:
            # Fast path: no timing overhead
            fields.work_items.from_numpy(work_items_np)

        # Launch solve kernel
        kernels.solve_ftff_parallel_kernel(
            chunk_n,
            total_budget,
            gem_scale_fever,
            is_p_ft, is_s_ft, is_p_ff, is_s_ff,
            is_p_pp, is_s_pp, is_p_cm, is_s_cm,
            is_p_fm, is_s_fm, is_p_ov, is_s_ov,
        )
        
        # GPU-side reduction: safe best-per-genome aggregation for this chunk
        kernels.init_chunk_best_key_kernel(n_genomes)
        kernels.reduce_chunk_to_best_key_kernel(chunk_n)
        kernels.merge_chunk_best_to_genomes_kernel(n_genomes)
        # OPTIMIZATION: Only sync on last chunk to reduce overhead (558 syncs -> ~30 syncs)
        # GPU kernels are already queued, sync before download is sufficient
        is_last_chunk = (chunk_idx == num_chunks - 1)
        if _profiler.enabled and _SYNC_FOR_TIMING and is_last_chunk:
            _maybe_sync(for_timing=True)
            _profiler.record_kernel(time.perf_counter() - _t_kernel, genome_count=chunk_n)
    
    # Download only O(n_genomes) results (not O(n_work_items)!)
    # OPTIMIZATION: Ensure GPU work is complete before download
    _maybe_sync(for_timing=False)  # Single sync before download
    _t_download = time.perf_counter()
    # [score, ft, ff, pp, cm, fm, ov]
    results_np = fields.genome_result_stats.to_numpy()[:n_genomes]
    if _profiler.enabled:
        _profiler.record_download(time.perf_counter() - _t_download)
    
    # Build results in order
    results = []
    for i in range(n_genomes):
        row = results_np[i]
        results.append((
            int(row[0]), # score
            int(row[1]), # ft
            int(row[2]), # ff
            int(row[3]), # pp
            int(row[4]), # cm
            int(row[5]), # fm
            int(row[6]), # ov
        ))
    
    return results


def solve_genomes_parallel_merged(
    payloads: list[dict],
    *,
    total_budget: int,
    gem_scale_fever: int,
) -> list[list[tuple]]:
    """
    Merge multiple solve requests into a single (chunked) GPU execution.

    This uses:
    - per-song-slot timeline grids (MAX_SONG_SLOTS)
    - per-song-slot flags (fields.song_flags)
    - GPU-side reduction (reduce_chunk_to_best_key_kernel + merge_chunk_best_to_genomes_kernel)

    Each payload must contain:
      - genome_stats_list: list[dict]
      - timeline_grid: calc_song dict (metadata + song_data[timestamps])
      - is_p_*/is_s_* flags
      - ref_arrays
    """
    if not payloads:
        return []

    if len(payloads) > fields.MAX_SONG_SLOTS:
        raise ValueError(f"Too many merged payloads: {len(payloads)} > {fields.MAX_SONG_SLOTS}")

    total_budget = int(total_budget)
    gem_scale_fever = int(gem_scale_fever)

    # Validate ref_arrays compatibility (batch by content).
    ref0 = payloads[0].get("ref_arrays")
    if ref0 is None:
        raise ValueError("Merged solve: payload missing ref_arrays")
    sig0 = _ref_arrays_sig(ref0)
    for p in payloads[1:]:
        r = p.get("ref_arrays")
        if r is None:
            raise ValueError("Merged solve: payload missing ref_arrays")
        if _ref_arrays_sig(r) != sig0:
            raise ValueError("Merged solve requires compatible ref_arrays across payloads")

    ensure_ready(ref0, need_grid=True)
    log_batches = os.environ.get("GPU_BATCH_LOG", "0") == "1"

    # Assign slots 0..N-1 in payload order.
    slot_to_flags: dict[int, tuple[int, ...]] = {}
    genome_ranges: list[tuple[int, int]] = []

    staging = _ensure_parallel_staging()
    genome_stats_np = staging["genome_base_stats"]
    work_items_np = staging["work_items"]

    # Build merged genome_base_stats and precompute per-slot grids/flags.
    genome_offset = 0
    for slot, payload in enumerate(payloads):
        calc_song = payload.get("timeline_grid")
        if not (isinstance(calc_song, dict) and "metadata" in calc_song and "song_data" in calc_song):
            raise ValueError("Merged solve requires calc_song dict payload['timeline_grid']")

        precompute_timeline_gpu(calc_song, ref0, song_slot=slot)

        flags12 = (
            int(payload["is_p_ft"]), int(payload["is_s_ft"]),
            int(payload["is_p_ff"]), int(payload["is_s_ff"]),
            int(payload["is_p_pp"]), int(payload["is_s_pp"]),
            int(payload["is_p_cm"]), int(payload["is_s_cm"]),
            int(payload["is_p_fm"]), int(payload["is_s_fm"]),
            int(payload["is_p_ov"]), int(payload["is_s_ov"]),
        )
        slot_to_flags[slot] = flags12

        g_list = payload.get("genome_stats_list") or []
        n_g = len(g_list)
        if genome_offset + n_g > MAX_GENOMES:
            raise ValueError(f"Merged genomes exceed MAX_GENOMES: {genome_offset + n_g} > {MAX_GENOMES}")

        for i, stats in enumerate(g_list):
            dst = genome_offset + i
            genome_stats_np[dst, 0] = stats["base_pp"]
            genome_stats_np[dst, 1] = stats["base_cm"]
            genome_stats_np[dst, 2] = stats["base_fm"]
            genome_stats_np[dst, 3] = stats["base_p_val"]
            genome_stats_np[dst, 4] = stats["base_s_val"]
            genome_stats_np[dst, 5] = stats["base_ft_stat"]
            genome_stats_np[dst, 6] = stats["base_ff_stat"]

        genome_ranges.append((genome_offset, genome_offset + n_g))
        genome_offset += n_g

    n_total_genomes = genome_offset
    if n_total_genomes == 0:
        return [[] for _ in payloads]

    # Upload merged genome stats and per-slot flags once.
    fields.genome_base_stats.from_numpy(genome_stats_np)
    _upload_song_flags(slot_to_flags)

    # Initialize per-genome results once for the whole merged batch.
    kernels.init_genome_results_kernel(n_total_genomes)

    # Use any one payload's flags for legacy kernel args (the kernel reads song_flags by slot).
    any_flags = next(iter(slot_to_flags.values()))

    # Stream work items into MAX_WORK_ITEMS chunks.
    cur = 0
    total_work = 0
    chunks = 0
    for slot, payload in enumerate(payloads):
        g_list = payload.get("genome_stats_list") or []
        base_gid = genome_ranges[slot][0]
        for local_idx, stats in enumerate(g_list):
            gid = base_gid + local_idx

            remaining_ft = 160 - int(stats["base_ft_stat"])
            remaining_ff = 160 - int(stats["base_ff_stat"])
            max_ft = (remaining_ft // gem_scale_fever) if remaining_ft > 0 else 0
            max_ff = (remaining_ff // gem_scale_fever) if remaining_ff > 0 else 0
            if max_ft > total_budget:
                max_ft = total_budget
            if max_ff > total_budget:
                max_ff = total_budget

            for ft in range(max_ft + 1):
                ff_max = total_budget - ft
                if ff_max > max_ff:
                    ff_max = max_ff
                
                cnt = ff_max + 1
                if cnt <= 0:
                    continue
                
                # Flush if chunk would overflow
                if cur + cnt > MAX_WORK_ITEMS:
                    fields.work_items.from_numpy(work_items_np[:cur])
                    kernels.solve_ftff_parallel_kernel(
                        cur,
                        total_budget,
                        gem_scale_fever,
                        any_flags[0], any_flags[1], any_flags[2], any_flags[3],
                        any_flags[4], any_flags[5], any_flags[6], any_flags[7],
                        any_flags[8], any_flags[9], any_flags[10], any_flags[11],
                    )
                    kernels.init_chunk_best_key_kernel(n_total_genomes)
                    kernels.reduce_chunk_to_best_key_kernel(cur)
                    kernels.merge_chunk_best_to_genomes_kernel(n_total_genomes)
                    chunks += 1
                    cur = 0

                # Vectorized packing
                # [budget, count_fever, count_normal, ft_gems, ff_gems, head_len, genome_id, song_slot]
                end = cur + cnt
                
                # Budget: (total - ft) - [0, 1, ... cnt-1]
                work_items_np[cur:end, 0] = (total_budget - ft) - np.arange(cnt, dtype=np.int32)
                # ft_gems: constant ft
                work_items_np[cur:end, 3] = ft
                # ff_gems: [0, 1, ... cnt-1]
                work_items_np[cur:end, 4] = np.arange(cnt, dtype=np.int32)
                # genome_id: constant
                work_items_np[cur:end, 6] = gid
                # song_slot: constant
                work_items_np[cur:end, 7] = slot
                
                cur += cnt
                total_work += cnt


    # Final partial chunk
    if cur > 0:
        fields.work_items.from_numpy(work_items_np)
        kernels.solve_ftff_parallel_kernel(
            cur,
            total_budget,
            gem_scale_fever,
            any_flags[0], any_flags[1], any_flags[2], any_flags[3],
            any_flags[4], any_flags[5], any_flags[6], any_flags[7],
            any_flags[8], any_flags[9], any_flags[10], any_flags[11],
        )
        kernels.init_chunk_best_key_kernel(n_total_genomes)
        kernels.reduce_chunk_to_best_key_kernel(cur)
        kernels.merge_chunk_best_to_genomes_kernel(n_total_genomes)
        chunks += 1

    if log_batches:
        print(f"[GPU_BATCH] merged_requests={len(payloads)} genomes={n_total_genomes} work_items={total_work} chunks={chunks}")

    # Download O(total_genomes) results once and demux.
    results_np = fields.genome_result_stats.to_numpy()[:n_total_genomes]
    out: list[list[tuple]] = []
    for start, end in genome_ranges:
        req = []
        for i in range(start, end):
            row = results_np[i]
            req.append((
                int(row[0]),  # score
                int(row[1]),  # ft
                int(row[2]),  # ff
                int(row[3]),  # pp
                int(row[4]),  # cm
                int(row[5]),  # fm
                int(row[6]),  # ov
            ))
        out.append(req)
    return out



# ============================================================================
# GPU-NATIVE GA OPERATORS (UNUSED - Future infrastructure)
# ============================================================================
# These functions implement GPU-side GA operators (selection, crossover, mutation)
# but are NOT currently wired into genetic.py. They exist as prep work for a
# future GPU-native GA where the entire population lives on GPU.
#
# To complete: need encoder (genome -> item_ids) and integration in genetic.py.
# ============================================================================

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
    # GPU-only op; no CPU readback needed.


def ga_upload_item_stats(
    item_stats_np: np.ndarray,
    slot_start_np: np.ndarray,
    slot_count_np: np.ndarray,
) -> int:
    """
    Upload item stats and slot pool boundaries for GPU-native GA.
    
    Args:
        item_stats_np: (n_items, 10) int32 - per-item stats
        slot_start_np: (9,) int32 - first item_id per slot
        slot_count_np: (9,) int32 - count of items per slot
        
    Returns:
        Number of items uploaded
    """
    ensure_ready()
    n_items = int(item_stats_np.shape[0])
    
    if n_items > fields.MAX_ITEMS:
        raise ValueError(f"Too many items: {n_items} > {fields.MAX_ITEMS}")
    
    # Upload item stats (padded to MAX_ITEMS)
    stats_buf = np.zeros((fields.MAX_ITEMS, fields.ITEM_STAT_DIM), dtype=np.int32)
    stats_buf[:n_items, :] = np.asarray(item_stats_np[:, :fields.ITEM_STAT_DIM], dtype=np.int32)
    fields.item_stats.from_numpy(stats_buf)
    
    # Upload slot pool boundaries
    start_buf = np.zeros(fields.MAX_SLOTS, dtype=np.int32)
    count_buf = np.zeros(fields.MAX_SLOTS, dtype=np.int32)
    start_buf[:len(slot_start_np)] = np.asarray(slot_start_np, dtype=np.int32)
    count_buf[:len(slot_count_np)] = np.asarray(slot_count_np, dtype=np.int32)
    fields.slot_start.from_numpy(start_buf)
    fields.slot_count.from_numpy(count_buf)
    
    return n_items


def ga_upload_base_fixed_stats(base_stats_np: np.ndarray) -> None:
    """
    Upload fixed base stats (added to all genomes during aggregation).
    
    Args:
        base_stats_np: (10,) int32 - base stats [PP, CM, FM, FT, FF, Beat, Vibe, Rush, Flow, Chill]
    """
    ensure_ready()
    buf = np.zeros(fields.ITEM_STAT_DIM, dtype=np.int32)
    buf[:len(base_stats_np)] = np.asarray(base_stats_np, dtype=np.int32)
    fields.base_fixed_stats.from_numpy(buf)


def ga_aggregate_stats(
    n_genomes: int,
    n_slots: int = 9,
    *,
    is_p_ft: int = 0, is_s_ft: int = 0,
    is_p_ff: int = 0, is_s_ff: int = 0,
    is_p_pp: int = 0, is_s_pp: int = 0,
    is_p_cm: int = 0, is_s_cm: int = 0,
    is_p_fm: int = 0, is_s_fm: int = 0,
    is_p_ov: int = 0, is_s_ov: int = 0,
) -> None:
    """
    Aggregate item stats into genome_base_stats on GPU.
    
    For each genome, sums base_fixed_stats + item_stats[population_indices[g, s]]
    across all slots, then computes p_val/s_val from color flags.
    
    PREREQUISITES:
    - Call ga_upload_population_indices() first
    - Call ga_upload_item_stats() first
    - Call ga_upload_base_fixed_stats() first
    
    Args:
        n_genomes: Number of genomes to aggregate
        n_slots: Number of slots per genome (default 9)
        is_p_*: Primary color contribution flags (0 or 1)
        is_s_*: Secondary color contribution flags (0 or 1)
    """
    ensure_ready()
    kernels.ga_aggregate_genome_stats_kernel(
        int(n_genomes),
        int(n_slots),
        int(is_p_ft), int(is_s_ft),
        int(is_p_ff), int(is_s_ff),
        int(is_p_pp), int(is_s_pp),
        int(is_p_cm), int(is_s_cm),
        int(is_p_fm), int(is_s_fm),
        int(is_p_ov), int(is_s_ov),
    )


def ga_evaluate_population(
    n_genomes: int,
    n_slots: int = 9,
    *,
    total_budget: int,
    gem_scale_fever: int = 3,
    song_slot: int = 0,
    is_p_ft: int = 0, is_s_ft: int = 0,
    is_p_ff: int = 0, is_s_ff: int = 0,
    is_p_pp: int = 0, is_s_pp: int = 0,
    is_p_cm: int = 0, is_s_cm: int = 0,
    is_p_fm: int = 0, is_s_fm: int = 0,
    is_p_ov: int = 0, is_s_ov: int = 0,
) -> None:
    """
    GPU-native population evaluation: aggregate stats + evaluate + copy scores.
    
    This is the main GA evaluation function for GPU-native mode. It:
    1. Aggregates item stats → genome_base_stats (ga_aggregate_genome_stats_kernel)
    2. Evaluates all (ft, ff) combos → genome_result_stats (solve_genomes_with_ftff_kernel)
    3. Copies scores to ga_scores for selection (ga_copy_scores_kernel)
    
    PREREQUISITES:
    - Call ga_upload_population_indices() with encoded population
    - Call ga_upload_item_stats() with item stats and slot pools
    - Call ga_upload_base_fixed_stats() with base stats
    - Upload timeline grid using precompute_timeline_gpu() or _upload_timeline_grid()
    
    Args:
        n_genomes: Number of genomes to evaluate
        n_slots: Slots per genome (default 9)
        total_budget: Total gem budget
        gem_scale_fever: Stat points per FT/FF gem (default 3)
        song_slot: Timeline grid slot (0 for single-song)
        is_p_*, is_s_*: Color contribution flags
    """
    ensure_ready()
    n_genomes = int(n_genomes)
    n_slots = int(n_slots)
    
    # Step 1: Aggregate item stats into genome_base_stats
    kernels.ga_aggregate_genome_stats_kernel(
        n_genomes, n_slots,
        int(is_p_ft), int(is_s_ft),
        int(is_p_ff), int(is_s_ff),
        int(is_p_pp), int(is_s_pp),
        int(is_p_cm), int(is_s_cm),
        int(is_p_fm), int(is_s_fm),
        int(is_p_ov), int(is_s_ov),
    )
    
    # Step 2: Evaluate genomes using existing FT/FF iteration kernel
    total_budget_i = int(total_budget)
    gem_scale_fever_i = int(gem_scale_fever)
    song_slot_i = int(song_slot)

    # Precompute FT/FF combo tables once per budget (tiny upload, reused across generations).
    n_combos = _ensure_ftff_combo_tables(total_budget_i)

    # Step 2: GPU-parallel evaluation across (genome, ft/ff combo), writing best key per genome.
    kernels.init_chunk_best_key_kernel(n_genomes)
    combo_chunk = n_combos
    # Chunk very large workloads to reduce kernel wall time (helps avoid Windows TDR on Vulkan).
    if n_genomes * n_combos > MAX_WORK_ITEMS:
        combo_chunk = 1024

    for offset in range(0, n_combos, combo_chunk):
        kernels.ga_find_best_combo_key_kernel(
            n_genomes,
            n_combos,
            int(offset),
            int(min(combo_chunk, n_combos - offset)),
            total_budget_i,
            gem_scale_fever_i,
            int(is_p_ft), int(is_s_ft),
            int(is_p_ff), int(is_s_ff),
            int(is_p_pp), int(is_s_pp),
            int(is_p_cm), int(is_s_cm),
            int(is_p_fm), int(is_s_fm),
            int(is_p_ov), int(is_s_ov),
            song_slot_i,
        )

    # Step 3: Finalize best combo → genome_result_stats + ga_scores (one thread per genome).
    kernels.ga_write_best_results_from_key_kernel(
        n_genomes,
        total_budget_i,
        gem_scale_fever_i,
        int(is_p_ft), int(is_s_ft),
        int(is_p_ff), int(is_s_ff),
        int(is_p_pp), int(is_s_pp),
        int(is_p_cm), int(is_s_cm),
        int(is_p_fm), int(is_s_fm),
        int(is_p_ov), int(is_s_ov),
        song_slot_i,
    )


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
    elite_indices: np.ndarray | None = None,
) -> None:
    """
    Run one GPU-side GA operator step on resident population:
      selection -> crossover+mutation -> [elitism] -> swap buffers.
    
    Args:
        n_genomes: Population size
        n_slots: Slots per genome (default 9)
        mutation_rate: Probability of mutation per genome (default 0.02)
        tournament_k: Tournament size for selection (default 3)
        elite_count: Number of elites to preserve (default 2)
        elite_indices: Optional array of elite genome indices from current gen.
                      If provided, these genomes are copied to front of next gen.
                      If None and elite_count > 0, uses indices [0..elite_count-1].
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

    # Step 1: Selection
    kernels.ga_select_parents_tournament_kernel(n_genomes, tournament_k)
    
    # Step 2: Crossover + Mutation (with mini uniqueness repair)
    kernels.ga_crossover_mutate_kernel(n_genomes, n_slots, mr_fp, elite_count)
    
    # Step 3: Elitism - copy elite genomes to front of next generation
    if elite_count > 0:
        if elite_indices is None:
            # Default: use first elite_count genomes as elites
            elite_indices = np.arange(elite_count, dtype=np.int32)
        else:
            elite_indices = np.asarray(elite_indices[:elite_count], dtype=np.int32)
        kernels.ga_copy_elites_kernel(len(elite_indices), n_slots, elite_indices)
    
    # Step 4: Swap buffers (next -> current)
    kernels.ga_swap_populations_kernel(n_genomes, n_slots)


def ga_download_population_indices(*, n_genomes: int, n_slots: int = 9) -> np.ndarray:
    """Download the current resident population indices (for testing / debugging)."""
    ensure_ready()
    n_genomes = int(n_genomes)
    n_slots = int(n_slots)
    out = fields.population_indices.to_numpy()
    return np.asarray(out[:n_genomes, :n_slots], dtype=np.int32)


def ga_download_scores(n_genomes: int) -> np.ndarray:
    """
    Download fitness scores from GPU (for CPU-side elitism).
    
    Args:
        n_genomes: Number of genomes to download
        
    Returns:
        np.ndarray: (n_genomes,) int32 array of scores
    """
    ensure_ready()
    n_genomes = int(n_genomes)
    out = fields.ga_scores.to_numpy()
    return np.asarray(out[:n_genomes], dtype=np.int32)


def ga_download_results(n_genomes: int) -> np.ndarray:
    """
    Download full evaluation results from GPU.
    
    Args:
        n_genomes: Number of genomes to download
        
    Returns:
        np.ndarray: (n_genomes, 7) int32 array [score, ft, ff, pp, cm, fm, ov]
    """
    ensure_ready()
    n_genomes = int(n_genomes)
    out = fields.genome_result_stats.to_numpy()
    return np.asarray(out[:n_genomes], dtype=np.int32)
