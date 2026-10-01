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

import logging

import numpy as np

from .. import fields
from ..fields import MAX_EVALS_PER_DISPATCH
from ..combo_chunking import compute_combo_chunk
from ..kernel_loader import get_kernels

from .initialization import (
    ensure_ready,
    _ensure_ftff_combo_tables,
    _ensure_timing_response_combo_tables,
    _upload_timing_response_genome_rows,
)

logger = logging.getLogger(__name__)

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
    try:
        kernels.skyline_copy_population_indices_from_ndarray_kernel(int(n_genomes), int(n_slots), src)
    except Exception as e:
        logger.debug(f"skyline_operations:skyline_upload_population_indices: {e}")
        pop_buf = np.zeros((fields.MAX_GENOMES, fields.MAX_SLOTS), dtype=np.int32)
        pop_buf[:n_genomes, : int(n_slots)] = src
        fields.population_indices.from_numpy(pop_buf)
    return n_genomes


def skyline_upload_item_stats(
    item_stats_np: np.ndarray, slot_start_np: np.ndarray, slot_count_np: np.ndarray,
) -> int:
    from .registry_upload import upload_item_stats
    return upload_item_stats(item_stats_np, slot_start_np, slot_count_np)


def skyline_upload_base_fixed_stats(base_stats_np: np.ndarray) -> None:
    from .registry_upload import upload_base_fixed_stats
    upload_base_fixed_stats(base_stats_np)


