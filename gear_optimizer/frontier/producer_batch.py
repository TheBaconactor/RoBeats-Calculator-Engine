"""A song's frontiers: every fever geometry of one song, built in one call from its parsed arrays."""

from __future__ import annotations

from typing import Any, Iterable

import numpy as np

from gear_optimizer.solver.timing_envelope import FRAME_MARGIN_MS

from . import producer_kernels as kernels
from .fill_crossing import late_great_activation_prefix, perfect_crossing_is_region3, perfect_fill_crossing_offset
from .producer_precompute import ActionTable, Geometry, SongArrays, canonical_groups, end_classes, fever_ends
from .producer_reducer import (
    SongBuild,
    WorkspacePlan,
    admit_workspaces,
    early_great_gap_bound,
    pair_mod_bound,
    threads_for,
)
from .producer_scheduler import schedule_groups
from .types import FgResponseFrontierResult


def early_exit_min_fill(perfect_floor_timestamps: np.ndarray, perfect_candidate_timestamps: np.ndarray) -> int:
    """The smallest fill count at which no early fever exit can delay the next activation.

    The search state is a fever's end, not its cutoff, and every note after an early exit is hit at or past the cutoff,
    so an early exit is planned only where the activation `fill` notes past any note has its earliest Perfect two frame
    margins past that note's (and every later note's) latest Perfect: past any cutoff a fever can end there at, its
    conservative separation from the cutoff and next press."""
    floor = perfect_floor_timestamps.astype(np.float64)
    latest = perfect_candidate_timestamps.astype(np.float64)
    reach = np.minimum.accumulate(latest[::-1])[::-1] + 2.0 * FRAME_MARGIN_MS / 1000.0
    n = floor.shape[0]
    lo, hi = 1, max(1, n)
    while lo < hi:  # the condition only gets easier as the fill grows
        mid = (lo + hi) // 2
        if np.all(floor[mid:] >= reach[: n - mid]):
            hi = mid
        else:
            lo = mid + 1
    return lo


def song_arrays(
    timestamps: Any,
    perfect_candidates: Any,
    great_candidates: Any,
    perfect_floor: Any,
    great_floor: Any,
    late_great_floor: Any | None,
    exit_ceiling: Any | None,
    lanes: Any,
) -> SongArrays:
    """Parse one song's per-note arrays, the producer's and the trace's boundary: contiguous float32 times and int32
    lanes of one length, the chart times sorted. A song with no envelopes of its own (Non-Precise, or the Base build's
    Perfect-only song) passes None for the late-Great floor (1 ms past the latest Perfect) and the exit ceiling (the
    suffix minimum of the latest Perfects)."""
    ts = np.ascontiguousarray(np.asarray(timestamps, dtype=np.float32).reshape(-1))
    if np.any(ts[1:] < ts[:-1]):
        raise ValueError("timestamps must be sorted in nondecreasing order")

    def parsed(values: Any, name: str, dtype: type = np.float32) -> np.ndarray:
        array = np.ascontiguousarray(np.asarray(values, dtype=dtype).reshape(-1))
        if array.shape[0] != ts.shape[0]:
            raise ValueError(f"{name} length must match timestamps")
        return array

    perfect = parsed(perfect_candidates, "perfect_candidates")
    return SongArrays(
        timestamps=ts,
        perfect_candidates=perfect,
        great_candidates=parsed(great_candidates, "great_candidates"),
        perfect_floor=parsed(perfect_floor, "perfect_floor"),
        great_floor=parsed(great_floor, "great_floor"),
        late_great_floor=(
            perfect + np.float32(0.001) if late_great_floor is None else parsed(late_great_floor, "late_great_floor")
        ),
        exit_ceiling=(
            np.ascontiguousarray(np.minimum.accumulate(perfect[::-1])[::-1])
            if exit_ceiling is None
            else parsed(exit_ceiling, "exit_ceiling")
        ),
        lanes=parsed(lanes, "lanes", np.int32),
    )


def action_table(*, raw_fever_fill: float, non_fever_base: int, use_forced_great_timing: bool):
    """The fever activations of a fill threshold with k = 0 .. `non_fever_base` forced Greats packed at a section's
    first accumulating note, as five lists: each action's k, its Perfect activation's offset in a later section and in
    the first one, and the forced Greats that fit before it there. Without forced-Great timing only the first k of each
    later-section offset is an action."""
    actions: list[int] = []
    later_fill: list[int] = []
    first_fill: list[int] = []
    later_forced: list[int] = []
    first_forced: list[int] = []
    for k in range(non_fever_base + 1):
        fill = perfect_fill_crossing_offset(raw_fever_fill, k, first=False)
        if use_forced_great_timing or not later_fill or fill != later_fill[-1]:
            fill_first = perfect_fill_crossing_offset(raw_fever_fill, k, first=True)
            actions.append(k)
            later_fill.append(fill)
            first_fill.append(fill_first)
            later_forced.append(min(k, fill))
            first_forced.append(min(k, fill_first))
    return actions, later_fill, first_fill, later_forced, first_forced


