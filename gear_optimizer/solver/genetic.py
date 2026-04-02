"""
Genetic algorithm solver for gear and mini co-evolution.

This module contains the main GA that optimizes both gear (6 slots) and minis (3 slots)
simultaneously to find optimal loadouts. Uses tournament selection, crossover, mutation,
and memetic local search.

The main function solve_coevolution_genetic() has been refactored to use helper functions
from helpers.ga_helpers for improved modularity and maintainability.
"""

import os
import logging
import random
import time
import importlib.util

import numpy as np

_TRUTHY_ENV = {"1", "true", "yes", "on"}
logger = logging.getLogger(__name__)


def _env_flag(name: str, default: str = "0") -> bool:
    return str(os.environ.get(name, default) or "").strip().lower() in _TRUTHY_ENV


def _env_int(name: str, default: int) -> int:
    try:
        return int(str(os.environ.get(name, str(default)) or str(default)).strip())
    except Exception:
        return int(default)


def _ga_redundancy_audit_enabled() -> bool:
    return _env_flag("GA_REDUNDANCY_AUDIT", "0")


# Support deterministic testing via GA_SEED environment variable
_GA_SEED = os.environ.get("GA_SEED")
if _GA_SEED is not None:
    _GA_SEED = int(_GA_SEED)
    random.seed(_GA_SEED)
    logger.info(f"[GA] Deterministic mode: seed={_GA_SEED}")

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
from ..core.config import read_fg_candidate_limit
from ..core.color_flags import build_color_flags
from ..core.env_config import env_flag
from ..core.utils import safe_int, safe_float
from .base_stats import (
    COLOR_TO_STAT_INDEX,
    STAT_NAMES,
    build_base_fixed_stats_array,
    build_stats_array,
    build_stats_dict,
)
from .scoring import GEM_SOLVER_CACHE, FG_CACHE, FEVER_TIMELINE_CACHE
from .scoring.stats_ops import apply_gems_to_base_stats
from ..data.models import GASettings
from ..helpers.ga_helpers import (
    initialize_pools,
)
from ..helpers.ga_helpers.steady_state import (
    build_steady_state_initial_population_ids,
    build_steady_state_next_population_ids,
    extend_seen_archive_keys,
    resolve_steady_state_settings,
)
from ..helpers.ga_helpers.unique_eval import select_exact_unique_row_indices
from ..helpers.ga_helpers.redundancy_audit import (
    analyze_ga_redundancy_from_runs_payload,
    summarize_ga_redundancy_record,
    write_ga_redundancy_audit_record,
)
from ..helpers.song_helpers.fg_candidate_selector import select_fg_candidates
from ..helpers.song_helpers.fg_combo_booster import (
    build_fg_combo_booster_candidates,
    hydrate_fg_candidate_stats,
)
from ..helpers.song_helpers.force_greats.entry_utils import build_fg_group_meta
from .item_registry import ItemRegistry
from .convergence_trace import build_convergence_trace_writer

# Optional: GPU-native GA dependencies are probed without importing Taichi eagerly.
try:
    _GPU_NATIVE_AVAILABLE = importlib.util.find_spec("taichi") is not None
except Exception:
    _GPU_NATIVE_AVAILABLE = False


def _require_gpu_api():
    # Import on-demand so the app can auto-size GPU_SONG_SLOTS before Taichi fields allocate.
    try:
        from .taichi_gem import api as gpu_api  # type: ignore[no-redef]
    except Exception as exc:
        raise RuntimeError(f"GPU-native GA requires taichi_gem api/fields: {exc}") from exc
    return gpu_api


def _selected_color_stat_index(color: str) -> int:
    return int(COLOR_TO_STAT_INDEX.get(str(color or ""), -1))


def _build_gem_counts(g_pp: int, g_cm: int, g_fm: int, g_ov: int) -> dict[str, int]:
    return {
        "Perfect Points": int(g_pp),
        "Combo Multiplier": int(g_cm),
        "Fever Multiplier": int(g_fm),
        "Element": int(g_ov),
    }


def _build_gem_details(g_ft: int, g_ff: int, g_pp: int, g_cm: int, g_fm: int, g_ov: int) -> dict[str, int]:
    return {
        "FeverGems": int(g_ft),
        "FeverFillGems": int(g_ff),
        "PP": int(g_pp),
        "CM": int(g_cm),
        "FM": int(g_fm),
        "OV": int(g_ov),
    }


def _add_genome_item_stats(base_stats: dict, genome: list[dict]) -> dict:
    merged = dict(base_stats or {})
    for item in genome or []:
        if not item:
            continue
        for k, v in item.items():
            if k not in SKIP_ITEM_KEYS:
                merged[k] = merged.get(k, 0) + v
    return merged


def _build_best_result_payload(
    *,
    score: int,
    genome: list[dict],
    stats: dict,
    selected_color: str,
    g_ft: int,
    g_ff: int,
    g_pp: int,
    g_cm: int,
    g_fm: int,
    g_ov: int,
) -> dict:
    gear = list((genome or [])[:6])
    minis = list((genome or [])[6:9])
    return {
        "Score": int(score),
        "BaseScore": int(score),
        "Genome": list(genome or []),
        "Gear": gear,
        "Minis": minis,
        "GearNames": [g.get("Name", "None") for g in gear],
        "MiniNames": [m.get("Name", "None") for m in minis],
        "FT": int(g_ft),
        "FF": int(g_ff),
        "GemCounts": _build_gem_counts(g_pp, g_cm, g_fm, g_ov),
        "Stats": dict(stats or {}),
        "Selected Element": str(selected_color or ""),
        "Details": _build_gem_details(g_ft, g_ff, g_pp, g_cm, g_fm, g_ov),
    }


def _build_candidate_data_obj(
    *,
    score: int,
    selected_color: str,
    g_ft: int,
    g_ff: int,
    g_pp: int,
    g_cm: int,
    g_fm: int,
    g_ov: int,
    stats: dict | None = None,
    base_stats: dict | None = None,
    run_idx: int | None = None,
    row_idx: int | None = None,
) -> dict:
    data_obj = {
        "Score": int(score),
        "FT": int(g_ft),
        "FF": int(g_ff),
        "GemCounts": _build_gem_counts(g_pp, g_cm, g_fm, g_ov),
        "Selected Element": str(selected_color or ""),
        "BaseScore": int(score),
    }
    if isinstance(stats, dict):
        data_obj["Stats"] = stats
    if isinstance(base_stats, dict):
        data_obj["BaseStats"] = base_stats
    if run_idx is not None:
        data_obj["_ga_gpu_run_idx"] = int(run_idx)
    if row_idx is not None:
        data_obj["_ga_gpu_row_idx"] = int(row_idx)
    return data_obj


def _decode_requires_full_stats(cfg_data: dict | None) -> bool:
    # PRODUCTION: decode flag (GA_DECODE_INCLUDE_STATS).
    if env_flag("GA_DECODE_INCLUDE_STATS", "0"):
        return True
    if not isinstance(cfg_data, dict):
        return False
    return bool(cfg_data.get("ga_require_full_stats") or cfg_data.get("fg_require_full_stats"))


# PRODUCTION: GA_FORCE_COLD_START is a production runtime override for the GPU-native GA path.
# DEV / DEBUG: PERF_TIMING, GPU_NATIVE_GA_LOG_ISLAND_MODEL, GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS, GPU_NATIVE_GA_VULKAN_RETRIES, GPU_NATIVE_GA_BATCH_RUNS, GPU_NATIVE_GA_LOG_PROGRESS, GPU_NATIVE_GA_COLD_TAIL_GENS.
_GA_FORCE_COLD_START = _env_flag("GA_FORCE_COLD_START", "")
_PERF_TIMING = _env_flag("PERF_TIMING", "0")
_GPU_NATIVE_GA_LOG_ISLAND_MODEL = _env_flag("GPU_NATIVE_GA_LOG_ISLAND_MODEL", "0")
_GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS = _env_int("GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS", 0)
_GPU_NATIVE_GA_VULKAN_RETRIES = _env_int("GPU_NATIVE_GA_VULKAN_RETRIES", 1)
_GPU_NATIVE_GA_BATCH_RUNS = _env_int("GPU_NATIVE_GA_BATCH_RUNS", 0)
_GPU_NATIVE_GA_LOG_PROGRESS = _env_flag("GPU_NATIVE_GA_LOG_PROGRESS", "0")
# Warm-start (use_hints=1) uses a bounded local search that can under-score some genomes.
# Force a cold-scored tail so the final persisted winner is selected under canonical scoring.
_GPU_NATIVE_GA_COLD_TAIL_GENS = _env_int("GPU_NATIVE_GA_COLD_TAIL_GENS", 1)


if _GPU_NATIVE_AVAILABLE:

    def build_ga_init_heuristic_topk(
        *,
        item_stats: "np.ndarray",
        slot_start: "np.ndarray",
        slot_count: "np.ndarray",
        primary_color: str,
        secondary_color: str,
        heuristic_k: int,
        n_slots: int = 9,
    ) -> "np.ndarray | None":
        heuristic_k = int(heuristic_k)
        if heuristic_k <= 0:
            return None

        color_to_idx = {
            "Perfect Points": 0,
            "Combo Multiplier": 1,
            "Fever Multiplier": 2,
            "Beat": 5,
            "Vibe": 6,
            "Rush": 7,
            "Flow": 8,
            "Chill": 9,
        }
        p_idx = color_to_idx.get(str(primary_color or ""), -1)
        s_idx = color_to_idx.get(str(secondary_color or ""), -1)
        pp_idx = 0

        n_slots = int(n_slots)
        if n_slots <= 0:
            return None

        topk = np.zeros((n_slots, max(1, heuristic_k)), dtype=np.int32)
        for slot_i in range(n_slots):
            start_id = int(slot_start[slot_i])
            count = int(slot_count[slot_i])
            if count <= 0:
                continue
            ids = np.arange(start_id, start_id + count, dtype=np.int32)
            sc = np.zeros((count,), dtype=np.int64)
            if p_idx >= 0:
                sc += item_stats[ids, p_idx].astype(np.int64) * 2
            if s_idx >= 0:
                sc += item_stats[ids, s_idx].astype(np.int64)
            sc += item_stats[ids, pp_idx].astype(np.int64)
            k_eff = min(int(heuristic_k), int(count))
            if k_eff <= 0:
                continue
            order = np.lexsort((ids.astype(np.int64), -sc))
            sel = ids[order[:k_eff]]
            topk[slot_i, :k_eff] = sel
            if k_eff < heuristic_k:
                topk[slot_i, k_eff:heuristic_k] = sel[-1]
        return topk

    def extract_db_seed_ids(
        *,
        db_seed: dict | None,
        registry: "ItemRegistry",
        n_slots: int = 9,
    ) -> "np.ndarray | None":
        if not isinstance(db_seed, dict):
            return None
        try:
            n_slots = int(n_slots)
        except Exception:
            n_slots = 9
        if n_slots <= 0:
            n_slots = 9

        seed_ids = np.zeros((n_slots,), dtype=np.int32)
        try:
            gear_part = db_seed.get("gear") or db_seed.get("Gear") or []
            minis_part = db_seed.get("minis") or db_seed.get("Minis") or []
            for si in range(min(6, n_slots)):
                name = ""
                if si < len(gear_part):
                    gi = gear_part[si]
                    name = gi.get("Name", "") if isinstance(gi, dict) else str(gi or "")
                if name:
                    seed_ids[si] = int(registry.item_to_id.get((si, name), 0) or 0)
            for j, si in enumerate(range(6, min(9, n_slots))):
                name = ""
                if j < len(minis_part):
                    mi = minis_part[j]
                    name = mi.get("Name", "") if isinstance(mi, dict) else str(mi or "")
                if name:
                    seed_ids[si] = int(registry.item_to_id.get((si, name), 0) or 0)
        except Exception:
            return None
        if not bool(np.any(seed_ids[: min(9, n_slots)] != 0)):
            return None
        return seed_ids


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
    sel_color = cfg_data.get("selected_color", "")
    sel_color_idx = _selected_color_stat_index(sel_color)

    # Build base stats array for vectorized computation
    base_stats_arr = build_stats_array(base_stats_fixed)

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
        current_stats = build_stats_dict(final_stats)
        data_obj = _build_candidate_data_obj(
            score=score_val,
            selected_color=sel_color,
            g_ft=g_ft,
            g_ff=g_ff,
            g_pp=g_pp,
            g_cm=g_cm,
            g_fm=g_fm,
            g_ov=g_ov,
            stats=current_stats,
        )

        cand_data = {
            "Score": score_val,
            "BaseScore": score_val,
            "Genome": genome,
            "Gear": genome[:6],
            "Minis": genome[6:9],
            "GearNames": [g.get("Name", "None") for g in genome[:6]],
            "MiniNames": [m.get("Name", "None") for m in genome[6:9]],
            "Data": data_obj,
            "Details": _build_gem_details(g_ft, g_ff, g_pp, g_cm, g_fm, g_ov),
        }
        all_evaluated.append(cand_data)

    return all_evaluated


