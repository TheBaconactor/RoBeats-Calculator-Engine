from __future__ import annotations

import time
from typing import Any
import logging

from ....core.constants import GEM_SCALE_FEVER
from ....core.utils import get_selected_element
from ....solver.scoring import _force_greats_counts_to_dict
from ....solver.scoring.force_greats import FORCE_GREATS_ALGO_VERSION
from ....solver.scoring.stats_ops import apply_gems_to_base_stats



logger = logging.getLogger(__name__)
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
    except Exception as e:
        logger.debug(f"result_application:_coerce_int: {e}")
        try:
            return int(float(value))
        except Exception as e:
            logger.debug(f"result_application:_coerce_int: {e}")
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
    rep_flags: list[Any] | None,
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

    rep_flags_list = list(rep_flags or [])
    forced_counts: list[int] = []
    for idx, fp in enumerate(fp_counts):
        fp_i = int(fp)
        forced = _min_forced_for_fp(fp_i)
        # Plateau-aware representative:
        # If requested and valid, move from minimal-k to k+1 on the same FP plateau.
        rep_flag = 0
        try:
            if idx < len(rep_flags_list):
                rep_flag = 1 if int(rep_flags_list[idx] or 0) > 0 else 0
        except Exception as e:
            logger.debug(f"result_application:_min_forced_for_fp: {e}")
            rep_flag = 0
        if rep_flag:
            alt = int(forced + 1)
            if alt <= int(non_fever_base):
                fp_alt = int(math.ceil(raw_fever_fill + (float(alt) * 0.5)) - base_ceil)
                if fp_alt == fp_i:
                    forced = alt
        if forced > non_fever_base:
            forced = non_fever_base
        forced_counts.append(int(forced))
    return forced_counts


def _build_raw_gpu_result(
    *,
    base_stats: dict[str, Any],
    sel_color: str,
    n_sections: int,
    max_per_section: int,
    counts_list: Any,
    fg_scorer: Any,
    final_score: Any,
    base_score: Any,
    cfg_idx: Any,
    cfg_counts_row: Any,
    ft: Any,
    ff: Any,
    g_pp: Any,
    g_cm: Any,
    g_fm: Any,
    g_ov: Any,
    materialize_stats: bool = True,
) -> tuple[int, int, dict[str, Any]]:
    final_score_i = int(final_score)
    base_score_i = int(base_score)
    ft_val = int(ft)
    ff_val = int(ff)
    g_pp_i = int(g_pp)
    g_cm_i = int(g_cm)
    g_fm_i = int(g_fm)
    g_ov_i = int(g_ov)

    if cfg_counts_row is not None:
        row = cfg_counts_row
        try:
            if int(n_sections) > 0:
                cfg_counts = list(row[: int(n_sections)])
            else:
                cfg_counts = list(row)
        except Exception as e:
            logger.debug(f"result_application:_build_raw_gpu_result: {e}")
            cfg_counts = []
    else:
        cfg_idx_i = int(cfg_idx) if cfg_idx is not None else -1
        cfg_counts = list(counts_list[cfg_idx_i]) if 0 <= cfg_idx_i < len(counts_list) else []

    forced_counts: list[int] = []
    for raw_val in list(cfg_counts or []):
        try:
            raw_i = int(raw_val)
        except Exception as e:
            logger.debug(f"result_application:_build_raw_gpu_result: {e}")
            raw_i = 0
        if raw_i < 0:
            raw_i = 0
        forced_counts.append(int(raw_i))

    gem_counts = {
        "Perfect Points": g_pp_i,
        "Combo Multiplier": g_cm_i,
        "Fever Multiplier": g_fm_i,
        "Element": g_ov_i,
    }

    config_dict = _force_greats_counts_to_dict(forced_counts, max(2, int(len(forced_counts))))

    fg_info = {
        "enabled": True,
        "mode": "finder",
        "algo_version": int(FORCE_GREATS_ALGO_VERSION),
        "config": config_dict,
        "final_score": final_score_i,
    }

    raw_payload = {
        "BaseScore": base_score_i,
        "Score": final_score_i,
        "FT": ft_val,
        "FF": ff_val,
        "GemCounts": gem_counts,
        "BaseStats": base_stats,
        "Selected Element": str(sel_color),
        "ForceGreats": fg_info,
        "forced_counts": list(forced_counts) if forced_counts else [],
    }

    if materialize_stats:
        final_stats = apply_gems_to_base_fast(
            base_stats,
            str(sel_color),
            ft_val,
            ff_val,
            g_pp_i,
            g_cm_i,
            g_fm_i,
            g_ov_i,
        )
        if isinstance(final_stats, dict) and final_stats:
            raw_payload["Stats"] = final_stats

    return final_score_i, base_score_i, raw_payload


