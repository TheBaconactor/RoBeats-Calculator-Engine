from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np

from gear_optimizer.core.constants import MAX_STAT_INDEX


@dataclass(frozen=True)
class FixedTimingPrefixSkylineStats:
    """Telemetry for the fixed-FT/FF prefix skyline reducer.

    The reducer keeps one representative for every undominated prefix state under
    the partial order

        (PP, CM, FM, base) ascending, with FT and FF fixed.

    Applying this after each gear-slot expansion is lossless because every later
    completion adds the same nonnegative/capped vector to compared states with the
    same timing cell, so dominance is preserved into the final gear skyline.
    """

    points_in: int
    points_unique: int
    points_out: int
    timing_cells: int
    pp_layers: int
    max_cell_size: int
    seconds: float


def _suffix_max_3d_inplace(dst: np.ndarray) -> None:
    """Convert a 3-D PP/CM/FM grid into a suffix maximum grid in-place."""

    v0 = dst[::-1, :, :]
    np.maximum.accumulate(v0, axis=0, out=v0)
    v1 = dst[:, ::-1, :]
    np.maximum.accumulate(v1, axis=1, out=v1)
    v2 = dst[:, :, ::-1]
    np.maximum.accumulate(v2, axis=2, out=v2)


def reduce_fixed_timing_prefix_skyline(
    points: np.ndarray,
    codes: np.ndarray,
    *,
    max_stat_index: int = MAX_STAT_INDEX,
) -> tuple[FixedTimingPrefixSkylineStats, np.ndarray, np.ndarray]:
    """Return the fixed-FT/FF prefix skyline of ``points`` with aligned ``codes``.

    ``points`` must be an ``(n, 6)`` array with columns
    ``PP, CM, FM, FT, FF, base``. A point is removed when another point has the
    same ``FT`` and ``FF`` and has ``PP >=``, ``CM >=``, ``FM >=``, and ``base >=``
    with at least one strict inequality. Exact duplicates in ``PP,CM,FM,FT,FF``
    are collapsed to the highest-base representative.

    Implementation: for each timing cell, coordinate-compress the actually
    present PP/CM/FM values and build one dense suffix-maximum grid over that
    compressed cell. The grid stores a lexicographic value ``(base, PP, CM, FM)``;
    therefore an equal-base point with any strictly larger stat coordinate is also
    detected as a dominator.
    """

    t0 = time.perf_counter()
    pts = np.asarray(points)
    cds = np.asarray(codes, dtype=np.uint64)

    if pts.ndim != 2 or pts.shape[1] != 6:
        raise ValueError("points must have shape (n, 6)")
    if cds.ndim != 1 or int(cds.shape[0]) != int(pts.shape[0]):
        raise ValueError("codes must be a 1-D array aligned with points")

    n = int(pts.shape[0])
    if n == 0:
        empty_points = np.zeros((0, 6), dtype=np.int32)
        empty_codes = np.zeros(0, dtype=np.uint64)
        return (
            FixedTimingPrefixSkylineStats(0, 0, 0, 0, 0, 0, float(time.perf_counter() - t0)),
            empty_points,
            empty_codes,
        )

    pts_i32 = pts.astype(np.int32, copy=False)
    max_idx = int(max_stat_index)
    stat_span = max_idx + 1
    if max_idx <= 0:
        raise ValueError("max_stat_index must be positive")

    pp = pts_i32[:, 0]
    cm = pts_i32[:, 1]
    fm = pts_i32[:, 2]
    ft = pts_i32[:, 3]
    ff = pts_i32[:, 4]
    base = pts_i32[:, 5]

    timing_key = ft.astype(np.int64, copy=False) * np.int64(stat_span) + ff.astype(np.int64, copy=False)

    # Sort by timing cell and exact stat key, with highest base first for each
    # exact (PP,CM,FM,FT,FF) duplicate group.
    order = np.lexsort((-base, fm, cm, pp, timing_key))
    sorted_pts = pts_i32[order]
    sorted_codes = cds[order]
    sorted_timing_key = timing_key[order]

    cell_starts = np.flatnonzero(
        np.concatenate(([True], sorted_timing_key[1:] != sorted_timing_key[:-1]))
    ).astype(np.int64, copy=False)
    cell_ends = np.append(cell_starts[1:], np.int64(n))

    keep_chunks: list[np.ndarray] = []
    points_unique = 0
    pp_layers = 0
    max_cell_size = 0
    neg_inf = np.int64(np.iinfo(np.int64).min // 4)
    # Enough room to lexicographically encode (base, PP, CM, FM). base is a lane
    # sum over six gear pieces and remains tiny relative to int64; this keeps the
    # check branch-free and exact.
    big = np.int64(stat_span * stat_span * stat_span)

    for cell_start_i, cell_end_i in zip(cell_starts, cell_ends, strict=True):
        start = int(cell_start_i)
        end = int(cell_end_i)
        max_cell_size = max(max_cell_size, end - start)
        cell_pts = sorted_pts[start:end]
        # Deduplicate exact (PP,CM,FM) keys inside this fixed FT/FF cell. The
        # sorted order ensures the first row has the highest base.
        unique_mask = np.ones(int(cell_pts.shape[0]), dtype=np.bool_)
        if int(cell_pts.shape[0]) > 1:
            unique_mask[1:] = np.any(cell_pts[1:, :3] != cell_pts[:-1, :3], axis=1)
        if not np.any(unique_mask):
            continue

        unique_pts = cell_pts[unique_mask]
        points_unique += int(unique_pts.shape[0])

        upp, pp_idx = np.unique(unique_pts[:, 0], return_inverse=True)
        ucm, cm_idx = np.unique(unique_pts[:, 1], return_inverse=True)
        ufm, fm_idx = np.unique(unique_pts[:, 2], return_inverse=True)
        pp_layers += int(upp.shape[0])

        aug = (
            unique_pts[:, 5].astype(np.int64, copy=False) * big
            + unique_pts[:, 0].astype(np.int64, copy=False) * np.int64(stat_span * stat_span)
            + unique_pts[:, 1].astype(np.int64, copy=False) * np.int64(stat_span)
            + unique_pts[:, 2].astype(np.int64, copy=False)
        )

        grid = np.full((int(upp.shape[0]), int(ucm.shape[0]), int(ufm.shape[0])), neg_inf, dtype=np.int64)
        np.maximum.at(grid, (pp_idx, cm_idx, fm_idx), aug)
        _suffix_max_3d_inplace(grid)

        keep_unique = grid[pp_idx, cm_idx, fm_idx] <= aug
        if np.any(keep_unique):
            # Convert from unique-row positions back to positions in sorted_pts.
            unique_positions = np.flatnonzero(unique_mask)
            keep_chunks.append(unique_positions[keep_unique].astype(np.int64, copy=False) + start)

    if keep_chunks:
        keep_sorted_idx = np.concatenate(keep_chunks).astype(np.int64, copy=False)
        out_points = sorted_pts[keep_sorted_idx].astype(np.int32, copy=False)
        out_codes = sorted_codes[keep_sorted_idx].astype(np.uint64, copy=False)
    else:
        out_points = np.zeros((0, 6), dtype=np.int32)
        out_codes = np.zeros(0, dtype=np.uint64)

    return (
        FixedTimingPrefixSkylineStats(
            points_in=n,
            points_unique=int(points_unique),
            points_out=int(out_points.shape[0]),
            timing_cells=int(cell_starts.shape[0]),
            pp_layers=int(pp_layers),
            max_cell_size=int(max_cell_size),
            seconds=float(time.perf_counter() - t0),
        ),
        out_points,
        out_codes,
    )
