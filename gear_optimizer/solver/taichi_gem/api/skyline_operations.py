"""
API skyline Operations - GPU-native Skyline candidate evaluation.

This module provides the GPU-side skyline evaluation operators:
- skyline_upload_population_indices: Upload integer-encoded population to GPU
- skyline_upload_item_stats: Upload item stats and slot pools
- skyline_upload_base_fixed_stats: Upload fixed base stats
- skyline_evaluate_population: Full GPU-native evaluation pipeline
- skyline_download_*: Download results from GPU

These functions are called from parallel_solvers.py and tests.
"""

from __future__ import annotations


import numpy as np

from .. import fields
from ..fields import MAX_EVALS_PER_DISPATCH
from ..combo_chunking import compute_combo_chunk
from ..kernel_loader import get_kernels

from gear_optimizer.rules import GEM_BUDGET, STAT_GEM_GAIN_FEVER

from .initialization import _ensure_ftff_combo_tables, ensure_ready


_SKYLINE_COMBO_CHUNK_MIN = 1024
_SKYLINE_COMBO_CHUNK_MAX = 4096

# Merge a tiny remainder into the prior dispatch when it is safe under the max-evals budget.
# This can reduce dispatch count when chunking would otherwise leave a very small "tail" kernel and the
# per-dispatch budget still has slack (e.g. when chunking is capped by `chunk_max` rather than the
# `max_evals` target).
_SKYLINE_COMBO_TAIL_MERGE_MAX = 256


# Get appropriate kernels for current platform (Metal-safe on macOS)
kernels = get_kernels()


# ============================================================================
# GPU-NATIVE skyline OPERATORS
# ============================================================================
# These functions implement GPU-side skyline evaluation (upload, aggregate, evaluate,
# download). They are called from parallel_solvers.py and tests.
# ============================================================================


def skyline_upload_population_indices(population_indices_np: np.ndarray, *, n_slots: int = 9) -> int:
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

    src = np.ascontiguousarray(population_indices_np[:n_genomes, : int(n_slots)], dtype=np.int32)
    kernels.skyline_copy_population_indices_from_ndarray_kernel(int(n_genomes), int(n_slots), src)
    return n_genomes


def skyline_upload_item_stats(
    item_stats_np: np.ndarray, slot_start_np: np.ndarray, slot_count_np: np.ndarray,
) -> int:
    from .registry_upload import upload_item_stats
    return upload_item_stats(item_stats_np, slot_start_np, slot_count_np)


def skyline_upload_base_fixed_stats(base_stats_np: np.ndarray) -> None:
    from .registry_upload import upload_base_fixed_stats
    upload_base_fixed_stats(base_stats_np)


def skyline_evaluate_population(n_genomes: int, n_slots: int = 9, *, song_slot: int = 0, flags) -> None:
    """Aggregate the genomes' stats, search every FT/FF combo of the full gem budget in chunks, and write each
    genome's best allocation to genome_result_stats. Needs the population, item stats, base stats and the song's
    exact timeline frontier uploaded first."""
    ensure_ready()
    n_genomes = int(n_genomes)
    kernels.skyline_aggregate_and_init_best_kernel(n_genomes, int(n_slots), flags)
    n_combos = _ensure_ftff_combo_tables(GEM_BUDGET, max_ft_gems=GEM_BUDGET, max_ff_gems=GEM_BUDGET)
    max_evals = max(int(MAX_EVALS_PER_DISPATCH), n_genomes)
    combo_chunk = compute_combo_chunk(
        n_genomes=n_genomes,
        n_combos=n_combos,
        max_evals=max_evals,
        chunk_min=_SKYLINE_COMBO_CHUNK_MIN,
        chunk_max=_SKYLINE_COMBO_CHUNK_MAX,
    )
    if combo_chunk <= 0:
        combo_chunk = int(n_combos)
    offset = 0
    while offset < n_combos:
        chunk_len = int(min(combo_chunk, n_combos - offset))
        # If the remainder is tiny, fold it into this dispatch to avoid a "tail kernel" launch.
        rem = int(n_combos - (offset + chunk_len))
        if 0 < rem <= _SKYLINE_COMBO_TAIL_MERGE_MAX and n_genomes * (chunk_len + rem) <= max_evals:
            chunk_len += rem
        kernels.skyline_find_best_combo_warmstart_kernel(
            n_genomes, int(offset), chunk_len, GEM_BUDGET, STAT_GEM_GAIN_FEVER, flags, int(song_slot)
        )
        offset += chunk_len
    kernels.skyline_write_best_results_from_key_kernel(n_genomes, GEM_BUDGET, STAT_GEM_GAIN_FEVER, flags, int(song_slot))


def skyline_download_results(n_genomes: int) -> np.ndarray:
    """
    Download full evaluation results from GPU.

    Args:
        n_genomes: Number of genomes to download

    Returns:
        np.ndarray: (n_genomes, 7) int32 array [score, ft, ff, pp, cm, fm, ov]
    """
    ensure_ready()
    n_genomes = int(n_genomes)
    if n_genomes <= 0:
        return np.empty((0, 7), dtype=np.int32)

    results_np = None
    full_shape = getattr(fields.genome_result_stats, "shape", None)
    full_elems = int(full_shape[0]) * 7 if full_shape is not None else 0

    staging_candidates = [
        fields.genome_result_stats_download_staging_256,
        fields.genome_result_stats_download_staging_1024,
    ]
    best = None
    for fld in staging_candidates:
        if fld is None:
            continue
        shape = getattr(fld, "shape", None)
        if not shape or len(shape) < 1:
            continue
        if n_genomes <= int(shape[0]):
            elems = int(shape[0]) * 7
            if best is None or elems < best[0]:
                best = (elems, fld)

    if best is not None and full_elems > int(best[0]):
        _elems, staging_fld = best
        kernels.copy_genome_result_stats_to_download_staging_kernel(staging_fld, n_genomes)
        results_np = staging_fld.to_numpy()[:n_genomes]

    if results_np is None:
        out = fields.genome_result_stats.to_numpy()
        results_np = out[:n_genomes]
    return np.asarray(results_np, dtype=np.int32)
