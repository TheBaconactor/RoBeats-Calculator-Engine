"""Scoring an in-memory (session-pruned) pool in place is bit-identical to the retired compact copy.

The retired pack copied each batch's selected frontier segments out of the pruned pool, re-densified
their pattern IDs with ``np.unique`` and rebased group offsets onto the copy. The CPU-f64 scorer
(the macOS FG authority) reads rows by ``group_offset + local_row`` and patterns by ID, so reading
the full pool through absolute offsets must give the same inner rows and the same winning surfaces.
CPU-only (numba), no GPU.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from gear_optimizer.core.constants import TOTAL_ROWS

_HEAD_LEN = 40
_BODY_TOTAL = 100


def _random_pattern_words(rng: np.random.Generator, pattern_count: int) -> np.ndarray:
    words = np.zeros((pattern_count, 8), dtype=np.uint32)
    for row in range(pattern_count):
        start = int(rng.integers(0, _HEAD_LEN - 2))
        end = int(rng.integers(start + 1, _HEAD_LEN + 1))
        fever = sum(1 << pos for pos in range(start, end))
        greats = sum(1 << pos for pos in range(_HEAD_LEN) if rng.random() < 0.2)
        words[row, 0] = fever & 0xFFFFFFFF
        words[row, 1] = (fever >> 32) & 0xFFFFFFFF
        words[row, 4] = greats & 0xFFFFFFFF
        words[row, 5] = (greats >> 32) & 0xFFFFFFFF
    return words


def _random_in_memory_batch(seed: int):
    from gear_optimizer.solver.taichi_gem.force_greats.response_inner_host import _precompute_surface_head_coeffs

    rng = np.random.default_rng(seed)
    pattern_count = 60
    pattern_words = _random_pattern_words(rng, pattern_count)
    pattern_coeffs = np.ascontiguousarray(
        _precompute_surface_head_coeffs(pattern_words, head_len=_HEAD_LEN), dtype=np.int32
    )
    segment_lengths = [int(v) for v in rng.integers(3, 51, size=20)]
    segment_offsets = [0]
    for length in segment_lengths[:-1]:
        segment_offsets.append(segment_offsets[-1] + length)
    row_count = int(sum(segment_lengths))
    # Rows reference only part of the table, so the pool's pattern IDs are not dense.
    pattern_ids = np.ascontiguousarray(rng.integers(0, 45, size=row_count), dtype=np.int32)
    counts = np.empty((row_count, 3), dtype=np.int32)
    counts[:, 0] = rng.integers(0, 41, size=row_count)
    counts[:, 2] = rng.integers(0, 6, size=row_count)
    counts[:, 1] = counts[:, 2] + rng.integers(0, 9, size=row_count)
    # Frontiers: every segment once, plus three frontiers sharing an earlier segment.
    frontier_segments = list(range(20)) + [3, 3, 11]
    frontier_offsets = np.asarray([segment_offsets[s] for s in frontier_segments], dtype=np.int32)
    frontier_lengths = np.asarray([segment_lengths[s] for s in frontier_segments], dtype=np.int32)
    frontier_idx_by_stat = np.full((TOTAL_ROWS + 1, TOTAL_ROWS + 1), -1, dtype=np.int32)
    stat_keys = [(int(ft), int(ff)) for ft, ff in rng.integers(0, TOTAL_ROWS + 1, size=(len(frontier_segments), 2))]
    stat_keys = list(dict.fromkeys(stat_keys))
    for frontier_idx, (ft, ff) in enumerate(stat_keys):
        frontier_idx_by_stat[ft, ff] = frontier_idx
    bundle = SimpleNamespace(
        frontier_idx_by_stat=frontier_idx_by_stat,
        frontier_offsets=frontier_offsets,
        frontier_lengths=frontier_lengths,
        surface_pattern_ids=pattern_ids,
        surface_pattern_words=pattern_words,
        surface_counts=counts,
        surface_pattern_head_coeffs=pattern_coeffs,
        cache_key=("unit", "pack-in-place"),
    )
    # A subset of stat keys, with repeats, as a GA batch would select.
    picked = rng.choice(len(stat_keys) - 4, size=30, replace=True)
    group_ft_stat = np.asarray([stat_keys[int(i)][0] for i in picked], dtype=np.int32)
    group_ff_stat = np.asarray([stat_keys[int(i)][1] for i in picked], dtype=np.int32)
    group_meta = np.empty((30, 8), dtype=np.int32)
    group_meta[:, 0] = rng.integers(0, 21, size=30)  # residual gem budget
    group_meta[:, 1] = rng.integers(0, 60, size=30)  # cur_pp
    group_meta[:, 2] = rng.integers(0, 60, size=30)  # cur_cm
    group_meta[:, 3] = rng.integers(0, 60, size=30)  # cur_fm
    group_meta[:, 4] = rng.integers(20, 120, size=30)  # cur_primary
    group_meta[:, 5] = rng.integers(20, 120, size=30)  # cur_secondary
    group_meta[:, 6] = _HEAD_LEN
    group_meta[:, 7] = _BODY_TOTAL
    return bundle, group_meta, group_ft_stat, group_ff_stat


def _retired_compact_pack(bundle, group_ft_stat, group_ff_stat):
    """The retired in-memory branch: copy selected segments, np.unique-remap, rebase offsets."""
    kept_frontiers = np.ascontiguousarray(bundle.frontier_idx_by_stat[group_ft_stat, group_ff_stat], dtype=np.int32)
    offsets_all = np.asarray(bundle.frontier_offsets, dtype=np.int32)
    lengths_all = np.asarray(bundle.frontier_lengths, dtype=np.int32)
    selected_segments = sorted(
        {(int(offsets_all[int(f)]), int(lengths_all[int(f)])) for f in np.unique(kept_frontiers)}
    )
    copy_ranges: list[tuple[int, int, int]] = []
    segment_offsets: dict[tuple[int, int], int] = {}
    cursor = 0
    for start, length in selected_segments:
        if copy_ranges and copy_ranges[-1][0] + copy_ranges[-1][1] == start:
            prev_start, prev_length, target_start = copy_ranges[-1]
            copy_ranges[-1] = (prev_start, prev_length + length, target_start)
        else:
            copy_ranges.append((start, length, cursor))
        segment_offsets[(start, length)] = cursor
        cursor += length
    group_offsets = np.asarray(
        [segment_offsets[(int(offsets_all[int(f)]), int(lengths_all[int(f)]))] for f in kept_frontiers],
        dtype=np.int32,
    )
    selected_pattern_ids = np.empty((cursor,), dtype=np.int32)
    surface_counts = np.empty((cursor, 3), dtype=np.int32)
    for source_start, length, target_start in copy_ranges:
        selected_pattern_ids[target_start : target_start + length] = bundle.surface_pattern_ids[
            source_start : source_start + length
        ]
        surface_counts[target_start : target_start + length] = bundle.surface_counts[source_start : source_start + length]
    used_pattern_ids, surface_pattern_ids = np.unique(selected_pattern_ids, return_inverse=True)
    return (
        np.ascontiguousarray(surface_pattern_ids, dtype=np.int32),
        np.ascontiguousarray(bundle.surface_pattern_words[used_pattern_ids], dtype=np.uint32),
        surface_counts,
        np.ascontiguousarray(bundle.surface_pattern_head_coeffs[used_pattern_ids], dtype=np.int32),
        group_offsets,
        np.ascontiguousarray(lengths_all[kept_frontiers], dtype=np.int32),
    )


def _score_cpu_f64(group_meta, packed, *, allow_pp: bool) -> np.ndarray:
    from gear_optimizer.solver.taichi_gem.force_greats.response_inner_host import _score_fg_response_groups_native_f64

    ids, words, counts, coeffs, group_offsets, group_lengths = packed[:6]
    idx = np.arange(TOTAL_ROWS + 1, dtype=np.float64)
    color_flags = (
        np.asarray([1, 0, 0, 0, 0, 0, 1, 0], dtype=np.int32)
        if allow_pp
        else np.asarray([0, 0, 1, 0, 0, 1, 1, 0], dtype=np.int32)
    )
    return np.asarray(
        _score_fg_response_groups_native_f64(
            np.ascontiguousarray(group_offsets, dtype=np.int64),
            np.ascontiguousarray(group_lengths, dtype=np.int64),
            np.ascontiguousarray(group_meta, dtype=np.int32),
            np.ascontiguousarray(ids, dtype=np.int32),
            np.ascontiguousarray(words, dtype=np.uint32),
            np.ascontiguousarray(counts, dtype=np.int32),
            np.ascontiguousarray(coeffs, dtype=np.int32),
            color_flags,
            np.ascontiguousarray(idx * 0.5 + 0.3),
            np.ascontiguousarray(1.0 + idx * 0.011),
            np.ascontiguousarray(1.0 + idx * 0.017),
            bool(allow_pp),
            int(TOTAL_ROWS),
        ),
        dtype=np.int32,
    )


def _winning_surfaces(packed, inner_rows) -> list[tuple[int, ...]]:
    from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import _surface_from_packed_arrays

    ids, words, counts, _coeffs, group_offsets, _group_lengths = packed[:6]
    return [
        tuple(
            _surface_from_packed_arrays(
                surface_pattern_ids=ids,
                surface_pattern_words=words,
                surface_counts=counts,
                surface_idx=int(group_offsets[g]) + int(inner_rows[g, 1]),
            )
        )
        for g in range(int(inner_rows.shape[0]))
    ]


@pytest.mark.parametrize("seed", [1, 2, 3])
@pytest.mark.parametrize("allow_pp", [False, True])
def test_in_memory_pack_scores_bit_identical_to_retired_compact_copy(seed: int, allow_pp: bool) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_frontier

    bundle, group_meta, group_ft_stat, group_ff_stat = _random_in_memory_batch(seed)
    retired = _retired_compact_pack(bundle, group_ft_stat, group_ff_stat)
    packed = response_frontier._pack_scoring_surfaces_for_batch(
        scoring_bundle=bundle,
        group_meta=group_meta,
        group_ft_stat=group_ft_stat,
        group_ff_stat=group_ff_stat,
    )
    np.testing.assert_array_equal(packed[5], retired[5])

    retired_rows = _score_cpu_f64(group_meta, retired, allow_pp=allow_pp)
    packed_rows = _score_cpu_f64(group_meta, packed, allow_pp=allow_pp)
    np.testing.assert_array_equal(packed_rows, retired_rows)
    assert int(np.max(retired_rows[:, 0])) > 0
    assert _winning_surfaces(packed, packed_rows) == _winning_surfaces(retired, retired_rows)


def test_in_memory_pack_reads_the_pool_in_place() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_frontier

    bundle, group_meta, group_ft_stat, group_ff_stat = _random_in_memory_batch(4)
    packed = response_frontier._pack_scoring_surfaces_for_batch(
        scoring_bundle=bundle,
        group_meta=group_meta,
        group_ft_stat=group_ft_stat,
        group_ff_stat=group_ff_stat,
    )
    assert np.shares_memory(packed[0], bundle.surface_pattern_ids)
    assert np.shares_memory(packed[1], bundle.surface_pattern_words)
    assert np.shares_memory(packed[2], bundle.surface_counts)
    assert np.shares_memory(packed[3], bundle.surface_pattern_head_coeffs)
    kept = bundle.frontier_idx_by_stat[group_ft_stat, group_ff_stat]
    np.testing.assert_array_equal(packed[4], bundle.frontier_offsets[kept])
