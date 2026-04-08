"""
API GA Operations - GPU-native genetic algorithm operators.

This module provides GPU-side GA operators (selection, crossover, mutation, evaluation):
- ga_upload_population_indices: Upload integer-encoded population to GPU
- ga_seed_rng: Seed per-genome RNG state
- ga_upload_item_stats: Upload item stats and slot pools
- ga_upload_base_fixed_stats: Upload fixed base stats
- ga_aggregate_stats: Aggregate item stats into genome stats on GPU
- ga_evaluate_population: Full GPU-native evaluation pipeline
- ga_set_scores: Manually set scores for custom evaluation
- ga_next_generation: Tournament selection + crossover + mutation + elitism
- ga_download_*: Download results from GPU

These functions are prep work for future GPU-native GA where the entire
population lives on GPU, avoiding CPU-GPU transfers during evolution.
"""

from __future__ import annotations

import os
import time

import numpy as np

from .. import fields
from ..fields import MAX_EVALS_PER_DISPATCH
from ..ga_chunking import compute_ga_combo_chunk
from ..kernel_loader import get_kernels

from .initialization import ensure_ready, _ensure_ftff_combo_tables

# Cache environment variables at module load time to avoid per-call overhead.
#
# Note: plateau pruning is currently correctness-risky (it can prune away valid
# FT/FF combos that produce better top-1 results). Keep it OFF by default and
# allow explicit opt-in for profiling/experimentation.
_GA_PLATEAU_PRUNE_ENABLED: int = 0
_raw = str(os.environ.get("GPU_NATIVE_GA_PLATEAU_PRUNE", "0") or "").strip().lower()
if _raw in {"1", "true", "yes", "on"}:
    _GA_PLATEAU_PRUNE_ENABLED = 1
del _raw

_GA_COMBO_CHUNK_MIN: int = max(64, int(os.environ.get("GPU_NATIVE_GA_COMBO_CHUNK_MIN", "1024") or 1024))
_GA_COMBO_CHUNK_MAX: int = max(
    _GA_COMBO_CHUNK_MIN, int(os.environ.get("GPU_NATIVE_GA_COMBO_CHUNK_MAX", "4096") or 4096)
)

# Merge a tiny remainder into the prior dispatch when it is safe under the max-evals budget.
# This can reduce dispatch count when chunking would otherwise leave a very small "tail" kernel and the
# per-dispatch budget still has slack (e.g. when chunking is capped by `chunk_max` rather than the
# `max_evals` target).
_GA_COMBO_TAIL_MERGE_MAX: int = max(0, int(os.environ.get("GPU_NATIVE_GA_COMBO_TAIL_MERGE_MAX", "256") or 256))

# Evaluation budget for GA combo-search chunking (<= MAX_EVALS_PER_DISPATCH).
#
# Note: this is read lazily (with light caching) instead of at module import time so
# in-flight schedulers can apply env defaults before the first GA dispatch.
_GA_EVAL_BUDGET_RAW: str | None = None
_GA_EVAL_BUDGET: int = int(MAX_EVALS_PER_DISPATCH)
_GA_BASE_STATS_REUSE_RAW: str | None = None
_GA_BASE_STATS_REUSE_ENABLED: int = 0
_GA_EXACT_EVAL_RESULTS_REUSE_RAW: str | None = None
_GA_EXACT_EVAL_RESULTS_REUSE_ENABLED: int = 0


def _ga_eval_budget() -> int:
    global _GA_EVAL_BUDGET_RAW, _GA_EVAL_BUDGET
    raw = os.environ.get("GPU_NATIVE_GA_EVAL_BUDGET", None)
    raw_norm = str(raw or "").strip()
    if raw_norm == _GA_EVAL_BUDGET_RAW:
        return int(_GA_EVAL_BUDGET)

    _GA_EVAL_BUDGET_RAW = raw_norm
    if raw_norm == "":
        _GA_EVAL_BUDGET = int(MAX_EVALS_PER_DISPATCH)
        return int(_GA_EVAL_BUDGET)

    try:
        val = int(raw_norm)
    except Exception:
        _GA_EVAL_BUDGET = int(MAX_EVALS_PER_DISPATCH)
        return int(_GA_EVAL_BUDGET)

    _GA_EVAL_BUDGET = max(64, min(int(MAX_EVALS_PER_DISPATCH), int(val)))
    return int(_GA_EVAL_BUDGET)


def _ga_exact_genome_base_stats_reuse_enabled() -> int:
    global _GA_BASE_STATS_REUSE_RAW, _GA_BASE_STATS_REUSE_ENABLED
    raw = os.environ.get("GPU_NATIVE_GA_BASE_STATS_REUSE", None)
    raw_norm = str(raw or "").strip().lower()
    if raw_norm == _GA_BASE_STATS_REUSE_RAW:
        return int(_GA_BASE_STATS_REUSE_ENABLED)

    _GA_BASE_STATS_REUSE_RAW = raw_norm
    if raw_norm in {"", "0", "false", "no", "off"}:
        _GA_BASE_STATS_REUSE_ENABLED = 0
    else:
        _GA_BASE_STATS_REUSE_ENABLED = 1
    return int(_GA_BASE_STATS_REUSE_ENABLED)


def _ga_exact_genome_eval_results_reuse_enabled() -> int:
    global _GA_EXACT_EVAL_RESULTS_REUSE_RAW, _GA_EXACT_EVAL_RESULTS_REUSE_ENABLED
    raw = os.environ.get("GPU_NATIVE_GA_EXACT_EVAL_RESULTS_REUSE", None)
    if raw is None:
        raw = os.environ.get("GPU_NATIVE_GA_EXACT_EVAL_REUSE", None)
    raw_norm = str(raw or "").strip().lower()
    if raw_norm == _GA_EXACT_EVAL_RESULTS_REUSE_RAW:
        return int(_GA_EXACT_EVAL_RESULTS_REUSE_ENABLED)

    _GA_EXACT_EVAL_RESULTS_REUSE_RAW = raw_norm
    if raw_norm in {"", "0", "false", "no", "off"}:
        _GA_EXACT_EVAL_RESULTS_REUSE_ENABLED = 0
    else:
        _GA_EXACT_EVAL_RESULTS_REUSE_ENABLED = 1
    return int(_GA_EXACT_EVAL_RESULTS_REUSE_ENABLED)


# Get appropriate kernels for current platform (Metal-safe on macOS)
kernels = get_kernels()


# ============================================================================
# UPLOAD CACHES (avoid redundant uploads over eGPU/Thunderbolt)
# ============================================================================
# Cache item_stats, slot_start, slot_count to avoid re-uploading ~2.6MB per song
# Cache base_fixed_stats (tiny but frequently called)

import hashlib


def _compute_array_sig(*arrays: np.ndarray) -> bytes:
    """Compute stable hash signature for numpy arrays."""
    h = hashlib.blake2b(digest_size=16)
    for arr in arrays:
        arr = np.ascontiguousarray(arr)
        h.update(arr.dtype.str.encode("utf-8"))
        h.update(np.array(arr.shape, dtype=np.int64).tobytes())
        h.update(arr.tobytes())
    return h.digest()


# Cache state for item_stats + slot boundaries
_ITEM_STATS_CACHE: dict = {"sig": None, "n_items": None, "array_id": None, "slot_start_id": None, "slot_count_id": None}

# Cache state for base_fixed_stats (simple tuple comparison)
_BASE_FIXED_STATS_CACHE: tuple | None = None
# Cache state for island boundaries (simple tuple comparison)
_ISLAND_BOUNDARIES_CACHE: tuple | None = None
_ISLAND_ELITES_CACHE: tuple | None = None
_ISLAND_ELITES_UPLOAD_BUFFER: np.ndarray | None = None


def reset_ga_upload_caches() -> None:
    """Reset upload caches after ti.reset() or when switching songs."""
    global _ITEM_STATS_CACHE, _BASE_FIXED_STATS_CACHE, _ISLAND_BOUNDARIES_CACHE
    global _ISLAND_ELITES_CACHE, _ISLAND_ELITES_UPLOAD_BUFFER
    _ITEM_STATS_CACHE = {"sig": None, "n_items": None, "array_id": None, "slot_start_id": None, "slot_count_id": None}
    _BASE_FIXED_STATS_CACHE = None
    _ISLAND_BOUNDARIES_CACHE = None
    _ISLAND_ELITES_CACHE = None
    _ISLAND_ELITES_UPLOAD_BUFFER = None


def _upload_island_elites(elite_indices: np.ndarray, n_elites: int) -> None:
    """Upload manual elite indices into GPU-resident `island_elite_indices`."""
    global _ISLAND_ELITES_CACHE, _ISLAND_ELITES_UPLOAD_BUFFER

    n_elites = int(n_elites)
    if n_elites <= 0:
        return
    elite_arr = np.asarray(elite_indices[:n_elites], dtype=np.int32)
    key = tuple(int(x) for x in elite_arr.tolist())
    if _ISLAND_ELITES_CACHE == key:
        return

    buf = _ISLAND_ELITES_UPLOAD_BUFFER
    if buf is None or int(buf.shape[0]) != int(fields.MAX_GENOMES):
        buf = np.zeros((fields.MAX_GENOMES,), dtype=np.int32)
        _ISLAND_ELITES_UPLOAD_BUFFER = buf

    buf[:n_elites] = elite_arr
    if n_elites < int(fields.MAX_GENOMES):
        buf[n_elites:] = 0
    fields.island_elite_indices.from_numpy(buf)
    _ISLAND_ELITES_CACHE = key


