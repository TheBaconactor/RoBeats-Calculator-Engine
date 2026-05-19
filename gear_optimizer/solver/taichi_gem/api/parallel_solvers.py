"""
GPU genome solver API.

The public optimizer route is the registry solver: GPU-side stat aggregation,
exhaustive FT/FF combo search, and exact bounded PP/CM/FM/overflow allocation.
"""

from __future__ import annotations

import logging
import time

import numpy as np

from gear_optimizer.solver.gpu_profiler import get_gpu_profiler

from ..fields import MAX_GENOMES
from .ga_operations import (
    ga_download_results,
    ga_evaluate_population,
    ga_upload_base_candidate_cache,
    ga_upload_population_indices,
)
from .initialization import _SYNC_FOR_TIMING, _maybe_sync, ensure_ready
from .timeline import precompute_timeline_gpu

logger = logging.getLogger(__name__)
_profiler = get_gpu_profiler()


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
) -> list[tuple[int, int, int, int, int, int, int]]:
    """
    GPU-resident stat aggregation plus FT/FF combo search.

    Returns one tuple per genome:
      (score, ft_gems, ff_gems, pp_gems, cm_gems, fm_gems, overflow_gems)
    """
    ensure_ready(ref_arrays)

    if isinstance(timeline_grid, dict) and "metadata" in timeline_grid and "song_data" in timeline_grid:
        precompute_timeline_gpu(timeline_grid, ref_arrays, song_slot=song_slot)
    else:
        raise TypeError("solve_genomes_from_registry requires a calc_song dict with metadata and song_data")

    n_genomes = int(population_indices.shape[0])
    if n_genomes == 0:
        return []
    if n_genomes > MAX_GENOMES:
        raise ValueError(f"Too many genomes: {n_genomes} > {MAX_GENOMES}")

    if _profiler.enabled:
        t_upload = time.perf_counter()
        n_uploaded = int(ga_upload_population_indices(population_indices, n_slots=9) or 0)
        _maybe_sync(for_timing=True)
        _profiler.record_upload(
            time.perf_counter() - t_upload,
            bytes_count=int(max(0, n_uploaded) * 9 * 4),
        )
        t_kernel = time.perf_counter()
    else:
        ga_upload_population_indices(population_indices, n_slots=9)
        t_kernel = None

    ga_upload_base_candidate_cache(
        np.zeros((0,), dtype=np.uint32),
        np.zeros((0, 7), dtype=np.int16),
        np.zeros((0, 6), dtype=np.int32),
    )

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

    if _profiler.enabled and _SYNC_FOR_TIMING and t_kernel is not None:
        _maybe_sync(for_timing=True)
        _profiler.record_kernel(time.perf_counter() - float(t_kernel), genome_count=int(n_genomes))

    _maybe_sync(for_timing=False)
    t_download = time.perf_counter()
    results_np = ga_download_results(int(n_genomes))
    if _profiler.enabled:
        try:
            download_bytes = int(results_np.nbytes)
        except Exception as e:
            logger.debug(f"parallel_solvers:solve_genomes_from_registry: {e}")
            download_bytes = 0
        _profiler.record_download(time.perf_counter() - t_download, bytes_count=download_bytes)

    return _results_from_stats(results_np, n_genomes)
