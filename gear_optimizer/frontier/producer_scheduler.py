"""A song's frontier build on its threads: each group's region table and reduction, under an exact byte budget."""

from __future__ import annotations

import concurrent.futures
from typing import Callable

import numpy as np

from . import producer_kernels as kernels
from .producer_precompute import ActionTable, Geometry
from .producer_reducer import SongBuild, fill_runs, reduce_geometries, threads_for
from .types import FgResponseFrontierResult

_REGION_TABLE_ENTRY_BYTES = 7 * np.dtype(np.int32).itemsize
_Group = list[Geometry]  # the geometries that share a region table (precompute.canonical_groups)
_Results = list[tuple[int, FgResponseFrontierResult]]  # (source, frontier) per geometry


def _executor(workers: int) -> concurrent.futures.ThreadPoolExecutor:
    return concurrent.futures.ThreadPoolExecutor(max_workers=workers, thread_name_prefix="FrontierBuild")


def _region_table(build: SongBuild, table: ActionTable) -> tuple[np.ndarray, ...]:
    song = build.song
    return kernels.region_core_table(
        song.timestamps.shape[0],
        table.action_k.shape[0],
        table.action_k,
        table.raw_fever_fill,
        song.timestamps,
        kernels.HitTimes(
            song.perfect_floor, song.perfect_candidates, song.great_floor, song.great_candidates, song.late_great_floor
        ),
        song.lanes,
    )


def _table_bytes(region_table: tuple[np.ndarray, ...]) -> int:
    return sum(array.nbytes for array in region_table)


def _table_bounds(n: int, table: ActionTable) -> tuple[int, int]:
    """Exact upper bounds of a region table's bytes: while its build holds the candidate arrays and their trimmed
    copies, and after."""
    capacity = kernels.region_core_candidate_capacity(
        n, table.action_k.shape[0], table.action_k, table.raw_fever_fill
    )
    starts_bytes = (n + 2) * np.dtype(np.int64).itemsize
    return starts_bytes + 2 * capacity * _REGION_TABLE_ENTRY_BYTES, starts_bytes + capacity * _REGION_TABLE_ENTRY_BYTES


def _single_table_byte_budget(n: int, groups: list[_Group]) -> int:
    """What the song's live tables may reserve together: the build bytes of one table with a candidate for every
    (section start, action, offset kind)."""
    capacity = (n + 1) * max(group[0].table.action_k.shape[0] for group in groups) * 2
    return (n + 2) * np.dtype(np.int64).itemsize + 2 * capacity * _REGION_TABLE_ENTRY_BYTES


def _reduce_group(
    build: SongBuild,
    group: _Group,
    region_table: tuple[np.ndarray, ...],
    executor: concurrent.futures.ThreadPoolExecutor | None,
    threads: int,
) -> _Results:
    """A group's frontiers: one kernel call, or with several threads up to 256 ranges per thread on `executor`."""
    table = group[0].table
    runs = (*fill_runs(table.later_fill), *fill_runs(table.later_fill[table.later_activation_forced >= 0]))
    if threads <= 1:
        return reduce_geometries(build, group, runs, region_table)
    step = -(-len(group) // (threads * 256))
    futures = [
        executor.submit(reduce_geometries, build, group[start : start + step], runs, region_table)
        for start in range(0, len(group), step)
    ]
    return [result for future in futures for result in future.result()]


def _schedule_parallel(
    build: SongBuild,
    groups: list[_Group],
    table_of: Callable[[_Group], tuple[np.ndarray, ...]],
    bounds: list[tuple[int, int]],
    byte_budget: int,
) -> list[_Results]:
    """Pipeline table builds and reductions, one thread per group in flight, under one exact byte reservation: a build
    reserves its peak bound, and a built table its own bytes until its reduction ends."""
    workers = threads_for(len(groups))
    results: list[_Results | None] = [None] * len(groups)
    building: dict[concurrent.futures.Future, int] = {}
    reducing: dict[concurrent.futures.Future, tuple[int, int]] = {}
    reserved_bytes = 0
    next_group = 0
    with _executor(workers) as build_executor, _executor(workers) as reduce_executor:
        while next_group < len(groups) or building or reducing:
            while next_group < len(groups) and len(building) + len(reducing) < workers:
                if reserved_bytes + bounds[next_group][0] > byte_budget:
                    break
                building[build_executor.submit(table_of, groups[next_group])] = next_group
                reserved_bytes += bounds[next_group][0]
                next_group += 1
            if not building and not reducing:
                raise MemoryError("the region-table pipeline cannot admit its next exact build")
            completed, _pending = concurrent.futures.wait(
                (*building, *reducing), return_when=concurrent.futures.FIRST_COMPLETED
            )
            for future in completed:
                if future in reducing:
                    group_index, table_bytes = reducing.pop(future)
                    results[group_index] = future.result()
                    reserved_bytes -= table_bytes
                    continue
                group_index = building.pop(future)
                region_table = future.result()
                table_bytes = _table_bytes(region_table)
                if table_bytes > bounds[group_index][1]:
                    raise MemoryError("a region table exceeds its exact bound")
                reserved_bytes += table_bytes - bounds[group_index][0]
                reduction = reduce_executor.submit(_reduce_group, build, groups[group_index], region_table, None, 1)
                reducing[reduction] = (group_index, table_bytes)
                del region_table
    return results


def _schedule_sequential(
    build: SongBuild, groups: list[_Group], table_of: Callable[[_Group], tuple[np.ndarray, ...]]
) -> list[_Results]:
    """One group at a time, its geometries on several threads when it has several."""
    threads = max(threads_for(len(group)) for group in groups)
    executor = _executor(threads) if threads > 1 else None
    try:
        return [_reduce_group(build, group, table_of(group), executor, threads_for(len(group))) for group in groups]
    finally:
        if executor is not None:
            executor.shutdown(wait=True)


def schedule_groups(build: SongBuild, groups: list[_Group]) -> list[_Results]:
    """Every group's frontiers, in group order: several groups run in parallel, one group in ranges of its geometries.
    Without forced-Great timing no region run exists and every group reads one contentless table."""
    n = build.song.timestamps.shape[0]
    if build.use_forced_great_timing:
        def table_of(group: _Group) -> tuple[np.ndarray, ...]:
            return _region_table(build, group[0].table)
    else:
        empty_table = (np.zeros(n + 2, dtype=np.int64), *(np.empty(0, dtype=np.int32) for _ in range(7)))

        def table_of(group: _Group) -> tuple[np.ndarray, ...]:
            return empty_table
    if threads_for(len(groups)) <= 1:
        return _schedule_sequential(build, groups, table_of)
    if build.use_forced_great_timing:
        bounds = [_table_bounds(n, group[0].table) for group in groups]
        return _schedule_parallel(build, groups, table_of, bounds, _single_table_byte_budget(n, groups))
    shared = _table_bytes(empty_table)
    return _schedule_parallel(build, groups, table_of, [(shared, shared)] * len(groups), shared * len(groups))
