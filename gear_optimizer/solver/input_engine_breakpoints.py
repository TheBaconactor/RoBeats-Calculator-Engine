from __future__ import annotations

from typing import Sequence

import numpy as np

INPUT_ORDER_EPS_SEC = 1.0e-6


def latest_activation_hit_from_label_highs(
    *,
    activation_index: int,
    hit_lo: float,
    hit_hi: float,
    chart_timestamps: Sequence[float] | np.ndarray,
    label_high_timestamps: Sequence[float] | np.ndarray,
    section_end: int,
    epsilon: float = INPUT_ORDER_EPS_SEC,
) -> float | None:
    """Latest activation hit that preserves the scored labels of following notes.

    The activation cannot be after a later note's latest legal hit unless that later note's
    scored label has also been widened to make that order legal. ``label_high_timestamps`` is
    therefore the owner-provided upper edge for each note's current scored label: Perfect upper
    for Perfect notes, Great upper for intentionally-forced Great notes.
    """
    a = int(activation_index)
    ts = np.asarray(chart_timestamps, dtype=np.float64).reshape(-1)
    highs = np.asarray(label_high_timestamps, dtype=np.float64).reshape(-1)
    n = min(int(section_end), int(ts.shape[0]), int(highs.shape[0]))
    if not (0 <= a < n):
        raise ValueError("activation_index must be inside the section")

    lo = float(hit_lo)
    cap = float(hit_hi)
    if lo > cap:
        return None

    eps = max(0.0, float(epsilon))
    for j in range(a + 1, n):
        if float(ts[j]) >= cap:
            break
        cap = min(float(cap), float(highs[j]) - eps)
        if cap < lo:
            return None
    return float(cap)


def latest_activation_hit_for_contiguous_great_run(
    *,
    activation_index: int,
    hit_lo: float,
    hit_hi: float,
    chart_timestamps: Sequence[float] | np.ndarray,
    perfect_high_timestamps: Sequence[float] | np.ndarray,
    great_high_timestamps: Sequence[float] | np.ndarray,
    great_start: int,
    great_count: int,
    section_end: int,
    epsilon: float = INPUT_ORDER_EPS_SEC,
) -> float | None:
    """Latest activation hit when scored Greats form one contiguous run."""
    a = int(activation_index)
    ts = np.asarray(chart_timestamps, dtype=np.float64).reshape(-1)
    perfect_hi = np.asarray(perfect_high_timestamps, dtype=np.float64).reshape(-1)
    great_hi = np.asarray(great_high_timestamps, dtype=np.float64).reshape(-1)
    n = min(int(section_end), int(ts.shape[0]), int(perfect_hi.shape[0]), int(great_hi.shape[0]))
    if not (0 <= a < n):
        raise ValueError("activation_index must be inside the section")

    lo = float(hit_lo)
    cap = float(hit_hi)
    if lo > cap:
        return None

    great_lo = max(0, min(int(great_start), n))
    great_end = min(n, great_lo + max(0, int(great_count)))
    eps = max(0.0, float(epsilon))
    for j in range(a + 1, n):
        if float(ts[j]) >= cap:
            break
        label_hi = float(great_hi[j]) if great_lo <= j < great_end else float(perfect_hi[j])
        cap = min(float(cap), label_hi - eps)
        if cap < lo:
            return None
    return float(cap)
