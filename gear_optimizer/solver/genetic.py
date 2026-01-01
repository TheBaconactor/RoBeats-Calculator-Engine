"""
Genetic algorithm solver for gear and mini co-evolution.

This module contains the main GA that optimizes both gear (6 slots) and minis (3 slots)
simultaneously to find optimal loadouts. Uses tournament selection, crossover, mutation,
and memetic local search.

The main function solve_coevolution_genetic() has been refactored to use helper functions
from helpers.ga_helpers for improved modularity and maintainability.
"""

import os
import random
import time

# Support deterministic testing via GA_SEED environment variable
_GA_SEED = os.environ.get("GA_SEED")
if _GA_SEED is not None:
    _GA_SEED = int(_GA_SEED)
    random.seed(_GA_SEED)
    print(f"[GA] Deterministic mode: seed={_GA_SEED}")

from ..core.constants import (
    GA_POPULATION_SIZE,
    GA_MUTATION_RATE,
    GA_ELITISM,
    GEM_SCALE_NORMAL,
    GEM_SCALE_FEVER,
    GEM_STAT_TO_ELEMENT_SCALE,
    ELEMENTAL_GEM_SCALE,
    LOADOUTS_PER_SONG_LIMIT,
    FG_CANDIDATE_LIMIT,
    SKIP_ITEM_KEYS,
    GPU_GA_NUM_ISLANDS,
    GPU_GA_GENS_PER_MIGRATION,
    GPU_GA_MIGRATE_COUNT,
)
from ..core.utils import safe_int, safe_float
from .scoring import worker_coevolution_evaluate, GEM_SOLVER_CACHE, FG_CACHE, FEVER_TIMELINE_CACHE
from ..data.models import GASettings
from ..helpers.ga_helpers import (
    initialize_pools,
    create_genome_functions,
    create_evaluation_functions,
    create_local_search_function,
    build_initial_population,
    perform_crossover_mutation,
    evaluate_population_parallel,
    update_mutation_and_diversity,
    compute_dynamic_mutation,
)
from ..helpers.song_helpers.fg_candidate_selector import select_fg_candidates
from ..helpers.song_helpers.fg_combo_booster import (
    build_fg_beam_booster_candidates,
    build_fg_combo_booster_candidates,
    hydrate_fg_candidate_stats,
)

# Optional: GPU-native GA imports (only loaded if needed)
_GPU_NATIVE_AVAILABLE = False
try:
    from .item_registry import ItemRegistry
    from .taichi_gem import api as gpu_api
    import numpy as np

    _GPU_NATIVE_AVAILABLE = True
except ImportError:
    pass


def _build_base_stats_array(base_stats_fixed: dict, cfg_data: dict) -> tuple:
    """
    Construct base stats array for GPU upload with user gem adjustments.

    This helper consolidates the duplicated base stats array construction
    logic used in both the GPU-native GA and fallback paths.

    Args:
        base_stats_fixed: Dict of fixed base stats (from config/team buffs)
        cfg_data: Configuration dict containing user gem inputs

    Returns:
        tuple: (base_stats_arr, selected_color) where base_stats_arr is np.int32[10]
    """
    base_stats_arr = np.array(
        [
            base_stats_fixed.get("Perfect Points", 0),
            base_stats_fixed.get("Combo Multiplier", 0),
            base_stats_fixed.get("Fever Multiplier", 0),
            base_stats_fixed.get("Fever Time", 0),
            base_stats_fixed.get("Fever Fill Rate", 0),
            base_stats_fixed.get("Beat", 0),
            base_stats_fixed.get("Vibe", 0),
            base_stats_fixed.get("Rush", 0),
            base_stats_fixed.get("Flow", 0),
            base_stats_fixed.get("Chill", 0),
        ],
        dtype=np.int32,
    )

    user_pp = int(cfg_data.get("user_pp", 0))
    user_cm = int(cfg_data.get("user_cm", 0))
    user_fm = int(cfg_data.get("user_fm", 0))
    user_ft = int(cfg_data.get("user_ft", 0))
    user_ff = int(cfg_data.get("user_ff", 0))
    static_elem_input = int(cfg_data.get("static_elem_input", 0))
    selected_color = str(cfg_data.get("selected_color", ""))

    if user_pp or user_cm or user_fm or user_ft or user_ff:
        base_stats_arr[0] -= user_pp * GEM_SCALE_NORMAL
        base_stats_arr[1] -= user_cm * GEM_SCALE_NORMAL
        base_stats_arr[2] -= user_fm * GEM_SCALE_FEVER
        base_stats_arr[3] -= user_ft * GEM_SCALE_FEVER
        base_stats_arr[4] -= user_ff * GEM_SCALE_FEVER

        base_stats_arr[9] -= user_pp * GEM_STAT_TO_ELEMENT_SCALE  # Chill
        base_stats_arr[8] -= user_cm * GEM_STAT_TO_ELEMENT_SCALE  # Flow
        base_stats_arr[7] -= user_fm * GEM_STAT_TO_ELEMENT_SCALE  # Rush
        base_stats_arr[5] -= user_ft * GEM_STAT_TO_ELEMENT_SCALE  # Beat
        base_stats_arr[6] -= user_ff * GEM_STAT_TO_ELEMENT_SCALE  # Vibe

    if static_elem_input and selected_color:
        color_to_idx = {"Beat": 5, "Vibe": 6, "Rush": 7, "Flow": 8, "Chill": 9}
        idx = color_to_idx.get(selected_color)
        if idx is not None:
            base_stats_arr[idx] -= static_elem_input * ELEMENTAL_GEM_SCALE

    return base_stats_arr, selected_color


def _extract_fg_candidates_from_ga_snapshot(
    *,
    registry: "ItemRegistry",
    cfg_data: dict,
    base_stats_fixed: dict,
    pop_snapshot: "np.ndarray",
    results: "np.ndarray",
    scores: "np.ndarray",
    n_genomes: int,
    candidate_limit: int,
) -> list:
    """
    Extract top unique genomes from a GA run snapshot to seed the Force Greats solver.

    This mirrors the vectorized extraction logic used in `_run_gpu_native_ga`, but is
    factored out so the multi-start loop can run fully GPU-side (no per-run readbacks)
    and do candidate extraction after a single download at end-of-song.
    """
    all_evaluated: list = []
    if pop_snapshot is None or results is None or scores is None:
        return all_evaluated

    n_genomes = int(n_genomes)
    if n_genomes <= 0:
        return all_evaluated

    candidate_limit = int(candidate_limit)
    if candidate_limit <= 0:
        return all_evaluated

    # NOTE: We scan the full final population here to maximize unique candidate
    # coverage for downstream ForceGreats evaluation. With the GPU-native GA the
    # population often converges, so looking only at a small top-K window can
    # yield too few unique genomes.
    limit = n_genomes

    # Map selected color to stat index for overflow gem contribution
    color_to_idx = {"Beat": 5, "Vibe": 6, "Rush": 7, "Flow": 8, "Chill": 9}
    sel_color = cfg_data.get("selected_color", "")
    sel_color_idx = color_to_idx.get(sel_color, -1)

    # Build base stats array for vectorized computation
    base_stats_arr = np.array(
        [
            base_stats_fixed.get("Perfect Points", 0),
            base_stats_fixed.get("Combo Multiplier", 0),
            base_stats_fixed.get("Fever Multiplier", 0),
            base_stats_fixed.get("Fever Time", 0),
            base_stats_fixed.get("Fever Fill Rate", 0),
            base_stats_fixed.get("Beat", 0),
            base_stats_fixed.get("Vibe", 0),
            base_stats_fixed.get("Rush", 0),
            base_stats_fixed.get("Flow", 0),
            base_stats_fixed.get("Chill", 0),
        ],
        dtype=np.int32,
    )

    # VECTORIZED: Get top-K indices, item stats, and gem contributions in one call
    top_indices, item_stats_sum, gem_contributions = registry.batch_decode_stats_numpy(
        pop_snapshot,
        results,
        scores,
        base_stats_arr,
        limit,
        gem_scale_normal=GEM_SCALE_NORMAL,
        gem_scale_fever=GEM_SCALE_FEVER,
        gem_stat_to_element=GEM_STAT_TO_ELEMENT_SCALE,
        elemental_gem_scale=ELEMENTAL_GEM_SCALE,
        sel_color_idx=sel_color_idx,
    )

    # Stat names for dict construction (only done for final candidates)
    stat_names = [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Time",
        "Fever Fill Rate",
        "Beat",
        "Vibe",
        "Rush",
        "Flow",
        "Chill",
    ]

    # OPTIMIZATION: Two-pass lazy evaluation
    # Pass 1: Filter unique genomes by ID tuple (fast, no decode_genome)
    # Pass 2: Decode and construct dicts only for unique candidates
    seen_id_hashes = set()
    unique_candidate_indices = []  # Indices into top_indices

    for i, idx in enumerate(top_indices):
        score_val = int(scores[idx])
        if score_val <= 0:
            continue

        genome_ids = pop_snapshot[idx]
        # Canonicalize minis (order-invariant) so mini permutations don't consume
        # candidate budget or downstream decode work.
        try:
            gear_ids = tuple(int(x) for x in genome_ids[:6])
            mini_ids = tuple(sorted(int(x) for x in genome_ids[6:9]))
            id_hash = gear_ids + mini_ids
        except Exception:
            id_hash = tuple(int(x) for x in genome_ids[:9])

        if id_hash not in seen_id_hashes:
            seen_id_hashes.add(id_hash)
            unique_candidate_indices.append(i)

            # Keep scanning the full final population to maximize diversity for downstream
            # ForceGreats evaluation; the final funnel size is selected later.

    # Pass 2: Decode and build dicts only for unique candidates
    for i in unique_candidate_indices:
        idx = top_indices[i]
        score_val = int(scores[idx])

        genome_ids = pop_snapshot[idx]
        genome = registry.decode_genome(genome_ids)

        # Get gem allocations from results array
        res_row = results[idx]
        g_ft, g_ff = int(res_row[1]), int(res_row[2])
        g_pp, g_cm, g_fm, g_ov = int(res_row[3]), int(res_row[4]), int(res_row[5]), int(res_row[6])

        # Compute final stats: base + item_stats + gem_contributions
        final_stats = base_stats_arr + item_stats_sum[i] + gem_contributions[i]

        # Build stats dict from numpy array (fast)
        current_stats = {stat_names[j]: int(final_stats[j]) for j in range(10)}

        data_obj = {
            "Score": score_val,
            "FT": g_ft,
            "FF": g_ff,
            "GemCounts": {
                "Perfect Points": g_pp,
                "Combo Multiplier": g_cm,
                "Fever Multiplier": g_fm,
                "Element": g_ov,
            },
            "Stats": current_stats,
            "Selected Element": sel_color,
            "BaseScore": score_val,
        }

        cand_data = {
            "Score": score_val,
            "BaseScore": score_val,
            "Genome": genome,
            "Gear": genome[:6],
            "Minis": genome[6:9],
            "GearNames": [g.get("Name", "None") for g in genome[:6]],
            "MiniNames": [m.get("Name", "None") for m in genome[6:9]],
            "Data": data_obj,
            "Details": {
                "FeverGems": g_ft,
                "FeverFillGems": g_ff,
                "PP": g_pp,
                "CM": g_cm,
                "FM": g_fm,
                "OV": g_ov,
            },
        }
        all_evaluated.append(cand_data)

    return all_evaluated


