from __future__ import annotations

from typing import Any
import logging

from ....core.utils import get_selected_element, stats_signature
from ....core.utils import safe_int
from ....solver.scoring.stats_scoring import fg_baseline_params



logger = logging.getLogger(__name__)
def expected_selected_element(entry: dict[str, Any], meta_primary_color: str) -> str:
    """
    Best-effort "selected element" for cache validation.

    Preference order:
    1) `entry["selected_element"]` (fast path; produced by lean GA candidate plumbing)
    2) `entry["details"]` Selected Element/SelectedElement (DB-cached payloads)
    3) `meta_primary_color` fallback
    """
    try:
        v = entry.get("selected_element")
        if v:
            return str(v)
    except Exception as e:
        logger.debug(f"entry_utils:expected_selected_element: {e}")
    try:
        det0 = entry.get("details") or {}
        return get_selected_element(det0, meta_primary_color)
    except Exception as e:
        logger.debug(f"entry_utils:expected_selected_element: {e}")
        return str(meta_primary_color or "")

def fg_proxy_from_base_stats(stats: dict[str, Any] | None, primary_color: str, secondary_color: str) -> int:
    score = 0
    score += safe_int((stats or {}).get("Fever Multiplier", 0), 0) * 4
    score += safe_int((stats or {}).get("Fever Fill Rate", 0), 0) * 4
    score += safe_int((stats or {}).get("Fever Time", 0), 0) * 3
    score += safe_int((stats or {}).get("Combo Multiplier", 0), 0) * 2
    score += safe_int((stats or {}).get("Perfect Points", 0), 0)
    if primary_color:
        score += safe_int((stats or {}).get(primary_color, 0), 0) * 2
    if secondary_color and secondary_color != primary_color:
        score += safe_int((stats or {}).get(secondary_color, 0), 0)
    return int(score)


def _normalize_fg_group_key(value: Any) -> tuple[str, int, int] | None:
    if isinstance(value, tuple):
        parts = value
    elif isinstance(value, list):
        parts = tuple(value)
    else:
        return None
    if len(parts) != 3:
        return None
    try:
        return (
            str(parts[0] or ""),
            int(parts[1]),
            int(parts[2]),
        )
    except Exception as e:
        logger.debug(f"entry_utils:_normalize_fg_group_key: {e}")
        return None


def _cached_fg_group_meta_is_reusable(meta: dict[str, Any] | None) -> bool:
    if not isinstance(meta, dict):
        return False
    if bool(meta.get("skip")):
        return True
    group_key = _normalize_fg_group_key(meta.get("group_key"))
    if group_key is None:
        return False
    try:
        if int(meta.get("n_sections", 0) or 0) <= 0:
            return False
    except Exception as e:
        logger.debug(f"entry_utils:_cached_fg_group_meta_is_reusable: {e}")
        return False
    try:
        if int(meta.get("max_per_section", 0) or 0) < 0:
            return False
    except Exception as e:
        logger.debug(f"entry_utils:_cached_fg_group_meta_is_reusable: {e}")
        return False
    signature = meta.get("signature")
    return signature is not None