# ============================================================================
# GPU-NATIVE GA OPERATORS (UNUSED - Future infrastructure)
# ============================================================================
# These functions implement GPU-side GA operators (selection, crossover, mutation)
# but are NOT currently wired into genetic.py. They exist as prep work for a
# future GPU-native GA where the entire population lives on GPU.
#
# To complete: need encoder (genome -> item_ids) and integration in genetic.py.
# ============================================================================


def ga_upload_population_indices(population_indices_np: np.ndarray, *, n_slots: int = 9) -> int:
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
        kernels.ga_copy_population_indices_from_ndarray_kernel(int(n_genomes), int(n_slots), src)
    except Exception:
        pop_buf = np.zeros((fields.MAX_GENOMES, fields.MAX_SLOTS), dtype=np.int32)
        pop_buf[:n_genomes, : int(n_slots)] = src
        fields.population_indices.from_numpy(pop_buf)
    return n_genomes


def ga_upload_initial_populations(populations_np: np.ndarray, *, n_runs: int, n_genomes: int, n_slots: int = 9) -> None:
    """
    Upload a batch of initial populations for multi-start GA runs.

    `populations_np` is expected to contain encoded item IDs with shape (n_runs, n_genomes, n_slots).
    Data is padded to the fixed GPU buffer shapes and uploaded in one transfer.
    """
    ensure_ready()
    n_runs = int(n_runs)
    n_genomes = int(n_genomes)
    n_slots = int(n_slots)
    if n_runs <= 0 or n_genomes <= 0:
        return
    if n_runs > fields.MAX_GA_RUNS:
        raise ValueError(f"Too many runs: {n_runs} > {fields.MAX_GA_RUNS}")
    if n_genomes > fields.MAX_GA_RUN_GENOMES:
        raise ValueError(f"Too many genomes: {n_genomes} > {fields.MAX_GA_RUN_GENOMES}")
    if n_slots > fields.MAX_SLOTS:
        raise ValueError(f"Too many slots: {n_slots} > {fields.MAX_SLOTS}")

    src = np.asarray(populations_np, dtype=np.int32)
    expected_shape = (fields.MAX_GA_RUNS, fields.MAX_GA_RUN_GENOMES, fields.MAX_SLOTS)
    if src.shape == expected_shape:
        fields.ga_initial_populations.from_numpy(np.ascontiguousarray(src))
        return

    buf = np.zeros((fields.MAX_GA_RUNS, fields.MAX_GA_RUN_GENOMES, fields.MAX_SLOTS), dtype=np.int32)
    buf[:n_runs, :n_genomes, :n_slots] = src[:n_runs, :n_genomes, :n_slots]
    fields.ga_initial_populations.from_numpy(buf)


def ga_load_initial_population(*, run_idx: int, n_genomes: int, n_slots: int = 9) -> None:
    """
    Load a staged initial population (run_idx) into the active GA `population_indices`.
    """
    ensure_ready()
    run_idx = int(run_idx)
    n_genomes = int(n_genomes)
    n_slots = int(n_slots)
    if run_idx < 0 or run_idx >= fields.MAX_GA_RUNS:
        raise ValueError(f"run_idx out of range: {run_idx} (MAX_GA_RUNS={fields.MAX_GA_RUNS})")
    if n_genomes < 0 or n_genomes > fields.MAX_GA_RUN_GENOMES:
        raise ValueError(f"Too many genomes: {n_genomes} > {fields.MAX_GA_RUN_GENOMES}")
    kernels.ga_load_initial_population_kernel(run_idx, n_genomes, n_slots)


def ga_load_initial_populations_batch(
    *, run_idx_start: int, n_runs: int, n_genomes_per_run: int, n_slots: int = 9
) -> int:
    """
    Load a batch of staged initial populations into the active GA `population_indices`.

    Returns:
        Total genomes loaded (n_runs * n_genomes_per_run).
    """
    ensure_ready()
    run_idx_start = int(run_idx_start)
    n_runs = int(n_runs)
    n_genomes_per_run = int(n_genomes_per_run)
    n_slots = int(n_slots)
    if n_runs <= 0 or n_genomes_per_run <= 0:
        return 0
    if run_idx_start < 0 or run_idx_start >= fields.MAX_GA_RUNS:
        raise ValueError(f"run_idx_start out of range: {run_idx_start} (MAX_GA_RUNS={fields.MAX_GA_RUNS})")
    if run_idx_start + n_runs > fields.MAX_GA_RUNS:
        raise ValueError(
            f"batch runs out of range: start={run_idx_start}, n_runs={n_runs} (MAX_GA_RUNS={fields.MAX_GA_RUNS})"
        )
    if n_genomes_per_run < 0 or n_genomes_per_run > fields.MAX_GA_RUN_GENOMES:
        raise ValueError(f"Too many genomes: {n_genomes_per_run} > {fields.MAX_GA_RUN_GENOMES}")
    if n_slots > fields.MAX_SLOTS:
        raise ValueError(f"Too many slots: {n_slots} > {fields.MAX_SLOTS}")

    n_total = n_runs * n_genomes_per_run
    if n_total > fields.MAX_GENOMES:
        raise ValueError(f"Batch too large for MAX_GENOMES: {n_total} > {fields.MAX_GENOMES}")

    kernels.ga_load_initial_populations_batch_kernel(run_idx_start, n_runs, n_genomes_per_run, n_slots)
    return n_total


def ga_upload_init_heuristic_topk(*, topk_ids: np.ndarray, heuristic_k: int, n_slots: int = 9) -> None:
    """
    Upload per-slot heuristic sampling table used by GPU initial population generation.

    `topk_ids` is shape (n_slots, heuristic_k) containing valid item IDs for each slot.
    When heuristic_k <= 0, callers can skip this entirely.
    """
    ensure_ready()
    heuristic_k = int(heuristic_k)
    n_slots = int(n_slots)
    if heuristic_k <= 0:
        return

    src = np.asarray(topk_ids, dtype=np.int32)
    if src.ndim != 2:
        raise ValueError(f"topk_ids must be 2D; got shape={getattr(src, 'shape', None)}")
    if int(src.shape[0]) < n_slots:
        raise ValueError(f"topk_ids has too few slots: {src.shape[0]} < {n_slots}")

    # Field shape is (MAX_SLOTS, K) where K may be 1 when disabled.
    k_field = int(getattr(fields, "GA_INIT_HEURISTIC_K", heuristic_k) or heuristic_k)
    k_field = max(1, int(k_field))
    buf = np.zeros((fields.MAX_SLOTS, k_field), dtype=np.int32)
    buf[:n_slots, : min(k_field, heuristic_k)] = src[:n_slots, : min(heuristic_k, k_field)]
    fields.ga_init_heuristic_topk.from_numpy(buf)


