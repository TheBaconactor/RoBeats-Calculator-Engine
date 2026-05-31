"""
API GA Operations - GPU-native genetic algorithm operators.
This module provides GPU-side GA operators (selection, crossover, mutation, evaluation):
- ga_upload_item_stats: Upload item stats and slot pools
- ga_upload_base_fixed_stats: Upload fixed base stats
- ga_generate_initial_populations / ga_load_initial_populations_batch: stage multi-run GA inputs
- ga_prepare_population_base_stats / ga_evaluate_prepared_population: exact GPU evaluation
These functions are called from the GPU executor's native in-flight path.
"""
from __future__ import annotations
import time
import logging
from types import SimpleNamespace
import numpy as np
from gear_optimizer.core.parsing import env_flag
try:
    from .. import fields
    from ..fields import MAX_EVALS_PER_DISPATCH
    from ..kernel_loader import get_kernels
    from .initialization import ensure_ready, _ensure_ftff_combo_tables
except ModuleNotFoundError as exc:  # pragma: no cover - CPU-only import/test path
    if exc.name != "taichi":
        raise
    fields = SimpleNamespace(
        MAX_EVALS_PER_DISPATCH=4_194_304,
        MAX_GENOMES=4096,
        MAX_GA_RUNS=128,
        MAX_GA_RUN_GENOMES=1024,
        ITEM_STAT_DIM=10,
    )
    MAX_EVALS_PER_DISPATCH = int(fields.MAX_EVALS_PER_DISPATCH)
    def ensure_ready(*_args, **_kwargs):
        raise RuntimeError("Taichi is not installed")
    def _ensure_ftff_combo_tables(*_args, **_kwargs):
        raise RuntimeError("Taichi is not installed")
    def get_kernels():
        return SimpleNamespace()
from ..ga_chunking import compute_ga_combo_chunk
from gear_optimizer.core.parsing import env_get
from .common_operations import compute_array_sig, probability_to_u32_fp
logger = logging.getLogger(__name__)
_GA_PLATEAU_PRUNE_ENABLED: int = 0
if env_flag("GPU_NATIVE_GA_PLATEAU_PRUNE"):
    _GA_PLATEAU_PRUNE_ENABLED = 1
_GA_COMBO_CHUNK_MIN: int = max(64, int(env_get("GPU_NATIVE_GA_COMBO_CHUNK_MIN", "1024") or 1024))
_GA_COMBO_CHUNK_MAX: int = max(
    _GA_COMBO_CHUNK_MIN, int(env_get("GPU_NATIVE_GA_COMBO_CHUNK_MAX", "4096") or 4096)
)
_GA_COMBO_TAIL_MERGE_MAX: int = max(0, int(env_get("GPU_NATIVE_GA_COMBO_TAIL_MERGE_MAX", "256") or 256))
_GA_EVAL_BUDGET_RAW: str | None = None
_GA_EVAL_BUDGET: int = int(MAX_EVALS_PER_DISPATCH)
_GA_BASE_STATS_REUSE_RAW: str | None = None
_GA_BASE_STATS_REUSE_ENABLED: int = 0
_GA_EXACT_EVAL_RESULTS_REUSE_RAW: str | None = None
_GA_EXACT_EVAL_RESULTS_REUSE_ENABLED: int = 0
_GA_EXACT_STATS_REUSE_RAW: str | None = None
_GA_EXACT_STATS_REUSE_ENABLED: int = 0
_GA_KERNELS_LIGHT_WARMED: bool = False


def _warmup_ref_arrays() -> dict[str, np.ndarray]:
    x = np.linspace(0.0, 1.0, int(fields.GRID_SIZE), dtype=np.float32)
    return {
        "Perfect Points": (1000.0 + (500.0 * x)).astype(np.float32, copy=False),
        "Combo Multiplier": (1.0 + x).astype(np.float32, copy=False),
        "Fever Multiplier": (1.0 + (0.5 * x)).astype(np.float32, copy=False),
        "Fever Time": (5.0 + (30.0 * x)).astype(np.float32, copy=False),
        "Fever Fill Rate": (1.0 + (4.0 * x)).astype(np.float32, copy=False),
    }


