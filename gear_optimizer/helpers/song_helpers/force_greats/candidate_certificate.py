from __future__ import annotations

from typing import Any

import numpy as np

from gear_optimizer.core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_STAT_TO_ELEMENT_SCALE,
    TOTAL_GEM_BUDGET,
    TOTAL_ROWS,
)
from gear_optimizer.solver.scoring.fg_policy import extract_fg_song_inputs

_ELEMENT_COLORS = frozenset(("Chill", "Flow", "Rush", "Beat", "Vibe"))


def _max_reference_value(ref_arrays: dict[str, Any], key: str) -> np.float32:
    arr = np.asarray(ref_arrays[key], dtype=np.float32).reshape(-1)
    if int(arr.shape[0]) <= 0:
        raise ValueError(f"FG candidate certificate requires non-empty {key!r} reference array")
    return np.float32(np.max(arr[: min(int(arr.shape[0]), int(TOTAL_ROWS) + 1)]))


def _max_element_delta_per_gem(color: str, *, selected_color: str) -> int:
    color = str(color or "")
    if not color:
        return 0
    delta = GEM_STAT_TO_ELEMENT_SCALE if color in _ELEMENT_COLORS else 0
    if color == str(selected_color or ""):
        delta = max(int(delta), int(ELEMENTAL_GEM_SCALE))
    return int(delta)


def certified_fg_candidate_upper_bound(
    base_stats: dict[str, Any],
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    *,
    selected_color: str,
    total_budget: int = TOTAL_GEM_BUDGET,
) -> int:
    """
    Admissible per-candidate upper bound for exact FG.

    This intentionally relaxes multiple constraints at once:
    - every note may score as fever/perfect,
    - no forced-Great penalty is charged,
    - each score-driving stat may independently receive the full gem budget.

    The bound is therefore not a candidate score. It is only a certificate for
    safe removal when `upper_bound <= known_feasible_lower_bound`.
    """
    if not isinstance(base_stats, dict) or not base_stats:
        raise ValueError("FG candidate certificate requires base stats")
    if not isinstance(calc_song, dict) or not calc_song:
        raise ValueError("FG candidate certificate requires calc_song")
    if not isinstance(ref_arrays, dict) or not ref_arrays:
        raise ValueError("FG candidate certificate requires reference arrays")

    song_inputs = extract_fg_song_inputs(calc_song)
    total_notes = max(0, int(song_inputs.total_notes))
    head_len = min(int(total_notes), 100)
    body_total = max(0, int(total_notes) - 100)

    primary_color = str(song_inputs.primary_color or "")
    secondary_color = str(song_inputs.secondary_color or "")
    budget = max(0, int(total_budget))

    primary_upper = int(base_stats.get(primary_color, 0) or 0)
    if primary_color:
        primary_upper += budget * _max_element_delta_per_gem(primary_color, selected_color=selected_color)
    secondary_upper = int(base_stats.get(secondary_color, 0) or 0)
    if secondary_color:
        secondary_upper += budget * _max_element_delta_per_gem(secondary_color, selected_color=selected_color)

    pp_factor = _max_reference_value(ref_arrays, "Perfect Points")
    combo_mul = _max_reference_value(ref_arrays, "Combo Multiplier")
    fever_mul = _max_reference_value(ref_arrays, "Fever Multiplier")

    base_value = float((int(primary_upper) * 2) + int(secondary_upper)) + float(pp_factor)
    base_f = np.float32(base_value)
    combo_f = np.float32(combo_mul)
    fever_f = np.float32(fever_mul)

    normal_body = int(base_f * combo_f)
    fever_body = int(base_f * combo_f * fever_f)
    score = int(body_total) * max(int(normal_body), int(fever_body))

    combo_span = np.float32(combo_f - np.float32(1.0))
    factor = np.float32(combo_span * base_f / np.float32(100.0))
    for i in range(int(head_len)):
        ramp = np.float32(base_f + (np.float32(i + 1) * factor))
        normal = int(ramp)
        fever = int(ramp * fever_f)
        score += max(int(normal), int(fever))
    return int(score)
