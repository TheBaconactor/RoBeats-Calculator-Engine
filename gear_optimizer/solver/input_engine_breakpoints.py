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
    lanes: Sequence[int] | np.ndarray | None = None,
    epsilon: float = INPUT_ORDER_EPS_SEC,
) -> float | None:
    """Latest activation hit that preserves scored labels of following same-lane notes.

    Later notes on other lanes cannot preempt the activation press in the input engine; they are
    independently schedulable and belong to the reachability owner. A later note in the activation
    lane does cap the witness, because the unhit activation note would block that lane's chart-order
    matching after the later note's scored label window has closed.
    """
    a = int(activation_index)
    ts = np.asarray(chart_timestamps, dtype=np.float64).reshape(-1)
    highs = np.asarray(label_high_timestamps, dtype=np.float64).reshape(-1)
    lane_arr = None if lanes is None else np.asarray(lanes, dtype=np.int32).reshape(-1)
    n = min(int(section_end), int(ts.shape[0]), int(highs.shape[0]))
    if lane_arr is not None:
        n = min(n, int(lane_arr.shape[0]))
    if not (0 <= a < n):
        raise ValueError("activation_index must be inside the section")

    lo = float(hit_lo)
    cap = float(hit_hi)
    if lo > cap:
        return None

    activation_lane = None if lane_arr is None else int(lane_arr[a])
    eps = max(0.0, float(epsilon))
    for j in range(a + 1, n):
        if float(ts[j]) >= cap:
            break
        if activation_lane is not None and int(lane_arr[j]) != activation_lane:
            continue
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
    lanes: Sequence[int] | np.ndarray | None = None,
    epsilon: float = INPUT_ORDER_EPS_SEC,
) -> float | None:
    """Latest activation hit when scored Greats form one contiguous run."""
    a = int(activation_index)
    ts = np.asarray(chart_timestamps, dtype=np.float64).reshape(-1)
    perfect_hi = np.asarray(perfect_high_timestamps, dtype=np.float64).reshape(-1)
    great_hi = np.asarray(great_high_timestamps, dtype=np.float64).reshape(-1)
    lane_arr = None if lanes is None else np.asarray(lanes, dtype=np.int32).reshape(-1)
    n = min(int(section_end), int(ts.shape[0]), int(perfect_hi.shape[0]), int(great_hi.shape[0]))
    if lane_arr is not None:
        n = min(n, int(lane_arr.shape[0]))
    if not (0 <= a < n):
        raise ValueError("activation_index must be inside the section")

    lo = float(hit_lo)
    cap = float(hit_hi)
    if lo > cap:
        return None

    activation_lane = None if lane_arr is None else int(lane_arr[a])
    great_lo = max(0, min(int(great_start), n))
    great_end = min(n, great_lo + max(0, int(great_count)))
    eps = max(0.0, float(epsilon))
    for j in range(a + 1, n):
        if float(ts[j]) >= cap:
            break
        if activation_lane is not None and int(lane_arr[j]) != activation_lane:
            continue
        label_hi = float(great_hi[j]) if great_lo <= j < great_end else float(perfect_hi[j])
        cap = min(float(cap), label_hi - eps)
        if cap < lo:
            return None
    return float(cap)