def _warmup_calc_song() -> dict:
    timestamps = np.linspace(0.0, 18.0, 48, dtype=np.float32)
    note_types = np.zeros((timestamps.shape[0],), dtype=np.int32)
    return {
        "metadata": {
            "Song Name": "__ga_live_request_warmup__",
            "Difficulty": "Warmup",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]) if timestamps.size else 0.0,
        },
        "song_data": {
            "timestamps": timestamps,
            "chart_timestamps": timestamps,
            "note_types": note_types,
        },
    }


def warmup_ga_kernels_light() -> None:
    """Warm the production-shaped GPU-native GA request path before real songs run."""
    global _GA_KERNELS_LIGHT_WARMED
    if _GA_KERNELS_LIGHT_WARMED:
        return

    import taichi as ti

    from .timeline import precompute_timeline_gpu

    n_slots = 9
    n_runs = min(3, int(fields.MAX_GA_RUNS))
    n_genomes = min(705, int(fields.MAX_GA_RUN_GENOMES), int(fields.MAX_GENOMES))
    n_genomes = max(1, int(n_genomes))
    n_runs = max(1, min(int(n_runs), max(1, int(fields.MAX_GENOMES) // int(n_genomes))))
    total_budget = min(90, int(fields.MAX_TOTAL_BUDGET))
    gem_scale_fever = 3
    song_slot = 0

    ref_arrays = _warmup_ref_arrays()
    ensure_ready(ref_arrays)
    precompute_timeline_gpu(_warmup_calc_song(), ref_arrays, song_slot=song_slot)

    item_stats_np = np.zeros((1, fields.ITEM_STAT_DIM), dtype=np.int32)
    slot_start_np = np.zeros((fields.MAX_SLOTS,), dtype=np.int32)
    slot_count_np = np.ones((fields.MAX_SLOTS,), dtype=np.int32)
    ga_upload_item_stats(item_stats_np, slot_start_np, slot_count_np)
    ga_upload_base_fixed_stats(np.zeros((fields.ITEM_STAT_DIM,), dtype=np.int32))
    ga_upload_initial_populations(
        np.zeros((int(n_runs), int(n_genomes), int(n_slots)), dtype=np.int32),
        n_runs=int(n_runs),
        n_genomes=int(n_genomes),
        n_slots=int(n_slots),
    )
    ga_load_initial_populations_batch(
        run_idx_start=0,
        n_runs=int(n_runs),
        n_genomes_per_run=int(n_genomes),
        n_slots=int(n_slots),
    )
    ga_seed_rng_runs(n_runs=int(n_runs), n_genomes_per_run=int(n_genomes), seed=12345)
    ga_init_runs_best(run_idx_start=0, n_runs=int(n_runs), n_slots=int(n_slots))
    ga_prepare_population_base_stats(
        n_genomes=int(n_runs) * int(n_genomes),
        n_slots=n_slots,
    )
    ga_evaluate_prepared_population(
        int(n_runs) * int(n_genomes),
        n_slots=n_slots,
        total_budget=total_budget,
        gem_scale_fever=gem_scale_fever,
        song_slot=song_slot,
    )
    ga_refresh_scores_update_runs_best_and_next_generation_fused_runs(
        run_idx_start=0,
        n_runs=int(n_runs),
        n_genomes_per_run=int(n_genomes),
        n_slots=int(n_slots),
        total_budget=total_budget,
        gem_scale_fever=gem_scale_fever,
        song_slot=song_slot,
        mutation_rate=0.0,
        immigrant_rate=0.0,
        tournament_k=1,
        n_islands=1,
        elites_per_island=1,
    )
    ga_pack_fg_candidates_table_segmented(
        table_slot=song_slot,
        run_idx_start=0,
        n_runs=int(n_runs),
        n_genomes_per_run=int(n_genomes),
        n_slots=n_slots,
        total_budget=total_budget,
        gem_scale_fever=gem_scale_fever,
        song_slot=song_slot,
    )
    _ = ga_download_fg_selected_payload(table_slot=song_slot, n_runs=int(n_runs), limit=1)
    ti.sync()
    _GA_KERNELS_LIGHT_WARMED = True
def _ga_eval_budget() -> int:
    global _GA_EVAL_BUDGET_RAW, _GA_EVAL_BUDGET
    raw = env_get("GPU_NATIVE_GA_EVAL_BUDGET", None)
    raw_norm = str(raw or "").strip()
    if raw_norm == _GA_EVAL_BUDGET_RAW:
        return int(_GA_EVAL_BUDGET)
    _GA_EVAL_BUDGET_RAW = raw_norm
    if raw_norm == "":
        _GA_EVAL_BUDGET = int(MAX_EVALS_PER_DISPATCH)
        return int(_GA_EVAL_BUDGET)
    try:
        val = int(raw_norm)
    except Exception as e:
        logger.debug(f"ga_operations:_ga_eval_budget: {e}")
        _GA_EVAL_BUDGET = int(MAX_EVALS_PER_DISPATCH)
        return int(_GA_EVAL_BUDGET)
    _GA_EVAL_BUDGET = max(64, min(int(MAX_EVALS_PER_DISPATCH), int(val)))
    return int(_GA_EVAL_BUDGET)
def _ga_exact_genome_base_stats_reuse_enabled() -> int:
    global _GA_BASE_STATS_REUSE_RAW, _GA_BASE_STATS_REUSE_ENABLED
    raw = env_get("GPU_NATIVE_GA_BASE_STATS_REUSE", None)
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
    raw = env_get("GPU_NATIVE_GA_EXACT_EVAL_RESULTS_REUSE", None)
    if raw is None:
        raw = env_get("GPU_NATIVE_GA_EXACT_EVAL_REUSE", None)
    raw_norm = str(raw or "").strip().lower()
    if raw_norm == _GA_EXACT_EVAL_RESULTS_REUSE_RAW:
        return int(_GA_EXACT_EVAL_RESULTS_REUSE_ENABLED)
    _GA_EXACT_EVAL_RESULTS_REUSE_RAW = raw_norm
    if raw_norm in {"", "0", "false", "no", "off"}:
        _GA_EXACT_EVAL_RESULTS_REUSE_ENABLED = 0
    else:
        _GA_EXACT_EVAL_RESULTS_REUSE_ENABLED = 1
    return int(_GA_EXACT_EVAL_RESULTS_REUSE_ENABLED)
def _ga_exact_genome_stats_signature_reuse_enabled() -> int:
    global _GA_EXACT_STATS_REUSE_RAW, _GA_EXACT_STATS_REUSE_ENABLED
    raw = env_get("GPU_NATIVE_GA_EXACT_STATS_REUSE", None)
    if raw is None:
        raw = env_get("GPU_NATIVE_GA_SCORE_SIGNATURE_REUSE", None)
    raw_norm = str(raw or "").strip().lower()
    if raw_norm == _GA_EXACT_STATS_REUSE_RAW:
        return int(_GA_EXACT_STATS_REUSE_ENABLED)
    _GA_EXACT_STATS_REUSE_RAW = raw_norm
    if raw_norm in {"0", "false", "no", "off"}:
        _GA_EXACT_STATS_REUSE_ENABLED = 0
    else:
        _GA_EXACT_STATS_REUSE_ENABLED = 1
    return int(_GA_EXACT_STATS_REUSE_ENABLED)
kernels = get_kernels()
_ITEM_STATS_CACHE: dict = {"sig": None, "n_items": None, "array_id": None, "slot_start_id": None, "slot_count_id": None}
_BASE_FIXED_STATS_CACHE: tuple | None = None
def reset_ga_upload_caches() -> None:
    """Reset upload caches after ti.reset() or when switching songs."""
    global _ITEM_STATS_CACHE, _BASE_FIXED_STATS_CACHE
    _ITEM_STATS_CACHE = {"sig": None, "n_items": None, "array_id": None, "slot_start_id": None, "slot_count_id": None}
    _BASE_FIXED_STATS_CACHE = None
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
    seed: int,
    heuristic_prob: float = 0.0,
    heuristic_k: int = 0,
    heuristic_copies: int = 0,
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
    heuristic_prob_fp = probability_to_u32_fp(heuristic_prob)
    heuristic_k = int(heuristic_k)
    if heuristic_k < 0:
        heuristic_k = 0
    k_field = int(getattr(fields, "GA_INIT_HEURISTIC_K", heuristic_k) or 0)
    if k_field <= 0:
        heuristic_k = 0
    else:
        heuristic_k = min(int(heuristic_k), int(k_field))
    heuristic_copies = int(heuristic_copies)
    heuristic_copies = max(0, min(heuristic_copies, n_genomes))
    kernels.ga_generate_initial_populations_kernel(
        int(run_idx_start),
        int(n_runs),
        int(n_genomes),
        int(n_slots),
        np.uint32(int(seed) & 0xFFFFFFFF),
        heuristic_prob_fp,
        int(heuristic_k),
        int(heuristic_copies),
    )
def ga_seed_rng_runs(*, n_runs: int, n_genomes_per_run: int, seed: int) -> None:
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
    try:
        if (
            _ITEM_STATS_CACHE.get("n_items") == n_items
            and _ITEM_STATS_CACHE.get("array_id") == id(item_stats_np)
            and _ITEM_STATS_CACHE.get("slot_start_id") == id(slot_start_np)
            and _ITEM_STATS_CACHE.get("slot_count_id") == id(slot_count_np)
        ):
            return n_items
    except Exception as e:
        logger.debug(f"ga_operations:ga_upload_item_stats: {e}")
    sig = compute_array_sig(
        np.asarray(item_stats_np[:n_items, : fields.ITEM_STAT_DIM], dtype=np.int32),
        np.asarray(slot_start_np, dtype=np.int32),
        np.asarray(slot_count_np, dtype=np.int32),
    )
    if _ITEM_STATS_CACHE.get("sig") == sig:
        _ITEM_STATS_CACHE["n_items"] = n_items
        _ITEM_STATS_CACHE["array_id"] = id(item_stats_np)
        _ITEM_STATS_CACHE["slot_start_id"] = id(slot_start_np)
        _ITEM_STATS_CACHE["slot_count_id"] = id(slot_count_np)
        return n_items  # Already uploaded
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
    key = tuple(int(x) for x in base_stats_np[: fields.ITEM_STAT_DIM])
    if _BASE_FIXED_STATS_CACHE == key:
        return  # Already uploaded
    ensure_ready()
    buf = np.zeros(fields.ITEM_STAT_DIM, dtype=np.int32)
    buf[: len(base_stats_np)] = np.asarray(base_stats_np, dtype=np.int32)
    fields.base_fixed_stats.from_numpy(buf)
    _BASE_FIXED_STATS_CACHE = key
def ga_prepare_population_base_stats(
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
    Aggregate the active population into `genome_base_stats` and initialize exact-eval state.
    """
    ensure_ready()
    n_genomes = int(n_genomes)
    n_slots = int(n_slots)
    exact_genome_base_stats_reuse = bool(_ga_exact_genome_base_stats_reuse_enabled())
    exact_genome_eval_results_reuse = bool(_ga_exact_genome_eval_results_reuse_enabled())
    exact_genome_stats_signature_reuse = bool(_ga_exact_genome_stats_signature_reuse_enabled())
    if exact_genome_base_stats_reuse or (exact_genome_eval_results_reuse and not exact_genome_stats_signature_reuse):
        kernels.ga_build_exact_eval_reuse_map_kernel(int(n_genomes), int(n_slots))
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
    if exact_genome_stats_signature_reuse:
        kernels.ga_build_exact_eval_reuse_map_from_base_stats_kernel(int(n_genomes))
def ga_evaluate_prepared_population(
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
) -> None:
    """
    Evaluate a population whose `genome_base_stats` were already aggregated.
    This is the main GA evaluation function for GPU-native mode. It:
    PREREQUISITES:
    - Load the active multi-run batch with ga_load_initial_populations_batch()
    - Call ga_upload_item_stats() with item stats and slot pools
    - Call ga_upload_base_fixed_stats() with base stats
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
        raise ValueError("GA evaluation requires exact inner GPU solving.")
    exact_genome_eval_results_reuse = bool(_ga_exact_genome_eval_results_reuse_enabled())
    exact_genome_stats_signature_reuse = bool(_ga_exact_genome_stats_signature_reuse_enabled())
    total_budget_i = int(total_budget)
    gem_scale_fever_i = int(gem_scale_fever)
    song_slot_i = int(song_slot)
    prune_plateaus_i = _GA_PLATEAU_PRUNE_ENABLED
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
            int(prune_plateaus_i),
            use_exact_inner_solver_i,
            int(exact_genome_eval_results_reuse or exact_genome_stats_signature_reuse),
        )
        kernels.ga_finalize_warmstart_lane_best_kernel(n_genomes)
        offset += int(chunk_len)
    if exact_genome_eval_results_reuse or exact_genome_stats_signature_reuse:
        kernels.ga_propagate_exact_eval_reuse_chunk_best_kernel(int(n_genomes))
def _validate_ga_runs_batch(
    *, run_idx_start: int, n_runs: int, n_genomes_per_run: int, n_slots: int
) -> tuple[int, int, int, int]:
    run_idx_start = int(run_idx_start)
    n_runs = int(n_runs)
    n_genomes_per_run = int(n_genomes_per_run)
    n_slots = int(n_slots)
    if n_runs <= 0 or n_genomes_per_run <= 0:
        return run_idx_start, n_runs, n_genomes_per_run, n_slots
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
    return run_idx_start, n_runs, n_genomes_per_run, n_slots
def ga_refresh_scores_and_update_runs_best(
    *,
    run_idx_start: int,
    n_runs: int,
    n_genomes_per_run: int,
    n_slots: int,
    total_budget: int,
    gem_scale_fever: int,
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
    use_exact_inner_solver: bool = True,
) -> None:
    """
    Lightweight live-score refresh for packed multi-run GA execution.
    This keeps `ga_scores` exact from the reduction state and updates each run's row 0 best
    with exact materialization only when that run improves. It avoids the full-pop
    `genome_result_stats` write pass that the final FG packing path no longer needs every
    generation.
    """
    ensure_ready()
    run_idx_start, n_runs, n_genomes_per_run, n_slots = _validate_ga_runs_batch(
        run_idx_start=run_idx_start,
        n_runs=n_runs,
        n_genomes_per_run=n_genomes_per_run,
        n_slots=n_slots,
    )
    if n_runs <= 0 or n_genomes_per_run <= 0:
        return
    kernels.ga_refresh_scores_and_update_runs_best_kernel(
        int(run_idx_start),
        int(n_runs),
        int(n_genomes_per_run),
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
    novelty_repair_attempts: int = 0,
) -> None:
    """
    FULLY FUSED next generation for multiple independent runs packed contiguously.
    Executes:
    1) ga_next_generation_full_runs_kernel (select+crossover+mutate+elitism within each run)
    2) ga_swap_population_kernel (swap) for the combined population
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
    novelty_repair_attempts = max(0, min(4, int(novelty_repair_attempts)))
    n_total = n_runs * n_genomes_per_run
    if n_total > fields.MAX_GENOMES:
        raise ValueError(f"Batch too large for MAX_GENOMES: {n_total} > {fields.MAX_GENOMES}")
    mr_fp = probability_to_u32_fp(float(mutation_rate))
    ir_fp = probability_to_u32_fp(float(immigrant_rate))
    kernels.ga_next_generation_full_runs_kernel(
        n_runs,
        n_genomes_per_run,
        n_slots,
        n_islands,
        elites_per_island,
        tournament_k,
        mr_fp,
        ir_fp,
        int(novelty_repair_attempts),
    )
    kernels.ga_swap_population_kernel(int(n_total), n_slots)
def ga_refresh_scores_update_runs_best_and_next_generation_fused_runs(
    *,
    run_idx_start: int,
    n_runs: int,
    n_genomes_per_run: int,
    n_slots: int = 9,
    total_budget: int,
    gem_scale_fever: int,
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
    use_exact_inner_solver: bool = True,
    mutation_rate: float = 0.02,
    immigrant_rate: float = 0.0,
    tournament_k: int = 3,
    n_islands: int = 1,
    elites_per_island: int = 1,
    novelty_repair_attempts: int = 0,
) -> None:
    """
    Fused packed multi-run transition.
    This is the non-final, non-migration companion to:
    `ga_refresh_scores_and_update_runs_best()` followed by `ga_next_generation_fused_runs()`.
    It preserves row-0 run best before mutating the population, then swaps the next generation in.
    """
    ensure_ready()
    run_idx_start, n_runs, n_genomes_per_run, n_slots = _validate_ga_runs_batch(
        run_idx_start=run_idx_start,
        n_runs=n_runs,
        n_genomes_per_run=n_genomes_per_run,
        n_slots=n_slots,
    )
    if n_runs <= 0 or n_genomes_per_run <= 0:
        return
    n_islands = int(n_islands)
    elites_per_island = int(elites_per_island)
    tournament_k = int(tournament_k)
    if n_islands < 1:
        n_islands = 1
    if elites_per_island < 0:
        elites_per_island = 0
    if tournament_k < 1:
        tournament_k = 1
    novelty_repair_attempts = max(0, min(4, int(novelty_repair_attempts)))
    mr_fp = probability_to_u32_fp(float(mutation_rate))
    ir_fp = probability_to_u32_fp(float(immigrant_rate))
    kernels.ga_refresh_scores_update_runs_best_and_next_generation_full_runs_kernel(
        int(run_idx_start),
        int(n_runs),
        int(n_genomes_per_run),
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
        int(n_islands),
        int(elites_per_island),
        int(tournament_k),
        mr_fp,
        ir_fp,
        int(novelty_repair_attempts),
    )
    kernels.ga_swap_population_kernel(int(n_runs) * int(n_genomes_per_run), int(n_slots))
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
def ga_pack_fg_candidates_table_segmented(
    *,
    table_slot: int,
    run_idx_start: int,
    n_runs: int,
    n_genomes_per_run: int,
    n_slots: int = 9,
    total_budget: int,
    gem_scale_fever: int,
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
    use_exact_inner_solver: bool = True,
) -> None:
    """
    Pack a compact GA->FG candidate table for packed multi-run execution.
    This is the canonical compact GA->FG handoff; full population downloads are not part of the production route.
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
def ga_download_fg_selected_payload(
    *,
    table_slot: int,
    n_runs: int,
    limit: int,
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
    if n_runs < 0 or n_runs > int(fields.MAX_GA_RUNS):
        raise ValueError(f"n_runs out of range: {n_runs} (MAX_GA_RUNS={fields.MAX_GA_RUNS})")
    if table_slot < 0 or table_slot >= int(fields.MAX_SONG_SLOTS):
        raise ValueError(f"table_slot out of range: {table_slot} (MAX_SONG_SLOTS={fields.MAX_SONG_SLOTS})")
    if limit < 0:
        limit = 0
    if limit > int(fields.GA_FG_SELECTED_MAX):
        limit = int(fields.GA_FG_SELECTED_MAX)
    perf = env_flag("PERF_TIMING")
    t_total = time.perf_counter() if perf else 0.0
    kernels.ga_select_top_base_fg_candidate_coords_kernel(
        int(table_slot),
        int(n_runs),
        int(limit),
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
    except Exception as e:
        logger.debug(f"ga_operations:ga_download_fg_selected_payload: {e}")
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
        except Exception as e:
            logger.debug(f"ga_operations:ga_download_fg_selected_payload: {e}")
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
