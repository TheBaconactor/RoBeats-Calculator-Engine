"""The FG first-frontier kernel's inputs for one ``(raw_fever_fill, non_fever_base, real_fever_time)`` geometry,
built with the production prep functions (action table -> compaction -> end-index precompute)."""

from __future__ import annotations

from typing import Any

import numpy as np

from gear_optimizer.solver.timing_envelope import precise_envelopes
from gear_optimizer.solver.taichi_gem.force_greats.response_builder import _action_table
from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_batch import (
    _compact_first_frontier_action_arrays,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_precompute import (
    _precompute_end_indices,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
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
    """Return the full argument bundle for the first-frontier kernel.

    Reuses the production action-table + compaction + end-index precompute so the
    arrays are bit-identical to what ``build_force_greats_response_first_frontiers_gpu_batch``
    feeds the Numba kernel for one geometry.
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

    actions, later_fill, first_fill, later_forced, first_forced = _action_table(
        raw_fever_fill=float(raw_fever_fill),
        non_fever_base=max(0, int(non_fever_base)),
        use_forced_great_timing=bool(use_forced_great_timing),
    )
    (
        action_k_arr,
        later_fill_arr,
        first_fill_arr,
        later_forced_arr,
        first_forced_arr,
        later_activation_forced_arr,
        first_activation_forced_arr,
    ) = _compact_first_frontier_action_arrays(
        actions, later_fill, first_fill, later_forced, first_forced, float(raw_fever_fill)
    )

    real_times = np.asarray([float(real_fever_time)], dtype=np.float32)
    prefix_perfect_hit, _prefix_perfect_valid, prefix_late_hit, _prefix_late_valid = (
        _numba_build_prefix_activation_hit_tables(
            int(n),
            ts,
            perfect_ts,
            great_ts,
            perfect_ts + np.float32(0.001),
        )
    )
    (
        real_time_index,
        timestamp_end_idx,
        perfect_end_idx,
        great_end_idx,
        great_floor_end_idx,
        capped_perfect_edge_e,
        capped_late_edge_e,
        capped_eg_perfect_e,
        capped_eg_late_e,
        capped_perfect_exit_e,
        capped_late_exit_e,
    ) = _precompute_end_indices(
        timestamps=ts,
        perfect_candidate_timestamps=perfect_ts,
        great_candidate_timestamps=great_ts,
        perfect_floor_timestamps=floor_ts,
        great_floor_timestamps=great_floor_ts,
        prefix_perfect_hit=prefix_perfect_hit,
        prefix_late_hit=prefix_late_hit,
        exit_ceiling_timestamps=np.minimum.accumulate(perfect_ts[::-1])[::-1],
        late_great_floor_timestamps=perfect_ts + np.float32(0.001),
        lanes=lane_arr,
        real_times=real_times,
    )

    return {
        "n": n,
        "action_count": int(later_fill_arr.shape[0]),
        "raw_fever_fill": float(raw_fever_fill),
        "action_k": np.ascontiguousarray(action_k_arr, dtype=np.int32),
        "later_fill": np.ascontiguousarray(later_fill_arr, dtype=np.int32),
        "first_fill": np.ascontiguousarray(first_fill_arr, dtype=np.int32),
        "later_forced": np.ascontiguousarray(later_forced_arr, dtype=np.int32),
        "first_forced": np.ascontiguousarray(first_forced_arr, dtype=np.int32),
        "later_activation_forced": np.ascontiguousarray(later_activation_forced_arr, dtype=np.int32),
        "first_activation_forced": np.ascontiguousarray(first_activation_forced_arr, dtype=np.int32),
        "timestamps": ts,
        "perfect_candidate_timestamps": perfect_ts,
        "great_candidate_timestamps": great_ts,
        "perfect_floor_timestamps": floor_ts,
        "great_floor_timestamps": great_floor_ts,
        "lanes": lane_arr,
        "timestamp_end_idx": timestamp_end_idx,
        "perfect_end_idx": perfect_end_idx,
        "great_end_idx": great_end_idx,
        "great_floor_end_idx": great_floor_end_idx,
        "capped_perfect_edge_e": capped_perfect_edge_e,
        "capped_late_edge_e": capped_late_edge_e,
        "capped_eg_perfect_e": capped_eg_perfect_e,
        "capped_eg_late_e": capped_eg_late_e,
        "capped_perfect_exit_e": capped_perfect_exit_e,
        "capped_late_exit_e": capped_late_exit_e,
        "real_time_idx": int(real_time_index[0]),
        "use_forced_great_timing_i": 1 if bool(use_forced_great_timing) else 0,
    }