def ga_generate_initial_populations(
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
    Generate initial populations on the GPU into `fields.ga_initial_populations`.

    This replaces the CPU-side build+encode+upload loop for multi-start runs.
    """
    ensure_ready()
    run_idx_start = int(run_idx_start)
    n_runs = int(n_runs)
    n_genomes = int(n_genomes)
    n_slots = int(n_slots)
    if n_runs <= 0 or n_genomes <= 0:
        return
    if run_idx_start < 0 or run_idx_start >= fields.MAX_GA_RUNS:
        raise ValueError(f"run_idx_start out of range: {run_idx_start} (MAX_GA_RUNS={fields.MAX_GA_RUNS})")
    if run_idx_start + n_runs > fields.MAX_GA_RUNS:
        raise ValueError(
            f"batch runs out of range: start={run_idx_start}, n_runs={n_runs} (MAX_GA_RUNS={fields.MAX_GA_RUNS})"
        )
    if n_genomes < 0 or n_genomes > fields.MAX_GA_RUN_GENOMES:
        raise ValueError(f"Too many genomes: {n_genomes} > {fields.MAX_GA_RUN_GENOMES}")
    if n_slots > fields.MAX_SLOTS:
        raise ValueError(f"Too many slots: {n_slots} > {fields.MAX_SLOTS}")

    heuristic_prob = float(heuristic_prob)
    heuristic_prob = max(0.0, min(1.0, heuristic_prob))
    seed_prob = float(seed_prob)
    seed_prob = max(0.0, min(1.0, seed_prob))

    heuristic_prob_fp = np.uint32(int(heuristic_prob * 4294967295.0))
    seed_prob_fp = np.uint32(int(seed_prob * 4294967295.0))

    heuristic_k = int(heuristic_k)
    if heuristic_k < 0:
        heuristic_k = 0
    # Clamp to actual allocated field K.
    k_field = int(getattr(fields, "GA_INIT_HEURISTIC_K", heuristic_k) or 0)
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

    kernels.ga_generate_initial_populations_kernel(
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


def ga_seed_rng(n_genomes: int, seed: int = 12345) -> None:
    """Seed per-genome RNG state for GPU GA operators."""
    ensure_ready()
    kernels.ga_seed_rng_kernel(int(n_genomes), np.uint32(seed))
    # GPU-only op; no CPU readback needed.


def ga_seed_rng_runs(*, n_runs: int, n_genomes_per_run: int, seed: int = 12345) -> None:
    """
    Seed per-genome RNG state for multiple independent runs packed contiguously.

    Each run is seeded as if its genomes were indexed [0..n_genomes_per_run).
    """
    ensure_ready()
    n_runs = int(n_runs)
    n_genomes_per_run = int(n_genomes_per_run)
    if n_runs <= 0 or n_genomes_per_run <= 0:
        return
    n_total = n_runs * n_genomes_per_run
    if n_total > fields.MAX_GENOMES:
        raise ValueError(f"Batch too large for MAX_GENOMES: {n_total} > {fields.MAX_GENOMES}")
    kernels.ga_seed_rng_runs_kernel(int(n_total), int(n_genomes_per_run), np.uint32(seed))


def ga_upload_item_stats(
    item_stats_np: np.ndarray,
    slot_start_np: np.ndarray,
    slot_count_np: np.ndarray,
) -> int:
    """
    Upload item stats and slot pool boundaries for GPU-native GA.

    Caches uploads to avoid redundant transfers over Thunderbolt/eGPU.

    Args:
        item_stats_np: (n_items, 10) int32 - per-item stats
        slot_start_np: (9,) int32 - first item_id per slot
        slot_count_np: (9,) int32 - count of items per slot

    Returns:
        Number of items uploaded (or cached)
    """
    global _ITEM_STATS_CACHE

    ensure_ready()
    n_items = int(item_stats_np.shape[0])

    if n_items > fields.MAX_ITEMS:
        raise ValueError(f"Too many items: {n_items} > {fields.MAX_ITEMS}")

    # Fast-path: if the caller is reusing the *same* numpy array objects, avoid hashing.
    try:
        if (
            _ITEM_STATS_CACHE.get("n_items") == n_items
            and _ITEM_STATS_CACHE.get("array_id") == id(item_stats_np)
            and _ITEM_STATS_CACHE.get("slot_start_id") == id(slot_start_np)
            and _ITEM_STATS_CACHE.get("slot_count_id") == id(slot_count_np)
        ):
            return n_items
    except Exception:
        pass

    # Check cache - avoid redundant uploads (~2.6MB savings)
    sig = _compute_array_sig(
        np.asarray(item_stats_np[:n_items, : fields.ITEM_STAT_DIM], dtype=np.int32),
        np.asarray(slot_start_np, dtype=np.int32),
        np.asarray(slot_count_np, dtype=np.int32),
    )
    if _ITEM_STATS_CACHE.get("sig") == sig:
        # Also memoize identities so subsequent calls can hit the fast-path.
        _ITEM_STATS_CACHE["n_items"] = n_items
        _ITEM_STATS_CACHE["array_id"] = id(item_stats_np)
        _ITEM_STATS_CACHE["slot_start_id"] = id(slot_start_np)
        _ITEM_STATS_CACHE["slot_count_id"] = id(slot_count_np)
        return n_items  # Already uploaded

    # Upload only the active rows instead of a full MAX_ITEMS padded table.
    stats_src = np.ascontiguousarray(item_stats_np[:n_items, : fields.ITEM_STAT_DIM], dtype=np.int32)

    slot_start_arr = np.zeros(fields.MAX_SLOTS, dtype=np.int32)
    slot_count_arr = np.zeros(fields.MAX_SLOTS, dtype=np.int32)
    start_np = np.asarray(slot_start_np, dtype=np.int32).reshape(-1)
    count_np = np.asarray(slot_count_np, dtype=np.int32).reshape(-1)
    n_slot_vals = min(int(fields.MAX_SLOTS), int(start_np.shape[0]), int(count_np.shape[0]))
    if n_slot_vals > 0:
        slot_start_arr[:n_slot_vals] = start_np[:n_slot_vals]
        slot_count_arr[:n_slot_vals] = count_np[:n_slot_vals]

    kernels.ga_upload_item_stats_and_slots_kernel(stats_src, int(n_items), slot_start_arr, slot_count_arr)

    _ITEM_STATS_CACHE["sig"] = sig
    _ITEM_STATS_CACHE["n_items"] = n_items
    _ITEM_STATS_CACHE["array_id"] = id(item_stats_np)
    _ITEM_STATS_CACHE["slot_start_id"] = id(slot_start_np)
    _ITEM_STATS_CACHE["slot_count_id"] = id(slot_count_np)
    return n_items


def ga_upload_base_fixed_stats(base_stats_np: np.ndarray) -> None:
    """
    Upload fixed base stats (added to all genomes during aggregation).

    Caches uploads to avoid redundant transfers.

    Args:
        base_stats_np: (10,) int32 - base stats [PP, CM, FM, FT, FF, Beat, Vibe, Rush, Flow, Chill]
    """
    global _BASE_FIXED_STATS_CACHE

    # Fast tuple comparison for small array
    key = tuple(int(x) for x in base_stats_np[: fields.ITEM_STAT_DIM])
    if _BASE_FIXED_STATS_CACHE == key:
        return  # Already uploaded

    ensure_ready()
    buf = np.zeros(fields.ITEM_STAT_DIM, dtype=np.int32)
    buf[: len(base_stats_np)] = np.asarray(base_stats_np, dtype=np.int32)
    fields.base_fixed_stats.from_numpy(buf)

    _BASE_FIXED_STATS_CACHE = key


def ga_aggregate_stats(
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
    - Call ga_upload_population_indices() first
    - Call ga_upload_item_stats() first
    - Call ga_upload_base_fixed_stats() first

    Args:
        n_genomes: Number of genomes to aggregate
        n_slots: Number of slots per genome (default 9)
        is_p_*: Primary color contribution flags (0 or 1)
        is_s_*: Secondary color contribution flags (0 or 1)
    """
    ensure_ready()
    kernels.ga_aggregate_genome_stats_kernel(
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


def ga_evaluate_population(
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
    use_hints: int = 0,
    use_exact_inner_solver: bool = False,
    max_ft_gems_global: int | None = None,
    max_ff_gems_global: int | None = None,
    materialize_mode: str = "none",
    update_global_best: bool = False,
) -> None:
    """
    GPU-native population evaluation: aggregate stats + evaluate + copy scores.

    This is the main GA evaluation function for GPU-native mode. It:
    1. Aggregates item stats → genome_base_stats (ga_aggregate_genome_stats_kernel)
    2. Evaluates all (ft, ff) combos → genome_result_stats (solve_genomes_with_ftff_kernel)
    3. Copies scores to ga_scores for selection (ga_copy_scores_kernel)

    PREREQUISITES:
    - Call ga_upload_population_indices() with encoded population
    - Call ga_upload_item_stats() with item stats and slot pools
    - Call ga_upload_base_fixed_stats() with base stats
    - Upload timeline grid using precompute_timeline_gpu() or _upload_timeline_grid()

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
    use_hints_i = int(use_hints)
    use_exact_inner_solver_i = int(bool(use_exact_inner_solver))
    exact_genome_base_stats_reuse = bool(_ga_exact_genome_base_stats_reuse_enabled())
    # Warm-start local search is not result-stable enough on the current Metal path
    # to safely collapse duplicate rows without changing convergence behavior.
    # Keep exact-eval reuse limited to cold-start generations.
    exact_genome_eval_results_reuse = bool(_ga_exact_genome_eval_results_reuse_enabled()) and use_hints_i == 0

    if exact_genome_base_stats_reuse or exact_genome_eval_results_reuse:
        kernels.ga_build_exact_eval_reuse_map_kernel(
            int(n_genomes),
            int(n_slots),
            int(exact_genome_eval_results_reuse and use_hints_i != 0),
        )

    # Step 1: FUSED aggregate + init (was 2 kernels, now 1)
    kernels.ga_aggregate_and_init_best_kernel(
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
        int(exact_genome_base_stats_reuse),
    )

    if exact_genome_base_stats_reuse:
        kernels.ga_propagate_exact_eval_reuse_base_stats_kernel(int(n_genomes))

    # Step 2: Evaluate genomes using existing FT/FF iteration kernel
    total_budget_i = int(total_budget)
    gem_scale_fever_i = int(gem_scale_fever)
    song_slot_i = int(song_slot)

    # Warm-start logic: Default to cold start (0) unless specified
    # Use cached module-level plateau prune setting (avoids per-call os.environ overhead)
    prune_plateaus_i = _GA_PLATEAU_PRUNE_ENABLED

    # Precompute FT/FF combo tables once per budget (tiny upload, reused across generations).
    max_ft_gems_i = int(total_budget_i) if max_ft_gems_global is None else int(max_ft_gems_global)
    max_ff_gems_i = int(total_budget_i) if max_ff_gems_global is None else int(max_ff_gems_global)
    max_ft_gems_i = max(0, min(int(total_budget_i), int(max_ft_gems_i)))
    max_ff_gems_i = max(0, min(int(total_budget_i), int(max_ff_gems_i)))
    n_combos = _ensure_ftff_combo_tables(
        total_budget_i,
        max_ft_gems=max_ft_gems_i,
        max_ff_gems=max_ff_gems_i,
    )
    eval_budget = int(_ga_eval_budget())
    max_evals = max(int(eval_budget), int(n_genomes))
    combo_chunk = compute_ga_combo_chunk(
        n_genomes=n_genomes,
        n_combos=n_combos,
        max_evals=max_evals,
        chunk_min=_GA_COMBO_CHUNK_MIN,
        chunk_max=_GA_COMBO_CHUNK_MAX,
    )
    if combo_chunk <= 0:
        combo_chunk = int(n_combos)

    offset = 0
    while offset < n_combos:
        chunk_len = int(min(combo_chunk, n_combos - offset))
        # If the remainder is tiny, fold it into this dispatch to avoid a "tail kernel" launch.
        if _GA_COMBO_TAIL_MERGE_MAX > 0:
            rem = int(n_combos - (offset + chunk_len))
            if 0 < rem <= int(_GA_COMBO_TAIL_MERGE_MAX):
                merged = int(chunk_len + rem)
                if int(n_genomes) * int(merged) <= int(max_evals):
                    chunk_len = merged
        kernels.ga_find_best_combo_warmstart_kernel(
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
            use_hints_i,
            int(prune_plateaus_i),
            use_exact_inner_solver_i,
            int(exact_genome_eval_results_reuse),
        )
        offset += int(chunk_len)

    if exact_genome_eval_results_reuse:
        kernels.ga_propagate_exact_eval_reuse_chunk_best_kernel(int(n_genomes))

    _ga_materialize_population_results(
        n_genomes=n_genomes,
        n_slots=n_slots,
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
        update_global_best=bool(update_global_best),
    )


def _ga_materialize_population_results(
    *,
    n_genomes: int,
    n_slots: int,
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
    update_global_best: bool = False,
) -> None:
    mode = str(materialize_mode or "none").strip().lower()
    if mode in {"", "none", "off", "false", "0"}:
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

    if mode in {"results", "results_only", "write_results"}:
        kernels.ga_write_best_results_from_key_kernel(*common_args)
        if update_global_best:
            kernels.ga_update_global_best_kernel(int(n_genomes), int(n_slots))
        return

    if mode in {"hints", "store_hints", "write_hints"}:
        kernels.ga_write_best_and_store_hints_kernel(*common_args)
        if update_global_best:
            kernels.ga_update_global_best_kernel(int(n_genomes), int(n_slots))
        return

    if mode in {"global", "update_global", "write_global", "write_best_and_update_global"}:
        kernels.ga_write_best_and_update_global_kernel(
            int(n_genomes),
            int(n_slots),
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
        return

    raise ValueError(f"Unknown GA materialize_mode: {materialize_mode!r}")


def ga_write_best_and_update_global(
    n_genomes: int,
    n_slots: int,
    total_budget: int,
    gem_scale_fever: int,
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
    song_slot: int = 0,
) -> None:
    """
    FUSED: Write best results + store hints + update global best (3 kernels -> 1).

    Call this AFTER evaluation (ga_evaluate_population) to:
    1. Finalize best combo from chunk_best_key
    2. Store hints for next generation (warm-start)
    3. Update GPU-side global best

    Args:
        n_genomes: Number of genomes
        n_slots: Number of equipment slots
        total_budget: Total gem budget
        gem_scale_fever: Gems per fever stat point
        is_*: Color contribution flags (0/1)
        song_slot: Timeline grid slot
    """
    ensure_ready()
    _ga_materialize_population_results(
        n_genomes=int(n_genomes),
        n_slots=int(n_slots),
        total_budget=int(total_budget),
        gem_scale_fever=int(gem_scale_fever),
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
        song_slot=int(song_slot),
        materialize_mode="update_global",
    )


def ga_write_best_and_store_hints(
    n_genomes: int,
    total_budget: int,
    gem_scale_fever: int,
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
    song_slot: int = 0,
) -> None:
    """
    Materialize best results + store hints (no global-best update).

    This is used for batched multi-run execution where each run is packed into
    a segment of the population arrays and per-run best is computed at packing time.
    """
    ensure_ready()
    _ga_materialize_population_results(
        n_genomes=int(n_genomes),
        n_slots=0,
        total_budget=int(total_budget),
        gem_scale_fever=int(gem_scale_fever),
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
        song_slot=int(song_slot),
        materialize_mode="store_hints",
    )


def ga_store_hints(n_genomes: int) -> None:
    """
    Store current best gem allocations as hints for next generation.
    Call this AFTER evaluation, BEFORE crossover.
    """
    ensure_ready()
    kernels.ga_store_hints_kernel(int(n_genomes))


def ga_inherit_hints(n_genomes: int) -> None:
    """
    Inherit hints from parents to children.
    Call this AFTER crossover, BEFORE next evaluation.
    """
    ensure_ready()
    kernels.ga_inherit_hints_kernel(int(n_genomes))


def ga_set_scores(scores_np: np.ndarray, *, n_genomes: int | None = None) -> int:
    """Upload fitness scores to GPU (fields.ga_scores). Returns n_genomes used."""
    ensure_ready()
    if n_genomes is None:
        n_genomes = int(scores_np.shape[0])
    n_genomes = int(n_genomes)
    if n_genomes <= 0:
        return 0
    if n_genomes > fields.MAX_GENOMES:
        raise ValueError(f"Too many genomes: {n_genomes} > {fields.MAX_GENOMES}")
    buf = np.zeros((fields.MAX_GENOMES,), dtype=np.int32)
    buf[:n_genomes] = np.asarray(scores_np[:n_genomes], dtype=np.int32)
    fields.ga_scores.from_numpy(buf)
    return n_genomes


def ga_next_generation(
    *,
    n_genomes: int,
    n_slots: int = 9,
    mutation_rate: float = 0.02,
    tournament_k: int = 3,
    elite_count: int = 2,
    elite_indices: np.ndarray | None = None,
) -> None:
    """
    Run one GPU-side GA operator step on resident population:
      selection -> crossover+mutation -> [elitism] -> swap buffers.

    Args:
        n_genomes: Population size
        n_slots: Slots per genome (default 9)
        mutation_rate: Probability of mutation per genome (default 0.02)
        tournament_k: Tournament size for selection (default 3)
        elite_count: Number of elites to preserve (default 2)
        elite_indices: Optional array of elite genome indices from current gen.
                      If provided, these genomes are copied to front of next gen.
                      If None and elite_count > 0, uses indices [0..elite_count-1].
    """
    ensure_ready()
    n_genomes = int(n_genomes)
    n_slots = int(n_slots)
    elite_count = int(elite_count)
    tournament_k = int(tournament_k)
    if n_genomes <= 0:
        return
    if n_slots <= 0 or n_slots > fields.MAX_SLOTS:
        raise ValueError(f"Invalid n_slots: {n_slots}")
    if elite_count < 0:
        elite_count = 0
    if elite_count > n_genomes:
        elite_count = n_genomes
    if tournament_k < 1:
        tournament_k = 1

    # Convert probability to uint32 threshold.
    mr = float(mutation_rate)
    if mr <= 0.0:
        mr_fp = np.uint32(0)
    elif mr >= 1.0:
        mr_fp = np.uint32(0xFFFFFFFF)
    else:
        mr_fp = np.uint32(int(mr * 4294967295.0))

    n_elites = 0
    if elite_count > 0:
        if elite_indices is None:
            elite_arr = np.arange(elite_count, dtype=np.int32)
        else:
            elite_arr = np.asarray(elite_indices[:elite_count], dtype=np.int32)
        n_elites = int(min(n_genomes, int(elite_arr.shape[0])))
        if n_elites > 0:
            _upload_island_elites(elite_arr, n_elites)

    # Use the fused next-generation kernel so the older selection/crossover kernels
    # are no longer on the hot path.
    kernels.ga_next_generation_full_kernel(
        int(n_genomes),
        int(n_slots),
        int(n_elites),
        int(tournament_k),
        mr_fp,
        np.uint32(0),  # no immigrants in this call shape
    )
    kernels.ga_swap_and_inherit_hints_kernel(int(n_genomes), int(n_slots))


def ga_next_generation_gpu_elites(
    *,
    n_genomes: int,
    n_slots: int = 9,
    mutation_rate: float = 0.02,
    tournament_k: int = 3,
    n_elites: int = 10,
) -> None:
    """
    Run one GPU-side GA operator step using GPU-resident elite indices.

    This is an optimized version of ga_next_generation that reads elite indices
    from the GPU-resident island_elite_indices field (set by ga_find_island_elites)
    instead of a CPU ndarray. This avoids the expensive GPU->CPU transfer per generation.

    Args:
        n_genomes: Population size
        n_slots: Slots per genome (default 9)
        mutation_rate: Probability of mutation per genome (default 0.02)
        tournament_k: Tournament size for selection (default 3)
        n_elites: Total number of elites to preserve (n_islands * elites_per_island)
    """
    ensure_ready()
    n_genomes = int(n_genomes)
    n_slots = int(n_slots)
    n_elites = int(n_elites)
    tournament_k = int(tournament_k)
    if n_genomes <= 0:
        return
    if n_slots <= 0 or n_slots > fields.MAX_SLOTS:
        raise ValueError(f"Invalid n_slots: {n_slots}")
    if n_elites < 0:
        n_elites = 0
    if n_elites > n_genomes:
        n_elites = n_genomes
    if tournament_k < 1:
        tournament_k = 1

    # Convert probability to uint32 threshold.
    mr = float(mutation_rate)
    if mr <= 0.0:
        mr_fp = np.uint32(0)
    elif mr >= 1.0:
        mr_fp = np.uint32(0xFFFFFFFF)
    else:
        mr_fp = np.uint32(int(mr * 4294967295.0))

    # Use fused kernel path (selection+crossover+mutation+elitism), then swap.
    kernels.ga_next_generation_full_kernel(
        int(n_genomes),
        int(n_slots),
        int(n_elites),
        int(tournament_k),
        mr_fp,
        np.uint32(0),  # no immigrants in this API
    )
    kernels.ga_swap_and_inherit_hints_kernel(int(n_genomes), int(n_slots))


def ga_next_generation_fused(
    *,
    n_genomes: int,
    n_slots: int = 9,
    mutation_rate: float = 0.02,
    immigrant_rate: float = 0.0,
    tournament_k: int = 3,
    n_islands: int = 1,
    elites_per_island: int = 1,
) -> None:
    """
    FULLY FUSED next generation: 2 kernel launches instead of 4.

    This combines:
    1. ga_next_generation_full_islands_kernel: select + crossover + mutate + island elites (computed on-the-fly)
    2. ga_swap_and_inherit_hints_kernel: swap + hint inheritance

    Args:
        n_genomes: Population size
        n_slots: Slots per genome (default 9)
        mutation_rate: Probability of mutation per genome (default 0.02)
        immigrant_rate: Probability of fully re-rolling a genome per generation (default 0.0)
        tournament_k: Tournament size for selection (default 3)
        n_islands: Number of islands (must match uploaded island_boundaries)
        elites_per_island: Elites preserved per island
    """
    ensure_ready()
    n_genomes = int(n_genomes)
    n_slots = int(n_slots)
    n_islands = int(n_islands)
    elites_per_island = int(elites_per_island)
    tournament_k = int(tournament_k)
    if n_genomes <= 0:
        return
    if n_slots <= 0 or n_slots > fields.MAX_SLOTS:
        raise ValueError(f"Invalid n_slots: {n_slots}")
    if n_islands < 1:
        n_islands = 1
    if elites_per_island < 0:
        elites_per_island = 0
    if tournament_k < 1:
        tournament_k = 1

    # Convert probability to uint32 threshold.
    mr = float(mutation_rate)
    if mr <= 0.0:
        mr_fp = np.uint32(0)
    elif mr >= 1.0:
        mr_fp = np.uint32(0xFFFFFFFF)
    else:
        mr_fp = np.uint32(int(mr * 4294967295.0))

    ir = float(immigrant_rate)
    if ir <= 0.0:
        ir_fp = np.uint32(0)
    elif ir >= 1.0:
        ir_fp = np.uint32(0xFFFFFFFF)
    else:
        ir_fp = np.uint32(int(ir * 4294967295.0))

    # Precompute island elites once, then run fused next-gen using GPU-resident elite indices.
    elites_per_island_eff = max(1, int(elites_per_island))
    n_elites = min(int(n_genomes), int(n_islands) * int(elites_per_island_eff))
    kernels.ga_find_island_elites_kernel(
        int(n_genomes),
        int(n_islands),
        int(elites_per_island_eff),
    )
    kernels.ga_next_generation_full_kernel(
        int(n_genomes),
        int(n_slots),
        int(n_elites),
        int(tournament_k),
        mr_fp,
        ir_fp,
    )

    # FUSED: Swap + Hint Inheritance (second kernel)
    kernels.ga_swap_and_inherit_hints_kernel(n_genomes, n_slots)


def ga_next_generation_fused_runs(
    *,
    n_runs: int,
    n_genomes_per_run: int,
    n_slots: int = 9,
    mutation_rate: float = 0.02,
    immigrant_rate: float = 0.0,
    tournament_k: int = 3,
    n_islands: int = 1,
    elites_per_island: int = 1,
) -> None:
    """
    FULLY FUSED next generation for multiple independent runs packed contiguously.

    Executes:
    1) ga_next_generation_full_runs_kernel (select+crossover+mutate+elitism within each run)
    2) ga_swap_and_inherit_hints_kernel (swap + hint inheritance) for the combined population
    """
    ensure_ready()
    n_runs = int(n_runs)
    n_genomes_per_run = int(n_genomes_per_run)
    n_slots = int(n_slots)
    n_islands = int(n_islands)
    elites_per_island = int(elites_per_island)
    tournament_k = int(tournament_k)
    if n_runs <= 0 or n_genomes_per_run <= 0:
        return
    if n_slots <= 0 or n_slots > fields.MAX_SLOTS:
        raise ValueError(f"Invalid n_slots: {n_slots}")
    if n_islands < 1:
        n_islands = 1
    if elites_per_island < 0:
        elites_per_island = 0
    if tournament_k < 1:
        tournament_k = 1

    n_total = n_runs * n_genomes_per_run
    if n_total > fields.MAX_GENOMES:
        raise ValueError(f"Batch too large for MAX_GENOMES: {n_total} > {fields.MAX_GENOMES}")

    mr = float(mutation_rate)
    if mr <= 0.0:
        mr_fp = np.uint32(0)
    elif mr >= 1.0:
        mr_fp = np.uint32(0xFFFFFFFF)
    else:
        mr_fp = np.uint32(int(mr * 4294967295.0))

    ir = float(immigrant_rate)
    if ir <= 0.0:
        ir_fp = np.uint32(0)
    elif ir >= 1.0:
        ir_fp = np.uint32(0xFFFFFFFF)
    else:
        ir_fp = np.uint32(int(ir * 4294967295.0))

    kernels.ga_next_generation_full_runs_kernel(
        n_runs,
        n_genomes_per_run,
        n_slots,
        n_islands,
        elites_per_island,
        tournament_k,
        mr_fp,
        ir_fp,
    )
    kernels.ga_swap_and_inherit_hints_kernel(int(n_total), n_slots)


def ga_download_population_indices(*, n_genomes: int, n_slots: int = 9) -> np.ndarray:
    """Download the current resident population indices (for testing / debugging)."""
    ensure_ready()
    n_genomes = int(n_genomes)
    n_slots = int(n_slots)
    out = fields.population_indices.to_numpy()
    return np.asarray(out[:n_genomes, :n_slots], dtype=np.int32)


def ga_download_scores(n_genomes: int) -> np.ndarray:
    """
    Download fitness scores from GPU (for CPU-side elitism).

    Args:
        n_genomes: Number of genomes to download

    Returns:
        np.ndarray: (n_genomes,) int32 array of scores
    """
    ensure_ready()
    n_genomes = int(n_genomes)
    out = fields.ga_scores.to_numpy()
    return np.asarray(out[:n_genomes], dtype=np.int32)


def ga_download_results(n_genomes: int) -> np.ndarray:
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
    except Exception:
        results_np = None

    if results_np is None:
        out = fields.genome_result_stats.to_numpy()
        results_np = out[:n_genomes]
    return np.asarray(results_np, dtype=np.int32)


def ga_download_run_payload(
    *, n_genomes: int, n_slots: int = 9
) -> tuple[int, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Download a GA run snapshot with a single GPU->CPU transfer.

    Returns:
        (best_score, best_genome_ids, best_results, population_indices, results, scores)
    """
    ensure_ready()
    n_genomes = int(n_genomes)
    n_slots = int(n_slots)
    kernels.ga_pack_run_payload_kernel(n_genomes, n_slots)
    packed_full = None
    try:
        cols = 1 + n_slots + 7
        rows = n_genomes + 1
        staging = getattr(fields, "ga_run_payload_download_staging_256", None)
        if staging is not None:
            shape = getattr(staging, "shape", None)
            if shape and len(shape) >= 2 and rows <= int(shape[0]):
                try:
                    full_shape = getattr(fields.ga_run_payload_packed, "shape", None)
                    full_elems = int(full_shape[0]) * int(full_shape[1]) if full_shape is not None else 0
                except Exception:
                    full_elems = 0
                try:
                    staging_elems = int(shape[0]) * int(shape[1])
                except Exception:
                    staging_elems = 0
                if full_elems <= 0 or staging_elems <= 0 or full_elems > staging_elems:
                    kernels.ga_copy_run_payload_to_download_staging_kernel(staging, int(n_genomes), int(n_slots))
                    packed_full = staging.to_numpy()
    except Exception:
        packed_full = None

    if packed_full is None:
        packed_full = fields.ga_run_payload_packed.to_numpy()

    cols = 1 + n_slots + 7
    rows = n_genomes + 1
    packed = packed_full[:rows, :cols]

    best_score = int(packed[0, 0])
    best_genome_ids = np.asarray(packed[0, 1 : 1 + n_slots], dtype=np.int32).copy()
    best_results = np.asarray(packed[0, 1 + n_slots : 1 + n_slots + 7], dtype=np.int32).copy()

    pop_snapshot = np.asarray(packed[1 : n_genomes + 1, 1 : 1 + n_slots], dtype=np.int32).copy()
    results = np.asarray(packed[1 : n_genomes + 1, 1 + n_slots : 1 + n_slots + 7], dtype=np.int32).copy()
    scores = np.asarray(packed[1 : n_genomes + 1, 0], dtype=np.int32).copy()

    return best_score, best_genome_ids, best_results, pop_snapshot, results, scores


