"""The bytes of an FG bundle file: its arrays, in the order they are written, and the byte-plane form of its two surface
tables (fg_cache_store has the format). A logic change here rotates the FG cache version."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import numpy as np
from numpy.lib import format as np_format

from .fg_cache_patterns import intern_surface_row_words, pack_surface_patterns, surface_head_coeffs
from .fg_cache_types import FgResponseFrontierCachePayload
from .producer_surfaces import SurfaceRowsFirstFrontier, surface_rows_from_numba_rows
from .types import FgResponseFrontierResult

_NPZ_FAST_COMPRESS_LEVEL = 1


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


def pack_frontiers(frontiers: tuple[FgResponseFrontierResult, ...]) -> dict[str, np.ndarray]:
    meta = np.asarray(
        [
            (f.states_evaluated, f.actions, f.transitions_evaluated, f.generated_surfaces, f.retained_surfaces_total,
             f.max_state_frontier, f.non_fever_base)
            for f in frontiers
        ],
        dtype=np.int32,
    )
    first_counts = np.asarray([len(f.first_frontier) for f in frontiers], dtype=np.int32)
    unique_frontier_indices, segment_id_by_frontier = _frontier_segment_ids(frontiers)
    segment_counts = first_counts[unique_frontier_indices]
    segment_offsets = np.cumsum(segment_counts, dtype=np.int64) - segment_counts
    first_surface_pool = np.empty((segment_counts.sum(), 11), dtype=np.uint32)
    for frontier_idx, offset, count in zip(unique_frontier_indices, segment_offsets.tolist(), segment_counts.tolist()):
        # Each segment converts straight into its pool slice: an all-rows uint64 staging pool doubled peak RSS on
        # multi-million-row bundles.
        surface_rows_from_numba_rows(frontiers[frontier_idx].first_frontier.numba_rows(),
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


def unpack_frontiers(arrays: dict[str, np.ndarray]) -> tuple[FgResponseFrontierResult, ...]:
    """The frontiers of a bundle file's arrays (store.read_compatible_bundle). Frontiers share packed pool segments, so
    each distinct (offset, count) is expanded once."""
    meta = arrays["frontier_meta"].tolist()
    segments: dict[tuple[int, int], SurfaceRowsFirstFrontier] = {}
    out: list[FgResponseFrontierResult] = []
    offsets, counts = arrays["first_offsets"].tolist(), arrays["first_counts"].tolist()
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
                states_evaluated=row[0],
                actions=row[1],
                transitions_evaluated=row[2],
                generated_surfaces=row[3],
                retained_surfaces_total=row[4],
                max_state_frontier=row[5],
                non_fever_base=row[6],
            )
        )
    return tuple(out)


def byte_planes(table: np.ndarray) -> np.ndarray:
    """(n, k) uint32 -> (4k, n) uint8: plane 4j + b holds byte b of column j."""
    n, k = table.shape
    columns = np.ascontiguousarray(table.T, dtype="<u4")
    return np.ascontiguousarray(columns.view(np.uint8).reshape(k, n, 4).transpose(0, 2, 1)).reshape(4 * k, n)


def byte_plane_columns(planes: np.ndarray) -> np.ndarray:
    """(4k, n) uint8 byte planes -> the table's (k, n) uint32 columns."""
    k4, n = planes.shape
    return np.ascontiguousarray(planes.reshape(k4 // 4, 4, n).transpose(0, 2, 1)).view("<u4").reshape(k4 // 4, n)


def bundle_arrays(payload: FgResponseFrontierCachePayload, version: str) -> dict[str, np.ndarray]:
    """The arrays of the payload's bundle file written by `version`, in file order."""
    frontiers = payload.frontiers
    frontier_id_by_object = {id(frontier): idx for idx, frontier in enumerate(frontiers)}
    sorted_items = sorted(payload.frontier_by_key.items())
    packed_frontiers = pack_frontiers(frontiers)
    head_len = min(payload.total_notes, 100)
    # Pattern identity is established from every exact mask word before coefficient work: head coefficients depend
    # only on those words and head_len, so they are computed once per pattern instead of once per row.
    rows, pattern_words = intern_surface_row_words(packed_frontiers["first_surface_pool"])
    patterns = pack_surface_patterns(pattern_words, surface_head_coeffs(pattern_words, head_len=head_len))
    return {
        "version": np.asarray(version),
        "stat_keys": np.asfortranarray(np.asarray([key for key, _frontier in sorted_items], dtype=np.uint8)),
        "frontier_ids": np.asarray(
            [frontier_id_by_object[id(frontier)] for _key, frontier in sorted_items], dtype=np.int32
        ),
        "raw_fill_by_ff": np.asarray(payload.raw_fill_by_ff, dtype=np.float64),
        "non_fever_base_by_ff": np.asarray(payload.non_fever_base_by_ff, dtype=np.int32),
        "real_time_by_ft": np.asarray(payload.real_time_by_ft, dtype=np.float64),
        "total_notes": np.asarray(payload.total_notes, dtype=np.int32),
        "long_notes": np.asarray(payload.long_notes, dtype=np.int32),
        "use_forced_great_timing": np.asarray(payload.use_forced_great_timing, dtype=np.int8),
        "first_surface_head_len": np.asarray(head_len, dtype=np.uint8),
        "frontier_meta": np.asfortranarray(packed_frontiers["frontier_meta"]),
        "first_offsets": packed_frontiers["first_offsets"],
        "first_counts": packed_frontiers["first_counts"],
        "surface_rows": byte_planes(rows),
        "surface_patterns": byte_planes(patterns),
    }


def write_bundle_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    """The arrays as an .npz archive, each member deflated at level 1 in dict order."""
    with zipfile.ZipFile(
        path, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=_NPZ_FAST_COMPRESS_LEVEL, allowZip64=True
    ) as archive:
        for name, array in arrays.items():
            with archive.open(f"{name}.npy", mode="w", force_zip64=True) as handle:
                np_format.write_array(handle, array, allow_pickle=False)
