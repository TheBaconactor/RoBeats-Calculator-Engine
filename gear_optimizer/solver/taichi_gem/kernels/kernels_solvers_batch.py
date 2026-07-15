"""Small result-staging kernels shared by GPU loadout evaluation paths."""

import taichi as ti

from . import kernels_helpers


@ti.kernel
def copy_loadout_result_stats_to_download_staging_kernel(out_stats: ti.template(), n_loadouts: ti.i32):
    """
    Copy the populated slice of ``loadout_result_stats`` into a smaller staging field.

    On Vulkan, `to_numpy()` transfers the full field shape, so downloading the padded
    MAX_LOADOUTS buffer can dominate throughput when only a small prefix is active.
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for loadout_idx in range(n_loadouts):
        out_stats[loadout_idx] = kernels_helpers.loadout_result_stats[loadout_idx]
