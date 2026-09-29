"""
API skyline Operations - GPU-native Skyline candidate evaluation.

This module provides the GPU-side skyline evaluation operators:
- skyline_upload_population_indices: Upload integer-encoded population to GPU
- skyline_generate_initial_populations / skyline_load_initial_population: Stage populations on GPU
- skyline_upload_item_stats: Upload item stats and slot pools
- skyline_upload_base_fixed_stats: Upload fixed base stats
- skyline_aggregate_stats: Aggregate item stats into genome stats on GPU
- skyline_evaluate_population: Full GPU-native evaluation pipeline
- skyline_download_*: Download results from GPU

These functions are called from parallel_solvers.py and tests.
"""

from __future__ import annotations

import logging

import numpy as np

from .. import fields
from ..fields import MAX_EVALS_PER_DISPATCH
from ..skyline_chunking import compute_skyline_combo_chunk
from ..kernel_loader import get_kernels

from .common_operations import probability_to_u32_fp
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


def skyline_load_initial_population(*, run_idx: int, n_genomes: int, n_slots: int = 9) -> None:
    """
    Load a staged initial population (run_idx) into the active skyline `population_indices`.
    """
    ensure_ready()
    run_idx = int(run_idx)
    n_genomes = int(n_genomes)
    n_slots = int(n_slots)
    if run_idx < 0 or run_idx >= fields.MAX_SKYLINE_RUNS:
        raise ValueError(f"run_idx out of range: {run_idx} (MAX_SKYLINE_RUNS={fields.MAX_SKYLINE_RUNS})")
    if n_genomes < 0 or n_genomes > fields.MAX_SKYLINE_RUN_GENOMES:
        raise ValueError(f"Too many genomes: {n_genomes} > {fields.MAX_SKYLINE_RUN_GENOMES}")
    kernels.skyline_load_initial_population_kernel(run_idx, n_genomes, n_slots)


def skyline_generate_initial_populations(
    *,
    run_idx_start: int,
    n_runs: int,
    n_genomes: int,
    n_slots: int = 9,
    seed: int = 12345,
    heuristic_prob: float = 0.0,
    heuristic_k: int = 0,
    seed_prob: float = 0.0,
    seed_copies: int = 0,
    seed_mutations: int = 0,
    heuristic_copies: int = 0,
    seed_ids: np.ndarray | None = None,
) -> None:
    """
    Generate initial populations on the GPU into `fields.skyline_initial_populations`.

    This replaces the CPU-side build+encode+upload loop for multi-start runs.
    """
    ensure_ready()
    run_idx_start = int(run_idx_start)
    n_runs = int(n_runs)
    n_genomes = int(n_genomes)
    n_slots = int(n_slots)
    if n_runs <= 0 or n_genomes <= 0:
        return
    if run_idx_start < 0 or run_idx_start >= fields.MAX_SKYLINE_RUNS:
        raise ValueError(f"run_idx_start out of range: {run_idx_start} (MAX_SKYLINE_RUNS={fields.MAX_SKYLINE_RUNS})")
    if run_idx_start + n_runs > fields.MAX_SKYLINE_RUNS:
        raise ValueError(
            f"batch runs out of range: start={run_idx_start}, n_runs={n_runs} (MAX_SKYLINE_RUNS={fields.MAX_SKYLINE_RUNS})"
        )
    if n_genomes < 0 or n_genomes > fields.MAX_SKYLINE_RUN_GENOMES:
        raise ValueError(f"Too many genomes: {n_genomes} > {fields.MAX_SKYLINE_RUN_GENOMES}")
    if n_slots > fields.MAX_SLOTS:
        raise ValueError(f"Too many slots: {n_slots} > {fields.MAX_SLOTS}")

    heuristic_prob = float(heuristic_prob)
    heuristic_prob = max(0.0, min(1.0, heuristic_prob))
    seed_prob = float(seed_prob)
    seed_prob = max(0.0, min(1.0, seed_prob))

    heuristic_prob_fp = probability_to_u32_fp(heuristic_prob)
    seed_prob_fp = probability_to_u32_fp(seed_prob)

    heuristic_k = int(heuristic_k)
    if heuristic_k < 0:
        heuristic_k = 0
    # Clamp to actual allocated field K.
    k_field = int(getattr(fields, "SKYLINE_INIT_HEURISTIC_K", heuristic_k) or 0)
    if k_field <= 0:
        heuristic_k = 0
    else:
        heuristic_k = min(int(heuristic_k), int(k_field))

    seed_copies = int(seed_copies)
    seed_copies = max(0, min(seed_copies, n_genomes))
    seed_mutations = int(seed_mutations)
    seed_mutations = max(0, min(seed_mutations, n_genomes))
    heuristic_copies = int(heuristic_copies)
    heuristic_copies = max(0, min(heuristic_copies, n_genomes))

    if seed_ids is None:
        seed_ids_arr = np.zeros((n_slots,), dtype=np.int32)
    else:
        seed_ids_arr = np.asarray(seed_ids, dtype=np.int32).reshape(-1)
        if seed_ids_arr.shape[0] < n_slots:
            raise ValueError(f"seed_ids has too few entries: {seed_ids_arr.shape[0]} < {n_slots}")
        seed_ids_arr = seed_ids_arr[:n_slots]

    kernels.skyline_generate_initial_populations_kernel(
        int(run_idx_start),
        int(n_runs),
        int(n_genomes),
        int(n_slots),
        np.uint32(int(seed) & 0xFFFFFFFF),
        heuristic_prob_fp,
        int(heuristic_k),
        seed_prob_fp,
        int(seed_copies),
        int(seed_mutations),
        int(heuristic_copies),
        seed_ids_arr,
    )


