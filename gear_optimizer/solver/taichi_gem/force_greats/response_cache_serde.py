from __future__ import annotations

import hashlib

import numpy as np

from gear_optimizer.solver.timing_envelope import TimedSong
from gear_optimizer.gamedata import StatCurves
from .response_build_gpu_surfaces import SurfaceRowsFirstFrontier, _surface_rows_from_numba_rows
from .response_cache_keys import (
    _surface_from_values_cached,
    fg_response_frontier_geometry_cache_key,
)
from .response_cache_store import (
    _frontier_is_complete,
    _memory_get,
    _memory_put,
)
from .response_cache_patterns import expand_surface_rows
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


def _unpack_frontiers(arrays: dict[str, np.ndarray]) -> tuple[FgResponseFrontierResult, ...]:
    """The frontiers of a bundle file's arrays (store.read_compatible_bundle), as the exact logical rows the scoring
    path sees."""
    meta = np.asarray(arrays["frontier_meta"], dtype=np.int32)
    first_offsets = np.asarray(arrays["first_offsets"], dtype=np.int32)
    first_counts = np.asarray(arrays["first_counts"], dtype=np.int32)
    first_pool, _first_coeffs = expand_surface_rows(arrays["surface_rows"].T, arrays["surface_patterns"].T)

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
    first_end = first_start + int(scoring_bundle.frontier_lengths[idx])
    if int(scoring_bundle.surface_pattern_ids.shape[0]) > 0:
        # An in-memory pool (a session-pruned bundle): the offsets index the pool.
        segment_words = scoring_bundle.surface_pattern_words[scoring_bundle.surface_pattern_ids[first_start:first_end]]
        segment_counts = scoring_bundle.surface_counts[first_start:first_end]
    else:
        rows = scoring_bundle.surface_rows[:, first_start:first_end]
        segment_words = scoring_bundle.surface_patterns[:8, rows[0]].T
        segment_counts = rows[1:4].T
    rows7 = np.empty((first_end - first_start, 7), dtype=np.uint64)
    for column in range(4):
        rows7[:, column] = segment_words[:, 2 * column].astype(np.uint64) | (
            segment_words[:, 2 * column + 1].astype(np.uint64) << np.uint64(32)
        )
    rows7[:, 4:7] = segment_counts.astype(np.uint64)
    row = meta[idx]
    return FgResponseFrontierResult(
        first_frontier=SurfaceRowsFirstFrontier(rows7),
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
    song: TimedSong,
    curves: StatCurves,
    scoring_bundle: FgResponseFrontierScoringBundle,
    *,
    ft_stat: int,
    ff_stat: int,
) -> FgResponseFrontierResult:
    key = _normalize_stat_key((int(ft_stat), int(ff_stat)))
    geometry_cache_key = fg_response_frontier_geometry_cache_key(
        song,
        curves,
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
