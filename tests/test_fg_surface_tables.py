"""A bundle's surface tables round-trip exactly: every range of the saved rows expands back to the producer's rows and
head coefficients, and the compact scoring gather matches an independent np.unique oracle.

CPU-only; no GPU. Synthesizes everything in a temp dir -- never touches the production cache.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from gear_optimizer.rules import MAX_STAT
from gear_optimizer.solver.taichi_gem.force_greats import response_cache_store
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_patterns import expand_surface_rows
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import (
    _save_payload,
    gather_surface_patterns,
    read_compatible_bundle,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_types import FgResponseFrontierCachePayload
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_patterns import surface_head_coeffs
from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseFrontierResult, FgResponseSurface
from tests.fg_response_frontier_oracles import intern_surface_rows

pytestmark = pytest.mark.filterwarnings("ignore")


def _tables(cache_key: tuple) -> tuple[np.ndarray, np.ndarray]:
    """The saved bundle's (4, n) row and (10, m) pattern columns."""
    arrays = read_compatible_bundle(cache_key)
    return arrays["surface_rows"], arrays["surface_patterns"]


def _expanded(cache_key: tuple, ranges) -> tuple[np.ndarray, np.ndarray]:
    """The saved rows of `ranges`, expanded to the scorer's (k, 11) rows and (k, 4) head coefficients."""
    rows, patterns = _tables(cache_key)
    row_refs = np.concatenate([rows[:, start : start + count].T for start, count in ranges])
    return expand_surface_rows(row_refs, patterns.T)


# --------------------------------------------------------------------------------------------------
# Synthetic surface helpers.
# --------------------------------------------------------------------------------------------------
def _synthetic_pool(row_count: int) -> np.ndarray:
    """A deterministic uint32 N x 11 pool with distinct, head-coeff-meaningful column values."""
    rng = np.random.default_rng(2026_06_10)
    pool = np.empty((int(row_count), 11), dtype=np.uint32)
    # cols 0-3 are fever words (drive head coeffs): mix of small bit patterns so coeffs are non-trivial.
    pool[:, 0:4] = rng.integers(0, np.iinfo(np.uint32).max, size=(row_count, 4), dtype=np.uint64).astype(np.uint32)
    # cols 4-7 great words.
    pool[:, 4:8] = rng.integers(0, np.iinfo(np.uint32).max, size=(row_count, 4), dtype=np.uint64).astype(np.uint32)
    # cols 8-10 body counts: keep modest so values are obviously distinct per row.
    pool[:, 8] = np.arange(row_count, dtype=np.uint32) * 3 + 7
    pool[:, 9] = np.arange(row_count, dtype=np.uint32) * 2 + 1
    pool[:, 10] = np.arange(row_count, dtype=np.uint32)
    return pool


def _surfaces_from_pool(pool: np.ndarray) -> tuple[FgResponseSurface, ...]:
    return tuple(FgResponseSurface(*(int(v) for v in pool[idx, :11])) for idx in range(int(pool.shape[0])))


def _coeffs_for(pool: np.ndarray, *, total_notes: int) -> np.ndarray:
    head_len = min(int(total_notes), 100)
    coeffs = surface_head_coeffs(np.ascontiguousarray(pool, dtype=np.uint32), head_len=int(head_len))
    return np.ascontiguousarray(np.asarray(coeffs, dtype=np.uint16))


def _build_payload(pool: np.ndarray, *, total_notes: int) -> FgResponseFrontierCachePayload:
    surfaces = _surfaces_from_pool(pool)
    frontier = FgResponseFrontierResult(surfaces, {}, 1, 2, 3, 4, 5, 6, 7, 0.0)
    return FgResponseFrontierCachePayload(
        frontier_by_key={(0, 0): frontier},
        raw_fill_by_ff=np.zeros((MAX_STAT + 1,), dtype=np.float64),
        non_fever_base_by_ff=np.zeros((MAX_STAT + 1,), dtype=np.int32),
        real_time_by_ft=np.zeros((MAX_STAT + 1,), dtype=np.float64),
        total_notes=int(total_notes),
        long_notes=0,
        use_forced_great_timing=True,
    )


