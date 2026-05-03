"""
API Parallel Solvers - Maximum parallelism genome solvers.

This module provides GPU genome solvers:
- solve_genomes_with_ftff: GPU-resident FT/FF iteration (no CPU work-item staging)
- solve_genomes_from_registry: GPU-resident stat aggregation + FT/FF combo search
"""

from __future__ import annotations

import os
import time

import numpy as np

from gear_optimizer.core.fallback_monitor import warn_fallback
from gear_optimizer.solver.gpu_profiler import get_gpu_profiler

from .. import fields
from ..fields import MAX_GENOMES
from ..kernel_loader import get_kernels
from ..ftff_combos import ftff_combo_arrays

from .initialization import (
    ensure_ready,
    _maybe_sync,
    _SYNC_FOR_TIMING,
    _ensure_ftff_combo_tables,
)
from .timeline import precompute_timeline_gpu
from .ga_operations import (
    ga_upload_population_indices,
    ga_evaluate_population,
    ga_download_results,
)

_profiler = get_gpu_profiler()

# Cache for genome_base_stats uploads to avoid redundant from_numpy calls
_GENOME_STATS_BUFFER = None

# The Vulkan block-per-genome FT/FF solver is currently unsafe on AMD/Vulkan
# (score mismatches vs the canonical registry path). Keep it opt-in only.
_USE_FTFF_BLOCK_KERNEL = str(os.environ.get("GPU_FTFF_BLOCK_KERNEL", "0") or "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

# Get appropriate kernels for current platform (Metal-safe on macOS)
kernels = get_kernels()

# -----------------------------------------------------------------------------
# Legacy helpers (kept for regression tests + strict fallback policy).
# -----------------------------------------------------------------------------


def _upload_work_items_chunk(arr: np.ndarray, n_items: int) -> None:
    """
    Upload a prefix of a 2D int32 array via the prefix-copy kernel.

    We intentionally do NOT fall back to `field.from_numpy()` here; fallback is both
    slow (CPU zeroing + full-shape upload) and can hide missing-kernel regressions.
    """
    n = max(0, int(n_items))
    try:
        src = np.asarray(arr, dtype=np.int32)
    except Exception:
        src = arr
    try:
        kernel = getattr(kernels, "copy_work_items_from_ndarray_kernel")
    except Exception as exc:
        warn_fallback(
            "gpu.parallel_solvers.work_items_upload_kernel",
            "work-items prefix upload kernel not available",
            fatal=True,
            exc=exc,
        )
        return
    try:
        kernel(int(n), src[:n])
    except Exception as exc:
        warn_fallback(
            "gpu.parallel_solvers.work_items_upload_kernel",
            "work-items prefix upload kernel failed",
            fatal=True,
            exc=exc,
        )


def _get_ftff_host_combo_arrays(total_budget: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Return the host-side FT/FF combo enumeration for a given budget.

    Order matches the triangular enumeration used by the GPU combo tables:
      ft=0, ff=0..B ; ft=1, ff=0..B-1 ; ... ; ft=B, ff=0
    """
    return ftff_combo_arrays(int(total_budget))


def _combo_indices_for_limits(
    combo_ft: np.ndarray,
    combo_ff: np.ndarray,
    *,
    max_ft: int,
    max_ff: int,
    cache: dict | None = None,
) -> np.ndarray:
    """
    Filter combo indices by per-axis limits with a tiny cache.

    Returns a stable cached ndarray when `cache` is provided.
    """
    cache_key = (int(max_ft), int(max_ff), int(getattr(combo_ft, "shape", (0,))[0]))
    if cache is not None:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
    ft = np.asarray(combo_ft, dtype=np.int32)
    ff = np.asarray(combo_ff, dtype=np.int32)
    mask = (ft <= int(max_ft)) & (ff <= int(max_ff))
    idx = np.nonzero(mask)[0].astype(np.int32, copy=False)
    if cache is not None:
        cache[cache_key] = idx
    return idx


def _results_from_stats(results_np: np.ndarray, n_genomes: int) -> list[tuple[int, int, int, int, int, int, int]]:
    n = max(0, int(n_genomes))
    if n <= 0:
        return []
    rows = np.asarray(results_np[:n, :7], dtype=np.int32)
    return [tuple(row) for row in rows.tolist()]


def solve_genomes_with_ftff(
    genome_stats_list: list,
    timeline_grid,
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
    total_budget: int = 90,
    gem_scale_fever: int = 3,
    song_slot: int = 0,
) -> list:
    """
    Solve gem allocation for multiple genomes with GPU-resident FT/FF iteration.

    Uploads the timeline grid ONCE, then processes all genomes in a single
    kernel launch that iterates FT/FF combinations on-GPU.

    ~100x faster than the old approach which transferred 400k work items.

    Args:
        genome_stats_list: List of dicts with base stats per genome
    timeline_grid: calc_song dict (precomputed on GPU)
        is_*: Color contribution flags (0/1)
        ref_arrays: Reference lookup arrays
        total_budget: Gem budget (default 90)
        gem_scale_fever: Stats per fever gem (default 3)

    Returns:
        List of (score, ft, ff, pp, cm, fm, ov) tuples per genome
    """
    ensure_ready(ref_arrays)
    if isinstance(timeline_grid, dict) and "metadata" in timeline_grid and "song_data" in timeline_grid:
        precompute_timeline_gpu(timeline_grid, ref_arrays, song_slot=int(song_slot))
    else:
        raise TypeError("solve_genomes_with_ftff requires a calc_song dict with metadata and song_data")

    n_genomes = len(genome_stats_list)
    if n_genomes == 0:
        return []

    if n_genomes > MAX_GENOMES:
        raise ValueError(f"Too many genomes: {n_genomes} > {MAX_GENOMES}")

    # Upload per-genome stats
    # [pp, cm, fm, p_val, s_val, ft, ff]
    #
    # Avoid per-call allocations/zeroing on the CPU hot path by reusing a preallocated
    # buffer (we fully overwrite every column for the active slice).
    global _GENOME_STATS_BUFFER
    if _GENOME_STATS_BUFFER is None:
        _GENOME_STATS_BUFFER = np.empty((MAX_GENOMES, 7), dtype=np.int16)
    stats_buf = _GENOME_STATS_BUFFER[:n_genomes]

    # Fast path: if genome_stats_list is already a numpy array, use slice copy (182x faster)
    if isinstance(genome_stats_list, np.ndarray):
        stats_buf[:, :7] = genome_stats_list[:n_genomes, :7]
    else:
        # Slow path: unpack list of dicts
        for i, stats in enumerate(genome_stats_list):
            stats_buf[i, 0] = stats["base_pp"]
            stats_buf[i, 1] = stats["base_cm"]
            stats_buf[i, 2] = stats["base_fm"]
            stats_buf[i, 3] = stats["base_p_val"]
            stats_buf[i, 4] = stats["base_s_val"]
            stats_buf[i, 5] = stats["base_ft_stat"]
            stats_buf[i, 6] = stats["base_ff_stat"]

    if _profiler.enabled:
        _t_upload = time.perf_counter()
        fields.genome_base_stats.from_numpy(stats_buf)
        _profiler.record_upload(time.perf_counter() - _t_upload, bytes_count=int(getattr(stats_buf, "nbytes", 0) or 0))
        _maybe_sync(for_timing=True)
        _t_kernel = time.perf_counter()
    else:
        fields.genome_base_stats.from_numpy(stats_buf)
        _t_kernel = None

    # Launch kernel:
    # - Default: portable per-genome loop (correct across backends)
    # - Optional: Vulkan block-per-genome implementation (experimental; opt-in only)
    if bool(getattr(fields, "IS_METAL", False)) or not _USE_FTFF_BLOCK_KERNEL:
        kernels.solve_genomes_with_ftff_kernel(
            n_genomes,
            total_budget,
            gem_scale_fever,
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
            int(song_slot),
        )
    else:
        warn_fallback(
            "gpu.ftff.block_kernel",
            "using experimental Vulkan block FT/FF kernel (may be incorrect on some AMD/Vulkan drivers)",
            context={"env": "GPU_FTFF_BLOCK_KERNEL"},
        )
        n_combos = _ensure_ftff_combo_tables(int(total_budget))
        kernels.solve_genomes_with_ftff_block_kernel(
            n_genomes,
            int(n_combos),
            total_budget,
            gem_scale_fever,
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
            int(song_slot),
        )

    if _profiler.enabled and _SYNC_FOR_TIMING and _t_kernel is not None:
        _maybe_sync(for_timing=True)
        _profiler.record_kernel(time.perf_counter() - float(_t_kernel), genome_count=int(n_genomes))

    # Download results
    # [score, ft, ff, pp, cm, fm, ov]
    #
    # Vulkan `to_numpy()` transfers the full field shape. For FTFF, that would be
    # MAX_GENOMES=4096 rows every call, even when only ~250 genomes are active.
    # Use a bounded staging field + copy kernel when possible.
    _maybe_sync(for_timing=False)
    _t_download = time.perf_counter()
    results_np = None
    try:
        full_shape = getattr(fields.genome_result_stats, "shape", None)
        full_elems = int(full_shape[0]) * 7 if full_shape is not None else 0

        staging_candidates = [
            ("staging_256", fields.genome_result_stats_download_staging_256),
            ("staging_1024", fields.genome_result_stats_download_staging_1024),
        ]
        best = None
        for name, fld in staging_candidates:
            if fld is None:
                continue
            shape = getattr(fld, "shape", None)
            if not shape or len(shape) < 1:
                continue
            if n_genomes <= int(shape[0]):
                elems = int(shape[0]) * 7
                if best is None or elems < best[0]:
                    best = (elems, name, fld)

        if best is not None and full_elems > int(best[0]):
            _elems, _name, fld = best
            kernels.copy_genome_result_stats_to_download_staging_kernel(fld, int(n_genomes))
            results_np = fld.to_numpy()[:n_genomes]
    except Exception:
        results_np = None

    if results_np is None:
        results_np = fields.genome_result_stats.to_numpy()[:n_genomes]

    if _profiler.enabled:
        try:
            download_bytes = int(results_np.nbytes)
        except Exception:
            download_bytes = 0
        _profiler.record_download(time.perf_counter() - _t_download, bytes_count=download_bytes)

    return _results_from_stats(results_np, n_genomes)


def solve_genomes_from_registry(
    population_indices: np.ndarray,
    timeline_grid,
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
    total_budget: int = 90,
    gem_scale_fever: int = 3,
    song_slot: int = 0,
    use_exact_inner_solver: bool = True,
) -> list:
    """
    V3: GPU-RESIDENT stat aggregation path.

    Uses GPU-side stat aggregation instead of CPU-side, eliminating the
    56KB genome_base_stats upload per call.

    PREREQUISITES (must be called before this function):
    - ga_upload_item_stats() with registry.to_gpu_arrays()
    - ga_upload_base_fixed_stats() with base stats array

    This function:
    1. Uploads population_indices (once per call)
    2. Runs the GPU-native eval kernels (aggregate + FT/FF combo search)
    3. Materializes the best combo per genome

    Args:
        population_indices: (n_genomes, 9) int32 - encoded genome IDs from ItemRegistry
    timeline_grid: calc_song dict
        is_*: Color contribution flags (0/1)
        ref_arrays: Reference lookup arrays
        total_budget: Gem budget (default 90)
        gem_scale_fever: Stats per fever gem (default 3)
        song_slot: Grid slot for batch coalescing (0-7, default 0)

    Returns:
        List of (score, ft, ff, pp, cm, fm, ov) tuples per genome
    """
    ensure_ready(ref_arrays)

    # Upload timeline grid if needed
    if isinstance(timeline_grid, dict) and "metadata" in timeline_grid and "song_data" in timeline_grid:
        precompute_timeline_gpu(timeline_grid, ref_arrays, song_slot=song_slot)
    else:
        raise TypeError("solve_genomes_from_registry requires a calc_song dict with metadata and song_data")

    n_genomes = population_indices.shape[0]
    if n_genomes == 0:
        return []

    if n_genomes > MAX_GENOMES:
        raise ValueError(f"Too many genomes: {n_genomes} > {MAX_GENOMES}")

    # Upload population indices (only ~150KB vs building/uploading genome_stats)
    if _profiler.enabled:
        _t_upload = time.perf_counter()
        n_uploaded = int(ga_upload_population_indices(population_indices, n_slots=9) or 0)
        _maybe_sync(for_timing=True)
        _profiler.record_upload(
            time.perf_counter() - _t_upload,
            bytes_count=int(max(0, n_uploaded) * 9 * 4),
        )
        _t_kernel = time.perf_counter()
    else:
        ga_upload_population_indices(population_indices, n_slots=9)
        _t_kernel = None

    # GPU-native eval:
    # - Fused aggregate + best-key init
    # - Parallel (genome, ft/ff) combo search (chunked to limit kernel wall time)
    # - Materialize best allocations per genome (writes genome_result_stats)
    ga_evaluate_population(
        n_genomes,
        n_slots=9,
        total_budget=int(total_budget),
        gem_scale_fever=int(gem_scale_fever),
        song_slot=int(song_slot),
        is_p_ft=int(is_p_ft),
        is_s_ft=int(is_s_ft),
        is_p_ff=int(is_p_ff),
        is_s_ff=int(is_s_ff),
        is_p_pp=int(is_p_pp),
        is_s_pp=int(is_s_pp),
        is_p_cm=int(is_p_cm),
        is_s_cm=int(is_s_cm),
        is_p_fm=int(is_p_fm),
        is_s_fm=int(is_s_fm),
        is_p_ov=int(is_p_ov),
        is_s_ov=int(is_s_ov),
        use_exact_inner_solver=bool(use_exact_inner_solver),
        materialize_mode="results_only",
    )

    if _profiler.enabled and _SYNC_FOR_TIMING and _t_kernel is not None:
        _maybe_sync(for_timing=True)
        _profiler.record_kernel(time.perf_counter() - float(_t_kernel), genome_count=int(n_genomes))

    # Download only the active result prefix (uses staging field when available).
    _maybe_sync(for_timing=False)  # Single sync before download (respects sync policy)
    _t_download = time.perf_counter()
    results_np = ga_download_results(int(n_genomes))
    if _profiler.enabled:
        try:
            download_bytes = int(results_np.nbytes)
        except Exception:
            download_bytes = 0
        _profiler.record_download(time.perf_counter() - _t_download, bytes_count=download_bytes)

    return _results_from_stats(results_np, n_genomes)


# ============================================================================
# GPU-NATIVE GA OPERATORS (UNUSED - Future infrastructure)
# ============================================================================
# These functions implement GPU-side GA operators (selection, crossover, mutation)
# but are NOT currently wired into genetic.py. They exist as prep work for a
# future GPU-native GA where the entire population lives on GPU.
#
# To complete: need encoder (genome -> item_ids) and integration in genetic.py.
# ============================================================================
