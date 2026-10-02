"""Engine-physical Base fever frontier construction.

Base and force-Great scoring share one lane-aware response producer. Base invokes that producer
with no Great actions, so chart order, lane matching, simultaneous press/release dispatch, fever
activation, and Pareto reduction are decided by the same canonical engine model before any surface
is uploaded or persisted.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


from .taichi_gem.fields import GRID_SIZE, MAX_TIMELINE_FRONTIER_SURFACES

_MAX_HEAD = 100


def configure_timeline_pair_build_threads(max_threads: int) -> int:
    """Size the shared exact lane-aware frontier reducer used by Base and FG."""
    from .taichi_gem.force_greats.response_build_gpu_reducer import (
        configure_force_greats_response_first_frontier_threads,
    )

    return int(configure_force_greats_response_first_frontier_threads(int(max_threads)))


@dataclass(frozen=True, slots=True)
class TimelineExactSignature:
    head_len: int
    head_bits: tuple[int, int, int, int]
    body_fever: int
    body_normal: int


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


def _surface_sort_key(surface: TimelineExactSignature) -> tuple[int, int, int, int, int]:
    return (
        int(surface.body_fever),
        int(surface.head_bits[3]) & 0xFFFFFFFF,
        int(surface.head_bits[2]) & 0xFFFFFFFF,
        int(surface.head_bits[1]) & 0xFFFFFFFF,
        int(surface.head_bits[0]) & 0xFFFFFFFF,
    )


def _head_mask_coefficients_py(
    m0: int,
    m1: int,
    m2: int,
    m3: int,
    head_len: int,
) -> tuple[int, int, int, int]:
    n_hn = 0
    n_hf = 0
    sigma_hn = 0
    sigma_hf = 0
    words = (int(m0), int(m1), int(m2), int(m3))
    for note_index in range(max(0, int(head_len))):
        position = note_index + 1
        fever = (words[note_index // 32] >> (note_index % 32)) & 1
        if fever:
            n_hf += 1
            sigma_hf += position
        else:
            n_hn += 1
            sigma_hn += position
    return n_hn, n_hf, sigma_hn, sigma_hf


def reconstruct_timeline_physical_trace(
    *,
    head_bits: tuple[int, int, int, int],
    body_fever: int,
    timestamps: np.ndarray,
    perfect_candidate_timestamps: np.ndarray,
    great_candidate_timestamps: np.ndarray,
    perfect_floor_timestamps: np.ndarray,
    great_floor_timestamps: np.ndarray,
    lanes: np.ndarray,
    raw_fever_fill: float,
    real_fever_time: float,
) -> list[dict[str, object]]:
    """Decode one retained Base surface through the same exact lane-aware producer owner."""
    from .taichi_gem.force_greats.response_builder import reconstruct_force_greats_response_trace
    from .taichi_gem.force_greats.response_types import FgResponseSurface

    surface = FgResponseSurface(
        int(head_bits[0]),
        int(head_bits[1]),
        int(head_bits[2]),
        int(head_bits[3]),
        0,
        0,
        0,
        0,
        int(body_fever),
        0,
        0,
    )
    return reconstruct_force_greats_response_trace(
        non_fever_base=0,
        target_surface=surface,
        timestamps=np.asarray(timestamps, dtype=np.float32),
        perfect_candidate_timestamps=np.asarray(
            perfect_candidate_timestamps, dtype=np.float32
        ),
        great_candidate_timestamps=np.asarray(great_candidate_timestamps, dtype=np.float32),
        perfect_floor_timestamps=np.asarray(perfect_floor_timestamps, dtype=np.float32),
        great_floor_timestamps=np.asarray(great_floor_timestamps, dtype=np.float32),
        lanes=np.asarray(lanes, dtype=np.int32),
        raw_fever_fill=float(raw_fever_fill),
        real_fever_time=float(real_fever_time),
        use_forced_great_timing=False,
    )


def build_timeline_frontier_grid_payload(
    *,
    total_notes: int,
    timestamps: np.ndarray,
    perfect_candidate_timestamps: np.ndarray,
    perfect_floor_timestamps: np.ndarray,
    lanes: np.ndarray,
    fever_times: np.ndarray,
    fever_fills: np.ndarray,
) -> TimelineFrontierGridPayload:
    """Build every FT/FF Base cell from exact lane-aware all-Perfect producer surfaces.

    `fever_times` holds each Fever Time row's window time (timing_envelope.fever_window_times), `fever_fills` each Fever
    Fill Rate row's fill in Perfects (timing_envelope.fever_fill_raw)."""
    real_times = np.asarray(fever_times, dtype=np.float64).reshape(-1)
    fills = np.asarray(fever_fills, dtype=np.float64).reshape(-1)
    if int(real_times.shape[0]) != GRID_SIZE:
        raise ValueError(f"Fever Time axis must be shape ({GRID_SIZE},), got {real_times.shape}")
    if int(fills.shape[0]) != GRID_SIZE:
        raise ValueError(f"Fever Fill Rate axis must be shape ({GRID_SIZE},), got {fills.shape}")

    n = int(total_notes)
    timestamps, perfect_candidates, perfect_floor = (
        np.ascontiguousarray(np.asarray(values, dtype=np.float32).reshape(-1))
        for values in (timestamps, perfect_candidate_timestamps, perfect_floor_timestamps)
    )
    lane_arr = np.ascontiguousarray(np.asarray(lanes, dtype=np.int32).reshape(-1))
    if any(int(values.shape[0]) != n for values in (timestamps, perfect_candidates, perfect_floor, lane_arr)):
        raise ValueError("timeline frontier physical producer arrays must match total_notes")
    if bool(np.any(timestamps[1:] < timestamps[:-1])):
        raise ValueError("timeline frontier timestamps must be sorted in chart order")

    fill_counts = np.maximum(np.ceil(fills).astype(np.int32), np.int32(1))
    unique_fill_counts, fill_inverse = np.unique(fill_counts, return_inverse=True)
    unique_real_times, time_inverse = np.unique(real_times, return_inverse=True)

    from .taichi_gem.force_greats.response_build_gpu_batch import (
        build_force_greats_response_first_frontiers_gpu_batch,
    )

    geometries = tuple(
        (float(fill_count), 0, float(real_time))
        for real_time in unique_real_times.tolist()
        for fill_count in unique_fill_counts.tolist()
    )
    physical_frontiers = build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=timestamps,
        perfect_candidate_timestamps=perfect_candidates,
        # Base has no Great judgments. Collapsing both Great envelopes onto Perfect prevents the
        # shared producer from emitting Great-only edges while preserving its lane-aware scheduler.
        great_candidate_timestamps=perfect_candidates,
        perfect_floor_timestamps=perfect_floor,
        great_floor_timestamps=perfect_floor,
        lanes=lane_arr,
        geometries=geometries,
        use_forced_great_timing=False,
    )
    if len(physical_frontiers) != len(geometries):
        raise ValueError("timeline physical producer returned the wrong number of geometries")

    head_len = min(n, _MAX_HEAD)
    total_body = max(0, n - _MAX_HEAD)
    # Identical surface lists share one pool range; dense cells are indexed (unique time, unique fill).
    pool: list[TimelineExactSignature] = []
    pool_offset_by_surfaces: dict[tuple[TimelineExactSignature, ...], int] = {}
    # Per (unique time, unique fill) cell: canonical body fever, body normal, head length, head words, surface count,
    # pool offset; the grids index these by every FT/FF stat value.
    dense = np.zeros((int(unique_real_times.size), int(unique_fill_counts.size), 9), dtype=np.int64)
    for geometry_idx, frontier in enumerate(physical_frontiers):
        surfaces: list[TimelineExactSignature] = []
        for row in frontier.first_frontier:
            if any(int(value) for value in (*row[4:8], row.body_great, row.body_fever_great)):
                raise ValueError("timeline all-Perfect producer emitted a Great response surface")
            if int(row.body_fever) < 0 or int(row.body_fever) > total_body:
                raise ValueError("timeline physical producer emitted invalid body fever count")
            surfaces.append(
                TimelineExactSignature(
                    head_len=head_len,
                    head_bits=(int(row.fever0), int(row.fever1), int(row.fever2), int(row.fever3)),
                    body_fever=int(row.body_fever),
                    body_normal=total_body - int(row.body_fever),
                )
            )
        if not surfaces:
            raise ValueError("timeline physical producer emitted an empty frontier")
        ordered = tuple(surfaces)
        offset = pool_offset_by_surfaces.get(ordered)
        if offset is None:
            if len(pool) + len(ordered) > int(MAX_TIMELINE_FRONTIER_SURFACES):
                raise RuntimeError(
                    "timeline frontier pool overflow: "
                    f"need {len(pool) + len(ordered)}, cap {MAX_TIMELINE_FRONTIER_SURFACES}"
                )
            offset = pool_offset_by_surfaces[ordered] = len(pool)
            pool.extend(ordered)
        canonical = max(ordered, key=_surface_sort_key)
        dense[divmod(geometry_idx, int(unique_fill_counts.size))] = (
            canonical.body_fever, canonical.body_normal, canonical.head_len, *canonical.head_bits, len(ordered), offset
        )

    cells = dense[time_inverse.reshape(GRID_SIZE, 1), fill_inverse.reshape(1, GRID_SIZE)][None]
    pool_shape = (1, MAX_TIMELINE_FRONTIER_SURFACES)
    body_fever_pool = np.zeros(pool_shape, dtype=np.int32)
    body_normal_pool = np.zeros(pool_shape, dtype=np.int32)
    masks_pool = np.zeros((*pool_shape, 4), dtype=np.uint32)
    coeffs_pool = np.zeros((*pool_shape, 4), dtype=np.int16)
    head_coeffs: dict[tuple[int, ...], tuple[int, int, int, int]] = {}
    for pool_idx, surface in enumerate(pool):
        key = (*surface.head_bits, int(surface.head_len))
        if key not in head_coeffs:
            head_coeffs[key] = _head_mask_coefficients_py(*surface.head_bits, head_len=surface.head_len)
        body_fever_pool[0, pool_idx] = int(surface.body_fever)
        body_normal_pool[0, pool_idx] = int(surface.body_normal)
        masks_pool[0, pool_idx, :] = np.asarray(surface.head_bits, dtype=np.uint32)
        coeffs_pool[0, pool_idx, :] = np.asarray(head_coeffs[key], dtype=np.int16)

    return TimelineFrontierGridPayload(
        grid_count_body_fever=cells[..., 0].astype(np.int32),
        grid_count_body_normal=cells[..., 1].astype(np.int32),
        grid_head_len=cells[..., 2].astype(np.int8),
        grid_fever_masks_bits=cells[..., 3:7].astype(np.uint32),
        grid_frontier_count=cells[..., 7].astype(np.int32),
        grid_frontier_offset=cells[..., 8].astype(np.int32),
        grid_frontier_body_fever_pool=body_fever_pool,
        grid_frontier_body_normal_pool=body_normal_pool,
        grid_frontier_masks_bits_pool=masks_pool,
        grid_frontier_head_coeffs_pool=coeffs_pool,
        grid_gap=np.zeros((1, GRID_SIZE, GRID_SIZE), dtype=np.int32),
        grid_fever_activations=np.zeros((1, GRID_SIZE, GRID_SIZE), dtype=np.int32),
        frontier_pool_used=len(pool),
    )
