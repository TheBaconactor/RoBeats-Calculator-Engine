"""
Taichi Kernels - GPU-Native Skyline candidate Operations.

This module contains the registry upload kernel:
- skyline_upload_item_stats_and_slots_kernel: Upload item stats and slot pools
"""

import taichi as ti


from . import kernels_helpers
from .kernels_helpers import GpuColorFlags


@ti.kernel
def skyline_upload_item_stats_and_slots_kernel(
    item_stats_src: ti.types.ndarray(dtype=ti.i32, ndim=2),
    n_items: ti.i32,
    slot_start_src: ti.types.ndarray(dtype=ti.i32, ndim=1),
    slot_count_src: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    """
    Upload per-item stats and slot pool boundaries without padded CPU buffers.

    This avoids uploading a full MAX_ITEMS x ITEM_STAT_DIM table for every song;
    only the first `n_items` rows are copied.
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for i, j in ti.ndrange(n_items, ti.static(10)):
        kernels_helpers.item_stats[i, j] = item_stats_src[i, j]

    for s in ti.static(range(9)):
        kernels_helpers.slot_start[s] = slot_start_src[s]
        kernels_helpers.slot_count[s] = slot_count_src[s]
