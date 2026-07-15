"""
API Parallel Solvers - exact loadout batch solving.

This module provides ``solve_loadouts_from_registry`` for GPU-resident stat
aggregation and exact FT/FF combo search.
"""

from __future__ import annotations

import numpy as np

from ..fields import MAX_LOADOUTS

from .initialization import (
    ensure_ready,
    _maybe_sync,
)
from .timeline import precompute_timeline_gpu
from .skyline_operations import (
    skyline_upload_loadout_indices,
    skyline_evaluate_loadouts,
    skyline_download_scores,
    skyline_download_results,
)


def _results_from_stats(results_np: np.ndarray, n_loadouts: int) -> list[tuple[int, int, int, int, int, int, int]]:
    n = max(0, int(n_loadouts))
    if n <= 0:
        return []
    rows = np.asarray(results_np[:n, :7], dtype=np.int32)
    return [tuple(row) for row in rows.tolist()]


def solve_loadouts_from_registry(
    loadout_indices: np.ndarray,
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
    score_only: bool = False,
) -> list:
    """
    GPU-resident exact stat aggregation and gem allocation.

    PREREQUISITES (must be called before this function):
    - skyline_upload_item_stats() with registry.to_gpu_arrays()
    - skyline_upload_base_fixed_stats() with base stats array

    This function:
    1. Uploads loadout_indices (once per call)
    2. Runs the GPU-native eval kernels (aggregate + FT/FF combo search)
    3. Materializes the best combo per loadout

    Args:
        loadout_indices: (n_loadouts, 9) int32 - encoded loadout IDs from ItemRegistry
    timeline_grid: calc_song dict
        is_*: Color contribution flags (0/1)
        ref_arrays: Reference lookup arrays
        total_budget: Gem budget (default 90)
        gem_scale_fever: Stats per fever gem (default 3)
        song_slot: Grid slot for batch coalescing (0-7, default 0)

    Returns:
        List of (score, ft, ff, pp, cm, fm, ov) tuples per loadout
    """
    ensure_ready(ref_arrays)

    # Upload timeline grid if needed
    if isinstance(timeline_grid, dict) and "metadata" in timeline_grid and "song_data" in timeline_grid:
        precompute_timeline_gpu(timeline_grid, ref_arrays, song_slot=song_slot)
    else:
        raise TypeError("solve_loadouts_from_registry requires a calc_song dict with metadata and song_data")

    n_loadouts = loadout_indices.shape[0]
    if n_loadouts == 0:
        return []

    if n_loadouts > MAX_LOADOUTS:
        raise ValueError(f"Too many loadouts: {n_loadouts} > {MAX_LOADOUTS}")

    skyline_upload_loadout_indices(loadout_indices, n_slots=9)

    # GPU-native eval:
    # - Fused aggregate + best-key init
    # - Parallel (loadout, ft/ff) combo search (chunked to limit kernel wall time)
    # - Materialize best allocations per loadout
    skyline_evaluate_loadouts(
        n_loadouts,
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
        materialize_mode="scores" if bool(score_only) else "results",
    )

    if bool(score_only):
        _maybe_sync(for_timing=False)
        return skyline_download_scores(int(n_loadouts))

    # Download only the active result prefix (uses staging field when available).
    _maybe_sync(for_timing=False)  # Single sync before download (respects sync policy)
    results_np = skyline_download_results(int(n_loadouts))

    return _results_from_stats(results_np, n_loadouts)
