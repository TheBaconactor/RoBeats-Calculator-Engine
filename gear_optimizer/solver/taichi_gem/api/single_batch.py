"""
API Single & Batch Optimization - Single-item and batch gem optimization.

This module provides the main gem optimization entry points:
- optimize_gems_gpu: Single-item optimization (wrapper for batch API)
- optimize_gems_batch_gpu: Batch gem optimization with automatic genome mapping
"""
from __future__ import annotations

import numpy as np

from .. import fields
from ..fields import MAX_WORK_ITEMS, MAX_HEAD_NOTES, MAX_GENOMES
from ..kernel_loader import get_kernels

from .initialization import ensure_ready, _ensure_batch_staging

# Get appropriate kernels for current platform (Metal-safe on macOS)
kernels = get_kernels()


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
        genome_stats_np[gid, 5] = 0  # Dummy FT stat
        genome_stats_np[gid, 6] = 0  # Dummy FF stat

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
         int(row[5]), int(row[6]),  # p_val, s_val
         int(row[1]), int(row[2]), int(row[3]), int(row[4]))  # repeats for generic tuple format
        for row in results_np
    ]

    return results
