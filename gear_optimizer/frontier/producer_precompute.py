"""What a song's frontier build derives before its kernels run: the records of its stage values, the fever-end tables of
its fever times, and the geometries that need a kernel run of their own."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import NamedTuple

import numpy as np
from numba import njit


class SongArrays(NamedTuple):
    """One song's per-note arrays in chart order, as producer_batch.song_arrays parses them: contiguous, the times in
    float32 seconds."""

    timestamps: np.ndarray  # the chart times, non-decreasing
    perfect_candidates: np.ndarray  # each note's latest Perfect hit
    great_candidates: np.ndarray  # its latest late-Great hit
    perfect_floor: np.ndarray  # its earliest Perfect hit after every earlier note's (a prefix maximum)
    great_floor: np.ndarray  # its earliest Great hit, likewise
    late_great_floor: np.ndarray  # its earliest late-Great hit
    exit_ceiling: np.ndarray  # the latest cutoff it and every later note can still be hit at or past (a suffix minimum)
    lanes: np.ndarray  # int32


@dataclass(frozen=True, slots=True, eq=False)
class ActionTable:
    """The fever activations of one fill threshold (`raw_fever_fill`, in Perfects) with up to `non_fever_base` forced
    Greats in a section. `action_k` holds every action's forced-Great count. The other arrays hold one row per distinct
    (later, first) pair of activation offsets: the offset in a later section and in the first one, the forced Greats
    of a Perfect activation there (-1: another family prices that placement) and those before a late-Great activation
    (-1: no late Great activates there)."""

    raw_fever_fill: float
    non_fever_base: int
    action_k: np.ndarray
    later_fill: np.ndarray
    first_fill: np.ndarray
    later_forced: np.ndarray
    first_forced: np.ndarray
    later_activation_forced: np.ndarray
    first_activation_forced: np.ndarray

    @property
    def arrays(self) -> tuple[np.ndarray, ...]:
        """The seven arrays, in the kernels' order."""
        return (self.action_k, self.later_fill, self.first_fill, self.later_forced, self.first_forced,
                self.later_activation_forced, self.first_activation_forced)


class Geometry(NamedTuple):
    """One fever geometry of a build: its index in the request, its action table, and its fever time's row in the
    fever-end tables."""

    source: int
    table: ActionTable
    fever_row: int


class FeverEnds(NamedTuple):
    """Where fevers end, per distinct fever time (a row), as note indices: a fever's cutoff is its activation's hit time
    plus the fever time, and its end the first note whose floor lies at or past the cutoff.

    Per activation note, clamped to (activation, n]: the end its latest reachable Perfect / late-Great hit reaches on
    the Perfect floor (`perfect_e`, `late_e`) and on the Great floor (`eg_perfect_e`, `eg_late_e`), and the earliest
    end it can exit at, hit at its earliest (`perfect_exit_e`, `late_exit_e`). `no_exit_e` stands for both exit tables
    at a fill that plans no early exit: every entry is n, so each activation keeps its own latest end. Per hit token
    (producer_kernels._REGION_HIT_*: kind * n + note), unclamped: its end on the Perfect floor and on the Great floor.
    """

    fever_times: np.ndarray
    perfect_e: np.ndarray
    late_e: np.ndarray
    eg_perfect_e: np.ndarray
    eg_late_e: np.ndarray
    perfect_exit_e: np.ndarray
    late_exit_e: np.ndarray
    no_exit_e: np.ndarray
    perfect_floor_by_hit: np.ndarray
    great_floor_by_hit: np.ndarray


@njit(cache=True, nogil=True)
def _ends_at_cutoffs(floor, hits, fever_times, first_end):
    """Per fever time (a row) and hit, the first index whose `floor` is at or past float32(hit + fever time), raised to
    first_end[hit index] where `first_end` is given (empty: as found).

    The fever times ascend, so a hit's cutoff and its end only grow from one row to the next: each search starts at the
    end of the row before and gallops, a few probes where a search of the whole floor takes log n."""
    rows, count, n = fever_times.shape[0], hits.shape[0], floor.shape[0]
    clamped = first_end.shape[0] != 0
    ends = np.empty((rows, count), dtype=np.int32)
    found = np.zeros(count, dtype=np.int64)
    for row in range(rows):
        fever_time = fever_times[row]
        for index in range(count):
            needle = np.float32(hits[index] + fever_time)
            lo = found[index]
            hi = lo
            step = 1
            while hi < n and floor[hi] < needle:
                lo = hi + 1
                hi += step
                step += step
            if hi > n:
                hi = n
            while lo < hi:
                mid = (lo + hi) >> 1
                if floor[mid] < needle:
                    lo = mid + 1
                else:
                    hi = mid
            found[index] = lo
            ends[row, index] = max(lo, first_end[index]) if clamped else lo
    return ends