def _promote_best_candidate_over_header(
    *,
    best_data: dict,
    registry: "ItemRegistry",
    best_gear: list,
    best_minis: list,
    candidates: list[dict],
) -> tuple[dict, list, list]:
    # Sanity: prefer the true max score across decoded candidates if it exceeds
    # the header best score. This protects against rare GPU header reductions
    # being out-of-sync with the selected candidate table.
    try:
        best_score_run = int(best_data.get("BaseScore") or best_data.get("Score") or 0)
    except Exception:
        best_score_run = 0
    try:
        cand_best = max(candidates, key=lambda c: int(c.get("BaseScore") or c.get("Score") or 0))
    except Exception:
        cand_best = None
    if isinstance(cand_best, dict):
        try:
            cand_score = int(cand_best.get("BaseScore") or cand_best.get("Score") or 0)
        except Exception:
            cand_score = 0
        if cand_score > best_score_run:
            data_obj = cand_best.get("Data") or {}
            if isinstance(data_obj, dict):
                best_data = data_obj
            cand_ids = cand_best.get("GenomeIDs")
            if cand_ids is not None:
                try:
                    cand_genome = registry.decode_genome(np.asarray(cand_ids, dtype=np.int32))
                    best_gear = list(cand_genome[:6] or best_gear)
                    best_minis = list(cand_genome[6:9] or best_minis)
                except Exception:
                    pass

    return best_data, best_gear, best_minis