def ga_store_run_payload(*, run_idx: int, n_genomes: int, n_slots: int = 9) -> None:
    """
    Store a GA run snapshot into the GPU multi-run buffer (no CPU readback).
    """
    ensure_ready()
    run_idx = int(run_idx)
    n_genomes = int(n_genomes)
    n_slots = int(n_slots)
    if run_idx < 0 or run_idx >= fields.MAX_GA_RUNS:
        raise ValueError(f"run_idx out of range: {run_idx} (MAX_GA_RUNS={fields.MAX_GA_RUNS})")
    if n_genomes < 0 or n_genomes > fields.MAX_GA_RUN_GENOMES:
        raise ValueError(
            f"n_genomes out of range for run buffer: {n_genomes} (MAX_GA_RUN_GENOMES={fields.MAX_GA_RUN_GENOMES})"
        )
    kernels.ga_pack_and_store_run_payload_kernel(run_idx, n_genomes, n_slots)


def ga_init_runs_best(*, run_idx_start: int, n_runs: int, n_slots: int = 9) -> None:
    """
    Initialize per-run best rows (row 0) for multi-run payload packing.
    """
    ensure_ready()
    run_idx_start = int(run_idx_start)
    n_runs = int(n_runs)
    n_slots = int(n_slots)
    if n_runs <= 0:
        return
    if run_idx_start < 0 or run_idx_start >= fields.MAX_GA_RUNS:
        raise ValueError(f"run_idx_start out of range: {run_idx_start} (MAX_GA_RUNS={fields.MAX_GA_RUNS})")
    if run_idx_start + n_runs > fields.MAX_GA_RUNS:
        raise ValueError(
            f"batch runs out of range: start={run_idx_start}, n_runs={n_runs} (MAX_GA_RUNS={fields.MAX_GA_RUNS})"
        )
    kernels.ga_init_runs_best_kernel(run_idx_start, n_runs, n_slots)


