from __future__ import annotations

import concurrent.futures
import threading
import time
from dataclasses import dataclass

import numpy as np

from . import response_build_gpu_numba as _rb_numba
from .response_build_gpu_precompute import FirstOnlyCanonicalization
from .response_build_gpu_reducer import (
    _exact_action_fill_runs,
    _first_frontier_reducer_executor,
    _first_frontier_results_for_precomputed_range,
    _FirstFrontierWorkspacePlan,
    _resolve_first_only_reducer_threads,
)
from .response_types import FgResponseFrontierResult


_REGION_TABLE_ENTRY_BYTES = 5 * np.dtype(np.int32).itemsize + 2 * np.dtype(np.float64).itemsize


@dataclass(frozen=True, slots=True)
class _FirstFrontierGroupContext:
    n: int
    timestamps: np.ndarray
    candidate_high_delta_max: float
    perfect_candidate_timestamps: np.ndarray
    great_candidate_timestamps: np.ndarray
    perfect_floor_timestamps: np.ndarray
    great_floor_timestamps: np.ndarray
    lanes: np.ndarray
    prefix_perfect_hit: np.ndarray
    prefix_perfect_valid: np.ndarray
    prefix_late_hit: np.ndarray
    prefix_late_valid: np.ndarray
    canonical: FirstOnlyCanonicalization
    use_forced_great_timing: bool
    empty_region_table: tuple | None
    workspace_plan: _FirstFrontierWorkspacePlan


@dataclass(frozen=True, slots=True)
class _RegionGroupScheduleStats:
    executor_creations: int
    region_tables_built: int
    region_table_peak_live: int
    region_table_peak_live_bytes: int
    region_table_parallelism: int
    region_table_parallel_peak_bound_bytes: int
    region_table_legacy_single_peak_bound_bytes: int
    region_table_build_work_ms: float
    region_group_reduce_work_ms: float


def _region_table_build_peak_bound_bytes(
    *,
    n: int,
    action_k: np.ndarray,
    raw_fever_fill: float,
) -> int:
    """Exact upper bound while candidate arrays materialize the trimmed table copies."""
    actions = np.ascontiguousarray(np.asarray(action_k, dtype=np.int32).reshape(-1))
    capacity = int(
        _rb_numba._numba_region_core_candidate_capacity(
            int(n), int(actions.shape[0]), actions, float(raw_fever_fill)
        )
    )
    starts_bytes = (int(n) + 2) * np.dtype(np.int64).itemsize
    return int(starts_bytes + 2 * int(capacity) * int(_REGION_TABLE_ENTRY_BYTES))


def _region_table_retained_bound_bytes(
    *,
    n: int,
    action_k: np.ndarray,
    raw_fever_fill: float,
) -> int:
    """Exact upper bound after candidate arrays have been replaced by retained copies."""
    actions = np.ascontiguousarray(np.asarray(action_k, dtype=np.int32).reshape(-1))
    capacity = int(
        _rb_numba._numba_region_core_candidate_capacity(
            int(n), int(actions.shape[0]), actions, float(raw_fever_fill)
        )
    )
    starts_bytes = (int(n) + 2) * np.dtype(np.int64).itemsize
    return int(starts_bytes + int(capacity) * int(_REGION_TABLE_ENTRY_BYTES))


def _legacy_single_region_table_peak_bound_bytes(*, n: int, region_action_count: int) -> int:
    """Historical exhaustive one-live-table bound that current-main already reserves safely."""
    capacity = (int(n) + 1) * max(1, int(region_action_count)) * 2
    starts_bytes = (int(n) + 2) * np.dtype(np.int64).itemsize
    return int(starts_bytes + 2 * int(capacity) * int(_REGION_TABLE_ENTRY_BYTES))


