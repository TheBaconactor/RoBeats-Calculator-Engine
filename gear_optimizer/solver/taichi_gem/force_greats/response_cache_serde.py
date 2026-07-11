from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np

from .response_build_gpu_surfaces import SurfaceRowsFirstFrontier, _surface_rows_from_numba_rows
from .response_cache_keys import (
    _surface_from_row_cached,
    _surface_from_values_cached,
    fg_response_frontier_geometry_cache_key,
)
from .response_cache_store import (
    _frontier_is_complete,
    _open_surface_sidecar_memmap,
    load_first_surface_scoring_rows,
    _memory_get,
    _memory_put,
)
from .response_cache_patterns import SURFACE_PATTERN_COLUMNS, SURFACE_ROW_COLUMNS, expand_surface_rows
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


def _surface_rows_from_frontier(frontier: FgResponseFrontierResult) -> np.ndarray:
    first_frontier = frontier.first_frontier
    if isinstance(first_frontier, SurfaceRowsFirstFrontier):
        return np.ascontiguousarray(first_frontier.surface_rows(), dtype=np.uint32)
    rows = np.empty((len(first_frontier), 11), dtype=np.uint32)
    for idx, surface in enumerate(first_frontier):
        _write_surface_row(rows, int(idx), surface)
    return rows


def _frontier_segment_fingerprint(frontier: FgResponseFrontierResult) -> tuple[int, int, bytes]:
    first_frontier = frontier.first_frontier
    if isinstance(first_frontier, SurfaceRowsFirstFrontier):
        rows = np.ascontiguousarray(first_frontier.numba_rows(), dtype=np.uint64)
        layout = 7
    else:
        rows = _surface_rows_from_frontier(frontier)
        layout = 11
    digest = hashlib.blake2b(rows.view(np.uint8), digest_size=16).digest()
    return int(layout), int(rows.shape[0]), bytes(digest)


def _frontier_segment_equal(left: FgResponseFrontierResult, right: FgResponseFrontierResult) -> bool:
    left_first = left.first_frontier
    right_first = right.first_frontier
    if isinstance(left_first, SurfaceRowsFirstFrontier) and isinstance(right_first, SurfaceRowsFirstFrontier):
        return bool(np.array_equal(left_first.numba_rows(), right_first.numba_rows()))
    return bool(np.array_equal(_surface_rows_from_frontier(left), _surface_rows_from_frontier(right)))


def _frontier_segment_ids(frontiers: tuple[FgResponseFrontierResult, ...]) -> tuple[list[int], np.ndarray]:
    unique_frontier_indices: list[int] = []
    segment_id_by_frontier = np.empty((len(frontiers),), dtype=np.int32)
    by_fingerprint: dict[tuple[int, int, bytes], list[int]] = {}
    for idx, frontier in enumerate(frontiers):
        fingerprint = _frontier_segment_fingerprint(frontier)
        segment_id = -1
        for candidate_segment_id in by_fingerprint.get(fingerprint, ()):
            candidate_idx = unique_frontier_indices[int(candidate_segment_id)]
            if _frontier_segment_equal(frontier, frontiers[int(candidate_idx)]):
                segment_id = int(candidate_segment_id)
                break
        if segment_id < 0:
            segment_id = len(unique_frontier_indices)
            unique_frontier_indices.append(int(idx))
            by_fingerprint.setdefault(fingerprint, []).append(int(segment_id))
        segment_id_by_frontier[int(idx)] = int(segment_id)
    return unique_frontier_indices, segment_id_by_frontier


def _pack_frontiers(frontiers: tuple[FgResponseFrontierResult, ...]) -> dict[str, np.ndarray]:
    meta = np.empty((len(frontiers), 7), dtype=np.int32)
    first_offsets = np.empty((len(frontiers),), dtype=np.int32)
    first_counts = np.empty((len(frontiers),), dtype=np.int32)
    unique_frontier_indices, segment_id_by_frontier = _frontier_segment_ids(frontiers)
    first_surface_pool = np.empty(
        (sum(len(frontiers[int(frontier_idx)].first_frontier) for frontier_idx in unique_frontier_indices), 11),
        dtype=np.uint32,
    )
    segment_offsets = np.empty((len(unique_frontier_indices),), dtype=np.int32)
    first_cursor = 0

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
        first_counts[idx] = len(frontier.first_frontier)

    for segment_id, frontier_idx in enumerate(unique_frontier_indices):
        frontier = frontiers[int(frontier_idx)]
        segment_offsets[int(segment_id)] = int(first_cursor)
        if isinstance(frontier.first_frontier, SurfaceRowsFirstFrontier):
            first_rows = frontier.first_frontier.numba_rows()
            first_count = int(first_rows.shape[0])
            # Convert each row-backed segment straight into its pool slice: staging every
            # row-backed segment into an all-rows uint64 pool plus a second all-rows converted
            # copy doubled peak RSS on multi-million-row bundles (~2.3 GB extra on a 23M-row
            # chart) for no output difference.
            _surface_rows_from_numba_rows(
                first_rows,
                out=first_surface_pool[int(first_cursor) : int(first_cursor) + first_count],
            )
            first_cursor += first_count
        else:
            for surface in frontier.first_frontier:
                _write_surface_row(first_surface_pool, int(first_cursor), surface)
                first_cursor += 1

    for idx in range(len(frontiers)):
        first_offsets[int(idx)] = int(segment_offsets[int(segment_id_by_frontier[int(idx)])])

    return {
        "frontier_meta": meta,
        "first_offsets": first_offsets,
        "first_counts": first_counts,
        "first_surface_pool": first_surface_pool,
    }


