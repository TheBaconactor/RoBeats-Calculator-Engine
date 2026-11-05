"""A song's frontier build: its region tables and their reductions on the song's threads, under an exact byte budget."""

from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass

import numpy as np

from . import producer_kernels as _rb_numba
from .producer_precompute import FirstOnlyCanonicalization
from .producer_reducer import (
    _exact_action_fill_runs,
    _first_frontier_reducer_executor,
    _first_frontier_results_for_precomputed_range,
    _FirstFrontierWorkspacePlan,
    _resolve_first_only_reducer_threads,
)
from .types import FgResponseFrontierResult


_REGION_TABLE_ENTRY_BYTES = 7 * np.dtype(np.int32).itemsize
_Group = tuple[tuple[float, int], list[tuple]]  # (raw fill, non-Fever base), its geometries
_GroupResults = list[tuple[int, FgResponseFrontierResult]]


@dataclass(frozen=True, slots=True)
class _FirstFrontierGroupContext:
    n: int
    timestamps: np.ndarray
    perfect_candidate_timestamps: np.ndarray
    great_candidate_timestamps: np.ndarray
    perfect_floor_timestamps: np.ndarray
    great_floor_timestamps: np.ndarray
    late_great_floor_timestamps: np.ndarray
    lanes: np.ndarray
    prefix_perfect_hit: np.ndarray
    prefix_perfect_valid: np.ndarray
    prefix_late_hit: np.ndarray
    prefix_late_valid: np.ndarray
    canonical: FirstOnlyCanonicalization
    use_forced_great_timing: bool
    empty_region_table: tuple | None
    workspace_plan: _FirstFrontierWorkspacePlan
    # Below this fill a geometry plans no early fever exits (producer_batch.early_exit_min_fill); its exit tables are
    # then no_early_exit_e (every activation's earliest end is n, so each uses its own latest end).
    early_exit_min_fill: int
    no_early_exit_e: np.ndarray


def _region_table_bytes(region_table: tuple) -> int:
    return int(sum(int(np.asarray(array).nbytes) for array in region_table))


def _region_table_bounds(n: int, group: _Group) -> tuple[int, int]:
    """Exact upper bounds of a region table's bytes: while candidate arrays materialize the trimmed copies, and after."""
    (raw_fever_fill, _base), group_items = group
    actions = np.ascontiguousarray(group_items[0][4], dtype=np.int32)
    capacity = int(_rb_numba._numba_region_core_candidate_capacity(n, int(actions.shape[0]), actions, raw_fever_fill))
    starts_bytes = (n + 2) * np.dtype(np.int64).itemsize
    return starts_bytes + 2 * capacity * _REGION_TABLE_ENTRY_BYTES, starts_bytes + capacity * _REGION_TABLE_ENTRY_BYTES


def _single_table_byte_budget(n: int, group_entries: tuple[_Group, ...]) -> int:
    """The bytes of the exhaustive one-live-table allocation: what the song's live tables may reserve together."""
    capacity = (n + 1) * max(max(1, int(group_items[0][4].shape[0])) for _key, group_items in group_entries) * 2
    return (n + 2) * np.dtype(np.int64).itemsize + 2 * capacity * _REGION_TABLE_ENTRY_BYTES