def decode_gpu_native_ga_runs_payload(
    *,
    runs_payload: "np.ndarray",
    registry: "ItemRegistry",
    cfg_data: dict,
    base_stats_fixed: dict,
    fg_candidate_limit: int,
    calc_song: dict | None = None,
    ref_arrays: dict | None = None,
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
    if runs_payload.ndim == 2:
        # GPU-selected payload format (preferred):
        # - Row 0: [selected_count, best_score, best_ids(9), best_results(7), best_run_idx, ...]
        # - Rows 1..N: [run_idx, row_idx, packed_row(24)]
        n_slots = 9
        header_cols_min = 2 + n_slots + 7 + 1
        if int(runs_payload.shape[0]) < 1:
            raise ValueError("runs_payload has no rows")
        if int(runs_payload.shape[1]) < header_cols_min:
            raise ValueError(f"runs_payload has too few columns: {runs_payload.shape[1]} < {header_cols_min}")

        eff_limit = int(fg_candidate_limit)
        if eff_limit <= 0:
            eff_limit = int(cfg_data.get("fg_candidate_limit", FG_CANDIDATE_LIMIT) or FG_CANDIDATE_LIMIT)
        eff_limit = max(LOADOUTS_PER_SONG_LIMIT, min(5000, int(eff_limit)))

        perf = _PERF_TIMING
        t_total = time.perf_counter() if perf else 0.0

        try:
            selected_n = int(runs_payload[0, 0])
        except Exception:
            selected_n = 0
        if selected_n < 0:
            selected_n = 0
        if selected_n > int(eff_limit):
            selected_n = int(eff_limit)
        max_rows = int(runs_payload.shape[0]) - 1
        if selected_n > max_rows:
            selected_n = max_rows

        best_global_score = int(runs_payload[0, 1])
        best_ids = np.asarray(runs_payload[0, 2 : 2 + n_slots], dtype=np.int32)
        best_global_res_arr = np.asarray(runs_payload[0, 2 + n_slots : 2 + n_slots + 7], dtype=np.int32).copy()
        best_global_genome = registry.decode_genome(best_ids)

        best_gear = best_global_genome[:6]
        best_minis = best_global_genome[6:9]

        # Reconstruct Stats exactly like the GPU kernels:
        # - Start from the "base_fixed" vector with user-fixed gems + static overflow removed
        #   (see solver/base_stats.py).
        # - Add item stats.
        # - Add gem allocation contributions (FT/FF/PP/CM/FM + overflow).
        base_fixed_arr, sel_color_built = build_base_fixed_stats_array(base_stats_fixed, cfg_data)
        best_stats = _add_genome_item_stats(build_stats_dict(base_fixed_arr), best_global_genome)

        g_ft = int(best_global_res_arr[1])
        g_ff = int(best_global_res_arr[2])
        g_pp = int(best_global_res_arr[3])
        g_cm = int(best_global_res_arr[4])
        g_fm = int(best_global_res_arr[5])
        g_ov = int(best_global_res_arr[6])

        selected_color = str(sel_color_built or cfg_data.get("selected_color", "") or "")
        best_stats = apply_gems_to_base_stats(
            best_stats,
            selected_color,
            g_ft,
            g_ff,
            g_pp,
            g_cm,
            g_fm,
            g_ov,
        )

        best_data = _build_best_result_payload(
            score=int(best_global_score),
            genome=best_global_genome,
            stats=best_stats,
            selected_color=selected_color,
            g_ft=g_ft,
            g_ff=g_ff,
            g_pp=g_pp,
            g_cm=g_cm,
            g_fm=g_fm,
            g_ov=g_ov,
        )

        if selected_n <= 0:
            return best_data, list(best_gear), list(best_minis), []

        cand_rows = runs_payload[1 : 1 + selected_n]
        packed_cols = 1 + n_slots + 7 + 7
        if int(cand_rows.shape[1]) < 2 + packed_cols:
            raise ValueError(
                f"runs_payload candidate rows have too few columns: {cand_rows.shape[1]} < {2 + packed_cols}"
            )

        sel_run_idx = np.asarray(cand_rows[:, 0], dtype=np.int32)
        sel_rows = np.asarray(cand_rows[:, 1], dtype=np.int32)
        packed = np.asarray(cand_rows[:, 2 : 2 + packed_cols], dtype=np.int32)

        scores_vec = np.asarray(packed[:, 0], dtype=np.int32)
        genome_ids_mat = np.asarray(packed[:, 1 : 1 + n_slots], dtype=np.int32)
        results_mat = np.asarray(packed[:, 1 + n_slots : 1 + n_slots + 7], dtype=np.int32)
        dedup_indices, dedup_stats = select_exact_unique_row_indices(
            genome_ids_mat=genome_ids_mat,
            scores=scores_vec,
            exact=True,
        )
        if int(dedup_indices.size) != int(genome_ids_mat.shape[0]):
            genome_ids_mat = genome_ids_mat[dedup_indices]
            results_mat = results_mat[dedup_indices]
            scores_vec = scores_vec[dedup_indices]
            sel_run_idx = sel_run_idx[dedup_indices]
            sel_rows = sel_rows[dedup_indices]

        # PERF/CPU NOTE:
        # - The GPU-selected payload already contains everything the in-flight pipeline needs
        #   (score + FT/FF + gem counts + selected element + (run,row) provenance).
        # - Reconstructing full per-candidate post-gem `Stats` is expensive.
        # - ForceGreatsFinder grouping only needs `BaseStats`, so keep full `Stats`
        #   reconstruction opt-in and carry only `BaseStats` on the hot path by default.
        include_full_stats = _decode_requires_full_stats(cfg_data)
        include_base_stats = bool(include_full_stats or cfg_data.get("fg_require_stats", False))
        fg_group_meta_enabled = bool(include_base_stats and isinstance(calc_song, dict) and calc_song)

        base_stats_arr = None
        sel_color_built = None
        if include_base_stats:
            base_stats_arr, sel_color_built = build_base_fixed_stats_array(base_stats_fixed, cfg_data)

        sel_color = str(cfg_data.get("selected_color", "") or "")
        if sel_color_built:
            sel_color = str(sel_color_built)

        sel_color_idx = _selected_color_stat_index(sel_color)

        t_stats = 0.0
        final_stats_mat = None
        item_stats_sum = None
        stat_names = None

        if include_base_stats:
            item_stats = registry.to_gpu_arrays()["item_stats"]  # (n_items, 10)
            t_stats = time.perf_counter() if perf else 0.0
            item_stats_sum = item_stats[genome_ids_mat].sum(axis=1)

            if include_full_stats:
                # Gem contributions: (n_cand, 10)
                n_cand = int(genome_ids_mat.shape[0])
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
                stat_names = STAT_NAMES

        unique_evaluated: list[dict] = []
        n_cand = int(genome_ids_mat.shape[0])
        g_ft = results_mat[:, 1]
        g_ff = results_mat[:, 2]
        g_pp = results_mat[:, 3]
        g_cm = results_mat[:, 4]
        g_fm = results_mat[:, 5]
        g_ov = results_mat[:, 6]
        for i in range(n_cand):
            score_val = int(scores_vec[i])
            ids_row = genome_ids_mat[i]
            genome_ids = [int(x) for x in np.asarray(ids_row, dtype=np.int32).tolist()]

            g_ft_i = int(g_ft[i])
            g_ff_i = int(g_ff[i])
            g_pp_i = int(g_pp[i])
            g_cm_i = int(g_cm[i])
            g_fm_i = int(g_fm[i])
            g_ov_i = int(g_ov[i])

            data_obj = _build_candidate_data_obj(
                score=score_val,
                selected_color=sel_color,
                g_ft=g_ft_i,
                g_ff=g_ff_i,
                g_pp=g_pp_i,
                g_cm=g_cm_i,
                g_fm=g_fm_i,
                g_ov=g_ov_i,
                run_idx=int(sel_run_idx[i]),
                row_idx=int(sel_rows[i]),
            )
            data_obj["GenomeIDs"] = list(genome_ids)

            if include_base_stats and base_stats_arr is not None and item_stats_sum is not None:
                # Always try to provide BaseStats when requested; ForceGreats batching can
                # operate on BaseStats even if full post-gem Stats reconstruction fails.
                try:
                    base_row_stats = base_stats_arr + item_stats_sum[i]
                    base_stats = build_stats_dict(base_row_stats)
                    data_obj["BaseStats"] = base_stats
                    if fg_group_meta_enabled:
                        fg_group_meta = build_fg_group_meta(
                            base_stats=base_stats,
                            calc_song=calc_song,
                            ref_arrays=ref_arrays,
                            selected_element=sel_color,
                            center_ft=g_ft_i,
                            center_ff=g_ff_i,
                            primary_color=str(cfg_data.get("primary_color", "") or ""),
                            secondary_color=str(cfg_data.get("secondary_color", "") or ""),
                            run_idx=int(sel_run_idx[i]),
                            row_idx=int(sel_rows[i]),
                        )
                        if isinstance(fg_group_meta, dict):
                            data_obj["_fg_group_meta"] = fg_group_meta
                except Exception:
                    pass
                if include_full_stats and stat_names is not None:
                    try:
                        if final_stats_mat is not None:
                            row_stats = final_stats_mat[i]
                            current_stats = build_stats_dict(row_stats)
                            data_obj["Stats"] = current_stats
                    except Exception:
                        pass

            cand_data = {
                "Score": score_val,
                "BaseScore": score_val,
                "GenomeIDs": list(genome_ids),
                "_ga_registry": registry,
                "Data": data_obj,
            }
            unique_evaluated.append(cand_data)

        best_data, best_gear, best_minis = _promote_best_candidate_over_header(
            best_data=best_data,
            registry=registry,
            best_gear=list(best_gear),
            best_minis=list(best_minis),
            candidates=unique_evaluated,
        )

        if perf:
            stats_ms = (time.perf_counter() - t_stats) * 1000.0 if (perf and include_base_stats) else 0.0
            total_ms = (time.perf_counter() - t_total) * 1000.0 if perf else 0.0
            logger.info(
                "[PERF][GADecode] "
                f"selected={int(selected_n)} unique_rows={int(dedup_stats.unique)} "
                f"duplicate_hits={int(dedup_stats.duplicate_hits)} replacements={int(dedup_stats.replacements)} "
                f"stats={stats_ms:.1f}ms total={total_ms:.1f}ms candidates={len(unique_evaluated)}"
            )

        return best_data, list(best_gear), list(best_minis), unique_evaluated
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

    perf = _PERF_TIMING
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
    except Exception:
        stub_scores = np.empty((0,), dtype=np.int32)
        stub_run_idx = np.empty((0,), dtype=np.int32)
        stub_pop_idx = np.empty((0,), dtype=np.int32)

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
    best_stats = _add_genome_item_stats(dict(base_stats_fixed or {}), best_global_genome)

    g_ft = int(best_global_res_arr[1])
    g_ff = int(best_global_res_arr[2])
    g_pp = int(best_global_res_arr[3])
    g_cm = int(best_global_res_arr[4])
    g_fm = int(best_global_res_arr[5])
    g_ov = int(best_global_res_arr[6])

    selected_color = str(cfg_data.get("selected_color", ""))
    best_stats = apply_gems_to_base_stats(
        best_stats,
        selected_color,
        g_ft,
        g_ff,
        g_pp,
        g_cm,
        g_fm,
        g_ov,
    )

    best_data = _build_best_result_payload(
        score=int(best_global_score),
        genome=best_global_genome,
        stats=best_stats,
        selected_color=selected_color,
        g_ft=g_ft,
        g_ff=g_ff,
        g_pp=g_pp,
        g_cm=g_cm,
        g_fm=g_fm,
        g_ov=g_ov,
    )

    if stub_scores.size == 0:
        return best_data, list(best_gear), list(best_minis), []

    # Fast path: select top base-score candidates in ID-space (no dict genome decode)
    # and only decode full genomes for the final bounded funnel.
    t_stub = time.perf_counter() if perf else 0.0
    t_stub_arrays = time.perf_counter() if perf else 0.0
    n_stub = int(stub_scores.shape[0])

    stub_rows = 1 + stub_pop_idx
    # Avoid multi-dim advanced indexing here: it can be surprisingly slow/alloc-heavy.
    # Flatten (run,row) to a single index, then slice columns.
    try:
        row_stride = int(runs_payload.shape[1])
        flat = runs_payload.reshape(-1, int(runs_payload.shape[2]))
        flat_idx = (stub_run_idx.astype(np.int64, copy=False) * row_stride) + stub_rows.astype(np.int64, copy=False)
        stub_genome_ids = flat[flat_idx, 1 : 1 + n_slots]
    except Exception:
        stub_genome_ids = runs_payload[stub_run_idx, stub_rows, 1 : 1 + n_slots]

    item_stats = registry.to_gpu_arrays()["item_stats"]  # (n_items, 10)
    arrays_ms = (time.perf_counter() - t_stub_arrays) * 1000.0 if perf else 0.0

    # Deterministic FG candidate funnel selection.
    #
    # Keep this GPU-free: we operate in ID-space and only decode full genomes for the
    # final bounded funnel. The selection logic mirrors `select_fg_candidates()`:
    # - hard-keep top-N by base score (DB/leaderboard stability)
    # - fill by base score (exploitation)
    # - then by an FG-proxy score with FT/FF center diversity
    # - then mini-team diversity
    t_stub = time.perf_counter() if perf else 0.0

    scores_i64 = stub_scores.astype(np.int64, copy=False)

    minis_sorted = np.sort(stub_genome_ids[:, 6:9], axis=1)
    canon_ids_mat = np.concatenate([stub_genome_ids[:, :6], minis_sorted], axis=1).astype(np.int32, copy=False)

    # Reuse the (score, ft, ff, pp, cm, fm, ov) result row for centers (FT/FF).
    try:
        row_stride = int(runs_payload.shape[1])
        flat = runs_payload.reshape(-1, int(runs_payload.shape[2]))
        flat_idx = (stub_run_idx.astype(np.int64, copy=False) * row_stride) + stub_rows.astype(np.int64, copy=False)
        stub_results = flat[flat_idx, 1 + n_slots : 1 + n_slots + 7]
    except Exception:
        stub_results = runs_payload[stub_run_idx, stub_rows, 1 + n_slots : 1 + n_slots + 7]

    centers_ft = stub_results[:, 1].astype(np.int32, copy=False)
    centers_ff = stub_results[:, 2].astype(np.int32, copy=False)

    # FG proxy matches `select_fg_candidates()` weights (on summed item stats).
    stats_sum = (
        item_stats[stub_genome_ids.astype(np.int32, copy=False)].sum(axis=1).astype(np.int64, copy=False)
    )  # (n,10)
    pp = stats_sum[:, 0]
    cm = stats_sum[:, 1]
    fm = stats_sum[:, 2]
    ft_stat = stats_sum[:, 3]
    ff_stat = stats_sum[:, 4]

    primary_color = str(cfg_data.get("primary_color", "") or "")
    secondary_color = str(cfg_data.get("secondary_color", "") or "")
    p_idx = _selected_color_stat_index(primary_color)
    s_idx = _selected_color_stat_index(secondary_color) if secondary_color and secondary_color != primary_color else -1
    p_val = stats_sum[:, p_idx] if p_idx >= 0 else 0
    s_val = stats_sum[:, s_idx] if s_idx >= 0 else 0

    fg_proxy_i64 = fm * 4 + ff_stat * 4 + ft_stat * 3 + cm * 2 + pp + p_val * 2 + s_val

    # Lexsort tie-breakers need the key in reverse order (element0 has highest priority).
    key_cols_desc = [-(canon_ids_mat[:, i].astype(np.int64, copy=False)) for i in range(8, -1, -1)]

    base_order = [int(i) for i in np.lexsort(tuple(key_cols_desc + [-fg_proxy_i64, -scores_i64])).tolist()]
    fg_order = [int(i) for i in np.lexsort(tuple(key_cols_desc + [-scores_i64, -fg_proxy_i64])).tolist()]

    limit = int(fg_candidate_limit)
    top_base_keep = min(limit, int(LOADOUTS_PER_SONG_LIMIT))
    base_budget = min(limit, max(top_base_keep, int(limit * 0.55)))
    fg_budget_end = min(limit, base_budget + int(limit * 0.30))

    selected_stub_indices: list[int] = []
    selected_mask = np.zeros((n_stub,), dtype=bool)
    seen_centers: set[tuple[int, int]] = set()
    seen_minis: set[tuple[int, int, int]] = set()
    centers_ft_list = centers_ft.tolist()
    centers_ff_list = centers_ff.tolist()
    mini_triplets = canon_ids_mat[:, 6:9].astype(np.int32, copy=False).tolist()

    def _add(i: int) -> bool:
        if selected_mask[i]:
            return False
        selected_mask[i] = True
        selected_stub_indices.append(i)
        seen_centers.add((int(centers_ft_list[i]), int(centers_ff_list[i])))
        mi = mini_triplets[i]
        seen_minis.add((int(mi[0]), int(mi[1]), int(mi[2])))
        return True

    # 1) Hard keep top-N by base score.
    for i in base_order:
        if len(selected_stub_indices) >= top_base_keep:
            break
        _add(i)

    # 2) Base-score fill (exploitation).
    for i in base_order:
        if len(selected_stub_indices) >= base_budget:
            break
        _add(i)

    # 3) FG-proxy fill; prefer new FT/FF centers first.
    for i in fg_order:
        if len(selected_stub_indices) >= fg_budget_end:
            break
        c = (int(centers_ft_list[i]), int(centers_ff_list[i]))
        if c in seen_centers:
            continue
        _add(i)
    for i in fg_order:
        if len(selected_stub_indices) >= fg_budget_end:
            break
        _add(i)

    # 4) Mini-team diversity fill.
    for i in base_order:
        if len(selected_stub_indices) >= limit:
            break
        mi = mini_triplets[i]
        mk = (int(mi[0]), int(mi[1]), int(mi[2]))
        if mk in seen_minis:
            continue
        _add(i)

    # 5) Final fill by base score.
    for i in base_order:
        if len(selected_stub_indices) >= limit:
            break
        _add(i)

    select_ms = (time.perf_counter() - t_stub) * 1000.0 if perf else 0.0
    proxy_ms = 0.0

    include_full_stats = _decode_requires_full_stats(cfg_data)
    include_base_stats = bool(include_full_stats or cfg_data.get("fg_require_stats", False))
    fg_group_meta_enabled = bool(include_base_stats and isinstance(calc_song, dict) and calc_song)

    # Vectorized stat reconstruction for selected candidates only.
    t_stats = time.perf_counter() if perf else 0.0
    sel_color = str(cfg_data.get("selected_color", ""))
    sel_color_idx = _selected_color_stat_index(sel_color)
    base_stats_arr = build_stats_array(base_stats_fixed) if include_base_stats else None

    n_cand = len(selected_stub_indices)
    genome_ids_mat = stub_genome_ids[selected_stub_indices]
    item_stats_sum = item_stats[genome_ids_mat].sum(axis=1) if include_base_stats else None
    scores_vec = stub_scores[selected_stub_indices].astype(np.int32, copy=False)
    sel_run_idx = stub_run_idx[selected_stub_indices]
    sel_rows = 1 + stub_pop_idx[selected_stub_indices]
    # Avoid advanced indexing across multiple dimensions (can be surprisingly slow/alloc-heavy).
    # Flatten (run,row) to a single index, then slice columns.
    try:
        row_stride = int(runs_payload.shape[1])
        flat = runs_payload.reshape(-1, int(runs_payload.shape[2]))
        flat_idx = (sel_run_idx.astype(np.int64, copy=False) * row_stride) + sel_rows.astype(np.int64, copy=False)
        results_mat = flat[flat_idx, 1 + n_slots : 1 + n_slots + 7]
    except Exception:
        results_mat = runs_payload[sel_run_idx, sel_rows, 1 + n_slots : 1 + n_slots + 7]

    g_ft = results_mat[:, 1]
    g_ff = results_mat[:, 2]
    g_pp = results_mat[:, 3]
    g_cm = results_mat[:, 4]
    g_fm = results_mat[:, 5]
    g_ov = results_mat[:, 6]

    final_stats_mat = None
    if include_full_stats and base_stats_arr is not None and item_stats_sum is not None:
        gem_contributions = np.zeros((n_cand, 10), dtype=np.int32)
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
        ids_row = genome_ids_mat[i]
        genome_ids = [int(x) for x in np.asarray(ids_row, dtype=np.int32).tolist()]

        current_stats = None
        if include_full_stats and final_stats_mat is not None:
            # Build stats dict from numpy array (fast).
            row_stats = final_stats_mat[i]
            current_stats = build_stats_dict(row_stats)
        # Pre-gem base stats (before FT/FF/PP/CM/FM/OV allocation). This is useful for downstream
        # ForceGreatsFinder batching to avoid re-deriving base stats from post-gem Stats + GemCounts.
        base_stats = None
        if include_base_stats and base_stats_arr is not None and item_stats_sum is not None:
            base_row_stats = base_stats_arr + item_stats_sum[i]
            base_stats = build_stats_dict(base_row_stats)

        g_ft_i = int(g_ft[i])
        g_ff_i = int(g_ff[i])
        g_pp_i = int(g_pp[i])
        g_cm_i = int(g_cm[i])
        g_fm_i = int(g_fm[i])
        g_ov_i = int(g_ov[i])

        data_obj = _build_candidate_data_obj(
            score=score_val,
            selected_color=sel_color,
            g_ft=g_ft_i,
            g_ff=g_ff_i,
            g_pp=g_pp_i,
            g_cm=g_cm_i,
            g_fm=g_fm_i,
            g_ov=g_ov_i,
            stats=current_stats,
            base_stats=base_stats,
            run_idx=int(sel_run_idx[i]),
            row_idx=int(sel_rows[i]),
        )
        data_obj["GenomeIDs"] = list(genome_ids)
        if base_stats is not None and fg_group_meta_enabled:
            fg_group_meta = build_fg_group_meta(
                base_stats=base_stats,
                calc_song=calc_song,
                ref_arrays=ref_arrays,
                selected_element=sel_color,
                center_ft=g_ft_i,
                center_ff=g_ff_i,
                primary_color=str(cfg_data.get("primary_color", "") or ""),
                secondary_color=str(cfg_data.get("secondary_color", "") or ""),
                run_idx=int(sel_run_idx[i]),
                row_idx=int(sel_rows[i]),
            )
            if isinstance(fg_group_meta, dict):
                data_obj["_fg_group_meta"] = fg_group_meta

        cand_data = {
            "Score": score_val,
            "BaseScore": score_val,
            "GenomeIDs": list(genome_ids),
            "_ga_registry": registry,
            "Data": data_obj,
        }
        unique_evaluated.append(cand_data)

    stats_ms = (time.perf_counter() - t_stats) * 1000.0 if perf else 0.0
    total_ms = (time.perf_counter() - t_total) * 1000.0 if perf else 0.0
    if perf:
        logger.info(
            "[PERF][GADecode] "
            f"runs={n_runs} pop={n_genomes} uniq={n_stub} "
            f"scan={scan_ms:.1f}ms select={select_ms:.1f}ms stats={stats_ms:.1f}ms total={total_ms:.1f}ms "
            f"selected={len(unique_evaluated)}"
        )
        logger.info(
            "[PERF][GADecodeDetails] "
            f"runs={n_runs} pop={n_genomes} uniq={n_stub} arrays={arrays_ms:.1f}ms proxy={proxy_ms:.1f}ms"
        )

    best_data, best_gear, best_minis = _promote_best_candidate_over_header(
        best_data=best_data,
        registry=registry,
        best_gear=list(best_gear),
        best_minis=list(best_minis),
        candidates=unique_evaluated,
    )

    return best_data, list(best_gear), list(best_minis), unique_evaluated


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
    ga_seed: int | None = None,
    ga_seed_offset: int = 0,
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

    gpu_api = _require_gpu_api()

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
        # Fallback path (slower): upload per run.
        gpu_data = registry.to_gpu_arrays()
        gpu_api.ga_upload_item_stats(
            gpu_data["item_stats"],
            gpu_data["slot_start"],
            gpu_data["slot_count"],
        )

        base_stats_arr, _ = build_base_fixed_stats_array(base_stats_fixed, cfg_data)
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
    seed = 42
    if ga_seed is not None:
        try:
            seed = (int(ga_seed) + int(ga_seed_offset)) & 0xFFFFFFFF
        except Exception:
            seed = 42
    gpu_api.ga_seed_rng(n_genomes, seed=int(seed))

    trace_writer, trace_every = build_convergence_trace_writer(
        calc_song=calc_song,
        cfg_data=cfg_data,
        ga_seed=ga_seed if ga_seed is not None else seed,
    )
    trace_t0 = time.perf_counter() if trace_writer is not None else 0.0

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

    if _GPU_NATIVE_GA_LOG_ISLAND_MODEL:
        logger.info(f"  >> Island Model: {num_islands} islands, ~{island_size} genomes each")

    # Track population snapshot - only downloaded when best improves or during migrations
    pop_snapshot = None

    # Warm-start control: force cold start on Gen 0
    gen_use_hints = 0
    cold_tail_gens = max(0, int(_GPU_NATIVE_GA_COLD_TAIL_GENS))

    # Upload island boundaries to GPU (once per run)
    island_boundaries_np = np.array(island_starts, dtype=np.int32)
    gpu_api.ga_upload_island_boundaries(island_boundaries_np)

    # Initialize GPU-side global best tracking
    gpu_api.ga_init_global_best()

    # Main GPU-native GA loop with island migration (GPU-resident elitism)
    for gen in range(n_generations):
        eval_use_hints = int(gen_use_hints)
        if cold_tail_gens > 0 and int(gen) >= (int(n_generations) - int(cold_tail_gens)):
            eval_use_hints = 0
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
            use_hints=int(eval_use_hints),  # 0=cold, 1=warm
            materialize_mode="update_global",
        )

        if trace_writer is not None and (int(gen) % int(trace_every) == 0):
            try:
                trace_best_score, _trace_best_genome, trace_best_results = gpu_api.ga_download_global_best()
                trace_writer.append(
                    generation_idx=int(gen),
                    elapsed_s=float(time.perf_counter() - trace_t0),
                    best_score=int(trace_best_score),
                    best_results=trace_best_results,
                    extra={"path": "single_run"},
                )
            except Exception:
                pass

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
        # Also pack the compact GA->FG candidate table for this run (stored in the per-song slot).
        # This enables callers to download only a small candidate buffer instead of the full run payload.
        gpu_api.ga_pack_fg_candidates_table_segmented(
            table_slot=int(song_slot),
            run_idx_start=int(store_payload_idx),
            n_runs=1,
            n_genomes_per_run=int(n_genomes),
            n_slots=int(n_slots),
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
        )
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