def _validate_region_group_memory_bounds(
    *,
    build_peak_bounds: tuple[int, ...],
    retained_peak_bounds: tuple[int, ...],
    legacy_single_peak_bound: int,
) -> None:
    """Validate producer-owned bounds used by dynamic build/reduce admission."""
    builds = tuple(int(value) for value in build_peak_bounds)
    retained = tuple(int(value) for value in retained_peak_bounds)
    if len(builds) != len(retained):
        raise ValueError("FG region-table build and retained memory bounds must align")
    if any(value < 0 for value in (*builds, *retained)):
        raise ValueError("FG region-table memory bounds must be nonnegative")
    if any(int(retained_value) > int(build_value) for build_value, retained_value in zip(builds, retained, strict=True)):
        raise ValueError("FG retained region-table bound cannot exceed its build peak")
    if builds and max(builds) > int(legacy_single_peak_bound):
        raise MemoryError("FG exact region table exceeds the historical single-table peak bound")


def _region_table_bytes(region_table: tuple) -> int:
    return int(sum(int(np.asarray(array).nbytes) for array in region_table))


class _ConcurrentRegionTableStats:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.build_seconds = 0.0
        self.built = 0
        self.live = 0
        self.live_bytes = 0
        self.peak_live = 0
        self.peak_live_bytes = 0
        self.reduce_seconds = 0.0

    def opened(self, *, table_bytes: int, build_seconds: float) -> None:
        with self._lock:
            self.built += 1
            self.build_seconds += float(build_seconds)
            self.live += 1
            self.live_bytes += int(table_bytes)
            self.peak_live = max(int(self.peak_live), int(self.live))
            self.peak_live_bytes = max(int(self.peak_live_bytes), int(self.live_bytes))

    def closed(self, *, table_bytes: int, reduce_seconds: float) -> None:
        with self._lock:
            self.reduce_seconds += float(reduce_seconds)
            self.live -= 1
            self.live_bytes -= int(table_bytes)
            if int(self.live) < 0 or int(self.live_bytes) < 0:
                raise ValueError("FG concurrent region-table accounting underflowed")

    def reduced(self, *, reduce_seconds: float) -> None:
        with self._lock:
            self.reduce_seconds += float(reduce_seconds)


