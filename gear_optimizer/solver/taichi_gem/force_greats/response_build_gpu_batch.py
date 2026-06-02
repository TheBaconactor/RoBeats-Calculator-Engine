from __future__ import annotations

import concurrent.futures
from typing import Any

import numpy as np

from .response_builder import _action_table
from .response_build_gpu_precompute import (
    _canonicalize_first_only_prepared_items,
    _first_only_chunks,
    _precompute_end_indices,
    _precompute_great_range_argmax,
)
from .response_build_gpu_reducer import (
    _first_frontier_results_for_precomputed_range,
    _first_frontier_reducer_executor,
    _resolve_first_only_reducer_threads,
)
from .response_types import FgResponseFrontierResult, _EMPTY_SURFACE


def _build_force_greats_response_first_frontiers_gpu_batch(
    *,
    timestamps: Any,
    great_candidate_timestamps: Any | None = None,
    geometries: Any,
    use_forced_great_timing: bool = True,
) -> tuple[FgResponseFrontierResult, ...]:
    ts = np.ascontiguousarray(np.asarray(timestamps, dtype=np.float32).reshape(-1))
    n = int(ts.shape[0])
    geometry_rows = tuple(geometries or ())
    if not geometry_rows:
        return ()
    if n <= 0:
        return tuple(FgResponseFrontierResult((_EMPTY_SURFACE,), {}, 0, 0, 0, 0, 1, 1, 0, 0.0) for _ in geometry_rows)
    if bool(np.any(ts[1:] < ts[:-1])):
        raise ValueError("timestamps must be sorted in nondecreasing order")
    if great_candidate_timestamps is None:
        great_ts = ts
    else:
        great_ts = np.ascontiguousarray(np.asarray(great_candidate_timestamps, dtype=np.float32).reshape(-1))
        if int(great_ts.shape[0]) != n:
            raise ValueError("great_candidate_timestamps length must match timestamps")
    great_range_argmax, great_range_log2 = _precompute_great_range_argmax(great_ts)

    prepared = []
    action_table_cache: dict[tuple[float, int, bool], tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = {}
    for idx, row in enumerate(geometry_rows):
        raw_fever_fill, non_fever_base, real_fever_time = row
        action_key = (float(raw_fever_fill), max(0, int(non_fever_base)), bool(use_forced_great_timing))
        action_arrays = action_table_cache.get(action_key)
        if action_arrays is None:
            actions, later_fill, first_fill, later_forced, first_forced = _action_table(
                raw_fever_fill=float(raw_fever_fill),
                non_fever_base=max(0, int(non_fever_base)),
                use_forced_great_timing=bool(use_forced_great_timing),
            )
            action_arrays = (
                np.asarray(actions, dtype=np.int32),
                np.asarray(later_fill, dtype=np.int32),
                np.asarray(first_fill, dtype=np.int32),
                np.asarray(later_forced, dtype=np.int32),
                np.asarray(first_forced, dtype=np.int32),
            )
            action_table_cache[action_key] = action_arrays
        actions_arr, later_fill_arr, first_fill_arr, later_forced_arr, first_forced_arr = action_arrays
        prepared.append(
            (
                idx,
                max(0, int(non_fever_base)),
                float(real_fever_time),
                actions_arr,
                later_fill_arr,
                first_fill_arr,
                later_forced_arr,
                first_forced_arr,
            )
        )

    out: list[FgResponseFrontierResult | None] = [None] * len(geometry_rows)
    prepared, duplicate_sources_by_source = _canonicalize_first_only_prepared_items(
        prepared=prepared,
        timestamps=ts,
        great_candidate_timestamps=great_ts,
    )
    chunk_iter = _first_only_chunks(n=int(n), items=prepared)

    first_only_executor: concurrent.futures.ThreadPoolExecutor | None = None
    try:
        for action_count, chunk in chunk_iter:
            geometry_count = len(chunk)
            real_times = np.asarray([item[2] for item in chunk], dtype=np.float32)
            real_time_index, timestamp_end_idx, great_end_idx = _precompute_end_indices(
                timestamps=ts,
                great_candidate_timestamps=great_ts,
                real_times=real_times,
            )
            reducer_threads = _resolve_first_only_reducer_threads(int(geometry_count))
            if int(reducer_threads) <= 1:
                range_results = (
                    _first_frontier_results_for_precomputed_range(
                        n=int(n),
                        chunk=chunk,
                        start=0,
                        stop=int(geometry_count),
                        timestamps=ts,
                        great_candidate_timestamps=great_ts,
                        timestamp_end_idx=timestamp_end_idx,
                        great_end_idx=great_end_idx,
                        great_range_argmax=great_range_argmax,
                        great_range_log2=great_range_log2,
                        real_time_index=real_time_index,
                        use_forced_great_timing=bool(use_forced_great_timing),
                    ),
                )
            else:
                target_ranges = max(int(reducer_threads), int(reducer_threads) * 32)
                step = max(1, (int(geometry_count) + int(target_ranges) - 1) // int(target_ranges))
                ranges = tuple(
                    (start, min(int(geometry_count), start + int(step)))
                    for start in range(0, int(geometry_count), int(step))
                )
                if first_only_executor is None:
                    first_only_executor = _first_frontier_reducer_executor(int(reducer_threads))
                futures = tuple(
                    first_only_executor.submit(
                        _first_frontier_results_for_precomputed_range,
                        n=int(n),
                        chunk=chunk,
                        start=int(start),
                        stop=int(stop),
                        timestamps=ts,
                        great_candidate_timestamps=great_ts,
                        timestamp_end_idx=timestamp_end_idx,
                        great_end_idx=great_end_idx,
                        great_range_argmax=great_range_argmax,
                        great_range_log2=great_range_log2,
                        real_time_index=real_time_index,
                        use_forced_great_timing=bool(use_forced_great_timing),
                    )
                    for start, stop in ranges
                )
                range_results = tuple(future.result() for future in futures)
            for result_rows in range_results:
                for source_idx, frontier in result_rows:
                    for duplicate_source_idx in duplicate_sources_by_source[int(source_idx)]:
                        out[int(duplicate_source_idx)] = frontier
    finally:
        if first_only_executor is not None:
            first_only_executor.shutdown(wait=True)

    missing = [idx for idx, frontier in enumerate(out) if frontier is None]
    if missing:
        raise ValueError(f"FG response frontier GPU batch missed geometry indices: {missing[:8]}")
    return tuple(frontier for frontier in out if frontier is not None)

def build_force_greats_response_first_frontiers_gpu_batch(
    *,
    timestamps: Any,
    great_candidate_timestamps: Any | None = None,
    geometries: Any,
    use_forced_great_timing: bool = True,
) -> tuple[FgResponseFrontierResult, ...]:
    return _build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=timestamps,
        great_candidate_timestamps=great_candidate_timestamps,
        geometries=geometries,
        use_forced_great_timing=bool(use_forced_great_timing),
    )