def ga_update_runs_best(*, run_idx_start: int, n_runs: int, n_genomes_per_run: int, n_slots: int = 9) -> None:
    """
    Update per-run best rows (row 0) for packed multi-run execution.
    """
    ensure_ready()
    run_idx_start = int(run_idx_start)
    n_runs = int(n_runs)
    n_genomes_per_run = int(n_genomes_per_run)
    n_slots = int(n_slots)
    if n_runs <= 0 or n_genomes_per_run <= 0:
        return
    if run_idx_start < 0 or run_idx_start >= fields.MAX_GA_RUNS:
        raise ValueError(f"run_idx_start out of range: {run_idx_start} (MAX_GA_RUNS={fields.MAX_GA_RUNS})")
    if run_idx_start + n_runs > fields.MAX_GA_RUNS:
        raise ValueError(
            f"batch runs out of range: start={run_idx_start}, n_runs={n_runs} (MAX_GA_RUNS={fields.MAX_GA_RUNS})"
        )
    n_total = n_runs * n_genomes_per_run
    if n_total > fields.MAX_GENOMES:
        raise ValueError(f"Batch too large for MAX_GENOMES: {n_total} > {fields.MAX_GENOMES}")
    kernels.ga_update_runs_best_kernel(run_idx_start, n_runs, n_genomes_per_run, n_slots)