def build_fg_group_meta(
    *,
    base_stats: dict[str, Any] | None,
    calc_song: dict[str, Any] | None,
    ref_arrays: dict[str, Any] | None,
    selected_element: str,
    center_ft: int,
    center_ff: int,
    primary_color: str = "",
    secondary_color: str = "",
    run_idx: int | None = None,
    row_idx: int | None = None,
    prefer_grid: bool | None = None,
) -> dict[str, Any] | None:
    if not isinstance(base_stats, dict) or not base_stats:
        return None
    if not isinstance(calc_song, dict) or not calc_song:
        return None

    sel_color = str(selected_element or "")
    meta: dict[str, Any] = {
        "selected_element": sel_color,
        "center_ft": int(center_ft),
        "center_ff": int(center_ff),
    }
    if run_idx is not None:
        meta["ga_run_idx"] = int(run_idx)
    if row_idx is not None:
        meta["ga_row_idx"] = int(row_idx)

    try:
        n_sections, non_fever_base = fg_baseline_params(
            base_stats,
            calc_song,
            ref_arrays or {},
            prefer_grid=prefer_grid,
        )
        if int(n_sections) <= 0:
            meta["skip"] = True
            return meta

        max_per_section = max(0, int(non_fever_base or 0))
        meta["skip"] = False
        meta["n_sections"] = int(n_sections)
        meta["max_per_section"] = int(max_per_section)
        meta["group_key"] = (sel_color, int(n_sections), int(max_per_section))
        meta["signature"] = stats_signature(base_stats, calc_song, sel_color)
        meta["fg_proxy_score"] = fg_proxy_from_base_stats(
            base_stats,
            str(primary_color or ""),
            str(secondary_color or ""),
        )
        return meta
    except Exception as e:
        logger.debug(f"entry_utils:build_fg_group_meta: {e}")
        return None


def fg_group_meta_from_eval_data(
    eval_data: dict[str, Any] | None,
    *,
    calc_song: dict[str, Any] | None,
    ref_arrays: dict[str, Any] | None,
    meta_primary_color: str = "",
    primary_color: str = "",
    secondary_color: str = "",
    base_stats: dict[str, Any] | None = None,
    prefer_grid: bool | None = None,
) -> dict[str, Any] | None:
    if not isinstance(eval_data, dict):
        return None

    cached = eval_data.get("_fg_group_meta")
    if _cached_fg_group_meta_is_reusable(cached):
        return cached

    base_stats_obj = base_stats if isinstance(base_stats, dict) else eval_data.get("BaseStats")
    if not isinstance(base_stats_obj, dict) or not base_stats_obj:
        return None

    meta = build_fg_group_meta(
        base_stats=base_stats_obj,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_element=get_selected_element(eval_data, meta_primary_color),
        center_ft=int(eval_data.get("FT", 0) or 0),
        center_ff=int(eval_data.get("FF", 0) or 0),
        primary_color=primary_color,
        secondary_color=secondary_color,
        run_idx=eval_data.get("_ga_gpu_run_idx"),
        row_idx=eval_data.get("_ga_gpu_row_idx"),
        prefer_grid=prefer_grid,
    )
    if isinstance(meta, dict):
        eval_data["_fg_group_meta"] = meta
    return meta


def eval_data_from_entry(entry: dict[str, Any], meta_primary_color: str) -> dict[str, Any] | None:
    """
    Extract a minimal eval payload for ForceGreats.

    Returns a dict with keys:
      - Stats
      - Selected Element
      - FT / FF
      - GemCounts
      - optional BaseStats (when upstream provides it, e.g. GPU-native GA)
    """
    try:
        eval_data = entry.get("eval_data")
    except Exception as e:
        logger.debug(f"entry_utils:eval_data_from_entry: {e}")
        eval_data = None
    if isinstance(eval_data, dict):
        # Prefer full Stats when present (most complete signal).
        stats = eval_data.get("Stats")
        if isinstance(stats, dict) and stats:
            return eval_data
        # GPU-native GA can provide BaseStats without full Stats; that's sufficient for
        # ForceGreatsFinder batching and signature grouping.
        base_stats = eval_data.get("BaseStats")
        if isinstance(base_stats, dict) and base_stats:
            return eval_data

    try:
        det = entry.get("details") or {}
        stats = det.get("Stats") or {}
        if not isinstance(stats, dict) or not stats:
            return None
        return {
            "Stats": stats,
            "Selected Element": get_selected_element(det, meta_primary_color),
            "FT": det.get("FT", 0),
            "FF": det.get("FF", 0),
            "GemCounts": det.get("GemCounts", {}),
        }
    except Exception as e:
        logger.debug(f"entry_utils:eval_data_from_entry: {e}")
        return None
