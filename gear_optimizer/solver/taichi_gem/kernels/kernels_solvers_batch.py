"""Small result-staging kernels shared by GPU genome evaluation paths."""

import taichi as ti

from . import kernels_helpers


@ti.kernel
def copy_genome_result_stats_to_download_staging_kernel(out_stats: ti.template(), n_genomes: ti.i32):
    """
    Copy the populated slice of `genome_result_stats` into a smaller staging field.

    On Vulkan, `to_numpy()` transfers the full field shape, so downloading the padded
    MAX_GENOMES buffer can dominate throughput when only a small prefix is active.
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for g in range(n_genomes):
        out_stats[g] = kernels_helpers.genome_result_stats[g]
