"""The Base (Perfect-only) frontier of every (Fever Time, Fever Fill Rate) cell of a song, as one grid payload.

Base and Force Great scoring share one lane-aware response producer. Base runs it with no Great action, so chart order,
lane matching, simultaneous press and release, fever activation and the Pareto reduction are decided by the same model
before a surface is uploaded or persisted.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from gear_optimizer.rules import MAX_STAT

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


def _head_mask_coefficients_py(m0: int, m1: int, m2: int, m3: int, head_len: int) -> tuple[int, int, int, int]:
    """Of the first `head_len` notes, by the fever mask's four 32-bit words: how many are normal and how many fever
    notes, then the sums of their 1-based positions."""
    words = (m0, m1, m2, m3)
    n_hn = n_hf = sigma_hn = sigma_hf = 0
    for note_index in range(head_len):
        if (words[note_index // 32] >> (note_index % 32)) & 1:
            n_hf += 1
            sigma_hf += note_index + 1
        else:
            n_hn += 1
            sigma_hn += note_index + 1
    return n_hn, n_hf, sigma_hn, sigma_hf


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
    cells = []
    for frontier in frontiers:
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
        cells.append((
            body_fever, total_body - body_fever, head_len, fever_lo & _WORD, fever_lo >> 32, fever_hi & _WORD,
            fever_hi >> 32, len(surfaces), offset,
        ))
    dense = np.asarray(cells, dtype=np.int64).reshape(unique_fever_times.size, unique_fill_counts.size, 9)
    grid = dense[time_inverse.reshape(GRID_SIZE, 1), fill_inverse.reshape(1, GRID_SIZE)][None]

    pool_shape = (1, MAX_TIMELINE_FRONTIER_SURFACES)
    body_fever_pool = np.zeros(pool_shape, dtype=np.int32)
    body_normal_pool = np.zeros(pool_shape, dtype=np.int32)
    masks_pool = np.zeros((*pool_shape, 4), dtype=np.uint32)
    coeffs_pool = np.zeros((*pool_shape, 4), dtype=np.int16)
    head_coeffs: dict[tuple[int, int, int, int], tuple[int, int, int, int]] = {}
    for pool_idx, (body_fever, fever_lo, fever_hi) in enumerate(pool):
        words = (fever_lo & _WORD, fever_lo >> 32, fever_hi & _WORD, fever_hi >> 32)
        if words not in head_coeffs:
            head_coeffs[words] = _head_mask_coefficients_py(*words, head_len=head_len)
        body_fever_pool[0, pool_idx] = body_fever
        body_normal_pool[0, pool_idx] = total_body - body_fever
        masks_pool[0, pool_idx] = words
        coeffs_pool[0, pool_idx] = head_coeffs[words]

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
