"""
Shared stat/gem operations for scoring paths.

Keep these helpers pure and lightweight; they are used by both CPU and GPU code paths.
"""

from __future__ import annotations

from typing import Any

from ...core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
)


def apply_gems_to_base_stats(
    base: dict[str, Any],
    sel_color: str,
    ft: int,
    ff: int,
    g_pp: int,
    g_cm: int,
    g_fm: int,
    g_ov: int,
    *,
    add_missing_element_key: bool = True,
) -> dict[str, Any]:
    """
    Recompose final stats from base stats and solved gem counts.

    This is the canonical pure helper for rebuilding `Stats` payloads after gem decisions.
    Keep this function side-effect free so persistence and scoring paths can share it.

    Args:
        base: Base stats before gem allocation.
        sel_color: Selected elemental color receiving overflow gems.
        ft: Fever Time gem count.
        ff: Fever Fill Rate gem count.
        g_pp: Perfect Points gem count.
        g_cm: Combo Multiplier gem count.
        g_fm: Fever Multiplier gem count.
        g_ov: Elemental overflow gem count.
        add_missing_element_key: If True, create `sel_color` key when missing.

    Returns:
        A new stats dictionary with gem effects applied.
    """
    out = dict(base or {})
    out["Perfect Points"] = out.get("Perfect Points", 0) + int(g_pp) * GEM_SCALE_NORMAL
    out["Combo Multiplier"] = out.get("Combo Multiplier", 0) + int(g_cm) * GEM_SCALE_NORMAL
    out["Fever Multiplier"] = out.get("Fever Multiplier", 0) + int(g_fm) * GEM_SCALE_FEVER
    out["Fever Time"] = out.get("Fever Time", 0) + int(ft) * GEM_SCALE_FEVER
    out["Fever Fill Rate"] = out.get("Fever Fill Rate", 0) + int(ff) * GEM_SCALE_FEVER

    out["Chill"] = out.get("Chill", 0) + int(g_pp) * GEM_STAT_TO_ELEMENT_SCALE
    out["Flow"] = out.get("Flow", 0) + int(g_cm) * GEM_STAT_TO_ELEMENT_SCALE
    out["Rush"] = out.get("Rush", 0) + int(g_fm) * GEM_STAT_TO_ELEMENT_SCALE
    out["Beat"] = out.get("Beat", 0) + int(ft) * GEM_STAT_TO_ELEMENT_SCALE
    out["Vibe"] = out.get("Vibe", 0) + int(ff) * GEM_STAT_TO_ELEMENT_SCALE

    if sel_color:
        if add_missing_element_key or sel_color in out:
            out[sel_color] = out.get(sel_color, 0) + int(g_ov) * ELEMENTAL_GEM_SCALE
    return out
