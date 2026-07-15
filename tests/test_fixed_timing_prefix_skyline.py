from __future__ import annotations

import numpy as np

from gear_optimizer.solver.fixed_timing_skyline import reduce_fixed_timing_prefix_skyline


def _brute_fixed_timing_rows(points: np.ndarray) -> set[tuple[int, ...]]:
    pts = np.asarray(points, dtype=np.int32)
    kept: set[tuple[int, ...]] = set()
    for i, p in enumerate(pts):
        dominated = False
        for j, q in enumerate(pts):
            if i == j:
                continue
            if int(q[3]) != int(p[3]) or int(q[4]) != int(p[4]):
                continue
            non_timing_ge = bool(
                q[0] >= p[0]
                and q[1] >= p[1]
                and q[2] >= p[2]
                and q[5] >= p[5]
            )
            non_timing_strict = bool(
                q[0] > p[0]
                or q[1] > p[1]
                or q[2] > p[2]
                or q[5] > p[5]
            )
            if non_timing_ge and non_timing_strict:
                dominated = True
                break
        if not dominated:
            kept.add(tuple(int(x) for x in p.tolist()))
    return kept


def test_fixed_timing_prefix_skyline_matches_bruteforce_random() -> None:
    rng = np.random.default_rng(12345)
    for n in (1, 2, 5, 10, 50, 200):
        for _ in range(20):
            points = np.empty((n, 6), dtype=np.int32)
            points[:, 0] = rng.integers(0, 9, size=n)   # PP
            points[:, 1] = rng.integers(0, 9, size=n)   # CM
            points[:, 2] = rng.integers(0, 9, size=n)   # FM
            points[:, 3] = rng.integers(0, 4, size=n)   # FT
            points[:, 4] = rng.integers(0, 4, size=n)   # FF
            points[:, 5] = rng.integers(0, 25, size=n)  # base
            codes = np.arange(n, dtype=np.uint64)

            _, reduced, _ = reduce_fixed_timing_prefix_skyline(points, codes, max_stat_index=8)

            assert set(map(tuple, reduced.tolist())) == _brute_fixed_timing_rows(points)


def test_fixed_timing_prefix_skyline_keeps_incomparable_timing_cells() -> None:
    points = np.array(
        [
            [10, 10, 10, 0, 0, 100],
            [10, 10, 10, 0, 1, 100],  # Same non-timing stats, different FF: not comparable.
            [11, 10, 10, 0, 0, 100],  # Dominates only the first row.
        ],
        dtype=np.int32,
    )
    codes = np.arange(points.shape[0], dtype=np.uint64)

    _, reduced, reduced_codes = reduce_fixed_timing_prefix_skyline(points, codes, max_stat_index=16)

    assert set(map(tuple, reduced.tolist())) == {
        (10, 10, 10, 0, 1, 100),
        (11, 10, 10, 0, 0, 100),
    }
    assert int(reduced.shape[0]) == int(reduced_codes.shape[0])


def test_fixed_timing_prefix_skyline_equal_base_strict_cm_fm_dominates() -> None:
    points = np.array(
        [
            [7, 5, 5, 2, 3, 42],
            [7, 6, 5, 2, 3, 42],  # Equal PP/base and higher CM dominates row 0.
            [7, 6, 6, 2, 3, 42],  # Equal PP/base and higher FM dominates row 1.
        ],
        dtype=np.int32,
    )
    codes = np.arange(points.shape[0], dtype=np.uint64)

    _, reduced, _ = reduce_fixed_timing_prefix_skyline(points, codes, max_stat_index=8)

    assert set(map(tuple, reduced.tolist())) == {(7, 6, 6, 2, 3, 42)}