def decode_gpu_native_ga_runs_payload(
    *,
    runs_payload: "np.ndarray",
    registry: "ItemRegistry",
    cfg_data: dict,
    base_stats_fixed: dict,
    fg_candidate_limit: int,
) -> tuple[dict, list, list, list[dict]]:
    """
    CPU-side decoding for the GPU-native GA multi-run payload.

    This is shared between the direct GPU-native GA path (single-thread) and the
    GPU-native in-flight pipeline (GpuExecutor owner thread for kernels + CPU main
    thread for formatting).

    Important: This function must remain GPU-free (no Taichi calls). It only
    decodes the payload and reconstructs candidate dicts for downstream stages.
    """
    if not _GPU_NATIVE_AVAILABLE:
        raise RuntimeError("GPU-native GA not available (missing dependencies)")

    runs_payload = np.asarray(runs_payload, dtype=np.int32)
    if runs_payload.ndim != 3:
        raise ValueError(f"runs_payload must be 3D, got ndim={runs_payload.ndim}")

    n_runs = int(runs_payload.shape[0])
    if n_runs <= 0:
        raise ValueError("runs_payload has no runs")

    n_slots = 9
    n_genomes = int(runs_payload.shape[1] - 1)
    if n_genomes <= 0:
        raise ValueError("runs_payload has invalid n_genomes (expected >=1)")

    fg_candidate_limit = int(fg_candidate_limit)
    if fg_candidate_limit <= 0:
        fg_candidate_limit = int(cfg_data.get("fg_candidate_limit", FG_CANDIDATE_LIMIT) or FG_CANDIDATE_LIMIT)
    fg_candidate_limit = max(LOADOUTS_PER_SONG_LIMIT, min(5000, int(fg_candidate_limit)))

    perf = str(os.environ.get("PERF_TIMING", "0") or "").strip().lower() in {"1", "true", "yes", "on"}
    t_total = time.perf_counter() if perf else 0.0

    best_global_score = -1
    best_global_genome = None
    best_global_res_arr = None
    # Candidate stubs are collected without computing full stats. We canonicalize minis
    # (order-invariant) to avoid over-counting mini permutations and collapsing the
    # effective FG funnel.
    t_scan = time.perf_counter() if perf else 0.0

    for r in range(n_runs):
        run_pack = runs_payload[r]
        run_best_score = int(run_pack[0, 0])
        run_best_ids = np.asarray(run_pack[0, 1 : 1 + n_slots], dtype=np.int32)
        run_best_res = np.asarray(run_pack[0, 1 + n_slots : 1 + n_slots + 7], dtype=np.int32)

        if run_best_score > best_global_score:
            best_global_score = run_best_score
            best_global_genome = registry.decode_genome(run_best_ids)
            best_global_res_arr = run_best_res.copy()

    # Vectorized stub collection in the same order as the historical scan:
    # per run: candidates sorted by base score desc; runs processed in order.
    stub_scores = np.empty((0,), dtype=np.int32)
    stub_run_idx = np.empty((0,), dtype=np.int32)
    stub_pop_idx = np.empty((0,), dtype=np.int32)
    stub_keys_mat = np.empty((0, n_slots), dtype=np.int32)

    try:
        scores_snapshot_all = runs_payload[:, 1 : n_genomes + 1, 0]
        pop_snapshot_all = runs_payload[:, 1 : n_genomes + 1, 1 : 1 + n_slots]
        order = np.argsort(scores_snapshot_all, axis=1)[:, ::-1]

        ordered_scores = np.take_along_axis(scores_snapshot_all, order, axis=1)
        ordered_pop = np.take_along_axis(pop_snapshot_all, order[:, :, None], axis=1)
        ordered_pop_idx = order.astype(np.int32, copy=False)

        flat_scores_all = ordered_scores.reshape(-1)
        positive_mask = flat_scores_all > 0
        if np.any(positive_mask):
            flat_scores = flat_scores_all[positive_mask].astype(np.int32, copy=False)
            flat_pop = ordered_pop.reshape(-1, n_slots)[positive_mask]
            flat_pop_idx = ordered_pop_idx.reshape(-1)[positive_mask]
            flat_run_idx = np.repeat(np.arange(n_runs, dtype=np.int32), n_genomes)[positive_mask]

            minis_sorted = np.sort(flat_pop[:, 6:9], axis=1)
            keys_mat = np.concatenate([flat_pop[:, :6], minis_sorted], axis=1).astype(np.int32, copy=False)
            keys_contig = np.ascontiguousarray(keys_mat)
            keys_void = keys_contig.view(
                np.dtype((np.void, keys_contig.dtype.itemsize * keys_contig.shape[1]))
            ).reshape(-1)

            unique_void, inv = np.unique(keys_void, return_inverse=True)
            n_stub = int(unique_void.shape[0])
            scan_idx = np.arange(keys_void.shape[0], dtype=np.int32)

            first_idx = np.full((n_stub,), scan_idx.shape[0], dtype=np.int32)
            np.minimum.at(first_idx, inv, scan_idx)

            max_score = np.full((n_stub,), np.iinfo(np.int32).min, dtype=np.int32)
            np.maximum.at(max_score, inv, flat_scores)

            best_scan = np.full((n_stub,), scan_idx.shape[0], dtype=np.int32)
            best_rank = np.where(flat_scores == max_score[inv], scan_idx, scan_idx.shape[0])
            np.minimum.at(best_scan, inv, best_rank)

            group_order = np.argsort(first_idx, kind="stable")
            best_pos = best_scan[group_order]

            stub_scores = flat_scores[best_pos].astype(np.int32, copy=False)
            stub_run_idx = flat_run_idx[best_pos].astype(np.int32, copy=False)
            stub_pop_idx = flat_pop_idx[best_pos].astype(np.int32, copy=False)
            stub_keys_mat = keys_contig[best_pos]
    except Exception:
        stub_scores = np.empty((0,), dtype=np.int32)
        stub_run_idx = np.empty((0,), dtype=np.int32)
        stub_pop_idx = np.empty((0,), dtype=np.int32)
        stub_keys_mat = np.empty((0, n_slots), dtype=np.int32)

    scan_ms = (time.perf_counter() - t_scan) * 1000.0 if perf else 0.0

    if best_global_genome is None or best_global_res_arr is None:
        try:
            fallback_ids = np.asarray(runs_payload[0, 0, 1 : 1 + n_slots], dtype=np.int32)
            best_global_genome = registry.decode_genome(fallback_ids)
            best_global_score = int(runs_payload[0, 0, 0])
            best_global_res_arr = np.asarray(runs_payload[0, 0, 1 + n_slots : 1 + n_slots + 7], dtype=np.int32).copy()
        except Exception:
            best_global_genome = []
            best_global_score = 0
            best_global_res_arr = np.zeros((7,), dtype=np.int32)

    best_gear = best_global_genome[:6]
    best_minis = best_global_genome[6:9]

    # Compute full stats for best genome (like FG candidates).
    best_stats = dict(base_stats_fixed or {})
    for item in best_global_genome or []:
        if not item:
            continue
        for k, v in item.items():
            if k not in SKIP_ITEM_KEYS:
                best_stats[k] = best_stats.get(k, 0) + v

    g_ft = int(best_global_res_arr[1])
    g_ff = int(best_global_res_arr[2])
    g_pp = int(best_global_res_arr[3])
    g_cm = int(best_global_res_arr[4])
    g_fm = int(best_global_res_arr[5])
    g_ov = int(best_global_res_arr[6])

    best_stats["Perfect Points"] = best_stats.get("Perfect Points", 0) + g_pp * GEM_SCALE_NORMAL
    best_stats["Combo Multiplier"] = best_stats.get("Combo Multiplier", 0) + g_cm * GEM_SCALE_NORMAL
    best_stats["Fever Multiplier"] = best_stats.get("Fever Multiplier", 0) + g_fm * GEM_SCALE_FEVER
    best_stats["Fever Time"] = best_stats.get("Fever Time", 0) + g_ft * GEM_SCALE_FEVER
    best_stats["Fever Fill Rate"] = best_stats.get("Fever Fill Rate", 0) + g_ff * GEM_SCALE_FEVER

    best_stats["Chill"] = best_stats.get("Chill", 0) + g_pp * GEM_STAT_TO_ELEMENT_SCALE
    best_stats["Flow"] = best_stats.get("Flow", 0) + g_cm * GEM_STAT_TO_ELEMENT_SCALE
    best_stats["Rush"] = best_stats.get("Rush", 0) + g_fm * GEM_STAT_TO_ELEMENT_SCALE
    best_stats["Beat"] = best_stats.get("Beat", 0) + g_ft * GEM_STAT_TO_ELEMENT_SCALE
    best_stats["Vibe"] = best_stats.get("Vibe", 0) + g_ff * GEM_STAT_TO_ELEMENT_SCALE

    selected_color = str(cfg_data.get("selected_color", ""))
    if selected_color:
        best_stats[selected_color] = best_stats.get(selected_color, 0) + g_ov * ELEMENTAL_GEM_SCALE

    best_data = {
        "Score": int(best_global_score),
        "BaseScore": int(best_global_score),
        "Genome": best_global_genome,
        "Gear": best_gear,
        "Minis": best_minis,
        "GearNames": [g.get("Name", "None") for g in best_gear],
        "MiniNames": [m.get("Name", "None") for m in best_minis],
        # FT/FF at root level for build_details() compatibility
        "FT": g_ft,
        "FF": g_ff,
        "GemCounts": {
            "Perfect Points": g_pp,
            "Combo Multiplier": g_cm,
            "Fever Multiplier": g_fm,
            "Element": g_ov,
        },
        "Stats": best_stats,
        "Selected Element": selected_color,
        "Details": {
            "FeverGems": g_ft,
            "FeverFillGems": g_ff,
            "PP": g_pp,
            "CM": g_cm,
            "FM": g_fm,
            "OV": g_ov,
        },
    }

    if stub_scores.size == 0:
        return best_data, list(best_gear), list(best_minis), []

    # Fast path: do FG-aware selection in ID-space (no dict genome decode) and only
    # decode full genomes for the final bounded funnel.
    t_stub = time.perf_counter() if perf else 0.0
    n_stub = int(stub_scores.shape[0])

    stub_rows = 1 + stub_pop_idx
    stub_genome_ids = runs_payload[stub_run_idx, stub_rows, 1 : 1 + n_slots]
    stub_res = runs_payload[stub_run_idx, stub_rows, 1 + n_slots : 1 + n_slots + 7]
    stub_ft = np.asarray(stub_res[:, 1], dtype=np.int32)
    stub_ff = np.asarray(stub_res[:, 2], dtype=np.int32)

    if not hasattr(registry, "_item_stats_cache"):
        gpu_arrays = registry.to_gpu_arrays()
        registry._item_stats_cache = gpu_arrays["item_stats"]
    item_stats = registry._item_stats_cache  # (n_items, 10)

    stub_item_stats_sum = item_stats[stub_genome_ids].sum(axis=1)  # (n_stub, 10)
    stub_item_stats_sum64 = stub_item_stats_sum.astype(np.int64, copy=False)

    p_color = str(cfg_data.get("primary_color", "") or "")
    s_color = str(cfg_data.get("secondary_color", "") or "")
    color_to_idx = {"Beat": 5, "Vibe": 6, "Rush": 7, "Flow": 8, "Chill": 9}
    p_idx = color_to_idx.get(p_color, -1)
    s_idx = color_to_idx.get(s_color, -1)

    fg_proxy_vec = (
        (stub_item_stats_sum64[:, 2] * 4)  # Fever Multiplier
        + (stub_item_stats_sum64[:, 4] * 4)  # Fever Fill Rate
        + (stub_item_stats_sum64[:, 3] * 3)  # Fever Time
        + (stub_item_stats_sum64[:, 1] * 2)  # Combo Multiplier
        + stub_item_stats_sum64[:, 0]  # Perfect Points
    )
    if 5 <= p_idx <= 9:
        fg_proxy_vec = fg_proxy_vec + (stub_item_stats_sum64[:, p_idx] * 2)
    if 5 <= s_idx <= 9 and s_idx != p_idx:
        fg_proxy_vec = fg_proxy_vec + stub_item_stats_sum64[:, s_idx]

    # Deterministic ordering helpers (stable for ties, matches select_fg_candidates behavior).
    #
    # Avoid Python `sorted(..., key=lambda ...)` here: `n_stub` can be large and this code
    # runs on the CPU between GPU jobs (a common throughput bottleneck).
    #
    # We use stable NumPy argsorts so the result matches Python's stable sort semantics:
    # - metas_by_base: primary=stub_scores desc, secondary=fg_proxy desc
    # - metas_by_fg: primary=fg_proxy desc, secondary=stub_scores desc
    idx = np.arange(n_stub, dtype=np.int32)
    # metas_by_base
    _tmp = idx[np.argsort(-fg_proxy_vec, kind="stable")]
    metas_by_base = _tmp[np.argsort(-stub_scores[_tmp], kind="stable")].tolist()
    # metas_by_fg
    _tmp2 = idx[np.argsort(-stub_scores, kind="stable")]
    metas_by_fg = _tmp2[np.argsort(-fg_proxy_vec[_tmp2], kind="stable")].tolist()

    if n_stub <= fg_candidate_limit:
        selected_stub_indices = idx[np.argsort(-stub_scores, kind="stable")].tolist()
    else:
        selected_stub_indices: list[int] = []
        selected_set: set[int] = set()
        seen_minis: set[tuple[int, ...]] = set()
        center_keys = (stub_ft.astype(np.int64) << 32) | (stub_ff.astype(np.int64) & 0xFFFFFFFF)
        seen_centers: set[int] = set()

        mini_keys = [
            (int(stub_keys_mat[j, 6]), int(stub_keys_mat[j, 7]), int(stub_keys_mat[j, 8])) for j in range(n_stub)
        ]

        def _add(j: int) -> bool:
            if j in selected_set:
                return False
            selected_set.add(j)
            selected_stub_indices.append(j)
            seen_minis.add(mini_keys[j])
            seen_centers.add(int(center_keys[j]))
            return True

        top_base_keep = min(int(fg_candidate_limit), int(LOADOUTS_PER_SONG_LIMIT))
        for j in metas_by_base:
            if len(selected_stub_indices) >= top_base_keep:
                break
            _add(j)

        base_budget = min(int(fg_candidate_limit), max(top_base_keep, int(fg_candidate_limit * 0.55)))
        fg_budget_end = min(int(fg_candidate_limit), base_budget + int(fg_candidate_limit * 0.30))

        for j in metas_by_base:
            if len(selected_stub_indices) >= base_budget:
                break
            _add(j)

        for j in metas_by_fg:
            if len(selected_stub_indices) >= fg_budget_end:
                break
            if int(center_keys[j]) in seen_centers:
                continue
            _add(j)
        for j in metas_by_fg:
            if len(selected_stub_indices) >= fg_budget_end:
                break
            _add(j)

        for j in metas_by_base:
            if len(selected_stub_indices) >= int(fg_candidate_limit):
                break
            mini_key = mini_keys[j]
            if mini_key in seen_minis:
                continue
            _add(j)

        for j in metas_by_base:
            if len(selected_stub_indices) >= int(fg_candidate_limit):
                break
            _add(j)

    selected_stub_indices = selected_stub_indices[: int(fg_candidate_limit)]
    select_ms = (time.perf_counter() - t_stub) * 1000.0 if perf else 0.0
    if not selected_stub_indices:
        return best_data, list(best_gear), list(best_minis), []

    # Vectorized stats computation for selected candidates only.
    t_stats = time.perf_counter() if perf else 0.0
    sel_color = str(cfg_data.get("selected_color", ""))
    color_to_idx = {"Beat": 5, "Vibe": 6, "Rush": 7, "Flow": 8, "Chill": 9}
    sel_color_idx = color_to_idx.get(sel_color, -1)

    base_stats_arr = np.array(
        [
            base_stats_fixed.get("Perfect Points", 0),
            base_stats_fixed.get("Combo Multiplier", 0),
            base_stats_fixed.get("Fever Multiplier", 0),
            base_stats_fixed.get("Fever Time", 0),
            base_stats_fixed.get("Fever Fill Rate", 0),
            base_stats_fixed.get("Beat", 0),
            base_stats_fixed.get("Vibe", 0),
            base_stats_fixed.get("Rush", 0),
            base_stats_fixed.get("Flow", 0),
            base_stats_fixed.get("Chill", 0),
        ],
        dtype=np.int32,
    )

    # Stat names for dict construction.
    stat_names = [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Time",
        "Fever Fill Rate",
        "Beat",
        "Vibe",
        "Rush",
        "Flow",
        "Chill",
    ]

    n_cand = len(selected_stub_indices)
    genome_ids_mat = stub_genome_ids[selected_stub_indices]
    item_stats_sum = stub_item_stats_sum[selected_stub_indices]
    scores_vec = stub_scores[selected_stub_indices].astype(np.int32, copy=False)
    sel_run_idx = stub_run_idx[selected_stub_indices]
    sel_rows = 1 + stub_pop_idx[selected_stub_indices]
    results_mat = runs_payload[sel_run_idx, sel_rows, 1 + n_slots : 1 + n_slots + 7]

    # Gem contributions: (n_cand, 10)
    gem_contributions = np.zeros((n_cand, 10), dtype=np.int32)
    g_ft = results_mat[:, 1]
    g_ff = results_mat[:, 2]
    g_pp = results_mat[:, 3]
    g_cm = results_mat[:, 4]
    g_fm = results_mat[:, 5]
    g_ov = results_mat[:, 6]

    gem_contributions[:, 0] = g_pp * GEM_SCALE_NORMAL
    gem_contributions[:, 1] = g_cm * GEM_SCALE_NORMAL
    gem_contributions[:, 2] = g_fm * GEM_SCALE_FEVER
    gem_contributions[:, 3] = g_ft * GEM_SCALE_FEVER
    gem_contributions[:, 4] = g_ff * GEM_SCALE_FEVER

    gem_contributions[:, 5] = g_ft * GEM_STAT_TO_ELEMENT_SCALE
    gem_contributions[:, 6] = g_ff * GEM_STAT_TO_ELEMENT_SCALE
    gem_contributions[:, 7] = g_fm * GEM_STAT_TO_ELEMENT_SCALE
    gem_contributions[:, 8] = g_cm * GEM_STAT_TO_ELEMENT_SCALE
    gem_contributions[:, 9] = g_pp * GEM_STAT_TO_ELEMENT_SCALE

    if 5 <= sel_color_idx <= 9:
        gem_contributions[:, sel_color_idx] += g_ov * ELEMENTAL_GEM_SCALE

    final_stats_mat = base_stats_arr + item_stats_sum + gem_contributions

    unique_evaluated: list[dict] = []
    for i in range(n_cand):
        score_val = int(scores_vec[i])
        genome = registry.decode_genome(genome_ids_mat[i])

        # Build stats dict from numpy array (fast).
        current_stats = {stat_names[j]: int(final_stats_mat[i, j]) for j in range(10)}

        g_ft_i = int(g_ft[i])
        g_ff_i = int(g_ff[i])
        g_pp_i = int(g_pp[i])
        g_cm_i = int(g_cm[i])
        g_fm_i = int(g_fm[i])
        g_ov_i = int(g_ov[i])

        data_obj = {
            "Score": score_val,
            "FT": g_ft_i,
            "FF": g_ff_i,
            "GemCounts": {
                "Perfect Points": g_pp_i,
                "Combo Multiplier": g_cm_i,
                "Fever Multiplier": g_fm_i,
                "Element": g_ov_i,
            },
            "Stats": current_stats,
            "Selected Element": sel_color,
            "BaseScore": score_val,
        }

        cand_data = {
            "Score": score_val,
            "BaseScore": score_val,
            "Genome": genome,
            "Gear": genome[:6],
            "Minis": genome[6:9],
            "GearNames": [g.get("Name", "None") for g in genome[:6]],
            "MiniNames": [m.get("Name", "None") for m in genome[6:9]],
            "Data": data_obj,
            "Details": {
                "FeverGems": g_ft_i,
                "FeverFillGems": g_ff_i,
                "PP": g_pp_i,
                "CM": g_cm_i,
                "FM": g_fm_i,
                "OV": g_ov_i,
            },
        }
        unique_evaluated.append(cand_data)

    stats_ms = (time.perf_counter() - t_stats) * 1000.0 if perf else 0.0
    total_ms = (time.perf_counter() - t_total) * 1000.0 if perf else 0.0
    if perf:
        print(
            "[PERF][GADecode] "
            f"runs={n_runs} pop={n_genomes} uniq={n_stub} "
            f"scan={scan_ms:.1f}ms select={select_ms:.1f}ms stats={stats_ms:.1f}ms total={total_ms:.1f}ms "
            f"selected={len(unique_evaluated)}"
        )

    return best_data, list(best_gear), list(best_minis), unique_evaluated


