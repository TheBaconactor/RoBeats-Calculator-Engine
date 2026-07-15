"""GPU-free formatting of the typed exact Base candidate surface."""

from __future__ import annotations

from typing import Any

import numpy as np

from gear_optimizer.core.constants import SKIP_ITEM_KEYS
from gear_optimizer.core.gem_defs import build_gem_counts, build_gem_details
from gear_optimizer.solver.base_stats import build_stats_dict
from gear_optimizer.solver.exact_base_search import ExactBasePipelineResult
from gear_optimizer.solver.force_greats_common import FG_BASE_STATS7_KEY
from gear_optimizer.solver.scoring.stats_ops import apply_gems_to_base_stats
from gear_optimizer.solver.solver_common import SolverContext


def _decode_loadout(context: SolverContext, ids: np.ndarray) -> list[dict[str, Any]]:
    loadout = context.registry.decode_loadout(np.asarray(ids, dtype=np.int32))
    if not isinstance(loadout, list) or len(loadout) != 9:
        raise RuntimeError("Exact Base registry did not decode a nine-item loadout")
    return loadout


def decode_exact_base_pipeline_result(
    *,
    result: ExactBasePipelineResult,
    context: SolverContext,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Format an already ranked typed surface without selecting or re-ranking it."""

    if not isinstance(result, ExactBasePipelineResult):
        raise TypeError(f"Expected ExactBasePipelineResult, got {type(result).__name__}")
    surface = result.candidate_surface
    candidate_ids = np.asarray(surface.candidate_ids, dtype=np.int32)
    scores = np.asarray(surface.base_scores, dtype=np.int32)
    result_rows = np.asarray(surface.result_rows, dtype=np.int32)
    base_stats7 = np.asarray(surface.base_stats7, dtype=np.int32)
    count = int(candidate_ids.shape[0])
    if count <= 0:
        raise RuntimeError("Exact Base result has an empty candidate surface")
    if candidate_ids.shape != (count, 9) or result_rows.shape != (count, 7):
        raise RuntimeError("Exact Base candidate surface has an invalid typed shape")
    if base_stats7.shape != (count, 7) or scores.shape != (count,):
        raise RuntimeError("Exact Base candidate surface arrays are not aligned")
    if np.any(scores[:-1] < scores[1:]):
        raise RuntimeError("Exact Base candidate surface lost Base-score ordering")

    item_stats = np.asarray(context.gpu_arrays["item_stats"], dtype=np.int32)
    base_fixed = np.asarray(context.base_fixed_stats_arr, dtype=np.int32)
    item_stats_sum = item_stats[candidate_ids].sum(axis=1, dtype=np.int64).astype(np.int32)
    selected_color = str(context.selected_color or "")
    candidates: list[dict[str, Any]] = []
    decoded_loadouts: list[list[dict[str, Any]]] = []
    for index in range(count):
        loadout = _decode_loadout(context, candidate_ids[index])
        decoded_loadouts.append(loadout)
        gear = list(loadout[:6])
        minis = list(loadout[6:9])
        ids = [int(value) for value in candidate_ids[index].tolist()]
        row = result_rows[index]
        score = int(scores[index])
        g_ft, g_ff, g_pp, g_cm, g_fm, g_ov = (int(value) for value in row[1:7])
        base_stats = build_stats_dict(base_fixed + item_stats_sum[index])
        data = {
            "Score": score,
            "BaseScore": score,
            "FT": g_ft,
            "FF": g_ff,
            "GemCounts": build_gem_counts(g_pp, g_cm, g_fm, g_ov),
            "Selected Element": selected_color,
            "LoadoutIDs": ids,
            "BaseStats": base_stats,
            "Stats": apply_gems_to_base_stats(
                base_stats,
                selected_color,
                g_ft,
                g_ff,
                g_pp,
                g_cm,
                g_fm,
                g_ov,
            ),
            FG_BASE_STATS7_KEY: tuple(int(value) for value in base_stats7[index].tolist()),
        }
        candidates.append(
            {
                "Score": score,
                "BaseScore": score,
                "Gear": gear,
                "Minis": minis,
                "LoadoutIDs": ids,
                "Data": data,
            }
        )

    best_loadout = decoded_loadouts[0]
    best_gear = list(best_loadout[:6])
    best_minis = list(best_loadout[6:9])
    best_row = result_rows[0]
    best_score = int(scores[0])
    g_ft, g_ff, g_pp, g_cm, g_fm, g_ov = (int(value) for value in best_row[1:7])
    best_stats = build_stats_dict(base_fixed)
    for item in best_loadout:
        for key, value in item.items():
            if key not in SKIP_ITEM_KEYS:
                best_stats[key] = best_stats.get(key, 0) + value
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
    best_ids = [int(value) for value in candidate_ids[0].tolist()]
    best_data = {
        "Score": best_score,
        "BaseScore": best_score,
        "Loadout": list(best_loadout),
        "LoadoutIDs": best_ids,
        "Gear": best_gear,
        "Minis": best_minis,
        "GearNames": [str(item.get("Name", "None")) for item in best_gear],
        "MiniNames": [str(item.get("Name", "None")) for item in best_minis],
        "FT": g_ft,
        "FF": g_ff,
        "GemCounts": build_gem_counts(g_pp, g_cm, g_fm, g_ov),
        "Stats": best_stats,
        "Selected Element": selected_color,
        "Details": build_gem_details(g_ft, g_ff, g_pp, g_cm, g_fm, g_ov),
    }
    return best_data, best_gear, best_minis, candidates


__all__ = ["decode_exact_base_pipeline_result"]