def _reduce_first_frontier_group(
    *,
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
    fill_runs = (
        *_exact_action_fill_runs(representative[5]),
        *_exact_action_fill_runs(representative[5], representative[9]),
    )
    real_time_index = np.ascontiguousarray(
        np.asarray(
            [canonical.real_time_index_by_source[int(item[0])] for item in group_items],
            dtype=np.int32,
        )
    )
    common = {
        "context": context,
        "chunk": group_items,
        "real_time_index": real_time_index,
        "fill_runs": fill_runs,
        "region_table": region_table,
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


def _build_region_table(group: _Group, context: _FirstFrontierGroupContext) -> tuple:
    """A group's region table; without forced-Great timing every group shares one contentless table."""
    if context.empty_region_table is not None:
        return context.empty_region_table
    (raw_fever_fill, _base), group_items = group
    action_k_arr = np.ascontiguousarray(group_items[0][4], dtype=np.int32)
    return _rb_numba._numba_build_region_core_table(
        int(context.n),
        int(action_k_arr.shape[0]),
        action_k_arr,
        float(raw_fever_fill),
        context.timestamps,
        _rb_numba.HitTimes(
            context.perfect_floor_timestamps,
            context.perfect_candidate_timestamps,
            context.great_floor_timestamps,
            context.great_candidate_timestamps,
            context.late_great_floor_timestamps,
        ),
        context.lanes,
    )


def _schedule_parallel_groups(
    group_entries: tuple[_Group, ...],
    bounds: list[tuple[int, int]],
    byte_budget: int,
    worker_limit: int,
    context: _FirstFrontierGroupContext,
) -> list[_GroupResults]:
    """Pipeline table builds and reductions under one exact byte reservation: a build reserves its peak bound, and a
    built table only its own bytes until its reduction ends."""
    group_results: list[_GroupResults | None] = [None] * len(group_entries)
    building: dict[concurrent.futures.Future, int] = {}
    reducing: dict[concurrent.futures.Future, tuple[int, int]] = {}
    reserved_bytes = 0
    next_group = 0
    with (
        _first_frontier_reducer_executor(worker_limit) as build_executor,
        _first_frontier_reducer_executor(worker_limit) as reduce_executor,
    ):
        while next_group < len(group_entries) or building or reducing:
            while next_group < len(group_entries) and len(building) + len(reducing) < worker_limit:
                if reserved_bytes + bounds[next_group][0] > byte_budget:
                    break
                building[build_executor.submit(_build_region_table, group_entries[next_group], context)] = next_group
                reserved_bytes += bounds[next_group][0]
                next_group += 1
            if not building and not reducing:
                raise MemoryError("FG region-table pipeline cannot admit its next exact build")
            completed, _pending = concurrent.futures.wait((*building, *reducing), return_when=concurrent.futures.FIRST_COMPLETED)
            for future in completed:
                if future in reducing:
                    group_idx, table_bytes = reducing.pop(future)
                    group_results[group_idx] = future.result()
                    reserved_bytes -= table_bytes
                    continue
                group_idx = building.pop(future)
                region_table = future.result()
                table_bytes = _region_table_bytes(region_table)
                if table_bytes > bounds[group_idx][1]:
                    raise MemoryError("FG retained region table exceeds its producer-owned bound")
                reserved_bytes += table_bytes - bounds[group_idx][0]
                reduction = reduce_executor.submit(
                    _reduce_first_frontier_group,
                    group_items=group_entries[group_idx][1],
                    region_table=region_table,
                    context=context,
                    executor=None,
                    reducer_threads=1,
                )
                reducing[reduction] = (group_idx, table_bytes)
                del region_table
    return group_results


def _schedule_sequential_groups(group_entries: tuple[_Group, ...], context: _FirstFrontierGroupContext) -> list[_GroupResults]:
    """One group at a time, its geometries reduced in parallel when it has several."""
    song_reducer_threads = max(_resolve_first_only_reducer_threads(len(group_items)) for _key, group_items in group_entries)
    executor = _first_frontier_reducer_executor(song_reducer_threads) if song_reducer_threads > 1 else None
    try:
        return [
            _reduce_first_frontier_group(
                group_items=group[1],
                region_table=_build_region_table(group, context),
                context=context,
                executor=executor,
                reducer_threads=_resolve_first_only_reducer_threads(len(group[1])),
            )
            for group in group_entries
        ]
    finally:
        if executor is not None:
            executor.shutdown(wait=True)


def _schedule_first_frontier_region_groups(
    *,
    grouped_items: dict[tuple[float, int], list[tuple]],
    context: _FirstFrontierGroupContext,
) -> list[_GroupResults]:
    group_entries = tuple(grouped_items.items())
    parallelism = _resolve_first_only_reducer_threads(len(group_entries))
    if parallelism <= 1:
        return _schedule_sequential_groups(group_entries, context)
    n = int(context.n)
    if context.empty_region_table is None:
        return _schedule_parallel_groups(group_entries, [_region_table_bounds(n, group) for group in group_entries],
                                         _single_table_byte_budget(n, group_entries), parallelism, context)
    shared = _region_table_bytes(context.empty_region_table)
    return _schedule_parallel_groups(group_entries, [(shared, shared)] * len(group_entries),
                                     shared * len(group_entries), parallelism, context)