def _run_gpu_native_ga_runs_payload_steady_state(
    *,
    calc_song: dict,
    ref_arrays: dict,
    song_slot: int,
    item_stats: "np.ndarray",
    slot_start: "np.ndarray",
    slot_count: "np.ndarray",
    base_fixed_stats_arr: "np.ndarray",
    n_generations: int,
    initial_populations: "np.ndarray | None",
    num_runs: int,
    n_genomes: int,
    init_heuristic_topk: "np.ndarray | None",
    init_heuristic_k: int,
    init_heuristic_copies: int,
    db_seed_ids: "np.ndarray | None",
    db_seed_prob: float,
    db_seed_copies: int,
    db_seed_mutations: int,
    elite_count: int,
    mutation_rate: float,
    immigrant_rate: float,
    tournament_k: int,
    color_flags: dict | None,
    cfg_data: dict | None,
    ga_seed: int | None,
) -> "np.ndarray":
    if not _GPU_NATIVE_AVAILABLE:
        raise RuntimeError("GPU-native GA not available (missing dependencies)")

    gpu_api = _require_gpu_api()
    cfg_data = dict(cfg_data or {})
    color_flags = dict(color_flags or {})

    try:
        from .taichi_gem.api import load_ref_arrays, precompute_timeline_gpu
        from .taichi_gem import fields as gpu_fields
    except Exception as exc:
        raise RuntimeError(f"GPU-native GA requires taichi_gem api/fields: {exc}") from exc

    n_generations = max(1, int(n_generations))
    num_runs = max(1, int(num_runs))
    n_genomes = max(1, int(n_genomes))
    n_slots = 9

    steady_state = resolve_steady_state_settings(cfg_data=cfg_data, epoch_count=num_runs, n_genomes=n_genomes)
    if not steady_state.enabled:
        raise RuntimeError("steady-state helper called while steady-state is disabled")

    gpu_fields.configure_ga_run_buffers(max_runs=int(num_runs), max_genomes=int(n_genomes))

    reset_every_runs_env = str(_GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS)
    try:
        reset_every_runs = int(reset_every_runs_env)
    except Exception:
        reset_every_runs = 0

    max_retries_env = str(_GPU_NATIVE_GA_VULKAN_RETRIES)
    try:
        max_retries = int(max_retries_env)
    except Exception:
        max_retries = 1

    def _is_vulkan_semaphore_failure(exc: BaseException) -> bool:
        msg = str(exc)
        return ("failed to create semaphore" in msg) or ("RHI Error" in msg and "semaphore" in msg)

    def _restore_song_gpu_state() -> None:
        load_ref_arrays(ref_arrays)
        precompute_timeline_gpu(calc_song, ref_arrays, song_slot=int(song_slot))
        gpu_api.ga_upload_item_stats(item_stats, slot_start, slot_count)
        gpu_api.ga_upload_base_fixed_stats(base_fixed_stats_arr)
        if init_heuristic_topk is not None and int(init_heuristic_k) > 0:
            gpu_api.ga_upload_init_heuristic_topk(
                topk_ids=np.asarray(init_heuristic_topk, dtype=np.int32),
                heuristic_k=int(init_heuristic_k),
                n_slots=int(n_slots),
            )

    _restore_song_gpu_state()

    if initial_populations is not None:
        current_population_ids = build_steady_state_initial_population_ids(
            initial_populations,
            n_genomes=int(n_genomes),
            n_slots=int(n_slots),
        )
        gpu_api.ga_upload_population_indices(current_population_ids, n_slots=int(n_slots))
    else:
        seed_base = 42 if ga_seed is None else int(ga_seed)
        gpu_api.ga_generate_initial_populations(
            run_idx_start=0,
            n_runs=1,
            n_genomes=int(n_genomes),
            n_slots=int(n_slots),
            seed=int(seed_base),
            heuristic_prob=0.0,
            heuristic_k=int(init_heuristic_k),
            seed_prob=float(db_seed_prob or 0.0),
            seed_copies=int(db_seed_copies if db_seed_ids is not None else 0),
            seed_mutations=int(db_seed_mutations if db_seed_ids is not None else 0),
            heuristic_copies=int(init_heuristic_copies),
            seed_ids=db_seed_ids,
        )
        gpu_api.ga_load_initial_population(run_idx=0, n_genomes=int(n_genomes), n_slots=int(n_slots))
        current_population_ids = np.asarray(
            gpu_api.ga_download_population_indices(n_genomes=int(n_genomes), n_slots=int(n_slots)),
            dtype=np.int32,
        )

    fg_candidate_limit = int(cfg_data.get("fg_candidate_limit", FG_CANDIDATE_LIMIT) or FG_CANDIDATE_LIMIT)
    if fg_candidate_limit <= 0:
        fg_candidate_limit = FG_CANDIDATE_LIMIT
    fg_candidate_limit = max(LOADOUTS_PER_SONG_LIMIT, min(5000, int(fg_candidate_limit)))
    top_base_keep = min(int(fg_candidate_limit), int(LOADOUTS_PER_SONG_LIMIT))
    base_budget = min(int(fg_candidate_limit), max(int(top_base_keep), int(int(fg_candidate_limit) * 0.55)))
    fg_budget_end = min(int(fg_candidate_limit), int(base_budget) + int(int(fg_candidate_limit) * 0.30))

    logger.info(
        "  Steady-state epochs: %d (generations per epoch: %d, refresh_count: %d, refresh_pct: %.0f%%)",
        int(num_runs),
        int(n_generations),
        int(steady_state.refresh_count),
        float(steady_state.refresh_pct) * 100.0,
    )

    seen_archive_keys: set[tuple[int, ...]] = set()
    for epoch_idx in range(int(num_runs)):
        if reset_every_runs > 0 and epoch_idx > 0 and (epoch_idx % reset_every_runs) == 0:
            gpu_api.hard_reset_taichi(reason=f"periodic Vulkan reset at steady-state epoch {epoch_idx + 1}/{num_runs}")
            _restore_song_gpu_state()
            gpu_api.ga_upload_population_indices(current_population_ids, n_slots=int(n_slots))

        last_exc = None
        for attempt in range(max_retries + 1):
            try:
                gpu_api.ga_upload_population_indices(current_population_ids, n_slots=int(n_slots))
                _run_gpu_native_ga(
                    population=None,
                    n_generations=int(n_generations),
                    registry=None,
                    cfg_data=cfg_data,
                    calc_song=calc_song,
                    ref_arrays=ref_arrays,
                    base_stats_fixed={},
                    gpu_static={
                        "need_upload_item_stats": False,
                        "need_upload_base_fixed": False,
                        "item_stats": item_stats,
                        "slot_start": slot_start,
                        "slot_count": slot_count,
                        "base_fixed_stats": base_fixed_stats_arr,
                    },
                    elite_count=int(elite_count),
                    mutation_rate=float(mutation_rate),
                    immigrant_rate=float(immigrant_rate),
                    tournament_k=int(tournament_k),
                    color_flags=color_flags,
                    status_cb=None,
                    song_slot=int(song_slot),
                    store_payload_idx=int(epoch_idx),
                    store_payload_only=True,
                    n_genomes_override=int(n_genomes),
                    population_preloaded=True,
                    ga_seed=ga_seed,
                    ga_seed_offset=int(epoch_idx),
                )
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                if attempt >= max_retries or not _is_vulkan_semaphore_failure(exc):
                    break
                logger.warning(
                    "[GPU GA] Vulkan backend error; retrying steady-state epoch after reset (attempt %d/%d)",
                    int(attempt + 1),
                    int(max_retries),
                )
                try:
                    gpu_api.hard_reset_taichi(reason=str(exc).splitlines()[0][:200])
                    _restore_song_gpu_state()
                    gpu_api.ga_upload_population_indices(current_population_ids, n_slots=int(n_slots))
                except Exception:
                    break

        if last_exc is not None:
            raise last_exc

        if epoch_idx >= int(num_runs) - 1:
            continue

        _best_score, _best_ids, _best_result_row, pop_snapshot, _results, scores = gpu_api.ga_download_run_payload(
            n_genomes=int(n_genomes),
            n_slots=int(n_slots),
        )
        current_population_ids, refresh_stats = build_steady_state_next_population_ids(
            current_population_ids=np.asarray(pop_snapshot, dtype=np.int32),
            scores=np.asarray(scores, dtype=np.int32),
            slot_start=np.asarray(slot_start, dtype=np.int32),
            slot_count=np.asarray(slot_count, dtype=np.int32),
            refresh_count=int(steady_state.refresh_count),
            seed=((42 if ga_seed is None else int(ga_seed)) ^ ((int(epoch_idx) + 1) * 747796405)),
            seen_archive_keys=seen_archive_keys,
            elite_keep_count=int(elite_count),
        )
        extend_seen_archive_keys(
            seen_archive_keys=seen_archive_keys,
            population_ids=np.asarray(pop_snapshot, dtype=np.int32),
        )
        logger.info(
            "  Steady-state refresh %d/%d: survivors=%d dropped_dupes=%d archive_rejected=%d fresh=%d fresh_collisions=%d fallback_archive=%d fallback_dupes=%d",
            int(epoch_idx + 1),
            int(num_runs - 1),
            int(refresh_stats.survivors_kept),
            int(refresh_stats.survivor_duplicates_dropped),
            int(refresh_stats.survivor_archive_rejected),
            int(refresh_stats.fresh_added),
            int(refresh_stats.fresh_archive_collisions),
            int(refresh_stats.fallback_archive_reused),
            int(refresh_stats.fallback_duplicates_added),
        )

    audit_redundancy = _ga_redundancy_audit_enabled()
    if audit_redundancy:
        try:
            audit_payload = gpu_api.ga_download_runs_payload(
                n_runs=int(num_runs),
                n_genomes=int(n_genomes),
                n_slots=int(n_slots),
            )
            audit_record = analyze_ga_redundancy_from_runs_payload(
                runs_payload=audit_payload,
                item_stats=item_stats,
                base_fixed_stats_arr=base_fixed_stats_arr,
                calc_song=calc_song,
                cfg_data=cfg_data,
                ga_seed=ga_seed,
            )
            logger.info(summarize_ga_redundancy_record(audit_record))
            audit_path = write_ga_redundancy_audit_record(audit_record)
            logger.info(f"[GA Redundancy Audit] wrote {audit_path}")
        except Exception as exc:
            logger.warning(f"[GA Redundancy Audit] Warning: failed to capture audit: {exc}")

    return gpu_api.ga_download_fg_selected_payload(
        table_slot=int(song_slot),
        n_runs=int(num_runs),
        limit=int(fg_candidate_limit),
        top_base_keep=int(top_base_keep),
        base_budget=int(base_budget),
        fg_budget_end=int(fg_budget_end),
    )


