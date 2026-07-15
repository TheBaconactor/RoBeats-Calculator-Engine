from __future__ import annotations

from typing import Any
import logging

from ....core.utils import get_selected_element



logger = logging.getLogger(__name__)
def expected_selected_element(entry: dict[str, Any], meta_primary_color: str) -> str:
    """
    Best-effort "selected element" for cache validation.

    Preference order:
    1) `entry["selected_element"]` (fast path from exact Base candidate plumbing)
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

def eval_data_from_entry(entry: dict[str, Any], meta_primary_color: str) -> dict[str, Any] | None:
    """
    Extract a minimal eval payload for ForceGreats.

    Returns a dict with keys:
      - Stats
      - Selected Element
      - FT / FF
      - GemCounts
      - optional BaseStats (when upstream exact Base decode provides it)
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
        # Exact Base decode can provide BaseStats without full Stats. Response-frontier
        # FG batching uses BaseStats when full Stats are absent.
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
