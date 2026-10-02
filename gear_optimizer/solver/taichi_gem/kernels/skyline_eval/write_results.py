"""
Taichi Kernels - Materialize best results from packed keys.

Includes:
- skyline_write_best_results_from_key_kernel
"""

import taichi as ti

from .. import kernels_helpers
from ..kernels_helpers import GpuColorFlags
from ..write_results_common import solve_best_combo_uncached


@ti.func
def _best_combo_idx_from_chunk_state(genome_idx: ti.i32) -> ti.i32:
    return kernels_helpers.chunk_best_idx[genome_idx]


@ti.func
def _materialize_best_combo_stats(
    genome_idx: ti.i32,
    combo_idx: ti.i32,
    total_budget: ti.i32,
    gem_scale_fever: ti.i32,
    flags: GpuColorFlags,
    song_slot: ti.i32,
) -> ti.types.vector(7, ti.i32):
    ft: ti.i32 = kernels_helpers.ftff_combo_ft[combo_idx]
    ff: ti.i32 = kernels_helpers.ftff_combo_ff[combo_idx]

    best = solve_best_combo_uncached(genome_idx, ft, ff, total_budget, gem_scale_fever, flags, song_slot, False)
    return ti.Vector([best[0], ft, ff, best[1], best[2], best[3], best[4]])


@ti.func
def _write_materialized_result(genome_idx: ti.i32, result_stats: ti.types.vector(7, ti.i32)):
    kernels_helpers.genome_result_stats[genome_idx] = result_stats
    kernels_helpers.skyline_scores[genome_idx] = result_stats[0]


@ti.func
def _write_invalid_materialized_result(genome_idx: ti.i32):
    kernels_helpers.genome_result_stats[genome_idx] = ti.Vector([-1, 0, 0, 0, 0, 0, 0])
    kernels_helpers.skyline_scores[genome_idx] = -1


@ti.kernel
def skyline_write_best_results_from_key_kernel(
    n_genomes: ti.i32,
    total_budget: ti.i32,
    gem_scale_fever: ti.i32,
    flags: GpuColorFlags,
    song_slot: ti.i32,
):
    """
    Finalize best (ft, ff, gem counts) per genome from chunk_best_key.
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)

    for genome_idx in range(n_genomes):
        combo_idx = _best_combo_idx_from_chunk_state(genome_idx)
        if combo_idx < 0:
            _write_invalid_materialized_result(genome_idx)
            continue

        result_stats = _materialize_best_combo_stats(
            genome_idx,
            combo_idx,
            total_budget,
            gem_scale_fever,
            flags,
            song_slot,
        )
        _write_materialized_result(genome_idx, result_stats)


