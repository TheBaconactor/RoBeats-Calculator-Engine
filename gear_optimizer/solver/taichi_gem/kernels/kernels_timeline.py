"""
Taichi Kernels - Timeline Computation.

This module contains kernels for fever timeline precomputation:
- precompute_fever_end_idx_kernel: Precompute fever end indices per (note, FT)
- binary_search_left_from: Binary search with lower bound
- binary_search_left: Binary search for leftmost index
"""

import taichi as ti

from gear_optimizer.core.constants import FEVER_TIME_OFFSET, FEVER_TIME_SCALE

# Import kernels_helpers to access fields at runtime (they're bound by fields.bind_fields())
from . import kernels_helpers


@ti.kernel
def precompute_fever_end_idx_kernel(total_notes: ti.i32, last_note_time: ti.f32):
    """
    Precompute fever end indices for each (note_idx, ft_idx) using song timestamps.

    This replaces per-section binary searches in timeline simulation with O(1)
    table lookups (reduces divergent branches on GPU).
    """
    n_stat: ti.i32 = 161
    n: ti.i32 = ti.max(total_notes, 0)
    fever_time_cas: ti.f32 = last_note_time * FEVER_TIME_SCALE + FEVER_TIME_OFFSET

    for flat in range(n * n_stat):
        note_idx: ti.i32 = flat // n_stat
        ft_idx: ti.i32 = flat - (note_idx * n_stat)

        ft_factor: ti.f32 = kernels_helpers.ref_ft_field[ft_idx]
        fever_time: ti.f32 = fever_time_cas * ft_factor

        start_time: ti.f32 = kernels_helpers.song_timestamps[note_idx]
        end_time: ti.f32 = start_time + fever_time
        kernels_helpers.fever_end_idx_song[note_idx, ft_idx] = kernels_helpers.binary_search_left(
            kernels_helpers.song_timestamps, n, end_time
        )