def compact_action_table(raw_fever_fill: float, non_fever_base: int, use_forced_great_timing: bool) -> ActionTable:
    """`action_table` as the kernels read it: every action's k, and one row per distinct (later, first) offset pair.

    A row's Perfect activation is its first action's, and only as that action's region-3 crossing (the forced run fits
    before the activation and leaves the bar short of full): its forced count is -1 elsewhere, where the region-run
    family prices the placement. A late Great activates at a row's offset for an action that shares the offset with
    the action before it, when the bar fills on that Great (late_great_activation_prefix); the row keeps the smallest
    such prefix."""
    actions, later_fill, first_fill, later_forced, first_forced = action_table(
        raw_fever_fill=raw_fever_fill, non_fever_base=non_fever_base, use_forced_great_timing=use_forced_great_timing
    )
    rows: dict[tuple[int, int], list[int]] = {}
    for index, k in enumerate(actions):
        later, first = later_fill[index], first_fill[index]
        row = rows.get((later, first))
        if row is None:
            row = rows[(later, first)] = [
                later,
                first,
                later_forced[index] if perfect_crossing_is_region3(later, k, False, raw_fever_fill) else -1,
                first_forced[index] if perfect_crossing_is_region3(first, k, True, raw_fever_fill) else -1,
                -1,
                -1,
            ]
        if index == 0:
            continue
        for column, fills, in_first_section in ((4, later_fill, False), (5, first_fill, True)):
            if fills[index - 1] == fills[index]:
                prefix = late_great_activation_prefix(fills[index], k, in_first_section, raw_fever_fill)
                if prefix is not None:
                    row[column] = prefix if row[column] < 0 else min(row[column], prefix)
    later, first, later_forced_rows, first_forced_rows, later_activation, first_activation = (
        np.ascontiguousarray(column) for column in np.asarray(list(rows.values()), dtype=np.int32).T
    )
    return ActionTable(
        raw_fever_fill=raw_fever_fill,
        non_fever_base=non_fever_base,
        action_k=np.asarray(actions, dtype=np.int32),
        later_fill=later,
        first_fill=first,
        later_forced=later_forced_rows,
        first_forced=first_forced_rows,
        later_activation_forced=later_activation,
        first_activation_forced=first_activation,
    )


def build_frontiers(
    song: SongArrays, geometries: Iterable[tuple[float, int, float]], use_forced_great_timing: bool
) -> tuple[FgResponseFrontierResult, ...]:
    """The frontier of each (raw fever fill, non-Fever base, fever time) geometry of one song, aligned to `geometries`.
    Without forced-Great timing (Non-Precise, Base) no Great is timed: no late Great activates and no region run exists.

    The song's activation-hit tables, the fever-end tables of its distinct fever times and one action table per (fill,
    base) are built once. Geometries that must build one frontier (precompute.canonical_groups) share its result, and
    the region tables and reductions of the others run on the build's threads (scheduler.schedule_groups)."""
    geometries = tuple(geometries)
    if not geometries:
        return ()
    n = song.timestamps.shape[0]
    perfect_hit, perfect_valid, late_hit, late_valid = kernels._numba_build_prefix_activation_hit_tables(
        n, song.timestamps, song.perfect_candidates, song.great_candidates, song.late_great_floor
    )
    fever_times, fever_rows = np.unique(
        np.asarray([fever_time for _fill, _base, fever_time in geometries], dtype=np.float64), return_inverse=True
    )
    ends = fever_ends(song, perfect_hit, late_hit, fever_times)
    tables: dict[tuple[float, int], ActionTable] = {}
    requested: list[Geometry] = []
    for source, ((raw_fever_fill, non_fever_base, _time), fever_row) in enumerate(zip(geometries, fever_rows.tolist())):
        key = (float(raw_fever_fill), int(non_fever_base))
        table = tables.get(key)
        if table is None:
            table = tables[key] = compact_action_table(*key, use_forced_great_timing)
        requested.append(Geometry(source, table, fever_row))
    groups, sources = canonical_groups(requested, end_classes(ends, use_forced_great_timing))

    plan = WorkspacePlan(
        n,
        pair_mod_bound(
            n,
            min(int(table.later_fill[0]) for table in tables.values()),
            early_great_gap_bound(song.perfect_floor, song.great_floor),
        ),
    )
    admit_workspaces(plan, threads_for(max(len(groups), max(len(group) for group in groups))))
    build = SongBuild(
        song=song,
        activation_hits=(perfect_hit, perfect_valid, late_hit, late_valid),
        ends=ends,
        use_forced_great_timing=use_forced_great_timing,
        early_exit_min_fill=early_exit_min_fill(song.perfect_floor, song.perfect_candidates),
        workspace_plan=plan,
    )
    frontiers: list[FgResponseFrontierResult | None] = [None] * len(geometries)
    for results in schedule_groups(build, groups):
        for source, frontier in results:
            for duplicate in sources[source]:
                frontiers[duplicate] = frontier
    return tuple(frontiers)