def ga_store_runs_payload_snapshot_segmented(
    *, run_idx_start: int, n_runs: int, n_genomes_per_run: int, n_slots: int = 9
) -> None:
    """
    Store per-genome snapshot rows (1..n_genomes) into the multi-run buffer for packed execution.

    This does not touch each run's row 0 best.
    """
    ensure_ready()
    run_idx_start = int(run_idx_start)
    n_runs = int(n_runs)
    n_genomes_per_run = int(n_genomes_per_run)
    n_slots = int(n_slots)
    if n_runs <= 0 or n_genomes_per_run <= 0:
        return
    if run_idx_start < 0 or run_idx_start >= fields.MAX_GA_RUNS:
        raise ValueError(f"run_idx_start out of range: {run_idx_start} (MAX_GA_RUNS={fields.MAX_GA_RUNS})")
    if run_idx_start + n_runs > fields.MAX_GA_RUNS:
        raise ValueError(
            f"batch runs out of range: start={run_idx_start}, n_runs={n_runs} (MAX_GA_RUNS={fields.MAX_GA_RUNS})"
        )
    if n_genomes_per_run < 0 or n_genomes_per_run > fields.MAX_GA_RUN_GENOMES:
        raise ValueError(
            f"n_genomes_per_run out of range: {n_genomes_per_run} (MAX_GA_RUN_GENOMES={fields.MAX_GA_RUN_GENOMES})"
        )
    n_total = n_runs * n_genomes_per_run
    if n_total > fields.MAX_GENOMES:
        raise ValueError(f"Batch too large for MAX_GENOMES: {n_total} > {fields.MAX_GENOMES}")
    kernels.ga_store_runs_payload_snapshot_segmented_kernel(run_idx_start, n_runs, n_genomes_per_run, n_slots)


def ga_store_run_payload_segmented(*, run_idx: int, start_offset: int, n_genomes: int, n_slots: int = 9) -> None:
    """
    Store a GA run snapshot into the multi-run buffer for a run stored at an offset.
    """
    ensure_ready()
    run_idx = int(run_idx)
    start_offset = int(start_offset)
    n_genomes = int(n_genomes)
    n_slots = int(n_slots)
    if run_idx < 0 or run_idx >= fields.MAX_GA_RUNS:
        raise ValueError(f"run_idx out of range: {run_idx} (MAX_GA_RUNS={fields.MAX_GA_RUNS})")
    if n_genomes < 0 or n_genomes > fields.MAX_GA_RUN_GENOMES:
        raise ValueError(
            f"n_genomes out of range for run buffer: {n_genomes} (MAX_GA_RUN_GENOMES={fields.MAX_GA_RUN_GENOMES})"
        )
    if start_offset < 0 or (start_offset + n_genomes) > fields.MAX_GENOMES:
        raise ValueError(f"Invalid start_offset/n_genomes: start={start_offset} n_genomes={n_genomes}")
    kernels.ga_pack_and_store_run_payload_segmented_kernel(run_idx, start_offset, n_genomes, n_slots)


def ga_download_runs_payload(*, n_runs: int, n_genomes: int, n_slots: int = 9) -> np.ndarray:
    """
    Download stored GA run snapshots from the GPU multi-run buffer in one transfer.

    Returns:
        np.ndarray[int32] with shape (n_runs, n_genomes+1, 1+n_slots+7)
    """
    ensure_ready()
    n_runs = int(n_runs)
    n_genomes = int(n_genomes)
    n_slots = int(n_slots)
    if n_runs < 0 or n_runs > fields.MAX_GA_RUNS:
        raise ValueError(f"n_runs out of range: {n_runs} (MAX_GA_RUNS={fields.MAX_GA_RUNS})")
    if n_genomes < 0 or n_genomes > fields.MAX_GA_RUN_GENOMES:
        raise ValueError(
            f"n_genomes out of range for run buffer: {n_genomes} (MAX_GA_RUN_GENOMES={fields.MAX_GA_RUN_GENOMES})"
        )

    cols = 1 + n_slots + 7
    n_rows = n_genomes + 1

    perf = str(os.environ.get("PERF_TIMING", "0") or "").strip().lower() in {"1", "true", "yes", "on"}
    t_total = time.perf_counter() if perf else 0.0

    out = None
    mode = "full"
    copy_ms = 0.0

    try:
        full_shape = getattr(fields.ga_runs_payload_packed, "shape", None)
        full_elems = int(full_shape[0]) * int(full_shape[1]) * int(full_shape[2]) if full_shape is not None else 0

        staging_candidates = [
            ("staging_16", fields.ga_runs_payload_download_staging_16),
            ("staging_64", fields.ga_runs_payload_download_staging_64),
            ("staging_128", fields.ga_runs_payload_download_staging_128),
        ]
        best = None
        for name, fld in staging_candidates:
            if fld is None:
                continue
            shape = getattr(fld, "shape", None)
            if not shape or len(shape) < 3:
                continue
            if n_runs <= int(shape[0]) and n_rows <= int(shape[1]):
                elems = int(shape[0]) * int(shape[1]) * int(shape[2])
                if best is None or elems < best[0]:
                    best = (elems, name, fld, shape)

        if best is not None and full_elems > int(best[0]):
            _, name, fld, shape = best
            mode = str(name)
            t_copy = time.perf_counter() if perf else 0.0
            kernels.ga_copy_runs_payload_to_download_staging_kernel(fld, int(n_runs), int(n_genomes), int(n_slots))
            copy_ms = (time.perf_counter() - t_copy) * 1000.0 if perf else 0.0
            out = fld.to_numpy()
    except Exception:
        out = None

    if out is None:
        out = fields.ga_runs_payload_packed.to_numpy()

    view = out[:n_runs, :n_rows, :cols]
    total_ms = (time.perf_counter() - t_total) * 1000.0 if perf else 0.0
    if perf:
        try:
            shape = getattr(view, "shape", None)
            elems = int(shape[0]) * int(shape[1]) * int(shape[2]) if shape is not None else 0
            view_bytes_i32 = elems * 4
        except Exception:
            view_bytes_i32 = 0
        try:
            out_shape = getattr(out, "shape", None)
            out_elems = int(out_shape[0]) * int(out_shape[1]) * int(out_shape[2]) if out_shape is not None else 0
            transfer_bytes_i32 = out_elems * 4
        except Exception:
            transfer_bytes_i32 = 0
        print(
            "[PERF][GADownloadRunsPayload] "
            f"runs={n_runs} pop={n_genomes} mode={mode} copy={copy_ms:.1f}ms total={total_ms:.1f}ms "
            f"view_bytes={view_bytes_i32} transfer_bytes={transfer_bytes_i32}"
        )

    if view.dtype == np.int32 and view.flags["C_CONTIGUOUS"]:
        return view
    return np.ascontiguousarray(view, dtype=np.int32)