def skyline_upload_item_stats(
    item_stats_np: np.ndarray, slot_start_np: np.ndarray, slot_count_np: np.ndarray,
) -> int:
    from .registry_upload import upload_item_stats
    return upload_item_stats(item_stats_np, slot_start_np, slot_count_np)


def skyline_upload_base_fixed_stats(base_stats_np: np.ndarray) -> None:
    from .registry_upload import upload_base_fixed_stats
    upload_base_fixed_stats(base_stats_np)


def skyline_upload_fg_effective_tables(gear_name_rank_np: np.ndarray, mini_sig_id_np: np.ndarray) -> None:
    """
    Upload the skyline GA->FG effective-dedup equivalence tables (Slice 1 mirror).

    Mirrors ga_upload_fg_effective_tables; the skyline fields alias the GA fields
    (fields.skyline_fg_gear_name_rank is fields.ga_fg_gear_name_rank), so this
    writes the same device tables the skyline select kernel reads. Kept in lockstep
    with the GA upload so the skyline select kernel never reads an unbound table.
    """
    ensure_ready()
    rank_src = np.asarray(gear_name_rank_np, dtype=np.int32).reshape(-1)
    sig_src = np.asarray(mini_sig_id_np, dtype=np.int32).reshape(-1)
    if int(rank_src.shape[0]) > int(fields.MAX_ITEMS):
        raise ValueError(
            f"gear_name_rank too large: {rank_src.shape[0]} > MAX_ITEMS={fields.MAX_ITEMS}"
        )
    if int(sig_src.shape[0]) > int(fields.MAX_ITEMS):
        raise ValueError(
            f"mini_sig_id too large: {sig_src.shape[0]} > MAX_ITEMS={fields.MAX_ITEMS}"
        )
    rank_buf = np.zeros(int(fields.MAX_ITEMS), dtype=np.int32)
    sig_buf = np.zeros(int(fields.MAX_ITEMS), dtype=np.int32)
    rank_buf[: rank_src.shape[0]] = rank_src
    sig_buf[: sig_src.shape[0]] = sig_src
    fields.skyline_fg_gear_name_rank.from_numpy(rank_buf)
    fields.skyline_fg_mini_sig_id.from_numpy(sig_buf)


def skyline_aggregate_stats(
    n_genomes: int,
    n_slots: int = 9,
    *,
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
) -> None:
    """
    Aggregate item stats into genome_base_stats on GPU.

    For each genome, sums base_fixed_stats + item_stats[population_indices[g, s]]
    across all slots, then computes p_val/s_val from color flags.

    PREREQUISITES:
    - Call skyline_upload_population_indices() first
    - Call skyline_upload_item_stats() first
    - Call skyline_upload_base_fixed_stats() first

    Args:
        n_genomes: Number of genomes to aggregate
        n_slots: Number of slots per genome (default 9)
        is_p_*: Primary color contribution flags (0 or 1)
        is_s_*: Secondary color contribution flags (0 or 1)
    """
    ensure_ready()
    kernels.skyline_aggregate_genome_stats_kernel(
        int(n_genomes),
        int(n_slots),
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
    )


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
    use_exact_inner_solver_i = int(bool(use_exact_inner_solver))
    if use_exact_inner_solver_i == 0:
        raise ValueError("Skyline evaluation requires exact inner GPU solving.")

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
    combo_chunk = compute_skyline_combo_chunk(
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
            use_exact_inner_solver_i,
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
        use_exact_inner_solver=bool(use_exact_inner_solver_i),
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
    use_exact_inner_solver: bool,
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
        int(bool(use_exact_inner_solver)),
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
    try:
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
    except Exception as e:
        logger.debug(f"skyline_operations:skyline_download_results: {e}")
        results_np = None

    if results_np is None:
        out = fields.genome_result_stats.to_numpy()
        results_np = out[:n_genomes]
    return np.asarray(results_np, dtype=np.int32)
