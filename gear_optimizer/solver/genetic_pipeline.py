"""
GPU-native GA payload helpers for gear and mini co-evolution.

This module contains the payload generation, decoding, and selection helpers used by
the native in-flight optimizer. The legacy direct CPU GA entrypoint has been removed.
"""

import logging
import time
import importlib

import numpy as np

from ..core.parsing import env_flag, env_get, env_int

logger = logging.getLogger(__name__)


def _ga_redundancy_audit_enabled() -> bool:
    return env_flag("GA_REDUNDANCY_AUDIT")


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
from ..core.gem_defs import build_gem_counts, build_gem_details
from ..core.color_flags import normalize_color_flags
from ..core.profile_events import emit_profile_event
from .base_stats import (
    COLOR_TO_STAT_INDEX,
    STAT_NAMES,
    build_base_fixed_stats_array,
    build_stats_array,
    build_stats_dict,
)
from .scoring.stats_ops import apply_gems_to_base_stats
from ..helpers.ga_helpers.unique_eval import select_exact_unique_row_indices
from ..helpers.ga_helpers.redundancy_audit import (
    analyze_ga_redundancy_from_runs_payload,
    summarize_ga_redundancy_record,
    write_ga_redundancy_audit_record,
)
from ..helpers.song_helpers.force_greats.entry_utils import build_fg_group_meta
from .item_registry import ItemRegistry
from .convergence_trace import build_convergence_trace_writer
from .gpu_tuning_policy import choose_ga_batch_runs

# Optional: GPU-native GA dependencies are probed without importing Taichi eagerly.
try:
    _GPU_NATIVE_AVAILABLE = importlib.util.find_spec("taichi") is not None
except Exception as e:
    logger.debug(f"genetic:_ga_redundancy_audit_enabled: {e}")
    _GPU_NATIVE_AVAILABLE = False


def _require_gpu_api():
    # Import on-demand so the app can auto-size GPU_SONG_SLOTS before Taichi fields allocate.
    try:
        gpu_api = importlib.import_module("gear_optimizer.solver.taichi_gem.api")
    except Exception as exc:
        raise RuntimeError(f"GPU-native GA requires taichi_gem api/fields: {exc}") from exc
    return gpu_api


def _require_gpu_fields():
    try:
        return importlib.import_module("gear_optimizer.solver.taichi_gem.fields")
    except Exception as exc:
        raise RuntimeError(f"GPU-native GA requires taichi_gem api/fields: {exc}") from exc


def _resolve_ga_payload_candidate_limit(fg_candidate_limit: int) -> int:
    """
    Canonical GA->FG staging bound.

    Exact FG owns candidate reduction. GA may order generated candidates for the
    fixed staging buffer, but must not apply a smaller heuristic funnel first.
    """
    return 5000


def _resolve_ga_novelty_repair_attempts(cfg_data: dict | None) -> int:
    cfg = dict(cfg_data or {})
    raw = env_get("GPU_GA_NOVELTY_REPAIR_ATTEMPTS")
    if raw is None or str(raw).strip() == "":
        raw = cfg.get("ga_novelty_repair_attempts", 2)
    try:
        attempts = int(raw)
    except Exception as e:
        logger.debug(f"genetic:_resolve_ga_novelty_repair_attempts: {e}")
        attempts = 2
    return max(0, min(4, int(attempts)))


def _selected_color_stat_index(color: str) -> int:
    return int(COLOR_TO_STAT_INDEX.get(str(color or ""), -1))


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
        "GemCounts": build_gem_counts(g_pp, g_cm, g_fm, g_ov),
        "Stats": dict(stats or {}),
        "Selected Element": str(selected_color or ""),
        "Details": build_gem_details(g_ft, g_ff, g_pp, g_cm, g_fm, g_ov),
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
        "GemCounts": build_gem_counts(g_pp, g_cm, g_fm, g_ov),
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


