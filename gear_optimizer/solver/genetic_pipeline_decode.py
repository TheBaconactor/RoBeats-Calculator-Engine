"""CPU-side decoding of the GPU-native GA's selected payload (pipeline.ga.decode_ga_result)."""

import numpy as np

from ..core.gem_defs import build_gem_counts
from ..helpers.ga_helpers.unique_eval import select_exact_unique_row_indices
from .base_stats import (
    build_stats_array,
    build_stats_dict,
)
from .force_greats_common import FG_BASE_STATS7_KEY
from ..stats import apply_gems, gems, total


def decode_gpu_native_ga_runs_payload(
    *,
    runs_payload: "np.ndarray",
    registry: object,
    selected_color: str,
    base_stats_fixed: dict,
    fg_candidate_limit: int,
) -> tuple[dict, list, list, list[dict]]:
    """
    Decode the GPU-native GA's selected payload (CPU only, no Taichi calls): the best loadout's data, gear and minis,
    and the candidate pool for the FG stage (the header best, then the GPU-selected rows, exact duplicates dropped).

    Row 0: [selected_count, best_score, best_ids(9), best_results(7), best_run_idx, ...]; rows 1..N:
    [run_idx, row_idx, score, ids(9), results(7), base_stats7(7)]; results = [score, ft, ff, pp, cm, fm, ov].
    """
    runs_payload = np.asarray(runs_payload, dtype=np.int32)
    if runs_payload.ndim != 2:
        raise ValueError(f"runs_payload must be a 2D selected payload, got ndim={runs_payload.ndim}")
    n_slots = 9
    header_cols_min = 2 + n_slots + 7 + 1
    if int(runs_payload.shape[0]) < 1:
        raise ValueError("runs_payload has no rows")
    if int(runs_payload.shape[1]) < header_cols_min:
        raise ValueError(f"runs_payload has too few columns: {runs_payload.shape[1]} < {header_cols_min}")
    selected_n = max(0, min(int(runs_payload[0, 0]), int(fg_candidate_limit), int(runs_payload.shape[0]) - 1))

    best_score = int(runs_payload[0, 1])
    best_ids = runs_payload[0, 2 : 2 + n_slots]
    _, g_ft, g_ff, g_pp, g_cm, g_fm, g_ov = (int(v) for v in runs_payload[0, 2 + n_slots : 2 + n_slots + 7])
    best_genome = registry.decode_genome(best_ids)
    best_gear, best_minis = list(best_genome[:6]), list(best_genome[6:9])
    # Stats exactly as the GPU kernels see them: the song's fixed stats, plus the items, plus gems.
    best_stats = apply_gems(
        total(base_stats_fixed, *(item.stats for item in best_genome if item is not None)),
        gems(pp=g_pp, cm=g_cm, fm=g_fm, ft=g_ft, ff=g_ff, element=g_ov),
        selected_color,
    )
    # The best loadout's items travel beside best_data (best_gear/best_minis), never inside it:
    # candidate Data becomes the persisted FG payload, and stored rows keep item ids and names.
    best_data = {
        "Score": best_score,
        "BaseScore": best_score,
        "FT": g_ft,
        "FF": g_ff,
        "GemCounts": build_gem_counts(g_pp, g_cm, g_fm, g_ov),
        "Stats": dict(best_stats or {}),
        "Selected Element": selected_color,
    }
    best_genome_ids = [int(x) for x in best_ids]
    candidates = [{
        "Score": best_score,
        "BaseScore": best_score,
        "Gear": list(best_gear),
        "Minis": list(best_minis),
        "GenomeIDs": list(best_genome_ids),
        "_ga_registry": registry,
        "Data": {**best_data, "GenomeIDs": list(best_genome_ids)},
    }]
    if selected_n <= 0:
        return best_data, best_gear, best_minis, candidates

    rows = runs_payload[1 : 1 + selected_n]
    packed_cols = 1 + n_slots + 7 + 7
    if int(rows.shape[1]) < 2 + packed_cols:
        raise ValueError(f"runs_payload candidate rows have too few columns: {rows.shape[1]} < {2 + packed_cols}")
    run_idx, row_idx, packed = rows[:, 0], rows[:, 1], rows[:, 2 : 2 + packed_cols]
    scores, ids = packed[:, 0], packed[:, 1 : 1 + n_slots]
    results, base_stats7 = packed[:, 1 + n_slots : 8 + n_slots], packed[:, 8 + n_slots : 15 + n_slots]
    keep, _ = select_exact_unique_row_indices(genome_ids_mat=ids, scores=scores, exact=True)
    if int(keep.size) != int(ids.shape[0]):
        run_idx, row_idx, scores, ids, results, base_stats7 = (
            a[keep] for a in (run_idx, row_idx, scores, ids, results, base_stats7)
        )
    base_stats_arr = build_stats_array(base_stats_fixed)
    item_stats_sum = registry.to_gpu_arrays()["item_stats"][ids].sum(axis=1)  # (n_cand, 10)
    for i in range(int(ids.shape[0])):
        score = int(scores[i])
        genome_ids = [int(x) for x in ids[i]]
        _, ft, ff, pp, cm, fm, ov = (int(v) for v in results[i])
        candidates.append({
            "Score": score,
            "BaseScore": score,
            "GenomeIDs": list(genome_ids),
            "_ga_registry": registry,
            "Data": {
                "Score": score,
                "FT": ft,
                "FF": ff,
                "GemCounts": build_gem_counts(pp, cm, fm, ov),
                "Selected Element": selected_color,
                "BaseScore": score,
                "_ga_gpu_run_idx": int(run_idx[i]),
                "_ga_gpu_row_idx": int(row_idx[i]),
                # Device-computed FG base components (the FG planner's scoring input; bit-exact equal to the host
                # BaseStats 7-vector, tests/test_gpu_base_stats7_equivalence.py).
                FG_BASE_STATS7_KEY: tuple(int(v) for v in base_stats7[i]),
                "GenomeIDs": list(genome_ids),
                "BaseStats": build_stats_dict(base_stats_arr + item_stats_sum[i]),
            },
        })
    # No host select here: the canonical color-folded select is the FG-prep funnel's
    # (prepare_ga_candidate_surface_for_fg).
    max_candidate_score = max(int(c.get("BaseScore") or c.get("Score") or 0) for c in candidates)
    if max_candidate_score > best_score:
        raise RuntimeError(
            "GPU-selected payload invariant violated: candidate score exceeds header best score "
            f"({max_candidate_score} > {best_score})"
        )
    return best_data, best_gear, best_minis, candidates
