from __future__ import annotations

import logging
from typing import Any

from gear_optimizer.core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
)


logger = logging.getLogger(__name__)
STAT_KEYS = (
    "Perfect Points",
    "Combo Multiplier",
    "Fever Multiplier",
    "Fever Time",
    "Fever Fill Rate",
    "Beat",
    "Vibe",
    "Rush",
    "Flow",
    "Chill",
)


def extract_base_stats(
    stats: dict[str, Any],
    gem_counts: dict[str, Any] | None,
    selected_color: str,
    ft_gems: int = 0,
    ff_gems: int = 0,
) -> dict[str, Any]:
    if not isinstance(stats, dict) or not stats:
        return {}

    gs = stats.get
    base = {key: gs(key, 0) for key in STAT_KEYS}
    if not gem_counts:
        return base

    try:
        g_pp = int(gem_counts.get("Perfect Points", 0) or 0)
        g_cm = int(gem_counts.get("Combo Multiplier", 0) or 0)
        g_fm = int(gem_counts.get("Fever Multiplier", 0) or 0)
        g_ov = int(gem_counts.get("Element", 0) or 0)
        deltas = {
            "Perfect Points": g_pp * int(GEM_SCALE_NORMAL),
            "Chill": g_pp * int(GEM_STAT_TO_ELEMENT_SCALE),
            "Combo Multiplier": g_cm * int(GEM_SCALE_NORMAL),
            "Flow": g_cm * int(GEM_STAT_TO_ELEMENT_SCALE),
            "Fever Multiplier": g_fm * int(GEM_SCALE_FEVER),
            "Rush": g_fm * int(GEM_STAT_TO_ELEMENT_SCALE),
            "Fever Time": int(ft_gems) * int(GEM_SCALE_FEVER),
            "Beat": int(ft_gems) * int(GEM_STAT_TO_ELEMENT_SCALE),
            "Fever Fill Rate": int(ff_gems) * int(GEM_SCALE_FEVER),
            "Vibe": int(ff_gems) * int(GEM_STAT_TO_ELEMENT_SCALE),
        }
        if selected_color:
            selected = str(selected_color)
            deltas[selected] = deltas.get(selected, 0) + g_ov * int(ELEMENTAL_GEM_SCALE)

        for key, delta in deltas.items():
            if int(delta) > 0 and int(gs(key, 0)) - int(delta) < -50:
                raise ValueError(
                    "Cannot losslessly extract base stats: "
                    f"{key!r} stat {int(gs(key, 0))} is smaller than applied gem delta {int(delta)}."
                )
    except (TypeError, ValueError) as exc:
        logger.debug("force_greats_common:extract_base_stats: %s", exc)
        raise

    for key, delta in deltas.items():
        base[key] = base.get(key, 0) - delta
    return base
