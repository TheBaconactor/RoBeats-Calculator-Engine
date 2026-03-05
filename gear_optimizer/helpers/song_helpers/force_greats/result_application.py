from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from ....core.constants import GEM_SCALE_FEVER
from ....core.utils import get_selected_element
from ....solver.scoring import FG_CACHE, _force_greats_counts_to_dict
from ....solver.scoring.force_greats import FORCE_GREATS_ALGO_VERSION
from ....solver.scoring.stats_ops import apply_gems_to_base_stats


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
    return apply_gems_to_base_stats(
        base,
        str(sel_color),
        int(ft),
        int(ff),
        int(g_pp),
        int(g_cm),
        int(g_fm),
        int(g_ov),
        add_missing_element_key=True,
    )


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return int(default)
        return int(value)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return int(default)


def materialize_stats_from_payload(
    payload: Any,
    *,
    selected_element: Any = None,
    ft_override: Any = None,
    ff_override: Any = None,
    mutate_payload: bool = False,
) -> dict[str, Any]:
    """
    Build `Stats` from `BaseStats` + gem allocations when needed.

    This helper centralizes FG payload materialization used by pipeline, inflight
    orchestration, and DB persistence paths.
    """
    if not isinstance(payload, dict):
        return {}

    existing_stats = payload.get("Stats")
    if isinstance(existing_stats, dict) and existing_stats:
        return existing_stats

    base_stats = payload.get("BaseStats")
    if not isinstance(base_stats, dict) or not base_stats:
        return {}

    gem_counts = payload.get("GemCounts")
    if not isinstance(gem_counts, dict):
        gem_counts = {}

    ft_val = _coerce_int(
        ft_override if ft_override is not None else payload.get("FT", gem_counts.get("Fever Time", 0)),
        0,
    )
    ff_val = _coerce_int(
        ff_override
        if ff_override is not None
        else payload.get("FF", gem_counts.get("Fever Fill", gem_counts.get("Fever Fill Rate", 0))),
        0,
    )
    g_pp = _coerce_int(gem_counts.get("Perfect Points", 0), 0)
    g_cm = _coerce_int(gem_counts.get("Combo Multiplier", 0), 0)
    g_fm = _coerce_int(gem_counts.get("Fever Multiplier", 0), 0)
    g_ov = _coerce_int(
        gem_counts.get("Element", gem_counts.get("Element Overflow", gem_counts.get("ElementOverflow", 0))),
        0,
    )
    selected = str(selected_element if selected_element is not None else get_selected_element(payload, "")).strip()
    computed = apply_gems_to_base_fast(base_stats, selected, ft_val, ff_val, g_pp, g_cm, g_fm, g_ov)

    if not (isinstance(computed, dict) and computed):
        return {}
    if mutate_payload:
        payload["Stats"] = dict(computed)
        return payload["Stats"]
    return dict(computed)


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
    sig_map: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]],
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
    fg_variants: list[dict[str, Any]] | None,
    build_details_fn: Callable[[dict[str, Any]], dict[str, Any]] | None,
    names_list_fn: Callable[[Any], list[str]],
    perf: bool,
    materialize_stats: bool = True,
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

        if result_cfg_counts is not None:
            # `result_cfg_counts` can be a numpy array; avoid ambiguous truthiness on ndarray rows.
            row = result_cfg_counts[idx]
            if row is None:
                cfg_counts = []
            else:
                try:
                    if int(n_sections) > 0:
                        cfg_counts = list(row[: int(n_sections)])
                    else:
                        cfg_counts = list(row)
                except Exception:
                    cfg_counts = []
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

        config_dict = _force_greats_counts_to_dict(forced_counts, max(2, len(forced_counts)))

        fg_info = {
            "enabled": True,
            "mode": "finder",
            "algo_version": int(FORCE_GREATS_ALGO_VERSION),
            # Keep search_radius optional; when absent, cache validation remains permissive.
            "config": config_dict,
            "final_score": final_score,
        }

        final_stats = {}
        if materialize_stats:
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

        # Lean-only: always store a compact raw payload for DB/UI consumers without
        # building heavyweight `details` dicts.
        raw_payload = {
            "BaseScore": base_score,
            "Score": final_score,
            "FT": ft_val,
            "FF": ff_val,
            "GemCounts": gem_counts,
            # Store base stats so downstream can materialize Stats if needed.
            "BaseStats": bs,
            "Selected Element": str(sel_color),
            "ForceGreats": fg_info,
            # Per-section forced counts (useful for tiering / recompute paths).
            "forced_counts": list(forced_counts) if forced_counts else [],
        }

        for entry, eval_data in sig_map.get(sig, []):
            if "base_score" not in entry:
                entry["base_score"] = entry.get("score")

            # Always store the numeric FG score for downstream ranking/retention.
            entry["fg_score"] = final_score

            # Store the raw payload directly under `force` (persisted to force_details_json).
            entry["force"] = raw_payload
            entry.pop("_fg_raw", None)

            if fg_variants is not None:
                # Keep FG variants for printing/debug without requiring materialized Stats.
                fg_variants.append(
                    {
                        "data": raw_payload,
                        "gear": entry.get("gear", []),
                        "minis": entry.get("minis", []),
                        "score": base_score,
                        "fg_score": final_score,
                        "base_score": base_score,
                    }
                )

            c_ft = int(eval_data.get("FT", 0) or 0)
            c_ff = int(eval_data.get("FF", 0) or 0)
            FG_CACHE[(sig, str(sel_color), c_ft, c_ff, int(n_sections), int(max_per_section))] = fg_variant

    return (time.perf_counter() - t0) if perf else 0.0