def _reduce_first_frontier_group(
    *,
    table_key: tuple[float, int],
    group_items: list[tuple],
    region_table: tuple,
    context: _FirstFrontierGroupContext,
    executor: concurrent.futures.ThreadPoolExecutor | None,
    reducer_threads: int,
) -> list[tuple[int, FgResponseFrontierResult]]:
    if not group_items:
        raise ValueError("FG region-table group cannot be empty")
    canonical = context.canonical
    representative = group_items[0]
    perfect_run_starts, perfect_run_ends = _exact_action_fill_runs(representative[5])
    late_run_starts, late_run_ends = _exact_action_fill_runs(representative[5], representative[9])
    real_time_index = np.ascontiguousarray(
        np.asarray(
            [canonical.real_time_index_by_source[int(item[0])] for item in group_items],
            dtype=np.int32,
        )
    )
    common = {
        "n": int(context.n),
        "chunk": group_items,
        "timestamps": context.timestamps,
        "candidate_high_delta_max": context.candidate_high_delta_max,
        "perfect_candidate_timestamps": context.perfect_candidate_timestamps,
        "great_candidate_timestamps": context.great_candidate_timestamps,
        "perfect_floor_timestamps": context.perfect_floor_timestamps,
        "great_floor_timestamps": context.great_floor_timestamps,
        "lanes": context.lanes,
        "prefix_perfect_hit": context.prefix_perfect_hit,
        "prefix_perfect_valid": context.prefix_perfect_valid,
        "prefix_late_hit": context.prefix_late_hit,
        "prefix_late_valid": context.prefix_late_valid,
        "timestamp_end_idx": canonical.timestamp_end_idx,
        "perfect_end_idx": canonical.perfect_end_idx,
        "great_end_idx": canonical.great_end_idx,
        "great_floor_end_idx": canonical.great_floor_end_idx,
        "capped_perfect_edge_e": canonical.capped_perfect_edge_e,
        "capped_late_edge_e": canonical.capped_late_edge_e,
        "capped_eg_perfect_e": canonical.capped_eg_perfect_e,
        "capped_eg_late_e": canonical.capped_eg_late_e,
        "real_time_index": real_time_index,
        "use_forced_great_timing": bool(context.use_forced_great_timing),
        "perfect_run_starts": perfect_run_starts,
        "perfect_run_ends": perfect_run_ends,
        "late_run_starts": late_run_starts,
        "late_run_ends": late_run_ends,
        "region_tables_by_key": {table_key: region_table},
        "workspace_plan": context.workspace_plan,
    }
    geometry_count = len(group_items)
    if int(reducer_threads) <= 1:
        return _first_frontier_results_for_precomputed_range(
            start=0,
            stop=int(geometry_count),
            **common,
        )
    if executor is None:
        raise ValueError("FG multi-thread group reduction requires its song executor")
    target_ranges = max(int(reducer_threads), int(reducer_threads) * 256)
    step = max(1, (int(geometry_count) + int(target_ranges) - 1) // int(target_ranges))
    futures = tuple(
        executor.submit(
            _first_frontier_results_for_precomputed_range,
            start=int(start),
            stop=min(int(geometry_count), int(start) + int(step)),
            **common,
        )
        for start in range(0, int(geometry_count), int(step))
    )
    return [row for future in futures for row in future.result()]


def _reduce_prebuilt_first_frontier_group(
    *,
    table_key: tuple[float, int],
    group_items: list[tuple],
    region_table: tuple,
    table_bytes: int,
    tracked_table: bool,
    context: _FirstFrontierGroupContext,
    table_stats: _ConcurrentRegionTableStats,
) -> list[tuple[int, FgResponseFrontierResult]]:
    reduce_t0 = time.perf_counter()
    try:
        return _reduce_first_frontier_group(
            table_key=table_key,
            group_items=group_items,
            region_table=region_table,
            context=context,
            executor=None,
            reducer_threads=1,
        )
    finally:
        reduce_seconds = float(time.perf_counter() - reduce_t0)
        if tracked_table:
            table_stats.closed(table_bytes=int(table_bytes), reduce_seconds=reduce_seconds)
        else:
            table_stats.reduced(reduce_seconds=reduce_seconds)


def _consume_completed_group_futures(
    *,
    completed: set[concurrent.futures.Future],
    inflight: dict[concurrent.futures.Future, tuple[int, int]],
    group_results: list[list[tuple[int, FgResponseFrontierResult]] | None],
) -> int:
    released_bytes = 0
    for future in completed:
        group_idx, table_bytes = inflight.pop(future)
        group_results[int(group_idx)] = future.result()
        released_bytes += int(table_bytes)
    return int(released_bytes)


def _build_region_table(
    *,
    table_key: tuple[float, int],
    group_items: list[tuple],
    context: _FirstFrontierGroupContext,
) -> tuple[tuple, int, float]:
    build_t0 = time.perf_counter()
    action_k_arr = np.ascontiguousarray(group_items[0][4], dtype=np.int32)
    region_table = _rb_numba._numba_build_region_core_table(
        int(context.n),
        int(action_k_arr.shape[0]),
        action_k_arr,
        float(table_key[0]),
        context.timestamps,
        context.candidate_high_delta_max,
        context.perfect_floor_timestamps,
        context.perfect_candidate_timestamps,
        context.great_floor_timestamps,
        context.great_candidate_timestamps,
        context.lanes,
    )
    return region_table, _region_table_bytes(region_table), float(time.perf_counter() - build_t0)


def _schedule_parallel_groups(
    *,
    group_entries: tuple[tuple[tuple[float, int], list[tuple]], ...],
    build_peak_bounds: tuple[int, ...],
    retained_peak_bounds: tuple[int, ...],
    legacy_peak_bound: int,
    parallelism: int,
    context: _FirstFrontierGroupContext,
) -> tuple[tuple[list[tuple[int, FgResponseFrontierResult]], ...], _ConcurrentRegionTableStats]:
    table_stats = _ConcurrentRegionTableStats()
    group_results: list[list[tuple[int, FgResponseFrontierResult]] | None] = [None] * len(group_entries)
    if bool(context.use_forced_great_timing):
        return _schedule_parallel_built_groups(
            group_entries=group_entries,
            build_peak_bounds=build_peak_bounds,
            retained_peak_bounds=retained_peak_bounds,
            legacy_peak_bound=int(legacy_peak_bound),
            worker_limit=int(parallelism),
            context=context,
            table_stats=table_stats,
            group_results=group_results,
        )
    inflight: dict[concurrent.futures.Future, tuple[int, int]] = {}
    inflight_table_bytes = 0
    with _first_frontier_reducer_executor(int(parallelism)) as group_executor:
        for group_idx, ((table_key, group_items), build_peak_bound, retained_peak_bound) in enumerate(
            zip(group_entries, build_peak_bounds, retained_peak_bounds, strict=True)
        ):
            while len(inflight) >= int(parallelism) or (
                bool(context.use_forced_great_timing)
                and int(inflight_table_bytes) + int(build_peak_bound) > int(legacy_peak_bound)
            ):
                if not inflight:
                    raise MemoryError("FG region-table pipeline cannot admit its next exact build")
                completed, _pending = concurrent.futures.wait(
                    tuple(inflight), return_when=concurrent.futures.FIRST_COMPLETED
                )
                inflight_table_bytes -= _consume_completed_group_futures(
                    completed=completed,
                    inflight=inflight,
                    group_results=group_results,
                )

            if bool(context.use_forced_great_timing):
                region_table, table_bytes, build_seconds = _build_region_table(
                    table_key=table_key,
                    group_items=group_items,
                    context=context,
                )
                if int(table_bytes) > int(retained_peak_bound):
                    raise MemoryError("FG retained region table exceeds its producer-owned bound")
                table_stats.opened(table_bytes=int(table_bytes), build_seconds=float(build_seconds))
                tracked_table = True
            else:
                if context.empty_region_table is None:
                    raise ValueError("FG empty region table is missing for non-forced timing")
                region_table = context.empty_region_table
                table_bytes = 0
                tracked_table = False

            future = group_executor.submit(
                _reduce_prebuilt_first_frontier_group,
                table_key=table_key,
                group_items=group_items,
                region_table=region_table,
                table_bytes=int(table_bytes),
                tracked_table=bool(tracked_table),
                context=context,
                table_stats=table_stats,
            )
            inflight[future] = (int(group_idx), int(table_bytes))
            inflight_table_bytes += int(table_bytes)
            del region_table

        while inflight:
            completed, _pending = concurrent.futures.wait(
                tuple(inflight), return_when=concurrent.futures.FIRST_COMPLETED
            )
            inflight_table_bytes -= _consume_completed_group_futures(
                completed=completed,
                inflight=inflight,
                group_results=group_results,
            )
    if int(inflight_table_bytes) != 0:
        raise ValueError("FG region-table pipeline byte accounting did not drain")
    if int(table_stats.live) != 0 or int(table_stats.live_bytes) != 0:
        raise ValueError("FG concurrent region-table accounting did not drain")
    if any(result is None for result in group_results):
        raise ValueError("FG region-table pipeline missed a group result")
    return tuple(result for result in group_results if result is not None), table_stats


def _schedule_parallel_built_groups(
    *,
    group_entries: tuple[tuple[tuple[float, int], list[tuple]], ...],
    build_peak_bounds: tuple[int, ...],
    retained_peak_bounds: tuple[int, ...],
    legacy_peak_bound: int,
    worker_limit: int,
    context: _FirstFrontierGroupContext,
    table_stats: _ConcurrentRegionTableStats,
    group_results: list[list[tuple[int, FgResponseFrontierResult]] | None],
) -> tuple[tuple[list[tuple[int, FgResponseFrontierResult]], ...], _ConcurrentRegionTableStats]:
    """Pipeline independent table producers and consumers under one exact byte reservation."""
    build_inflight: dict[concurrent.futures.Future, tuple[int, int, int]] = {}
    reduce_inflight: dict[concurrent.futures.Future, tuple[int, int]] = {}
    reserved_bytes = 0
    next_group_idx = 0
    with (
        _first_frontier_reducer_executor(int(worker_limit)) as build_executor,
        _first_frontier_reducer_executor(int(worker_limit)) as reduce_executor,
    ):
        while (
            int(next_group_idx) < len(group_entries)
            or bool(build_inflight)
            or bool(reduce_inflight)
        ):
            while int(next_group_idx) < len(group_entries):
                active = len(build_inflight) + len(reduce_inflight)
                build_peak_bound = int(build_peak_bounds[int(next_group_idx)])
                if int(active) >= int(worker_limit):
                    break
                if int(reserved_bytes) + int(build_peak_bound) > int(legacy_peak_bound):
                    break
                table_key, group_items = group_entries[int(next_group_idx)]
                future = build_executor.submit(
                    _build_region_table,
                    table_key=table_key,
                    group_items=group_items,
                    context=context,
                )
                build_inflight[future] = (
                    int(next_group_idx),
                    int(build_peak_bound),
                    int(retained_peak_bounds[int(next_group_idx)]),
                )
                reserved_bytes += int(build_peak_bound)
                next_group_idx += 1

            futures = tuple(build_inflight) + tuple(reduce_inflight)
            if not futures:
                raise MemoryError("FG region-table pipeline cannot admit its next exact build")
            completed, _pending = concurrent.futures.wait(
                futures, return_when=concurrent.futures.FIRST_COMPLETED
            )
            completed_reductions = {future for future in completed if future in reduce_inflight}
            if completed_reductions:
                reserved_bytes -= _consume_completed_group_futures(
                    completed=completed_reductions,
                    inflight=reduce_inflight,
                    group_results=group_results,
                )
            for future in (value for value in completed if value in build_inflight):
                group_idx, build_peak_bound, retained_peak_bound = build_inflight.pop(future)
                region_table, table_bytes, build_seconds = future.result()
                reserved_bytes -= int(build_peak_bound)
                if int(table_bytes) > int(retained_peak_bound):
                    raise MemoryError("FG retained region table exceeds its producer-owned bound")
                table_stats.opened(table_bytes=int(table_bytes), build_seconds=float(build_seconds))
                reserved_bytes += int(table_bytes)
                table_key, group_items = group_entries[int(group_idx)]
                reduction = reduce_executor.submit(
                    _reduce_prebuilt_first_frontier_group,
                    table_key=table_key,
                    group_items=group_items,
                    region_table=region_table,
                    table_bytes=int(table_bytes),
                    tracked_table=True,
                    context=context,
                    table_stats=table_stats,
                )
                reduce_inflight[reduction] = (int(group_idx), int(table_bytes))
                del region_table
            if int(reserved_bytes) < 0 or int(reserved_bytes) > int(legacy_peak_bound):
                raise ValueError("FG region-table pipeline reservation escaped its exact bound")
    if int(reserved_bytes) != 0:
        raise ValueError("FG region-table pipeline byte reservation did not drain")
    if int(table_stats.live) != 0 or int(table_stats.live_bytes) != 0:
        raise ValueError("FG concurrent region-table accounting did not drain")
    if any(result is None for result in group_results):
        raise ValueError("FG region-table pipeline missed a group result")
    return tuple(result for result in group_results if result is not None), table_stats


def _schedule_sequential_groups(
    *,
    group_entries: tuple[tuple[tuple[float, int], list[tuple]], ...],
    context: _FirstFrontierGroupContext,
) -> tuple[tuple[list[tuple[int, FgResponseFrontierResult]], ...], _ConcurrentRegionTableStats, int]:
    table_stats = _ConcurrentRegionTableStats()
    song_reducer_threads = max(
        (_resolve_first_only_reducer_threads(len(group_items)) for _key, group_items in group_entries),
        default=1,
    )
    executor = None
    executor_creations = 0
    results = []
    try:
        if int(song_reducer_threads) > 1:
            executor = _first_frontier_reducer_executor(int(song_reducer_threads))
            executor_creations = 1
        for table_key, group_items in group_entries:
            if bool(context.use_forced_great_timing):
                region_table, table_bytes, build_seconds = _build_region_table(
                    table_key=table_key,
                    group_items=group_items,
                    context=context,
                )
                table_stats.opened(table_bytes=int(table_bytes), build_seconds=float(build_seconds))
                tracked_table = True
            else:
                if context.empty_region_table is None:
                    raise ValueError("FG empty region table is missing for non-forced timing")
                region_table = context.empty_region_table
                table_bytes = 0
                tracked_table = False

            reduce_t0 = time.perf_counter()
            try:
                results.append(
                    _reduce_first_frontier_group(
                        table_key=table_key,
                        group_items=group_items,
                        region_table=region_table,
                        context=context,
                        executor=executor,
                        reducer_threads=_resolve_first_only_reducer_threads(len(group_items)),
                    )
                )
            finally:
                reduce_seconds = float(time.perf_counter() - reduce_t0)
                if tracked_table:
                    table_stats.closed(table_bytes=int(table_bytes), reduce_seconds=reduce_seconds)
                else:
                    table_stats.reduced(reduce_seconds=reduce_seconds)
            del region_table
    finally:
        if executor is not None:
            executor.shutdown(wait=True)
    if int(table_stats.live) != 0 or int(table_stats.live_bytes) != 0:
        raise ValueError("FG sequential region-table accounting did not drain")
    return tuple(results), table_stats, int(executor_creations)


def _schedule_first_frontier_region_groups(
    *,
    grouped_items: dict[tuple[float, int], list[tuple]],
    context: _FirstFrontierGroupContext,
) -> tuple[tuple[list[tuple[int, FgResponseFrontierResult]], ...], _RegionGroupScheduleStats]:
    group_entries = tuple(grouped_items.items())
    thread_limit = _resolve_first_only_reducer_threads(len(group_entries))
    if bool(context.use_forced_great_timing):
        build_peak_bounds = tuple(
            _region_table_build_peak_bound_bytes(
                n=int(context.n),
                action_k=np.ascontiguousarray(group_items[0][4], dtype=np.int32),
                raw_fever_fill=float(table_key[0]),
            )
            for table_key, group_items in group_entries
        )
        retained_peak_bounds = tuple(
            _region_table_retained_bound_bytes(
                n=int(context.n),
                action_k=np.ascontiguousarray(group_items[0][4], dtype=np.int32),
                raw_fever_fill=float(table_key[0]),
            )
            for table_key, group_items in group_entries
        )
        legacy_peak_bound = max(
            (
                _legacy_single_region_table_peak_bound_bytes(
                    n=int(context.n),
                    region_action_count=int(np.asarray(group_items[0][4]).shape[0]),
                )
                for _table_key, group_items in group_entries
            ),
            default=0,
        )
        _validate_region_group_memory_bounds(
            build_peak_bounds=build_peak_bounds,
            retained_peak_bounds=retained_peak_bounds,
            legacy_single_peak_bound=int(legacy_peak_bound),
        )
        # Builders and reducers now share the configured worker budget dynamically. Admission is
        # performed against exact per-group reservations inside the pipeline, so completed builds
        # release their temporary half before the retained table enters reduction.
        parallelism = int(thread_limit)
        parallel_peak_bound = int(legacy_peak_bound)
    else:
        build_peak_bounds = (0,) * len(group_entries)
        retained_peak_bounds = (0,) * len(group_entries)
        legacy_peak_bound = 0
        parallel_peak_bound = 0
        parallelism = int(thread_limit)

    if int(parallelism) > 1:
        group_results, table_stats = _schedule_parallel_groups(
            group_entries=group_entries,
            build_peak_bounds=build_peak_bounds,
            retained_peak_bounds=retained_peak_bounds,
            legacy_peak_bound=int(legacy_peak_bound),
            parallelism=int(parallelism),
            context=context,
        )
        executor_creations = 2 if bool(context.use_forced_great_timing) else 1
    else:
        group_results, table_stats, executor_creations = _schedule_sequential_groups(
            group_entries=group_entries,
            context=context,
        )

    stats = _RegionGroupScheduleStats(
        executor_creations=int(executor_creations),
        region_tables_built=int(table_stats.built),
        region_table_peak_live=int(table_stats.peak_live),
        region_table_peak_live_bytes=int(table_stats.peak_live_bytes),
        region_table_parallelism=int(parallelism),
        region_table_parallel_peak_bound_bytes=int(parallel_peak_bound),
        region_table_legacy_single_peak_bound_bytes=int(legacy_peak_bound),
        region_table_build_work_ms=float(table_stats.build_seconds * 1000.0),
        region_group_reduce_work_ms=float(table_stats.reduce_seconds * 1000.0),
    )
    return group_results, stats
