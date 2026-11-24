"""The Base (Perfect-only) frontier of every (Fever Time, Fever Fill Rate) cell of a song, as one grid payload.

Base and Force Great scoring share one lane-aware response producer. Base runs it with no Great action, so chart order,
lane matching, simultaneous press and release, fever activation and the Pareto reduction are decided by the same model
before a surface is uploaded or persisted.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from gear_optimizer.gamedata import StatCurves
from gear_optimizer.rules import MAX_STAT
from gear_optimizer.solver.fever_timeline import calculate_fever_timeline_surface_grid, intern_fixed_timing_surfaces
from gear_optimizer.solver.timing_envelope import TimedSong, fever_axes

from .fg_cache_patterns import surface_head_coeffs

GRID_SIZE = MAX_STAT + 1
MAX_TIMELINE_FRONTIER_SURFACES = 262144  # the song's frontier pool: the GPU field-size cap (VRAM bound 1,048,576)
_MAX_HEAD = 100
_WORD = 0xFFFFFFFF


def configure_timeline_pair_build_threads(max_threads: int) -> int:
    """Set how many threads a song's frontier build may use, Base and FG alike; returns the previous setting."""
    from .producer_reducer import configure_frontier_build_threads

    return configure_frontier_build_threads(max_threads)


@dataclass(frozen=True, slots=True)
class TimelineFrontierGridPayload:
    grid_count_body_fever: np.ndarray
    grid_count_body_normal: np.ndarray
    grid_head_len: np.ndarray
    grid_fever_masks_bits: np.ndarray
    grid_frontier_count: np.ndarray
    grid_frontier_offset: np.ndarray
    grid_frontier_body_fever_pool: np.ndarray
    grid_frontier_body_normal_pool: np.ndarray
    grid_frontier_masks_bits_pool: np.ndarray
    grid_frontier_head_coeffs_pool: np.ndarray
    grid_gap: np.ndarray
    grid_fever_activations: np.ndarray
    frontier_pool_used: int


def build_timeline_frontier_grid_payload(
    *,
    timestamps: np.ndarray,
    perfect_candidate_timestamps: np.ndarray,
    perfect_floor_timestamps: np.ndarray,
    exit_ceiling_timestamps: np.ndarray,
    lanes: np.ndarray,
    fever_times: np.ndarray,
    fever_fills: np.ndarray,
) -> TimelineFrontierGridPayload:
    """Every FT/FF cell's Base frontier, from the shared producer's exact lane-aware all-Perfect surfaces.

    `fever_times` holds each Fever Time value's fever duration and `fever_fills` each Fever Fill Rate value's fill
    threshold in Perfects (timing_envelope.fever_axes). Cells with the same duration and the same whole fill count share
    a geometry, and geometries with the same surfaces share one range of the pool."""
    from .producer_batch import build_frontiers, song_arrays

    fill_counts = np.maximum(np.ceil(fever_fills).astype(np.int32), np.int32(1))
    unique_fill_counts, fill_inverse = np.unique(fill_counts, return_inverse=True)
    unique_fever_times, time_inverse = np.unique(fever_times, return_inverse=True)
    # Base has no Great judgment: with both Great envelopes on the Perfect ones the producer emits no Great edge.
    song = song_arrays(
        timestamps, perfect_candidate_timestamps, perfect_candidate_timestamps, perfect_floor_timestamps,
        perfect_floor_timestamps, None, exit_ceiling_timestamps, lanes,
    )
    frontiers = build_frontiers(
        song,
        tuple(
            (float(fill_count), 0, fever_time)
            for fever_time in unique_fever_times.tolist()
            for fill_count in unique_fill_counts.tolist()
        ),
        use_forced_great_timing=False,
    )

    n = song.timestamps.shape[0]
    head_len, total_body = min(n, _MAX_HEAD), max(0, n - _MAX_HEAD)
    # A pool surface is (body fever notes, the head's fever mask in two 64-bit words). A geometry's cell holds its
    # top surface (most body fever notes, then the highest mask): body fever and normal notes, head length, the
    # mask's four 32-bit words, and its surface count and pool offset.
    pool: list[tuple[int, int, int]] = []
    offset_of: dict[tuple[tuple[int, int, int], ...], int] = {}
    cell_by_id: dict[int, tuple[int, ...]] = {}
    cells = []
    for frontier in frontiers:
        fid = id(frontier)
        cached_cell = cell_by_id.get(fid)
        if cached_cell is not None:
            cells.append(cached_cell)
            continue
        rows = frontier.first_frontier.numba_rows().tolist()
        if not rows:
            raise ValueError("timeline physical producer emitted an empty frontier")
        if any(any(row[2:4]) or any(row[5:7]) for row in rows):
            raise ValueError("timeline all-Perfect producer emitted a Great response surface")
        surfaces = tuple((body_fever, fever_lo, fever_hi) for fever_lo, fever_hi, _, _, body_fever, _, _ in rows)
        if any(body_fever > total_body for body_fever, _, _ in surfaces):
            raise ValueError("timeline physical producer emitted invalid body fever count")
        offset = offset_of.get(surfaces)
        if offset is None:
            if len(pool) + len(surfaces) > MAX_TIMELINE_FRONTIER_SURFACES:
                raise RuntimeError(
                    f"timeline frontier pool overflow: need {len(pool) + len(surfaces)}, "
                    f"cap {MAX_TIMELINE_FRONTIER_SURFACES}"
                )
            offset = offset_of[surfaces] = len(pool)
            pool.extend(surfaces)
        body_fever, fever_lo, fever_hi = max(surfaces, key=lambda surface: (surface[0], surface[2], surface[1]))
        cell = (
            body_fever, total_body - body_fever, head_len, fever_lo & _WORD, fever_lo >> 32, fever_hi & _WORD,
            fever_hi >> 32, len(surfaces), offset,
        )
        cell_by_id[fid] = cell
        cells.append(cell)
    dense = np.asarray(cells, dtype=np.int64).reshape(unique_fever_times.size, unique_fill_counts.size, 9)
    grid = dense[time_inverse.reshape(GRID_SIZE, 1), fill_inverse.reshape(1, GRID_SIZE)][None]

    pool_shape = (1, MAX_TIMELINE_FRONTIER_SURFACES)
    body_fever_pool = np.zeros(pool_shape, dtype=np.int32)
    body_normal_pool = np.zeros(pool_shape, dtype=np.int32)
    masks_pool = np.zeros((*pool_shape, 4), dtype=np.uint32)
    coeffs_pool = np.zeros((*pool_shape, 4), dtype=np.int16)
    pool_used = len(pool)
    if pool_used:
        pool_arr = np.asarray(pool, dtype=np.uint64)
        bf_col = pool_arr[:, 0].astype(np.int32)
        body_fever_pool[0, :pool_used] = bf_col
        body_normal_pool[0, :pool_used] = total_body - bf_col
        masks_pool[0, :pool_used, 0] = (pool_arr[:, 1] & np.uint64(_WORD)).astype(np.uint32)
        masks_pool[0, :pool_used, 1] = (pool_arr[:, 1] >> np.uint64(32)).astype(np.uint32)
        masks_pool[0, :pool_used, 2] = (pool_arr[:, 2] & np.uint64(_WORD)).astype(np.uint32)
        masks_pool[0, :pool_used, 3] = (pool_arr[:, 2] >> np.uint64(32)).astype(np.uint32)
        coeffs_pool[0, :pool_used] = surface_head_coeffs(masks_pool[0, :pool_used], head_len=head_len).astype(np.int16)

    return TimelineFrontierGridPayload(
        grid_count_body_fever=grid[..., 0].astype(np.int32),
        grid_count_body_normal=grid[..., 1].astype(np.int32),
        grid_head_len=grid[..., 2].astype(np.int8),
        grid_fever_masks_bits=grid[..., 3:7].astype(np.uint32),
        grid_frontier_count=grid[..., 7].astype(np.int32),
        grid_frontier_offset=grid[..., 8].astype(np.int32),
        grid_frontier_body_fever_pool=body_fever_pool,
        grid_frontier_body_normal_pool=body_normal_pool,
        grid_frontier_masks_bits_pool=masks_pool,
        grid_frontier_head_coeffs_pool=coeffs_pool,
        grid_gap=np.zeros((1, GRID_SIZE, GRID_SIZE), dtype=np.int32),
        grid_fever_activations=np.zeros((1, GRID_SIZE, GRID_SIZE), dtype=np.int32),
        frontier_pool_used=len(pool),
    )