def fever_ends(song: SongArrays, perfect_hit: np.ndarray, late_hit: np.ndarray, fever_times: np.ndarray) -> FeverEnds:
    """The fever-end tables of the distinct, ascending `fever_times`; `perfect_hit` / `late_hit` hold each activation's
    latest reachable Perfect / late-Great hit. A cutoff is the float32 of the float64 sum, as the kernels form it."""
    n = song.timestamps.shape[0]
    first_end = np.arange(1, n + 1, dtype=np.int64)
    as_found = np.empty(0, dtype=np.int64)
    perfect_floor, late_great_floor = song.perfect_floor.astype(np.float64), song.late_great_floor.astype(np.float64)
    # Every hit an activation can be capped to: a chart time, a latest Perfect or Great, or 1 us before one.
    tokens = np.concatenate((
        song.timestamps, song.perfect_candidates, song.great_candidates,
        song.perfect_candidates.astype(np.float64) - 0.000001, song.great_candidates.astype(np.float64) - 0.000001,
    ))
    perfect_exit_e = _ends_at_cutoffs(song.exit_ceiling, perfect_floor, fever_times, first_end)
    return FeverEnds(
        fever_times=fever_times,
        perfect_e=_ends_at_cutoffs(song.perfect_floor, perfect_hit, fever_times, first_end),
        late_e=_ends_at_cutoffs(song.perfect_floor, late_hit, fever_times, first_end),
        eg_perfect_e=_ends_at_cutoffs(song.great_floor, perfect_hit, fever_times, first_end),
        eg_late_e=_ends_at_cutoffs(song.great_floor, late_hit, fever_times, first_end),
        perfect_exit_e=perfect_exit_e,
        late_exit_e=_ends_at_cutoffs(song.exit_ceiling, late_great_floor, fever_times, first_end),
        no_exit_e=np.full_like(perfect_exit_e, n),
        perfect_floor_by_hit=_ends_at_cutoffs(song.perfect_floor, tokens, fever_times, as_found),
        great_floor_by_hit=_ends_at_cutoffs(song.great_floor, tokens, fever_times, as_found),
    )


def end_classes(ends: FeverEnds, late_great_exits: bool) -> list[int]:
    """Per fever-time row, a number its row shares with the rows whose fevers end alike: at every note's chart time,
    latest Perfect and latest Great on the Perfect floor, at the latter two on the Great floor, and at its earliest
    exits (a late Great's only where Greats are timed: elsewhere none activates)."""
    n = ends.perfect_e.shape[1]
    classes: dict[tuple, int] = {}
    return [
        classes.setdefault(
            (
                ends.perfect_floor_by_hit[row, : 3 * n].tobytes(),
                ends.great_floor_by_hit[row, n : 3 * n].tobytes(),
                ends.perfect_exit_e[row].tobytes(),
                ends.late_exit_e[row].tobytes() if late_great_exits else None,
            ),
            len(classes),
        )
        for row in range(ends.fever_times.shape[0])
    ]


def canonical_groups(
    geometries: list[Geometry], end_class: list[int]
) -> tuple[list[list[Geometry]], dict[int, list[int]]]:
    """The geometries that need a kernel run, in groups that share a region table, and per kept geometry's source the
    sources it stands for (itself first).

    Two geometries build one frontier when their action tables hold the same arrays and their fever times share an end
    class: the first is kept. The region-run cores read a fill only in whole half-units (every fill crossing, region
    offset, k-scan stop, shifted-head test and fill-window check subtracts half-integers from it, which is exact), so
    kept geometries with the same half-unit fill count, non-Fever base and action counts share one table, built for the
    first of them. Groups come in the order of their first geometry and keep their geometries in request order."""
    action_class: dict[ActionTable, int] = {}
    class_of_arrays: dict[tuple[bytes, ...], int] = {}
    kept_source: dict[tuple[int, int], int] = {}
    sources: dict[int, list[int]] = {}
    group_of_table: dict[ActionTable, list[Geometry]] = {}
    groups: dict[tuple[int, int, bytes], list[Geometry]] = {}
    for geometry in geometries:
        table = geometry.table
        if table not in action_class:
            arrays = tuple(array.tobytes() for array in table.arrays)
            action_class[table] = class_of_arrays.setdefault(arrays, len(class_of_arrays))
        kept = kept_source.setdefault((action_class[table], end_class[geometry.fever_row]), geometry.source)
        if kept != geometry.source:
            sources[kept].append(geometry.source)
            continue
        sources[kept] = [kept]
        group = group_of_table.get(table)
        if group is None:
            region_class = (ceil(2.0 * table.raw_fever_fill), table.non_fever_base, table.action_k.tobytes())
            group = group_of_table[table] = groups.setdefault(region_class, [])
        group.append(geometry)
    return list(groups.values()), sources
