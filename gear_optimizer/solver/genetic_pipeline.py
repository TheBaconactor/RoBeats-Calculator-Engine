"""
GPU-native GA payload helpers for gear and mini co-evolution.

This module contains the payload generation, decoding, and selection helpers used by
the native in-flight optimizer. The legacy direct CPU GA entrypoint has been removed.
"""

import logging
import time
import importlib

import numpy as np

from ..core.parsing import env_flag, env_get, env_str

logger = logging.getLogger(__name__)


from ..core.constants import (
    GA_POPULATION_SIZE,
    GA_MUTATION_RATE,
    GA_ELITISM,
    GEM_SCALE_NORMAL,
    GEM_SCALE_FEVER,
    GEM_STAT_TO_ELEMENT_SCALE,
    ELEMENTAL_GEM_SCALE,
    LOADOUTS_PER_SONG_LIMIT,
    SKIP_ITEM_KEYS,
    GPU_GA_NUM_ISLANDS,
    GPU_GA_GENS_PER_MIGRATION,
    GPU_GA_MIGRATE_COUNT,
)
from ..core.gem_defs import build_gem_counts, build_gem_details
from ..core.color_flags import normalize_color_flags
from ..core.profile_events import emit_profile_event, profile_events_active
from .base_stats import (
    COLOR_TO_STAT_INDEX,
    build_base_fixed_stats_array,
    build_stats_dict,
)
from .force_greats_common import FG_BASE_STATS7_KEY
from .scoring.stats_ops import apply_gems_to_base_stats
from ..helpers.ga_helpers.unique_eval import select_exact_unique_row_indices
from .gpu_tuning_policy import choose_ga_batch_runs

# Optional: GPU-native GA dependencies are probed without importing Taichi eagerly.
try:
    _GPU_NATIVE_AVAILABLE = importlib.util.find_spec("taichi") is not None
except Exception as e:
    logger.debug(f"genetic:taichi_probe: {e}")
    _GPU_NATIVE_AVAILABLE = False


def _resolve_ga_novelty_repair_attempts(cfg_data: dict | None) -> int:
    # cfg-driven only (config.ini GPU_GA_NoveltyRepairAttempts -> ga_novelty_repair_attempts);
    # the ambient GPU_GA_NOVELTY_REPAIR_ATTEMPTS env override was removed.
    cfg = dict(cfg_data or {})
    raw = cfg.get("ga_novelty_repair_attempts", 2)
    try:
        attempts = int(raw)
    except Exception as e:
        logger.debug(f"genetic:_resolve_ga_novelty_repair_attempts: {e}")
        attempts = 2
    return max(0, min(4, int(attempts)))


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


# DEV / DEBUG: PERF_TIMING.
# Vulkan reset/retry are hardwired constants (tests setattr these module globals directly).
_PERF_TIMING = env_flag("PERF_TIMING", "0")
_GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS = 0
_GPU_NATIVE_GA_VULKAN_RETRIES = 1
_GPU_NATIVE_GA_BATCH_RUNS = 0  # auto: choose_ga_batch_runs decides (was GPU_NATIVE_GA_BATCH_RUNS)


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


