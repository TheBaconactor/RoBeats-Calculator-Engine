"""
CPU-side decoding for the GPU-native GA multi-run payload.

Extracted from ``genetic_pipeline.py`` (issue #52 item 2) so the large GA
run-loop module no longer also owns the GPU-free payload decoder. The function
is GPU-free by contract (no Taichi calls): it only reconstructs candidate dicts
from the device-produced selected payload. It is shared by the single-thread
GPU-native GA path and the in-flight pipeline (GpuExecutor owner thread for
kernels + CPU main thread for formatting).
"""

import logging

import numpy as np

from gear_optimizer.rules import (
    ELEMENT_GEM_GAIN,
    STAT_GEM_ELEMENT_GAIN,
    STAT_GEM_GAIN_FEVER,
    STAT_GEM_GAIN_NORMAL,
)
from ..core.gem_defs import build_gem_counts
from ..helpers.ga_helpers.unique_eval import select_exact_unique_row_indices
from .base_stats import (
    COLOR_TO_STAT_INDEX,
    build_stats_array,
    build_stats_dict,
)
from .force_greats_common import FG_BASE_STATS7_KEY
from ..stats import apply_gems, gems, total

logger = logging.getLogger(__name__)


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

        selected_n = int(runs_payload[0, 0])
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

        g_ft = int(best_global_res_arr[1])
        g_ff = int(best_global_res_arr[2])
        g_pp = int(best_global_res_arr[3])
        g_cm = int(best_global_res_arr[4])
        g_fm = int(best_global_res_arr[5])
        g_ov = int(best_global_res_arr[6])

        selected_color = str(cfg_data.get("selected_color", "") or "")
        # Reconstruct Stats exactly like the GPU kernels: the song's fixed stats, plus the items, plus gems.
        best_stats = apply_gems(
            total(base_stats_fixed, *(item.stats for item in best_global_genome if item is not None)),
            gems(pp=g_pp, cm=g_cm, fm=g_fm, ft=g_ft, ff=g_ff, element=g_ov),
            selected_color,
        )

        # The best loadout's items travel beside best_data (best_gear/best_minis), never inside it:
        # candidate Data becomes the persisted FG payload, and stored rows keep item ids and names.
        best_data = {
            "Score": int(best_global_score),
            "BaseScore": int(best_global_score),
            "FT": int(g_ft),
            "FF": int(g_ff),
            "GemCounts": build_gem_counts(g_pp, g_cm, g_fm, g_ov),
            "Stats": dict(best_stats or {}),
            "Selected Element": str(selected_color or ""),
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
        dedup_indices, _ = select_exact_unique_row_indices(
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
        base_stats_arr = build_stats_array(base_stats_fixed)

        sel_color = str(cfg_data.get("selected_color", "") or "")

        sel_color_idx = int(COLOR_TO_STAT_INDEX.get(str(sel_color or ""), -1))

        final_stats_mat = None
        item_stats = registry.to_gpu_arrays()["item_stats"]  # (n_items, 10)
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

            gem_contributions[:, 0] = g_pp * STAT_GEM_GAIN_NORMAL
            gem_contributions[:, 1] = g_cm * STAT_GEM_GAIN_NORMAL
            gem_contributions[:, 2] = g_fm * STAT_GEM_GAIN_FEVER
            gem_contributions[:, 3] = g_ft * STAT_GEM_GAIN_FEVER
            gem_contributions[:, 4] = g_ff * STAT_GEM_GAIN_FEVER

            gem_contributions[:, 5] = g_ft * STAT_GEM_ELEMENT_GAIN
            gem_contributions[:, 6] = g_ff * STAT_GEM_ELEMENT_GAIN
            gem_contributions[:, 7] = g_fm * STAT_GEM_ELEMENT_GAIN
            gem_contributions[:, 8] = g_cm * STAT_GEM_ELEMENT_GAIN
            gem_contributions[:, 9] = g_pp * STAT_GEM_ELEMENT_GAIN

            if 5 <= sel_color_idx <= 9:
                gem_contributions[:, sel_color_idx] += g_ov * ELEMENT_GEM_GAIN

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
            except (IndexError, ValueError) as e:
                logger.debug(f"genetic:decode_gpu_native_ga_runs_payload: {e}")
            if include_full_stats and final_stats_mat is not None:
                try:
                    row_stats = final_stats_mat[i]
                    current_stats = build_stats_dict(row_stats)
                    data_obj["Stats"] = current_stats
                except (IndexError, ValueError) as e:
                    logger.debug(f"genetic:decode_gpu_native_ga_runs_payload: {e}")

            cand_data = {
                "Score": score_val,
                "BaseScore": score_val,
                "GenomeIDs": list(genome_ids),
                "_ga_registry": registry,
                "Data": data_obj,
            }
            unique_evaluated.append(cand_data)

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

        return best_data, list(best_gear), list(best_minis), unique_evaluated
    raise ValueError(f"runs_payload must be a 2D selected payload, got ndim={runs_payload.ndim}")
