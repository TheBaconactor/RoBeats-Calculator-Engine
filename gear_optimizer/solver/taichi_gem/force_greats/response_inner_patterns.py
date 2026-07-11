from __future__ import annotations

import numpy as np

from gear_optimizer.core.jit_setup import jit


@jit(nopython=True, cache=True)
def _build_response_group_pattern_plan_jit(
    surface_pattern_ids: np.ndarray,
    group_offsets: np.ndarray,
    group_lengths: np.ndarray,
    pattern_count: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    group_count = int(group_offsets.shape[0])
    total_rows = 0
    pair_count = 0
    stamps = np.zeros(max(1, int(pattern_count)), dtype=np.int32)

    for owner in range(group_count):
        stamp = int(owner) + 1
        start = int(group_offsets[owner])
        length = int(group_lengths[owner])
        total_rows += int(length)
        for local_surface in range(length):
            pattern_id = int(surface_pattern_ids[int(start) + int(local_surface)])
            if int(stamps[pattern_id]) != int(stamp):
                stamps[pattern_id] = np.int32(stamp)
                pair_count += 1

    pair_owners = np.empty(int(pair_count), dtype=np.int32)
    pair_pattern_ids = np.empty(int(pair_count), dtype=np.int32)
    pair_counts = np.zeros(int(pair_count), dtype=np.int32)
    pair_by_pattern = np.empty(max(1, int(pattern_count)), dtype=np.int32)
    stamps.fill(0)
    pair_cursor = 0

    for owner in range(group_count):
        stamp = int(owner) + 1
        start = int(group_offsets[owner])
        length = int(group_lengths[owner])
        for local_surface in range(length):
            pattern_id = int(surface_pattern_ids[int(start) + int(local_surface)])
            if int(stamps[pattern_id]) != int(stamp):
                stamps[pattern_id] = np.int32(stamp)
                pair_by_pattern[pattern_id] = np.int32(pair_cursor)
                pair_owners[pair_cursor] = np.int32(owner)
                pair_pattern_ids[pair_cursor] = np.int32(pattern_id)
                pair_cursor += 1
            pair_idx = int(pair_by_pattern[pattern_id])
            pair_counts[pair_idx] += np.int32(1)

    pair_offsets = np.empty(int(pair_count) + 1, dtype=np.int64)
    pair_offsets[0] = np.int64(0)
    for pair_idx in range(int(pair_count)):
        pair_offsets[int(pair_idx) + 1] = pair_offsets[int(pair_idx)] + np.int64(
            pair_counts[int(pair_idx)]
        )

    local_surfaces = np.empty(int(total_rows), dtype=np.int32)
    write_cursors = pair_offsets[:-1].copy()
    stamps.fill(0)
    pair_cursor = 0
    for owner in range(group_count):
        stamp = int(owner) + 1
        start = int(group_offsets[owner])
        length = int(group_lengths[owner])
        for local_surface in range(length):
            pattern_id = int(surface_pattern_ids[int(start) + int(local_surface)])
            if int(stamps[pattern_id]) != int(stamp):
                stamps[pattern_id] = np.int32(stamp)
                pair_by_pattern[pattern_id] = np.int32(pair_cursor)
                pair_cursor += 1
            pair_idx = int(pair_by_pattern[pattern_id])
            write = int(write_cursors[pair_idx])
            local_surfaces[write] = np.int32(local_surface)
            write_cursors[pair_idx] += np.int64(1)

    return pair_owners, pair_pattern_ids, pair_offsets, pair_counts, local_surfaces


def build_response_group_pattern_plan(
    surface_pattern_ids: np.ndarray,
    group_offsets: np.ndarray,
    group_lengths: np.ndarray,
    *,
    pattern_count: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Group exact surface rows by ``(owner, head-pattern)`` in first-seen order.

    The returned local-surface rows retain their original ascending ordinals inside each pair.
    Scoring may therefore evaluate one engine-owned head pattern once and still apply the original
    first-surface tie rule explicitly.
    """

    ids = np.ascontiguousarray(np.asarray(surface_pattern_ids, dtype=np.int32).reshape(-1))
    offsets = np.ascontiguousarray(np.asarray(group_offsets, dtype=np.int64).reshape(-1))
    lengths = np.ascontiguousarray(np.asarray(group_lengths, dtype=np.int64).reshape(-1))
    patterns = int(pattern_count)
    if int(offsets.shape[0]) != int(lengths.shape[0]):
        raise ValueError("response pattern plan group metadata has inconsistent lengths")
    if patterns <= 0:
        if int(ids.shape[0]) != 0 or bool(np.any(lengths != 0)):
            raise ValueError("response pattern plan requires a nonempty pattern table")
        return (
            np.empty(0, dtype=np.int32),
            np.empty(0, dtype=np.int32),
            np.asarray((0,), dtype=np.int64),
            np.empty(0, dtype=np.int32),
            np.empty(0, dtype=np.int32),
        )
    if int(offsets.shape[0]) >= int(np.iinfo(np.int32).max):
        raise OverflowError("response pattern plan group count exceeds int32 stamps")
    if bool(np.any(offsets < 0)) or bool(np.any(lengths < 0)):
        raise ValueError("response pattern plan ranges must be nonnegative")
    if bool(np.any(offsets + lengths > int(ids.shape[0]))):
        raise ValueError("response pattern plan range exceeds the surface rows")
    if bool(np.any(ids < 0)) or bool(np.any(ids >= patterns)):
        raise ValueError("response pattern plan references an invalid head-pattern ID")
    return _build_response_group_pattern_plan_jit(ids, offsets, lengths, patterns)
