from __future__ import annotations
import logging

from ....solver.scoring.force_greats import FORCE_GREATS_ALGO_VERSION
from ....core.utils import get_selected_element



logger = logging.getLogger(__name__)
def is_cached_force_valid_for_response_frontier(cached_force_obj, expected_selected_element) -> bool:
    if not isinstance(cached_force_obj, dict):
        return False
    fg_meta = (cached_force_obj.get("ForceGreats") or {}) if isinstance(cached_force_obj, dict) else {}
    if not isinstance(fg_meta, dict) or not fg_meta:
        return False
    if not fg_meta.get("config"):
        return False
    try:
        if fg_meta.get("mode") != "response_frontier":
            return False
        algo = fg_meta.get("algo_version")
        if algo is not None and int(algo) != int(FORCE_GREATS_ALGO_VERSION):
            return False
    except Exception as e:
        logger.debug(f"cache_validation:is_cached_force_valid_for_response_frontier: {e}")
        return False
    cached_sel = get_selected_element(cached_force_obj, "")
    if expected_selected_element and cached_sel and cached_sel != expected_selected_element:
        return False
    return True