def build_fixed_timing_payload(song: TimedSong, curves: StatCurves) -> TimelineFrontierGridPayload:
    """The payload of a fixed-timing song. Every hit lands at its hit time, so each (Fever Time, Fever Fill) cell has
    exactly one fever surface and no Perfect-window frontier is searched; the per-cell fever kernel is the one the
    fixed-timing Base scorer runs, so the payload scores bit-identically to it. Cells with equal surfaces share one
    pool row, and the rows are in the order their first cells come (Fever Time major)."""
    timestamps = song.hit_timestamps
    total_notes = int(timestamps.shape[0])
    head_len = min(total_notes, 100)
    fever_durations, fill_thresholds = fever_axes(total_notes, song.chart.long_notes, song.chart.last_note_time, curves)
    grid = (MAX_STAT + 1, MAX_STAT + 1)
    body_fever, body_normal, activations, last_fever_end = (np.zeros(grid, dtype=np.int32) for _ in range(4))
    masks = np.zeros((*grid, 4), dtype=np.uint32)
    calculate_fever_timeline_surface_grid(
        timestamps, total_notes, fever_durations, np.ceil(fill_thresholds).astype(np.int64),
        (body_fever, body_normal, masks, activations, last_fever_end),
    )
    gap = (total_notes - last_fever_end).astype(np.int32)
    total_body = max(0, total_notes - 100)
    offsets, pool_bf, pool_masks, pool_used = intern_fixed_timing_surfaces(
        body_fever, masks, activations, last_fever_end, MAX_TIMELINE_FRONTIER_SURFACES
    )
    head_coeffs = surface_head_coeffs(pool_masks, head_len=head_len).astype(np.int16)
    shape = (1, *grid)
    return TimelineFrontierGridPayload(
        grid_count_body_fever=body_fever[np.newaxis],
        grid_count_body_normal=body_normal[np.newaxis],
        grid_head_len=np.full(shape, head_len, dtype=np.int8),
        grid_fever_masks_bits=masks[np.newaxis],
        grid_frontier_count=np.ones(shape, dtype=np.int32),
        grid_frontier_offset=offsets[np.newaxis],
        grid_frontier_body_fever_pool=pool_bf[np.newaxis],
        grid_frontier_body_normal_pool=(total_body - pool_bf).astype(np.int32)[np.newaxis],
        grid_frontier_masks_bits_pool=pool_masks[np.newaxis],
        grid_frontier_head_coeffs_pool=head_coeffs[np.newaxis],
        grid_gap=gap[np.newaxis],
        grid_fever_activations=activations[np.newaxis],
        frontier_pool_used=int(pool_used),
    )
