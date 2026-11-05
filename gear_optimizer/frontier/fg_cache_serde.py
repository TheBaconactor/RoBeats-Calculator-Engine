from __future__ import annotations

import hashlib

import numpy as np

from .producer_surfaces import SurfaceRowsFirstFrontier, _surface_rows_from_numba_rows
from .types import FgResponseFrontierResult


def _frontier_segment_ids(frontiers: tuple[FgResponseFrontierResult, ...]) -> tuple[list[int], np.ndarray]:
    """The frontiers with distinct rows (their indices) and each frontier's position among them: equal rows are one pool
    segment."""
    unique_frontier_indices: list[int] = []
    segment_id_by_frontier = np.empty((len(frontiers),), dtype=np.int32)
    by_digest: dict[tuple[int, bytes], list[int]] = {}
    for idx, frontier in enumerate(frontiers):
        rows = frontier.first_frontier.numba_rows()
        digest = (int(rows.shape[0]), hashlib.blake2b(rows.view(np.uint8), digest_size=16).digest())
        segment_id = -1
        for candidate in by_digest.get(digest, ()):
            if np.array_equal(rows, frontiers[unique_frontier_indices[candidate]].first_frontier.numba_rows()):
                segment_id = candidate
                break
        if segment_id < 0:
            segment_id = len(unique_frontier_indices)
            unique_frontier_indices.append(idx)
            by_digest.setdefault(digest, []).append(segment_id)
        segment_id_by_frontier[idx] = segment_id
    return unique_frontier_indices, segment_id_by_frontier


def _pack_frontiers(frontiers: tuple[FgResponseFrontierResult, ...]) -> dict[str, np.ndarray]:
    meta = np.asarray(
        [
            (f.states_evaluated, f.actions, f.transitions_evaluated, f.generated_surfaces, f.retained_surfaces_total,
             f.max_state_frontier, f.non_fever_base)
            for f in frontiers
        ],
        dtype=np.int32,
    ).reshape(-1, 7)
    first_counts = np.asarray([len(f.first_frontier) for f in frontiers], dtype=np.int32)
    unique_frontier_indices, segment_id_by_frontier = _frontier_segment_ids(frontiers)
    segment_counts = first_counts[unique_frontier_indices]
    segment_offsets = np.cumsum(segment_counts, dtype=np.int64) - segment_counts
    first_surface_pool = np.empty((int(segment_counts.sum()), 11), dtype=np.uint32)
    for frontier_idx, offset, count in zip(unique_frontier_indices, segment_offsets.tolist(), segment_counts.tolist()):
        # Each segment converts straight into its pool slice: an all-rows uint64 staging pool doubled peak RSS on
        # multi-million-row bundles.
        _surface_rows_from_numba_rows(frontiers[frontier_idx].first_frontier.numba_rows(),
                                      out=first_surface_pool[offset : offset + count])
    return {
        "frontier_meta": meta,
        "first_offsets": segment_offsets[segment_id_by_frontier].astype(np.int32),
        "first_counts": first_counts,
        "first_surface_pool": first_surface_pool,
    }


def _segment_rows(rows: np.ndarray, patterns: np.ndarray, start: int, stop: int) -> np.ndarray:
    """Rows start..stop of a bundle's (4, n) surface rows as the producer's (m, 7) uint64 rows."""
    segment = rows[:, start:stop]
    words = patterns[:8, segment[0]].T.astype(np.uint64)
    out = np.empty((stop - start, 7), dtype=np.uint64)
    out[:, :4] = words[:, 0::2] | (words[:, 1::2] << np.uint64(32))
    out[:, 4:7] = segment[1:4].T
    return out


def _unpack_frontiers(arrays: dict[str, np.ndarray]) -> tuple[FgResponseFrontierResult, ...]:
    """The frontiers of a bundle file's arrays (store.read_compatible_bundle). Frontiers share packed pool segments, so
    each distinct (offset, count) is expanded once."""
    meta = np.asarray(arrays["frontier_meta"], dtype=np.int32).tolist()
    segments: dict[tuple[int, int], SurfaceRowsFirstFrontier] = {}
    out: list[FgResponseFrontierResult] = []
    offsets, counts = np.asarray(arrays["first_offsets"]).tolist(), np.asarray(arrays["first_counts"]).tolist()
    for row, start, count in zip(meta, offsets, counts, strict=True):
        first_frontier = segments.get((start, count))
        if first_frontier is None:
            first_frontier = SurfaceRowsFirstFrontier(
                _segment_rows(arrays["surface_rows"], arrays["surface_patterns"], start, start + count)
            )
            segments[(start, count)] = first_frontier
        out.append(
            FgResponseFrontierResult(
                first_frontier=first_frontier,
                state_frontiers={},
                states_evaluated=row[0],
                actions=row[1],
                transitions_evaluated=row[2],
                generated_surfaces=row[3],
                retained_surfaces_total=row[4],
                max_state_frontier=row[5],
                non_fever_base=row[6],
                seconds=0.0,
            )
        )
    return tuple(out)
