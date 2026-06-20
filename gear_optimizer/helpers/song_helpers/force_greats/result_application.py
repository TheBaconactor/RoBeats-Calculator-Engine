from __future__ import annotations

import logging
from typing import Any

from ....core.gem_defs import element_gem_count
from ....core.utils import get_selected_element, safe_int
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

    ft_val = safe_int(
        ft_override if ft_override is not None else payload.get("FT", gem_counts.get("Fever Time", 0)),
        0,
    )
    ff_val = safe_int(
        ff_override
        if ff_override is not None
        else payload.get("FF", gem_counts.get("Fever Fill", gem_counts.get("Fever Fill Rate", 0))),
        0,
    )
    g_pp = safe_int(gem_counts.get("Perfect Points", 0), 0)
    g_cm = safe_int(gem_counts.get("Combo Multiplier", 0), 0)
    g_fm = safe_int(gem_counts.get("Fever Multiplier", 0), 0)
    g_ov = element_gem_count(gem_counts)
    selected = str(selected_element if selected_element is not None else get_selected_element(payload, "")).strip()
    computed = apply_gems_to_base_fast(base_stats, selected, ft_val, ff_val, g_pp, g_cm, g_fm, g_ov)

    if not (isinstance(computed, dict) and computed):
        return {}
    if mutate_payload:
        payload["Stats"] = dict(computed)
        return payload["Stats"]
    return dict(computed)
