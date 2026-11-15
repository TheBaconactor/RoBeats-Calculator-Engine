"""`_points_skyline` must produce byte-identical output to the `_points_append` fold it replaced: the same kept set,
in the same original order, with the first occurrence of an exact duplicate surviving. That contract covers the
small-kept fold, the bail into `_points_skyline_sorted` once the kept set crosses 64 rows, and the packed-key range
guard's fold fallback."""

from __future__ import annotations

import numpy as np
import pytest
from numba import njit

from gear_optimizer.frontier.producer_kernels import _points_append, _points_skyline


@njit
def _reference_fold(buf, start: int, end: int) -> int:
    kept = start
    for idx in range(start, end):
        kept = _points_append(buf, start, int(kept), int(buf[idx, 0]), int(buf[idx, 1]), int(buf[idx, 2]))
    return int(kept)


def _assert_parity(rows: np.ndarray, start: int = 0, end: int | None = None) -> None:
    if end is None:
        end = rows.shape[0]
    expected = rows.copy()
    actual = rows.copy()
    kept_expected = _reference_fold(expected, start, end)
    kept_actual = _points_skyline(actual, start, end)
    assert kept_actual == kept_expected
    assert (actual[start:kept_actual] == expected[start:kept_expected]).all()
    assert (actual[:start] == expected[:start]).all()


def test_points_skyline_random_parity() -> None:
    rng = np.random.default_rng(0x5F1EA)
    for _ in range(300):
        m = int(rng.integers(1, 220))
        rows = rng.integers(-40, 200, size=(m, 3)).astype(np.int64)
        _assert_parity(rows)


def test_points_skyline_duplicate_first_occurrence() -> None:
    # A narrow value domain forces exact duplicates; the fold keeps the first, so the sorted pass must be stable.
    rng = np.random.default_rng(0xD0F5)
    for _ in range(200):
        m = int(rng.integers(2, 300))
        rows = rng.integers(0, 6, size=(m, 3)).astype(np.int64)
        _assert_parity(rows)


def test_points_skyline_kept_set_bail() -> None:
    # All coordinates ascending: nothing dominates, so kept == m and the fold bails into the sorted pass mid-way.
    rng = np.random.default_rng(0xBA1)
    for m in (65, 66, 100, 200, 400):
        rows = np.empty((m, 3), dtype=np.int64)
        rows[:, 0] = np.arange(m)
        rows[:, 1] = np.arange(m)
        rows[:, 2] = rng.integers(0, 8, m)
        _assert_parity(rows)


def test_points_skyline_mixed_growth() -> None:
    # A dominated head, then a surviving run crossing the 64-row cap, then a dominated tail.
    rng = np.random.default_rng(0xCAF3)
    for _ in range(150):
        head = rng.integers(0, 10, size=(int(rng.integers(1, 40)), 3))
        mid = np.empty((int(rng.integers(70, 150)), 3), dtype=np.int64)
        mid[:, 0] = np.arange(mid.shape[0]) + 100
        mid[:, 1] = np.arange(mid.shape[0])
        mid[:, 2] = rng.integers(0, 5, mid.shape[0])
        tail = rng.integers(0, 30, size=(int(rng.integers(0, 40)), 3))
        _assert_parity(np.vstack([head, mid, tail]).astype(np.int64))


def test_points_skyline_offset_windows() -> None:
    rng = np.random.default_rng(0x0FF5E7)
    for _ in range(150):
        head = rng.integers(0, 50, size=(int(rng.integers(1, 30)), 3))
        mid = rng.integers(-20, 150, size=(int(rng.integers(1, 260)), 3))
        tail = rng.integers(0, 50, size=(int(rng.integers(1, 30)), 3))
        rows = np.vstack([head, mid, tail]).astype(np.int64)
        _assert_parity(rows, start=head.shape[0], end=head.shape[0] + mid.shape[0])


def test_points_skyline_packed_range_guard() -> None:
    # The packed-key guard lives inside _points_skyline_sorted, which only runs after the fold's kept set passes 64 -
    # so exercise it with >64 mutually non-dominated rows whose coordinate spans overflow an int64 sort key: the
    # sorted path must refuse the packed key and fold the window instead of wrapping it.
    m = 120
    rows = np.empty((m, 3), dtype=np.int64)
    rows[:, 0] = np.arange(m, dtype=np.int64) - (1 << 62)
    rows[:, 1] = np.arange(m, dtype=np.int64)
    rows[:, 2] = np.arange(m, dtype=np.int64) * (1 << 55)
    _assert_parity(rows)


def test_points_skyline_empty_and_singleton() -> None:
    rows = np.zeros((0, 3), dtype=np.int64)
    assert _points_skyline(rows, 0, 0) == 0
    _assert_parity(np.asarray([[5, 2, 1]], dtype=np.int64))
