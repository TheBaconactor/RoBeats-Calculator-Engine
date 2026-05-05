"""
Taichi Kernels - Timeline Computation.

This module contains kernels for fever timeline precomputation:
- precompute_fever_end_idx_kernel: Precompute fever end indices per (note, FT)
- binary_search_left_from: Binary search with lower bound
- binary_search_left: Binary search for leftmost index
- unpack_timeline_grid_masks_kernel: Optional debug unpack of bitpacked masks
"""

import taichi as ti

from .kernels_helpers import (
    _KERNEL_BLOCK_DIM,
)

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
    fever_time_cas: ti.f32 = last_note_time * 0.15 + 0.15  # FEVER_TIME_SCALE + FEVER_TIME_OFFSET

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


@ti.kernel
def unpack_timeline_grid_masks_kernel(song_slot: ti.i32):
    """
    Unpack bitpacked head-fever masks (4×u32) into the legacy i8 mask grid.

    Production kernels use `grid_fever_masks_bits` as the canonical representation.
    This kernel exists for debug/tests that still compare against the unpacked
    `grid_fever_masks` representation.
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    for ft_idx, ff_idx, k in ti.ndrange(161, 161, 100):
        # Unpacked masks are stored only for slot 0 to keep VRAM usage low.
        dst_slot = ti.i32(0)
        word = kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, k >> 5]
        bit = (word >> ti.u32(k & 31)) & ti.u32(1)
        kernels_helpers.grid_fever_masks[dst_slot, ft_idx, ff_idx, k] = ti.cast(bit, ti.i8)
