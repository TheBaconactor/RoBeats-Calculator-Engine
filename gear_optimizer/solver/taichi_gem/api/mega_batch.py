"""
API Mega Batch - Multi-genome batch population solver.

This module provides the highest-performance mega-batch solver:
- mega_batch_solve_population: Process all work items from ALL genomes in one kernel
"""
from __future__ import annotations

import numpy as np

from .. import fields
from ..fields import MAX_WORK_ITEMS, MAX_HEAD_NOTES, MAX_GENOMES
from ..kernel_loader import get_kernels

from .initialization import ensure_ready, _ensure_mega_staging

# Get appropriate kernels for current platform (Metal-safe on macOS)
kernels = get_kernels()


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
    genome_stats_np = staging["genome_base_stats"]
    genome_stats_np[:] = 0

    for gid, (base_pp, base_cm, base_fm, base_p, base_s) in genome_stats.items():
        genome_stats_np[gid, 0] = base_pp
        genome_stats_np[gid, 1] = base_cm
        genome_stats_np[gid, 2] = base_fm
        genome_stats_np[gid, 3] = base_p
        genome_stats_np[gid, 4] = base_s
        genome_stats_np[gid, 5] = 0  # Dummy FT
        genome_stats_np[gid, 6] = 0  # Dummy FF

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
                int(row[5]), int(row[6]),  # p, s
                int(row[1]), int(row[2]), int(row[3]), int(row[4]),  # g_pp, g_cm, g_fm, g_ov
                int(ft_in), int(ff_in)  # Added FT/FF specific to this result
            )

    return best_per_genome
