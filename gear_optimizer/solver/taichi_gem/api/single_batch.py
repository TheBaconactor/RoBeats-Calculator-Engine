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

_OPT_BATCH_WORK_ITEMS_STAGING: np.ndarray | None = None  # (>=n, 8) int32
_OPT_BATCH_FEVER_MASKS_STAGING: np.ndarray | None = None  # (>=n, MAX_HEAD_NOTES) int8
_OPT_BATCH_GENOME_BASE_STATS_STAGING: np.ndarray | None = None  # (MAX_GENOMES, 7) int16


def _ensure_optimize_batch_staging(n_items: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Allocate and reuse small host staging buffers for optimize_gems_batch_gpu().

    The legacy `_ensure_batch_staging()` allocates MAX_WORK_ITEMS host buffers so it can
    use full-field from_numpy() uploads, but that is extremely expensive on Vulkan.
    We prefer variable-length ndarray upload kernels and only allocate as much host
    storage as the caller actually needs.
    """
    global _OPT_BATCH_WORK_ITEMS_STAGING, _OPT_BATCH_FEVER_MASKS_STAGING, _OPT_BATCH_GENOME_BASE_STATS_STAGING

    n = int(n_items)
    if n <= 0:
        work = np.empty((0, 8), dtype=np.int32)
        masks = np.empty((0, int(MAX_HEAD_NOTES)), dtype=np.int8)
    else:
        cur = (
            int(_OPT_BATCH_WORK_ITEMS_STAGING.shape[0]) if isinstance(_OPT_BATCH_WORK_ITEMS_STAGING, np.ndarray) else 0
        )
        if cur < n:
            cap = max(n, 1024 if cur <= 0 else (cur * 2))
            cap = min(cap, int(MAX_WORK_ITEMS))
            _OPT_BATCH_WORK_ITEMS_STAGING = np.empty((cap, 8), dtype=np.int32)
        cur_m = (
            int(_OPT_BATCH_FEVER_MASKS_STAGING.shape[0])
            if isinstance(_OPT_BATCH_FEVER_MASKS_STAGING, np.ndarray)
            else 0
        )
        if cur_m < n:
            cap_m = max(n, 1024 if cur_m <= 0 else (cur_m * 2))
            cap_m = min(cap_m, int(MAX_WORK_ITEMS))
            _OPT_BATCH_FEVER_MASKS_STAGING = np.empty((cap_m, int(MAX_HEAD_NOTES)), dtype=np.int8)
        work = _OPT_BATCH_WORK_ITEMS_STAGING[:n, :]
        masks = _OPT_BATCH_FEVER_MASKS_STAGING[:n, :]

    if _OPT_BATCH_GENOME_BASE_STATS_STAGING is None or int(_OPT_BATCH_GENOME_BASE_STATS_STAGING.shape[0]) != int(
        MAX_GENOMES
    ):
        _OPT_BATCH_GENOME_BASE_STATS_STAGING = np.empty((int(MAX_GENOMES), 7), dtype=np.int16)

    return work, masks, _OPT_BATCH_GENOME_BASE_STATS_STAGING


# ============================================================================
# SINGLE-ITEM OPTIMIZATION
# ============================================================================


def optimize_gems_gpu(
    budget: int,
    fever_mask_head: np.ndarray,
    count_body_fever: int,
    count_body_normal: int,
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
    ref_arrays: dict,
):
    """
    Single-item GPU gem optimization (for compatibility with existing code).

    Wraps the batch API for single-item use.
    """
    batch_input = [
        {
            "budget": budget,
            "fever_mask_head": fever_mask_head,
            "count_body_fever": count_body_fever,
            "count_body_normal": count_body_normal,
            "ft_gems": 0,
            "ff_gems": 0,
        }
    ]

    results = optimize_gems_batch_gpu(
        batch_input,
        cur_pp,
        cur_cm,
        cur_fm,
        base_p_val=cur_p_val,
        base_s_val=cur_s_val,
        is_p_ft=0,
        is_s_ft=0,
        is_p_ff=0,
        is_s_ff=0,
        is_p_pp=is_p_pp,
        is_s_pp=is_s_pp,
        is_p_cm=is_p_cm,
        is_s_cm=is_s_cm,
        is_p_fm=is_p_fm,
        is_s_fm=is_s_fm,
        is_p_ov=is_p_ov,
        is_s_ov=is_s_ov,
        ref_arrays=ref_arrays,
    )

    return results[0] if results else None


# ============================================================================
# BATCH OPTIMIZATION
# ============================================================================


def optimize_gems_batch_gpu(
    batch_input: list,
    cur_pp: int,
    cur_cm: int,
    cur_fm: int,
    base_p_val: int,
    base_s_val: int,
    is_p_ft: int,
    is_s_ft: int,
    is_p_ff: int,
    is_s_ff: int,
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
                chunk,
                cur_pp,
                cur_cm,
                cur_fm,
                base_p_val,
                base_s_val,
                is_p_ft,
                is_s_ft,
                is_p_ff,
                is_s_ff,
                is_p_pp,
                is_s_pp,
                is_p_cm,
                is_s_cm,
                is_p_fm,
                is_s_fm,
                is_p_ov,
                is_s_ov,
                ref_arrays,
            )
            all_results.extend(chunk_results)
        return all_results

    ensure_ready(ref_arrays)
    fields.ensure_legacy_work_fields_allocated()

    # ========================================================================
    # DYNAMIC GENOME MAPPING (Fix for Batch Coalescing)
    # ========================================================================
    # Identify unique (base_p, base_s) pairs to support merged batches

    unique_stats_map = {}  # (p, s) -> genome_id
    next_genome_id = 0

    # Use small host staging buffers sized to the active batch. We upload via ndarray kernels
    # to avoid full-field transfers of MAX_WORK_ITEMS legacy buffers.
    work_items_np, fever_masks_np, genome_stats_np = _ensure_optimize_batch_staging(int(n))

    for i, item in enumerate(batch_input):
        # [budget, count_fever, count_normal, ft_gems, ff_gems, head_len, genome_id]
        work_items_np[i, 0] = int(item["budget"])
        work_items_np[i, 1] = int(item["count_body_fever"])
        work_items_np[i, 2] = int(item["count_body_normal"])
        work_items_np[i, 3] = int(item.get("ft_gems", 0) or 0)
        work_items_np[i, 4] = int(item.get("ff_gems", 0) or 0)

        mask = item.get("fever_mask_head")
        if mask is not None:
            mask_arr = np.asarray(mask, dtype=np.int8)
            hl = min(int(mask_arr.shape[0]), int(MAX_HEAD_NOTES))
            work_items_np[i, 5] = int(hl)
            if hl > 0:
                fever_masks_np[i, :hl] = mask_arr[:hl]
        else:
            work_items_np[i, 5] = 0

        # Check for overrides
        p = item.get("_base_p_val", base_p_val)
        s = item.get("_base_s_val", base_s_val)
        stats_key = (p, s)

        if stats_key not in unique_stats_map:
            unique_stats_map[stats_key] = next_genome_id
            next_genome_id += 1

        work_items_np[i, 6] = unique_stats_map[stats_key]
        work_items_np[i, 7] = 0  # song_slot (unused by solve_batch_kernel)

    # Ensure we don't exceed max genomes (unlikely for reasonable batches)
    if next_genome_id > MAX_GENOMES:
        raise RuntimeError(f"Too many unique base stat combinations in batch ({next_genome_id} > {MAX_GENOMES})")

    # Upload per-genome stats
    # [pp, cm, fm, p_val, s_val, ft, ff]
    # In this mode, we assume constant pp/cm/fm/ft/ff for the whole batch
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

    # Upload the active prefix via ndarray kernels (avoid full-field legacy buffer transfers).
    try:
        kernels.copy_work_items_from_ndarray_kernel(int(n), work_items_np)
        kernels.copy_fever_masks_from_ndarray_kernel(int(n), int(MAX_HEAD_NOTES), fever_masks_np)
    except Exception:
        # Fallback: allocate full padded host buffers and use from_numpy (slow, but preserves compatibility).
        staging_full = _ensure_batch_staging()
        work_full = staging_full["work_items"]
        masks_full = staging_full["fever_masks"]
        work_full[:n, :] = work_items_np[:n, :]
        masks_full[:n, :] = fever_masks_np[:n, :]
        fields.work_items.from_numpy(work_full)
        fields.fever_masks.from_numpy(masks_full)

    # Launch kernel
    kernels.solve_batch_kernel(
        n,
        is_p_ft,
        is_s_ft,
        is_p_ff,
        is_s_ff,
        is_p_pp,
        is_s_pp,
        is_p_cm,
        is_s_cm,
        is_p_fm,
        is_s_fm,
        is_p_ov,
        is_s_ov,
    )
    # NOTE: ti.sync() removed - to_numpy() internally syncs

    # Download results
    # [score, pp, cm, fm, ov, p_val, s_val]
    results_np = None
    try:
        full_shape = getattr(fields.result_stats, "shape", None)
        full_elems = int(full_shape[0]) * 7 if full_shape is not None else 0

        staging_candidates = [
            ("staging_4096", getattr(fields, "result_stats_download_staging_4096", None)),
            ("staging_65536", getattr(fields, "result_stats_download_staging_65536", None)),
            ("staging_262144", getattr(fields, "result_stats_download_staging_262144", None)),
        ]
        best = None
        for name, fld in staging_candidates:
            if fld is None:
                continue
            shape = getattr(fld, "shape", None)
            if not shape or len(shape) < 1:
                continue
            if n <= int(shape[0]):
                elems = int(shape[0]) * 7
                if best is None or elems < best[0]:
                    best = (elems, name, fld)

        if best is not None and full_elems > int(best[0]):
            _elems, _name, staging_fld = best
            kernels.copy_result_stats_to_download_staging_kernel(staging_fld, int(n))
            results_np = staging_fld.to_numpy()[:n]
    except Exception:
        results_np = None

    if results_np is None:
        results_np = fields.result_stats.to_numpy()[:n]

    rows_list = np.asarray(results_np[:n, :7], dtype=np.int32).tolist()
    results = [(r[0], r[1], r[2], r[3], r[5], r[6], r[1], r[2], r[3], r[4]) for r in rows_list]

    return results
