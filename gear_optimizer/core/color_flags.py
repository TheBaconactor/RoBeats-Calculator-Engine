"""
Color flag helpers for scoring/gem allocation.

These flags are used by both CPU and GPU paths to determine which elemental lanes
receive stat-gem contributions and which lanes receive overflow gems.
"""

from __future__ import annotations


def build_color_flags(p_color: str | None, s_color: str | None, selected_color: str | None) -> dict[str, int]:
    p = str(p_color or "")
    s = str(s_color or "")
    sel = str(selected_color or "")

    return {
        "is_p_ft": 1 if p == "Beat" else 0,
        "is_s_ft": 1 if s == "Beat" else 0,
        "is_p_ff": 1 if p == "Vibe" else 0,
        "is_s_ff": 1 if s == "Vibe" else 0,
        "is_p_pp": 1 if p == "Chill" else 0,
        "is_s_pp": 1 if s == "Chill" else 0,
        "is_p_cm": 1 if p == "Flow" else 0,
        "is_s_cm": 1 if s == "Flow" else 0,
        "is_p_fm": 1 if p == "Rush" else 0,
        "is_s_fm": 1 if s == "Rush" else 0,
        "is_p_ov": 1 if sel and sel == p else 0,
        "is_s_ov": 1 if sel and sel == s else 0,
    }