def _unpack_frontiers(
    data: object,
    *,
    row_sidecar: Path,
    pattern_sidecar: Path,
) -> tuple[FgResponseFrontierResult, ...]:
    meta = np.asarray(data["frontier_meta"], dtype=np.int32)
    first_offsets = np.asarray(data["first_offsets"], dtype=np.int32)
    first_counts = np.asarray(data["first_counts"], dtype=np.int32)
    surface_row_count = int(np.asarray(data["first_surface_row_count"]).item())
    surface_pattern_count = int(np.asarray(data["first_surface_pattern_count"]).item())
    # Materialize the same exact logical rows the scoring path sees. Long-lived surface tuples
    # never alias either read-only memmap.
    row_memmap = _open_surface_sidecar_memmap(
        row_sidecar,
        columns=SURFACE_ROW_COLUMNS,
        dtype=np.dtype(np.uint32),
        row_count=surface_row_count,
    )
    pattern_memmap = _open_surface_sidecar_memmap(
        pattern_sidecar,
        columns=SURFACE_PATTERN_COLUMNS,
        dtype=np.dtype(np.uint32),
        row_count=surface_pattern_count,
    )
    first_pool, _first_coeffs = expand_surface_rows(row_memmap, pattern_memmap)

    out: list[FgResponseFrontierResult] = []
    surface_cache: dict[tuple[int, ...], FgResponseSurface] = {}
    # Frontiers share packed pool segments (pack-time dedup), so materialize each unique
    # (offset, count) segment once and alias the immutable tuple across its frontiers.
    # tolist() converts a whole segment to plain ints in one C pass -- the per-row
    # int()-boxing generator was the dominant unpack cost on multi-million-row pools.
    segment_cache: dict[tuple[int, int], tuple[FgResponseSurface, ...]] = {}
    for idx in range(int(meta.shape[0])):
        first_start = int(first_offsets[idx])
        first_count = int(first_counts[idx])
        segment_key = (first_start, first_count)
        first_frontier = segment_cache.get(segment_key)
        if first_frontier is None:
            first_frontier = tuple(
                _surface_from_values_cached(tuple(values), surface_cache)
                for values in first_pool[first_start : first_start + first_count].tolist()
            )
            segment_cache[segment_key] = first_frontier
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
            first_pool, _coeffs = load_first_surface_scoring_rows(
                self._bundle_key,
                ((int(self._first_start), int(self._first_count)),),
            )
            materialized = tuple(
                _surface_from_row_cached(first_pool[row_idx], self._surface_cache)
                for row_idx in range(int(first_pool.shape[0]))
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
    pattern_ids = np.asarray(scoring_bundle.surface_pattern_ids)
    if int(pattern_ids.shape[0]) > 0:
        # In-memory bundle (e.g. session-box pruned): its offsets index the IN-MEMORY arrays, not
        # the disk sidecar -- serve the frontier eagerly from them. The disk-lazy path below would
        # silently read the wrong rows for a compacted bundle.
        pattern_words = np.asarray(scoring_bundle.surface_pattern_words)
        counts = np.asarray(scoring_bundle.surface_counts)
        segment_ids = np.asarray(pattern_ids[first_start : first_start + first_count], dtype=np.int64)
        if bool(np.any(segment_ids < 0)) or bool(np.any(segment_ids >= int(pattern_words.shape[0]))):
            raise ValueError("FG response scoring bundle references an invalid head-pattern ID")
        segment_words = pattern_words[segment_ids]
        segment_counts = counts[first_start : first_start + first_count]
        rows7 = np.empty((int(first_count), 7), dtype=np.uint64)
        rows7[:, 0] = segment_words[:, 0].astype(np.uint64) | (segment_words[:, 1].astype(np.uint64) << np.uint64(32))
        rows7[:, 1] = segment_words[:, 2].astype(np.uint64) | (segment_words[:, 3].astype(np.uint64) << np.uint64(32))
        rows7[:, 2] = segment_words[:, 4].astype(np.uint64) | (segment_words[:, 5].astype(np.uint64) << np.uint64(32))
        rows7[:, 3] = segment_words[:, 6].astype(np.uint64) | (segment_words[:, 7].astype(np.uint64) << np.uint64(32))
        rows7[:, 4:7] = segment_counts.astype(np.uint64)
        first_frontier = SurfaceRowsFirstFrontier(rows7)
    else:
        first_frontier = _LazyResponseFirstFrontier(
            bundle_key=scoring_bundle.cache_key,
            first_start=int(first_start),
            first_count=int(first_count),
        )
    return FgResponseFrontierResult(
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
