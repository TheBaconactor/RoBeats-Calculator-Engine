"""
API Parallel Solvers - Maximum parallelism genome solvers.

This module provides GPU genome solvers:
- solve_genomes_from_registry: GPU-resident stat aggregation + FT/FF combo search
"""

from __future__ import annotations

import numpy as np

from gear_optimizer.gamedata import StatCurves
from ..fields import MAX_GENOMES

from .initialization import ensure_ready
from .timeline import precompute_timeline_gpu
from gear_optimizer.solver.timing_envelope import TimedSong
from .skyline_operations import (
    skyline_upload_population_indices,
    skyline_evaluate_population,
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
    song: TimedSong,
    flags,
    curves: StatCurves,
    song_slot: int = 0,
) -> list:
    """Each genome's best gem allocation over the full gem budget, as (score, ft, ff, pp, cm, fm, ov).

    Needs skyline_upload_item_stats() and skyline_upload_base_fixed_stats() first; aggregates the genomes' stats on
    the GPU, searches every FT/FF combo, and materializes each genome's best combo."""
    ensure_ready(curves)
    precompute_timeline_gpu(song, curves, song_slot=song_slot)
    n_genomes = population_indices.shape[0]
    if n_genomes == 0:
        return []
    if n_genomes > MAX_GENOMES:
        raise ValueError(f"Too many genomes: {n_genomes} > {MAX_GENOMES}")
    skyline_upload_population_indices(population_indices, n_slots=9)
    skyline_evaluate_population(n_genomes, n_slots=9, song_slot=int(song_slot), flags=flags)
    return _results_from_stats(skyline_download_results(int(n_genomes)), n_genomes)