def collect_gpu_results_by_signature(
    *,
    pending_sigs: list[str],
    pending: list[dict[str, Any]],
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
    perf: bool,
    materialize_stats: bool = True,
) -> tuple[dict[str, dict[str, Any]], float]:
    t0 = time.perf_counter() if perf else 0.0
    sig_results: dict[str, dict[str, Any]] = {}
    for idx, (sig, bs) in enumerate(zip(pending_sigs, pending)):
        final_score_i, base_score_i, raw_payload = _build_raw_gpu_result(
            base_stats=bs,
            sel_color=str(sel_color),
            n_sections=int(n_sections),
            max_per_section=int(max_per_section),
            counts_list=counts_list,
            fg_scorer=fg_scorer,
            final_score=result_final[idx],
            base_score=result_base[idx],
            cfg_idx=result_cfg_idx[idx] if result_cfg_idx is not None else None,
            cfg_counts_row=result_cfg_counts[idx] if result_cfg_counts is not None else None,
            ft=result_ft[idx],
            ff=result_ff[idx],
            g_pp=result_g_pp[idx],
            g_cm=result_g_cm[idx],
            g_fm=result_g_fm[idx],
            g_ov=result_g_ov[idx],
            materialize_stats=materialize_stats,
        )
        sig_results[str(sig)] = {
            "fg_score": int(final_score_i),
            "base_score": int(base_score_i),
            "force": raw_payload,
        }
    return sig_results, ((time.perf_counter() - t0) if perf else 0.0)


def apply_signature_result_to_entry(*, entry: dict[str, Any], sig_result: dict[str, Any]) -> None:
    if not isinstance(entry, dict) or not isinstance(sig_result, dict):
        return

    if "base_score" not in entry:
        entry["base_score"] = entry.get("score")

    try:
        entry["fg_score"] = int(sig_result.get("fg_score", 0) or 0)
    except Exception as e:
        logger.debug(f"result_application:apply_signature_result_to_entry: {e}")
        entry["fg_score"] = 0

    force_obj = sig_result.get("force")
    if isinstance(force_obj, dict):
        materialize_stats_from_payload(force_obj, mutate_payload=True)
        entry["force"] = force_obj
    entry.pop("_fg_raw", None)

    candidate_ref = entry.get("_candidate_ref")
    if isinstance(candidate_ref, dict):
        candidate_ref["fg_score"] = int(entry.get("fg_score", 0) or 0)
        if isinstance(force_obj, dict):
            candidate_ref["force"] = force_obj
        candidate_ref["_entry_ref"] = entry


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
    perf: bool,
    materialize_stats: bool = True,
) -> float:
    sig_results, elapsed = collect_gpu_results_by_signature(
        pending_sigs=pending_sigs,
        pending=pending,
        sel_color=sel_color,
        n_sections=n_sections,
        max_per_section=max_per_section,
        counts_list=counts_list,
        fg_scorer=fg_scorer,
        result_final=result_final,
        result_base=result_base,
        result_cfg_idx=result_cfg_idx,
        result_cfg_counts=result_cfg_counts,
        result_ft=result_ft,
        result_ff=result_ff,
        result_g_pp=result_g_pp,
        result_g_cm=result_g_cm,
        result_g_fm=result_g_fm,
        result_g_ov=result_g_ov,
        perf=perf,
        materialize_stats=materialize_stats,
    )
    for sig, _bs in zip(pending_sigs, pending):
        sig_result = sig_results.get(str(sig))
        if not isinstance(sig_result, dict):
            continue
        for entry, _eval_data in sig_map.get(sig, []):
            apply_signature_result_to_entry(entry=entry, sig_result=sig_result)
    return elapsed
