"""Parity harness for the FG first-frontier construction kernel.

Builds byte-identical inputs to the production Numba kernel
``_first_frontier_from_precomputed_end_indices_numba`` for a single
``(raw_fever_fill, non_fever_base, real_fever_time)`` geometry, by reusing the
exact production prep functions (action table -> compaction -> end-index
precompute). The Numba kernel is the bit-exact parity ORACLE that the Vulkan
port must reproduce (see docs/Implementation Records/FG_FRONTIER_VULKAN_PORT.md).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from gear_optimizer.solver.timing_envelope import (
    build_great_floor_envelope_sec,
    build_perfect_floor_envelope_sec,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_builder import _action_table
from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_batch import (
    _compact_first_frontier_action_arrays,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_precompute import (
    _precompute_end_indices,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
    _HEAD_FILTER_MIN_SURFACES,
    _first_frontier_from_precomputed_end_indices_numba,
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
    arrays are bit-identical to what ``_build_force_greats_response_first_frontiers_gpu_batch``
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
    floor_ts = np.ascontiguousarray(
        np.asarray(build_perfect_floor_envelope_sec(ts, None), dtype=np.float32).reshape(-1)
    )
    great_floor_ts = np.ascontiguousarray(
        np.asarray(build_great_floor_envelope_sec(ts, None), dtype=np.float32).reshape(-1)
    )
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
    (
        real_time_index,
        timestamp_end_idx,
        perfect_end_idx,
        great_end_idx,
        great_floor_end_idx,
    ) = _precompute_end_indices(
        timestamps=ts,
        perfect_candidate_timestamps=perfect_ts,
        great_candidate_timestamps=great_ts,
        perfect_floor_timestamps=floor_ts,
        great_floor_timestamps=great_floor_ts,
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
        "real_time_idx": int(real_time_index[0]),
        "use_forced_great_timing_i": 1 if bool(use_forced_great_timing) else 0,
    }


def numba_first_frontier(args: dict[str, Any]):
    """Run the parity ORACLE (Numba kernel) -> (out[m,7] uint64, 4 int counters)."""
    return _first_frontier_from_precomputed_end_indices_numba(
        int(args["n"]),
        int(args["action_count"]),
        float(args["raw_fever_fill"]),
        args["action_k"],
        args["later_fill"],
        args["first_fill"],
        args["later_forced"],
        args["first_forced"],
        args["later_activation_forced"],
        args["first_activation_forced"],
        args["timestamps"],
        args["perfect_candidate_timestamps"],
        args["great_candidate_timestamps"],
        args["perfect_floor_timestamps"],
        args["great_floor_timestamps"],
        args["lanes"],
        args["timestamp_end_idx"],
        args["perfect_end_idx"],
        args["great_end_idx"],
        args["great_floor_end_idx"],
        int(args["real_time_idx"]),
        int(args["use_forced_great_timing_i"]),
        int(_HEAD_FILTER_MIN_SURFACES),
    )
