"""
Shared helpers for constructing base fixed stats vectors used by GPU paths.

These helpers centralize the "subtract user-fixed gems + static overflow gems"
logic so the GA, batch evaluators, and utilities stay consistent.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

from ..core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
)
from ..core.utils import safe_int


STAT_NAMES: tuple[str, ...] = (
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

COLOR_TO_STAT_INDEX: dict[str, int] = {"Beat": 5, "Vibe": 6, "Rush": 7, "Flow": 8, "Chill": 9}


def build_stats_list(stats: Mapping[str, Any] | None) -> list[int]:
    src = stats or {}
    return [safe_int(src.get(name, 0), 0) for name in STAT_NAMES]


def build_stats_array(stats: Mapping[str, Any] | None) -> np.ndarray:
    return np.asarray(build_stats_list(stats), dtype=np.int32)


def build_stats_dict(values: Any) -> dict[str, int]:
    out: dict[str, int] = {}
    for idx, name in enumerate(STAT_NAMES):
        try:
            out[name] = int(values[idx])
        except Exception:
            out[name] = 0
    return out


def build_base_fixed_stats_list(
    base_stats_fixed: Mapping[str, Any] | None,
    cfg_data: Mapping[str, Any] | None,
    *,
    fallback_selected_color: str | None = None,
) -> tuple[list[int], str]:
    bs = base_stats_fixed or {}
    cfg = cfg_data or {}

    base_fixed = build_stats_list(bs)

    user_pp = safe_int(cfg.get("user_pp", 0), 0)
    user_cm = safe_int(cfg.get("user_cm", 0), 0)
    user_fm = safe_int(cfg.get("user_fm", 0), 0)
    user_ft = safe_int(cfg.get("user_ft", 0), 0)
    user_ff = safe_int(cfg.get("user_ff", 0), 0)
    static_elem_input = safe_int(cfg.get("static_elem_input", 0), 0)
    selected_color = str(cfg.get("selected_color") or fallback_selected_color or "")

    if user_pp or user_cm or user_fm or user_ft or user_ff:
        base_fixed[0] -= user_pp * GEM_SCALE_NORMAL
        base_fixed[1] -= user_cm * GEM_SCALE_NORMAL
        base_fixed[2] -= user_fm * GEM_SCALE_FEVER
        base_fixed[3] -= user_ft * GEM_SCALE_FEVER
        base_fixed[4] -= user_ff * GEM_SCALE_FEVER

        base_fixed[9] -= user_pp * GEM_STAT_TO_ELEMENT_SCALE  # Chill
        base_fixed[8] -= user_cm * GEM_STAT_TO_ELEMENT_SCALE  # Flow
        base_fixed[7] -= user_fm * GEM_STAT_TO_ELEMENT_SCALE  # Rush
        base_fixed[5] -= user_ft * GEM_STAT_TO_ELEMENT_SCALE  # Beat
        base_fixed[6] -= user_ff * GEM_STAT_TO_ELEMENT_SCALE  # Vibe

    if static_elem_input and selected_color:
        idx = COLOR_TO_STAT_INDEX.get(selected_color)
        if idx is not None:
            base_fixed[idx] -= static_elem_input * ELEMENTAL_GEM_SCALE

    return base_fixed, selected_color


def build_base_fixed_stats_array(
    base_stats_fixed: Mapping[str, Any] | None,
    cfg_data: Mapping[str, Any] | None,
    *,
    fallback_selected_color: str | None = None,
) -> tuple[np.ndarray, str]:
    base_fixed, sel = build_base_fixed_stats_list(
        base_stats_fixed,
        cfg_data,
        fallback_selected_color=fallback_selected_color,
    )
    return np.asarray(base_fixed, dtype=np.int32), sel