def _compute_global_ftff_combo_caps(
    *,
    item_stats: "np.ndarray | None",
    slot_start: "np.ndarray | None",
    slot_count: "np.ndarray | None",
    base_fixed_stats_arr: "np.ndarray | None",
    total_budget: int,
    gem_scale_fever: int,
    n_slots: int = 9,
) -> tuple[int, int]:
    """
    Compute conservative global FT/FF gem caps for combo-table pruning.

    The FT/FF kernels enforce per-genome max gems from stat ceilings:
      max_ft_gems = floor((MAX_STAT - base_ft_stat) / gem_scale_fever)
      max_ff_gems = floor((MAX_STAT - base_ff_stat) / gem_scale_fever)

    For a fixed song + item pools we can derive a safe global cap by using the
    minimum possible base FT/FF across all genomes (base-fixed + per-slot minima).
    Any combo above these caps is impossible for every genome and can be skipped.
    """
    budget_i = max(0, int(total_budget))
    gem_scale_i = int(gem_scale_fever)
    if budget_i <= 0 or gem_scale_i <= 0:
        return budget_i, budget_i

    try:
        stats = np.asarray(item_stats, dtype=np.int32)
        starts = np.asarray(slot_start, dtype=np.int32).reshape(-1)
        counts = np.asarray(slot_count, dtype=np.int32).reshape(-1)
        base = np.asarray(base_fixed_stats_arr, dtype=np.int32).reshape(-1)
    except Exception as e:
        logger.debug(f"genetic:_compute_global_ftff_combo_caps: {e}")
        return budget_i, budget_i

    if stats.ndim != 2 or int(stats.shape[1]) < 5 or int(base.size) < 5:
        return budget_i, budget_i

    slot_lim = min(int(n_slots), int(starts.shape[0]), int(counts.shape[0]))
    if slot_lim <= 0:
        return budget_i, budget_i

    min_ft_stat = int(base[3])
    min_ff_stat = int(base[4])
    n_items = int(stats.shape[0])

    for s in range(slot_lim):
        count_i = int(counts[s] or 0)
        if count_i <= 0:
            continue
        start_i = int(starts[s] or 0)
        if start_i < 0:
            start_i = 0
        end_i = min(int(n_items), int(start_i + count_i))
        if end_i <= start_i:
            continue
        slot_stats = stats[start_i:end_i]
        min_ft_stat += int(np.min(slot_stats[:, 3]))
        min_ff_stat += int(np.min(slot_stats[:, 4]))

    max_stat_index = 160
    cap_ft = (int(max_stat_index) - int(min_ft_stat)) // int(gem_scale_i)
    cap_ff = (int(max_stat_index) - int(min_ff_stat)) // int(gem_scale_i)
    cap_ft = max(0, min(int(budget_i), int(cap_ft)))
    cap_ff = max(0, min(int(budget_i), int(cap_ff)))
    return int(cap_ft), int(cap_ff)


def _abort_requested_now(abort_requested) -> bool:
    if abort_requested is None or not callable(abort_requested):
        return False
    try:
        return bool(abort_requested())
    except Exception as e:
        logger.debug(f"genetic:_abort_requested_now: {e}")
        return False


def _raise_if_abort_requested(abort_requested, where: str) -> None:
    if _abort_requested_now(abort_requested):
        raise RuntimeError(f"GpuExecutor aborted: {where}")


