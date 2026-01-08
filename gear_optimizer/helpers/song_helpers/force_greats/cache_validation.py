from __future__ import annotations

import os

from ....solver.scoring.force_greats import FORCE_GREATS_ALGO_VERSION


def is_cached_force_valid_for_finder(cached_force_obj, expected_selected_element, center_ft, center_ff) -> bool:
    if not isinstance(cached_force_obj, dict):
        return False
    details = cached_force_obj.get("details") or {}
    if not isinstance(details, dict):
        return False
    fg_meta = details.get("ForceGreats") or {}
    if not isinstance(fg_meta, dict) or not fg_meta:
        return False
    if not fg_meta.get("config"):
        return False
    try:
        if fg_meta.get("mode") not in (None, "", "finder"):
            return False
        algo = fg_meta.get("algo_version")
        if algo is not None and int(algo) != int(FORCE_GREATS_ALGO_VERSION):
            return False
        sr = fg_meta.get("search_radius")
        if sr is not None and int(sr) != int(os.environ.get("FG_SEARCH_RADIUS", "5")):
            return False
    except Exception:
        return False
    cached_sel = details.get("SelectedElement") or details.get("Selected Element") or ""
    if expected_selected_element and cached_sel and cached_sel != expected_selected_element:
        return False
    return True


def is_cached_force_valid(cached_force_obj, expected_selected_element) -> bool:
    """
    Validate that a DB-cached ForceGreats payload is compatible with the current code/config.
    This prevents stale FG results (from older algorithms or wrong overflow target) from
    presenting as score inflation.
    """
    if not isinstance(cached_force_obj, dict):
        return False
    details = cached_force_obj.get("details") or {}
    if not isinstance(details, dict):
        return False
    fg_meta = details.get("ForceGreats") or {}
    if not isinstance(fg_meta, dict) or not fg_meta:
        return False
    if not fg_meta.get("config"):
        return False
    cached_sel = details.get("SelectedElement") or details.get("Selected Element") or ""
    if expected_selected_element and cached_sel and cached_sel != expected_selected_element:
        return False
    return True