def run_gpu_native_ga_runs_payload_prebuilt(
    *,
    calc_song: dict,
    ref_arrays: dict,
    song_slot: int,
    item_stats: "np.ndarray",
    slot_start: "np.ndarray",
    slot_count: "np.ndarray",
    base_fixed_stats_arr: "np.ndarray",
    n_generations: int,
    initial_populations: "np.ndarray | None" = None,
    num_runs: int | None = None,
    n_genomes: int = GA_POPULATION_SIZE,
    init_heuristic_topk: "np.ndarray | None" = None,
    init_heuristic_k: int = 0,
    init_heuristic_copies: int = 25,
    db_seed_ids: "np.ndarray | None" = None,
    db_seed_prob: float = 0.0,
    db_seed_copies: int = 1,
    db_seed_mutations: int = 1,
    elite_count: int = GA_ELITISM,
    mutation_rate: float = GA_MUTATION_RATE,
    immigrant_rate: float = 0.0,
    tournament_k: int = 3,
    color_flags: dict | None = None,
    cfg_data: dict | None = None,
    ga_seed: int | None = None,
) -> "np.ndarray":
    """
    Run the GPU-native GA for multiple runs using either:
    - prebuilt CPU populations, or
    - GPU-generated initial populations (preferred).

    This entrypoint is designed for the GPU-native in-flight pipeline:
    - CPU prepares/encodes initial populations and item registry arrays
    - GPU-owner thread executes kernels back-to-back and returns a compact runs payload

    Important: This must be called from the Taichi/Vulkan owner thread (GpuExecutor).
    """
    if not _GPU_NATIVE_AVAILABLE:
        raise RuntimeError("GPU-native GA not available (missing dependencies)")

    gpu_api = _require_gpu_api()

    cfg_data = dict(cfg_data or {})
    color_flags = dict(color_flags or {})
    trace_writer, trace_every = build_convergence_trace_writer(
        calc_song=calc_song,
        cfg_data=cfg_data,
        ga_seed=ga_seed,
    )
    trace_t0 = time.perf_counter() if trace_writer is not None else 0.0

    seed_base = 42
    if ga_seed is not None:
        try:
            seed_base = int(ga_seed) & 0xFFFFFFFF
        except Exception:
            seed_base = 42

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

    if initial_populations is not None:
        if not isinstance(initial_populations, np.ndarray):
            initial_populations = np.asarray(initial_populations, dtype=np.int32)
        if initial_populations.ndim != 3:
            raise ValueError(
                f"initial_populations must have shape (n_runs, n_genomes, n_slots); got ndim={initial_populations.ndim}"
            )
        num_runs = int(initial_populations.shape[0])
        n_genomes = int(initial_populations.shape[1])
        n_slots = int(initial_populations.shape[2])
    else:
        if num_runs is None:
            raise ValueError("num_runs is required when initial_populations is None")
        num_runs = int(num_runs)
        n_genomes = int(n_genomes)
        n_slots = 9

    if num_runs <= 0 or n_genomes <= 0 or n_slots <= 0:
        raise ValueError(
            f"initial_populations has invalid shape: (n_runs={num_runs}, n_genomes={n_genomes}, n_slots={n_slots})"
        )

    if n_slots != 9:
        raise ValueError(f"GPU-native GA expects n_slots=9, got {n_slots}")

    steady_state = resolve_steady_state_settings(cfg_data=cfg_data, epoch_count=num_runs, n_genomes=n_genomes)
    if steady_state.enabled:
        return _run_gpu_native_ga_runs_payload_steady_state(
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            song_slot=int(song_slot),
            item_stats=np.asarray(item_stats, dtype=np.int32),
            slot_start=np.asarray(slot_start, dtype=np.int32),
            slot_count=np.asarray(slot_count, dtype=np.int32),
            base_fixed_stats_arr=np.asarray(base_fixed_stats_arr, dtype=np.int32),
            n_generations=int(n_generations),
            initial_populations=initial_populations,
            num_runs=int(num_runs),
            n_genomes=int(n_genomes),
            init_heuristic_topk=init_heuristic_topk,
            init_heuristic_k=int(init_heuristic_k),
            init_heuristic_copies=int(init_heuristic_copies),
            db_seed_ids=db_seed_ids,
            db_seed_prob=float(db_seed_prob or 0.0),
            db_seed_copies=int(db_seed_copies),
            db_seed_mutations=int(db_seed_mutations),
            elite_count=int(elite_count),
            mutation_rate=float(mutation_rate),
            immigrant_rate=float(immigrant_rate),
            tournament_k=int(tournament_k),
            color_flags=color_flags,
            cfg_data=cfg_data,
            ga_seed=ga_seed,
        )

    # Reduce padded CPU↔GPU transfers by sizing multi-run GA buffers to the
    # current session's needs. This MUST happen before the first Taichi field
    # allocation (i.e., before load_ref_arrays/precompute_timeline triggers ensure_ready()).
    gpu_fields.configure_ga_run_buffers(max_runs=num_runs, max_genomes=n_genomes)

    # Optional stability toggles (mirrors solve_coevolution_genetic GPU-native path)
    reset_every_runs_env = str(_GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS)
    try:
        reset_every_runs = int(reset_every_runs_env)
    except Exception:
        reset_every_runs = 0

    max_retries_env = str(_GPU_NATIVE_GA_VULKAN_RETRIES)
    try:
        max_retries = int(max_retries_env)
    except Exception:
        max_retries = 1

    def _is_vulkan_semaphore_failure(exc: BaseException) -> bool:
        msg = str(exc)
        return ("failed to create semaphore" in msg) or ("RHI Error" in msg and "semaphore" in msg)

    def _restore_song_gpu_state() -> None:
        # Rebuild Taichi/GA static state for this song slot after hard resets.
        load_ref_arrays(ref_arrays)
        precompute_timeline_gpu(calc_song, ref_arrays, song_slot=song_slot)
        gpu_api.ga_upload_item_stats(item_stats, slot_start, slot_count)
        gpu_api.ga_upload_base_fixed_stats(base_fixed_stats_arr)

    # Load refs/timeline + upload static per-song GA data once.
    _restore_song_gpu_state()

    # Optional heuristic top-K table for GPU initial population generation.
    init_heuristic_k = int(init_heuristic_k)
    if init_heuristic_topk is not None and init_heuristic_k > 0:
        gpu_api.ga_upload_init_heuristic_topk(
            topk_ids=np.asarray(init_heuristic_topk, dtype=np.int32),
            heuristic_k=int(init_heuristic_k),
            n_slots=int(n_slots),
        )

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

    fg_candidate_limit = int(cfg_data.get("fg_candidate_limit", FG_CANDIDATE_LIMIT) or FG_CANDIDATE_LIMIT)
    if fg_candidate_limit <= 0:
        fg_candidate_limit = FG_CANDIDATE_LIMIT
    fg_candidate_limit = max(LOADOUTS_PER_SONG_LIMIT, min(5000, int(fg_candidate_limit)))
    top_base_keep = min(int(fg_candidate_limit), int(LOADOUTS_PER_SONG_LIMIT))
    base_budget = min(int(fg_candidate_limit), max(int(top_base_keep), int(int(fg_candidate_limit) * 0.55)))
    fg_budget_end = min(int(fg_candidate_limit), int(base_budget) + int(int(fg_candidate_limit) * 0.30))

    # Island model (mirrors _run_gpu_native_ga)
    num_islands = min(GPU_GA_NUM_ISLANDS, n_genomes // 10)  # At least 10 per island
    if num_islands < 1:
        num_islands = 1

    # Determine an auto batch size that avoids combo-chunking in ga_evaluate_population.
    # Chunking increases kernel launch count, so we prefer keeping n_total*n_combos <= MAX_EVALS_PER_DISPATCH.
    try:
        n_combos = int(gpu_api._ensure_ftff_combo_tables(total_budget))
    except Exception:
        n_combos = 0
    denom = int(n_genomes) * max(1, n_combos)
    # Keep a small safety margin below MAX_EVALS_PER_DISPATCH to avoid accidental oversubscription.
    soft_evals = int(gpu_fields.MAX_EVALS_PER_DISPATCH) - 8192  # 8k headroom
    if soft_evals < 1:
        soft_evals = int(gpu_fields.MAX_EVALS_PER_DISPATCH)
    max_runs_by_work = int(soft_evals // denom) if denom > 0 else 1
    if max_runs_by_work < 1:
        max_runs_by_work = 1
    max_runs_by_genomes = int(gpu_fields.MAX_GENOMES // int(n_genomes)) if int(n_genomes) > 0 else 1
    if max_runs_by_genomes < 1:
        max_runs_by_genomes = 1

    batch_runs_env = str(_GPU_NATIVE_GA_BATCH_RUNS).strip()
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
    audit_payload_segments: list[np.ndarray] = []
    audit_redundancy = _ga_redundancy_audit_enabled()

    perf = _PERF_TIMING
    # DEV / DEBUG: phase timing flag (GPU_NATIVE_GA_PHASE_TIMING).
    phase_timing = perf and env_flag("GPU_NATIVE_GA_PHASE_TIMING", "0")
    if phase_timing:
        import taichi as ti

        def _sync() -> None:
            ti.sync()

    else:

        def _sync() -> None:
            return

    def _log_phase(*, phase: str, ms: float, runs: int, pop: int, gen: int, use_hints: int, combos: int) -> None:
        if not phase_timing:
            return
        try:
            logger.info(
                "[PERF][GAGPUPhase] "
                f"phase={phase} runs={int(runs)} pop={int(pop)} gen={int(gen)} "
                f"use_hints={int(use_hints)} combos={int(combos)} ms={float(ms):.3f}"
            )
        except Exception:
            return

    def _stage_segment_initial_populations(*, run_start: int, seg_runs: int, segment_pop_arr) -> None:
        if segment_pop_arr is not None:
            gpu_api.ga_upload_initial_populations(
                segment_pop_arr,
                n_runs=int(seg_runs),
                n_genomes=int(n_genomes),
                n_slots=int(n_slots),
            )
            return

        # Generate initial populations on GPU for this segment (seeded per segment to avoid repeats).
        seg_seed = int(seed_base) ^ (int(run_start) * 747796405)
        gpu_api.ga_generate_initial_populations(
            run_idx_start=0,
            n_runs=int(seg_runs),
            n_genomes=int(n_genomes),
            n_slots=int(n_slots),
            seed=int(seg_seed),
            heuristic_prob=0.0,
            heuristic_k=int(init_heuristic_k),
            seed_prob=float(db_seed_prob or 0.0),
            seed_copies=int(db_seed_copies if db_seed_ids is not None else 0),
            seed_mutations=int(db_seed_mutations if db_seed_ids is not None else 0),
            heuristic_copies=int(init_heuristic_copies),
            seed_ids=db_seed_ids,
        )

    run_start_global = 0
    while run_start_global < num_runs:
        seg_len = min(int(gpu_fields.MAX_GA_RUNS), num_runs - run_start_global)
        segment_pop = None
        if initial_populations is not None:
            segment_pop = np.asarray(initial_populations[run_start_global : run_start_global + seg_len], dtype=np.int32)
        _stage_segment_initial_populations(
            run_start=int(run_start_global),
            seg_runs=int(seg_len),
            segment_pop_arr=segment_pop,
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
                _restore_song_gpu_state()
                _stage_segment_initial_populations(
                    run_start=int(run_start_global),
                    seg_runs=int(seg_len),
                    segment_pop_arr=segment_pop,
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
                    gpu_api.ga_seed_rng_runs(
                        n_runs=int(batch_len),
                        n_genomes_per_run=int(n_genomes),
                        seed=int((int(seed_base) + int(global_run_idx)) & 0xFFFFFFFF),
                    )

                    if trace_writer is not None:
                        gpu_api.ga_init_global_best()

                    gen_use_hints = 0  # Force cold start on Gen 0
                    cold_tail_gens = max(0, int(_GPU_NATIVE_GA_COLD_TAIL_GENS))
                    n_total = int(batch_len) * int(n_genomes)

                    for gen in range(int(n_generations)):
                        eval_use_hints = int(gen_use_hints)
                        if cold_tail_gens > 0 and int(gen) >= (int(n_generations) - int(cold_tail_gens)):
                            eval_use_hints = 0
                        t0 = time.perf_counter() if phase_timing else 0.0
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
                            use_hints=int(eval_use_hints),
                            materialize_mode="store_hints",
                        )
                        _sync()
                        if t0:
                            _log_phase(
                                phase="evaluate",
                                ms=(time.perf_counter() - t0) * 1000.0,
                                runs=int(batch_len),
                                pop=int(n_genomes),
                                gen=int(gen),
                                use_hints=int(eval_use_hints),
                                combos=int(n_combos),
                            )

                        t0 = time.perf_counter() if phase_timing else 0.0
                        if trace_writer is not None:
                            gpu_api.ga_update_global_best(int(n_total), n_slots=int(n_slots))
                        _sync()
                        if t0:
                            _log_phase(
                                phase="write_best_hints",
                                ms=(time.perf_counter() - t0) * 1000.0,
                                runs=int(batch_len),
                                pop=int(n_genomes),
                                gen=int(gen),
                                use_hints=int(eval_use_hints),
                                combos=int(n_combos),
                            )

                        if trace_writer is not None and (int(gen) % int(trace_every) == 0):
                            try:
                                trace_best_score, _trace_best_genome, trace_best_results = (
                                    gpu_api.ga_download_global_best()
                                )
                                trace_writer.append(
                                    generation_idx=int(gen),
                                    elapsed_s=float(time.perf_counter() - trace_t0),
                                    best_score=int(trace_best_score),
                                    best_results=trace_best_results,
                                    extra={
                                        "path": "batch_runs",
                                        "batch_run_start": int(global_run_idx),
                                        "batch_runs": int(batch_len),
                                    },
                                )
                            except Exception:
                                pass

                        # Track best per run across generations.
                        t0 = time.perf_counter() if phase_timing else 0.0
                        gpu_api.ga_update_runs_best(
                            run_idx_start=int(local_run_idx),
                            n_runs=int(batch_len),
                            n_genomes_per_run=int(n_genomes),
                            n_slots=int(n_slots),
                        )
                        _sync()
                        if t0:
                            _log_phase(
                                phase="update_runs_best",
                                ms=(time.perf_counter() - t0) * 1000.0,
                                runs=int(batch_len),
                                pop=int(n_genomes),
                                gen=int(gen),
                                use_hints=int(eval_use_hints),
                                combos=int(n_combos),
                            )

                        # Migration only if another generation will be evaluated (avoid corrupting final snapshots).
                        is_migration_gen = (
                            num_islands > 1
                            and (gen + 1) % GPU_GA_GENS_PER_MIGRATION == 0
                            and gen < (int(n_generations) - 1)
                        )
                        if is_migration_gen:
                            t0 = time.perf_counter() if phase_timing else 0.0
                            gpu_api.ga_island_migration_runs(
                                n_runs=int(batch_len),
                                n_genomes_per_run=int(n_genomes),
                                n_islands=int(num_islands),
                                migrate_count=int(GPU_GA_MIGRATE_COUNT),
                                n_slots=int(n_slots),
                            )
                            _sync()
                            if t0:
                                _log_phase(
                                    phase="migration",
                                    ms=(time.perf_counter() - t0) * 1000.0,
                                    runs=int(batch_len),
                                    pop=int(n_genomes),
                                    gen=int(gen),
                                    use_hints=int(gen_use_hints),
                                    combos=int(n_combos),
                                )
                            gen_use_hints = 0
                        else:
                            gen_use_hints = 1

                        if gen < int(n_generations) - 1:
                            t0 = time.perf_counter() if phase_timing else 0.0
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
                            _sync()
                            if t0:
                                _log_phase(
                                    phase="next_generation",
                                    ms=(time.perf_counter() - t0) * 1000.0,
                                    runs=int(batch_len),
                                    pop=int(n_genomes),
                                    gen=int(gen),
                                    use_hints=int(gen_use_hints),
                                    combos=int(n_combos),
                                )

                    # Pack a compact GA->FG candidate table for this batch, avoiding large
                    # `(runs, pop, payload_cols)` downloads. Row 0 is per-run best (tracked
                    # across generations), rows 1..K are top-score entries from the final population.
                    t0 = time.perf_counter() if phase_timing else 0.0
                    gpu_api.ga_pack_fg_candidates_table_segmented(
                        table_slot=int(song_slot),
                        run_idx_start=int(local_run_idx),
                        n_runs=int(batch_len),
                        n_genomes_per_run=int(n_genomes),
                        n_slots=int(n_slots),
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
                    )
                    _sync()
                    if t0:
                        _log_phase(
                            phase="pack_fg_candidates",
                            ms=(time.perf_counter() - t0) * 1000.0,
                            runs=int(batch_len),
                            pop=int(n_genomes),
                            gen=int(n_generations),
                            use_hints=0,
                            combos=int(n_combos),
                        )

                    if audit_redundancy:
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
                        _restore_song_gpu_state()
                        _stage_segment_initial_populations(
                            run_start=int(run_start_global),
                            seg_runs=int(seg_len),
                            segment_pop_arr=segment_pop,
                        )
                        gpu_api.ga_init_runs_best(run_idx_start=0, n_runs=int(seg_len), n_slots=int(n_slots))
                    except Exception:
                        break

            if last_exc is not None:
                raise last_exc

            local_run_idx += int(batch_len)

        if audit_redundancy:
            audit_payload_segments.append(
                gpu_api.ga_download_runs_payload(
                    n_runs=int(seg_len),
                    n_genomes=int(n_genomes),
                    n_slots=int(n_slots),
                )
            )

        payload_segments.append(
            gpu_api.ga_download_fg_selected_payload(
                table_slot=int(song_slot),
                n_runs=int(seg_len),
                limit=int(fg_candidate_limit),
                top_base_keep=int(top_base_keep),
                base_budget=int(base_budget),
                fg_budget_end=int(fg_budget_end),
            )
        )
        run_start_global += seg_len

    if not payload_segments:
        raise RuntimeError("Internal error: no GA payload segments were produced")

    if audit_redundancy and audit_payload_segments:
        try:
            audit_payload = (
                audit_payload_segments[0]
                if len(audit_payload_segments) == 1
                else np.concatenate(audit_payload_segments, axis=0)
            )
            audit_record = analyze_ga_redundancy_from_runs_payload(
                runs_payload=audit_payload,
                item_stats=item_stats,
                base_fixed_stats_arr=base_fixed_stats_arr,
                calc_song=calc_song,
                cfg_data=cfg_data,
                ga_seed=ga_seed,
            )
            logger.info(summarize_ga_redundancy_record(audit_record))
            audit_path = write_ga_redundancy_audit_record(audit_record)
            logger.info(f"[GA Redundancy Audit] wrote {audit_path}")
        except Exception as exc:
            logger.warning(f"[GA Redundancy Audit] Warning: failed to capture audit: {exc}")

    if len(payload_segments) != 1:
        raise RuntimeError(
            f"Internal error: expected a single selected-payload segment, got {len(payload_segments)} segments"
        )
    return payload_segments[0]


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
    ga_seed: int | None = None,
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

    if ga_seed is not None:
        try:
            random.seed(int(ga_seed) & 0xFFFFFFFF)
        except Exception:
            pass

    logger.info("=== STARTING GENETIC ALGORITHM SOLVER ===")
    logger.info(f"Configuration: GearOptimization={optimize_gear}, MiniOptimization={optimize_minis}")

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
        logger.error(f"[GA Error] initialize_pools failed for song {calc_song['metadata'].get('Song Name', 'Unknown')}")
        return None, [], [], None, [], [], []

    if whitelisted_minis:
        logger.info(f"[GA] Force-including {len(whitelisted_minis)} whitelisted minis in initialization.")

    # Build configuration data
    # GPU-only policy: ignore any attempt to disable GPU via config.
    use_gpu_mode_requested = True
    try:
        use_gpu_mode_requested = (
            cfg.getboolean("IterationEngine", "GPU_Mode", fallback=True) if hasattr(cfg, "getboolean") else True
        )
    except Exception:
        use_gpu_mode_requested = True
    if not use_gpu_mode_requested:
        logger.warning("[GPU] IterationEngine.GPU_Mode=false ignored (GPU-only policy); forcing GPU_Mode=true.")
    use_gpu_mode = True

    use_gpu_native_requested = True
    try:
        use_gpu_native_requested = (
            cfg.getboolean("IterationEngine", "GPU_Native_GA", fallback=True) if hasattr(cfg, "getboolean") else True
        )
    except Exception:
        use_gpu_native_requested = True
    if not use_gpu_native_requested:
        logger.warning(
            "[GPU] IterationEngine.GPU_Native_GA=false ignored (GPU-only policy); forcing GPU_Native_GA=true."
        )
    use_gpu_native = True

    if not _GPU_NATIVE_AVAILABLE:
        raise RuntimeError("GPU-native GA is required (GPU-only policy) but taichi_gem dependencies are unavailable.")

    # GPU-native GA uses Taichi kernels directly (taichi_gem.api) and is not compatible with
    # cross-process GPU ownership. GPU-only policy: do not fall back to CPU GA.
    try:
        from .gpu_executor import is_gpu_worker_mode

        if is_gpu_worker_mode():
            raise RuntimeError(
                "GPU worker mode is not supported in GPU-only GA because it depends on a removed CPU-owned path."
            )
    except ImportError:
        pass

    # FG fitness heuristic was removed: GA always optimizes true base score (all perfects).
    # The FG finder separately evaluates loadouts with FG configs to find the best FG score.
    if use_gpu_mode:
        logger.info(f"[GPU] GPU_Mode enabled (Native GA: {use_gpu_native})")

    cfg_data = {
        "selected_color": selected_color,
        "primary_color": str(p_color or ""),
        "secondary_color": str(s_color or ""),
        "use_gpu": use_gpu_mode,
        "use_gpu_native": use_gpu_native,
        "fg_candidate_limit": read_fg_candidate_limit(
            cfg,
            default=FG_CANDIDATE_LIMIT,
            min_limit=LOADOUTS_PER_SONG_LIMIT,
        ),
        "user_ft": safe_int(cfg.get("UserInputStatsGems", "fever_time", fallback=0)),
        "user_ff": safe_int(cfg.get("UserInputStatsGems", "fever_fill", fallback=0)),
        "user_pp": safe_int(cfg.get("UserInputStatsGems", "perfect_points", fallback=0)),
        "user_cm": safe_int(cfg.get("UserInputStatsGems", "combo_multiplier", fallback=0)),
        "user_fm": safe_int(cfg.get("UserInputStatsGems", "fever_multiplier", fallback=0)),
        "static_elem_input": safe_int(cfg.get("ElementalGems", selected_color, fallback=0)),
    }
    # DEV / DEBUG: convergence trace flags
    # (GAConvergenceTrace, GAConvergenceTraceEvery, GAConvergenceTraceOutDir,
    #  GAConvergenceTraceSongFilter).
    try:
        cfg_data["ga_convergence_trace_enabled"] = bool(
            cfg.getboolean("IterationEngine", "GAConvergenceTrace", fallback=False)
        )
    except Exception:
        cfg_data["ga_convergence_trace_enabled"] = False
    try:
        cfg_data["ga_convergence_trace_every"] = max(
            1,
            safe_int(cfg.get("IterationEngine", "GAConvergenceTraceEvery", fallback="1"), 1),
        )
    except Exception:
        cfg_data["ga_convergence_trace_every"] = 1
    try:
        cfg_data["ga_convergence_trace_out_dir"] = str(
            cfg.get("IterationEngine", "GAConvergenceTraceOutDir", fallback="artifacts/ga_trace")
            or "artifacts/ga_trace"
        )
    except Exception:
        cfg_data["ga_convergence_trace_out_dir"] = "artifacts/ga_trace"
    try:
        cfg_data["ga_convergence_trace_song_filter"] = str(
            cfg.get("IterationEngine", "GAConvergenceTraceSongFilter", fallback="") or ""
        )
    except Exception:
        cfg_data["ga_convergence_trace_song_filter"] = ""
    try:
        cfg_data["ga_steady_state_enabled"] = bool(
            cfg.getboolean("IterationEngine", "GPU_GA_SteadyStateEnabled", fallback=True)
        )
    except Exception:
        cfg_data["ga_steady_state_enabled"] = True
    try:
        cfg_data["ga_steady_state_refresh_pct"] = max(
            0.0,
            min(0.75, safe_float(cfg.get("IterationEngine", "GPU_GA_SteadyStateRefreshPct", fallback="0.25"), 0.25)),
        )
    except Exception:
        cfg_data["ga_steady_state_refresh_pct"] = 0.25
    try:
        cfg_data["ga_steady_state_min_refresh"] = max(
            0,
            safe_int(cfg.get("IterationEngine", "GPU_GA_SteadyStateMinRefresh", fallback="8"), 8),
        )
    except Exception:
        cfg_data["ga_steady_state_min_refresh"] = 8
    # ForceGreatsFinder runs after GA and requires BaseStats for downstream FG batching.
    # Keep this flag on cfg_data so the GPU decode step can include BaseStats
    # without relying on an environment variable.
    try:
        from ..core.config import read_iteration_engine_settings

        ie = read_iteration_engine_settings(cfg)
        fg_enabled = bool(ie.force_greats_mode) and (bool(ie.force_greats_finder) or bool(ie.manual_force_greats))
    except Exception:
        fg_enabled = False
    cfg_data["fg_require_stats"] = bool(fg_enabled)
    # PRODUCTION: modern optimizer runtime path is GPU-native.
    # --- GPU-NATIVE GA PATH ---
    # If using GPU mode, bypass the entire CPU loop mechanism.
    if cfg_data.get("use_gpu", False) and cfg_data.get("use_gpu_native", True) and _GPU_NATIVE_AVAILABLE:
        logger.info("=== RUNNING GPU-NATIVE GENETIC ALGORITHM ===")
        logger.info(f"  Population: {GA_POPULATION_SIZE}, Generations: {ga_depth}")

        # 3. Create Registry (restrict pools only for non-optimized slots).
        registry_fixed_gear = fixed_gear if not bool(optimize_gear) else None
        registry_fixed_minis = fixed_minis if not bool(optimize_minis) else None
        registry = ItemRegistry(
            gear_pool, mini_pool, slots, fixed_gear=registry_fixed_gear, fixed_minis=registry_fixed_minis
        )

        gpu_data = registry.to_gpu_arrays()
        base_stats_arr, _ = build_base_fixed_stats_array(base_stats_fixed, cfg_data)
        num_runs = max(1, int(ga_settings.multi_start or 1))
        gens_per_run = max(1, (ga_depth + num_runs - 1) // num_runs)
        logger.info(f"  Multi-start runs: {num_runs} (generations per run: {gens_per_run})")

        gpu_tournament_k = safe_int(cfg.get("IterationEngine", "GPU_GA_TournamentK", fallback=3), 3)
        gpu_tournament_k = max(1, min(8, int(gpu_tournament_k)))

        gpu_mutation_rate = safe_float(
            cfg.get("IterationEngine", "GPU_GA_MutationRate", fallback=GA_MUTATION_RATE), GA_MUTATION_RATE
        )
        gpu_mutation_rate = max(0.0, min(1.0, float(gpu_mutation_rate)))

        gpu_immigrant_rate = safe_float(cfg.get("IterationEngine", "GPU_GA_ImmigrantRate", fallback=0.0), 0.0)
        gpu_immigrant_rate = max(0.0, min(1.0, float(gpu_immigrant_rate)))

        try:
            from .taichi_gem import fields as gpu_fields
        except Exception:
            gpu_fields = None

        heuristic_k = int(getattr(gpu_fields, "GA_INIT_HEURISTIC_K", 0) or 0)
        init_heuristic_topk = None
        if heuristic_k > 0:
            try:
                init_heuristic_topk = build_ga_init_heuristic_topk(
                    item_stats=gpu_data["item_stats"],
                    slot_start=gpu_data["slot_start"],
                    slot_count=gpu_data["slot_count"],
                    primary_color=str(p_color or ""),
                    secondary_color=str(s_color or ""),
                    heuristic_k=int(heuristic_k),
                    n_slots=9,
                )
            except Exception as exc:
                logger.warning(f"[GPU GA] Warning: failed to build init heuristic table: {exc}")

        seed_ids = extract_db_seed_ids(db_seed=db_seed, registry=registry, n_slots=9)
        have_seed = seed_ids is not None
        runs_payload = run_gpu_native_ga_runs_payload_prebuilt(
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            song_slot=int(song_slot),
            item_stats=gpu_data["item_stats"],
            slot_start=gpu_data["slot_start"],
            slot_count=gpu_data["slot_count"],
            base_fixed_stats_arr=base_stats_arr,
            n_generations=int(gens_per_run),
            initial_populations=None,
            num_runs=int(num_runs),
            n_genomes=int(GA_POPULATION_SIZE),
            init_heuristic_topk=init_heuristic_topk,
            init_heuristic_k=int(heuristic_k),
            init_heuristic_copies=25,
            db_seed_ids=seed_ids if have_seed else None,
            db_seed_prob=float(ga_settings.db_seed_prob if have_seed else 0.0),
            db_seed_copies=1 if have_seed else 0,
            db_seed_mutations=int(getattr(ga_settings, "db_seed_mutations", 1) or 0) if have_seed else 0,
            elite_count=int(GA_ELITISM),
            mutation_rate=float(gpu_mutation_rate),
            immigrant_rate=float(gpu_immigrant_rate),
            tournament_k=int(gpu_tournament_k),
            color_flags=build_color_flags(p_color, s_color, selected_color),
            cfg_data=cfg_data,
            ga_seed=ga_seed,
        )

        fg_candidate_limit = int(cfg_data.get("fg_candidate_limit", FG_CANDIDATE_LIMIT))
        if fg_candidate_limit <= 0:
            fg_candidate_limit = FG_CANDIDATE_LIMIT

        best_data, best_gear, best_minis, unique_evaluated = decode_gpu_native_ga_runs_payload(
            runs_payload=runs_payload,
            registry=registry,
            cfg_data=cfg_data,
            base_stats_fixed=base_stats_fixed,
            fg_candidate_limit=fg_candidate_limit,
            calc_song=calc_song,
            ref_arrays=ref_arrays,
        )

        # Winner refinement:
        #
        # GPU-native GA uses warm-start scoring (`use_hints=1`) for throughput, but warm-start relies on a bounded
        # local search that can under-score some genomes (and even pick a different FT/FF combo) when hints are stale
        # or inherited across mutated/crossover children. When that happens, the GA payload can represent a suboptimal
        # gem allocation for the correct gear/minis loadout, which later shows up as "same loadout_hash improved by
        # gem split" inconsistencies.
        #
        # To keep persisted winners stable, we always re-solve the final GA winner with the canonical cold (no-hints)
        # GPU gem solver and replace the payload when it improves score.
        refine_winner = env_flag("GPU_GA_WINNER_REFINEMENT", "1")
        exact_check = env_flag("GPU_GA_WINNER_EXACT_CHECK", "0")
        if refine_winner or exact_check:
            try:
                from .scoring.fever_solver import solve_best_fever_combination

                genome = best_data.get("Genome") if isinstance(best_data, dict) else None
                if isinstance(genome, list) and genome:
                    winner_stats = _add_genome_item_stats(base_stats_fixed, genome)
                    override_cfg = {
                        "user_ft": int(cfg_data.get("user_ft", 0) or 0),
                        "user_ff": int(cfg_data.get("user_ff", 0) or 0),
                        "user_pp": int(cfg_data.get("user_pp", 0) or 0),
                        "user_cm": int(cfg_data.get("user_cm", 0) or 0),
                        "user_fm": int(cfg_data.get("user_fm", 0) or 0),
                        "selected_color": str(cfg_data.get("selected_color", "") or p_color or ""),
                        "static_elem_input": int(cfg_data.get("static_elem_input", 0) or 0),
                        "use_gpu": True,
                    }
                    refined = solve_best_fever_combination(
                        cfg,
                        winner_stats,
                        calc_song,
                        ref_arrays,
                        silent=True,
                        override_cfg=override_cfg,
                    )
                    if isinstance(refined, dict) and refined:
                        refined_score = int(refined.get("Score", 0) or 0)
                        best_score = int(best_data.get("Score", 0) or 0)
                        if refined_score > best_score:
                            song_name = str((calc_song or {}).get("metadata", {}).get("Song Name", "") or "")
                            logger.warning(
                                "[GPU] refined GA winner payload: song=%r best=%d refined=%d delta=%d",
                                song_name,
                                best_score,
                                refined_score,
                                refined_score - best_score,
                            )
                            if refine_winner:
                                g_ft = int(refined.get("FT", 0) or 0)
                                g_ff = int(refined.get("FF", 0) or 0)
                                gems = refined.get("GemCounts") if isinstance(refined.get("GemCounts"), dict) else {}
                                g_pp = int((gems or {}).get("Perfect Points", 0) or 0)
                                g_cm = int((gems or {}).get("Combo Multiplier", 0) or 0)
                                g_fm = int((gems or {}).get("Fever Multiplier", 0) or 0)
                                g_ov = int((gems or {}).get("Element", 0) or 0)
                                sel = str(
                                    refined.get("Selected Element", "")
                                    or override_cfg.get("selected_color", "")
                                    or p_color
                                    or ""
                                )
                                refined_stats = refined.get("Stats") if isinstance(refined.get("Stats"), dict) else None
                                if not isinstance(refined_stats, dict) or not refined_stats:
                                    # Defensive: rebuild stats even if the solver omitted a full `Stats` payload.
                                    base_fixed_arr, _sel_built = build_base_fixed_stats_array(
                                        base_stats_fixed, cfg_data
                                    )
                                    merged = _add_genome_item_stats(build_stats_dict(base_fixed_arr), genome)
                                    refined_stats = apply_gems_to_base_stats(
                                        merged,
                                        sel,
                                        g_ft,
                                        g_ff,
                                        g_pp,
                                        g_cm,
                                        g_fm,
                                        g_ov,
                                    )
                                best_data = _build_best_result_payload(
                                    score=int(refined_score),
                                    genome=genome,
                                    stats=refined_stats,
                                    selected_color=sel,
                                    g_ft=g_ft,
                                    g_ff=g_ff,
                                    g_pp=g_pp,
                                    g_cm=g_cm,
                                    g_fm=g_fm,
                                    g_ov=g_ov,
                                )
                                best_gear = list(best_data.get("Gear") or best_gear or [])
                                best_minis = list(best_data.get("Minis") or best_minis or [])
                        elif exact_check and refined_score < best_score:
                            song_name = str((calc_song or {}).get("metadata", {}).get("Song Name", "") or "")
                            logger.warning(
                                "[GPU][ExactCheck] GA payload beat canonical winner solve (unexpected): song=%r best=%d refined=%d delta=%d",
                                song_name,
                                best_score,
                                refined_score,
                                refined_score - best_score,
                            )
            except Exception:
                # Never fail the run for a winner refinement issue; fall back to the GA payload.
                pass

        logger.info(f"=== GPU-NATIVE GA COMPLETE: Best Score {int(best_data.get('Score', 0))} ===")

        # FG booster(s): optional candidate augmentation to improve ForceGreatsFinder coverage
        # without inflating the downstream candidate limit (we re-select to the same funnel size).
        try:
            try:
                from ..core.config import read_iteration_engine_settings

                force_greats_enabled = bool(read_iteration_engine_settings(cfg).force_greats_finder)
            except Exception:
                force_greats_enabled = False
            # PRODUCTION: combo booster flag (FG_COMBO_BOOSTER_ENABLED).
            combo_enabled = env_flag("FG_COMBO_BOOSTER_ENABLED", "1")

            boosted = None
            if force_greats_enabled and combo_enabled:
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
                    cfg_data=cfg_data,
                )
        except Exception:
            pass

        return best_data, best_gear, best_minis, None, [], [], unique_evaluated

    raise RuntimeError("CPU GA path removed (GPU-only policy). Enable GPU-native GA and Taichi/Vulkan support.")