def ga_pack_fg_candidates_table_segmented(
    *,
    table_slot: int,
    run_idx_start: int,
    n_runs: int,
    n_genomes_per_run: int,
    n_slots: int = 9,
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
    Pack a compact GA->FG candidate table for packed multi-run execution.

    This is intended to replace large `ga_download_runs_payload()` transfers.
    """
    ensure_ready()
    table_slot = int(table_slot)
    run_idx_start = int(run_idx_start)
    n_runs = int(n_runs)
    n_genomes_per_run = int(n_genomes_per_run)
    n_slots = int(n_slots)
    if n_runs <= 0 or n_genomes_per_run <= 0:
        return
    if table_slot < 0 or table_slot >= int(fields.MAX_SONG_SLOTS):
        raise ValueError(f"table_slot out of range: {table_slot} (MAX_SONG_SLOTS={fields.MAX_SONG_SLOTS})")
    if run_idx_start < 0 or run_idx_start >= int(fields.MAX_GA_RUNS):
        raise ValueError(f"run_idx_start out of range: {run_idx_start} (MAX_GA_RUNS={fields.MAX_GA_RUNS})")
    if run_idx_start + n_runs > int(fields.MAX_GA_RUNS):
        raise ValueError(
            f"batch runs out of range: start={run_idx_start}, n_runs={n_runs} (MAX_GA_RUNS={fields.MAX_GA_RUNS})"
        )
    if n_slots != 9:
        raise ValueError(f"GPU-native GA expects n_slots=9 for FG candidate packing, got {n_slots}")

    kernels.ga_pack_fg_candidates_table_segmented_kernel(
        int(table_slot),
        int(run_idx_start),
        int(n_runs),
        int(n_genomes_per_run),
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


def ga_download_fg_selected_payload(
    *,
    table_slot: int,
    n_runs: int,
    limit: int,
    top_base_keep: int,
    base_budget: int,
    fg_budget_end: int,
) -> np.ndarray:
    """
    Download the GPU-selected GA->FG candidate payload for one song/table slot.

    Returns:
        np.ndarray[int32] with shape (N+1, 26):
          - Row 0: header [selected_count, best_score, best_ids(9), best_results(7), best_run_idx, ...]
          - Rows 1..N: candidates [run_idx, row_idx, packed_row(24)]
    """
    ensure_ready()
    table_slot = int(table_slot)
    n_runs = int(n_runs)
    limit = int(limit)
    top_base_keep = int(top_base_keep)
    base_budget = int(base_budget)
    fg_budget_end = int(fg_budget_end)

    if n_runs < 0 or n_runs > int(fields.MAX_GA_RUNS):
        raise ValueError(f"n_runs out of range: {n_runs} (MAX_GA_RUNS={fields.MAX_GA_RUNS})")
    if table_slot < 0 or table_slot >= int(fields.MAX_SONG_SLOTS):
        raise ValueError(f"table_slot out of range: {table_slot} (MAX_SONG_SLOTS={fields.MAX_SONG_SLOTS})")

    if limit < 0:
        limit = 0
    if limit > int(fields.GA_FG_SELECTED_MAX):
        limit = int(fields.GA_FG_SELECTED_MAX)

    perf = str(os.environ.get("PERF_TIMING", "0") or "").strip().lower() in {"1", "true", "yes", "on"}
    t_total = time.perf_counter() if perf else 0.0

    # Select coordinates on GPU, then copy only the selected candidates into a bounded staging field.
    kernels.ga_select_fg_candidates_coords_kernel(
        int(table_slot),
        int(n_runs),
        int(limit),
        int(top_base_keep),
        int(base_budget),
        int(fg_budget_end),
    )

    if limit <= 256:
        out_field = fields.ga_fg_selected_payload_staging_256
    elif limit <= 1024:
        out_field = fields.ga_fg_selected_payload_staging_1024
    else:
        out_field = fields.ga_fg_selected_payload_staging_5000

    kernels.ga_copy_fg_selected_payload_to_download_staging_kernel(int(table_slot), int(n_runs), out_field)
    out = out_field.to_numpy()

    selected_n = 0
    try:
        selected_n = int(out[0, 0])
    except Exception:
        selected_n = 0
    if selected_n < 0:
        selected_n = 0
    max_rows = int(out.shape[0]) - 1
    if selected_n > max_rows:
        selected_n = max_rows

    view = out[: selected_n + 1, :]

    total_ms = (time.perf_counter() - t_total) * 1000.0 if perf else 0.0
    if perf:
        try:
            view_bytes = int(getattr(view, "nbytes", 0) or 0)
            out_bytes = int(getattr(out, "nbytes", 0) or 0)
        except Exception:
            view_bytes = 0
            out_bytes = 0
        print(
            "[PERF][GADownloadGaFgSelected] "
            f"slot={table_slot} runs={n_runs} limit={limit} total={total_ms:.1f}ms "
            f"view_bytes={view_bytes} transfer_bytes={out_bytes}"
        )

    if view.dtype == np.int32 and view.flags["C_CONTIGUOUS"]:
        return view
    return np.ascontiguousarray(view, dtype=np.int32)


def ga_stage_genome_base_stats_from_fg_candidates_table(
    *,
    table_slot: int,
    coords: np.ndarray,
    n_slots: int = 9,
) -> int:
    """
    Stage `fields.genome_base_stats[0:n]` from the GA->FG candidate table (GPU->GPU copy).

    Args:
        table_slot: Candidate table slot (usually song_slot).
        coords: (n, 2) int32 array of (run_idx, row_idx) into the candidate table.
        n_slots: Expected 9.

    Returns:
        n (number of staged genomes)
    """
    ensure_ready()
    table_slot = int(table_slot)
    n_slots = int(n_slots)
    if n_slots != 9:
        raise ValueError(f"Expected n_slots=9, got {n_slots}")
    if table_slot < 0 or table_slot >= int(fields.MAX_SONG_SLOTS):
        raise ValueError(f"table_slot out of range: {table_slot} (MAX_SONG_SLOTS={fields.MAX_SONG_SLOTS})")

    coords = np.asarray(coords, dtype=np.int32)
    if coords.ndim != 2 or int(coords.shape[1]) < 2:
        raise ValueError(f"coords must have shape (n,2), got shape={getattr(coords, 'shape', None)}")
    if not coords.flags["C_CONTIGUOUS"]:
        coords = np.ascontiguousarray(coords, dtype=np.int32)
    n = int(coords.shape[0])
    if n <= 0:
        return 0
    if n > int(fields.MAX_GENOMES):
        raise ValueError(f"Too many genomes to stage: {n} > {fields.MAX_GENOMES}")

    kernels.ga_stage_genome_base_stats_from_fg_candidates_table_kernel(int(table_slot), int(n), int(n_slots), coords)
    return int(n)


# ============================================================================
# GPU-SIDE GLOBAL BEST TRACKING
# ============================================================================


def ga_init_global_best() -> None:
    """
    Initialize global best tracking at the start of a GA run.

    Resets ga_global_best_score to -1 (no best yet).
    Call this once at the start of each GA run.
    """
    ensure_ready()
    kernels.ga_init_global_best_kernel()


def ga_update_global_best(n_genomes: int, n_slots: int = 9) -> None:
    """
    Update global best genome on GPU if current generation has a better score.

    Atomically tracks the best genome across all generations on GPU,
    avoiding expensive per-generation CPU downloads.

    Call this after each ga_evaluate_population() call.

    Args:
        n_genomes: Number of genomes to check
        n_slots: Number of equipment slots per genome
    """
    ensure_ready()
    kernels.ga_update_global_best_kernel(int(n_genomes), int(n_slots))


def ga_download_global_best() -> tuple[int, np.ndarray, np.ndarray]:
    """
    Download the global best genome and results from GPU.

    Returns:
        Tuple of (best_score, best_genome_ids, best_results):
        - best_score: int - the best score found across all generations
        - best_genome_ids: np.ndarray (n_slots,) int32 - item IDs of best genome
        - best_results: np.ndarray (7,) int32 - [score, ft, ff, pp, cm, fm, ov]
    """
    ensure_ready()
    # Pack into single field then download once (1 GPU sync instead of 3)
    # Layout: [score(1), genome_ids(9), results(7)] = 17 values
    kernels.ga_pack_global_best_kernel()
    packed = fields.ga_global_best_packed.to_numpy()
    best_score = int(packed[0])
    best_genome_ids = packed[1:10].copy()
    best_results = packed[10:17].copy()
    return best_score, best_genome_ids, best_results


def ga_upload_island_boundaries(island_starts: np.ndarray) -> None:
    """
    Upload island boundary indices to GPU for island-based elitism.

    Args:
        island_starts: (n_islands + 1,) int32 array of island boundaries.
                      Format: [start0, start1, ..., end_last]
                      Island i owns indices [start[i], start[i+1])
    """
    global _ISLAND_BOUNDARIES_CACHE

    ensure_ready()
    n = min(len(island_starts), fields.MAX_ISLANDS + 1)
    key = tuple(int(x) for x in np.asarray(island_starts[:n], dtype=np.int32))
    if _ISLAND_BOUNDARIES_CACHE == key:
        return

    buf = np.zeros(fields.MAX_ISLANDS + 1, dtype=np.int32)
    buf[:n] = np.asarray(island_starts[:n], dtype=np.int32)
    fields.island_boundaries.from_numpy(buf)
    _ISLAND_BOUNDARIES_CACHE = key


def ga_find_island_elites(n_genomes: int, n_islands: int, elites_per_island: int) -> None:
    """
    GPU-side island elite selection: find top-k genomes per island.

    This replaces the CPU-side score download + argsort previously used.
    Must call ga_upload_island_boundaries() first.

    After calling, elite indices are available in island_elite_indices field.
    Use ga_download_island_elite_indices() to retrieve them if needed.

    Args:
        n_genomes: Total population size
        n_islands: Number of islands
        elites_per_island: Number of elites to select per island
    """
    ensure_ready()
    kernels.ga_find_island_elites_kernel(int(n_genomes), int(n_islands), int(elites_per_island))


def ga_download_island_elite_indices(n_elites: int) -> np.ndarray:
    """
    Download the elite genome indices computed by ga_find_island_elites.

    Args:
        n_elites: Total number of elites (n_islands * elites_per_island)

    Returns:
        np.ndarray: (n_elites,) int32 array of elite genome indices
    """
    ensure_ready()
    out = fields.island_elite_indices.to_numpy()
    return np.asarray(out[:n_elites], dtype=np.int32)


def ga_island_migration(n_genomes: int, n_islands: int, migrate_count: int, n_slots: int = 9) -> None:
    """
    GPU-side island migration using ring topology.

    Migrates top-k genomes from each island to the next island (ring topology),
    replacing the worst-k genomes in the destination. This eliminates the expensive
    CPU round-trip (download scores, download population, upload patched population)
    that was previously required for migration.

    Prerequisites:
    - Call ga_upload_island_boundaries() first
    - ga_scores must be populated from evaluation

    Args:
        n_genomes: Total population size
        n_islands: Number of islands
        migrate_count: Number of genomes to migrate per island (max 8)
        n_slots: Number of equipment slots per genome (default 9)
    """
    ensure_ready()
    kernels.ga_island_migration_kernel(int(n_genomes), int(n_islands), int(migrate_count), int(n_slots))


def ga_island_migration_runs(
    *, n_runs: int, n_genomes_per_run: int, n_islands: int, migrate_count: int, n_slots: int = 9
) -> None:
    """
    GPU-side island migration using ring topology for multiple independent runs.
    """
    ensure_ready()
    n_runs = int(n_runs)
    n_genomes_per_run = int(n_genomes_per_run)
    n_islands = int(n_islands)
    migrate_count = int(migrate_count)
    n_slots = int(n_slots)
    if n_runs <= 0 or n_genomes_per_run <= 0:
        return
    if n_slots <= 0 or n_slots > fields.MAX_SLOTS:
        raise ValueError(f"Invalid n_slots: {n_slots}")
    n_total = n_runs * n_genomes_per_run
    if n_total > fields.MAX_GENOMES:
        raise ValueError(f"Batch too large for MAX_GENOMES: {n_total} > {fields.MAX_GENOMES}")
    kernels.ga_island_migration_runs_kernel(n_runs, n_genomes_per_run, n_islands, migrate_count, n_slots)


_GA_KERNELS_WARMED = False
_GA_KERNELS_LIGHT_WARMED = False


def warmup_ga_kernels() -> None:
    """
    Best-effort Taichi JIT warmup for GPU-native GA kernels.

    Goal: avoid the first real GA request paying multi-second compilation latency on Vulkan,
    which shows up as a \"GPU idle\" gap in high-level monitoring and can create bursty
    utilization graphs.

    Notes:
    - Uses tiny dummy inputs (correctness is irrelevant; outputs are discarded).
    - Idempotent: safe to call multiple times.
    """
    global _GA_KERNELS_WARMED
    if _GA_KERNELS_WARMED:
        return

    ensure_ready()

    # Minimal sizes that still exercise the full GA pipeline (evaluate -> next-gen -> pack -> select).
    n_slots = 9
    n_runs = 1
    n_genomes_per_run = min(64, int(getattr(fields, "MAX_GA_RUN_GENOMES", 250) or 250))
    if n_genomes_per_run < 1:
        n_genomes_per_run = 1
    n_total = int(n_runs) * int(n_genomes_per_run)
    if n_total > int(fields.MAX_GENOMES):
        n_genomes_per_run = max(1, int(fields.MAX_GENOMES))
        n_total = int(n_runs) * int(n_genomes_per_run)

    # Small but non-zero budget so combo tables are populated and the FT/FF kernels are exercised.
    total_budget = 1
    gem_scale_fever = 3
    song_slot = 0

    # Ensure per-slot item ranges are valid (avoid divide-by-zero in mutation/immigrant ops).
    item_stats_np = np.zeros((1, fields.ITEM_STAT_DIM), dtype=np.int32)
    slot_start_np = np.zeros((fields.MAX_SLOTS,), dtype=np.int32)
    slot_count_np = np.ones((fields.MAX_SLOTS,), dtype=np.int32)
    ga_upload_item_stats(item_stats_np, slot_start_np, slot_count_np)
    ga_upload_base_fixed_stats(np.zeros((fields.ITEM_STAT_DIM,), dtype=np.int32))

    # Upload a trivial island boundary table so island-based kernels have valid ranges.
    n_islands = 2
    if n_islands > int(getattr(fields, "MAX_ISLANDS", n_islands) or n_islands):
        n_islands = int(getattr(fields, "MAX_ISLANDS", 1) or 1)
    if n_islands < 1:
        n_islands = 1
    # Boundaries: [0, mid, end] for 2 islands (or [0,end] for 1 island)
    if n_islands == 1:
        boundaries = np.array([0, int(n_total)], dtype=np.int32)
    else:
        mid = int(n_total // 2)
        boundaries = np.array([0, mid, int(n_total)], dtype=np.int32)
    ga_upload_island_boundaries(boundaries)

    # Stage a single-run initial population and seed RNG.
    pops = np.zeros((n_runs, n_genomes_per_run, n_slots), dtype=np.int32)
    ga_upload_initial_populations(pops, n_runs=n_runs, n_genomes=n_genomes_per_run, n_slots=n_slots)
    ga_load_initial_populations_batch(
        run_idx_start=0, n_runs=n_runs, n_genomes_per_run=n_genomes_per_run, n_slots=n_slots
    )
    ga_seed_rng_runs(n_runs=n_runs, n_genomes_per_run=n_genomes_per_run, seed=12345)

    # Initialize + run a minimal 1-generation evaluation.
    ga_init_runs_best(run_idx_start=0, n_runs=n_runs, n_slots=n_slots)
    ga_init_global_best()
    ga_evaluate_population(
        n_total,
        n_slots=n_slots,
        total_budget=total_budget,
        gem_scale_fever=gem_scale_fever,
        song_slot=song_slot,
        use_hints=0,
        materialize_mode="store_hints",
    )
    # Compile the warm-start (`use_hints=1`) specialization too; this path dominates
    # real runs after Gen 0 and otherwise incurs a first-hit JIT spike.
    ga_evaluate_population(
        n_total,
        n_slots=n_slots,
        total_budget=total_budget,
        gem_scale_fever=gem_scale_fever,
        song_slot=song_slot,
        use_hints=1,
        materialize_mode="update_global",
    )
    try:
        # Best-effort: ensure the global-best pack/download kernels are JIT'd too.
        _ = ga_download_global_best()
    except Exception:
        pass
    ga_update_runs_best(run_idx_start=0, n_runs=n_runs, n_genomes_per_run=n_genomes_per_run, n_slots=n_slots)

    # Warm migration + fused next-gen kernels (typical path in GPU-native GA).
    ga_island_migration_runs(
        n_runs=n_runs,
        n_genomes_per_run=n_genomes_per_run,
        n_islands=n_islands,
        migrate_count=1,
        n_slots=n_slots,
    )
    ga_next_generation_fused_runs(
        n_runs=n_runs,
        n_genomes_per_run=n_genomes_per_run,
        n_slots=n_slots,
        mutation_rate=0.0,
        immigrant_rate=0.0,
        tournament_k=1,
        n_islands=n_islands,
        elites_per_island=1,
    )

    # Warm GA->FG packing + GPU-side selection/download kernels.
    ga_pack_fg_candidates_table_segmented(
        table_slot=song_slot,
        run_idx_start=0,
        n_runs=n_runs,
        n_genomes_per_run=n_genomes_per_run,
        n_slots=n_slots,
    )
    # limit=1 keeps the staging download small while still exercising the kernels.
    _ = ga_download_fg_selected_payload(
        table_slot=song_slot,
        n_runs=n_runs,
        limit=1,
        top_base_keep=1,
        base_budget=1,
        fg_budget_end=1,
    )

    _GA_KERNELS_WARMED = True


def warmup_ga_kernels_light() -> None:
    """
    Lightweight per-process warmup for GPU-native GA kernels.

    This is intentionally smaller than `warmup_ga_kernels()`:
    - It targets the per-process first-hit JIT/loading costs for the kernels that dominate GA runtime
      (evaluate cold+warm, plus fused next-gen and initial population generation).
    - It avoids downloads and GA->FG packing/selection to keep runtime bounded.

    This is useful when offline caches are already built and we just want to avoid the first real GA
    request paying a multi-second spike (which can skew phase-timing profiles).

    Notes:
    - Outputs are discarded; correctness is irrelevant.
    - Idempotent per process.
    """
    global _GA_KERNELS_LIGHT_WARMED
    if _GA_KERNELS_LIGHT_WARMED or _GA_KERNELS_WARMED:
        return

    ensure_ready()

    import taichi as ti

    n_slots = 9
    n_genomes = min(64, int(getattr(fields, "MAX_GA_RUN_GENOMES", 250) or 250))
    if n_genomes < 1:
        n_genomes = 1
    n_genomes = min(int(n_genomes), int(fields.MAX_GENOMES))

    # Small but non-zero budget so combo tables are populated and the FT/FF kernels are exercised.
    total_budget = 1
    gem_scale_fever = 3
    song_slot = 0

    item_stats_np = np.zeros((1, fields.ITEM_STAT_DIM), dtype=np.int32)
    slot_start_np = np.zeros((fields.MAX_SLOTS,), dtype=np.int32)
    slot_count_np = np.ones((fields.MAX_SLOTS,), dtype=np.int32)
    ga_upload_item_stats(item_stats_np, slot_start_np, slot_count_np)
    ga_upload_base_fixed_stats(np.zeros((fields.ITEM_STAT_DIM,), dtype=np.int32))

    ga_upload_island_boundaries(np.array([0, int(n_genomes)], dtype=np.int32))
    pop = np.zeros((int(n_genomes), int(n_slots)), dtype=np.int32)
    ga_upload_population_indices(pop, n_slots=int(n_slots))

    ga_init_global_best()

    # Compile/load both evaluation template paths (cold + warm).
    ga_evaluate_population(
        int(n_genomes),
        n_slots=n_slots,
        total_budget=total_budget,
        gem_scale_fever=gem_scale_fever,
        song_slot=song_slot,
        use_hints=0,
        materialize_mode="update_global",
    )
    ti.sync()
    ga_evaluate_population(
        int(n_genomes),
        n_slots=n_slots,
        total_budget=total_budget,
        gem_scale_fever=gem_scale_fever,
        song_slot=song_slot,
        use_hints=1,
        materialize_mode="update_global",
    )
    ti.sync()

    # Warm the common GPU-generated population path (used when CPU prebuilt pops are absent).
    try:
        ga_generate_initial_populations(
            run_idx_start=0, n_runs=1, n_genomes=int(n_genomes), n_slots=n_slots, seed=12345
        )
        ti.sync()
    except Exception:
        pass

    # Warm fused next-gen path (single-run).
    try:
        ga_next_generation_fused(
            n_genomes=int(n_genomes),
            n_slots=n_slots,
            mutation_rate=0.0,
            immigrant_rate=0.0,
            tournament_k=1,
            n_islands=1,
            elites_per_island=1,
        )
        ti.sync()
    except Exception:
        pass

    _GA_KERNELS_LIGHT_WARMED = True
