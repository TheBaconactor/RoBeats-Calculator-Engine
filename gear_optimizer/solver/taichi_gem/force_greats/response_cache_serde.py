from __future__ import annotations

from typing import Any

import numpy as np

from .response_build_gpu_surfaces import SurfaceRowsFirstFrontier, _surface_rows_from_numba_rows
from .response_cache_keys import (
    _surface_from_row_cached,
    fg_response_frontier_geometry_cache_key,
)
from .response_cache_store import (
    _frontier_is_complete,
    _load_bundle_array_members,
    _memory_get,
    _memory_put,
)
from .response_cache_types import (
    FgResponseFrontierScoringBundle,
    _normalize_stat_key,
)
from .response_types import FgResponseFrontierResult, FgResponseSurface


def _write_surface_row(rows: np.ndarray, idx: int, surface: FgResponseSurface) -> None:
    rows[int(idx), 0] = int(surface.fever0)
    rows[int(idx), 1] = int(surface.fever1)
    rows[int(idx), 2] = int(surface.fever2)
    rows[int(idx), 3] = int(surface.fever3)
    rows[int(idx), 4] = int(surface.great0)
    rows[int(idx), 5] = int(surface.great1)
    rows[int(idx), 6] = int(surface.great2)
    rows[int(idx), 7] = int(surface.great3)
    rows[int(idx), 8] = int(surface.body_fever)
    rows[int(idx), 9] = int(surface.body_great)
    rows[int(idx), 10] = int(surface.body_fever_great)


def _pack_frontiers(frontiers: tuple[FgResponseFrontierResult, ...]) -> dict[str, np.ndarray]:
    meta = np.empty((len(frontiers), 7), dtype=np.int32)
    first_offsets = np.empty((len(frontiers),), dtype=np.int32)
    first_counts = np.empty((len(frontiers),), dtype=np.int32)
    row_backed_total = sum(
        len(frontier.first_frontier)
        for frontier in frontiers
        if isinstance(frontier.first_frontier, SurfaceRowsFirstFrontier)
    )
    first_surface_pool = np.empty((sum(len(frontier.first_frontier) for frontier in frontiers), 11), dtype=np.uint32)
    first_numba_pool = np.empty((int(row_backed_total), 7), dtype=np.uint64)
    row_backed_ranges: list[tuple[int, int, int]] = []
    first_cursor = 0
    first_numba_cursor = 0

    for idx, frontier in enumerate(frontiers):
        meta[idx] = np.asarray(
            [
                int(frontier.states_evaluated),
                int(frontier.actions),
                int(frontier.transitions_evaluated),
                int(frontier.generated_surfaces),
                int(frontier.retained_surfaces_total),
                int(frontier.max_state_frontier),
                int(frontier.non_fever_base),
            ],
            dtype=np.int32,
        )
        first_offsets[idx] = int(first_cursor)
        first_counts[idx] = len(frontier.first_frontier)
        if isinstance(frontier.first_frontier, SurfaceRowsFirstFrontier):
            first_rows = frontier.first_frontier.numba_rows()
            first_count = int(first_rows.shape[0])
            start = int(first_cursor)
            numba_start = int(first_numba_cursor)
            first_numba_pool[numba_start : numba_start + first_count] = first_rows
            row_backed_ranges.append((start, numba_start, first_count))
            first_cursor += first_count
            first_numba_cursor += first_count
        else:
            for surface in frontier.first_frontier:
                _write_surface_row(first_surface_pool, int(first_cursor), surface)
                first_cursor += 1

    if row_backed_ranges:
        converted = _surface_rows_from_numba_rows(first_numba_pool)
        for first_start, numba_start, count in row_backed_ranges:
            first_surface_pool[int(first_start) : int(first_start) + int(count)] = converted[
                int(numba_start) : int(numba_start) + int(count)
            ]

    return {
        "frontier_meta": meta,
        "first_offsets": first_offsets,
        "first_counts": first_counts,
        "first_surface_pool": first_surface_pool,
    }