def decode_gpu_native_ga_runs_payload(
    *,
    runs_payload: "np.ndarray",
    registry: object,
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

        perf = _PERF_TIMING
        t_total = time.perf_counter() if perf else 0.0

        try:
            selected_n = int(runs_payload[0, 0])
        except Exception as e:
            logger.debug(f"genetic:decode_gpu_native_ga_runs_payload: {e}")
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
        best_stats = build_stats_dict(base_fixed_arr)
        for item in best_global_genome or []:
            if not item:
                continue
            for key, value in item.items():
                if key not in SKIP_ITEM_KEYS:
                    best_stats[key] = best_stats.get(key, 0) + value

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

        gear = list(best_gear or [])
        minis = list(best_minis or [])
        best_data = {
            "Score": int(best_global_score),
            "BaseScore": int(best_global_score),
            "Genome": list(best_global_genome or []),
            "Gear": gear,
            "Minis": minis,
            "GearNames": [g.get("Name", "None") for g in gear],
            "MiniNames": [m.get("Name", "None") for m in minis],
            "FT": int(g_ft),
            "FF": int(g_ff),
            "GemCounts": build_gem_counts(g_pp, g_cm, g_fm, g_ov),
            "Stats": dict(best_stats or {}),
            "Selected Element": str(selected_color or ""),
            "Details": build_gem_details(g_ft, g_ff, g_pp, g_cm, g_fm, g_ov),
        }
        best_genome_ids = [int(x) for x in np.asarray(best_ids, dtype=np.int32).tolist()]
        best_candidate = {
            "Score": int(best_global_score),
            "BaseScore": int(best_global_score),
            "Gear": list(best_gear or []),
            "Minis": list(best_minis or []),
            "GenomeIDs": list(best_genome_ids),
            "_ga_registry": registry,
            "Data": {**best_data, "GenomeIDs": list(best_genome_ids)},
        }

        if selected_n <= 0:
            return best_data, list(best_gear), list(best_minis), [best_candidate]

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
        # Device-computed base_stats7 (pack kernel cols): [pp, cm, fm, p_val, s_val, ft, ff].
        # This is the FG scoring input source (Slice 2); it is bit-exact equal to the
        # host BaseStats-dict 7-vector (tests/test_gpu_base_stats7_equivalence.py). It is
        # carried per candidate so the FG funnel does not re-derive it on the host.
        base_stats7_mat = np.asarray(packed[:, 1 + n_slots + 7 : 1 + n_slots + 7 + 7], dtype=np.int32)
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
            base_stats7_mat = base_stats7_mat[dedup_indices]

        # PERF/CPU NOTE:
        # - The GPU-selected payload already contains everything the in-flight pipeline needs
        #   (score + FT/FF + gem counts + selected element + (run,row) provenance).
        # - Reconstructing full per-candidate post-gem `Stats` is expensive.
        # - Response-frontier FG only needs `BaseStats`, so keep full `Stats`
        #   reconstruction opt-in and carry only `BaseStats` on the hot path by default.
        # cfg-driven only; the ambient GA_DECODE_INCLUDE_STATS env override was removed.
        include_full_stats = bool(
            isinstance(cfg_data, dict)
            and (cfg_data.get("ga_require_full_stats") or cfg_data.get("fg_require_full_stats"))
        )
        base_stats_arr, sel_color_built = build_base_fixed_stats_array(base_stats_fixed, cfg_data)

        sel_color = str(cfg_data.get("selected_color", "") or "")
        if sel_color_built:
            sel_color = str(sel_color_built)

        sel_color_idx = int(COLOR_TO_STAT_INDEX.get(str(sel_color or ""), -1))

        t_stats = 0.0
        final_stats_mat = None
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

        unique_evaluated: list[dict] = [best_candidate]
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

            data_obj = {
                "Score": score_val,
                "FT": g_ft_i,
                "FF": g_ff_i,
                "GemCounts": build_gem_counts(g_pp_i, g_cm_i, g_fm_i, g_ov_i),
                "Selected Element": str(sel_color or ""),
                "BaseScore": score_val,
                "_ga_gpu_run_idx": int(sel_run_idx[i]),
                "_ga_gpu_row_idx": int(sel_rows[i]),
                # Device-computed FG base components for this loadout (Slice 2 scoring input
                # source); consumed by the FG planner via FgPlanner._device_base_stats7_for_entry.
                FG_BASE_STATS7_KEY: tuple(int(v) for v in base_stats7_mat[i].tolist()),
            }
            data_obj["GenomeIDs"] = list(genome_ids)

            try:
                base_row_stats = base_stats_arr + item_stats_sum[i]
                base_stats = build_stats_dict(base_row_stats)
                data_obj["BaseStats"] = base_stats
            except Exception as e:
                logger.debug(f"genetic:decode_gpu_native_ga_runs_payload: {e}")
            if include_full_stats and final_stats_mat is not None:
                try:
                    row_stats = final_stats_mat[i]
                    current_stats = build_stats_dict(row_stats)
                    data_obj["Stats"] = current_stats
                except Exception as e:
                    logger.debug(f"genetic:decode_gpu_native_ga_runs_payload: {e}")

            cand_data = {
                "Score": score_val,
                "BaseScore": score_val,
                "GenomeIDs": list(genome_ids),
                "_ga_registry": registry,
                "Data": data_obj,
            }
            unique_evaluated.append(cand_data)

        # Gated DEBUG instrumentation (OFF by default): capture the raw GA->FG
        # candidate pool (the funnel INPUT) for Slice 1 tie analysis. Enabled only
        # when FG_SELECT_TIE_DUMP names a JSONL path.
        _tie_dump_path = env_str("FG_SELECT_TIE_DUMP", "")
        if _tie_dump_path:
            from .fg_effective_dedup import dump_candidate_pool_jsonl

            dump_candidate_pool_jsonl(
                _tie_dump_path,
                registry=registry,
                candidates=unique_evaluated,
                primary_color=str(cfg_data.get("primary_color", "") or ""),
                secondary_color=str(cfg_data.get("secondary_color", "") or ""),
                selected_color=str(sel_color or ""),
                limit=int(eff_limit),
            )

        # No host select here: decode returns the raw GPU-deduped candidate pool.
        # The single canonical color-folded select lives at the FG-prep funnel layer
        # (prepare_ga_candidate_surface_for_fg). Slice 1 STEP A proved on all 96 real
        # pools that color-folding this raw pool yields the identical selected set as
        # the former decode-side name-only select followed by the FG-prep select
        # (fold(name-dedup-51) == fold-direct-51), so removing this select is
        # bit-exact for best_fg_score.

        max_candidate_score = max((int(c.get("BaseScore") or c.get("Score") or 0) for c in unique_evaluated), default=0)
        if int(max_candidate_score) > int(best_global_score):
            raise RuntimeError(
                "GPU-selected payload invariant violated: candidate score exceeds header best score "
                f"({int(max_candidate_score)} > {int(best_global_score)})"
            )

        if perf:
            stats_ms = (time.perf_counter() - t_stats) * 1000.0
            total_ms = (time.perf_counter() - t_total) * 1000.0 if perf else 0.0
            logger.info(
                "[PERF][GADecode] "
                f"selected={int(selected_n)} unique_rows={int(dedup_stats.unique)} "
                f"duplicate_hits={int(dedup_stats.duplicate_hits)} replacements={int(dedup_stats.replacements)} "
                f"stats={stats_ms:.1f}ms total={total_ms:.1f}ms candidates={len(unique_evaluated)}"
            )

        return best_data, list(best_gear), list(best_minis), unique_evaluated
    raise ValueError(f"runs_payload must be a 2D selected payload, got ndim={runs_payload.ndim}")


def score_fused_fg_from_selected_payload(
    *,
    runs_payload: "np.ndarray",
    fg_scoring_bundle: object,
    fg_calc_song: dict,
    ref_arrays: dict,
    cfg_data: dict,
) -> dict:
    """Fused GA->FG owner step: score FG straight from the selected payload (Slice 3).

    Runs on the GPU-owner thread immediately after the GA pack/select, BEFORE the
    payload leaves the owner for async decode/persistence. It slices each selected
    candidate's device ``base_stats7`` (== base_components) from the payload and runs
    the FG response-frontier BUILD + SCORE on the owner, returning a map
    ``base_components_7tuple -> FgFusedOwnerScoreRow`` the driver materializes off the
    owner's critical path (the driver re-derives the same 7-tuples from the same
    payload, so the lookup is exact; the SCORE is a pure function of base_components).

    Required state (no fallback): the song-level FG scoring bundle + resolved FG calc
    song are prepared pre-GA (prepare_fg_static_sync / resolve_active_fg_calc_song) and
    attached to the GA request payload. Their absence fails loudly here.
    """
    if fg_scoring_bundle is None:
        raise ValueError(
            "fused GA->FG handoff requires the song-level FG scoring bundle on the GA "
            "request (prepare_fg_static_sync must run pre-GA)"
        )
    if not isinstance(fg_calc_song, dict):
        raise ValueError("fused GA->FG handoff requires a resolved FG calc song on the GA request")
    if not isinstance(ref_arrays, dict):
        raise ValueError("fused GA->FG handoff requires reference arrays")

    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import (
        score_fused_owner_base_components_on_gpu_owner,
    )

    payload = np.asarray(runs_payload, dtype=np.int32)
    if payload.ndim != 2 or int(payload.shape[0]) < 1:
        raise ValueError("fused GA->FG handoff requires a 2D selected payload")

    selected_n = int(payload[0, 0])
    if selected_n <= 0:
        return {}
    max_rows = int(payload.shape[0]) - 1
    if selected_n > max_rows:
        selected_n = max_rows

    # Candidate rows 1..selected_n; base_stats7 occupies the last 7 cols of each
    # 26-wide row: [run_idx, row_idx, score, ids(9), results(7), base_stats7(7)] ->
    # base_stats7 starts at col 2 + 1 + 9 + 7 = 19. Same layout the pack kernel writes
    # (payload.py) and decode consumes (decode_gpu_native_ga_runs_payload).
    base_stats7_col0 = 2 + 1 + 9 + 7
    cand_rows = payload[1 : 1 + selected_n]
    if int(cand_rows.shape[1]) < base_stats7_col0 + 7:
        raise ValueError(
            f"fused GA->FG handoff: selected payload rows too narrow for base_stats7 "
            f"({cand_rows.shape[1]} < {base_stats7_col0 + 7})"
        )
    base_components = np.ascontiguousarray(cand_rows[:, base_stats7_col0 : base_stats7_col0 + 7], dtype=np.int32)

    total_budget = int((cfg_data or {}).get("TotalBudget", 90) or 90)
    selected_color = str((cfg_data or {}).get("selected_color", "") or "")

    return score_fused_owner_base_components_on_gpu_owner(
        base_components=base_components,
        calc_song=fg_calc_song,
        ref_arrays=ref_arrays,
        selected_color=selected_color,
        scoring_bundle=fg_scoring_bundle,
        total_budget=int(total_budget),
    )


def upload_ga_song_slot_timeline_state(
    *,
    calc_song: dict,
    ref_arrays: dict,
    song_slot: int,
    setup_phase_emitter=None,
) -> None:
    """Precompute timeline state for one GPU song slot."""
    if not _GPU_NATIVE_AVAILABLE:
        raise RuntimeError("GPU-native GA not available (missing dependencies)")
    try:
        gpu_api = importlib.import_module("gear_optimizer.solver.taichi_gem.api")
    except Exception as exc:
        raise RuntimeError(f"GPU-native GA requires taichi_gem api: {exc}") from exc

    song_slot = int(song_slot)
    if song_slot < 0:
        song_slot = 0

    t_phase = time.perf_counter()
    gpu_api.precompute_timeline_gpu(calc_song, ref_arrays, song_slot=song_slot)
    if setup_phase_emitter is not None:
        setup_phase_emitter(phase="precompute_timeline_gpu", start=t_phase)


def upload_ga_global_static_state(
    *,
    item_stats: "np.ndarray",
    slot_start: "np.ndarray",
    slot_count: "np.ndarray",
    base_fixed_stats_arr: "np.ndarray",
    fg_gear_name_rank: "np.ndarray",
    fg_mini_sig_id: "np.ndarray",
    setup_phase_emitter=None,
) -> None:
    """Upload GA global item/base-stat buffers immediately before a GA run."""
    if not _GPU_NATIVE_AVAILABLE:
        raise RuntimeError("GPU-native GA not available (missing dependencies)")
    try:
        gpu_api = importlib.import_module("gear_optimizer.solver.taichi_gem.api")
    except Exception as exc:
        raise RuntimeError(f"GPU-native GA requires taichi_gem api: {exc}") from exc

    t_phase = time.perf_counter()
    gpu_api.ga_upload_item_stats(item_stats, slot_start, slot_count)
    if setup_phase_emitter is not None:
        setup_phase_emitter(phase="ga_upload_item_stats", start=t_phase)
    t_phase = time.perf_counter()
    gpu_api.ga_upload_base_fixed_stats(base_fixed_stats_arr)
    if setup_phase_emitter is not None:
        setup_phase_emitter(phase="ga_upload_base_fixed_stats", start=t_phase)
    t_phase = time.perf_counter()
    gpu_api.ga_upload_fg_effective_tables(fg_gear_name_rank, fg_mini_sig_id)
    if setup_phase_emitter is not None:
        setup_phase_emitter(phase="ga_upload_fg_effective_tables", start=t_phase)


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
    fg_gear_name_rank: "np.ndarray | None" = None,
    fg_mini_sig_id: "np.ndarray | None" = None,
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

    if ga_seed is None:
        raise ValueError("GPU-native GA requires an explicit per-run ga_seed")
    try:
        seed_base = int(ga_seed) & 0xFFFFFFFF
    except Exception as exc:
        raise ValueError("GPU-native GA requires an integer per-run ga_seed") from exc

    if fg_gear_name_rank is None or fg_mini_sig_id is None:
        raise ValueError(
            "GPU-native GA requires fg_gear_name_rank/fg_mini_sig_id effective-dedup "
            "tables for the song's color context (built at prep via "
            "fg_effective_dedup.effective_tables_for_context)"
        )

    if not _GPU_NATIVE_AVAILABLE:
        raise RuntimeError("GPU-native GA not available (missing dependencies)")

    # Import on-demand so the app can auto-size GPU_SONG_SLOTS before Taichi fields allocate.
    try:
        gpu_api = importlib.import_module("gear_optimizer.solver.taichi_gem.api")
        gpu_fields = importlib.import_module("gear_optimizer.solver.taichi_gem.fields")
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

    # DIAGNOSTIC (off by default; GA_LOOP_PROFILE=1). Decides whether the per-generation
    # GPU re-feed gap is host-bound (host Python + Vulkan submit latency -> reducing the
    # number of per-gen kernel submits via fusion would help) or GPU-bound (the kernels are
    # the work -> fusion would not help). For a sparse sample of steady-state generations it
    # times host-enqueue (launch all of a generation's kernels with the GPU starting idle, so
    # async launches return after enqueue/submit) vs gpu-exec (a trailing ti.sync()).
    # Warmup generations are skipped so one-time JIT compile is excluded. Zero overhead and no
    # logging when disabled; aggregated result is written to GA_LOOP_PROFILE_PATH (one JSON line
    # per GA request) only when enabled.
    ga_loop_profile = env_flag("GA_LOOP_PROFILE", "0")
    # Sub-flag (gated DEBUG, OFF by default): on sampled generations, sync AFTER each
    # production kernel (prepare / evaluate / fused refresh+nextgen) to attribute GPU exec
    # time per kernel family WITHOUT un-fusing the loop. Adds a few syncs on sampled gens
    # only; the fused production call is unchanged. This is the stable alternative to the
    # Taichi Vulkan kernel profiler, which segfaults on AMD/Vulkan teardown here.
    ga_loop_profile_perkernel = bool(ga_loop_profile and env_flag("GA_LOOP_PROFILE_PERKERNEL", "0"))
    _lp_warmup_gens = max(0, int(env_get("GA_LOOP_PROFILE_WARMUP_GENS", "8") or "8"))
    _lp_sample_every = max(1, int(env_get("GA_LOOP_PROFILE_SAMPLE_EVERY", "8") or "8"))
    _lp_acc = {
        "samples": 0,
        "host_enqueue_s": 0.0,
        "gpu_exec_s": 0.0,
        "host_max_s": 0.0,
        "gpu_max_s": 0.0,
        "prep_host_s": 0.0,
        "eval_host_s": 0.0,
        "rest_host_s": 0.0,
        # Per-kernel GPU-exec accumulators (ga_loop_profile_perkernel only):
        "pk_samples": 0,
        "pk_prep_gpu_s": 0.0,
        "pk_eval_gpu_s": 0.0,
        "pk_fused_gpu_s": 0.0,
    }
    _lp_ti = None
    if ga_loop_profile:
        import taichi as _lp_ti

    def _is_vulkan_semaphore_failure(exc: BaseException) -> bool:
        msg = str(exc)
        return ("failed to create semaphore" in msg) or ("RHI Error" in msg and "semaphore" in msg)

    def _restore_song_gpu_state() -> None:
        upload_ga_song_slot_timeline_state(
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            song_slot=song_slot,
            setup_phase_emitter=_emit_ga_setup_phase,
        )
        upload_ga_global_static_state(
            item_stats=item_stats,
            slot_start=slot_start,
            slot_count=slot_count,
            base_fixed_stats_arr=base_fixed_stats_arr,
            fg_gear_name_rank=fg_gear_name_rank,
            fg_mini_sig_id=fg_mini_sig_id,
            setup_phase_emitter=_emit_ga_setup_phase,
        )

    # Load refs/timeline + upload static per-song GA data once, in-request on the
    # owner. The per-slot upload helpers content-skip when the slot already holds
    # this song's state, so the request is self-sufficient without a separate
    # slot-warm side channel.
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
    max_ft_gems_global, max_ff_gems_global = _compute_global_ftff_combo_caps(
        item_stats=item_stats,
        slot_start=slot_start,
        slot_count=slot_count,
        base_fixed_stats_arr=base_fixed_stats_arr,
        total_budget=int(total_budget),
        gem_scale_fever=int(gem_scale_fever),
        n_slots=int(n_slots),
    )
    novelty_repair_attempts = _resolve_ga_novelty_repair_attempts(cfg_data)

    fg_candidate_limit = int(LOADOUTS_PER_SONG_LIMIT)

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

    # Batch width is sized by genome capacity only (MAX_GENOMES pool); the
    # eval budget is NOT a factor -- combo chunking inside
    # ga_evaluate_prepared_population owns TDR/dispatch-length safety and
    # accumulates bit-exactly across chunks. Co-batch up to num_runs at once.
    batch_runs_default = choose_ga_batch_runs(
        n_genomes=int(n_genomes),
        num_runs=int(num_runs),
        max_genomes=int(gpu_fields.MAX_GENOMES),
        batch_runs_override=int(_GPU_NATIVE_GA_BATCH_RUNS),
    ).batch_runs

    payload_segments: list[np.ndarray] = []

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
                # hard_reset restores GA-buffer defaults; re-size for the rest of the
                # song (was the GPU_NATIVE_GA_MAX_RUNS/GENOMES env bridge's job).
                gpu_fields.configure_ga_run_buffers(max_runs=int(num_runs), max_genomes=int(n_genomes))
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
                    gpu_api.ga_seed_rng_runs_indexed(
                        n_runs=int(batch_len),
                        n_genomes_per_run=int(n_genomes),
                        seed_base=int(seed_base),
                        run_idx_start=int(global_run_idx),
                    )

                    n_total = int(batch_len) * int(n_genomes)
                    phase_samples_current = {} if phase_events_enabled else None

                    # Loop-invariant per-batch kernel args: build the prepare/evaluate kwargs
                    # once so the per-generation prepare->evaluate GPU re-feed window does not
                    # rebuild these dicts every generation. Every value here is fixed for this
                    # batch (n_total, n_slots, budgets, color flags, ftff caps) and is recomputed
                    # to the same value if the attempt loop re-enters on a Vulkan-reset retry.
                    prepare_kwargs = dict(
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
                    )

                    for gen in range(int(n_generations)):
                        _raise_if_abort_requested(abort_requested, f"before GPU-native GA generation {int(gen)}")
                        _lp_sample = bool(ga_loop_profile and gen >= _lp_warmup_gens and (gen % _lp_sample_every) == 0)
                        if _lp_sample:
                            if env_flag("GA_LOOP_PROFILE_NOSYNC", "0"):
                                _lp_h0 = time.perf_counter()  # measure host in the production stream (no drain)
                            else:
                                _lp_ti.sync()
                                _lp_h0 = time.perf_counter()
                        t0 = time.perf_counter() if phase_timing else 0.0
                        gpu_api.ga_prepare_population_base_stats(**prepare_kwargs)
                        if _lp_sample and ga_loop_profile_perkernel:
                            _lp_ti.sync()
                            _lp_pk_after_prep = time.perf_counter()
                        if _lp_sample:
                            _lp_t_prep = time.perf_counter()
                        gpu_api.ga_evaluate_prepared_population(**eval_kwargs)
                        if _lp_sample and ga_loop_profile_perkernel:
                            _lp_ti.sync()
                            _lp_pk_after_eval = time.perf_counter()
                        if _lp_sample:
                            _lp_t_eval = time.perf_counter()
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
                            not bool(phase_timing) and not bool(is_migration_gen) and gen < int(n_generations) - 1
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
                        else:
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
                        if _lp_sample and ga_loop_profile_perkernel:
                            # GPU exec of the (fused) refresh+update+next-generation kernel.
                            # In the production fused path this single dispatch also absorbs
                            # the standalone next-generation kernel (fused_refresh_next_done).
                            _lp_ti.sync()
                            _lp_pk_after_fused = time.perf_counter()
                            _lp_acc["pk_samples"] += 1
                            _lp_acc["pk_prep_gpu_s"] += _lp_pk_after_prep - _lp_h0
                            _lp_acc["pk_eval_gpu_s"] += _lp_pk_after_eval - _lp_pk_after_prep
                            _lp_acc["pk_fused_gpu_s"] += _lp_pk_after_fused - _lp_pk_after_eval
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

                        if _lp_sample:
                            _lp_h1 = time.perf_counter()
                            _lp_ti.sync()
                            _lp_g1 = time.perf_counter()
                            _lp_acc["samples"] += 1
                            _lp_h = _lp_h1 - _lp_h0
                            _lp_g = _lp_g1 - _lp_h1
                            _lp_acc["host_enqueue_s"] += _lp_h
                            _lp_acc["gpu_exec_s"] += _lp_g
                            _lp_acc["prep_host_s"] += _lp_t_prep - _lp_h0
                            _lp_acc["eval_host_s"] += _lp_t_eval - _lp_t_prep
                            _lp_acc["rest_host_s"] += _lp_h1 - _lp_t_eval
                            if _lp_h > _lp_acc["host_max_s"]:
                                _lp_acc["host_max_s"] = _lp_h
                            if _lp_g > _lp_acc["gpu_max_s"]:
                                _lp_acc["gpu_max_s"] = _lp_g

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

                    last_exc = None
                    break
                except Exception as e:
                    last_exc = e
                    if attempt >= max_retries or not _is_vulkan_semaphore_failure(e):
                        break
                    try:
                        gpu_api.hard_reset_taichi(reason=str(e).splitlines()[0][:200])
                        # hard_reset restores GA-buffer defaults; re-size for the rest
                        # of the song (was the env bridge's job before flag elimination).
                        gpu_fields.configure_ga_run_buffers(max_runs=int(num_runs), max_genomes=int(n_genomes))
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

        _prof_dl = profile_events_active()
        _t_dl = time.perf_counter() if _prof_dl else 0.0
        selected_payload = gpu_api.ga_download_fg_selected_payload(
            table_slot=int(song_slot),
            n_runs=int(seg_len),
            limit=int(fg_candidate_limit),
        )
        if _prof_dl:
            emit_profile_event(
                component="fg_fused",
                event="fg_owner_phase",
                metrics={"phase": "download", "total_ms": (time.perf_counter() - _t_dl) * 1000.0},
            )
        payload_segments.append(selected_payload)
        run_start_global += seg_len

    if not payload_segments:
        raise RuntimeError("Internal error: no GA payload segments were produced")

    if len(payload_segments) != 1:
        raise RuntimeError(
            f"Internal error: expected a single selected-payload segment, got {len(payload_segments)} segments"
        )

    if ga_loop_profile and int(_lp_acc["samples"]) > 0:
        _lp_n = int(_lp_acc["samples"])
        _lp_host_total = float(_lp_acc["host_enqueue_s"])
        _lp_gpu_total = float(_lp_acc["gpu_exec_s"])
        _lp_rec = {
            "song": song_profile_key,
            "samples": _lp_n,
            "n_generations": int(n_generations),
            "pop": int(n_genomes),
            "runs": int(num_runs),
            "host_enqueue_mean_ms": 1000.0 * _lp_host_total / _lp_n,
            "gpu_exec_mean_ms": 1000.0 * _lp_gpu_total / _lp_n,
            "host_enqueue_max_ms": 1000.0 * float(_lp_acc["host_max_s"]),
            "gpu_exec_max_ms": 1000.0 * float(_lp_acc["gpu_max_s"]),
            "prep_host_mean_ms": 1000.0 * float(_lp_acc["prep_host_s"]) / _lp_n,
            "eval_host_mean_ms": 1000.0 * float(_lp_acc["eval_host_s"]) / _lp_n,
            "rest_host_mean_ms": 1000.0 * float(_lp_acc["rest_host_s"]) / _lp_n,
            # host_fraction ~ recoverable-by-fusion share of a generation: >0.5 => host/submit-bound
            # (reducing per-gen submits helps); <<0.5 => GPU-bound (fusion will not help).
            "host_fraction": _lp_host_total / max(1e-9, _lp_host_total + _lp_gpu_total),
        }
        _lp_pk_n = int(_lp_acc["pk_samples"])
        if _lp_pk_n > 0:
            _lp_rec["pk_samples"] = _lp_pk_n
            _lp_rec["pk_prep_gpu_mean_ms"] = 1000.0 * float(_lp_acc["pk_prep_gpu_s"]) / _lp_pk_n
            _lp_rec["pk_eval_gpu_mean_ms"] = 1000.0 * float(_lp_acc["pk_eval_gpu_s"]) / _lp_pk_n
            _lp_rec["pk_fused_gpu_mean_ms"] = 1000.0 * float(_lp_acc["pk_fused_gpu_s"]) / _lp_pk_n
        _lp_path = str(env_get("GA_LOOP_PROFILE_PATH", "") or "").strip()
        if _lp_path:
            try:
                import json as _lp_json
                import os as _lp_os

                _lp_dir = _lp_os.path.dirname(_lp_os.path.abspath(_lp_path))
                if _lp_dir:
                    _lp_os.makedirs(_lp_dir, exist_ok=True)
                with open(_lp_path, "a", encoding="utf-8") as _lp_fh:
                    _lp_fh.write(_lp_json.dumps(_lp_rec) + "\n")
            except Exception as e:
                logger.debug(f"genetic:ga_loop_profile_write: {e}")

    return payload_segments[0]
