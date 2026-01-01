from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from ....core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
)
from ....solver.scoring import FG_CACHE, _force_greats_counts_to_dict


def apply_gems_to_base_fast(
    base: dict[str, Any],
    sel_color: str,
    ft: int,
    ff: int,
    g_pp: int,
    g_cm: int,
    g_fm: int,
    g_ov: int,
) -> dict[str, Any]:
    out = dict(base or {})
    out["Perfect Points"] = out.get("Perfect Points", 0) + g_pp * GEM_SCALE_NORMAL
    out["Combo Multiplier"] = out.get("Combo Multiplier", 0) + g_cm * GEM_SCALE_NORMAL
    out["Fever Multiplier"] = out.get("Fever Multiplier", 0) + g_fm * GEM_SCALE_FEVER
    out["Fever Time"] = out.get("Fever Time", 0) + ft * GEM_SCALE_FEVER
    out["Fever Fill Rate"] = out.get("Fever Fill Rate", 0) + ff * GEM_SCALE_FEVER
    out["Chill"] = out.get("Chill", 0) + g_pp * GEM_STAT_TO_ELEMENT_SCALE
    out["Flow"] = out.get("Flow", 0) + g_cm * GEM_STAT_TO_ELEMENT_SCALE
    out["Rush"] = out.get("Rush", 0) + g_fm * GEM_STAT_TO_ELEMENT_SCALE
    out["Beat"] = out.get("Beat", 0) + ft * GEM_STAT_TO_ELEMENT_SCALE
    out["Vibe"] = out.get("Vibe", 0) + ff * GEM_STAT_TO_ELEMENT_SCALE
    if sel_color:
        out[sel_color] = out.get(sel_color, 0) + g_ov * ELEMENTAL_GEM_SCALE
    return out


def fp_targets_to_forced_counts(
    fp_counts: list[Any],
    base_stats: dict[str, Any],
    ft_gems: int,
    ff_gems: int,
    scorer: Any,
) -> list[int]:
    if not fp_counts:
        return []
    ft_stat = int(base_stats.get("Fever Time", 0)) + int(ft_gems) * GEM_SCALE_FEVER
    ff_stat = int(base_stats.get("Fever Fill Rate", 0)) + int(ff_gems) * GEM_SCALE_FEVER
    non_fever_base, _, _, raw_fever_fill = scorer.get_fever_params(ft_stat, ff_stat)
    if non_fever_base <= 0:
        return [0] * len(fp_counts)
    import math

    base_ceil = math.ceil(raw_fever_fill)

    def _min_forced_for_fp(fp_target: int) -> int:
        if fp_target <= 0:
            return 0
        delta = (base_ceil + fp_target - 1) - raw_fever_fill
        if delta < 0:
            return 0
        return int(math.floor(delta * 2.0) + 1)

    forced_counts: list[int] = []
    for fp in fp_counts:
        fp_i = int(fp)
        forced = _min_forced_for_fp(fp_i)
        if forced > non_fever_base:
            forced = non_fever_base
        forced_counts.append(int(forced))
    return forced_counts


def apply_gpu_results_to_entries(
    *,
    pending_sigs: list[str],
    pending: list[dict[str, Any]],
    sig_map: dict[str, list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]],
    sel_color: str,
    n_sections: int,
    max_per_section: int,
    counts_list: Any,
    fg_scorer: Any,
    result_final: Any,
    result_base: Any,
    result_cfg_idx: Any,
    result_cfg_counts: Any,
    result_ft: Any,
    result_ff: Any,
    result_g_pp: Any,
    result_g_cm: Any,
    result_g_fm: Any,
    result_g_ov: Any,
    result_score_penalty: Any,
    result_fill_penalty: Any,
    fg_variants: list[dict[str, Any]],
    build_details_fn: Callable[[dict[str, Any]], dict[str, Any]],
    names_list_fn: Callable[[Any], list[str]],
    perf: bool,
) -> float:
    t0 = time.perf_counter() if perf else 0.0
    for idx, (sig, bs) in enumerate(zip(pending_sigs, pending)):
        final_score = int(result_final[idx])
        base_score = int(result_base[idx])
        ft_val = int(result_ft[idx])
        ff_val = int(result_ff[idx])
        g_pp = int(result_g_pp[idx])
        g_cm = int(result_g_cm[idx])
        g_fm = int(result_g_fm[idx])
        g_ov = int(result_g_ov[idx])
        score_penalty = int(result_score_penalty[idx])
        fill_penalty = int(result_fill_penalty[idx])
        _ = score_penalty, fill_penalty

        if result_cfg_counts is not None:
            cfg_counts = list(result_cfg_counts[idx]) if result_cfg_counts[idx] else []
        else:
            cfg_idx = int(result_cfg_idx[idx]) if result_cfg_idx is not None else -1
            cfg_counts = list(counts_list[cfg_idx]) if 0 <= cfg_idx < len(counts_list) else []

        forced_counts = cfg_counts
        if cfg_counts and fg_scorer is not None:
            try:
                forced_counts = fp_targets_to_forced_counts(cfg_counts, bs, ft_val, ff_val, fg_scorer)
            except Exception:
                forced_counts = cfg_counts

        gem_counts = {
            "Perfect Points": g_pp,
            "Combo Multiplier": g_cm,
            "Fever Multiplier": g_fm,
            "Element": g_ov,
        }

        final_stats = apply_gems_to_base_fast(
            bs,
            str(sel_color),
            ft_val,
            ff_val,
            g_pp,
            g_cm,
            g_fm,
            g_ov,
        )

        fg_info = {
            "config": _force_greats_counts_to_dict(forced_counts, max(2, len(forced_counts))),
            "final_score": final_score,
        }

        fg_variant = {
            "BaseScore": base_score,
            "Score": final_score,
            "FT": ft_val,
            "FF": ff_val,
            "GemCounts": gem_counts,
            "Stats": final_stats,
            "Selected Element": str(sel_color),
            "ForceGreats": fg_info,
        }

        for entry, eval_data, _ in sig_map.get(sig, []):
            if "base_score" not in entry:
                entry["base_score"] = entry.get("score")

            fg_variants.append(
                {
                    "data": fg_variant,
                    "gear": entry.get("gear", []),
                    "minis": entry.get("minis", []),
                    "score": base_score,
                    "fg_score": final_score,
                    "base_score": base_score,
                }
            )
            entry["force"] = {
                "score": final_score,
                "gear": names_list_fn(entry.get("gear", [])),
                "minis": names_list_fn(entry.get("minis", [])),
                "details": build_details_fn(fg_variant),
            }
            entry["fg_score"] = final_score

            c_ft = int(eval_data.get("FT", 0) or 0)
            c_ff = int(eval_data.get("FF", 0) or 0)
            FG_CACHE[(sig, str(sel_color), c_ft, c_ff, int(n_sections), int(max_per_section))] = fg_variant

    return (time.perf_counter() - t0) if perf else 0.0