def _range_sweep(row_count: int) -> tuple[tuple[tuple[int, int], ...], ...]:
    """A range sweep covering: single row, full span, multiple disjoint ranges, boundary stat keys."""
    sweeps: list[tuple[tuple[int, int], ...]] = [
        ((0, 1),),  # single first row
        ((int(row_count) - 1, 1),),  # single last row (boundary)
        ((0, int(row_count)),),  # full span
        ((0, 1), (2, 2), (int(row_count) - 1, 1)),  # multiple disjoint ranges incl. boundaries
    ]
    if row_count >= 4:
        sweeps.append(((1, 2), (0, 1)))  # out-of-order / overlapping starts, range-packed order matters
    return tuple(sweeps)


# --------------------------------------------------------------------------------------------------
# Tests.
# --------------------------------------------------------------------------------------------------
def test_saved_surfaces_expand_back_to_the_producer_rows_over_a_range_sweep(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache_store.reset_fg_response_frontier_payload_cache()
    total_notes = 80
    row_count = 70
    pool = _synthetic_pool(row_count)
    coeffs = _coeffs_for(pool, total_notes=total_notes).astype(np.int32)
    cache_key = ("unit", "range-sweep")
    _save_payload(cache_key, _build_payload(pool, total_notes=total_notes))

    for ranges in _range_sweep(row_count):
        rows, row_coeffs = _expanded(cache_key, ranges)
        want = np.concatenate([np.arange(start, start + count) for start, count in ranges])
        assert rows.dtype == np.dtype("uint32") and row_coeffs.dtype == np.dtype("int32")
        assert np.array_equal(rows, pool[want]), f"row mismatch for ranges={ranges}"
        assert np.array_equal(row_coeffs, coeffs[want]), f"coeff mismatch for ranges={ranges}"


def test_saved_surfaces_roundtrip_a_large_pool(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache_store.reset_fg_response_frontier_payload_cache()
    total_notes = 60
    row_count = 32773
    pool = _synthetic_pool(row_count)
    coeffs = _coeffs_for(pool, total_notes=total_notes).astype(np.int32)
    cache_key = ("unit", "large-pool")
    _save_payload(cache_key, _build_payload(pool, total_notes=total_notes))

    for ranges in (((0, row_count),), ((32765, 6),), ((row_count - 1, 1), (0, 1))):
        rows, row_coeffs = _expanded(cache_key, ranges)
        want = np.concatenate([np.arange(start, start + count) for start, count in ranges])
        assert np.array_equal(rows, pool[want]), f"row mismatch for ranges={ranges}"
        assert np.array_equal(row_coeffs, coeffs[want]), f"coeff mismatch for ranges={ranges}"


def test_surface_pattern_interning_preserves_row_order_and_repeated_patterns() -> None:
    pool = _synthetic_pool(6)
    pool[2, :8] = pool[0, :8]
    pool[4, :8] = pool[0, :8]
    coeffs = _coeffs_for(pool, total_notes=80)

    row_refs, patterns = intern_surface_rows(pool, coeffs)
    expanded_rows, expanded_coeffs = expand_surface_rows(row_refs, patterns)

    assert row_refs.shape == (6, 4)
    assert int(row_refs[0, 0]) == int(row_refs[2, 0]) == int(row_refs[4, 0])
    assert np.array_equal(expanded_rows, pool)
    assert np.array_equal(expanded_coeffs, coeffs.astype(np.int32))


def test_surface_pattern_interning_rejects_equal_masks_with_different_coefficients() -> None:
    pool = _synthetic_pool(2)
    pool[1, :8] = pool[0, :8]
    coeffs = _coeffs_for(pool, total_notes=80)
    coeffs[1, 0] = np.uint16(int(coeffs[1, 0]) + 1)

    with pytest.raises(ValueError, match="inconsistent scoring coefficients"):
        intern_surface_rows(pool, coeffs)


def test_issue116_writer_derives_head_coefficients_after_exact_pattern_interning(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache_store.reset_fg_response_frontier_payload_cache()

    total_notes = 80
    pool = _synthetic_pool(8)
    pool[2, :8] = pool[0, :8]
    pool[5, :8] = pool[0, :8]
    pool[7, :8] = pool[1, :8]
    expected_pattern_words = np.unique(pool[:, :8], axis=0)
    expected_coeffs = _coeffs_for(pool, total_notes=total_notes).astype(np.int32)
    real_precompute = response_cache_store.surface_head_coeffs
    precompute_inputs: list[np.ndarray] = []

    def _track_pattern_precompute(surface_words: np.ndarray, *, head_len: int) -> np.ndarray:
        precompute_inputs.append(np.asarray(surface_words).copy())
        return real_precompute(surface_words, head_len=int(head_len))

    monkeypatch.setattr(response_cache_store, "surface_head_coeffs", _track_pattern_precompute)
    cache_key = ("unit", "issue116-pattern-coeff-owner")
    _save_payload(cache_key, _build_payload(pool, total_notes=total_notes))

    assert len(precompute_inputs) == 1
    assert np.array_equal(precompute_inputs[0], expected_pattern_words)
    assert int(precompute_inputs[0].shape[0]) < int(pool.shape[0])

    rows, pattern_columns = _tables(cache_key)
    row_refs, patterns = rows.T, pattern_columns.T
    expected_row_refs, expected_patterns = intern_surface_rows(pool, expected_coeffs)
    assert np.array_equal(row_refs, expected_row_refs)
    assert np.array_equal(patterns, expected_patterns)
    expanded_rows, expanded_coeffs = expand_surface_rows(row_refs, patterns)
    assert np.array_equal(expanded_rows, pool)
    assert np.array_equal(expanded_coeffs, expected_coeffs)


def test_surface_pattern_expansion_rejects_invalid_pattern_id() -> None:
    row_refs = np.asarray([[1, 2, 3, 4]], dtype=np.uint32)
    patterns = np.zeros((1, 10), dtype=np.uint32)

    with pytest.raises(ValueError, match="invalid head-pattern ID"):
        expand_surface_rows(row_refs, patterns)


def test_compact_scoring_gather_preserves_range_order_and_pattern_sharing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache_store.reset_fg_response_frontier_payload_cache()
    pool = _synthetic_pool(6)
    pool[2, :8] = pool[0, :8]
    pool[4, :8] = pool[0, :8]
    cache_key = ("unit", "compact-scoring-loader")
    _save_payload(cache_key, _build_payload(pool, total_notes=80))
    ranges = ((4, 2), (0, 3))

    pattern_ids, counts, pattern_words, pattern_coeffs = gather_surface_patterns(*_tables(cache_key), ranges)
    expanded_rows, expanded_coeffs = _expanded(cache_key, ranges)

    assert pattern_ids.shape == (5,)
    assert counts.shape == (5, 3)
    assert pattern_words.shape[0] < pattern_ids.shape[0]
    np.testing.assert_array_equal(pattern_words[pattern_ids], expanded_rows[:, :8])
    np.testing.assert_array_equal(counts, expanded_rows[:, 8:11].astype(np.int32))
    np.testing.assert_array_equal(pattern_coeffs[pattern_ids], expanded_coeffs)


def _shared_pattern_pool(row_count: int, pattern_count: int) -> np.ndarray:
    """A pool whose rows reuse `pattern_count` distinct head mask-word rows (unique body counts)."""
    rng = np.random.default_rng(20260927)
    templates = _synthetic_pool(pattern_count)
    pool = _synthetic_pool(row_count)
    pool[:, :8] = templates[rng.integers(0, pattern_count, size=row_count), :8]
    return pool


def _retired_unique_compact_load(cache_key: tuple, ranges: tuple[tuple[int, int], ...]):
    """The retired N-row np.unique remap over the saved tables, kept as the gather oracle."""
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_patterns import unpack_surface_patterns

    rows, patterns = _tables(cache_key)
    row_refs_all, patterns_all = rows.T, patterns.T
    row_refs = np.concatenate([row_refs_all[start : start + count] for start, count in ranges])
    unique_ids, local_ids = np.unique(np.asarray(row_refs[:, 0], dtype=np.uint64), return_inverse=True)
    words, coeffs = unpack_surface_patterns(patterns_all[np.asarray(unique_ids, dtype=np.intp)])
    return (
        np.ascontiguousarray(local_ids, dtype=np.int32),
        np.ascontiguousarray(row_refs[:, 1:4], dtype=np.int32),
        words,
        coeffs,
    )


def test_compact_scoring_gather_matches_retired_unique_remap(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache_store.reset_fg_response_frontier_payload_cache()
    row_count = 300
    pool = _shared_pattern_pool(row_count, 23)
    cache_key = ("unit", "compact-loader-oracle")
    _save_payload(cache_key, _build_payload(pool, total_notes=80))

    for ranges in (
        ((0, row_count),),
        ((250, 50), (0, 40), (100, 1)),
        ((10, 5), (12, 30), (299, 1)),
        ((7, 1),),
    ):
        got = gather_surface_patterns(*_tables(cache_key), ranges)
        want = _retired_unique_compact_load(cache_key, ranges)
        for got_array, want_array in zip(got, want, strict=True):
            assert got_array.dtype == want_array.dtype
            assert got_array.shape == want_array.shape
            np.testing.assert_array_equal(got_array, want_array)


def test_compact_scoring_gather_rejects_invalid_pattern_ids_and_ranges(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", str(tmp_path))
    response_cache_store.reset_fg_response_frontier_payload_cache()
    pool = _shared_pattern_pool(6, 3)
    cache_key = ("unit", "compact-gather-invalid")
    _save_payload(cache_key, _build_payload(pool, total_notes=80))
    rows, patterns = _tables(cache_key)

    with pytest.raises(ValueError, match="outside the bundle's rows"):
        gather_surface_patterns(rows, patterns, ((4, 3),))

    for bad_id in (int(patterns.shape[1]), 2**31, 2**32 - 1):
        bad_rows = rows.copy()
        bad_rows[0, 3] = np.uint32(bad_id)
        with pytest.raises(ValueError, match="invalid head-pattern ID"):
            gather_surface_patterns(bad_rows, patterns, ((0, 6),))
        # Ranges that skip the corrupt row still gather.
        ids, _counts, _words, _coeffs = gather_surface_patterns(bad_rows, patterns, ((4, 2), (0, 3)))
        assert ids.shape == (5,)


@pytest.mark.parametrize("pattern_count", [1, 7, 101, 400_000])
def test_dense_rank_pattern_ids_matches_np_unique_inverse(pattern_count: int) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import (
        _DENSE_RANK_BLOCK_ROWS,
        _dense_rank_pattern_ids_inplace,
    )

    rng = np.random.default_rng(pattern_count)
    block = int(_DENSE_RANK_BLOCK_ROWS)
    cases = [
        np.empty((0,), dtype=np.int32),
        rng.integers(0, pattern_count, size=block - 1),
        rng.integers(0, pattern_count, size=block + 1),
        np.full((block + 17,), pattern_count - 1),
        rng.choice(pattern_count, size=min(pattern_count, 5), replace=False),
        np.tile(rng.permutation(pattern_count), -(-(block + 2) // pattern_count)),
    ]
    for case in cases:
        ids = np.ascontiguousarray(case, dtype=np.int32)
        expected_unique, expected_inverse = np.unique(ids, return_inverse=True)
        ranked = ids.copy()
        unique = _dense_rank_pattern_ids_inplace(ranked, pattern_count)
        np.testing.assert_array_equal(unique, expected_unique)
        assert ranked.dtype == np.dtype(np.int32)
        np.testing.assert_array_equal(ranked, np.asarray(expected_inverse, dtype=np.int32))


def test_dense_rank_pattern_ids_rejects_out_of_range_ids() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import _dense_rank_pattern_ids_inplace

    for bad in (np.asarray([0, 3], dtype=np.int32), np.asarray([-1, 0], dtype=np.int32)):
        with pytest.raises(ValueError, match="invalid head-pattern ID"):
            _dense_rank_pattern_ids_inplace(bad, 3)