def skyline_evaluate_population(
    n_genomes: int,
    n_slots: int = 9,
    *,
    total_budget: int,
    gem_scale_fever: int = 3,
    song_slot: int = 0,
    is_p_ft: int = 0,
    is_s_ft: int = 0,
    is_p_ff: int = 0,
    is_s_ff: int = 0,
    is_p_pp: int = 0,
    is_s_pp: int = 0,
    is_p_cm: int = 0,
    is_s_cm: int = 0,
    is_p_fm: int = 0,
    is_s_fm: int = 0,
    is_p_ov: int = 0,
    is_s_ov: int = 0,
    max_ft_gems_global: int | None = None,
    max_ff_gems_global: int | None = None,
    timing_response_combo_ft: np.ndarray | None = None,
    timing_response_combo_ff: np.ndarray | None = None,
    timing_response_genome_offsets: np.ndarray | None = None,
    timing_response_genome_lengths: np.ndarray | None = None,
    timing_response_max_combos: int | None = None,
    timing_response_cache_key: object | None = None,
    score_cull_threshold: int | None = None,
    materialize_mode: str = "none",
) -> None:
    """
    GPU-native population evaluation: aggregate stats + evaluate + materialize.

    This is the main skyline evaluation function for GPU-native mode. It:
    1. Aggregates item stats and initializes each genome's best key (skyline_aggregate_and_init_best_kernel)
    2. Searches all (ft, ff) combos in chunks (skyline_find_best_combo_warmstart_kernel)
    3. Writes scores ("scores_only") or full results ("results_only"), or nothing ("none")

    PREREQUISITES:
    - Call skyline_upload_population_indices() with encoded population
    - Call skyline_upload_item_stats() with item stats and slot pools
    - Call skyline_upload_base_fixed_stats() with base stats
    - Precompute the exact timeline frontier using precompute_timeline_gpu()

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

    kernels.skyline_aggregate_and_init_best_kernel(
        n_genomes,
        n_slots,
        int(is_p_ft),
        int(is_s_ft),
        int(is_p_ff),
        int(is_s_ff),
        int(is_p_pp),
        int(is_s_pp),
        int(is_p_cm),
        int(is_s_cm),
        int(is_p_fm),
        int(is_s_fm),
        int(is_p_ov),
        int(is_s_ov),
        0,
    )

    # Step 2: Evaluate genomes using existing FT/FF iteration kernel
    total_budget_i = int(total_budget)
    gem_scale_fever_i = int(gem_scale_fever)
    song_slot_i = int(song_slot)
    score_cull_threshold_i = -1 if score_cull_threshold is None else int(score_cull_threshold)

    use_timing_response_antichain = (
        timing_response_combo_ft is not None
        and timing_response_combo_ff is not None
        and timing_response_genome_offsets is not None
        and timing_response_genome_lengths is not None
        and timing_response_max_combos is not None
    )
    if use_timing_response_antichain and materialize_mode != "scores_only":
        raise ValueError("timing response antichain is score-only; materialize retained candidates with the full table")

    # Precompute FT/FF combo tables once per budget (tiny upload, reused across generations).
    max_ft_gems_i = int(total_budget_i) if max_ft_gems_global is None else int(max_ft_gems_global)
    max_ff_gems_i = int(total_budget_i) if max_ff_gems_global is None else int(max_ff_gems_global)
    max_ft_gems_i = max(0, min(int(total_budget_i), int(max_ft_gems_i)))
    max_ff_gems_i = max(0, min(int(total_budget_i), int(max_ff_gems_i)))
    if use_timing_response_antichain:
        _ensure_timing_response_combo_tables(
            combo_ft=np.asarray(timing_response_combo_ft, dtype=np.int32),
            combo_ff=np.asarray(timing_response_combo_ff, dtype=np.int32),
            cache_key=timing_response_cache_key,
        )
        _upload_timing_response_genome_rows(
            genome_offsets=np.asarray(timing_response_genome_offsets, dtype=np.int32),
            genome_lengths=np.asarray(timing_response_genome_lengths, dtype=np.int32),
            n_genomes=int(n_genomes),
        )
        n_combos = int(timing_response_max_combos or 0)
        if n_combos <= 0:
            raise ValueError("timing response antichain max combo count must be positive")
    else:
        n_combos = _ensure_ftff_combo_tables(
            total_budget_i,
            max_ft_gems=max_ft_gems_i,
            max_ff_gems=max_ff_gems_i,
        )
    eval_budget = int(MAX_EVALS_PER_DISPATCH)
    max_evals = max(int(eval_budget), int(n_genomes))
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
        if _SKYLINE_COMBO_TAIL_MERGE_MAX > 0:
            rem = int(n_combos - (offset + chunk_len))
            if 0 < rem <= int(_SKYLINE_COMBO_TAIL_MERGE_MAX):
                merged = int(chunk_len + rem)
                if int(n_genomes) * int(merged) <= int(max_evals):
                    chunk_len = merged
        kernels.skyline_find_best_combo_warmstart_kernel(
            n_genomes,
            n_combos,
            int(offset),
            int(chunk_len),
            total_budget_i,
            gem_scale_fever_i,
            int(is_p_ft),
            int(is_s_ft),
            int(is_p_ff),
            int(is_s_ff),
            int(is_p_pp),
            int(is_s_pp),
            int(is_p_cm),
            int(is_s_cm),
            int(is_p_fm),
            int(is_s_fm),
            int(is_p_ov),
            int(is_s_ov),
            song_slot_i,
            0,
            int(bool(use_timing_response_antichain)),
            int(score_cull_threshold_i),
        )
        offset += int(chunk_len)

    _skyline_materialize_population_results(
        n_genomes=n_genomes,
        total_budget=total_budget_i,
        gem_scale_fever=gem_scale_fever_i,
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
        song_slot=song_slot_i,
        materialize_mode=materialize_mode,
    )


def _skyline_materialize_population_results(
    *,
    n_genomes: int,
    total_budget: int,
    gem_scale_fever: int,
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
    song_slot: int,
    materialize_mode: str,
) -> None:
    if materialize_mode == "none":
        return

    if materialize_mode == "scores_only":
        kernels.skyline_write_scores_from_key_kernel(int(n_genomes))
        return

    common_args = (
        int(n_genomes),
        int(total_budget),
        int(gem_scale_fever),
        int(is_p_ft),
        int(is_s_ft),
        int(is_p_ff),
        int(is_s_ff),
        int(is_p_pp),
        int(is_s_pp),
        int(is_p_cm),
        int(is_s_cm),
        int(is_p_fm),
        int(is_s_fm),
        int(is_p_ov),
        int(is_s_ov),
        int(song_slot),
    )

    if materialize_mode == "results_only":
        kernels.skyline_write_best_results_from_key_kernel(*common_args)
        return

    raise ValueError(f"Unknown skyline materialize_mode: {materialize_mode!r}")


def skyline_download_scores(n_genomes: int) -> np.ndarray:
    """
    Download fitness scores from GPU (for CPU-side elitism).

    Args:
        n_genomes: Number of genomes to download

    Returns:
        np.ndarray: (n_genomes,) int32 array of scores
    """
    ensure_ready()
    n_genomes = int(n_genomes)
    out = fields.skyline_scores.to_numpy()
    return np.asarray(out[:n_genomes], dtype=np.int32)


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
