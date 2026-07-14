"""Engine-physical Base fever frontier construction.

Base and force-Great scoring share one lane-aware response producer. Base invokes that producer
with no Great actions, so chart order, lane matching, simultaneous press/release dispatch, fever
activation, and Pareto reduction are decided by the same canonical engine model before any surface
is uploaded or persisted.
"""

from __future__ import annotations

from dataclasses import dataclass
import time

import numpy as np

from gear_optimizer.core.constants import FEVER_FILL_BASE_RATE, FEVER_TIME_OFFSET, FEVER_TIME_SCALE
from gear_optimizer.core.profile_events import emit_profile_event

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


def _emit_frontier_phase(
    *,
    phase: str,
    start: float,
    song_key: str | None,
    song_slot: int,
    **metrics,
) -> None:
    payload = {
        "phase": str(phase),
        "ms": float((time.perf_counter() - float(start)) * 1000.0),
        "song_slot": int(song_slot),
    }
    payload.update(metrics)
    emit_profile_event(
        component="gpu_executor",
        event="timeline_frontier_phase",
        song_key=song_key,
        metrics=payload,
    )


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
    song_slot: int,
    total_notes: int,
    long_notes: int,
    last_note_time: float,
    timestamps: np.ndarray,
    perfect_candidate_timestamps: np.ndarray,
    perfect_floor_timestamps: np.ndarray,
    lanes: np.ndarray,
    ref_ft: np.ndarray,
    ref_ff: np.ndarray,
    song_key: str | None = None,
) -> TimelineFrontierGridPayload:
    """Build every FT/FF Base cell from exact lane-aware all-Perfect producer surfaces."""
    song_slot_i = int(song_slot)
    if song_slot_i < 0:
        raise ValueError(f"song_slot out of range: {song_slot_i}")

    ref_ft = np.asarray(ref_ft, dtype=np.float32).reshape(-1)
    ref_ff = np.asarray(ref_ff, dtype=np.float32).reshape(-1)
    if int(ref_ft.shape[0]) != GRID_SIZE:
        raise ValueError(f"Fever Time axis must be shape ({GRID_SIZE},), got {ref_ft.shape}")
    if int(ref_ff.shape[0]) != GRID_SIZE:
        raise ValueError(f"Fever Fill Rate axis must be shape ({GRID_SIZE},), got {ref_ff.shape}")

    total_notes_i = int(total_notes)
    long_notes_i = int(long_notes)
    timestamps = np.ascontiguousarray(np.asarray(timestamps, dtype=np.float32).reshape(-1))
    perfect_candidates = np.ascontiguousarray(
        np.asarray(perfect_candidate_timestamps, dtype=np.float32).reshape(-1)
    )
    perfect_floor = np.ascontiguousarray(
        np.asarray(perfect_floor_timestamps, dtype=np.float32).reshape(-1)
    )
    lane_arr = np.ascontiguousarray(np.asarray(lanes, dtype=np.int32).reshape(-1))
    if any(
        int(values.shape[0]) != total_notes_i
        for values in (timestamps, perfect_candidates, perfect_floor, lane_arr)
    ):
        raise ValueError("timeline frontier physical producer arrays must match total_notes")
    if bool(np.any(timestamps[1:] < timestamps[:-1])):
        raise ValueError("timeline frontier timestamps must be sorted in chart order")

    non_fever_base = float(max(0, total_notes_i - long_notes_i)) * float(FEVER_FILL_BASE_RATE)
    fever_time_base = float(last_note_time) * float(FEVER_TIME_SCALE) + float(FEVER_TIME_OFFSET)
    fill_counts = np.maximum(
        np.ceil(float(non_fever_base) * ref_ff.astype(np.float64)).astype(np.int32),
        np.int32(1),
    )
    real_times = np.maximum(
        float(fever_time_base) * ref_ft.astype(np.float64),
        np.float64(0.0),
    )
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
    build_stats: dict[str, object] = {}
    build_start = time.perf_counter()
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
        stats_sink=build_stats,
    )
    if len(physical_frontiers) != len(geometries):
        raise ValueError("timeline physical producer returned the wrong number of geometries")

    payload_slots = 1
    payload_slot = 0
    grid_count_body_fever = np.zeros((payload_slots, GRID_SIZE, GRID_SIZE), dtype=np.int32)
    grid_count_body_normal = np.zeros((payload_slots, GRID_SIZE, GRID_SIZE), dtype=np.int32)
    grid_head_len = np.zeros((payload_slots, GRID_SIZE, GRID_SIZE), dtype=np.int8)
    grid_fever_masks_bits = np.zeros((payload_slots, GRID_SIZE, GRID_SIZE, 4), dtype=np.uint32)
    grid_frontier_count = np.zeros((payload_slots, GRID_SIZE, GRID_SIZE), dtype=np.int32)
    grid_frontier_offset = np.zeros((payload_slots, GRID_SIZE, GRID_SIZE), dtype=np.int32)
    grid_frontier_body_fever_pool = np.zeros(
        (payload_slots, MAX_TIMELINE_FRONTIER_SURFACES), dtype=np.int32
    )
    grid_frontier_body_normal_pool = np.zeros(
        (payload_slots, MAX_TIMELINE_FRONTIER_SURFACES), dtype=np.int32
    )
    grid_frontier_masks_bits_pool = np.zeros(
        (payload_slots, MAX_TIMELINE_FRONTIER_SURFACES, 4), dtype=np.uint32
    )
    grid_frontier_head_coeffs_pool = np.zeros(
        (payload_slots, MAX_TIMELINE_FRONTIER_SURFACES, 4), dtype=np.int16
    )
    grid_gap = np.zeros((payload_slots, GRID_SIZE, GRID_SIZE), dtype=np.int32)
    grid_fever_activations = np.zeros((payload_slots, GRID_SIZE, GRID_SIZE), dtype=np.int32)

    pool_offset_by_pack: dict[tuple[tuple[int, ...], ...], int] = {}
    head_coeff_cache: dict[tuple[int, int, int, int, int], tuple[int, int, int, int]] = {}
    pool_cursor = 0

    def _store_surfaces(surfaces: tuple[TimelineExactSignature, ...]) -> int:
        nonlocal pool_cursor
        pack_key = tuple(
            (
                int(surface.head_bits[0]),
                int(surface.head_bits[1]),
                int(surface.head_bits[2]),
                int(surface.head_bits[3]),
                int(surface.body_fever),
                int(surface.body_normal),
            )
            for surface in surfaces
        )
        existing = pool_offset_by_pack.get(pack_key)
        if existing is not None:
            return int(existing)
        if pool_cursor + len(surfaces) > int(MAX_TIMELINE_FRONTIER_SURFACES):
            raise RuntimeError(
                "timeline frontier pool overflow: "
                f"need {pool_cursor + len(surfaces)}, cap {MAX_TIMELINE_FRONTIER_SURFACES}"
            )
        offset = int(pool_cursor)
        pool_offset_by_pack[pack_key] = offset
        for surface in surfaces:
            pool_index = int(pool_cursor)
            grid_frontier_body_fever_pool[payload_slot, pool_index] = int(surface.body_fever)
            grid_frontier_body_normal_pool[payload_slot, pool_index] = int(surface.body_normal)
            grid_frontier_masks_bits_pool[payload_slot, pool_index, :] = np.asarray(
                surface.head_bits, dtype=np.uint32
            )
            coeff_key = (*surface.head_bits, int(surface.head_len))
            coeffs = head_coeff_cache.get(coeff_key)
            if coeffs is None:
                coeffs = _head_mask_coefficients_py(*surface.head_bits, head_len=surface.head_len)
                head_coeff_cache[coeff_key] = coeffs
            grid_frontier_head_coeffs_pool[payload_slot, pool_index, :] = np.asarray(
                coeffs, dtype=np.int16
            )
            pool_cursor += 1
        return offset

    head_len = min(total_notes_i, _MAX_HEAD)
    total_body = max(0, total_notes_i - _MAX_HEAD)
    pair_cache: dict[tuple[float, int], tuple[tuple[TimelineExactSignature, ...], int]] = {}
    for geometry, frontier in zip(geometries, physical_frontiers, strict=True):
        surfaces: list[TimelineExactSignature] = []
        for row in frontier.first_frontier:
            if any(int(value) for value in (*row[4:8], row.body_great, row.body_fever_great)):
                raise ValueError("timeline all-Perfect producer emitted a Great response surface")
            body_fever = int(row.body_fever)
            if body_fever < 0 or body_fever > total_body:
                raise ValueError("timeline physical producer emitted invalid body fever count")
            surfaces.append(
                TimelineExactSignature(
                    head_len=head_len,
                    head_bits=(int(row.fever0), int(row.fever1), int(row.fever2), int(row.fever3)),
                    body_fever=body_fever,
                    body_normal=total_body - body_fever,
                )
            )
        if not surfaces:
            raise ValueError("timeline physical producer emitted an empty frontier")
        ordered = tuple(surfaces)
        pair_cache[(float(geometry[2]), int(geometry[0]))] = (ordered, _store_surfaces(ordered))

    _emit_frontier_phase(
        phase="physical_pair_builds",
        start=build_start,
        song_key=song_key,
        song_slot=song_slot_i,
        unique_fill_counts=int(unique_fill_counts.size),
        unique_real_times=int(unique_real_times.size),
        pair_count=int(len(pair_cache)),
        pair_surface_total=int(sum(len(frontier.first_frontier) for frontier in physical_frontiers)),
        pair_surface_max=int(max(len(frontier.first_frontier) for frontier in physical_frontiers)),
        unique_pool_packs=int(len(pool_offset_by_pack)),
        frontier_pool_used=int(pool_cursor),
        **{f"producer_{key}": value for key, value in build_stats.items()},
    )

    dense_shape = (int(unique_real_times.size), int(unique_fill_counts.size))
    dense_body_fever = np.zeros(dense_shape, dtype=np.int32)
    dense_body_normal = np.zeros(dense_shape, dtype=np.int32)
    dense_head_len = np.zeros(dense_shape, dtype=np.int8)
    dense_masks = np.zeros((*dense_shape, 4), dtype=np.uint32)
    dense_frontier_count = np.zeros(dense_shape, dtype=np.int32)
    dense_frontier_offset = np.zeros(dense_shape, dtype=np.int32)
    time_position = {float(value): index for index, value in enumerate(unique_real_times.tolist())}
    fill_position = {int(value): index for index, value in enumerate(unique_fill_counts.tolist())}
    for (real_time, fill_count), (surfaces, offset) in pair_cache.items():
        time_index = int(time_position[float(real_time)])
        fill_index = int(fill_position[int(fill_count)])
        canonical = max(surfaces, key=_surface_sort_key)
        dense_body_fever[time_index, fill_index] = int(canonical.body_fever)
        dense_body_normal[time_index, fill_index] = int(canonical.body_normal)
        dense_head_len[time_index, fill_index] = np.int8(canonical.head_len)
        dense_masks[time_index, fill_index, :] = np.asarray(canonical.head_bits, dtype=np.uint32)
        dense_frontier_count[time_index, fill_index] = int(len(surfaces))
        dense_frontier_offset[time_index, fill_index] = int(offset)

    grid_time_index = time_inverse.reshape(GRID_SIZE, 1)
    grid_fill_index = fill_inverse.reshape(1, GRID_SIZE)
    grid_count_body_fever[payload_slot] = dense_body_fever[grid_time_index, grid_fill_index]
    grid_count_body_normal[payload_slot] = dense_body_normal[grid_time_index, grid_fill_index]
    grid_head_len[payload_slot] = dense_head_len[grid_time_index, grid_fill_index]
    grid_fever_masks_bits[payload_slot] = dense_masks[grid_time_index, grid_fill_index]
    grid_frontier_count[payload_slot] = dense_frontier_count[grid_time_index, grid_fill_index]
    grid_frontier_offset[payload_slot] = dense_frontier_offset[grid_time_index, grid_fill_index]

    _emit_frontier_phase(
        phase="grid_fill",
        start=build_start,
        song_key=song_key,
        song_slot=song_slot_i,
        cell_count=int(GRID_SIZE * GRID_SIZE),
        frontier_cells=int(np.count_nonzero(grid_frontier_count[payload_slot])),
        frontier_variants=int(np.sum(grid_frontier_count[payload_slot], dtype=np.int64)),
        frontier_pool_used=int(pool_cursor),
    )
    return TimelineFrontierGridPayload(
        grid_count_body_fever=grid_count_body_fever,
        grid_count_body_normal=grid_count_body_normal,
        grid_head_len=grid_head_len,
        grid_fever_masks_bits=grid_fever_masks_bits,
        grid_frontier_count=grid_frontier_count,
        grid_frontier_offset=grid_frontier_offset,
        grid_frontier_body_fever_pool=grid_frontier_body_fever_pool,
        grid_frontier_body_normal_pool=grid_frontier_body_normal_pool,
        grid_frontier_masks_bits_pool=grid_frontier_masks_bits_pool,
        grid_frontier_head_coeffs_pool=grid_frontier_head_coeffs_pool,
        grid_gap=grid_gap,
        grid_fever_activations=grid_fever_activations,
        frontier_pool_used=int(pool_cursor),
    )
