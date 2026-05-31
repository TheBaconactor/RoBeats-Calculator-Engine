"""
API Parallel Solvers - Maximum parallelism genome solvers.

This module provides GPU genome solvers:
- solve_genomes_from_registry: GPU-resident stat aggregation + FT/FF combo search
"""

from __future__ import annotations

import numpy as np

from ..fields import MAX_GENOMES

from .initialization import (
    ensure_ready,
    _maybe_sync,
)
from .timeline import precompute_timeline_gpu
from .skyline_operations import (
    skyline_upload_population_indices,
    skyline_evaluate_population,
    skyline_download_scores,
    skyline_download_results,
)


def _results_from_stats(results_np: np.ndarray, n_genomes: int) -> list[tuple[int, int, int, int, int, int, int]]:
    n = max(0, int(n_genomes))
    if n <= 0:
        return []
    rows = np.asarray(results_np[:n, :7], dtype=np.int32)
    return [tuple(row) for row in rows.tolist()]


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
    max_ft_gems_global: int | None = None,
    max_ff_gems_global: int | None = None,
    timing_response_combo_ft: np.ndarray | None = None,
    timing_response_combo_ff: np.ndarray | None = None,
    timing_response_genome_offsets: np.ndarray | None = None,
    timing_response_genome_lengths: np.ndarray | None = None,
    timing_response_max_combos: int | None = None,
    timing_response_cache_key: object | None = None,
    score_cull_threshold: int | None = None,
    score_only: bool = False,
) -> list:
    """
    V3: GPU-RESIDENT stat aggregation path.

    Uses GPU-side stat aggregation instead of CPU-side, eliminating the
    56KB genome_base_stats upload per call.

    PREREQUISITES (must be called before this function):
    - skyline_upload_item_stats() with registry.to_gpu_arrays()
    - skyline_upload_base_fixed_stats() with base stats array

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

    skyline_upload_population_indices(population_indices, n_slots=9)

    # GPU-native eval:
    # - Fused aggregate + best-key init
    # - Parallel (genome, ft/ff) combo search (chunked to limit kernel wall time)
    # - Materialize best allocations per genome (writes genome_result_stats)
    skyline_evaluate_population(
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
        max_ft_gems_global=max_ft_gems_global,
        max_ff_gems_global=max_ff_gems_global,
        timing_response_combo_ft=timing_response_combo_ft,
        timing_response_combo_ff=timing_response_combo_ff,
        timing_response_genome_offsets=timing_response_genome_offsets,
        timing_response_genome_lengths=timing_response_genome_lengths,
        timing_response_max_combos=timing_response_max_combos,
        timing_response_cache_key=timing_response_cache_key,
        score_cull_threshold=score_cull_threshold,
        materialize_mode="scores_only" if bool(score_only) else "results_only",
    )

    if bool(score_only):
        _maybe_sync(for_timing=False)
        return skyline_download_scores(int(n_genomes))

    # Download only the active result prefix (uses staging field when available).
    _maybe_sync(for_timing=False)  # Single sync before download (respects sync policy)
    results_np = skyline_download_results(int(n_genomes))

    return _results_from_stats(results_np, n_genomes)
