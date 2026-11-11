"""The FG frontier kernel's inputs for one ``(raw_fever_fill, non_fever_base, real_fever_time)`` geometry,
built with the production prep functions (compact action table, fever-end tables)."""

from __future__ import annotations

from typing import Any

import numpy as np

from gear_optimizer.solver.timing_envelope import precise_envelopes
from gear_optimizer.frontier.producer_batch import compact_action_table, song_arrays
from gear_optimizer.frontier.producer_precompute import fever_ends
from gear_optimizer.frontier.producer_kernels import (
    _numba_build_prefix_activation_hit_tables,
)


def build_kernel_args(
    *,
    timestamps: Any,
    perfect_candidate_timestamps: Any | None = None,
    great_candidate_timestamps: Any | None = None,
    lanes: Any | None = None,
    raw_fever_fill: float,
    non_fever_base: int,
    real_fever_time: float,
    use_forced_great_timing: bool = True,
) -> dict[str, Any]:
    """Return the full argument bundle for the frontier kernel.

    Reuses the production compact action table and fever-end tables so the arrays are bit-identical to what
    ``build_frontiers`` feeds the Numba kernel for one geometry.
    """
    ts = np.ascontiguousarray(np.asarray(timestamps, dtype=np.float32).reshape(-1))
    n = int(ts.shape[0])
    if perfect_candidate_timestamps is None:
        perfect_ts = ts
    else:
        perfect_ts = np.ascontiguousarray(
            np.asarray(perfect_candidate_timestamps, dtype=np.float32).reshape(-1)
        )
        if int(perfect_ts.shape[0]) != n:
            raise ValueError("perfect_candidate_timestamps length must match timestamps")
    if great_candidate_timestamps is None:
        great_ts = ts
    else:
        great_ts = np.ascontiguousarray(
            np.asarray(great_candidate_timestamps, dtype=np.float32).reshape(-1)
        )
        if int(great_ts.shape[0]) != n:
            raise ValueError("great_candidate_timestamps length must match timestamps")
    envelopes = precise_envelopes(ts, np.ones(n, dtype=np.int16))
    floor_ts, great_floor_ts = envelopes.perfect_floor, envelopes.great_floor
    lane_arr = (
        np.arange(n, dtype=np.int32)
        if lanes is None
        else np.ascontiguousarray(np.asarray(lanes, dtype=np.int32).reshape(-1))
    )
    if int(lane_arr.shape[0]) != n:
        raise ValueError("lanes length must match timestamps")

    table = compact_action_table(float(raw_fever_fill), max(0, int(non_fever_base)), bool(use_forced_great_timing))
    song = song_arrays(ts, perfect_ts, great_ts, floor_ts, great_floor_ts, None, None, lane_arr)
    prefix_perfect_hit, _prefix_perfect_valid, prefix_late_hit, _prefix_late_valid = (
        _numba_build_prefix_activation_hit_tables(int(n), ts, perfect_ts, great_ts, song.late_great_floor)
    )
    # One fever time (kept in float32, as this bundle always held it): its row is 0.
    ends = fever_ends(song, prefix_perfect_hit, prefix_late_hit, np.asarray([np.float32(real_fever_time)], dtype=np.float64))
    # Per hit token on the Perfect floor: each note's chart time, then its latest Perfect, then its latest Great.
    timestamp_end_idx, perfect_end_idx, great_end_idx = (
        ends.perfect_floor_by_hit[:, kind * n : (kind + 1) * n] for kind in range(3)
    )

    return {
        "n": n,
        "action_count": int(table.later_fill.shape[0]),
        "raw_fever_fill": float(raw_fever_fill),
        "action_k": table.action_k,
        "later_fill": table.later_fill,
        "first_fill": table.first_fill,
        "later_forced": table.later_forced,
        "first_forced": table.first_forced,
        "later_activation_forced": table.later_activation_forced,
        "first_activation_forced": table.first_activation_forced,
        "timestamps": ts,
        "perfect_candidate_timestamps": perfect_ts,
        "great_candidate_timestamps": great_ts,
        "perfect_floor_timestamps": floor_ts,
        "great_floor_timestamps": great_floor_ts,
        "lanes": lane_arr,
        "timestamp_end_idx": timestamp_end_idx,
        "perfect_end_idx": perfect_end_idx,
        "great_end_idx": great_end_idx,
        "capped_perfect_edge_e": ends.perfect_e,
        "capped_late_edge_e": ends.late_e,
        "capped_eg_perfect_e": ends.eg_perfect_e,
        "capped_eg_late_e": ends.eg_late_e,
        "capped_perfect_exit_e": ends.perfect_exit_e,
        "capped_late_exit_e": ends.late_exit_e,
        "real_time_idx": 0,
        "use_forced_great_timing_i": 1 if bool(use_forced_great_timing) else 0,
    }