# DEV / DEBUG: PERF_TIMING, GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS, GPU_NATIVE_GA_VULKAN_RETRIES, GPU_NATIVE_GA_BATCH_RUNS.
_PERF_TIMING = env_flag("PERF_TIMING", "0")
_GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS = env_int("GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS", 0)
_GPU_NATIVE_GA_VULKAN_RETRIES = env_int("GPU_NATIVE_GA_VULKAN_RETRIES", 1)
_GPU_NATIVE_GA_BATCH_RUNS = env_int("GPU_NATIVE_GA_BATCH_RUNS", 0)
# Prune FT/FF combo tables to globally feasible caps derived from base-stat ceilings.
_GPU_NATIVE_GA_GLOBAL_FTFF_CAPS = env_flag("GPU_NATIVE_GA_GLOBAL_FTFF_CAPS", "1")


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
    except Exception as e:
        logger.debug(f"genetic:_promote_best_candidate_over_header: {e}")
        best_score_run = 0
    try:
        cand_best = max(candidates, key=lambda c: int(c.get("BaseScore") or c.get("Score") or 0))
    except Exception as e:
        logger.debug(f"genetic:_promote_best_candidate_over_header: {e}")
        cand_best = None
    if isinstance(cand_best, dict):
        try:
            cand_score = int(cand_best.get("BaseScore") or cand_best.get("Score") or 0)
        except Exception as e:
            logger.debug(f"genetic:_promote_best_candidate_over_header: {e}")
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
                except Exception as e:
                    logger.debug(f"genetic:_promote_best_candidate_over_header: {e}")

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
    fg_group_meta_limit: int | None = None,
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

    fg_group_meta_limit_i: int | None
    try:
        fg_group_meta_limit_i = None if fg_group_meta_limit is None else max(0, int(fg_group_meta_limit))
    except Exception as e:
        logger.debug(f"genetic:decode_gpu_native_ga_runs_payload: {e}")
        fg_group_meta_limit_i = None

    def _should_build_fg_group_meta(index: int, *, enabled: bool) -> bool:
        if not bool(enabled):
            return False
        if fg_group_meta_limit_i is None:
            return True
        return int(index) < int(fg_group_meta_limit_i)

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

        payload_limit_raw = cfg_data.get("ga_payload_candidate_limit")
        if payload_limit_raw is None:
            payload_limit_raw = max(int(fg_candidate_limit), int(runs_payload.shape[0]) - 1)
        eff_limit = int(payload_limit_raw or fg_candidate_limit)
        if eff_limit <= 0:
            eff_limit = int(cfg_data.get("fg_candidate_limit", FG_CANDIDATE_LIMIT) or FG_CANDIDATE_LIMIT)
        eff_limit = max(LOADOUTS_PER_SONG_LIMIT, min(5000, int(eff_limit)))

        perf = _PERF_TIMING
        t_total = time.perf_counter() if perf else 0.0

        try:
            selected_n = int(runs_payload[0, 0])
        except Exception as e:
            logger.debug(f"genetic:_should_build_fg_group_meta: {e}")
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
        include_base_stats = True
        fg_group_meta_enabled = bool(isinstance(calc_song, dict) and calc_song and fg_group_meta_limit_i != 0)
        need_base_stats = bool(include_base_stats or fg_group_meta_enabled)

        base_stats_arr = None
        sel_color_built = None
        if need_base_stats:
            base_stats_arr, sel_color_built = build_base_fixed_stats_array(base_stats_fixed, cfg_data)

        sel_color = str(cfg_data.get("selected_color", "") or "")
        if sel_color_built:
            sel_color = str(sel_color_built)

        sel_color_idx = _selected_color_stat_index(sel_color)

        t_stats = 0.0
        final_stats_mat = None
        item_stats_sum = None
        stat_names = None

        if need_base_stats:
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

            if need_base_stats and base_stats_arr is not None and item_stats_sum is not None:
                # Always try to provide BaseStats when requested; ForceGreats batching can
                # operate on BaseStats even if full post-gem Stats reconstruction fails.
                try:
                    base_row_stats = base_stats_arr + item_stats_sum[i]
                    base_stats = build_stats_dict(base_row_stats)
                    if include_base_stats:
                        data_obj["BaseStats"] = base_stats
                    if _should_build_fg_group_meta(i, enabled=fg_group_meta_enabled):
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
                            prefer_grid=True,
                        )
                        if isinstance(fg_group_meta, dict):
                            data_obj["_fg_group_meta"] = fg_group_meta
                except Exception as e:
                    logger.debug(f"genetic:_should_build_fg_group_meta: {e}")
                if include_full_stats and stat_names is not None:
                    try:
                        if final_stats_mat is not None:
                            row_stats = final_stats_mat[i]
                            current_stats = build_stats_dict(row_stats)
                            data_obj["Stats"] = current_stats
                    except Exception as e:
                        logger.debug(f"genetic:_should_build_fg_group_meta: {e}")

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
    except Exception as e:
        logger.debug(f"genetic:_should_build_fg_group_meta: {e}")
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
        except Exception as e:
            logger.debug(f"genetic:_should_build_fg_group_meta: {e}")
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
    except Exception as e:
        logger.debug(f"genetic:_should_build_fg_group_meta: {e}")
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
    except Exception as e:
        logger.debug(f"genetic:_should_build_fg_group_meta: {e}")
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
    include_base_stats = True
    fg_group_meta_enabled = bool(isinstance(calc_song, dict) and calc_song)

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
    except Exception as e:
        logger.debug(f"genetic:_add: {e}")
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
        if base_stats is not None and _should_build_fg_group_meta(i, enabled=fg_group_meta_enabled):
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
                prefer_grid=True,
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
    elite_count: int = GA_ELITISM,
    mutation_rate: float = GA_MUTATION_RATE,
    immigrant_rate: float = 0.0,
    tournament_k: int = 3,
    color_flags: dict | None = None,
    cfg_data: dict | None = None,
    ga_seed: int | None = None,
    abort_requested=None,
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
    cfg_data = dict(cfg_data or {})
    color_flags = dict(color_flags or {})
    trace_writer, trace_every = build_convergence_trace_writer(
        calc_song=calc_song,
        cfg_data=cfg_data,
        ga_seed=ga_seed,
    )
    trace_t0 = time.perf_counter() if trace_writer is not None else 0.0

    if ga_seed is None:
        raise ValueError("GPU-native GA requires an explicit per-run ga_seed")
    try:
        seed_base = int(ga_seed) & 0xFFFFFFFF
    except Exception as exc:
        raise ValueError("GPU-native GA requires an integer per-run ga_seed") from exc

    if not _GPU_NATIVE_AVAILABLE:
        raise RuntimeError("GPU-native GA not available (missing dependencies)")

    gpu_api = _require_gpu_api()

    try:
        gpu_api_module = importlib.import_module("gear_optimizer.solver.taichi_gem.api")
        ensure_ready = gpu_api_module.ensure_ready
        precompute_timeline_gpu = gpu_api_module.precompute_timeline_gpu
        gpu_fields = _require_gpu_fields()
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

    # Reduce padded CPU↔GPU transfers by sizing multi-run GA buffers to the
    # current session's needs. This MUST happen before the first Taichi field
    # allocation (i.e., before ensure_ready/precompute_timeline triggers field allocation).
    gpu_fields.configure_ga_run_buffers(max_runs=num_runs, max_genomes=n_genomes)

    # Optional stability toggles (mirrors the native GPU payload path)
    reset_every_runs_env = str(_GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS)
    try:
        reset_every_runs = int(reset_every_runs_env)
    except Exception as e:
        logger.debug(f"genetic:run_gpu_native_ga_runs_payload_prebuilt: {e}")
        reset_every_runs = 0

    max_retries_env = str(_GPU_NATIVE_GA_VULKAN_RETRIES)
    try:
        max_retries = int(max_retries_env)
    except Exception as e:
        logger.debug(f"genetic:run_gpu_native_ga_runs_payload_prebuilt: {e}")
        max_retries = 1

    # DEV / DEBUG: phase timing flag (GPU_NATIVE_GA_PHASE_TIMING).
    perf = _PERF_TIMING
    phase_timing = env_flag("GPU_NATIVE_GA_PHASE_TIMING", "0")
    profile_events_enabled = bool(
        env_flag("METAFINDER_PROFILE_EVENTS", "0")
        or str(env_get("METAFINDER_PROFILE_EVENTS_PATH") or env_get("PROFILE_EVENTS_PATH") or "").strip()
    )
    phase_events_enabled = bool(phase_timing and profile_events_enabled)
    song_profile_key = None
    try:
        meta = calc_song.get("metadata", {}) if isinstance(calc_song, dict) else {}
        song_name = str(meta.get("Song Name") or meta.get("Song") or "").strip()
        song_diff = str(meta.get("Difficulty") or "").strip()
        if song_name:
            song_profile_key = f"{song_name} ({song_diff})" if song_diff else song_name
    except Exception as e:
        logger.debug(f"genetic:run_gpu_native_ga_runs_payload_prebuilt: {e}")
        song_profile_key = None

    def _emit_ga_setup_phase(*, phase: str, start: float, **extra_metrics) -> None:
        if not profile_events_enabled:
            return
        metrics = {
            "phase": str(phase),
            "ms": float((time.perf_counter() - float(start)) * 1000.0),
            "runs": int(num_runs),
            "pop": int(n_genomes),
            "song_slot": int(song_slot),
        }
        metrics.update(extra_metrics)
        emit_profile_event(
            component="gpu_executor",
            event="ga_gpu_setup_phase",
            song_key=song_profile_key,
            metrics=metrics,
        )

    if profile_events_enabled:
        emit_profile_event(
            component="gpu_executor",
            event="ga_gpu_phase_flags",
            song_key=song_profile_key,
            metrics={
                "perf_timing": int(bool(perf)),
                "phase_timing": int(bool(phase_timing)),
                "phase_events_enabled": int(bool(phase_events_enabled)),
            },
        )

    def _is_vulkan_semaphore_failure(exc: BaseException) -> bool:
        msg = str(exc)
        return ("failed to create semaphore" in msg) or ("RHI Error" in msg and "semaphore" in msg)

    def _restore_song_gpu_state() -> None:
        # Rebuild Taichi/GA static state for this song slot after hard resets.
        t_phase = time.perf_counter()
        ensure_ready(ref_arrays)
        _emit_ga_setup_phase(phase="ensure_ready_ref_arrays", start=t_phase)
        t_phase = time.perf_counter()
        precompute_timeline_gpu(calc_song, ref_arrays, song_slot=song_slot)
        _emit_ga_setup_phase(phase="precompute_timeline_gpu", start=t_phase)
        t_phase = time.perf_counter()
        gpu_api.ga_upload_item_stats(item_stats, slot_start, slot_count)
        _emit_ga_setup_phase(phase="ga_upload_item_stats", start=t_phase)
        t_phase = time.perf_counter()
        gpu_api.ga_upload_base_fixed_stats(base_fixed_stats_arr)
        _emit_ga_setup_phase(phase="ga_upload_base_fixed_stats", start=t_phase)

    # Load refs/timeline + upload static per-song GA data once.
    _raise_if_abort_requested(abort_requested, "before GPU-native GA setup")
    t_setup_total = time.perf_counter()
    _restore_song_gpu_state()
    _emit_ga_setup_phase(phase="restore_song_gpu_state", start=t_setup_total)

    # Optional heuristic top-K table for GPU initial population generation.
    init_heuristic_k = int(init_heuristic_k)
    if init_heuristic_topk is not None and init_heuristic_k > 0:
        t_phase = time.perf_counter()
        gpu_api.ga_upload_init_heuristic_topk(
            topk_ids=np.asarray(init_heuristic_topk, dtype=np.int32),
            heuristic_k=int(init_heuristic_k),
            n_slots=int(n_slots),
        )
        _emit_ga_setup_phase(phase="ga_upload_init_heuristic_topk", start=t_phase)

    (
        is_p_ft,
        is_s_ft,
        is_p_ff,
        is_s_ff,
        is_p_pp,
        is_s_pp,
        is_p_cm,
        is_s_cm,
        is_p_fm,
        is_s_fm,
        is_p_ov,
        is_s_ov,
    ) = normalize_color_flags(color_flags).as_tuple()

    total_budget = int(cfg_data.get("TotalBudget", 90))
    gem_scale_fever = int(cfg_data.get("GemScaleFever", 3))
    if _GPU_NATIVE_GA_GLOBAL_FTFF_CAPS:
        max_ft_gems_global, max_ff_gems_global = _compute_global_ftff_combo_caps(
            item_stats=item_stats,
            slot_start=slot_start,
            slot_count=slot_count,
            base_fixed_stats_arr=base_fixed_stats_arr,
            total_budget=int(total_budget),
            gem_scale_fever=int(gem_scale_fever),
            n_slots=int(n_slots),
        )
    else:
        max_ft_gems_global = int(total_budget)
        max_ff_gems_global = int(total_budget)
    novelty_repair_attempts = _resolve_ga_novelty_repair_attempts(cfg_data)

    fg_candidate_limit = int(cfg_data.get("fg_candidate_limit", FG_CANDIDATE_LIMIT) or FG_CANDIDATE_LIMIT)
    if fg_candidate_limit <= 0:
        fg_candidate_limit = FG_CANDIDATE_LIMIT
    fg_candidate_limit = max(LOADOUTS_PER_SONG_LIMIT, min(5000, int(fg_candidate_limit)))
    payload_candidate_limit = _resolve_ga_payload_candidate_limit(int(fg_candidate_limit))
    cfg_data["ga_payload_candidate_limit"] = int(payload_candidate_limit)
    top_base_keep = min(int(payload_candidate_limit), int(LOADOUTS_PER_SONG_LIMIT))
    base_budget = min(
        int(payload_candidate_limit),
        max(int(top_base_keep), int(int(payload_candidate_limit) * 0.55)),
    )
    fg_budget_end = min(
        int(payload_candidate_limit),
        int(base_budget) + int(int(payload_candidate_limit) * 0.30),
    )

    # Island model (mirrors _run_gpu_native_ga)
    num_islands = min(GPU_GA_NUM_ISLANDS, n_genomes // 10)  # At least 10 per island
    if num_islands < 1:
        num_islands = 1

    # Determine an auto batch size that avoids combo-chunking in ga_evaluate_population.
    # Chunking increases kernel launch count, so we prefer keeping n_total*n_combos <= MAX_EVALS_PER_DISPATCH.
    t_phase = time.perf_counter()
    try:
        n_combos = int(
            gpu_api._ensure_ftff_combo_tables(
                total_budget,
                max_ft_gems=int(max_ft_gems_global),
                max_ff_gems=int(max_ff_gems_global),
            )
        )
    except Exception as e:
        logger.debug(f"genetic:_restore_song_gpu_state: {e}")
        n_combos = 0
    _emit_ga_setup_phase(phase="ensure_ftff_combo_tables", start=t_phase, combos=int(n_combos))

    batch_runs_default = choose_ga_batch_runs(
        n_genomes=int(n_genomes),
        n_combos=int(n_combos),
        max_evals_per_dispatch=int(gpu_fields.MAX_EVALS_PER_DISPATCH),
        max_genomes=int(gpu_fields.MAX_GENOMES),
        batch_runs_override=int(_GPU_NATIVE_GA_BATCH_RUNS),
    ).batch_runs

    payload_segments: list[np.ndarray] = []
    audit_payload_segments: list[np.ndarray] = []
    audit_redundancy = _ga_redundancy_audit_enabled()

    phase_samples_current: dict[str, list[float]] | None = None

    def _p95_ms(values: list[float]) -> float:
        if not values:
            return 0.0
        ordered = sorted(float(v) for v in values)
        idx = int(round(0.95 * (len(ordered) - 1)))
        idx = max(0, min(idx, len(ordered) - 1))
        return float(ordered[idx])

    def _emit_ga_phase_window(*, phase_samples: dict[str, list[float]], batch_run_start: int, batch_runs: int) -> None:
        if not phase_events_enabled or not phase_samples:
            return
        for phase_name, values in phase_samples.items():
            samples = [float(v) for v in values]
            if not samples:
                continue
            total_ms = float(sum(samples))
            sample_count = int(len(samples))
            max_ms = float(max(samples))
            emit_profile_event(
                component="gpu_executor",
                event="ga_gpu_phase",
                song_key=song_profile_key,
                metrics={
                    "phase": str(phase_name),
                    "samples": int(sample_count),
                    "total_ms": float(total_ms),
                    "mean_ms": float(total_ms / float(sample_count)) if sample_count > 0 else 0.0,
                    "p95_ms": float(_p95_ms(samples)),
                    "max_ms": float(max_ms),
                    "batch_run_start": int(batch_run_start),
                    "batch_runs": int(batch_runs),
                    "pop": int(n_genomes),
                    "n_generations": int(n_generations),
                    "combos": int(n_combos),
                    "sync_timed": 1,
                },
            )

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
        if phase_samples_current is not None:
            phase_samples_current.setdefault(str(phase), []).append(float(ms))
        try:
            logger.info(
                "[PERF][GAGPUPhase] "
                f"phase={phase} runs={int(runs)} pop={int(pop)} gen={int(gen)} "
                f"use_hints={int(use_hints)} combos={int(combos)} ms={float(ms):.3f}"
            )
        except Exception as e:
            logger.debug(f"genetic:_log_phase: {e}")
            return

    def _stage_segment_initial_populations(*, run_start: int, seg_runs: int, segment_pop_arr) -> None:
        _raise_if_abort_requested(abort_requested, "before staging initial populations")
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
            heuristic_copies=int(init_heuristic_copies),
        )

    run_start_global = 0
    while run_start_global < num_runs:
        _raise_if_abort_requested(abort_requested, "before GPU-native GA segment")
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
            _raise_if_abort_requested(abort_requested, "before GPU-native GA batch")
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
                    _raise_if_abort_requested(abort_requested, "before loading GPU-native GA batch")
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

                    n_total = int(batch_len) * int(n_genomes)
                    use_lightweight_runs_refresh = trace_writer is None
                    phase_samples_current = {} if phase_events_enabled else None

                    for gen in range(int(n_generations)):
                        _raise_if_abort_requested(abort_requested, f"before GPU-native GA generation {int(gen)}")
                        t0 = time.perf_counter() if phase_timing else 0.0
                        prepare_population_base_stats_fn = getattr(gpu_api, "ga_prepare_population_base_stats", None)
                        if callable(prepare_population_base_stats_fn):
                            prepare_population_base_stats_fn(
                                n_genomes=n_total,
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
                        eval_kwargs = dict(
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
                            max_ft_gems_global=int(max_ft_gems_global),
                            max_ff_gems_global=int(max_ff_gems_global),
                            materialize_mode="none",
                            use_base_candidate_cache=False,
                        )
                        evaluate_prepared_fn = getattr(gpu_api, "ga_evaluate_prepared_population", None)
                        if callable(evaluate_prepared_fn):
                            evaluate_prepared_fn(**eval_kwargs)
                        else:
                            gpu_api.ga_evaluate_population(**eval_kwargs)
                        _sync()
                        _raise_if_abort_requested(
                            abort_requested, f"after GPU-native GA evaluate generation {int(gen)}"
                        )
                        if t0:
                            _log_phase(
                                phase="evaluate",
                                ms=(time.perf_counter() - t0) * 1000.0,
                                runs=int(batch_len),
                                pop=int(n_genomes),
                                gen=int(gen),
                                use_hints=0,
                                combos=int(n_combos),
                            )

                        # Keep selection scores exact every generation, but only write full per-genome
                        # result rows when tracing needs them. Row 0 stays exact in both paths.
                        is_migration_gen = (
                            num_islands > 1
                            and (gen + 1) % GPU_GA_GENS_PER_MIGRATION == 0
                            and gen < (int(n_generations) - 1)
                        )
                        fuse_refresh_with_next = (
                            use_lightweight_runs_refresh
                            and not bool(phase_timing)
                            and not bool(is_migration_gen)
                            and gen < int(n_generations) - 1
                        )
                        fused_refresh_next_done = False
                        t0 = time.perf_counter() if phase_timing else 0.0
                        if fuse_refresh_with_next:
                            gpu_api.ga_refresh_scores_update_runs_best_and_next_generation_fused_runs(
                                run_idx_start=int(local_run_idx),
                                n_runs=int(batch_len),
                                n_genomes_per_run=int(n_genomes),
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
                                mutation_rate=float(mutation_rate),
                                immigrant_rate=float(immigrant_rate),
                                tournament_k=int(tournament_k),
                                n_islands=int(num_islands),
                                elites_per_island=int(elite_count),
                                novelty_repair_attempts=int(novelty_repair_attempts),
                            )
                            fused_refresh_next_done = True
                        elif use_lightweight_runs_refresh:
                            gpu_api.ga_refresh_scores_and_update_runs_best(
                                run_idx_start=int(local_run_idx),
                                n_runs=int(batch_len),
                                n_genomes_per_run=int(n_genomes),
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
                            )
                        else:
                            gpu_api.ga_write_best_results_and_update_runs_best(
                                run_idx_start=int(local_run_idx),
                                n_runs=int(batch_len),
                                n_genomes_per_run=int(n_genomes),
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
                            )
                        _sync()
                        _raise_if_abort_requested(
                            abort_requested, f"after GPU-native GA runs-best update generation {int(gen)}"
                        )
                        if t0:
                            _log_phase(
                                phase="update_runs_best",
                                ms=(time.perf_counter() - t0) * 1000.0,
                                runs=int(batch_len),
                                pop=int(n_genomes),
                                gen=int(gen),
                                use_hints=0,
                                combos=int(n_combos),
                            )

                        t0 = time.perf_counter() if phase_timing else 0.0
                        if trace_writer is not None:
                            gpu_api.ga_update_global_best(int(n_total), n_slots=int(n_slots))
                        _sync()
                        _raise_if_abort_requested(
                            abort_requested, f"after GPU-native GA global-best update generation {int(gen)}"
                        )
                        if t0:
                            _log_phase(
                                phase="write_best_hints",
                                ms=(time.perf_counter() - t0) * 1000.0,
                                runs=int(batch_len),
                                pop=int(n_genomes),
                                gen=int(gen),
                                use_hints=0,
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
                            except Exception as e:
                                logger.debug(f"genetic:_stage_segment_initial_populations: {e}")

                        # Migration only if another generation will be evaluated (avoid corrupting final snapshots).
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
                            _raise_if_abort_requested(
                                abort_requested, f"after GPU-native GA migration generation {int(gen)}"
                            )
                            if t0:
                                _log_phase(
                                    phase="migration",
                                    ms=(time.perf_counter() - t0) * 1000.0,
                                    runs=int(batch_len),
                                    pop=int(n_genomes),
                                    gen=int(gen),
                                    use_hints=0,
                                    combos=int(n_combos),
                                )

                        if gen < int(n_generations) - 1 and not fused_refresh_next_done:
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
                                novelty_repair_attempts=int(novelty_repair_attempts),
                            )
                            _sync()
                            _raise_if_abort_requested(
                                abort_requested, f"after GPU-native GA next-generation generation {int(gen)}"
                            )
                            if t0:
                                _log_phase(
                                    phase="next_generation",
                                    ms=(time.perf_counter() - t0) * 1000.0,
                                    runs=int(batch_len),
                                    pop=int(n_genomes),
                                    gen=int(gen),
                                    use_hints=0,
                                    combos=int(n_combos),
                                )

                    # Pack a compact GA->FG candidate table for this batch, avoiding large
                    # `(runs, pop, payload_cols)` downloads. Row 0 is per-run best (tracked
                    # across generations), rows 1..K are top-score entries from the final population.
                    t0 = time.perf_counter() if phase_timing else 0.0
                    _raise_if_abort_requested(abort_requested, "before packing FG candidates from GPU-native GA")
                    gpu_api.ga_pack_fg_candidates_table_segmented(
                        table_slot=int(song_slot),
                        run_idx_start=int(local_run_idx),
                        n_runs=int(batch_len),
                        n_genomes_per_run=int(n_genomes),
                        n_slots=int(n_slots),
                        total_budget=total_budget,
                        gem_scale_fever=gem_scale_fever,
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
                    _sync()
                    _raise_if_abort_requested(abort_requested, "after packing FG candidates from GPU-native GA")
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
                    if phase_samples_current:
                        _emit_ga_phase_window(
                            phase_samples=phase_samples_current,
                            batch_run_start=int(global_run_idx),
                            batch_runs=int(batch_len),
                        )

                    if audit_redundancy:
                        if use_lightweight_runs_refresh:
                            gpu_api.ga_write_best_results_from_key(
                                n_genomes=int(n_total),
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
                            )
                            _sync()
                        _raise_if_abort_requested(abort_requested, "before GA payload snapshot download")
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
                    except Exception as e:
                        logger.debug(f"genetic:_stage_segment_initial_populations: {e}")
                        break

            if last_exc is not None:
                raise last_exc

            local_run_idx += int(batch_len)

        if audit_redundancy:
            _raise_if_abort_requested(abort_requested, "before GA audit payload download")
            audit_payload_segments.append(
                gpu_api.ga_download_runs_payload(
                    n_runs=int(seg_len),
                    n_genomes=int(n_genomes),
                    n_slots=int(n_slots),
                )
            )

        selected_payload = gpu_api.ga_download_fg_selected_payload(
            table_slot=int(song_slot),
            n_runs=int(seg_len),
            limit=int(payload_candidate_limit),
            top_base_keep=int(top_base_keep),
            base_budget=int(base_budget),
            fg_budget_end=int(fg_budget_end),
        )
        payload_segments.append(selected_payload)
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