def _unpack_frontiers(data: object) -> tuple[FgResponseFrontierResult, ...]:
    meta = np.asarray(data["frontier_meta"], dtype=np.int32)
    first_offsets = np.asarray(data["first_offsets"], dtype=np.int32)
    first_counts = np.asarray(data["first_counts"], dtype=np.int32)
    first_pool = np.asarray(data["first_surface_pool"], dtype=np.uint32)

    out: list[FgResponseFrontierResult] = []
    surface_cache: dict[tuple[int, ...], FgResponseSurface] = {}
    for idx in range(int(meta.shape[0])):
        first_start = int(first_offsets[idx])
        first_count = int(first_counts[idx])
        first_frontier = tuple(
            _surface_from_row_cached(first_pool[row_idx], surface_cache)
            for row_idx in range(first_start, first_start + first_count)
        )
        row = meta[idx]
        out.append(
            FgResponseFrontierResult(
                first_frontier=first_frontier,
                state_frontiers={},
                states_evaluated=int(row[0]),
                actions=int(row[1]),
                transitions_evaluated=int(row[2]),
                generated_surfaces=int(row[3]),
                retained_surfaces_total=int(row[4]),
                max_state_frontier=int(row[5]),
                non_fever_base=int(row[6]),
                seconds=0.0,
            )
        )
    return tuple(out)


class _LazyResponseFirstFrontier:
    __slots__ = ("_bundle_key", "_first_start", "_first_count", "_materialized", "_surface_cache")

    def __init__(self, *, bundle_key: tuple, first_start: int, first_count: int) -> None:
        self._bundle_key = bundle_key
        self._first_start = int(first_start)
        self._first_count = int(first_count)
        self._materialized: tuple[FgResponseSurface, ...] | None = None
        self._surface_cache: dict[tuple[int, ...], FgResponseSurface] = {}

    def _as_tuple(self) -> tuple[FgResponseSurface, ...]:
        materialized = self._materialized
        if materialized is None:
            arrays = _load_bundle_array_members(self._bundle_key, names=("first_surface_pool",))
            first_pool = np.asarray(arrays["first_surface_pool"], dtype=np.uint32)
            materialized = tuple(
                _surface_from_row_cached(first_pool[row_idx], self._surface_cache)
                for row_idx in range(self._first_start, self._first_start + self._first_count)
            )
            self._materialized = materialized
        return materialized

    def __bool__(self) -> bool:
        return int(self._first_count) > 0

    def __len__(self) -> int:
        return int(self._first_count)

    def __iter__(self):
        return iter(self._as_tuple())

    def __getitem__(self, idx: int) -> FgResponseSurface:
        return self._as_tuple()[int(idx)]

    def __eq__(self, other: object) -> bool:
        try:
            return self._as_tuple() == tuple(other)  # type: ignore[arg-type]
        except TypeError:
            return self._as_tuple() == other


def frontier_result_from_scoring_bundle(
    scoring_bundle: FgResponseFrontierScoringBundle,
    *,
    frontier_idx: int,
) -> FgResponseFrontierResult:
    idx = int(frontier_idx)
    meta = np.asarray(scoring_bundle.frontier_meta, dtype=np.int32)
    if idx < 0 or idx >= int(meta.shape[0]):
        raise ValueError("FG response scoring bundle frontier index is outside the bundle")
    first_start = int(scoring_bundle.frontier_offsets[idx])
    first_count = int(scoring_bundle.frontier_lengths[idx])
    row = meta[idx]
    return FgResponseFrontierResult(
        first_frontier=_LazyResponseFirstFrontier(
            bundle_key=scoring_bundle.cache_key,
            first_start=int(first_start),
            first_count=int(first_count),
        ),
        state_frontiers={},
        states_evaluated=int(row[0]),
        actions=int(row[1]),
        transitions_evaluated=int(row[2]),
        generated_surfaces=int(row[3]),
        retained_surfaces_total=int(row[4]),
        max_state_frontier=int(row[5]),
        non_fever_base=int(row[6]),
        seconds=0.0,
    )


def frontier_result_from_scoring_bundle_for_stats(
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    scoring_bundle: FgResponseFrontierScoringBundle,
    *,
    ft_stat: int,
    ff_stat: int,
) -> FgResponseFrontierResult:
    key = _normalize_stat_key((int(ft_stat), int(ff_stat)))
    geometry_cache_key = fg_response_frontier_geometry_cache_key(
        calc_song,
        ref_arrays,
        ft_stat=int(key[0]),
        ff_stat=int(key[1]),
    )
    cached = _memory_get(geometry_cache_key)
    if _frontier_is_complete(cached):
        return cached
    frontier_idx = scoring_bundle.frontier_idx_by_key.get(key)
    if frontier_idx is None:
        raise ValueError(f"FG response frontier scoring bundle is missing stat key: {key}")
    frontier = frontier_result_from_scoring_bundle(scoring_bundle, frontier_idx=int(frontier_idx))
    _memory_put(geometry_cache_key, frontier)
    return frontier