def _parse_cfg_csv_list(raw: str) -> list[str]:
    if not raw:
        return []
    parts = []
    for chunk in str(raw).replace(";", ",").replace("|", ",").split(","):
        val = chunk.strip()
        if val:
            parts.append(val)
    return parts


def _neighbor_sweep_fg_candidates(
    *,
    cfg,
    existing_candidates: list[dict],
    registry: "ItemRegistry",
    gear_pool: dict,
    mini_pool: list,
    slots: list[str],
    cfg_data: dict,
    base_stats_fixed: dict,
    calc_song: dict,
    ref_arrays: dict,
) -> list[dict]:
    """
    Evaluate a small set of "neighbor" loadouts (single-slot swaps) and return
    them as fully-evaluated GA-style candidates for ForceGreatsFinder.

    Goal: include FG-relevant loadouts that may be far from the base-score optimum,
    without relying on DB seeds (cold start).
    """
    if cfg is None or not hasattr(cfg, "getboolean"):
        return []
    if not existing_candidates:
        return []

    enabled = cfg.getboolean("IterationEngine", "FG_NeighborSweep", fallback=False)
    if not enabled:
        return []

    try:
        if cfg.getboolean("IterationEngine", "ForceGreatsDebug", fallback=False):
            print("[FG Sweep] NeighborSweep enabled")
    except Exception:
        pass

    try:
        from .scoring import batch_evaluate_genomes
    except Exception:
        return []

    seed_top_k = safe_int(cfg.get("IterationEngine", "FG_NeighborSweepSeeds", fallback=12), 12)
    max_new = safe_int(cfg.get("IterationEngine", "FG_NeighborSweepMaxEvals", fallback=200), 200)
    top_per_stat = safe_int(cfg.get("IterationEngine", "FG_NeighborSweepTopPerStat", fallback=2), 2)
    top_by_heuristic = safe_int(cfg.get("IterationEngine", "FG_NeighborSweepTopByHeuristic", fallback=12), 12)
    sweep_slots_raw = cfg.get("IterationEngine", "FG_NeighborSweepSlots", fallback="Back")

    if max_new <= 0 or seed_top_k <= 0:
        return []

    slot_name_to_idx = {name: idx for idx, name in enumerate(slots)}
    sweep_slots: list[int] = []
    sweep_minis = False
    mini_tokens = {"mini", "minis", "miniteam", "mini-team", "mini_teams", "miniteams"}
    for token in _parse_cfg_csv_list(sweep_slots_raw):
        raw = token.strip()
        if not raw:
            continue
        normalized = raw.lower().replace(" ", "").replace("_", "-")
        if normalized in mini_tokens:
            sweep_minis = True
            continue
        idx = slot_name_to_idx.get(raw.title())
        if idx is not None:
            sweep_slots.append(idx)

    if not sweep_slots and not sweep_minis:
        return []

    meta = calc_song.get("metadata", {}) or {}
    p_color = str(meta.get("Primary Color", "") or "")
    s_color = str(meta.get("Secondary Color", "") or "")
    color_stats = ("Rush", "Flow", "Chill", "Beat", "Vibe")

    base_stat_keys = [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Time",
        "Fever Fill Rate",
    ]
    # Always include elemental stats so "specialist" items (e.g., Flow-heavy backs)
    # can enter the FG funnel even if they're not top-K by base-score heuristics.
    base_stat_keys.extend(color_stats)

    def _heuristic_item_score(item: dict) -> int:
        if not item:
            return 0
        pp = int(item.get("Perfect Points", 0) or 0)
        cm = int(item.get("Combo Multiplier", 0) or 0)
        fm = int(item.get("Fever Multiplier", 0) or 0)
        ft = int(item.get("Fever Time", 0) or 0)
        ff = int(item.get("Fever Fill Rate", 0) or 0)
        primary_val = int(item.get(p_color, 0) or 0) if p_color else 0
        secondary_val = int(item.get(s_color, 0) or 0) if (s_color and s_color != p_color) else 0
        modern_base = (pp * 3) + (cm * 3) + (fm * 3) + (ft * 2) + (ff * 2)
        modern_elemental_bonus = (primary_val * 2) + (secondary_val * 1)
        return int(modern_base + (modern_elemental_bonus // 2))

    def _candidate_key_from_genome(genome: list[dict]) -> tuple:
        gear_names = tuple((it or {}).get("Name", "") for it in genome[:6])
        mini_names = tuple(sorted(((it or {}).get("Name", "") for it in genome[6:9])))
        return gear_names + mini_names

    def _build_interesting_items(pool: list[dict]) -> list[dict]:
        if not pool:
            return []
        interesting: dict[str, dict] = {}
        if top_by_heuristic > 0:
            ranked = sorted(pool, key=_heuristic_item_score, reverse=True)
            for it in ranked[: max(1, top_by_heuristic)]:
                if not it:
                    continue
                name = it.get("Name")
                if name and name not in interesting:
                    interesting[name] = it

        for key in base_stat_keys:
            ranked = sorted(pool, key=lambda it: int((it or {}).get(key, 0) or 0), reverse=True)
            for it in ranked[: max(1, top_per_stat)]:
                if not it:
                    continue
                name = it.get("Name")
                if name and name not in interesting:
                    interesting[name] = it

        return list(interesting.values())

    gear_candidates_by_slot: dict[int, list[dict]] = {}
    for slot_idx in sweep_slots:
        slot_name = slots[slot_idx]
        pool = gear_pool.get(slot_name) or []
        gear_candidates_by_slot[slot_idx] = _build_interesting_items(pool)

    mini_candidates: list[dict] = _build_interesting_items(mini_pool) if sweep_minis else []

    # Seed selection: prefer mini-team diversity so we don't miss FG-relevant
    # loadouts that are lower-ranked by base score but have different minis.
    existing_candidate_keys = set()
    seen_mini_sets = set()
    seen_seed_keys = set()
    seeds: list[list[dict]] = []
    for cand in existing_candidates:
        genome = cand.get("Genome")
        if not genome:
            continue
        full_key = _candidate_key_from_genome(genome)
        existing_candidate_keys.add(full_key)

        mini_key = tuple(sorted(((it or {}).get("Name", "") for it in genome[6:9])))
        if mini_key in seen_mini_sets:
            continue
        seen_mini_sets.add(mini_key)
        if full_key in seen_seed_keys:
            continue
        seen_seed_keys.add(full_key)
        seeds.append(genome)
        if len(seeds) >= seed_top_k:
            break

    # If the mini-diverse pass didn't fill the seed budget (common on converged runs),
    # fill with the next best unique genomes so we still explore multiple gear variants.
    if len(seeds) < seed_top_k:
        for cand in existing_candidates:
            genome = cand.get("Genome")
            if not genome:
                continue
            full_key = _candidate_key_from_genome(genome)
            if full_key in seen_seed_keys:
                continue
            seen_seed_keys.add(full_key)
            seeds.append(genome)
            if len(seeds) >= seed_top_k:
                break

    if not seeds:
        return []

    neighbor_genomes: list[list[dict]] = []
    neighbor_keys = set(existing_candidate_keys)

    def _try_add(genome: list[dict]) -> bool:
        mini_names = [m.get("Name", "") for m in genome[6:9] if m]
        if len(mini_names) != len(set(mini_names)):
            return False
        key = _candidate_key_from_genome(genome)
        if key in neighbor_keys:
            return False
        neighbor_keys.add(key)
        neighbor_genomes.append(genome)
        return True

    mini_positions = (6, 7, 8)
    gear_pairs: list[tuple[int, int]] = []
    if len(sweep_slots) >= 2:
        for i, a in enumerate(sweep_slots):
            for b in sweep_slots[i + 1 :]:
                gear_pairs.append((a, b))

    pair_top = max(1, min(8, top_by_heuristic))
    mini_combo_top = max(1, min(8, top_by_heuristic))

    for seed in seeds:
        seed_minis = [m for m in seed[6:9] if m]
        seed_mini_names = {m.get("Name", "") for m in seed_minis}

        # Pairwise gear sweep (2-slot combos) + optional mini swap on the weakest mini.
        if gear_pairs:
            weakest_pos = 6
            weakest_score = None
            for pos in mini_positions:
                it = seed[pos] or {}
                score = _heuristic_item_score(it)
                if weakest_score is None or score < weakest_score:
                    weakest_score = score
                    weakest_pos = pos

            for a, b in gear_pairs:
                items_a = (gear_candidates_by_slot.get(a) or [])[:pair_top]
                items_b = (gear_candidates_by_slot.get(b) or [])[:pair_top]
                if not items_a or not items_b:
                    continue

                curr_a = (seed[a] or {}).get("Name", "")
                curr_b = (seed[b] or {}).get("Name", "")

                for it_a in items_a:
                    name_a = (it_a or {}).get("Name", "")
                    for it_b in items_b:
                        name_b = (it_b or {}).get("Name", "")
                        if name_a == curr_a and name_b == curr_b:
                            continue

                        genome_pair = list(seed)
                        if name_a and name_a != curr_a:
                            genome_pair[a] = it_a
                        if name_b and name_b != curr_b:
                            genome_pair[b] = it_b

                        _try_add(genome_pair)
                        if len(neighbor_genomes) >= max_new:
                            break

                        if sweep_minis and mini_candidates:
                            for mini in mini_candidates[:mini_combo_top]:
                                mini_name = mini.get("Name", "")
                                if not mini_name or mini_name in seed_mini_names:
                                    continue
                                genome_combo = list(genome_pair)
                                genome_combo[weakest_pos] = mini
                                _try_add(genome_combo)
                                if len(neighbor_genomes) >= max_new:
                                    break
                        if len(neighbor_genomes) >= max_new:
                            break
                    if len(neighbor_genomes) >= max_new:
                        break
                if len(neighbor_genomes) >= max_new:
                    break
            if len(neighbor_genomes) >= max_new:
                break

        # Gear sweep (optionally combined with mini swaps when "Minis" is included).
        for slot_idx in sweep_slots:
            pool_items = gear_candidates_by_slot.get(slot_idx) or []
            if not pool_items:
                continue

            current_item = seed[slot_idx] or {}
            current_name = current_item.get("Name", "")

            for it in pool_items:
                if (it or {}).get("Name", "") == current_name:
                    continue

                genome_gear = list(seed)
                genome_gear[slot_idx] = it
                _try_add(genome_gear)
                if len(neighbor_genomes) >= max_new:
                    break

                if sweep_minis and mini_candidates:
                    for mini in mini_candidates:
                        mini_name = mini.get("Name", "")
                        if not mini_name or mini_name in seed_mini_names:
                            continue

                        for pos in mini_positions:
                            genome_combo = list(genome_gear)
                            genome_combo[pos] = mini
                            _try_add(genome_combo)
                            if len(neighbor_genomes) >= max_new:
                                break
                        if len(neighbor_genomes) >= max_new:
                            break

                if len(neighbor_genomes) >= max_new:
                    break
            if len(neighbor_genomes) >= max_new:
                break
        if len(neighbor_genomes) >= max_new:
            break

        # Mini-only sweep (useful when minis are the missing axis, or when no gear slots are enabled).
        if sweep_minis and mini_candidates and len(neighbor_genomes) < max_new:
            for mini in mini_candidates:
                mini_name = mini.get("Name", "")
                if not mini_name or mini_name in seed_mini_names:
                    continue
                for pos in mini_positions:
                    genome_mini = list(seed)
                    genome_mini[pos] = mini
                    _try_add(genome_mini)
                    if len(neighbor_genomes) >= max_new:
                        break
                if len(neighbor_genomes) >= max_new:
                    break
        if len(neighbor_genomes) >= max_new:
            break

    if not neighbor_genomes:
        try:
            if cfg.getboolean("IterationEngine", "ForceGreatsDebug", fallback=False):
                print("[FG Sweep] NeighborSweep generated 0 swaps")
        except Exception:
            pass
        return []

    try:
        if cfg.getboolean("IterationEngine", "ForceGreatsDebug", fallback=False):
            print(
                f"[FG Sweep] NeighborSweep: seeds={len(seeds)}, swaps={len(neighbor_genomes)}, slots={sweep_slots_raw}"
            )
    except Exception:
        pass

    evaluated = batch_evaluate_genomes(
        neighbor_genomes,
        base_stats_fixed,
        cfg_data,
        calc_song,
        ref_arrays,
        registry=registry,
    )
    out = []
    for e in evaluated:
        if not e:
            continue
        # Mark as high-priority for FG funnel retention (these can have lower base scores).
        e["_fg_priority"] = 1
        e["_fg_source"] = "neighbor_sweep"
        out.append(e)
    return out


def _run_gpu_native_ga(
    population: list | None,
    n_generations: int,
    registry: "ItemRegistry",
    cfg_data: dict,
    calc_song: dict,
    ref_arrays: dict,
    base_stats_fixed: dict,
    gpu_static: dict | None = None,
    elite_count: int = 2,
    mutation_rate: float = 0.02,
    immigrant_rate: float = 0.0,
    tournament_k: int = 3,
    color_flags: dict = None,
    status_cb=None,
    song_slot: int = 0,  # GPU slot for prefetched timeline
    store_payload_idx: int | None = None,
    store_payload_only: bool = False,
    n_genomes_override: int | None = None,
    population_preloaded: bool = False,
) -> tuple:
    """
    Run GPU-native GA loop (internal function).

    This runs the GA entirely on GPU, only downloading scores for elitism
    and the final best genome. Eliminates per-generation CPU-GPU round-trips.

    Args:
        population: Initial population as list of genomes (item dicts)
        n_generations: Number of generations to run
        registry: ItemRegistry for encoding/decoding genomes
        cfg_data: Song configuration data
        calc_song: Song calculation context (for timeline)
        ref_arrays: Reference lookup arrays (PP, CM, FM, FT, FF)
        elite_count: Number of elites to preserve per generation
        mutation_rate: Mutation probability
        immigrant_rate: Probability of fully re-rolling a genome per generation
        tournament_k: Tournament size for selection
        color_flags: Dict with is_p_*, is_s_* flags
        status_cb: Optional status callback

    Returns:
        tuple: (best_genome, best_score, best_result_array, all_evaluated)
    """
    if not _GPU_NATIVE_AVAILABLE:
        raise RuntimeError("GPU-native GA not available (missing dependencies)")

    if n_genomes_override is not None:
        n_genomes = int(n_genomes_override)
    else:
        if population is None:
            raise ValueError("population is required unless n_genomes_override is provided")
        n_genomes = len(population)
    n_slots = 9

    # Ensure color flags are set
    color_flags = color_flags or {}
    is_p_ft = color_flags.get("is_p_ft", 0)
    is_s_ft = color_flags.get("is_s_ft", 0)
    is_p_ff = color_flags.get("is_p_ff", 0)
    is_s_ff = color_flags.get("is_s_ff", 0)
    is_p_pp = color_flags.get("is_p_pp", 0)
    is_s_pp = color_flags.get("is_s_pp", 0)
    is_p_cm = color_flags.get("is_p_cm", 0)
    is_s_cm = color_flags.get("is_s_cm", 0)
    is_p_fm = color_flags.get("is_p_fm", 0)
    is_s_fm = color_flags.get("is_s_fm", 0)
    is_p_ov = color_flags.get("is_p_ov", 0)
    is_s_ov = color_flags.get("is_s_ov", 0)

    total_budget = cfg_data.get("TotalBudget", 90)
    gem_scale_fever = cfg_data.get("GemScaleFever", 3)

    # Upload item stats / base fixed stats are static per song; do it once in the caller
    # and reuse here. This reduces heavy CPU->GPU transfers and mitigates Vulkan
    # resource exhaustion in long multi-start runs.
    if gpu_static is None:
        # Backward-compatible fallback (slower): upload per run.
        gpu_data = registry.to_gpu_arrays()
        gpu_api.ga_upload_item_stats(
            gpu_data["item_stats"],
            gpu_data["slot_start"],
            gpu_data["slot_count"],
        )

        base_stats_arr, _ = _build_base_stats_array(base_stats_fixed, cfg_data)
        gpu_api.ga_upload_base_fixed_stats(base_stats_arr)
    else:
        if gpu_static.get("need_upload_item_stats"):
            gpu_api.ga_upload_item_stats(
                gpu_static["item_stats"],
                gpu_static["slot_start"],
                gpu_static["slot_count"],
            )
        if gpu_static.get("need_upload_base_fixed"):
            gpu_api.ga_upload_base_fixed_stats(gpu_static["base_fixed_stats"])

    # NOTE: Timeline grid is already precomputed by caller (solve_coevolution_genetic)
    # No need to re-upload here - GPU fields persist across calls

    # Encode and upload initial population (unless already staged/loaded by caller).
    if not population_preloaded:
        if population is None:
            raise ValueError("population is required unless population_preloaded is True")
        pop_ids = registry.encode_population(population)
        gpu_api.ga_upload_population_indices(pop_ids, n_slots=n_slots)
    gpu_api.ga_seed_rng(n_genomes, seed=42)

    # CPU-side best tracking (faster than GPU-side for this use case)
    best_score = -1
    best_genome_ids = None
    best_result_row = None  # [score, ft, ff, pp, cm, fm, ov] - gem allocation for best genome

    # --- ISLAND MODEL SETUP ---
    # Partition population into islands (contiguous index ranges)
    num_islands = min(GPU_GA_NUM_ISLANDS, n_genomes // 10)  # At least 10 per island
    if num_islands < 1:
        num_islands = 1
    island_size = n_genomes // num_islands

    # Island boundaries: island i owns indices [island_start[i], island_start[i+1])
    island_starts = [i * island_size for i in range(num_islands)]
    island_starts.append(n_genomes)  # Sentinel for last island end

    if os.environ.get("GPU_NATIVE_GA_LOG_ISLAND_MODEL", "0").strip().lower() in {"1", "true", "yes", "on"}:
        print(f"  >> Island Model: {num_islands} islands, ~{island_size} genomes each")

    # Track population snapshot - only downloaded when best improves or during migrations
    pop_snapshot = None

    # Warm-start control: force cold start on Gen 0
    gen_use_hints = 0

    # Upload island boundaries to GPU (once per run)
    island_boundaries_np = np.array(island_starts, dtype=np.int32)
    gpu_api.ga_upload_island_boundaries(island_boundaries_np)

    # Initialize GPU-side global best tracking
    gpu_api.ga_init_global_best()

    # Main GPU-native GA loop with island migration (GPU-resident elitism)
    for gen in range(n_generations):
        # Evaluate ENTIRE population on GPU (all islands at once - efficient)
        gpu_api.ga_evaluate_population(
            n_genomes=n_genomes,
            n_slots=n_slots,
            total_budget=total_budget,
            gem_scale_fever=gem_scale_fever,
            song_slot=song_slot,
            is_p_ft=is_p_ft,
            is_s_ft=is_s_ft,
            is_p_ff=is_p_ff,
            is_s_ff=is_s_ff,
            is_p_pp=is_p_pp,
            is_s_pp=is_s_pp,
            is_p_cm=is_p_cm,
            is_s_cm=is_s_cm,
            is_p_fm=is_p_fm,
            is_s_fm=is_s_fm,
            is_p_ov=is_p_ov,
            is_s_ov=is_s_ov,
            use_hints=gen_use_hints,  # 0=cold, 1=warm
        )

        # FUSED: Write best + store hints + update global best (was 3 kernels, now 1)
        # This replaces: ga_write_best_results_from_key + ga_store_hints + ga_update_global_best
        gpu_api.ga_write_best_and_update_global(
            n_genomes,
            n_slots,
            total_budget,
            gem_scale_fever,
            is_p_ft=is_p_ft,
            is_s_ft=is_s_ft,
            is_p_ff=is_p_ff,
            is_s_ff=is_s_ff,
            is_p_pp=is_p_pp,
            is_s_pp=is_s_pp,
            is_p_cm=is_p_cm,
            is_s_cm=is_s_cm,
            is_p_fm=is_p_fm,
            is_s_fm=is_s_fm,
            is_p_ov=is_p_ov,
            is_s_ov=is_s_ov,
            song_slot=song_slot,
        )

        # --- MIGRATION PHASE (every GPU_GA_GENS_PER_MIGRATION generations) ---
        # Now fully GPU-side: no CPU downloads/uploads needed!
        #
        # IMPORTANT: Skip migration on the final generation. Migration updates
        # population+scores but not genome_result_stats; performing it after the
        # last evaluation would corrupt the final snapshot payload.
        is_migration_gen = num_islands > 1 and (gen + 1) % GPU_GA_GENS_PER_MIGRATION == 0 and gen < n_generations - 1
        if is_migration_gen:
            # GPU-side ring topology migration (replaces expensive CPU round-trip)
            gpu_api.ga_island_migration(n_genomes, num_islands, GPU_GA_MIGRATE_COUNT, n_slots)

            # Force cold start after migration, as hints are scrambled
            gen_use_hints = 0
        else:
            # Enable warm start for next generation (unless overridden by migration)
            gen_use_hints = 1

        # Skip ga_next_generation on final iteration - we don't use that population
        # This saves one generation step per run (30 total per song)
        if gen < n_generations - 1:
            # Run next generation using FUSED kernel (2 launches instead of 4!)
            # Includes: select + crossover + mutate + island elitism + swap + hint inheritance
            gpu_api.ga_next_generation_fused(
                n_genomes=n_genomes,
                n_slots=n_slots,
                mutation_rate=mutation_rate,
                immigrant_rate=immigrant_rate,
                tournament_k=tournament_k,
                n_islands=num_islands,
                elites_per_island=elite_count,
            )

    # Optionally store run payload to the multi-run GPU buffer (no CPU readback).
    if store_payload_idx is not None:
        gpu_api.ga_store_run_payload(run_idx=store_payload_idx, n_genomes=n_genomes, n_slots=n_slots)
        if store_payload_only:
            return None, None, None, None

    # --- END OF RUN: Download best + population snapshot with a single transfer ---
    # This avoids multiple `to_numpy()` calls (each forces a GPU sync on Vulkan).
    (
        best_score,
        best_genome_ids,
        best_result_row,
        pop_snapshot,
        results,
        scores,
    ) = gpu_api.ga_download_run_payload(n_genomes=n_genomes, n_slots=n_slots)

    # Decode best genome (already captured correctly during loop)
    best_genome = registry.decode_genome(best_genome_ids) if best_genome_ids is not None else []

    # Best result uses the captured best_result_row (has correct gem allocations from when best was found)
    if best_result_row is not None:
        best_result = best_result_row.copy()
    else:
        best_result = np.zeros(7, dtype=np.int32)

    all_evaluated = _extract_fg_candidates_from_ga_snapshot(
        registry=registry,
        cfg_data=cfg_data,
        base_stats_fixed=base_stats_fixed,
        pop_snapshot=pop_snapshot,
        results=results,
        scores=scores,
        n_genomes=n_genomes,
        candidate_limit=int(cfg_data.get("fg_candidate_limit", FG_CANDIDATE_LIMIT)),
    )

    return best_genome, best_score, best_result, all_evaluated


def run_gpu_native_ga_runs_payload_prebuilt(
    *,
    calc_song: dict,
    ref_arrays: dict,
    song_slot: int,
    item_stats: "np.ndarray",
    slot_start: "np.ndarray",
    slot_count: "np.ndarray",
    base_fixed_stats_arr: "np.ndarray",
    initial_populations: "np.ndarray",
    n_generations: int,
    elite_count: int = GA_ELITISM,
    mutation_rate: float = GA_MUTATION_RATE,
    immigrant_rate: float = 0.0,
    tournament_k: int = 3,
    color_flags: dict | None = None,
    cfg_data: dict | None = None,
) -> "np.ndarray":
    """
    Run the GPU-native GA for multiple runs using *prebuilt* initial populations.

    This entrypoint is designed for the GPU-native in-flight pipeline:
    - CPU prepares/encodes initial populations and item registry arrays
    - GPU-owner thread executes kernels back-to-back and returns a compact runs payload

    Important: This must be called from the Taichi/Vulkan owner thread (GpuExecutor).
    """
    if not _GPU_NATIVE_AVAILABLE:
        raise RuntimeError("GPU-native GA not available (missing dependencies)")

    cfg_data = dict(cfg_data or {})
    color_flags = dict(color_flags or {})

    try:
        from .taichi_gem.api import load_ref_arrays, precompute_timeline_gpu
        from .taichi_gem import fields as gpu_fields
    except Exception as exc:
        raise RuntimeError(f"GPU-native GA requires taichi_gem api/fields: {exc}") from exc

    song_slot = int(song_slot)
    if song_slot < 0:
        song_slot = 0

    n_generations = int(n_generations)
    if n_generations <= 0:
        n_generations = 1

    elite_count = int(elite_count)
    elite_count = max(0, elite_count)

    tournament_k = int(tournament_k)
    tournament_k = max(1, min(8, tournament_k))

    mutation_rate = float(mutation_rate)
    mutation_rate = max(0.0, min(1.0, mutation_rate))

    immigrant_rate = float(immigrant_rate)
    immigrant_rate = max(0.0, min(1.0, immigrant_rate))

    if not isinstance(initial_populations, np.ndarray):
        initial_populations = np.asarray(initial_populations, dtype=np.int32)
    if initial_populations.ndim != 3:
        raise ValueError(
            f"initial_populations must have shape (n_runs, n_genomes, n_slots); got ndim={initial_populations.ndim}"
        )

    num_runs = int(initial_populations.shape[0])
    n_genomes = int(initial_populations.shape[1])
    n_slots = int(initial_populations.shape[2])

    if num_runs <= 0 or n_genomes <= 0 or n_slots <= 0:
        raise ValueError(
            f"initial_populations has invalid shape: (n_runs={num_runs}, n_genomes={n_genomes}, n_slots={n_slots})"
        )

    if n_slots != 9:
        raise ValueError(f"GPU-native GA expects n_slots=9, got {n_slots}")

    # Reduce padded CPU↔GPU transfers by sizing multi-run GA buffers to the
    # current session's needs. This MUST happen before the first Taichi field
    # allocation (i.e., before load_ref_arrays/precompute_timeline triggers ensure_ready()).
    gpu_fields.configure_ga_run_buffers(max_runs=num_runs, max_genomes=n_genomes)

    # Optional stability toggles (mirrors solve_coevolution_genetic GPU-native path)
    reset_every_runs_env = os.environ.get("GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS", "0")
    try:
        reset_every_runs = int(reset_every_runs_env)
    except Exception:
        reset_every_runs = 0

    max_retries_env = os.environ.get("GPU_NATIVE_GA_VULKAN_RETRIES", "1")
    try:
        max_retries = int(max_retries_env)
    except Exception:
        max_retries = 1

    def _is_vulkan_semaphore_failure(exc: BaseException) -> bool:
        msg = str(exc)
        return ("failed to create semaphore" in msg) or ("RHI Error" in msg and "semaphore" in msg)

    # Load refs + timeline for this song slot
    load_ref_arrays(ref_arrays)
    precompute_timeline_gpu(calc_song, ref_arrays, song_slot=song_slot)

    # Upload static per-song GA data once (minimize CPU->GPU transfers)
    gpu_api.ga_upload_item_stats(item_stats, slot_start, slot_count)
    gpu_api.ga_upload_base_fixed_stats(base_fixed_stats_arr)

    is_p_ft = color_flags.get("is_p_ft", 0)
    is_s_ft = color_flags.get("is_s_ft", 0)
    is_p_ff = color_flags.get("is_p_ff", 0)
    is_s_ff = color_flags.get("is_s_ff", 0)
    is_p_pp = color_flags.get("is_p_pp", 0)
    is_s_pp = color_flags.get("is_s_pp", 0)
    is_p_cm = color_flags.get("is_p_cm", 0)
    is_s_cm = color_flags.get("is_s_cm", 0)
    is_p_fm = color_flags.get("is_p_fm", 0)
    is_s_fm = color_flags.get("is_s_fm", 0)
    is_p_ov = color_flags.get("is_p_ov", 0)
    is_s_ov = color_flags.get("is_s_ov", 0)

    total_budget = int(cfg_data.get("TotalBudget", 90))
    gem_scale_fever = int(cfg_data.get("GemScaleFever", 3))

    # Island model (mirrors _run_gpu_native_ga)
    num_islands = min(GPU_GA_NUM_ISLANDS, n_genomes // 10)  # At least 10 per island
    if num_islands < 1:
        num_islands = 1

    # Determine an auto batch size that avoids combo-chunking in ga_evaluate_population.
    # Chunking increases kernel launch count, so we prefer keeping n_total*n_combos <= MAX_WORK_ITEMS.
    try:
        n_combos = int(gpu_api._ensure_ftff_combo_tables(total_budget))
    except Exception:
        n_combos = 0
    denom = int(n_genomes) * max(1, n_combos)
    # Keep a small safety margin below MAX_WORK_ITEMS to avoid accidental oversubscription.
    # GA evaluation now reduces atomic contention (key tiling), so we can safely run much
    # closer to the limit without the steep slowdowns seen previously on Vulkan.
    soft_work_items = int(gpu_fields.MAX_WORK_ITEMS) - 8192  # 8k headroom
    if soft_work_items < 1:
        soft_work_items = int(gpu_fields.MAX_WORK_ITEMS)
    max_runs_by_work = int(soft_work_items // denom) if denom > 0 else 1
    if max_runs_by_work < 1:
        max_runs_by_work = 1
    max_runs_by_genomes = int(gpu_fields.MAX_GENOMES // int(n_genomes)) if int(n_genomes) > 0 else 1
    if max_runs_by_genomes < 1:
        max_runs_by_genomes = 1

    batch_runs_env = os.environ.get("GPU_NATIVE_GA_BATCH_RUNS", "0").strip()
    try:
        batch_runs_override = int(batch_runs_env)
    except Exception:
        batch_runs_override = 0

    batch_runs_default = min(max_runs_by_work, max_runs_by_genomes)
    if batch_runs_default < 1:
        batch_runs_default = 1
    if batch_runs_override > 0:
        batch_runs_default = batch_runs_override

    payload_segments: list[np.ndarray] = []

    run_start_global = 0
    while run_start_global < num_runs:
        seg_len = min(int(gpu_fields.MAX_GA_RUNS), num_runs - run_start_global)
        segment_pop = np.asarray(initial_populations[run_start_global : run_start_global + seg_len], dtype=np.int32)

        gpu_api.ga_upload_initial_populations(
            segment_pop,
            n_runs=int(seg_len),
            n_genomes=int(n_genomes),
            n_slots=int(n_slots),
        )

        # Initialize per-run best rows for this segment (used by batched execution).
        gpu_api.ga_init_runs_best(run_idx_start=0, n_runs=int(seg_len), n_slots=int(n_slots))

        batch_runs = min(int(batch_runs_default), int(seg_len))
        if batch_runs < 1:
            batch_runs = 1

        local_run_idx = 0
        while local_run_idx < seg_len:
            global_run_idx = run_start_global + local_run_idx

            if reset_every_runs > 0 and global_run_idx > 0 and (global_run_idx % reset_every_runs) == 0:
                gpu_api.hard_reset_taichi(reason=f"periodic Vulkan reset at run {global_run_idx + 1}/{num_runs}")
                load_ref_arrays(ref_arrays)
                precompute_timeline_gpu(calc_song, ref_arrays, song_slot=song_slot)
                gpu_api.ga_upload_item_stats(item_stats, slot_start, slot_count)
                gpu_api.ga_upload_base_fixed_stats(base_fixed_stats_arr)
                gpu_api.ga_upload_initial_populations(
                    segment_pop,
                    n_runs=int(seg_len),
                    n_genomes=int(n_genomes),
                    n_slots=int(n_slots),
                )
                gpu_api.ga_init_runs_best(run_idx_start=0, n_runs=int(seg_len), n_slots=int(n_slots))

            batch_len = min(batch_runs, seg_len - local_run_idx)
            # Avoid crossing a periodic reset boundary within a batch.
            if reset_every_runs > 0 and global_run_idx > 0:
                remaining_until_reset = reset_every_runs - (global_run_idx % reset_every_runs)
                if remaining_until_reset <= 0:
                    remaining_until_reset = reset_every_runs
                if batch_len > remaining_until_reset:
                    batch_len = remaining_until_reset
            if batch_len <= 0:
                batch_len = 1

            last_exc = None
            for attempt in range(max_retries + 1):
                try:
                    # Pack batch initial populations contiguously, preserving per-run semantics.
                    gpu_api.ga_load_initial_populations_batch(
                        run_idx_start=int(local_run_idx),
                        n_runs=int(batch_len),
                        n_genomes_per_run=int(n_genomes),
                        n_slots=int(n_slots),
                    )
                    gpu_api.ga_seed_rng_runs(n_runs=int(batch_len), n_genomes_per_run=int(n_genomes), seed=42)

                    gen_use_hints = 0  # Force cold start on Gen 0
                    n_total = int(batch_len) * int(n_genomes)

                    for gen in range(int(n_generations)):
                        gpu_api.ga_evaluate_population(
                            n_genomes=n_total,
                            n_slots=int(n_slots),
                            total_budget=total_budget,
                            gem_scale_fever=gem_scale_fever,
                            song_slot=int(song_slot),
                            is_p_ft=is_p_ft,
                            is_s_ft=is_s_ft,
                            is_p_ff=is_p_ff,
                            is_s_ff=is_s_ff,
                            is_p_pp=is_p_pp,
                            is_s_pp=is_s_pp,
                            is_p_cm=is_p_cm,
                            is_s_cm=is_s_cm,
                            is_p_fm=is_p_fm,
                            is_s_fm=is_s_fm,
                            is_p_ov=is_p_ov,
                            is_s_ov=is_s_ov,
                            use_hints=gen_use_hints,
                        )

                        # Materialize best + store hints (no global-best update; we track per-run best in payload row 0).
                        gpu_api.ga_write_best_and_store_hints(
                            n_total,
                            total_budget,
                            gem_scale_fever,
                            is_p_ft=is_p_ft,
                            is_s_ft=is_s_ft,
                            is_p_ff=is_p_ff,
                            is_s_ff=is_s_ff,
                            is_p_pp=is_p_pp,
                            is_s_pp=is_s_pp,
                            is_p_cm=is_p_cm,
                            is_s_cm=is_s_cm,
                            is_p_fm=is_p_fm,
                            is_s_fm=is_s_fm,
                            is_p_ov=is_p_ov,
                            is_s_ov=is_s_ov,
                            song_slot=int(song_slot),
                        )

                        # Track best per run across generations.
                        gpu_api.ga_update_runs_best(
                            run_idx_start=int(local_run_idx),
                            n_runs=int(batch_len),
                            n_genomes_per_run=int(n_genomes),
                            n_slots=int(n_slots),
                        )

                        # Migration only if another generation will be evaluated (avoid corrupting final snapshots).
                        is_migration_gen = (
                            num_islands > 1
                            and (gen + 1) % GPU_GA_GENS_PER_MIGRATION == 0
                            and gen < (int(n_generations) - 1)
                        )
                        if is_migration_gen:
                            gpu_api.ga_island_migration_runs(
                                n_runs=int(batch_len),
                                n_genomes_per_run=int(n_genomes),
                                n_islands=int(num_islands),
                                migrate_count=int(GPU_GA_MIGRATE_COUNT),
                                n_slots=int(n_slots),
                            )
                            gen_use_hints = 0
                        else:
                            gen_use_hints = 1

                        if gen < int(n_generations) - 1:
                            gpu_api.ga_next_generation_fused_runs(
                                n_runs=int(batch_len),
                                n_genomes_per_run=int(n_genomes),
                                n_slots=int(n_slots),
                                mutation_rate=float(mutation_rate),
                                immigrant_rate=float(immigrant_rate),
                                tournament_k=int(tournament_k),
                                n_islands=int(num_islands),
                                elites_per_island=int(elite_count),
                            )

                    # Store final per-genome snapshot rows (row 0 already contains best across all generations).
                    gpu_api.ga_store_runs_payload_snapshot_segmented(
                        run_idx_start=int(local_run_idx),
                        n_runs=int(batch_len),
                        n_genomes_per_run=int(n_genomes),
                        n_slots=int(n_slots),
                    )

                    last_exc = None
                    break
                except Exception as e:
                    last_exc = e
                    if attempt >= max_retries or not _is_vulkan_semaphore_failure(e):
                        break
                    try:
                        gpu_api.hard_reset_taichi(reason=str(e).splitlines()[0][:200])
                        load_ref_arrays(ref_arrays)
                        precompute_timeline_gpu(calc_song, ref_arrays, song_slot=song_slot)
                        gpu_api.ga_upload_item_stats(item_stats, slot_start, slot_count)
                        gpu_api.ga_upload_base_fixed_stats(base_fixed_stats_arr)
                        gpu_api.ga_upload_initial_populations(
                            segment_pop,
                            n_runs=int(seg_len),
                            n_genomes=int(n_genomes),
                            n_slots=int(n_slots),
                        )
                        gpu_api.ga_init_runs_best(run_idx_start=0, n_runs=int(seg_len), n_slots=int(n_slots))
                    except Exception:
                        break

            if last_exc is not None:
                raise last_exc

            local_run_idx += int(batch_len)

        payload_segments.append(
            gpu_api.ga_download_runs_payload(n_runs=int(seg_len), n_genomes=int(n_genomes), n_slots=int(n_slots))
        )
        run_start_global += seg_len

    if not payload_segments:
        raise RuntimeError("Internal error: no GA payload segments were produced")

    runs_payload = payload_segments[0] if len(payload_segments) == 1 else np.concatenate(payload_segments, axis=0)
    if runs_payload.shape[0] != num_runs:
        runs_payload = runs_payload[:num_runs]
    return runs_payload


def solve_coevolution_genetic(
    cfg,
    base_stats_fixed,
    paths,
    calc_song,
    ref_arrays,
    all_gears,
    all_minis,
    gears_by_name,
    minis_by_name,
    optimize_gear=True,
    optimize_minis=True,
    fixed_gear=None,
    fixed_minis=None,
    ga_depth=75,
    db_seed=None,
    ga_settings=None,
    status_cb=None,
    executor=None,
    known_loadouts=None,
    song_slot: int = 0,  # GPU slot for prefetched timeline (0 = compute on-demand)
):
    """
    Main genetic algorithm solver for gear and mini co-evolution.

    Features:
    - Multi-start restarts for better global search
    - Memetic local search on elite candidates
    - Deep mining: extends search when cache hits indicate known territory
    - Dynamic mutation rate based on stagnation
    - Polishing phase at end with exhaustive local search

    Args:
        cfg: Configuration object
        base_stats_fixed: Fixed base stats dictionary
        paths: Path configuration
        calc_song: Song calculation context
        ref_arrays: Reference lookup arrays
        all_gears: List of all gear items
        all_minis: List of all mini items
        gears_by_name: Dict mapping gear names to gear objects
        minis_by_name: Dict mapping mini names to mini objects
        optimize_gear: Whether to optimize gear (vs fixed)
        optimize_minis: Whether to optimize minis (vs fixed)
        fixed_gear: Fixed gear loadout if not optimizing
        fixed_minis: Fixed minis if not optimizing
        ga_depth: Total generations across all runs
        db_seed: Previous best loadout from database
        ga_settings: GA configuration settings
        status_cb: Optional status callback function
        executor: Optional process pool executor for parallel evaluation
        known_loadouts: Dict of known loadouts from database

    Returns:
        tuple: (best_data, best_gear, best_minis, None, [], [], all_evaluated)
    """
    # Caches are now cleared in process_song_task, but clearing here is safe redundancy.
    GEM_SOLVER_CACHE.clear()
    FG_CACHE.clear()
    FEVER_TIMELINE_CACHE.clear()

    print("\n=== STARTING GENETIC ALGORITHM SOLVER ===")
    print(f"Configuration: GearOptimization={optimize_gear}, MiniOptimization={optimize_minis}")

    ga_settings = ga_settings or GASettings.from_cfg(cfg)

    p_color = calc_song["metadata"].get("Primary Color", "Rush")
    s_color = calc_song["metadata"].get("Secondary Color", "")
    selected_color = p_color  # For overflow gems (could be customized per loadout)

    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]

    # Initialize pools and apply dominance pruning
    pools = initialize_pools(all_gears, all_minis, p_color, slots, s_color=s_color)
    if pools is None:
        gear_pool = None
        whitelisted_minis = []
    elif len(pools) == 4:
        gear_pool, mini_pool, total_before, total_after = pools
        whitelisted_minis = []
    else:
        gear_pool, mini_pool, total_before, total_after, whitelisted_minis = pools
    if gear_pool is None:
        print(f"[GA Error] initialize_pools failed for song {calc_song['metadata'].get('Song Name', 'Unknown')}")
        return None, [], [], None, [], [], []

    if whitelisted_minis:
        print(f"[GA] Force-including {len(whitelisted_minis)} whitelisted minis in initialization.")

    # Build configuration data
    # Read GPU mode setting from config
    use_gpu_mode = (
        cfg.getboolean("IterationEngine", "GPU_Mode", fallback=False) if hasattr(cfg, "getboolean") else False
    )
    use_gpu_native = (
        cfg.getboolean("IterationEngine", "GPU_Native_GA", fallback=True) if hasattr(cfg, "getboolean") else True
    )

    # GPU-native GA uses Taichi kernels directly (taichi_gem.api) and is not compatible with
    # cross-process GPU ownership (GpuExecutor). In GPU worker mode, force CPU-GA + IPC GPU eval
    # so we never initialize Taichi/Vulkan in multiple spawned processes.
    if use_gpu_native:
        try:
            from .gpu_executor import is_gpu_worker_mode

            if is_gpu_worker_mode():
                use_gpu_native = False
                print("[GPU] GPU_Native_GA disabled in GPU worker mode (using GpuExecutor IPC).")
        except Exception:
            pass

    # FG fitness heuristic was removed: GA always optimizes true base score (all perfects).
    # The FG finder separately evaluates loadouts with FG configs to find the best FG score.
    if use_gpu_mode:
        print(f"[GPU] GPU_Mode enabled (Native GA: {use_gpu_native})")

    cfg_data = {
        "selected_color": selected_color,
        "primary_color": str(p_color or ""),
        "secondary_color": str(s_color or ""),
        "use_gpu": use_gpu_mode,
        "use_gpu_native": use_gpu_native,
        "fg_candidate_limit": max(
            LOADOUTS_PER_SONG_LIMIT,
            min(
                5000,
                safe_int(
                    cfg.get("IterationEngine", "FG_CandidateLimit", fallback=FG_CANDIDATE_LIMIT), FG_CANDIDATE_LIMIT
                ),
            ),
        ),
        "user_ft": safe_int(cfg.get("UserInputStatsGems", "fever_time", fallback=0)),
        "user_ff": safe_int(cfg.get("UserInputStatsGems", "fever_fill", fallback=0)),
        "user_pp": safe_int(cfg.get("UserInputStatsGems", "perfect_points", fallback=0)),
        "user_cm": safe_int(cfg.get("UserInputStatsGems", "combo_multiplier", fallback=0)),
        "user_fm": safe_int(cfg.get("UserInputStatsGems", "fever_multiplier", fallback=0)),
        "static_elem_input": safe_int(cfg.get("ElementalGems", selected_color, fallback=0)),
    }

    # --- GPU-NATIVE GA PATH ---
    # If using GPU mode, bypass the entire CPU loop mechanism.
    if cfg_data.get("use_gpu", False) and cfg_data.get("use_gpu_native", True) and _GPU_NATIVE_AVAILABLE:
        print("\n=== RUNNING GPU-NATIVE GENETIC ALGORITHM ===")
        print(f"  Population: {GA_POPULATION_SIZE}, Generations: {ga_depth}")

        # CRITICAL: Upload GPU prerequisites for evaluation
        from .taichi_gem.api import load_ref_arrays, precompute_timeline_gpu

        # 1. Load reference bonus lookup tables (required by optimize_core_device)
        load_ref_arrays(ref_arrays)

        # 2. Precompute timeline grid (required by solve_genomes_with_ftff_kernel)
        precompute_timeline_gpu(calc_song, ref_arrays, song_slot=song_slot)

        # 3. Create Registry
        registry = ItemRegistry(gear_pool, mini_pool, slots)

        # Upload static per-song GA data once (item stats + base fixed stats)
        # Doing this once avoids large repeated from_numpy() calls which can
        # trigger Vulkan resource exhaustion (semaphore allocation failures)
        # during multi-start runs.
        gpu_data = registry.to_gpu_arrays()
        gpu_api.ga_upload_item_stats(
            gpu_data["item_stats"],
            gpu_data["slot_start"],
            gpu_data["slot_count"],
        )

        # Upload base fixed stats (team buffs + user gems from config)
        base_stats_arr, _ = _build_base_stats_array(base_stats_fixed, cfg_data)
        gpu_api.ga_upload_base_fixed_stats(base_stats_arr)

        # 4. Create simple rank caches for genome factory (not needed for random genomes, but required by function signature)
        # GPU-native GA uses random initialization, not heuristic, so these won't be used
        gear_rank_cache = {s: gear_pool[s] for s in slots}  # Just use full pools
        mini_rank_cache = mini_pool

        # 5. Build explicit factories for initial population
        # We reuse the existing factories to robustly create valid random genomes
        (
            create_random_genome,
            create_heuristic_genome,
            reconstruct_genome_from_db_list,
            build_seed_list_from_record,
            mutate_genome_once,
        ) = create_genome_functions(
            gear_pool,
            mini_pool,
            gear_rank_cache,
            mini_rank_cache,
            gears_by_name,
            minis_by_name,
            slots,
            optimize_gear,
            optimize_minis,
            fixed_gear,
            fixed_minis,
        )

        # 6. Create initial population functions (created once)
        # We reuse the existing factories to robustly create valid random genomes

        # --- MULTI-START LOOP ---
        num_runs = ga_settings.multi_start
        # Match CPU logic: split total depth across runs (Micro-GA strategy)
        # or use full depth if multi-start is 1.
        gens_per_run = max(1, (ga_depth + num_runs - 1) // num_runs)

        print(f"  Multi-start runs: {num_runs} (generations per run: {gens_per_run})")

        # GPU-native GA exploration knobs (optional; defaults preserve current behavior)
        gpu_tournament_k = safe_int(cfg.get("IterationEngine", "GPU_GA_TournamentK", fallback=3), 3)
        gpu_tournament_k = max(1, min(8, int(gpu_tournament_k)))

        gpu_mutation_rate = safe_float(
            cfg.get("IterationEngine", "GPU_GA_MutationRate", fallback=GA_MUTATION_RATE), GA_MUTATION_RATE
        )
        gpu_mutation_rate = max(0.0, min(1.0, float(gpu_mutation_rate)))

        gpu_immigrant_rate = safe_float(cfg.get("IterationEngine", "GPU_GA_ImmigrantRate", fallback=0.0), 0.0)
        gpu_immigrant_rate = max(0.0, min(1.0, float(gpu_immigrant_rate)))

        # Buffer per-run snapshots on GPU and download once per song to avoid
        # per-run GPU->CPU sync (Vulkan `to_numpy()` is expensive).
        from .taichi_gem import fields as gpu_fields

        n_slots = 9
        n_genomes = None
        payload_segments: list[np.ndarray] = []
        segment_runs = 0

        def _flush_ga_run_payload_segment() -> None:
            nonlocal segment_runs
            if segment_runs <= 0:
                return
            if n_genomes is None:
                raise RuntimeError("Internal error: n_genomes not set before GA payload flush")
            payload_segments.append(
                gpu_api.ga_download_runs_payload(n_runs=segment_runs, n_genomes=n_genomes, n_slots=n_slots)
            )
            segment_runs = 0

        def _is_vulkan_semaphore_failure(exc: BaseException) -> bool:
            msg = str(exc)
            return ("failed to create semaphore" in msg) or ("RHI Error" in msg and "semaphore" in msg)

        # Stability: reset Taichi runtime periodically on Vulkan to avoid long-run
        # resource exhaustion (seen as random "failed to create semaphore" crashes).
        # NOTE: Periodic runtime reset is OFF by default because it adds heavy
        # overhead (ti.reset() + ti.init() + field allocation) and can dominate
        # throughput when processing large queues. Enable only if you still hit
        # Vulkan backend instability.
        reset_every_runs_env = os.environ.get("GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS", "0")
        try:
            reset_every_runs = int(reset_every_runs_env)
        except Exception:
            reset_every_runs = 0

        max_retries_env = os.environ.get("GPU_NATIVE_GA_VULKAN_RETRIES", "1")
        try:
            max_retries = int(max_retries_env)
        except Exception:
            max_retries = 1

        # Segment state for batched initial population uploads.
        segment_start_global = 0
        segment_total_runs = 0
        segment_pop_ids = None  # np.ndarray[int32] shape (segment_total_runs, n_genomes, n_slots)
        segment_pop_uploaded = False

        for run_idx in range(num_runs):
            # Start a new segment whenever we exhausted the staged buffer.
            if segment_pop_ids is None or run_idx >= (segment_start_global + segment_total_runs):
                segment_start_global = run_idx
                segment_total_runs = min(gpu_fields.MAX_GA_RUNS, num_runs - run_idx)
                segment_pop_uploaded = False

                if os.environ.get("GPU_NATIVE_GA_LOG_PROGRESS", "0").strip().lower() in {"1", "true", "yes", "on"}:
                    print(f"  >> Prebuilding {segment_total_runs} initial populations (batched upload)...")
                seg_buf = None
                for j in range(segment_total_runs):
                    pop = build_initial_population(
                        create_random_genome,
                        create_heuristic_genome,
                        reconstruct_genome_from_db_list,
                        build_seed_list_from_record,
                        mutate_genome_once,
                        db_seed,
                        ga_settings,
                        fixed_gear,
                        fixed_minis,
                        force_db_seed=False,
                    )
                    if n_genomes is None:
                        n_genomes = len(pop)
                        if n_genomes > gpu_fields.MAX_GA_RUN_GENOMES:
                            raise RuntimeError(
                                f"GPU GA population too large for run buffer: {n_genomes} > {gpu_fields.MAX_GA_RUN_GENOMES}"
                            )
                    if seg_buf is None:
                        seg_buf = np.zeros((segment_total_runs, n_genomes, n_slots), dtype=np.int32)
                    seg_buf[j, :, :n_slots] = registry.encode_population(pop)
                segment_pop_ids = seg_buf

            if os.environ.get("GPU_NATIVE_GA_LOG_PROGRESS", "0").strip().lower() in {"1", "true", "yes", "on"}:
                print(f"  >> GPU GA Run {run_idx + 1}/{num_runs}...")

            if reset_every_runs > 0 and run_idx > 0 and (run_idx % reset_every_runs) == 0:
                try:
                    # Preserve buffered run payloads before resetting Taichi runtime.
                    _flush_ga_run_payload_segment()
                    gpu_api.hard_reset_taichi(reason=f"periodic Vulkan reset at run {run_idx + 1}/{num_runs}")
                    load_ref_arrays(ref_arrays)
                    precompute_timeline_gpu(calc_song, ref_arrays, song_slot=song_slot)
                    gpu_api.ga_upload_item_stats(
                        gpu_data["item_stats"],
                        gpu_data["slot_start"],
                        gpu_data["slot_count"],
                    )
                    gpu_api.ga_upload_base_fixed_stats(base_stats_arr)
                    segment_pop_uploaded = False
                except Exception as e:
                    print(f"[GPU GA] Warning: periodic reset failed: {e}")

            # Ensure the segment's initial populations are staged on GPU (re-upload after resets).
            if not segment_pop_uploaded:
                gpu_api.ga_upload_initial_populations(
                    segment_pop_ids,
                    n_runs=segment_total_runs,
                    n_genomes=n_genomes,
                    n_slots=n_slots,
                )
                segment_pop_uploaded = True

            # Load this run's initial population into active GA buffers (GPU->GPU copy).
            local_run_idx = run_idx - segment_start_global
            gpu_api.ga_load_initial_population(run_idx=local_run_idx, n_genomes=n_genomes, n_slots=n_slots)

            # Run GPU-Native GA (retry/reset on Vulkan semaphore failures)
            last_exc = None
            for attempt in range(max_retries + 1):
                try:
                    _run_gpu_native_ga(
                        population=None,
                        n_generations=gens_per_run,
                        registry=registry,
                        cfg_data=cfg_data,
                        calc_song=calc_song,
                        ref_arrays=ref_arrays,
                        base_stats_fixed=base_stats_fixed,
                        gpu_static={
                            "need_upload_item_stats": False,
                            "need_upload_base_fixed": False,
                            "item_stats": gpu_data["item_stats"],
                            "slot_start": gpu_data["slot_start"],
                            "slot_count": gpu_data["slot_count"],
                            "base_fixed_stats": base_stats_arr,
                        },
                        elite_count=GA_ELITISM,
                        mutation_rate=gpu_mutation_rate,
                        immigrant_rate=gpu_immigrant_rate,
                        tournament_k=gpu_tournament_k,
                        # Use color flags for correct p_val/s_val calculation
                        color_flags={
                            "is_p_ft": 1 if p_color == "Beat" else 0,
                            "is_s_ft": 1 if s_color == "Beat" else 0,
                            "is_p_ff": 1 if p_color == "Vibe" else 0,
                            "is_s_ff": 1 if s_color == "Vibe" else 0,
                            "is_p_pp": 1 if p_color == "Chill" else 0,
                            "is_s_pp": 1 if s_color == "Chill" else 0,
                            "is_p_cm": 1 if p_color == "Flow" else 0,
                            "is_s_cm": 1 if s_color == "Flow" else 0,
                            "is_p_fm": 1 if p_color == "Rush" else 0,
                            "is_s_fm": 1 if s_color == "Rush" else 0,
                            "is_p_ov": 1 if selected_color == p_color else 0,
                            "is_s_ov": 1 if selected_color == s_color else 0,
                        },
                        status_cb=status_cb,
                        song_slot=song_slot,  # Use prefetched GPU slot
                        store_payload_idx=segment_runs,
                        store_payload_only=True,
                        n_genomes_override=n_genomes,
                        population_preloaded=True,
                    )
                    last_exc = None
                    break
                except Exception as e:
                    last_exc = e
                    if attempt >= max_retries or not _is_vulkan_semaphore_failure(e):
                        break
                    print(
                        f"[GPU GA] Vulkan backend error; retrying run after reset (attempt {attempt + 1}/{max_retries})"
                    )
                    try:
                        # Preserve buffered run payloads before resetting Taichi runtime.
                        _flush_ga_run_payload_segment()
                        gpu_api.hard_reset_taichi(reason=str(e).splitlines()[0][:200])
                        load_ref_arrays(ref_arrays)
                        precompute_timeline_gpu(calc_song, ref_arrays, song_slot=song_slot)
                        gpu_api.ga_upload_item_stats(
                            gpu_data["item_stats"],
                            gpu_data["slot_start"],
                            gpu_data["slot_count"],
                        )
                        gpu_api.ga_upload_base_fixed_stats(base_stats_arr)
                        # Restore staged initial populations for the retry (reset clears GPU buffers).
                        gpu_api.ga_upload_initial_populations(
                            segment_pop_ids,
                            n_runs=segment_total_runs,
                            n_genomes=n_genomes,
                            n_slots=n_slots,
                        )
                        segment_pop_uploaded = True
                        gpu_api.ga_load_initial_population(run_idx=local_run_idx, n_genomes=n_genomes, n_slots=n_slots)
                    except Exception as reset_exc:
                        print(f"[GPU GA] Reset failed: {reset_exc}")
                        break

            if last_exc is not None:
                raise last_exc

            segment_runs += 1
            if segment_runs >= gpu_fields.MAX_GA_RUNS:
                _flush_ga_run_payload_segment()

        _flush_ga_run_payload_segment()

        # One-time download and CPU-side aggregation (preserves prior behavior/order).
        if not payload_segments:
            raise RuntimeError("Internal error: no GA run payloads were stored")
        runs_payload = payload_segments[0] if len(payload_segments) == 1 else np.concatenate(payload_segments, axis=0)
        if runs_payload.shape[0] != num_runs:
            runs_payload = runs_payload[:num_runs]

        best_global_score = -1
        best_global_genome = None
        best_global_res_arr = None
        all_evaluated_global = []

        fg_candidate_limit = int(cfg_data.get("fg_candidate_limit", FG_CANDIDATE_LIMIT))
        if fg_candidate_limit <= 0:
            fg_candidate_limit = FG_CANDIDATE_LIMIT

        for r in range(num_runs):
            run_pack = runs_payload[r]
            run_best_score = int(run_pack[0, 0])
            run_best_ids = np.asarray(run_pack[0, 1 : 1 + n_slots], dtype=np.int32)
            run_best_res = np.asarray(run_pack[0, 1 + n_slots : 1 + n_slots + 7], dtype=np.int32)

            if run_best_score > best_global_score:
                best_global_score = run_best_score
                best_global_genome = registry.decode_genome(run_best_ids)
                best_global_res_arr = run_best_res.copy()

            pop_snapshot = run_pack[1 : n_genomes + 1, 1 : 1 + n_slots]
            results_snapshot = run_pack[1 : n_genomes + 1, 1 + n_slots : 1 + n_slots + 7]
            scores_snapshot = run_pack[1 : n_genomes + 1, 0]
            all_evaluated_global.extend(
                _extract_fg_candidates_from_ga_snapshot(
                    registry=registry,
                    cfg_data=cfg_data,
                    base_stats_fixed=base_stats_fixed,
                    pop_snapshot=pop_snapshot,
                    results=results_snapshot,
                    scores=scores_snapshot,
                    n_genomes=n_genomes,
                    candidate_limit=fg_candidate_limit,
                )
            )

        # 8. Format results to match expected return signature
        # Use simple fallback if no valid genome found (shouldn't happen)
        if best_global_genome is None:
            # Should practically never happen unless 0 runs / all scores invalid.
            try:
                fallback_ids = np.asarray(runs_payload[0, 0, 1 : 1 + n_slots], dtype=np.int32)
                best_global_genome = registry.decode_genome(fallback_ids)
                best_global_score = int(runs_payload[0, 0, 0])
                best_global_res_arr = np.asarray(
                    runs_payload[0, 0, 1 + n_slots : 1 + n_slots + 7], dtype=np.int32
                ).copy()
            except Exception:
                best_global_genome = []
                best_global_score = 0
                best_global_res_arr = [0] * 7

        best_gear = best_global_genome[:6]
        best_minis = best_global_genome[6:9]

        # Compute full stats for best genome (like FG candidates)
        best_stats = base_stats_fixed.copy()
        for item in best_global_genome:
            for k, v in item.items():
                if k not in SKIP_ITEM_KEYS:
                    best_stats[k] = best_stats.get(k, 0) + v

        # Add gem contributions
        g_ft = int(best_global_res_arr[1])
        g_ff = int(best_global_res_arr[2])
        g_pp = int(best_global_res_arr[3])
        g_cm = int(best_global_res_arr[4])
        g_fm = int(best_global_res_arr[5])
        g_ov = int(best_global_res_arr[6])

        best_stats["Perfect Points"] = best_stats.get("Perfect Points", 0) + g_pp * GEM_SCALE_NORMAL
        best_stats["Combo Multiplier"] = best_stats.get("Combo Multiplier", 0) + g_cm * GEM_SCALE_NORMAL
        best_stats["Fever Multiplier"] = best_stats.get("Fever Multiplier", 0) + g_fm * GEM_SCALE_FEVER
        best_stats["Fever Time"] = best_stats.get("Fever Time", 0) + g_ft * GEM_SCALE_FEVER
        best_stats["Fever Fill Rate"] = best_stats.get("Fever Fill Rate", 0) + g_ff * GEM_SCALE_FEVER

        best_stats["Chill"] = best_stats.get("Chill", 0) + g_pp * GEM_STAT_TO_ELEMENT_SCALE
        best_stats["Flow"] = best_stats.get("Flow", 0) + g_cm * GEM_STAT_TO_ELEMENT_SCALE
        best_stats["Rush"] = best_stats.get("Rush", 0) + g_fm * GEM_STAT_TO_ELEMENT_SCALE
        best_stats["Beat"] = best_stats.get("Beat", 0) + g_ft * GEM_STAT_TO_ELEMENT_SCALE
        best_stats["Vibe"] = best_stats.get("Vibe", 0) + g_ff * GEM_STAT_TO_ELEMENT_SCALE

        if selected_color:
            best_stats[selected_color] = best_stats.get(selected_color, 0) + g_ov * ELEMENTAL_GEM_SCALE

        best_data = {
            "Score": best_global_score,
            "BaseScore": best_global_score,
            "Genome": best_global_genome,
            "Gear": best_gear,
            "Minis": best_minis,
            "GearNames": [g.get("Name", "None") for g in best_gear],
            "MiniNames": [m.get("Name", "None") for m in best_minis],
            # FT/FF at root level for build_details() compatibility
            "FT": g_ft,
            "FF": g_ff,
            "GemCounts": {
                "Perfect Points": g_pp,
                "Combo Multiplier": g_cm,
                "Fever Multiplier": g_fm,
                "Element": g_ov,
            },
            "Stats": best_stats,  # Full computed stats
            "Selected Element": selected_color,  # For correct overflow gem labeling
            # Reconstruct result details from kernel output
            # [score, ft, ff, pp, cm, fm, ov]
            "Details": {
                "FeverGems": g_ft,
                "FeverFillGems": g_ff,
                "PP": g_pp,
                "CM": g_cm,
                "FM": g_fm,
                "OV": g_ov,
            },
        }

        print(f"=== GPU-NATIVE GA COMPLETE: Best Score {best_global_score} ===")

        # Deduplicate all_evaluated to prevent duplicate loadouts from multiple runs
        # Key by tuple of names (Gear + Minis)
        unique_evaluated = []
        seen_hashes = set()

        for cand in all_evaluated_global:
            # Create a stable hashable key from gear names and mini names
            # Genome usually has 9 dicts.
            key_parts = []
            for item in cand.get("Genome", []):
                key_parts.append(item.get("Name", ""))

            cand_hash = tuple(key_parts)
            if cand_hash not in seen_hashes:
                seen_hashes.add(cand_hash)
                unique_evaluated.append(cand)

        # Select an FG-aware funnel (mix base-score strength + fever-stat potential + diversity).
        unique_evaluated = select_fg_candidates(
            unique_evaluated,
            limit=max(LOADOUTS_PER_SONG_LIMIT, fg_candidate_limit),
            primary_color=str(p_color or ""),
            secondary_color=str(s_color or ""),
        )

        # Optional: FG neighbor sweep (cold-start reliability)
        try:
            if cfg.getboolean("IterationEngine", "ForceGreatsFinder", fallback=False):
                neighbors = _neighbor_sweep_fg_candidates(
                    cfg=cfg,
                    existing_candidates=unique_evaluated,
                    registry=registry,
                    gear_pool=gear_pool,
                    mini_pool=mini_pool,
                    slots=slots,
                    cfg_data=cfg_data,
                    base_stats_fixed=base_stats_fixed,
                    calc_song=calc_song,
                    ref_arrays=ref_arrays,
                )
                if neighbors:
                    merged = []
                    seen = set()

                    def _key(cand: dict) -> tuple:
                        genome = cand.get("Genome") or []
                        gear_names = tuple((it or {}).get("Name", "") for it in genome[:6])
                        mini_names = tuple(sorted(((it or {}).get("Name", "") for it in genome[6:9])))
                        return gear_names + mini_names

                    for cand in unique_evaluated:
                        k = _key(cand)
                        if k in seen:
                            continue
                        seen.add(k)
                        merged.append(cand)

                    for cand in neighbors:
                        k = _key(cand)
                        if k in seen:
                            continue
                        seen.add(k)
                        merged.append(cand)

                    # Keep a wider candidate funnel here; the downstream FG stage is
                    # explicitly capped by `FG_CandidateLimit` and should decide which
                    # candidates to evaluate. Do not truncate purely by base score
                    # (regression risk); if we must cap, use the FG-aware selector.
                    max_keep = max(LOADOUTS_PER_SONG_LIMIT, fg_candidate_limit)
                    max_keep = max(max_keep, min(5000, max_keep * 10))
                    if len(merged) > max_keep:
                        unique_evaluated = select_fg_candidates(
                            merged,
                            limit=max_keep,
                            primary_color=str(p_color or ""),
                            secondary_color=str(s_color or ""),
                        )
                    else:
                        unique_evaluated = merged
        except Exception:
            # Never allow candidate augmentation to crash the GA solver.
            pass

        # FG booster(s): optional candidate augmentation to improve ForceGreatsFinder coverage
        # without inflating the downstream candidate limit (we re-select to the same funnel size).
        try:
            force_greats_enabled = cfg.getboolean("IterationEngine", "ForceGreatsFinder", fallback=False)
            beam_enabled = str(os.environ.get("FG_BEAM_BOOSTER_ENABLED", "0") or "").strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
            combo_enabled = str(os.environ.get("FG_COMBO_BOOSTER_ENABLED", "1") or "").strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }

            boosted = None
            if force_greats_enabled and beam_enabled:
                boosted = build_fg_beam_booster_candidates(
                    existing_candidates=list(unique_evaluated or []),
                    registry=registry,
                    base_stats_fixed=base_stats_fixed,
                    cfg_data=cfg_data,
                    calc_song=calc_song,
                    ref_arrays=ref_arrays,
                    primary_color=str(p_color or ""),
                    secondary_color=str(s_color or ""),
                    song_slot=int(song_slot),
                )
            elif force_greats_enabled and combo_enabled:
                boosted = build_fg_combo_booster_candidates(
                    existing_candidates=list(unique_evaluated or []),
                    registry=registry,
                    base_stats_fixed=base_stats_fixed,
                    cfg_data=cfg_data,
                    calc_song=calc_song,
                    ref_arrays=ref_arrays,
                    primary_color=str(p_color or ""),
                    secondary_color=str(s_color or ""),
                    song_slot=int(song_slot),
                )

            if boosted:
                unique_evaluated = select_fg_candidates(
                    list(unique_evaluated or []) + list(boosted),
                    limit=max(LOADOUTS_PER_SONG_LIMIT, fg_candidate_limit),
                    primary_color=str(p_color or ""),
                    secondary_color=str(s_color or ""),
                )
                hydrate_fg_candidate_stats(
                    unique_evaluated,
                    base_stats_fixed=base_stats_fixed,
                    selected_color=str(cfg_data.get("selected_color", "") or ""),
                )
        except Exception:
            pass

        return best_data, best_gear, best_minis, None, [], [], unique_evaluated

    # --- MEMETIC GA PARAMETERS (configurable from [IterationEngine]) ---
    if ga_settings.memetic_elites > 0 and ga_settings.memetic_steps > 0:
        print(
            f"[Memetic GA] Enabled: elites={ga_settings.memetic_elites}, "
            f"steps={ga_settings.memetic_steps}, top_gear={ga_settings.memetic_top_gear}, "
            f"top_minis={ga_settings.memetic_top_minis}"
        )
    else:
        print("[Memetic GA] Disabled (elites or steps <= 0).")

    # Create evaluation functions and caches
    cache_hits_tracker = [0]  # Mutable container for tracking cache hits
    (
        score_candidate,
        genome_key,
        check_persistent_cache,
        evaluate_genome_local,
        evaluation_cache,
        batch_evaluator,
    ) = create_evaluation_functions(
        p_color,
        base_stats_fixed,
        cfg_data,
        calc_song,
        ref_arrays,
        known_loadouts,
        cache_hits_tracker,
        getattr(ga_settings, "heuristic_mode", "modern"),
    )

    # Build ranked candidate caches
    gear_rank_max = getattr(ga_settings, "gear_rank_max", 40)
    mini_rank_max = getattr(ga_settings, "mini_rank_max", 40)
    gear_rank_cache = {s: sorted(gear_pool[s], key=score_candidate, reverse=True)[:gear_rank_max] for s in slots}
    sorted_minis = sorted(mini_pool, key=score_candidate, reverse=True)
    mini_rank_cache = sorted_minis[:mini_rank_max]

    # Create genome factory functions
    (
        create_random_genome,
        create_heuristic_genome,
        reconstruct_genome_from_db_list,
        build_seed_list_from_record,
        mutate_genome_once,
    ) = create_genome_functions(
        gear_pool,
        mini_pool,
        gear_rank_cache,
        mini_rank_cache,
        gears_by_name,
        minis_by_name,
        slots,
        optimize_gear,
        optimize_minis,
        fixed_gear,
        fixed_minis,
    )

    # Create local search functions
    run_local_search, polish_best_genome, memetic_local_search, batch_memetic_local_search = (
        create_local_search_function(
            evaluate_genome_local,
            batch_evaluator,
            gear_rank_cache,
            mini_rank_cache,
            mini_pool,
            gear_pool,
            slots,
            optimize_gear,
            optimize_minis,
            ga_settings=ga_settings,
        )
    )

    # Setup multi-start runs
    num_runs = ga_settings.multi_start
    gens_per_run = max(1, (ga_depth + num_runs - 1) // num_runs)
    print(f"Multi-start runs: {num_runs} (generations per run: {gens_per_run})")

    best_global_score = -1
    best_global_genome = []
    best_global_data = {}

    # Store each run's best for comparison at the end
    run_results = []  # List of (score, genome, data) tuples

    # Cross-run elite sharing: DISABLED - each run is independent now
    # global_elites = []

    # Soft non-regression guard:
    # Evaluate DB seed once up-front and cache it, but DON'T lock it as global best.
    # This allows the GA to explore freely without being anchored to the DB score.
    # We only use the DB seed for non-regression comparison at the END.
    db_seed_score = -1
    db_seed_genome = None
    db_seed_data = None
    if db_seed:
        try:
            seed_list = build_seed_list_from_record(db_seed)
            if seed_list:
                seed_genome = reconstruct_genome_from_db_list(seed_list)
                seed_res = worker_coevolution_evaluate((seed_genome, base_stats_fixed, cfg_data, calc_song, ref_arrays))
                evaluation_cache[genome_key(seed_genome)] = seed_res
                # Use BaseScore (true score) for DB comparison. (Score is the GA fitness score
                # and is currently the same as BaseScore.)
                db_seed_score = seed_res.get("BaseScore") or seed_res["Score"]
                db_seed_genome = seed_genome
                db_seed_data = seed_res["Data"]
                print(f" >> [Evolution] DB seed baseline (soft): {db_seed_score}")
        except Exception as exc:
            print(f" >> [Evolution] Warning: failed to evaluate DB seed: {exc}")

    # Read Deep Mining config
    if ga_settings.deep_mining_enabled:
        print(" >> [Deep Mining] Enabled: Will extend search based on cache hits.")
    else:
        print(" >> [Deep Mining] Disabled: Fixed generation count.")

    # Main multi-start GA loop
    for run_idx in range(num_runs):
        print(f"\n--- GA Run {run_idx + 1}/{num_runs} ---")
        if status_cb:
            status_cb(f"Run {run_idx + 1}/{num_runs} starting")

        # Initialize population
        population = build_initial_population(
            create_random_genome,
            create_heuristic_genome,
            reconstruct_genome_from_db_list,
            build_seed_list_from_record,
            mutate_genome_once,
            db_seed,
            ga_settings,
            fixed_gear,
            fixed_minis,
            force_db_seed=False,  # Use db_seed_prob probability instead of guaranteed injection
        )

        # Track progress within THIS run (not global best).
        # This avoids "false stagnation" when the global best is already locked.
        best_run_score = -1
        last_improvement_gen = 0

        # Reset global best at start of each run to ensure independence
        # The best across all runs will be selected after all runs complete
        best_global_score = -1
        best_global_genome = []
        best_global_data = {}

        base_stagnation_limit = max(8, gens_per_run // 2)
        explore_stagnation_limit = max(8, gens_per_run // 3)
        mutation_rate = GA_MUTATION_RATE

        # Dynamic generation limit based on cache hits
        current_run_gens = gens_per_run
        cache_hits_tracker[0] = 0  # Reset for each run
        generation = 0
        current_mutation_rate = mutation_rate

        # Evolution loop
        while generation < current_run_gens:
            generation += 1

            # Evaluate population in parallel
            results = evaluate_population_parallel(
                population,
                genome_key,
                evaluation_cache,
                check_persistent_cache,
                base_stats_fixed,
                cfg_data,
                calc_song,
                ref_arrays,
                executor,
                cache_hits_tracker,
                use_gpu_batch=cfg_data.get("use_gpu", False),
            )

            # Track best candidate (global best with tie-awareness)
            def consider_candidate(cand):
                nonlocal best_global_score, best_global_genome, best_global_data
                cand_score = cand["Score"]
                cand_genome = cand["Genome"]
                cand_data = cand["Data"]
                # CRITICAL: Inject BaseScore into cand_data so build_db_payload can access it.
                # The outer wrapper has BaseScore (true score), but cand_data (inner dict) doesn't.
                # Without this, build_db_payload uses cand_data["Score"] which may be outdated.
                if "BaseScore" in cand:
                    cand_data["BaseScore"] = cand["BaseScore"]
                best_key = genome_key(best_global_genome) if best_global_genome else None
                cand_key = genome_key(cand_genome)

                if cand_score > best_global_score:
                    best_global_score = cand_score
                    best_global_genome = cand_genome
                    best_global_data = cand_data
                    return 2  # strict improvement

                if cand_score == best_global_score and cand_key != best_key:
                    # Same score, different loadout: treat as a variant, not an improvement.
                    best_global_genome = cand_genome
                    best_global_data = cand_data
                    return 1  # tie variant

                return 0

            # --- MEMETIC GA STEP: local search on top elites ---
            if ga_settings.memetic_elites > 0 and ga_settings.memetic_steps > 0:
                elite_count = min(ga_settings.memetic_elites, len(results))

                # BATCHED PATH: Process all elites simultaneously
                # This reduces kernel launch overhead by packing all neighbors into fewer batches.
                seed_genomes = [results[i]["Genome"] for i in range(elite_count)]
                improved_results = batch_memetic_local_search(
                    seed_genomes,
                    ga_settings.memetic_steps,
                    ga_settings.memetic_top_gear,
                    ga_settings.memetic_top_minis,
                )

                # Update population with improved versions if score increased
                for i, improved_res in enumerate(improved_results):
                    if improved_res["Score"] > results[i]["Score"]:
                        results[i] = improved_res

                # Resort after memetic improvements
                results.sort(key=lambda x: x["Score"], reverse=True)

            # Best candidate AFTER memetic (this is the generation winner)
            best_cand = results[0]

            # Update run-best tracking (used for stagnation handling)
            if best_cand["Score"] > best_run_score:
                best_run_score = best_cand["Score"]
                last_improvement_gen = generation
                mutation_rate = GA_MUTATION_RATE

            promote_status = consider_candidate(best_cand)
            if promote_status == 2:
                m_names = best_cand["MiniNames"]
                print(f"  >> Gen {generation} (Run {run_idx + 1}): New Best {best_global_score} (Minis: {m_names})")
                if status_cb:
                    status_cb(f"Run {run_idx + 1}/{num_runs} Gen {generation}: New Best {best_global_score}")
            elif promote_status == 1:
                # Tie score, but a different loadout at the same global score.
                # Don't call it a "new best" to avoid confusing plateaus with improvements.
                if generation % 10 == 0:
                    m_names = best_cand["MiniNames"]
                    print(
                        f"  >> Gen {generation} (Run {run_idx + 1}): BestVariant {best_global_score} (Minis: {m_names})"
                    )
            else:
                if generation % 10 == 0:
                    print(
                        f"  >> Gen {generation} (Run {run_idx + 1}): "
                        f"BestInRun {best_cand['Score']} | GlobalBest {best_global_score}"
                    )
                    if status_cb:
                        status_cb(
                            f"Run {run_idx + 1}/{num_runs} Gen {generation}: "
                            f"BestInRun {best_cand['Score']} | GlobalBest {best_global_score}"
                        )

            # Generate next generation via crossover and mutation
            next_gen = perform_crossover_mutation(
                results,
                create_random_genome,
                mini_pool,
                gear_pool,
                slots,
                optimize_gear,
                optimize_minis,
                fixed_minis,
                current_mutation_rate,
                global_elites=None,  # Cross-run sharing disabled - runs are independent
            )

            population = next_gen
            next_gen = None  # Break reference to help GC

            # Compute dynamic mutation rate and generation limit
            current_mutation_rate, current_run_gens = compute_dynamic_mutation(
                mutation_rate,
                cache_hits_tracker[0],
                generation,
                current_run_gens,
                gens_per_run,
                ga_settings,
            )

            # Cache-hit driven exploration boost is only applied when DeepMining is enabled.
            total_evals_so_far = generation * GA_POPULATION_SIZE
            hit_ratio = cache_hits_tracker[0] / max(1, total_evals_so_far)
            exploration_boost = min(0.2, hit_ratio * 0.5) if ga_settings.deep_mining_enabled else 0.0

            # Handle stagnation
            # If this run is far below the global best, trigger diversity injection sooner
            # to avoid wasting many generations in a clearly inferior basin.
            stagnation_limit = base_stagnation_limit
            if best_global_score > 0 and best_run_score > 0 and best_run_score < best_global_score:
                stagnation_limit = explore_stagnation_limit

            population, mutation_rate, last_improvement_gen = update_mutation_and_diversity(
                population,
                results,
                generation,
                last_improvement_gen,
                stagnation_limit,
                mutation_rate,
                create_random_genome,
                create_heuristic_genome,
                run_idx,
                current_mutation_rate,
                exploration_boost,
                mini_pool=mini_pool,
                gear_pool=gear_pool,
                slots=slots,
                optimize_gear=optimize_gear,
                optimize_minis=optimize_minis,
            )

        # Cross-run elite sharing: add this run's best to the global elite pool.
        # This makes discoveries available for crossover in subsequent runs.
        if best_run_score > 0:
            # Store this run's best result (using heuristic Score for GA selection)
            run_best_genome = results[0]["Genome"] if results else None
            run_best_score = results[0]["Score"] if results else -1
            run_best_data = results[0]["Data"] if results else {}
            if run_best_genome and run_best_score > 0:
                run_results.append((run_best_score, run_best_genome, run_best_data))

    # Select the best result across all independent runs (using true base scores)
    for run_score, run_genome, run_data in run_results:
        if run_score > best_global_score:
            best_global_score = run_score
            best_global_genome = run_genome
            best_global_data = run_data

    # Polish best genome with exhaustive local search
    if best_global_genome:
        polished_result, polished_genome = polish_best_genome(best_global_genome)

        # If result was cached, re-evaluate fully to get all details
        if polished_result.get("_cached"):
            polished_result = worker_coevolution_evaluate(
                (polished_genome, base_stats_fixed, cfg_data, calc_song, ref_arrays)
            )

        # Use Score for GA selection (BaseScore only for DB comparisons)
        polished_score = polished_result["Score"]

        if polished_score > best_global_score:
            best_global_score = polished_score
            best_global_data = polished_result["Data"]
            best_global_genome = polished_genome

    # Soft non-regression guard: If GA's best is worse than DB seed, fall back.
    # This ensures we never regress while still allowing free exploration.
    # Compare using true base score.
    ga_true_score = (
        best_global_data.get("BaseScore", best_global_data.get("Score", 0)) if best_global_data else best_global_score
    )
    if db_seed_score > ga_true_score and db_seed_genome:
        print(f" >> [Evolution] GA best ({ga_true_score}) < DB seed ({db_seed_score}); using DB seed.")
        best_global_score = db_seed_score
        best_global_genome = db_seed_genome
        best_global_data = db_seed_data

    # CRITICAL: Re-evaluate if best_global_data is missing GemCounts (from DB cache path).
    # This ensures the final result always has complete gem allocation details for display.
    if best_global_genome and best_global_data and "GemCounts" not in best_global_data:
        full_result = worker_coevolution_evaluate(
            (best_global_genome, base_stats_fixed, cfg_data, calc_song, ref_arrays)
        )
        best_global_data = full_result["Data"]

    best_gear = best_global_genome[:6] if best_global_genome else []
    best_minis = best_global_genome[6:] if best_global_genome else []

    # Return all unique evaluated loadouts from the cache
    all_evaluated = list(evaluation_cache.values())

    # Memory leak fix: Clear cache immediately after extraction
    # This prevents the cache from lingering until function exit
    evaluation_cache.clear()

    # Memory leak fix: Clear all generation-scoped data before returning
    population = None
    results = None

    if not best_global_data:
        print(f"[GA Error] GA completed but found no valid candidates (best_global_score={best_global_score})")

    return (
        best_global_data if best_global_data else None,
        best_gear,
        best_minis,
        None,
        [],
        [],
        all_evaluated,  # All unique loadouts evaluated by GA (capped before DB persistence)
    )
